"""PostgreSQL/RLS coverage for harvest by field: guards, append-only, evidence, tenant isolation."""

from __future__ import annotations

import os
import unittest

import psycopg
from shapely.geometry import Polygon, mapping

from ribeira_platform.epistemology import DataClassification
from ribeira_platform.harvest import HarvestDiscard, HarvestRecord
from ribeira_platform.models import new_id, now_utc
from ribeira_platform.postgres import PostgresStore
from ribeira_platform.service import RibeiraApplication


DATABASE_URL = os.getenv("RIBEIRA_TEST_DATABASE_URL")


@unittest.skipUnless(DATABASE_URL, "RIBEIRA_TEST_DATABASE_URL is required")
class HarvestPostgresTests(unittest.TestCase):
    def setUp(self) -> None:
        self.store = PostgresStore(DATABASE_URL)  # type: ignore[arg-type]
        self.application = RibeiraApplication(self.store)
        self.store.connection.execute("BEGIN")

    def tearDown(self) -> None:
        self.store.connection.rollback()
        self.store.close()

    @staticmethod
    def polygon(west: float, south: float, east: float, north: float) -> dict:
        return mapping(
            Polygon(
                [
                    (west, south),
                    (east, south),
                    (east, north),
                    (west, north),
                    (west, south),
                ]
            )
        )

    def farm(self, tenant_name: str):
        """A tenant with one property holding two fields."""
        tenant = self.application.create_tenant(tenant_name)
        prop = self.application.create_property(
            tenant.id,
            "Fazenda Colheita",
            self.polygon(-47.0, -24.02, -46.98, -24.0),
            "EPSG:4326",
            boundary_source="synthetic integration boundary",
            classification=DataClassification.MANUAL_CONFIRMED,
        )
        fields = [
            self.application.fields.create(
                tenant.id,
                property_id=prop.id,
                name=name,
                status="ACTIVE",
                geometry_geojson=geometry,
                geometry_crs="EPSG:4326",
                source_reference="synthetic integration field walk",
                observed_at="2026-09-24T12:00:00+00:00",
                classification=DataClassification.MANUAL_CONFIRMED,
                actor="integration-operator",
            )
            for name, geometry in (
                ("Talhão A", self.polygon(-46.995, -24.010, -46.985, -24.005)),
                ("Talhão B", self.polygon(-46.995, -24.017, -46.985, -24.012)),
            )
        ]
        return tenant, prop, fields

    def record_item(
        self, tenant_id, property_id, field_id, **overrides
    ) -> HarvestRecord:
        values = {
            "id": new_id(),
            "tenant_id": tenant_id,
            "property_id": property_id,
            "field_id": field_id,
            "harvest_date": "2026-10-15",
            "bunches_harvested": None,
            "boxes_packed": 100,
            "weight_kg": None,
            "cut_criterion": None,
            "recorded_by": "Encarregado",
            "source_reference": "caderno",
            "classification": DataClassification.MANUAL_CONFIRMED,
            "notes": None,
            "supersedes_id": None,
            "created_at": now_utc(),
        }
        values.update(overrides)
        return HarvestRecord(**values)

    def discard_item(
        self, tenant_id, property_id, field_id, **overrides
    ) -> HarvestDiscard:
        values = {
            "id": new_id(),
            "tenant_id": tenant_id,
            "property_id": property_id,
            "field_id": field_id,
            "discard_date": "2026-10-15",
            "reason": "STAIN",
            "quantity": 5.0,
            "unit": "BOXES",
            "recorded_by": "Encarregado",
            "source_reference": "caderno",
            "classification": DataClassification.MANUAL_CONFIRMED,
            "notes": None,
            "supersedes_id": None,
            "created_at": now_utc(),
        }
        values.update(overrides)
        return HarvestDiscard(**values)

    def test_records_discards_evidence_and_tenant_isolation(self) -> None:
        tenant_a, prop_a, (field_a, _) = self.farm("Harvest PG tenant A")
        tenant_b, _, _ = self.farm("Harvest PG tenant B")

        record = self.application.register_harvest_record(
            tenant_a.id,
            prop_a.id,
            field_id=field_a.id,
            harvest_date="2026-10-15",
            boxes_packed=120,
            weight_kg=2400.5,
            recorded_by="Encarregado",
            source_reference="caderno",
            actor="operator@test.local",
        )
        discard = self.application.register_harvest_discard(
            tenant_a.id,
            prop_a.id,
            field_id=field_a.id,
            discard_date="2026-10-15",
            reason="MECHANICAL_DAMAGE",
            quantity=7,
            unit="BOXES",
            recorded_by="Encarregado",
            source_reference="caderno",
            actor="operator@test.local",
        )
        self.assertEqual(record.harvest_date, "2026-10-15")
        self.assertEqual(record.weight_kg, 2400.5)
        self.assertIsNone(record.bunches_harvested)

        with self.store.tenant_transaction(tenant_a.id):
            record_evidence = self.store.evidence_for_reference(tenant_a.id, record.id)
            discard_evidence = self.store.evidence_for_reference(
                tenant_a.id, discard.id
            )
            visible_to_a = self.store.connection.execute(
                "SELECT count(*) AS n FROM harvest_record"
            ).fetchone()["n"]
        self.assertEqual(record_evidence.evidence_type, "HARVEST_RECORD")
        self.assertEqual(discard_evidence.evidence_type, "HARVEST_DISCARD")
        self.assertEqual(visible_to_a, 1)

        with self.store.tenant_transaction(tenant_b.id):
            visible_to_b = self.store.connection.execute(
                "SELECT (SELECT count(*) FROM harvest_record) AS records,"
                "       (SELECT count(*) FROM harvest_discard) AS discards"
            ).fetchone()
            self.assertEqual(visible_to_b["records"], 0)
            self.assertEqual(visible_to_b["discards"], 0)
            self.assertIsNone(
                self.application.harvest.get_record(tenant_b.id, record.id)
            )

        # Tenant B cannot write a row that belongs to tenant A.
        with self.assertRaises(psycopg.errors.InsufficientPrivilege):
            with self.store.tenant_transaction(tenant_b.id):
                self.application.harvest.create_record(
                    self.record_item(tenant_a.id, prop_a.id, field_a.id)
                )

        # The service also refuses a property outside the tenant.
        with self.assertRaises(LookupError):
            self.application.register_harvest_record(
                tenant_b.id,
                prop_a.id,
                field_id=field_a.id,
                harvest_date="2026-10-15",
                boxes_packed=1,
                recorded_by="Encarregado",
                source_reference="caderno",
            )

    def test_database_rejects_a_field_from_another_property(self) -> None:
        tenant, prop_a, (field_a, _) = self.farm("Harvest PG guard tenant")
        prop_b = self.application.create_property(
            tenant.id,
            "Outro sítio",
            self.polygon(-47.1, -24.12, -47.08, -24.1),
            "EPSG:4326",
            boundary_source="synthetic integration boundary",
            classification=DataClassification.MANUAL_CONFIRMED,
        )
        with self.assertRaises(psycopg.errors.ForeignKeyViolation):
            with self.store.tenant_transaction(tenant.id):
                self.application.harvest.create_record(
                    self.record_item(tenant.id, prop_b.id, field_a.id)
                )
        with self.assertRaises(psycopg.errors.ForeignKeyViolation):
            with self.store.tenant_transaction(tenant.id):
                self.application.harvest.create_discard(
                    self.discard_item(tenant.id, prop_b.id, field_a.id)
                )

    def test_corrections_keep_field_and_allow_a_single_successor(self) -> None:
        tenant, prop, (field_a, field_b) = self.farm("Harvest PG correction tenant")
        with self.store.tenant_transaction(tenant.id):
            original = self.application.harvest.create_record(
                self.record_item(tenant.id, prop.id, field_a.id)
            )
            first = self.application.harvest.create_record(
                self.record_item(
                    tenant.id, prop.id, field_a.id, supersedes_id=original.id
                )
            )
        self.assertEqual(first.supersedes_id, original.id)

        with self.assertRaises(psycopg.errors.UniqueViolation):
            with self.store.tenant_transaction(tenant.id):
                self.application.harvest.create_record(
                    self.record_item(
                        tenant.id, prop.id, field_a.id, supersedes_id=original.id
                    )
                )
        # A correction cannot move the record to another field.
        with self.assertRaises(psycopg.errors.ForeignKeyViolation):
            with self.store.tenant_transaction(tenant.id):
                self.application.harvest.create_record(
                    self.record_item(
                        tenant.id, prop.id, field_b.id, supersedes_id=first.id
                    )
                )

    def test_application_role_cannot_update_or_delete(self) -> None:
        tenant, prop, (field_a, _) = self.farm("Harvest PG append-only tenant")
        record = self.application.register_harvest_record(
            tenant.id,
            prop.id,
            field_id=field_a.id,
            harvest_date="2026-10-15",
            boxes_packed=50,
            recorded_by="Encarregado",
            source_reference="caderno",
        )
        discard = self.application.register_harvest_discard(
            tenant.id,
            prop.id,
            field_id=field_a.id,
            discard_date="2026-10-15",
            reason="STAIN",
            quantity=2,
            unit="BOXES",
            recorded_by="Encarregado",
            source_reference="caderno",
        )
        statements = (
            ("UPDATE harvest_record SET boxes_packed = 1 WHERE id = %s", record.id),
            ("DELETE FROM harvest_record WHERE id = %s", record.id),
            ("UPDATE harvest_discard SET quantity = 1 WHERE id = %s", discard.id),
            ("DELETE FROM harvest_discard WHERE id = %s", discard.id),
        )
        for statement, row_id in statements:
            with self.subTest(statement=statement):
                with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                    with self.store.tenant_transaction(tenant.id):
                        self.store.connection.execute(statement, (row_id,))
        stored = self.application.harvest.get_record(tenant.id, record.id)
        self.assertEqual(stored.boxes_packed, 50)

    def test_database_constraints(self) -> None:
        tenant, prop, (field_a, _) = self.farm("Harvest PG constraint tenant")
        invalid_rows = {
            "no measure at all": lambda: self.application.harvest.create_record(
                self.record_item(tenant.id, prop.id, field_a.id, boxes_packed=None)
            ),
            "negative boxes": lambda: self.application.harvest.create_record(
                self.record_item(tenant.id, prop.id, field_a.id, boxes_packed=-1)
            ),
            "blank recorder": lambda: self.application.harvest.create_record(
                self.record_item(tenant.id, prop.id, field_a.id, recorded_by="  ")
            ),
            "unknown discard reason": lambda: self.application.harvest.create_discard(
                self.discard_item(tenant.id, prop.id, field_a.id, reason="ROTTEN")
            ),
            "unknown discard unit": lambda: self.application.harvest.create_discard(
                self.discard_item(tenant.id, prop.id, field_a.id, unit="TONS")
            ),
            "negative discard": lambda: self.application.harvest.create_discard(
                self.discard_item(tenant.id, prop.id, field_a.id, quantity=-1.0)
            ),
            "OTHER without notes": lambda: self.application.harvest.create_discard(
                self.discard_item(tenant.id, prop.id, field_a.id, reason="OTHER")
            ),
        }
        for label, action in invalid_rows.items():
            with self.subTest(case=label):
                with self.assertRaises(psycopg.errors.CheckViolation):
                    with self.store.tenant_transaction(tenant.id):
                        action()

    def test_summary_filters_and_corrections_on_postgres(self) -> None:
        tenant, prop, (field_a, field_b) = self.farm("Harvest PG summary tenant")
        kwargs = dict(recorded_by="Encarregado", source_reference="caderno")
        old = self.application.register_harvest_record(
            tenant.id,
            prop.id,
            field_id=field_a.id,
            harvest_date="2026-10-01",
            boxes_packed=10,
            **kwargs,
        )
        wrong = self.application.register_harvest_record(
            tenant.id,
            prop.id,
            field_id=field_a.id,
            harvest_date="2026-10-20",
            boxes_packed=999,
            weight_kg=1000,
            **kwargs,
        )
        fixed = self.application.correct_harvest_record(
            tenant.id,
            wrong.id,
            correction_reason="contagem refeita",
            harvest_date="2026-10-20",
            boxes_packed=90,
            weight_kg=1000,
            **kwargs,
        )
        self.application.register_harvest_discard(
            tenant.id,
            prop.id,
            field_id=field_a.id,
            discard_date="2026-10-20",
            reason="CALIBER",
            quantity=3,
            unit="BOXES",
            **kwargs,
        )

        everything = self.application.list_harvest_records(tenant.id, prop.id)
        self.assertEqual({item.id for item in everything}, {old.id, fixed.id})
        history = self.application.list_harvest_records(
            tenant.id, prop.id, include_superseded=True
        )
        self.assertEqual(len(history), 3)
        window = self.application.list_harvest_records(
            tenant.id, prop.id, date_from="2026-10-15", date_to="2026-10-31"
        )
        self.assertEqual([item.id for item in window], [fixed.id])

        summary = self.application.harvest_summary(
            tenant.id, prop.id, date_from="2026-10-15", date_to="2026-10-31"
        )
        by_field = {item["field_id"]: item for item in summary["fields"]}
        self.assertEqual(by_field[field_a.id]["boxes_packed"]["total"], 90)
        self.assertEqual(by_field[field_a.id]["weight_kg"]["total"], 1000.0)
        self.assertEqual(
            by_field[field_a.id]["discards_by_unit"]["BOXES"]["by_reason"],
            {"CALIBER": 3.0},
        )
        self.assertTrue(by_field[field_b.id]["no_harvest_records"])
        self.assertIsNone(by_field[field_b.id]["boxes_packed"]["total"])


if __name__ == "__main__":
    unittest.main()
