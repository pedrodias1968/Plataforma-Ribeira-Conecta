"""Unit and API tests for costs by field: entries, corrections, cost per kg, RBAC."""

from __future__ import annotations

from fastapi.testclient import TestClient

from ribeira_platform.api import create_app
from ribeira_platform.costs import CostConflict, CostValidationError
from ribeira_platform.epistemology import DataClassification
from ribeira_platform.iam import AuthContext, DevelopmentIdentityProvider
from tests.test_fertilization import FertilizationTestBase


class CostTestBase(FertilizationTestBase):
    def cost(self, field_id: str | None = None, **overrides):
        values = {
            "entry_date": "2026-10-05",
            "category": "LABOR",
            "description": "Diárias de colheita",
            "amount_brl": 500,
        }
        values.update(overrides)
        return self.app.register_cost_entry(
            self.tenant.id,
            self.property.id,
            field_id=field_id,
            recorded_by="Gerente",
            source_reference="caderno de custos",
            actor="manager@test.local",
            **values,
        )

    def summary_by_field(self, **filters):
        summary = self.app.cost_summary(self.tenant.id, self.property.id, **filters)
        return summary, {x["field_id"]: x for x in summary["fields"]}


class CostEntryTest(CostTestBase):
    def test_register_with_and_without_field_and_evidence(self) -> None:
        allocated = self.cost(self.field_a.id)
        wide = self.cost(None, category="FUEL", description="Diesel")
        self.assertEqual(allocated.field_id, self.field_a.id)
        self.assertIsNone(wide.field_id)
        self.assertEqual(allocated.classification, DataClassification.MANUAL_CONFIRMED)
        evidence = self.store.evidence_for_reference(self.tenant.id, allocated.id)
        self.assertEqual(evidence.evidence_type, "COST_ENTRY")
        listed = self.app.list_cost_entries(self.tenant.id, self.property.id)
        self.assertEqual({x.id for x in listed}, {allocated.id, wide.id})

    def test_zero_is_valid_and_amount_is_rounded_to_cents(self) -> None:
        self.assertEqual(self.cost(None, amount_brl=0).amount_brl, 0.0)
        self.assertEqual(self.cost(None, amount_brl=10.456).amount_brl, 10.46)

    def test_invalid_entries_are_rejected(self) -> None:
        cases = {
            "fertilizer category": {"category": "FERTILIZER"},
            "unknown category": {"category": "MAGIC"},
            "negative amount": {"amount_brl": -1},
            "nan amount": {"amount_brl": float("nan")},
            "OTHER without notes": {"category": "OTHER"},
            "blank description": {"description": " "},
            "future date": {"entry_date": "2999-01-01"},
            "derived classification": {"classification": DataClassification.CALCULATED},
        }
        for label, overrides in cases.items():
            with self.subTest(case=label):
                with self.assertRaises(ValueError):
                    self.cost(self.field_a.id, **overrides)
        self.assertEqual(
            self.app.list_cost_entries(self.tenant.id, self.property.id), []
        )

    def test_field_and_property_checks(self) -> None:
        with self.assertRaises(LookupError):
            self.cost("missing-field")
        other = self.app.create_tenant("Outro tenant")
        with self.assertRaises(LookupError):
            self.app.list_cost_entries(other.id, self.property.id)

    def test_filters(self) -> None:
        a = self.cost(self.field_a.id, entry_date="2026-10-01")
        b = self.cost(self.field_b.id, entry_date="2026-10-20")
        only_a = self.app.list_cost_entries(
            self.tenant.id, self.property.id, field_id=self.field_a.id
        )
        self.assertEqual([x.id for x in only_a], [a.id])
        window = self.app.list_cost_entries(
            self.tenant.id, self.property.id, date_from="2026-10-10"
        )
        self.assertEqual([x.id for x in window], [b.id])


class CostCorrectionTest(CostTestBase):
    def correct(self, entry_id: str, **overrides):
        values = {
            "correction_reason": "valor digitado errado",
            "entry_date": "2026-10-05",
            "category": "LABOR",
            "description": "Diárias de colheita",
            "amount_brl": 450,
            "recorded_by": "Gerente",
            "source_reference": "caderno de custos",
        }
        values.update(overrides)
        return self.app.correct_cost_entry(self.tenant.id, entry_id, **values)

    def test_correction_keeps_field_and_history(self) -> None:
        original = self.cost(self.field_a.id)
        fixed = self.correct(original.id)
        self.assertEqual(fixed.supersedes_id, original.id)
        self.assertEqual(fixed.field_id, self.field_a.id)
        current = self.app.list_cost_entries(self.tenant.id, self.property.id)
        self.assertEqual([x.id for x in current], [fixed.id])
        history = self.app.list_cost_entries(
            self.tenant.id, self.property.id, include_superseded=True
        )
        self.assertEqual(len(history), 2)

    def test_property_wide_cost_stays_property_wide_when_corrected(self) -> None:
        original = self.cost(None)
        self.assertIsNone(self.correct(original.id).field_id)

    def test_second_correction_conflicts_and_reason_is_required(self) -> None:
        original = self.cost(self.field_a.id)
        with self.assertRaises(ValueError):
            self.correct(original.id, correction_reason=" ")
        self.correct(original.id)
        with self.assertRaises(CostConflict):
            self.correct(original.id)
        with self.assertRaises(LookupError):
            self.correct("does-not-exist")


class CostSummaryTest(CostTestBase):
    def test_cost_per_kg_when_cost_and_weight_are_complete(self) -> None:
        self.cost(self.field_a.id, amount_brl=300)
        self.apply(self.field_a.id, cost_brl=100)
        self.record(self.field_a.id, weight_kg=200, boxes_packed=10)
        self.record(self.field_a.id, "2026-10-16", weight_kg=200)
        _, by_field = self.summary_by_field()
        block = by_field[self.field_a.id]
        self.assertEqual(block["manual_cost"]["total"], 300.0)
        self.assertEqual(block["fertilization_cost"]["total"], 100.0)
        self.assertEqual(block["allocated_cost_total"], 400.0)
        self.assertEqual(block["harvest"]["weight_kg_total"], 400.0)
        self.assertEqual(block["cost_per_kg"], 1.0)
        self.assertIsNone(block["cost_per_kg_unavailable_reason"])
        self.assertFalse(block["cost_is_partial"])

    def test_cost_per_kg_is_withheld_when_a_harvest_record_has_no_weight(self) -> None:
        self.cost(self.field_a.id, amount_brl=300)
        self.record(self.field_a.id, weight_kg=200)
        self.record(self.field_a.id, "2026-10-16")  # boxes only, weight unknown
        _, by_field = self.summary_by_field()
        block = by_field[self.field_a.id]
        self.assertIsNone(block["cost_per_kg"])
        self.assertEqual(
            block["cost_per_kg_unavailable_reason"], "SOME_HARVEST_WITHOUT_WEIGHT"
        )

    def test_unknown_is_not_zero(self) -> None:
        self.record(self.field_a.id, weight_kg=100)
        self.cost(self.field_b.id, amount_brl=80)
        _, by_field = self.summary_by_field()
        no_cost = by_field[self.field_a.id]
        self.assertIsNone(no_cost["allocated_cost_total"])
        self.assertIsNone(no_cost["cost_per_kg"])
        self.assertEqual(no_cost["cost_per_kg_unavailable_reason"], "NO_COST_DATA")
        no_weight = by_field[self.field_b.id]
        self.assertEqual(no_weight["allocated_cost_total"], 80.0)
        self.assertIsNone(no_weight["cost_per_kg"])
        self.assertEqual(no_weight["cost_per_kg_unavailable_reason"], "NO_WEIGHT_DATA")

    def test_partial_fertilization_cost_is_flagged(self) -> None:
        self.apply(self.field_a.id, cost_brl=100)
        self.apply(self.field_a.id, product_name="Calcário", cost_brl=None)
        _, by_field = self.summary_by_field()
        block = by_field[self.field_a.id]
        self.assertTrue(block["cost_is_partial"])
        self.assertEqual(block["fertilization_cost"]["records_without_value"], 1)
        self.assertEqual(block["allocated_cost_total"], 100.0)

    def test_property_wide_costs_are_not_spread_over_fields(self) -> None:
        self.cost(None, amount_brl=1000, category="MAINTENANCE", description="Trator")
        summary, by_field = self.summary_by_field()
        self.assertEqual(summary["unallocated_cost"]["total"], 1000.0)
        for block in by_field.values():
            self.assertIsNone(block["allocated_cost_total"])

    def test_only_current_entries_count_and_period_filters_apply(self) -> None:
        old = self.cost(self.field_a.id, amount_brl=999)
        self.app.correct_cost_entry(
            self.tenant.id,
            old.id,
            correction_reason="valor errado",
            entry_date="2026-10-05",
            category="LABOR",
            description="Diárias",
            amount_brl=90,
            recorded_by="Gerente",
            source_reference="caderno",
        )
        self.cost(self.field_a.id, amount_brl=7, entry_date="2026-08-01")
        _, by_field = self.summary_by_field(date_from="2026-10-01")
        self.assertEqual(by_field[self.field_a.id]["manual_cost"]["total"], 90.0)
        summary, single = self.summary_by_field(field_id=self.field_b.id)
        self.assertEqual(list(single), [self.field_b.id])
        with self.assertRaises(LookupError):
            self.app.cost_summary(self.tenant.id, self.property.id, field_id="nope")
        self.assertTrue(summary["limitations"])
        self.assertEqual(summary["classification"], "CALCULATED")


class CostApiTest(CostTestBase):
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
            "field_id": self.field_a.id,
            "entry_date": "2026-10-05",
            "category": "LABOR",
            "description": "Diárias de colheita",
            "amount_brl": 500,
            "recorded_by": "Gerente",
            "source_reference": "caderno de custos",
        }
        values.update(overrides)
        return values

    def test_only_management_roles_access_costs(self) -> None:
        url = f"{self.base()}/properties/{self.property.id}/cost-entries"
        summary_url = f"{self.base()}/properties/{self.property.id}/cost-summary"
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
        self.assertEqual(analyst.get(summary_url, headers=h_an).status_code, 200)
        self.assertEqual(
            analyst.post(url, headers=h_an, json=self.payload()).status_code, 403
        )
        created = manager.post(url, headers=h_mg, json=self.payload())
        self.assertEqual(created.status_code, 201)
        self.assertIsNotNone(created.json()["evidence_id"])
        wide = manager.post(url, headers=h_mg, json=self.payload(field_id=None))
        self.assertEqual(wide.status_code, 201)
        self.assertIsNone(wide.json()["field_id"])

    def test_validation_errors(self) -> None:
        url = f"{self.base()}/properties/{self.property.id}/cost-entries"
        client, h = self.client("MANAGER")
        for label, overrides in {
            "fertilizer category": {"category": "FERTILIZER"},
            "negative amount": {"amount_brl": -1},
            "future date": {"entry_date": "2999-01-01"},
            "derived classification": {"classification": "CALCULATED"},
            "extra field": {"unexpected": "x"},
        }.items():
            with self.subTest(case=label):
                status = client.post(
                    url, headers=h, json=self.payload(**overrides)
                ).status_code
                self.assertIn(status, (400, 422))
        self.assertEqual(
            client.post(
                url, headers=h, json=self.payload(field_id="missing")
            ).status_code,
            404,
        )

    def test_correction_conflict_and_summary(self) -> None:
        url = f"{self.base()}/properties/{self.property.id}/cost-entries"
        manager, h = self.client("MANAGER")
        original = manager.post(url, headers=h, json=self.payload()).json()
        body = self.payload(amount_brl=450)
        body.pop("field_id")
        body["correction_reason"] = "valor errado"
        corr = f"{self.base()}/cost-entries/{original['id']}/corrections"
        first = manager.post(corr, headers=h, json=body)
        self.assertEqual(first.status_code, 201)
        self.assertEqual(first.json()["field_id"], self.field_a.id)
        second = manager.post(corr, headers=h, json=body)
        self.assertEqual(second.status_code, 409)
        self.assertEqual(second.json()["error"]["code"], "COST_CONFLICT")
        summary = manager.get(
            f"{self.base()}/properties/{self.property.id}/cost-summary", headers=h
        ).json()
        block = {x["field_id"]: x for x in summary["fields"]}[self.field_a.id]
        self.assertEqual(block["manual_cost"]["total"], 450.0)
        self.assertIsNone(block["cost_per_kg"])

    def test_error_type(self) -> None:
        self.assertTrue(issubclass(CostValidationError, ValueError))
