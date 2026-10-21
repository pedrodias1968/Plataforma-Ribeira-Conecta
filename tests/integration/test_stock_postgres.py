"""PostgreSQL/RLS coverage for stock movements: guards, append-only, evidence, isolation."""

from __future__ import annotations

import os
import unittest

import psycopg
from shapely.geometry import Polygon, mapping

from ribeira_platform.epistemology import DataClassification
from ribeira_platform.models import new_id, now_utc
from ribeira_platform.postgres import PostgresStore
from ribeira_platform.service import RibeiraApplication
from ribeira_platform.stock import StockMovement

DATABASE_URL = os.getenv("RIBEIRA_TEST_DATABASE_URL")


@unittest.skipUnless(DATABASE_URL, "RIBEIRA_TEST_DATABASE_URL is required")
class StockPostgresTests(unittest.TestCase):
    def setUp(self) -> None:
        self.store = PostgresStore(DATABASE_URL)  # type: ignore[arg-type]
        self.application = RibeiraApplication(self.store)
        self.store.connection.execute("BEGIN")

    def tearDown(self) -> None:
        self.store.connection.rollback()
        self.store.close()

    @staticmethod
    def polygon(west: float, south: float, east: float, north: float) -> dict:
        ring = [
            (west, south),
            (east, south),
            (east, north),
            (west, north),
            (west, south),
        ]
        return mapping(Polygon(ring))

    def farm(
        self,
        tenant_name: str,
        boundary=(-47.0, -24.02, -46.98, -24.0),
        name="Fazenda Estoque",
    ):
        tenant = self.application.create_tenant(tenant_name)
        prop = self.application.create_property(
            tenant.id,
            name,
            self.polygon(*boundary),
            "EPSG:4326",
            boundary_source="synthetic integration boundary",
            classification=DataClassification.MANUAL_CONFIRMED,
        )
        return tenant, prop

    def item(self, tenant_id, property_id, **overrides) -> StockMovement:
        values = {
            "id": new_id(),
            "tenant_id": tenant_id,
            "property_id": property_id,
            "movement_date": "2026-10-01",
            "movement_type": "IN",
            "item_name": "Ureia",
            "unit": "KG",
            "quantity": 100.0,
            "counterparty": None,
            "recorded_by": "Encarregado",
            "source_reference": "caderno",
            "classification": DataClassification.MANUAL_CONFIRMED,
            "notes": None,
            "supersedes_id": None,
            "created_at": now_utc(),
        }
        values.update(overrides)
        return StockMovement(**values)

    def register(self, tenant, prop, **overrides):
        values = {
            "movement_date": "2026-10-01",
            "movement_type": "IN",
            "item_name": "Ureia",
            "unit": "KG",
            "quantity": 100,
        }
        values.update(overrides)
        return self.application.register_stock_movement(
            tenant.id,
            prop.id,
            recorded_by="Encarregado",
            source_reference="caderno",
            **values,
        )

    def test_evidence_and_tenant_isolation(self) -> None:
        tenant_a, prop_a = self.farm("Stock PG tenant A")
        tenant_b, _ = self.farm("Stock PG tenant B")
        move = self.register(tenant_a, prop_a)
        with self.store.tenant_transaction(tenant_a.id):
            evidence = self.store.evidence_for_reference(tenant_a.id, move.id)
        self.assertEqual(evidence.evidence_type, "STOCK_MOVEMENT")
        with self.store.tenant_transaction(tenant_b.id):
            row = self.store.connection.execute(
                "SELECT count(*) AS n FROM stock_movement"
            ).fetchone()
            self.assertEqual(row["n"], 0)
            self.assertIsNone(self.application.stock.get(tenant_b.id, move.id))
        with self.assertRaises(psycopg.errors.InsufficientPrivilege):
            with self.store.tenant_transaction(tenant_b.id):
                self.application.stock.create(self.item(tenant_a.id, prop_a.id))

    def test_correction_keeps_property_and_allows_one_successor(self) -> None:
        tenant, prop = self.farm("Stock PG correction tenant")
        other = self.application.create_property(
            tenant.id,
            "Outro sítio",
            self.polygon(-47.1, -24.12, -47.08, -24.1),
            "EPSG:4326",
            boundary_source="synthetic integration boundary",
            classification=DataClassification.MANUAL_CONFIRMED,
        )
        with self.store.tenant_transaction(tenant.id):
            first = self.application.stock.create(self.item(tenant.id, prop.id))
            self.application.stock.create(
                self.item(tenant.id, prop.id, supersedes_id=first.id)
            )
        with self.assertRaises(psycopg.errors.UniqueViolation):
            with self.store.tenant_transaction(tenant.id):
                self.application.stock.create(
                    self.item(tenant.id, prop.id, supersedes_id=first.id)
                )
        with self.assertRaises(psycopg.errors.ForeignKeyViolation):
            with self.store.tenant_transaction(tenant.id):
                self.application.stock.create(
                    self.item(tenant.id, other.id, supersedes_id=first.id)
                )

    def test_application_role_cannot_update_or_delete(self) -> None:
        tenant, prop = self.farm("Stock PG append-only tenant")
        move = self.register(tenant, prop)
        for statement in (
            "UPDATE stock_movement SET quantity = 1 WHERE id = %s",
            "DELETE FROM stock_movement WHERE id = %s",
        ):
            with self.subTest(statement=statement):
                with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                    with self.store.tenant_transaction(tenant.id):
                        self.store.connection.execute(statement, (move.id,))
        self.assertEqual(self.application.stock.get(tenant.id, move.id).quantity, 100.0)

    def test_database_constraints(self) -> None:
        tenant, prop = self.farm("Stock PG constraint tenant")
        cases = {
            "zero quantity": {"quantity": 0.0},
            "negative quantity": {"quantity": -1.0},
            "unknown unit": {"unit": "TON"},
            "unknown type": {"movement_type": "MOVE"},
            "blank item": {"item_name": " "},
            "blank counterparty": {"counterparty": " "},
        }
        for label, overrides in cases.items():
            with self.subTest(case=label):
                with self.assertRaises(psycopg.errors.CheckViolation):
                    with self.store.tenant_transaction(tenant.id):
                        self.application.stock.create(
                            self.item(tenant.id, prop.id, **overrides)
                        )

    def test_summary_on_postgres(self) -> None:
        tenant, prop = self.farm("Stock PG summary tenant")
        self.register(tenant, prop, quantity=100)
        self.register(
            tenant, prop, movement_type="OUT", quantity=130, movement_date="2026-10-05"
        )
        summary = self.application.stock_summary(tenant.id, prop.id, as_of="2026-10-20")
        self.assertEqual(summary["items"][0]["balance"], -30.0)
        self.assertTrue(summary["items"][0]["negative_balance"])


if __name__ == "__main__":
    unittest.main()
