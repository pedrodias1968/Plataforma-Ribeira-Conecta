"""PostgreSQL/RLS coverage for fertilization by field: guards, append-only, evidence, isolation."""

from __future__ import annotations

import os
import unittest

import psycopg
from shapely.geometry import Polygon, mapping

from ribeira_platform.epistemology import DataClassification
from ribeira_platform.fertilization import FertilizationRecord
from ribeira_platform.models import new_id, now_utc
from ribeira_platform.postgres import PostgresStore
from ribeira_platform.service import RibeiraApplication


DATABASE_URL = os.getenv("RIBEIRA_TEST_DATABASE_URL")


@unittest.skipUnless(DATABASE_URL, "RIBEIRA_TEST_DATABASE_URL is required")
class FertilizationPostgresTests(unittest.TestCase):
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
        tenant = self.application.create_tenant(tenant_name)
        prop = self.application.create_property(
            tenant.id,
            "Fazenda Adubação",
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

    def item(
        self, tenant_id, property_id, field_id, **overrides
    ) -> FertilizationRecord:
        values = {
            "id": new_id(),
            "tenant_id": tenant_id,
            "property_id": property_id,
            "field_id": field_id,
            "application_date": "2026-10-10",
            "product_name": "Ureia",
            "product_type": "MINERAL_FERTILIZER",
            "quantity": 50.0,
            "quantity_unit": "KG",
            "area_applied_ha": None,
            "application_method": None,
            "cost_brl": None,
            "applied_by": "João",
            "recorded_by": "Encarregado",
            "source_reference": "caderno",
            "classification": DataClassification.MANUAL_CONFIRMED,
            "notes": None,
            "supersedes_id": None,
            "created_at": now_utc(),
        }
        values.update(overrides)
        return FertilizationRecord(**values)

    def register(self, tenant, prop, field, **overrides):
        values = {
            "application_date": "2026-10-10",
            "product_name": "Ureia",
            "product_type": "MINERAL_FERTILIZER",
            "quantity": 50,
            "quantity_unit": "KG",
            "applied_by": "João",
        }
        values.update(overrides)
        return self.application.register_fertilization_record(
            tenant.id,
            prop.id,
            field_id=field.id,
            recorded_by="Encarregado",
            source_reference="caderno",
            **values,
        )

    def test_record_evidence_and_tenant_isolation(self) -> None:
        tenant_a, prop_a, (field_a, _) = self.farm("Fert PG tenant A")
        tenant_b, _, _ = self.farm("Fert PG tenant B")
        record = self.register(tenant_a, prop_a, field_a, cost_brl=123.45)
        self.assertEqual(record.cost_brl, 123.45)
        self.assertIsNone(record.area_applied_ha)

        with self.store.tenant_transaction(tenant_a.id):
            evidence = self.store.evidence_for_reference(tenant_a.id, record.id)
            seen_by_a = self.store.connection.execute(
                "SELECT count(*) AS n FROM fertilization_record"
            ).fetchone()["n"]
        self.assertEqual(evidence.evidence_type, "FERTILIZATION_RECORD")
        self.assertEqual(seen_by_a, 1)

        with self.store.tenant_transaction(tenant_b.id):
            seen_by_b = self.store.connection.execute(
                "SELECT count(*) AS n FROM fertilization_record"
            ).fetchone()["n"]
            self.assertEqual(seen_by_b, 0)
            self.assertIsNone(
                self.application.fertilization.get(tenant_b.id, record.id)
            )

        with self.assertRaises(psycopg.errors.InsufficientPrivilege):
            with self.store.tenant_transaction(tenant_b.id):
                self.application.fertilization.create(
                    self.item(tenant_a.id, prop_a.id, field_a.id)
                )
        with self.assertRaises(LookupError):
            self.register(tenant_b, prop_a, field_a)

    def test_database_rejects_a_field_from_another_property(self) -> None:
        tenant, _, (field_a, _) = self.farm("Fert PG guard tenant")
        other = self.application.create_property(
            tenant.id,
            "Outro sítio",
            self.polygon(-47.1, -24.12, -47.08, -24.1),
            "EPSG:4326",
            boundary_source="synthetic integration boundary",
            classification=DataClassification.MANUAL_CONFIRMED,
        )
        with self.assertRaises(psycopg.errors.ForeignKeyViolation):
            with self.store.tenant_transaction(tenant.id):
                self.application.fertilization.create(
                    self.item(tenant.id, other.id, field_a.id)
                )

    def test_corrections_keep_field_and_allow_a_single_successor(self) -> None:
        tenant, prop, (field_a, field_b) = self.farm("Fert PG correction tenant")
        with self.store.tenant_transaction(tenant.id):
            original = self.application.fertilization.create(
                self.item(tenant.id, prop.id, field_a.id)
            )
            first = self.application.fertilization.create(
                self.item(tenant.id, prop.id, field_a.id, supersedes_id=original.id)
            )
        self.assertEqual(first.supersedes_id, original.id)
        with self.assertRaises(psycopg.errors.UniqueViolation):
            with self.store.tenant_transaction(tenant.id):
                self.application.fertilization.create(
                    self.item(tenant.id, prop.id, field_a.id, supersedes_id=original.id)
                )
        with self.assertRaises(psycopg.errors.ForeignKeyViolation):
            with self.store.tenant_transaction(tenant.id):
                self.application.fertilization.create(
                    self.item(tenant.id, prop.id, field_b.id, supersedes_id=first.id)
                )

    def test_application_role_cannot_update_or_delete(self) -> None:
        tenant, prop, (field_a, _) = self.farm("Fert PG append-only tenant")
        record = self.register(tenant, prop, field_a)
        for statement in (
            "UPDATE fertilization_record SET quantity = 1 WHERE id = %s",
            "DELETE FROM fertilization_record WHERE id = %s",
        ):
            with self.subTest(statement=statement):
                with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                    with self.store.tenant_transaction(tenant.id):
                        self.store.connection.execute(statement, (record.id,))
        stored = self.application.fertilization.get(tenant.id, record.id)
        self.assertEqual(stored.quantity, 50.0)

    def test_database_constraints(self) -> None:
        tenant, prop, (field_a, _) = self.farm("Fert PG constraint tenant")
        cases = {
            "quantity without unit": {"quantity_unit": None},
            "unit without quantity": {"quantity": None},
            "unknown unit": {"quantity_unit": "TON"},
            "negative quantity": {"quantity": -1.0},
            "unknown product type": {"product_type": "MAGIC"},
            "OTHER without notes": {"product_type": "OTHER"},
            "zero area": {"area_applied_ha": 0.0},
            "negative cost": {"cost_brl": -1.0},
            "blank product": {"product_name": "  "},
            "blank applicator": {"applied_by": " "},
        }
        for label, overrides in cases.items():
            with self.subTest(case=label):
                with self.assertRaises(psycopg.errors.CheckViolation):
                    with self.store.tenant_transaction(tenant.id):
                        self.application.fertilization.create(
                            self.item(tenant.id, prop.id, field_a.id, **overrides)
                        )

    def test_summary_and_corrections_on_postgres(self) -> None:
        tenant, prop, (field_a, field_b) = self.farm("Fert PG summary tenant")
        old = self.register(tenant, prop, field_a, application_date="2026-09-01")
        wrong = self.register(
            tenant, prop, field_a, application_date="2026-10-20", cost_brl=999
        )
        fixed = self.application.correct_fertilization_record(
            tenant.id,
            wrong.id,
            correction_reason="custo refeito",
            application_date="2026-10-20",
            product_name="Ureia",
            product_type="MINERAL_FERTILIZER",
            quantity=50,
            quantity_unit="KG",
            cost_brl=90,
            applied_by="João",
            recorded_by="Encarregado",
            source_reference="caderno",
        )
        current = self.application.list_fertilization_records(tenant.id, prop.id)
        self.assertEqual({x.id for x in current}, {old.id, fixed.id})
        history = self.application.list_fertilization_records(
            tenant.id, prop.id, include_superseded=True
        )
        self.assertEqual(len(history), 3)
        summary = self.application.fertilization_summary(
            tenant.id, prop.id, date_from="2026-10-01"
        )
        by_field = {x["field_id"]: x for x in summary["fields"]}
        self.assertEqual(by_field[field_a.id]["cost_brl"]["total"], 90.0)
        self.assertEqual(by_field[field_a.id]["quantity_by_unit"], {"KG": 50.0})
        self.assertTrue(by_field[field_b.id]["no_fertilization_records"])
        self.assertIsNone(by_field[field_b.id]["cost_brl"]["total"])


if __name__ == "__main__":
    unittest.main()
