"""Unit and API tests for fertilization by field: evidence-first records, corrections, summary, RBAC."""

from __future__ import annotations

from fastapi.testclient import TestClient

from ribeira_platform.api import create_app
from ribeira_platform.epistemology import DataClassification
from ribeira_platform.fertilization import (
    FertilizationConflict,
    FertilizationValidationError,
)
from ribeira_platform.iam import AuthContext, DevelopmentIdentityProvider
from tests.test_harvest import HarvestTestBase


class FertilizationTestBase(HarvestTestBase):
    def apply(self, field_id: str, **overrides):
        values = {
            "application_date": "2026-10-10",
            "product_name": "Ureia",
            "product_type": "MINERAL_FERTILIZER",
            "quantity": 50,
            "quantity_unit": "KG",
            "applied_by": "João",
        }
        values.update(overrides)
        return self.app.register_fertilization_record(
            self.tenant.id,
            self.property.id,
            field_id=field_id,
            recorded_by="Encarregado",
            source_reference="caderno de adubação",
            actor="operator@test.local",
            **values,
        )


class FertilizationRecordTest(FertilizationTestBase):
    def test_absent_values_stay_unknown_and_evidence_is_created(self) -> None:
        item = self.apply(self.field_a.id, quantity=None, quantity_unit=None)
        self.assertIsNone(item.quantity)
        self.assertIsNone(item.quantity_unit)
        self.assertIsNone(item.area_applied_ha)
        self.assertIsNone(item.cost_brl)
        self.assertEqual(item.classification, DataClassification.MANUAL_CONFIRMED)
        evidence = self.store.evidence_for_reference(self.tenant.id, item.id)
        self.assertEqual(evidence.evidence_type, "FERTILIZATION_RECORD")
        stored = self.app.list_fertilization_records(self.tenant.id, self.property.id)
        self.assertIsNone(stored[0].cost_brl)

    def test_zero_is_a_valid_informed_value(self) -> None:
        item = self.apply(self.field_a.id, quantity=0, cost_brl=0)
        self.assertEqual(item.quantity, 0.0)
        self.assertEqual(item.cost_brl, 0.0)

    def test_invalid_values_are_rejected(self) -> None:
        cases = {
            "quantity without unit": {"quantity_unit": None},
            "unit without quantity": {"quantity": None},
            "unknown unit": {"quantity_unit": "TON"},
            "negative quantity": {"quantity": -1},
            "unknown product type": {"product_type": "MAGIC"},
            "OTHER without notes": {"product_type": "OTHER"},
            "zero area": {"area_applied_ha": 0},
            "negative cost": {"cost_brl": -5},
            "nan cost": {"cost_brl": float("nan")},
            "future date": {"application_date": "2999-01-01"},
            "bad date": {"application_date": "10/10/2026"},
            "blank product": {"product_name": "  "},
            "blank applicator": {"applied_by": ""},
            "derived classification": {"classification": DataClassification.CALCULATED},
        }
        for label, overrides in cases.items():
            with self.subTest(case=label):
                with self.assertRaises(ValueError):
                    self.apply(self.field_a.id, **overrides)
        self.assertEqual(
            self.app.list_fertilization_records(self.tenant.id, self.property.id), []
        )

    def test_other_with_notes_is_accepted(self) -> None:
        item = self.apply(
            self.field_a.id, product_type="OTHER", notes="  bokashi caseiro  "
        )
        self.assertEqual(item.notes, "bokashi caseiro")

    def test_field_must_belong_to_property_and_tenant(self) -> None:
        other_tenant = self.app.create_tenant("Outro tenant")
        other_property = self.make_property(other_tenant.id, "Outro sítio")
        other_field = self.make_field(
            other_property.id,
            "Talhão X",
            self.field_a.geometry_geojson,
            tenant_id=other_tenant.id,
        )
        with self.assertRaises(LookupError):
            self.apply(other_field.id)
        with self.assertRaises(LookupError):
            self.app.list_fertilization_records(other_tenant.id, self.property.id)

    def test_filters_and_ordering(self) -> None:
        a = self.apply(self.field_a.id, application_date="2026-10-01")
        b = self.apply(self.field_b.id, application_date="2026-10-12")
        listed = self.app.list_fertilization_records(self.tenant.id, self.property.id)
        self.assertEqual([x.id for x in listed], [b.id, a.id])
        only_a = self.app.list_fertilization_records(
            self.tenant.id, self.property.id, field_id=self.field_a.id
        )
        self.assertEqual([x.id for x in only_a], [a.id])
        window = self.app.list_fertilization_records(
            self.tenant.id,
            self.property.id,
            date_from="2026-10-05",
            date_to="2026-10-31",
        )
        self.assertEqual([x.id for x in window], [b.id])


class FertilizationCorrectionTest(FertilizationTestBase):
    def correct(self, record_id: str, **overrides):
        values = {
            "correction_reason": "dose anotada errada",
            "application_date": "2026-10-10",
            "product_name": "Ureia",
            "product_type": "MINERAL_FERTILIZER",
            "quantity": 40,
            "quantity_unit": "KG",
            "applied_by": "João",
            "recorded_by": "Encarregado",
            "source_reference": "caderno de adubação",
        }
        values.update(overrides)
        return self.app.correct_fertilization_record(
            self.tenant.id, record_id, **values
        )

    def test_correction_supersedes_and_keeps_history(self) -> None:
        original = self.apply(self.field_a.id)
        fixed = self.correct(original.id)
        self.assertEqual(fixed.supersedes_id, original.id)
        self.assertEqual(fixed.field_id, self.field_a.id)
        current = self.app.list_fertilization_records(self.tenant.id, self.property.id)
        self.assertEqual([x.id for x in current], [fixed.id])
        history = self.app.list_fertilization_records(
            self.tenant.id, self.property.id, include_superseded=True
        )
        self.assertEqual({x.id for x in history}, {original.id, fixed.id})
        self.assertEqual(
            self.store.evidence_for_reference(self.tenant.id, fixed.id).evidence_type,
            "FERTILIZATION_RECORD",
        )

    def test_second_correction_of_same_record_conflicts(self) -> None:
        original = self.apply(self.field_a.id)
        self.correct(original.id)
        with self.assertRaises(FertilizationConflict):
            self.correct(original.id)

    def test_correction_needs_reason_and_existing_record(self) -> None:
        original = self.apply(self.field_a.id)
        with self.assertRaises(ValueError):
            self.correct(original.id, correction_reason="  ")
        with self.assertRaises(LookupError):
            self.correct("does-not-exist")


class FertilizationSummaryTest(FertilizationTestBase):
    def test_summary_does_not_turn_unknown_into_zero_or_mix_units(self) -> None:
        self.apply(self.field_a.id, quantity=50, quantity_unit="KG", cost_brl=200)
        self.apply(self.field_a.id, quantity=10, quantity_unit="L", cost_brl=None)
        self.apply(
            self.field_a.id,
            application_date="2026-10-12",
            quantity=None,
            quantity_unit=None,
        )
        summary = self.app.fertilization_summary(self.tenant.id, self.property.id)
        by_field = {x["field_id"]: x for x in summary["fields"]}
        block = by_field[self.field_a.id]
        self.assertEqual(block["record_count"], 3)
        self.assertEqual(block["quantity_by_unit"], {"KG": 50.0, "L": 10.0})
        self.assertEqual(block["records_without_quantity"], 1)
        self.assertEqual(block["cost_brl"]["total"], 200.0)
        self.assertEqual(block["cost_brl"]["records_without_value"], 2)
        self.assertEqual(block["last_application_date"], "2026-10-12")
        self.assertEqual(block["products"], ["Ureia"])
        empty = by_field[self.field_b.id]
        self.assertTrue(empty["no_fertilization_records"])
        self.assertIsNone(empty["cost_brl"]["total"])
        self.assertIsNone(empty["last_application_date"])
        self.assertEqual(summary["classification"], "CALCULATED")
        self.assertTrue(summary["limitations"])

    def test_summary_uses_only_current_records_and_filters(self) -> None:
        old = self.apply(self.field_a.id, cost_brl=999)
        self.app.correct_fertilization_record(
            self.tenant.id,
            old.id,
            correction_reason="custo errado",
            application_date="2026-10-10",
            product_name="Ureia",
            product_type="MINERAL_FERTILIZER",
            quantity=50,
            quantity_unit="KG",
            cost_brl=99,
            applied_by="João",
            recorded_by="Encarregado",
            source_reference="caderno de adubação",
        )
        self.apply(self.field_b.id, application_date="2026-09-01", cost_brl=10)
        summary = self.app.fertilization_summary(
            self.tenant.id, self.property.id, date_from="2026-10-01"
        )
        self.assertEqual(summary["property_totals"]["record_count"], 1)
        self.assertEqual(summary["property_totals"]["cost_brl"]["total"], 99.0)
        one = self.app.fertilization_summary(
            self.tenant.id, self.property.id, field_id=self.field_b.id
        )
        self.assertEqual(len(one["fields"]), 1)
        with self.assertRaises(LookupError):
            self.app.fertilization_summary(
                self.tenant.id, self.property.id, field_id="nope"
            )


class FertilizationApiTest(FertilizationTestBase):
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
            "application_date": "2026-10-10",
            "product_name": "Ureia",
            "product_type": "MINERAL_FERTILIZER",
            "quantity": 50,
            "quantity_unit": "KG",
            "applied_by": "João",
            "recorded_by": "Encarregado",
            "source_reference": "caderno de adubação",
        }
        values.update(overrides)
        return values

    def test_rbac_and_create(self) -> None:
        url = f"{self.base()}/properties/{self.property.id}/fertilization-records"
        operator, h_op = self.client("OPERATOR")
        analyst, h_an = self.client("ANALYST")
        viewer, h_vw = self.client("VIEWER")
        commercial, h_co = self.client("COMMERCIAL")
        self.assertEqual(viewer.get(url, headers=h_vw).status_code, 403)
        self.assertEqual(commercial.get(url, headers=h_co).status_code, 403)
        self.assertEqual(
            viewer.post(url, headers=h_vw, json=self.payload()).status_code, 403
        )
        self.assertEqual(
            analyst.post(url, headers=h_an, json=self.payload()).status_code, 403
        )
        created = operator.post(url, headers=h_op, json=self.payload())
        self.assertEqual(created.status_code, 201)
        body = created.json()
        self.assertIsNone(body["cost_brl"])
        self.assertIsNone(body["area_applied_ha"])
        self.assertIsNotNone(body["evidence_id"])
        listed = analyst.get(url, headers=h_an)
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(len(listed.json()["items"]), 1)

    def test_validation_errors(self) -> None:
        url = f"{self.base()}/properties/{self.property.id}/fertilization-records"
        client, h = self.client("MANAGER")
        for label, overrides in {
            "quantity without unit": {"quantity_unit": None},
            "future date": {"application_date": "2999-01-01"},
            "bad type": {"product_type": "MAGIC"},
            "negative cost": {"cost_brl": -1},
            "derived classification": {"classification": "CALCULATED"},
            "unknown field": {"unexpected": "x"},
        }.items():
            with self.subTest(case=label):
                status = client.post(
                    url, headers=h, json=self.payload(**overrides)
                ).status_code
                self.assertIn(status, (400, 422))
        missing = client.post(
            url, headers=h, json=self.payload(field_id="missing-field")
        )
        self.assertEqual(missing.status_code, 404)

    def test_correction_conflict_and_summary(self) -> None:
        url = f"{self.base()}/properties/{self.property.id}/fertilization-records"
        manager, h = self.client("MANAGER")
        original = manager.post(url, headers=h, json=self.payload()).json()
        body = self.payload(cost_brl=120)
        body.pop("field_id")
        body["correction_reason"] = "faltava o custo"
        corr = f"{self.base()}/fertilization-records/{original['id']}/corrections"
        first = manager.post(corr, headers=h, json=body)
        self.assertEqual(first.status_code, 201)
        self.assertEqual(first.json()["supersedes_id"], original["id"])
        second = manager.post(corr, headers=h, json=body)
        self.assertEqual(second.status_code, 409)
        self.assertEqual(second.json()["error"]["code"], "FERTILIZATION_CONFLICT")
        summary = manager.get(
            f"{self.base()}/properties/{self.property.id}/fertilization-summary",
            headers=h,
        )
        self.assertEqual(summary.status_code, 200)
        totals = summary.json()["property_totals"]
        self.assertEqual(totals["record_count"], 1)
        self.assertEqual(totals["cost_brl"]["total"], 120.0)

    def test_tenant_mismatch_is_forbidden(self) -> None:
        client, h = self.client("MANAGER")
        response = client.get(
            "/v1/tenants/other-tenant/properties/x/fertilization-summary", headers=h
        )
        self.assertEqual(response.status_code, 403)


class ValidationErrorTypeTest(FertilizationTestBase):
    def test_validation_error_is_value_error(self) -> None:
        self.assertTrue(issubclass(FertilizationValidationError, ValueError))
