"""PostgreSQL/RLS coverage for sales and payments: guards, append-only, evidence, isolation."""

from __future__ import annotations

import os
import unittest
from datetime import date

import psycopg
from shapely.geometry import Polygon, mapping

from ribeira_platform.epistemology import DataClassification
from ribeira_platform.models import new_id, now_utc
from ribeira_platform.postgres import PostgresStore
from ribeira_platform.sales import PaymentRecord, SaleRecord
from ribeira_platform.service import RibeiraApplication


DATABASE_URL = os.getenv("RIBEIRA_TEST_DATABASE_URL")


@unittest.skipUnless(DATABASE_URL, "RIBEIRA_TEST_DATABASE_URL is required")
class SalesPostgresTests(unittest.TestCase):
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

    def farm(self, tenant_name: str, boundary=(-47.0, -24.02, -46.98, -24.0)):
        tenant = self.application.create_tenant(tenant_name)
        prop = self.application.create_property(
            tenant.id,
            "Fazenda Vendas",
            self.polygon(*boundary),
            "EPSG:4326",
            boundary_source="synthetic integration boundary",
            classification=DataClassification.MANUAL_CONFIRMED,
        )
        return tenant, prop

    def sale_item(self, tenant_id, property_id, **overrides) -> SaleRecord:
        values = {
            "id": new_id(),
            "tenant_id": tenant_id,
            "property_id": property_id,
            "sale_date": "2026-10-01",
            "buyer_name": "Silva",
            "quantity": 100.0,
            "quantity_unit": "BOXES",
            "unit_price_brl": None,
            "price_unit": None,
            "total_amount_brl": 3000.0,
            "expected_payment_date": "2026-10-15",
            "recorded_by": "Gerente",
            "source_reference": "caderno",
            "classification": DataClassification.MANUAL_CONFIRMED,
            "notes": None,
            "supersedes_id": None,
            "created_at": now_utc(),
        }
        values.update(overrides)
        return SaleRecord(**values)

    def payment_item(
        self, tenant_id, property_id, sale_id, **overrides
    ) -> PaymentRecord:
        values = {
            "id": new_id(),
            "tenant_id": tenant_id,
            "property_id": property_id,
            "sale_id": sale_id,
            "payment_date": "2026-10-10",
            "amount_brl": 1000.0,
            "method": None,
            "recorded_by": "Gerente",
            "source_reference": "extrato",
            "classification": DataClassification.MANUAL_CONFIRMED,
            "notes": None,
            "supersedes_id": None,
            "created_at": now_utc(),
        }
        values.update(overrides)
        return PaymentRecord(**values)

    def register(self, tenant, prop, **overrides):
        values = {
            "sale_date": "2026-10-01",
            "buyer_name": "Silva",
            "quantity": 100,
            "quantity_unit": "BOXES",
            "total_amount_brl": 3000,
            "expected_payment_date": "2026-10-15",
        }
        values.update(overrides)
        return self.application.register_sale(
            tenant.id,
            prop.id,
            recorded_by="Gerente",
            source_reference="caderno",
            **values,
        )

    def test_sale_payment_evidence_and_tenant_isolation(self) -> None:
        tenant_a, prop_a = self.farm("Sales PG tenant A")
        tenant_b, _ = self.farm("Sales PG tenant B")
        sale = self.register(tenant_a, prop_a)
        payment = self.application.register_payment(
            tenant_a.id,
            sale.id,
            payment_date="2026-10-10",
            amount_brl=1000,
            recorded_by="Gerente",
            source_reference="extrato",
        )
        with self.store.tenant_transaction(tenant_a.id):
            sale_ev = self.store.evidence_for_reference(tenant_a.id, sale.id)
            pay_ev = self.store.evidence_for_reference(tenant_a.id, payment.id)
        self.assertEqual(sale_ev.evidence_type, "SALE_RECORD")
        self.assertEqual(pay_ev.evidence_type, "PAYMENT_RECORD")

        with self.store.tenant_transaction(tenant_b.id):
            row = self.store.connection.execute(
                "SELECT (SELECT count(*) FROM sale_record) AS sales,"
                " (SELECT count(*) FROM payment_record) AS payments"
            ).fetchone()
            self.assertEqual(row["sales"], 0)
            self.assertEqual(row["payments"], 0)
            self.assertIsNone(self.application.sales.get_sale(tenant_b.id, sale.id))
        with self.assertRaises(psycopg.errors.InsufficientPrivilege):
            with self.store.tenant_transaction(tenant_b.id):
                self.application.sales.create_sale(
                    self.sale_item(tenant_a.id, prop_a.id)
                )
        with self.assertRaises(LookupError):
            self.application.register_payment(
                tenant_b.id,
                sale.id,
                payment_date="2026-10-10",
                amount_brl=1,
                recorded_by="x",
                source_reference="x",
            )

    def test_payment_must_belong_to_the_same_property_as_its_sale(self) -> None:
        tenant, prop = self.farm("Sales PG guard tenant")
        other = self.application.create_property(
            tenant.id,
            "Outro sítio",
            self.polygon(-47.1, -24.12, -47.08, -24.1),
            "EPSG:4326",
            boundary_source="synthetic integration boundary",
            classification=DataClassification.MANUAL_CONFIRMED,
        )
        sale = self.register(tenant, prop)
        with self.assertRaises(psycopg.errors.ForeignKeyViolation):
            with self.store.tenant_transaction(tenant.id):
                self.application.sales.create_payment(
                    self.payment_item(tenant.id, other.id, sale.id)
                )

    def test_corrections_keep_property_and_sale_and_allow_one_successor(self) -> None:
        tenant, prop = self.farm("Sales PG correction tenant")
        other = self.application.create_property(
            tenant.id,
            "Outro sítio",
            self.polygon(-47.1, -24.12, -47.08, -24.1),
            "EPSG:4326",
            boundary_source="synthetic integration boundary",
            classification=DataClassification.MANUAL_CONFIRMED,
        )
        with self.store.tenant_transaction(tenant.id):
            sale = self.application.sales.create_sale(
                self.sale_item(tenant.id, prop.id)
            )
            other_sale = self.application.sales.create_sale(
                self.sale_item(tenant.id, prop.id)
            )
            fixed = self.application.sales.create_sale(
                self.sale_item(tenant.id, prop.id, supersedes_id=sale.id)
            )
            payment = self.application.sales.create_payment(
                self.payment_item(tenant.id, prop.id, sale.id)
            )
        self.assertEqual(fixed.supersedes_id, sale.id)
        with self.assertRaises(psycopg.errors.UniqueViolation):
            with self.store.tenant_transaction(tenant.id):
                self.application.sales.create_sale(
                    self.sale_item(tenant.id, prop.id, supersedes_id=sale.id)
                )
        with self.assertRaises(psycopg.errors.ForeignKeyViolation):
            with self.store.tenant_transaction(tenant.id):
                self.application.sales.create_sale(
                    self.sale_item(tenant.id, other.id, supersedes_id=other_sale.id)
                )
        with self.store.tenant_transaction(tenant.id):
            self.application.sales.create_payment(
                self.payment_item(tenant.id, prop.id, sale.id, supersedes_id=payment.id)
            )
        with self.assertRaises(psycopg.errors.UniqueViolation):
            with self.store.tenant_transaction(tenant.id):
                self.application.sales.create_payment(
                    self.payment_item(
                        tenant.id, prop.id, sale.id, supersedes_id=payment.id
                    )
                )
        # A payment correction cannot move the payment to another sale.
        with self.assertRaises(psycopg.errors.ForeignKeyViolation):
            with self.store.tenant_transaction(tenant.id):
                self.application.sales.create_payment(
                    self.payment_item(
                        tenant.id, prop.id, other_sale.id, supersedes_id=payment.id
                    )
                )

    def test_application_role_cannot_update_or_delete(self) -> None:
        tenant, prop = self.farm("Sales PG append-only tenant")
        sale = self.register(tenant, prop)
        payment = self.application.register_payment(
            tenant.id,
            sale.id,
            payment_date="2026-10-10",
            amount_brl=500,
            recorded_by="Gerente",
            source_reference="extrato",
        )
        for statement, row_id in (
            ("UPDATE sale_record SET total_amount_brl = 1 WHERE id = %s", sale.id),
            ("DELETE FROM sale_record WHERE id = %s", sale.id),
            ("UPDATE payment_record SET amount_brl = 1 WHERE id = %s", payment.id),
            ("DELETE FROM payment_record WHERE id = %s", payment.id),
        ):
            with self.subTest(statement=statement):
                with self.assertRaises(psycopg.errors.InsufficientPrivilege):
                    with self.store.tenant_transaction(tenant.id):
                        self.store.connection.execute(statement, (row_id,))
        stored = self.application.sales.get_sale(tenant.id, sale.id)
        self.assertEqual(stored.total_amount_brl, 3000.0)

    def test_database_constraints(self) -> None:
        tenant, prop = self.farm("Sales PG constraint tenant")
        sale_cases = {
            "no quantity and no total": {
                "quantity": None,
                "quantity_unit": None,
                "total_amount_brl": None,
            },
            "quantity without unit": {"quantity_unit": None},
            "price without unit": {"unit_price_brl": 30.0},
            "unknown unit": {"quantity_unit": "TON"},
            "negative total": {"total_amount_brl": -1.0},
            "due before sale": {"expected_payment_date": "2026-09-01"},
            "blank buyer": {"buyer_name": " "},
        }
        for label, overrides in sale_cases.items():
            with self.subTest(sale=label):
                with self.assertRaises(psycopg.errors.CheckViolation):
                    with self.store.tenant_transaction(tenant.id):
                        self.application.sales.create_sale(
                            self.sale_item(tenant.id, prop.id, **overrides)
                        )
        sale = self.register(tenant, prop)
        for label, overrides in {
            "zero amount": {"amount_brl": 0.0},
            "negative amount": {"amount_brl": -1.0},
            "blank method": {"method": " "},
        }.items():
            with self.subTest(payment=label):
                with self.assertRaises(psycopg.errors.CheckViolation):
                    with self.store.tenant_transaction(tenant.id):
                        self.application.sales.create_payment(
                            self.payment_item(tenant.id, prop.id, sale.id, **overrides)
                        )

    def test_summary_follows_correction_chain_on_postgres(self) -> None:
        tenant, prop = self.farm("Sales PG summary tenant")
        sale = self.register(tenant, prop, total_amount_brl=3000)
        self.application.register_payment(
            tenant.id,
            sale.id,
            payment_date="2026-10-10",
            amount_brl=1000,
            recorded_by="Gerente",
            source_reference="extrato",
        )
        fixed = self.application.correct_sale(
            tenant.id,
            sale.id,
            correction_reason="total errado",
            sale_date="2026-10-01",
            buyer_name="Silva",
            quantity=100,
            quantity_unit="BOXES",
            total_amount_brl=2800,
            expected_payment_date="2026-10-15",
            recorded_by="Gerente",
            source_reference="caderno",
        )
        unknown = self.register(tenant, prop, total_amount_brl=None, buyer_name="Costa")
        summary = self.application.sales_summary(tenant.id, prop.id, as_of="2026-10-20")
        rows = {x["sale_id"]: x for x in summary["sales"]}
        self.assertEqual(set(rows), {fixed.id, unknown.id})
        self.assertEqual(rows[fixed.id]["received_brl"], 1000.0)
        self.assertEqual(rows[fixed.id]["balance_brl"], 1800.0)
        self.assertTrue(rows[fixed.id]["overdue"])
        self.assertEqual(rows[unknown.id]["status"], "AMOUNT_UNKNOWN")
        self.assertIsNone(rows[unknown.id]["balance_brl"])
        self.assertEqual(summary["outstanding_brl"], 1800.0)
        default_day = self.application.sales_summary(tenant.id, prop.id)
        self.assertEqual(default_day["as_of"], date.today().isoformat())


if __name__ == "__main__":
    unittest.main()
