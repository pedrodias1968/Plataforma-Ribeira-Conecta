"""Unit and API tests for sales and receivables: records, payments, corrections, balances, RBAC."""

from __future__ import annotations

from datetime import date

from fastapi.testclient import TestClient

from ribeira_platform.api import create_app
from ribeira_platform.epistemology import DataClassification
from ribeira_platform.iam import AuthContext, DevelopmentIdentityProvider
from ribeira_platform.sales import SalesConflict
from tests.test_harvest import HarvestTestBase

AS_OF = "2026-10-20"


class SalesTestBase(HarvestTestBase):
    def sale(self, **overrides):
        values = {
            "sale_date": "2026-10-01",
            "buyer_name": "Atravessador Silva",
            "quantity": 100,
            "quantity_unit": "BOXES",
            "unit_price_brl": 30,
            "price_unit": "BOXES",
            "total_amount_brl": 3000,
            "expected_payment_date": "2026-10-15",
        }
        values.update(overrides)
        return self.app.register_sale(
            self.tenant.id,
            self.property.id,
            recorded_by="Gerente",
            source_reference="caderno de vendas",
            actor="manager@test.local",
            **values,
        )

    def pay(self, sale_id: str, amount: float = 1000, **overrides):
        values = {"payment_date": "2026-10-10", "amount_brl": amount}
        values.update(overrides)
        return self.app.register_payment(
            self.tenant.id,
            sale_id,
            recorded_by="Gerente",
            source_reference="extrato",
            actor="manager@test.local",
            **values,
        )

    def summary(self, **filters):
        filters.setdefault("as_of", AS_OF)
        return self.app.sales_summary(self.tenant.id, self.property.id, **filters)

    def one(self, summary, sale_id):
        return {x["sale_id"]: x for x in summary["sales"]}[sale_id]


class SaleRecordTest(SalesTestBase):
    def test_absent_values_stay_unknown_and_evidence_is_created(self) -> None:
        item = self.sale(
            unit_price_brl=None,
            price_unit=None,
            total_amount_brl=None,
            expected_payment_date=None,
        )
        self.assertIsNone(item.total_amount_brl)
        self.assertIsNone(item.unit_price_brl)
        self.assertIsNone(item.expected_payment_date)
        self.assertEqual(item.classification, DataClassification.MANUAL_CONFIRMED)
        evidence = self.store.evidence_for_reference(self.tenant.id, item.id)
        self.assertEqual(evidence.evidence_type, "SALE_RECORD")

    def test_total_is_never_computed_from_quantity_and_price(self) -> None:
        item = self.sale(total_amount_brl=None)
        self.assertIsNone(item.total_amount_brl)

    def test_total_only_sale_is_valid_and_zero_is_valid(self) -> None:
        item = self.sale(quantity=None, quantity_unit=None, total_amount_brl=0)
        self.assertEqual(item.total_amount_brl, 0.0)

    def test_invalid_sales_are_rejected(self) -> None:
        cases = {
            "no quantity and no total": {
                "quantity": None,
                "quantity_unit": None,
                "total_amount_brl": None,
            },
            "quantity without unit": {"quantity_unit": None},
            "price without unit": {"price_unit": None},
            "unknown unit": {"quantity_unit": "TON"},
            "negative quantity": {"quantity": -1},
            "negative total": {"total_amount_brl": -1},
            "nan price": {"unit_price_brl": float("nan")},
            "blank buyer": {"buyer_name": "  "},
            "future sale date": {"sale_date": "2999-01-01"},
            "due before sale": {"expected_payment_date": "2026-09-01"},
            "bad due date": {"expected_payment_date": "15/10/2026"},
            "derived classification": {"classification": DataClassification.CALCULATED},
        }
        for label, overrides in cases.items():
            with self.subTest(case=label):
                with self.assertRaises(ValueError):
                    self.sale(**overrides)
        self.assertEqual(self.app.list_sales(self.tenant.id, self.property.id), [])

    def test_property_and_tenant_checks(self) -> None:
        other = self.app.create_tenant("Outro tenant")
        with self.assertRaises(LookupError):
            self.app.list_sales(other.id, self.property.id)


class SaleCorrectionTest(SalesTestBase):
    def correct(self, sale_id: str, **overrides):
        values = {
            "correction_reason": "total digitado errado",
            "sale_date": "2026-10-01",
            "buyer_name": "Atravessador Silva",
            "quantity": 100,
            "quantity_unit": "BOXES",
            "total_amount_brl": 2800,
            "recorded_by": "Gerente",
            "source_reference": "caderno de vendas",
        }
        values.update(overrides)
        return self.app.correct_sale(self.tenant.id, sale_id, **values)

    def test_correction_keeps_history_and_payments_follow_the_chain(self) -> None:
        original = self.sale()
        self.pay(original.id, 1000)
        fixed = self.correct(original.id)
        self.assertEqual(fixed.supersedes_id, original.id)
        current = self.app.list_sales(self.tenant.id, self.property.id)
        self.assertEqual([x.id for x in current], [fixed.id])
        history = self.app.list_sales(
            self.tenant.id, self.property.id, include_superseded=True
        )
        self.assertEqual(len(history), 2)
        row = self.one(self.summary(), fixed.id)
        self.assertEqual(row["total_amount_brl"], 2800.0)
        self.assertEqual(row["received_brl"], 1000.0)
        self.assertEqual(row["balance_brl"], 1800.0)

    def test_conflicts_and_errors(self) -> None:
        original = self.sale()
        with self.assertRaises(ValueError):
            self.correct(original.id, correction_reason=" ")
        self.correct(original.id)
        with self.assertRaises(SalesConflict):
            self.correct(original.id)
        with self.assertRaises(LookupError):
            self.correct("does-not-exist")

    def test_payment_cannot_target_a_superseded_sale(self) -> None:
        original = self.sale()
        fixed = self.correct(original.id)
        with self.assertRaises(SalesConflict):
            self.pay(original.id)
        self.pay(fixed.id)


class PaymentTest(SalesTestBase):
    def test_register_with_evidence_and_validations(self) -> None:
        sale = self.sale()
        payment = self.pay(sale.id, 500, method="PIX")
        self.assertEqual(payment.amount_brl, 500.0)
        self.assertEqual(payment.method, "PIX")
        evidence = self.store.evidence_for_reference(self.tenant.id, payment.id)
        self.assertEqual(evidence.evidence_type, "PAYMENT_RECORD")
        cases = {
            "zero amount": {"amount_brl": 0},
            "negative amount": {"amount_brl": -5},
            "nan amount": {"amount_brl": float("nan")},
            "future date": {"payment_date": "2999-01-01"},
            "before sale": {"payment_date": "2026-09-01"},
            "derived classification": {"classification": DataClassification.CALCULATED},
        }
        for label, overrides in cases.items():
            with self.subTest(case=label):
                with self.assertRaises(ValueError):
                    self.pay(sale.id, **overrides)
        with self.assertRaises(LookupError):
            self.pay("missing-sale")
        self.assertEqual(
            len(self.app.list_payments(self.tenant.id, self.property.id)), 1
        )

    def test_payment_correction_keeps_sale_and_conflicts_once(self) -> None:
        sale = self.sale()
        payment = self.pay(sale.id, 500)
        fixed = self.app.correct_payment(
            self.tenant.id,
            payment.id,
            correction_reason="valor errado",
            payment_date="2026-10-10",
            amount_brl=450,
            recorded_by="Gerente",
            source_reference="extrato",
        )
        self.assertEqual(fixed.sale_id, sale.id)
        self.assertEqual(fixed.supersedes_id, payment.id)
        with self.assertRaises(SalesConflict):
            self.app.correct_payment(
                self.tenant.id,
                payment.id,
                correction_reason="de novo",
                payment_date="2026-10-10",
                amount_brl=1,
                recorded_by="Gerente",
                source_reference="extrato",
            )
        self.assertEqual(self.one(self.summary(), sale.id)["received_brl"], 450.0)
        current = self.app.list_payments(self.tenant.id, self.property.id)
        self.assertEqual([x.id for x in current], [fixed.id])


class SalesSummaryTest(SalesTestBase):
    def test_statuses_balance_and_overdue(self) -> None:
        open_sale = self.sale(buyer_name="A", total_amount_brl=1000)
        partial = self.sale(buyer_name="B", total_amount_brl=1000)
        paid = self.sale(buyer_name="C", total_amount_brl=1000)
        over = self.sale(buyer_name="D", total_amount_brl=1000)
        self.pay(partial.id, 400)
        self.pay(paid.id, 1000)
        self.pay(over.id, 1200)
        summary = self.summary()
        self.assertEqual(self.one(summary, open_sale.id)["status"], "OPEN")
        self.assertEqual(self.one(summary, partial.id)["status"], "PARTIAL")
        self.assertEqual(self.one(summary, paid.id)["status"], "PAID")
        self.assertEqual(self.one(summary, over.id)["status"], "OVERPAID")
        self.assertEqual(self.one(summary, partial.id)["balance_brl"], 600.0)
        self.assertTrue(self.one(summary, open_sale.id)["overdue"])
        self.assertFalse(self.one(summary, paid.id)["overdue"])
        self.assertEqual(summary["total_known_brl"], 4000.0)
        self.assertEqual(summary["outstanding_brl"], 1600.0)
        self.assertEqual(summary["overdue_brl"], 1600.0)

    def test_not_overdue_before_the_expected_date_or_without_one(self) -> None:
        later = self.sale(total_amount_brl=500, expected_payment_date="2026-10-30")
        no_date = self.sale(total_amount_brl=500, expected_payment_date=None)
        summary = self.summary()
        self.assertFalse(self.one(summary, later.id)["overdue"])
        self.assertFalse(self.one(summary, no_date.id)["overdue"])
        self.assertEqual(summary["overdue_brl"], 0.0)
        self.assertEqual(summary["outstanding_brl"], 1000.0)

    def test_unknown_total_has_no_balance_and_is_not_zero(self) -> None:
        unknown = self.sale(total_amount_brl=None)
        self.pay(unknown.id, 300)
        summary = self.summary()
        row = self.one(summary, unknown.id)
        self.assertEqual(row["status"], "AMOUNT_UNKNOWN")
        self.assertIsNone(row["balance_brl"])
        self.assertFalse(row["overdue"])
        self.assertIsNone(summary["total_known_brl"])
        self.assertIsNone(summary["outstanding_brl"])
        self.assertEqual(summary["sales_without_total"], 1)
        self.assertEqual(summary["received_on_unknown_total_brl"], 300.0)
        self.assertEqual(summary["received_on_known_total_brl"], 0.0)

    def test_units_are_never_combined_and_latest_price_per_unit(self) -> None:
        self.sale(quantity=100, quantity_unit="BOXES", sale_date="2026-10-01")
        self.sale(
            quantity=500,
            quantity_unit="KG",
            unit_price_brl=2,
            price_unit="KG",
            sale_date="2026-10-05",
        )
        self.sale(
            quantity=50,
            quantity_unit="BOXES",
            unit_price_brl=33,
            price_unit="BOXES",
            sale_date="2026-10-08",
        )
        summary = self.summary()
        self.assertEqual(summary["quantity_by_unit"], {"BOXES": 150.0, "KG": 500.0})
        self.assertEqual(
            summary["latest_price_by_unit"]["BOXES"]["unit_price_brl"], 33.0
        )
        self.assertEqual(
            summary["latest_price_by_unit"]["BOXES"]["sale_date"], "2026-10-08"
        )
        self.assertEqual(summary["latest_price_by_unit"]["KG"]["unit_price_brl"], 2.0)

    def test_by_buyer_period_filter_and_current_only(self) -> None:
        self.sale(buyer_name="Silva", total_amount_brl=1000)
        self.sale(buyer_name="silva", total_amount_brl=500)
        self.sale(
            buyer_name="Costa",
            total_amount_brl=200,
            sale_date="2026-09-01",
            expected_payment_date=None,
        )
        summary = self.summary(date_from="2026-10-01")
        self.assertEqual(summary["sale_count"], 2)
        self.assertEqual(len(summary["by_buyer"]), 1)
        self.assertEqual(summary["by_buyer"][0]["outstanding_brl"], 1500.0)
        everything = self.summary()
        self.assertEqual(everything["sale_count"], 3)
        self.assertEqual(summary["classification"], "CALCULATED")
        self.assertTrue(summary["limitations"])

    def test_empty_summary_has_no_invented_totals(self) -> None:
        summary = self.summary()
        self.assertEqual(summary["sale_count"], 0)
        self.assertIsNone(summary["total_known_brl"])
        self.assertIsNone(summary["outstanding_brl"])

    def test_as_of_defaults_to_today(self) -> None:
        summary = self.app.sales_summary(self.tenant.id, self.property.id)
        self.assertEqual(summary["as_of"], date.today().isoformat())


class SalesApiTest(SalesTestBase):
    def client(self, role: str) -> tuple[TestClient, dict[str, str]]:
        token = f"{role.lower()}-token"
        client = TestClient(
            create_app(
                self.app,
                DevelopmentIdentityProvider(
                    token,
                    AuthContext(
                        f"{role.lower()}-user",
                        self.tenant.id,
                        roles=frozenset({role}),
                    ),
                ),
            )
        )
        return client, {"Authorization": f"Bearer {token}"}

    def base(self) -> str:
        return f"/v1/tenants/{self.tenant.id}"

    def payload(self, **overrides):
        values = {
            "sale_date": "2026-10-01",
            "buyer_name": "Atravessador Silva",
            "quantity": 100,
            "quantity_unit": "BOXES",
            "total_amount_brl": 3000,
            "expected_payment_date": "2026-10-15",
            "recorded_by": "Gerente",
            "source_reference": "caderno de vendas",
        }
        values.update(overrides)
        return values

    def pay_payload(self, **overrides):
        values = {
            "payment_date": "2026-10-10",
            "amount_brl": 1000,
            "recorded_by": "Gerente",
            "source_reference": "extrato",
        }
        values.update(overrides)
        return values

    def test_only_management_roles_access_sales(self) -> None:
        url = f"{self.base()}/properties/{self.property.id}/sale-records"
        summary_url = f"{self.base()}/properties/{self.property.id}/sales-summary"
        for role in ("OPERATOR", "TECHNICIAN", "AGRONOMIST", "VIEWER", "COMMERCIAL"):
            client, h = self.client(role)
            with self.subTest(role=role):
                self.assertEqual(client.get(url, headers=h).status_code, 403)
                self.assertEqual(client.get(summary_url, headers=h).status_code, 403)
                self.assertEqual(
                    client.post(url, headers=h, json=self.payload()).status_code, 403
                )
        analyst, h_an = self.client("ANALYST")
        manager, h_mg = self.client("MANAGER")
        self.assertEqual(analyst.get(url, headers=h_an).status_code, 200)
        self.assertEqual(
            analyst.post(url, headers=h_an, json=self.payload()).status_code, 403
        )
        created = manager.post(url, headers=h_mg, json=self.payload())
        self.assertEqual(created.status_code, 201)
        self.assertIsNotNone(created.json()["evidence_id"])
        sale_id = created.json()["id"]
        pay_url = f"{self.base()}/sale-records/{sale_id}/payments"
        self.assertEqual(
            analyst.post(pay_url, headers=h_an, json=self.pay_payload()).status_code,
            403,
        )
        self.assertEqual(
            manager.post(pay_url, headers=h_mg, json=self.pay_payload()).status_code,
            201,
        )

    def test_validation_errors(self) -> None:
        url = f"{self.base()}/properties/{self.property.id}/sale-records"
        client, h = self.client("MANAGER")
        for label, overrides in {
            "no quantity and no total": {
                "quantity": None,
                "quantity_unit": None,
                "total_amount_brl": None,
            },
            "quantity without unit": {"quantity_unit": None},
            "negative total": {"total_amount_brl": -1},
            "future date": {"sale_date": "2999-01-01"},
            "due before sale": {"expected_payment_date": "2026-09-01"},
            "derived classification": {"classification": "CALCULATED"},
            "extra field": {"unexpected": "x"},
        }.items():
            with self.subTest(case=label):
                status = client.post(
                    url, headers=h, json=self.payload(**overrides)
                ).status_code
                self.assertIn(status, (400, 422))
        sale = client.post(url, headers=h, json=self.payload()).json()
        pay_url = f"{self.base()}/sale-records/{sale['id']}/payments"
        for overrides in ({"amount_brl": 0}, {"payment_date": "2026-09-01"}):
            self.assertIn(
                client.post(
                    pay_url, headers=h, json=self.pay_payload(**overrides)
                ).status_code,
                (400, 422),
            )
        missing = f"{self.base()}/sale-records/missing/payments"
        self.assertEqual(
            client.post(missing, headers=h, json=self.pay_payload()).status_code, 404
        )

    def test_corrections_conflicts_and_summary(self) -> None:
        url = f"{self.base()}/properties/{self.property.id}/sale-records"
        manager, h = self.client("MANAGER")
        sale = manager.post(url, headers=h, json=self.payload()).json()
        pay = manager.post(
            f"{self.base()}/sale-records/{sale['id']}/payments",
            headers=h,
            json=self.pay_payload(),
        ).json()

        body = self.payload(total_amount_brl=2800)
        body["correction_reason"] = "total errado"
        corr = f"{self.base()}/sale-records/{sale['id']}/corrections"
        fixed = manager.post(corr, headers=h, json=body)
        self.assertEqual(fixed.status_code, 201)
        again = manager.post(corr, headers=h, json=body)
        self.assertEqual(again.status_code, 409)
        self.assertEqual(again.json()["error"]["code"], "SALES_CONFLICT")
        stale = manager.post(
            f"{self.base()}/sale-records/{sale['id']}/payments",
            headers=h,
            json=self.pay_payload(),
        )
        self.assertEqual(stale.status_code, 409)

        pay_body = self.pay_payload(amount_brl=900)
        pay_body["correction_reason"] = "valor errado"
        pay_corr = f"{self.base()}/payment-records/{pay['id']}/corrections"
        self.assertEqual(
            manager.post(pay_corr, headers=h, json=pay_body).status_code, 201
        )
        self.assertEqual(
            manager.post(pay_corr, headers=h, json=pay_body).status_code, 409
        )

        summary = manager.get(
            f"{self.base()}/properties/{self.property.id}/sales-summary?as_of=2026-10-20",
            headers=h,
        ).json()
        row = summary["sales"][0]
        self.assertEqual(row["total_amount_brl"], 2800.0)
        self.assertEqual(row["received_brl"], 900.0)
        self.assertEqual(row["balance_brl"], 1900.0)
        self.assertTrue(row["overdue"])
        payments = manager.get(
            f"{self.base()}/properties/{self.property.id}/payment-records", headers=h
        ).json()["items"]
        self.assertEqual(len(payments), 1)
