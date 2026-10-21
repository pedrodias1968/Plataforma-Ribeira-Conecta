"""PostgreSQL/RLS coverage for costs by field: guards, append-only, evidence, isolation."""

from __future__ import annotations

import os
import unittest

import psycopg
from shapely.geometry import Polygon, mapping

from ribeira_platform.costs import CostEntry
from ribeira_platform.epistemology import DataClassification
from ribeira_platform.models import new_id, now_utc
from ribeira_platform.postgres import PostgresStore
from ribeira_platform.service import RibeiraApplication


DATABASE_URL = os.getenv("RIBEIRA_TEST_DATABASE_URL")


@unittest.skipUnless(DATABASE_URL, "RIBEIRA_TEST_DATABASE_URL is required")
class CostPostgresTests(unittest.TestCase):
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
            "Fazenda Custos",
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

    def entry(self, tenant_id, property_id, field_id, **overrides) -> CostEntry:
        values = {
            "id": new_id(),
            "tenant_id": tenant_id,
            "property_id": property_id,
            "field_id": field_id,
            "entry_date": "2026-10-05",
            "category": "LABOR",
            "description": "Diárias",
            "amount_brl": 500.0,
            "recorded_by": "Gerente",
            "source_reference": "caderno",
            "classification": DataClassification.MANUAL_CONFIRMED,
            "notes": None,
            "supersedes_id": None,
            "created_at": now_utc(),
        }
        values.update(overrides)
        return CostEntry(**values)

    def register(self, tenant, prop, field_id, **overrides):
        values = {
            "entry_date": "2026-10-05",
            "category": "LABOR",
            "description": "Diárias",
            "amount_brl": 500,
        }
        values.update(overrides)
        return self.application.register_cost_entry(
            tenant.id,
            prop.id,
            field_id=field_id,
            recorded_by="Gerente",
            source_reference="caderno",
            **values,
        )

    def test_entry_evidence_and_tenant_isolation(self) -> None:
        tenant_a, prop_a, (field_a, _) = self.farm("Cost PG tenant A")
        tenant_b, _, _ = self.farm("Cost PG tenant B")
        entry = self.register(tenant_a, prop_a, field_a.id, amount_brl=123.45)
        wide = self.register(tenant_a, prop_a, None, category="FUEL")
        self.assertEqual(entry.amount_brl, 123.45)
        self.assertIsNone(wide.field_id)

        with self.store.tenant_transaction(tenant_a.id):
            evidence = self.store.evidence_for_reference(tenant_a.id, entry.id)
            seen_by_a = self.store.connection.execute(
                "SELECT count(*) AS n FROM cost_entry"
            ).fetchone()["n"]
        self.assertEqual(evidence.evidence_type, "COST_ENTRY")
        self.assertEqual(seen_by_a, 2)

        with self.store.tenant_transaction(tenant_b.id):
            seen_by_b = self.store.connection.execute(
                "SELECT count(*) AS n FROM cost_entry"
            ).fetchone()["n"]
            self.assertEqual(seen_by_b, 0)
            self.assertIsNone(self.application.costs.get(tenant_b.id, entry.id))

        with self.assertRaises(psycopg.errors.InsufficientPrivilege):
            with self.store.tenant_transaction(tenant_b.id):
                self.application.costs.create(
                    self.entry(tenant_a.id, prop_a.id, field_a.id)
                )
        with self.assertRaises(LookupError):
            self.register(tenant_b, prop_a, None)

    def test_database_rejects_a_field_from_another_property(self) -> None:
        tenant, _, (field_a, _) = self.farm("Cost PG guard tenant")
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
                self.application.costs.create(
                    self.entry(tenant.id, other.id, field_a.id)
                )

    def test_corrections_keep_field_and_allow_a_single_successor(self) -> None:
        tenant, prop, (field_a, field_b) = self.farm("Cost PG correction tenant")
        with self.store.tenant_transaction(tenant.id):
            original = self.application.costs.create(
                self.entry(tenant.id, prop.id, field_a.id)
            )
            first = self.application.costs.create(
                self.entry(tenant.id, prop.id, field_a.id, supersedes_id=original.id)
            )
            wide = self.application.costs.create(self.entry(tenant.id, prop.id, None))
        self.assertEqual(first.supersedes_id, original.id)
        with self.assertRaises(psycopg.errors.UniqueViolation):
            with self.store.tenant_transaction(tenant.id):
                self.application.costs.create(
                    self.entry(
                        tenant.id, prop.id, field_a.id, supersedes_id=original.id
                    )
                )
        # A correction cannot move the cost to another field, nor allocate a
        # property-wide cost to a field.
        with self.assertRaises(psycopg.errors.ForeignKeyViolation):
            with self.store.tenant_transaction(tenant.id):
                self.application.costs.create(
                    self.entry(tenant.id, prop.id, field_b.id, supersedes_id=first.id)
                )
        with self.assertRaises(psycopg.errors.ForeignKeyViolation):
            with self.store.tenant_transaction(tenant.id):
                self.application.costs.create(
                    self.entry(tenant.id, prop.id, field_a.id, supersedes_id=wide.id)
                )

    def test_application_role_cannot_update_or_delete(self) -> None:
        tenant, prop, (field_a, _) = self.farm("Cost PG append-only tenant")
        entry = self.register(tenant, prop, field_a.id)
        for statement in (
            "UPDATE cost_entry SET amount_brl = 1 WHERE id = %s",
            "DELETE FROM cost_entry WHERE id = %s",
        ):
            with self.subTest(statement=statement):
                with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                    with self.store.tenant_transaction(tenant.id):
                        self.store.connection.execute(statement, (entry.id,))
        self.assertEqual(
            self.application.costs.get(tenant.id, entry.id).amount_brl, 500.0
        )

    def test_database_constraints(self) -> None:
        tenant, prop, (field_a, _) = self.farm("Cost PG constraint tenant")
        cases = {
            "fertilizer category": {"category": "FERTILIZER"},
            "unknown category": {"category": "MAGIC"},
            "negative amount": {"amount_brl": -1.0},
            "OTHER without notes": {"category": "OTHER"},
            "blank description": {"description": " "},
            "blank recorder": {"recorded_by": " "},
        }
        for label, overrides in cases.items():
            with self.subTest(case=label):
                with self.assertRaises(psycopg.errors.CheckViolation):
                    with self.store.tenant_transaction(tenant.id):
                        self.application.costs.create(
                            self.entry(tenant.id, prop.id, field_a.id, **overrides)
                        )

    def test_cost_per_kg_on_postgres(self) -> None:
        tenant, prop, (field_a, field_b) = self.farm("Cost PG summary tenant")
        self.register(tenant, prop, field_a.id, amount_brl=300)
        self.register(tenant, prop, None, category="FUEL", amount_brl=1000)
        self.application.register_fertilization_record(
            tenant.id,
            prop.id,
            field_id=field_a.id,
            application_date="2026-10-10",
            product_name="Ureia",
            product_type="MINERAL_FERTILIZER",
            cost_brl=100,
            applied_by="João",
            recorded_by="Gerente",
            source_reference="caderno",
        )
        for day, weight in (("2026-10-15", 150), ("2026-10-16", 250)):
            self.application.register_harvest_record(
                tenant.id,
                prop.id,
                field_id=field_a.id,
                harvest_date=day,
                weight_kg=weight,
                recorded_by="Encarregado",
                source_reference="caderno",
            )
        summary = self.application.cost_summary(tenant.id, prop.id)
        by_field = {x["field_id"]: x for x in summary["fields"]}
        block = by_field[field_a.id]
        self.assertEqual(block["allocated_cost_total"], 400.0)
        self.assertEqual(block["harvest"]["weight_kg_total"], 400.0)
        self.assertEqual(block["cost_per_kg"], 1.0)
        self.assertEqual(summary["unallocated_cost"]["total"], 1000.0)
        self.assertIsNone(by_field[field_b.id]["allocated_cost_total"])
        self.assertEqual(
            by_field[field_b.id]["cost_per_kg_unavailable_reason"], "NO_COST_DATA"
        )


if __name__ == "__main__":
    unittest.main()
