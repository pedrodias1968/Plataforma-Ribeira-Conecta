"""Unit and API tests for harvest by field: evidence-first records, corrections, summary, RBAC."""

from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from ribeira_platform.api import create_app
from ribeira_platform.epistemology import DataClassification
from ribeira_platform.harvest import (
    HarvestConflict,
    HarvestValidationError,
    parse_record_date,
)
from ribeira_platform.iam import AuthContext, DevelopmentIdentityProvider
from ribeira_platform.service import RibeiraApplication
from ribeira_platform.storage import SQLiteStore


PROPERTY_GEOJSON = {
    "type": "Polygon",
    "coordinates": [
        [
            [-47.0, -24.0],
            [-46.98, -24.0],
            [-46.98, -24.02],
            [-47.0, -24.02],
            [-47.0, -24.0],
        ]
    ],
}

FIELD_A_GEOJSON = {
    "type": "Polygon",
    "coordinates": [
        [
            [-46.995, -24.005],
            [-46.985, -24.005],
            [-46.985, -24.010],
            [-46.995, -24.010],
            [-46.995, -24.005],
        ]
    ],
}

FIELD_B_GEOJSON = {
    "type": "Polygon",
    "coordinates": [
        [
            [-46.995, -24.012],
            [-46.985, -24.012],
            [-46.985, -24.017],
            [-46.995, -24.017],
            [-46.995, -24.012],
        ]
    ],
}


class HarvestTestBase(unittest.TestCase):
    def setUp(self) -> None:
        self.store = SQLiteStore()
        self.app = RibeiraApplication(self.store)
        self.tenant = self.app.create_tenant("Harvest Test Tenant")
        self.property = self.make_property(self.tenant.id, "Fazenda Colheita Teste")
        self.field_a = self.make_field(self.property.id, "Talhão A", FIELD_A_GEOJSON)
        self.field_b = self.make_field(self.property.id, "Talhão B", FIELD_B_GEOJSON)

    def make_property(self, tenant_id: str, name: str):
        return self.app.create_property(
            tenant_id,
            name,
            PROPERTY_GEOJSON,
            geometry_crs="EPSG:4326",
            boundary_source="MANUAL_FIELD_SURVEY",
        )

    def make_field(self, property_id: str, name: str, geometry: dict, tenant_id=None):
        return self.app.fields.create(
            tenant_id or self.tenant.id,
            property_id=property_id,
            name=name,
            status="ACTIVE",
            geometry_geojson=geometry,
            geometry_crs="EPSG:4326",
            source_reference="FIELD_SURVEY_GPS",
            observed_at="2026-09-20T10:00:00+00:00",
            classification=DataClassification.MANUAL_CONFIRMED,
            actor="agronomist@test.local",
        )

    def record(self, field_id: str, harvest_date: str = "2026-10-15", **measures):
        values = {"boxes_packed": 100}
        values.update(measures)
        return self.app.register_harvest_record(
            self.tenant.id,
            self.property.id,
            field_id=field_id,
            harvest_date=harvest_date,
            recorded_by="Encarregado",
            source_reference="caderno do encarregado",
            actor="operator@test.local",
            **values,
        )

    def discard(self, field_id: str, **overrides):
        values = {
            "discard_date": "2026-10-15",
            "reason": "STAIN",
            "quantity": 10,
            "unit": "BOXES",
        }
        values.update(overrides)
        return self.app.register_harvest_discard(
            self.tenant.id,
            self.property.id,
            field_id=field_id,
            recorded_by="Encarregado",
            source_reference="caderno do encarregado",
            actor="operator@test.local",
            **values,
        )


class HarvestRecordTest(HarvestTestBase):
    def test_absent_measures_stay_unknown_and_evidence_is_created(self) -> None:
        item = self.record(self.field_a.id, boxes_packed=120)
        self.assertEqual(item.boxes_packed, 120)
        self.assertIsNone(item.bunches_harvested)
        self.assertIsNone(item.weight_kg)
        self.assertEqual(item.harvest_date, "2026-10-15")
        self.assertEqual(item.classification, DataClassification.MANUAL_CONFIRMED)
        evidence = self.store.evidence_for_reference(self.tenant.id, item.id)
        self.assertIsNotNone(evidence)
        self.assertEqual(evidence.evidence_type, "HARVEST_RECORD")

        stored = self.app.list_harvest_records(self.tenant.id, self.property.id)
        self.assertEqual([entry.id for entry in stored], [item.id])
        self.assertIsNone(stored[0].bunches_harvested)

    def test_at_least_one_measure_is_required(self) -> None:
        with self.assertRaises(HarvestValidationError):
            self.app.register_harvest_record(
                self.tenant.id,
                self.property.id,
                field_id=self.field_a.id,
                harvest_date="2026-10-15",
                recorded_by="Encarregado",
                source_reference="caderno",
            )

    def test_invalid_measures_are_rejected(self) -> None:
        for measures in (
            {"boxes_packed": -1},
            {"bunches_harvested": True},
            {"bunches_harvested": 1.5},
            {"weight_kg": -0.1},
            {"weight_kg": float("nan")},
            {"weight_kg": float("inf")},
        ):
            with self.subTest(measures=measures):
                with self.assertRaises(HarvestValidationError):
                    self.record(self.field_a.id, **{"boxes_packed": None, **measures})

    def test_zero_is_a_valid_recorded_value(self) -> None:
        item = self.record(self.field_a.id, boxes_packed=0)
        self.assertEqual(item.boxes_packed, 0)

    def test_dates_are_validated(self) -> None:
        for bad in ("15/10/2026", "2026-13-01", "", "20261015"):
            with self.subTest(value=bad):
                with self.assertRaises(HarvestValidationError):
                    self.record(self.field_a.id, harvest_date=bad)
        with self.assertRaises(HarvestValidationError):
            self.record(self.field_a.id, harvest_date="2999-01-01")
        self.assertEqual(
            parse_record_date("2026-10-15", label="harvest_date"), "2026-10-15"
        )

    def test_derived_classifications_are_rejected(self) -> None:
        for classification in (
            DataClassification.CALCULATED,
            DataClassification.PREDICTED,
            DataClassification.INFERRED,
            DataClassification.SIMULATED,
        ):
            with self.subTest(classification=classification):
                with self.assertRaises(HarvestValidationError):
                    self.app.register_harvest_record(
                        self.tenant.id,
                        self.property.id,
                        field_id=self.field_a.id,
                        harvest_date="2026-10-15",
                        boxes_packed=10,
                        recorded_by="Encarregado",
                        source_reference="caderno",
                        classification=classification,
                    )

    def test_blank_recorder_and_source_are_rejected(self) -> None:
        with self.assertRaises(HarvestValidationError):
            self.app.register_harvest_record(
                self.tenant.id,
                self.property.id,
                field_id=self.field_a.id,
                harvest_date="2026-10-15",
                boxes_packed=10,
                recorded_by="   ",
                source_reference="caderno",
            )
        with self.assertRaises(HarvestValidationError):
            self.app.register_harvest_record(
                self.tenant.id,
                self.property.id,
                field_id=self.field_a.id,
                harvest_date="2026-10-15",
                boxes_packed=10,
                recorded_by="Encarregado",
                source_reference="",
            )

    def test_field_must_belong_to_the_property(self) -> None:
        other_property = self.make_property(self.tenant.id, "Outro Sítio")
        other_field = self.make_field(other_property.id, "Talhão X", FIELD_A_GEOJSON)
        with self.assertRaises(LookupError):
            self.record(other_field.id)
        with self.assertRaises(LookupError):
            self.record("00000000-0000-0000-0000-000000000000")

    def test_other_tenant_cannot_use_the_property(self) -> None:
        other_tenant = self.app.create_tenant("Another Tenant")
        with self.assertRaises(LookupError):
            self.app.register_harvest_record(
                other_tenant.id,
                self.property.id,
                field_id=self.field_a.id,
                harvest_date="2026-10-15",
                boxes_packed=10,
                recorded_by="Encarregado",
                source_reference="caderno",
            )
        self.assertEqual(
            self.app.harvest.list_records(other_tenant.id, self.property.id), []
        )

    def test_date_and_field_filters(self) -> None:
        a1 = self.record(self.field_a.id, "2026-10-10")
        a2 = self.record(self.field_a.id, "2026-10-20")
        b1 = self.record(self.field_b.id, "2026-10-15")
        everything = self.app.list_harvest_records(self.tenant.id, self.property.id)
        self.assertEqual(
            [item.id for item in everything], [a2.id, b1.id, a1.id]
        )  # newest first
        only_a = self.app.list_harvest_records(
            self.tenant.id, self.property.id, field_id=self.field_a.id
        )
        self.assertEqual({item.id for item in only_a}, {a1.id, a2.id})
        window = self.app.list_harvest_records(
            self.tenant.id,
            self.property.id,
            date_from="2026-10-12",
            date_to="2026-10-18",
        )
        self.assertEqual([item.id for item in window], [b1.id])
        with self.assertRaises(HarvestValidationError):
            self.app.list_harvest_records(
                self.tenant.id, self.property.id, date_from="12/10/2026"
            )


class HarvestCorrectionTest(HarvestTestBase):
    def test_correction_supersedes_and_preserves_history(self) -> None:
        original = self.record(self.field_a.id, boxes_packed=100)
        corrected = self.app.correct_harvest_record(
            self.tenant.id,
            original.id,
            correction_reason="caixas contadas errado",
            harvest_date="2026-10-15",
            boxes_packed=90,
            recorded_by="Encarregado",
            source_reference="conferência no galpão",
            actor="operator@test.local",
        )
        self.assertEqual(corrected.supersedes_id, original.id)
        self.assertEqual(corrected.field_id, original.field_id)
        self.assertEqual(corrected.property_id, original.property_id)
        self.assertEqual(corrected.boxes_packed, 90)

        current = self.app.list_harvest_records(self.tenant.id, self.property.id)
        self.assertEqual([item.id for item in current], [corrected.id])
        history = self.app.list_harvest_records(
            self.tenant.id, self.property.id, include_superseded=True
        )
        self.assertEqual({item.id for item in history}, {original.id, corrected.id})
        # The original row is untouched.
        stored = self.app.harvest.get_record(self.tenant.id, original.id)
        self.assertEqual(stored.boxes_packed, 100)

    def test_a_record_can_only_be_corrected_once(self) -> None:
        original = self.record(self.field_a.id)
        kwargs = dict(
            correction_reason="ajuste",
            harvest_date="2026-10-15",
            boxes_packed=80,
            recorded_by="Encarregado",
            source_reference="caderno",
        )
        self.app.correct_harvest_record(self.tenant.id, original.id, **kwargs)
        with self.assertRaises(HarvestConflict):
            self.app.correct_harvest_record(self.tenant.id, original.id, **kwargs)

    def test_correction_requires_a_reason_and_an_existing_record(self) -> None:
        original = self.record(self.field_a.id)
        with self.assertRaises(HarvestValidationError):
            self.app.correct_harvest_record(
                self.tenant.id,
                original.id,
                correction_reason="  ",
                harvest_date="2026-10-15",
                boxes_packed=80,
                recorded_by="Encarregado",
                source_reference="caderno",
            )
        with self.assertRaises(LookupError):
            self.app.correct_harvest_record(
                self.tenant.id,
                "00000000-0000-0000-0000-000000000000",
                correction_reason="ajuste",
                harvest_date="2026-10-15",
                boxes_packed=80,
                recorded_by="Encarregado",
                source_reference="caderno",
            )

    def test_correction_can_change_the_date(self) -> None:
        original = self.record(self.field_a.id, "2026-10-14")
        corrected = self.app.correct_harvest_record(
            self.tenant.id,
            original.id,
            correction_reason="data lançada errada",
            harvest_date="2026-10-15",
            boxes_packed=100,
            recorded_by="Encarregado",
            source_reference="caderno",
        )
        self.assertEqual(corrected.harvest_date, "2026-10-15")


class HarvestDiscardTest(HarvestTestBase):
    def test_discard_is_recorded_with_reason_unit_and_evidence(self) -> None:
        item = self.discard(self.field_a.id, reason="MECHANICAL_DAMAGE", quantity=7.5)
        self.assertEqual(item.reason, "MECHANICAL_DAMAGE")
        self.assertEqual(item.unit, "BOXES")
        self.assertEqual(item.quantity, 7.5)
        evidence = self.store.evidence_for_reference(self.tenant.id, item.id)
        self.assertEqual(evidence.evidence_type, "HARVEST_DISCARD")

    def test_other_reason_requires_notes(self) -> None:
        with self.assertRaises(HarvestValidationError):
            self.discard(self.field_a.id, reason="OTHER")
        item = self.discard(self.field_a.id, reason="OTHER", notes="fruta queimada")
        self.assertEqual(item.notes, "fruta queimada")

    def test_invalid_discard_values_are_rejected(self) -> None:
        for overrides in (
            {"reason": "ROTTEN"},
            {"unit": "TONS"},
            {"quantity": -1},
            {"quantity": float("nan")},
            {"quantity": True},
            {"discard_date": "2999-01-01"},
        ):
            with self.subTest(overrides=overrides):
                with self.assertRaises(HarvestValidationError):
                    self.discard(self.field_a.id, **overrides)

    def test_discard_correction_supersedes(self) -> None:
        original = self.discard(self.field_a.id, quantity=10)
        corrected = self.app.correct_harvest_discard(
            self.tenant.id,
            original.id,
            correction_reason="contagem refeita",
            discard_date="2026-10-15",
            reason="STAIN",
            quantity=12,
            unit="BOXES",
            recorded_by="Encarregado",
            source_reference="caderno",
        )
        self.assertEqual(corrected.supersedes_id, original.id)
        current = self.app.list_harvest_discards(self.tenant.id, self.property.id)
        self.assertEqual([item.id for item in current], [corrected.id])
        with self.assertRaises(HarvestConflict):
            self.app.correct_harvest_discard(
                self.tenant.id,
                original.id,
                correction_reason="outra vez",
                discard_date="2026-10-15",
                reason="STAIN",
                quantity=11,
                unit="BOXES",
                recorded_by="Encarregado",
                source_reference="caderno",
            )


class HarvestSummaryTest(HarvestTestBase):
    def test_summary_never_turns_missing_data_into_zero(self) -> None:
        self.record(self.field_a.id, "2026-10-10", boxes_packed=100, weight_kg=2000.5)
        self.record(self.field_a.id, "2026-10-12", boxes_packed=50)
        summary = self.app.harvest_summary(self.tenant.id, self.property.id)

        by_field = {item["field_id"]: item for item in summary["fields"]}
        a = by_field[self.field_a.id]
        self.assertEqual(a["record_count"], 2)
        self.assertFalse(a["no_harvest_records"])
        self.assertEqual(a["boxes_packed"]["total"], 150)
        self.assertEqual(a["weight_kg"]["total"], 2000.5)
        self.assertEqual(a["weight_kg"]["records_with_value"], 1)
        self.assertEqual(a["weight_kg"]["records_without_value"], 1)
        # No bunches were ever recorded: unknown, not zero.
        self.assertIsNone(a["bunches_harvested"]["total"])

        b = by_field[self.field_b.id]
        self.assertTrue(b["no_harvest_records"])
        self.assertEqual(b["record_count"], 0)
        self.assertIsNone(b["boxes_packed"]["total"])
        self.assertEqual(summary["classification"], "CALCULATED")
        self.assertTrue(summary["limitations"])

    def test_discards_are_grouped_by_unit_and_never_combined(self) -> None:
        self.record(self.field_a.id)
        self.discard(self.field_a.id, reason="STAIN", quantity=10, unit="BOXES")
        self.discard(self.field_a.id, reason="CALIBER", quantity=4, unit="BOXES")
        self.discard(self.field_a.id, reason="STAIN", quantity=25.5, unit="KG")
        summary = self.app.harvest_summary(self.tenant.id, self.property.id)
        a = next(i for i in summary["fields"] if i["field_id"] == self.field_a.id)
        units = a["discards_by_unit"]
        self.assertEqual(units["BOXES"]["total"], 14)
        self.assertEqual(units["BOXES"]["by_reason"], {"STAIN": 10, "CALIBER": 4})
        self.assertEqual(units["KG"]["total"], 25.5)
        self.assertNotIn("BUNCHES", units)
        # No percentage is invented.
        self.assertNotIn("discard_percentage", a)
        self.assertEqual(a["discard_record_count"], 3)

    def test_summary_counts_only_current_records(self) -> None:
        original = self.record(self.field_a.id, boxes_packed=100)
        self.app.correct_harvest_record(
            self.tenant.id,
            original.id,
            correction_reason="ajuste",
            harvest_date="2026-10-15",
            boxes_packed=90,
            recorded_by="Encarregado",
            source_reference="caderno",
        )
        summary = self.app.harvest_summary(self.tenant.id, self.property.id)
        a = next(i for i in summary["fields"] if i["field_id"] == self.field_a.id)
        self.assertEqual(a["record_count"], 1)
        self.assertEqual(a["boxes_packed"]["total"], 90)

    def test_summary_period_and_field_filter(self) -> None:
        self.record(self.field_a.id, "2026-10-01", boxes_packed=10)
        self.record(self.field_a.id, "2026-10-20", boxes_packed=20)
        self.record(self.field_b.id, "2026-10-20", boxes_packed=5)
        summary = self.app.harvest_summary(
            self.tenant.id,
            self.property.id,
            field_id=self.field_a.id,
            date_from="2026-10-15",
            date_to="2026-10-31",
        )
        self.assertEqual([i["field_id"] for i in summary["fields"]], [self.field_a.id])
        self.assertEqual(summary["fields"][0]["boxes_packed"]["total"], 20)
        self.assertEqual(summary["property_totals"]["boxes_packed"]["total"], 20)
        with self.assertRaises(LookupError):
            self.app.harvest_summary(
                self.tenant.id,
                self.property.id,
                field_id="00000000-0000-0000-0000-000000000000",
            )


class HarvestApiTest(HarvestTestBase):
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
            "harvest_date": "2026-10-15",
            "boxes_packed": 120,
            "recorded_by": "Encarregado",
            "source_reference": "caderno do encarregado",
        }
        values.update(overrides)
        return values

    def test_rbac_for_harvest_records(self) -> None:
        url = f"{self.base()}/properties/{self.property.id}/harvest-records"
        operator, h_operator = self.client("OPERATOR")
        analyst, h_analyst = self.client("ANALYST")
        viewer, h_viewer = self.client("VIEWER")
        commercial, h_commercial = self.client("COMMERCIAL")

        self.assertEqual(
            viewer.post(url, headers=h_viewer, json=self.payload()).status_code, 403
        )
        self.assertEqual(viewer.get(url, headers=h_viewer).status_code, 403)
        self.assertEqual(commercial.get(url, headers=h_commercial).status_code, 403)
        self.assertEqual(
            analyst.post(url, headers=h_analyst, json=self.payload()).status_code, 403
        )

        created = operator.post(url, headers=h_operator, json=self.payload())
        self.assertEqual(created.status_code, 201)
        body = created.json()
        self.assertEqual(body["boxes_packed"], 120)
        self.assertIsNone(body["bunches_harvested"])
        self.assertIsNone(body["weight_kg"])
        self.assertIsNotNone(body["evidence_id"])

        listed = analyst.get(url, headers=h_analyst)
        self.assertEqual(listed.status_code, 200)
        self.assertEqual([item["id"] for item in listed.json()["items"]], [body["id"]])

    def test_validation_and_not_found_errors(self) -> None:
        url = f"{self.base()}/properties/{self.property.id}/harvest-records"
        operator, h = self.client("OPERATOR")
        no_measure = self.payload()
        del no_measure["boxes_packed"]
        self.assertEqual(
            operator.post(url, headers=h, json=no_measure).status_code, 422
        )
        self.assertEqual(
            operator.post(
                url, headers=h, json=self.payload(harvest_date="2999-01-01")
            ).status_code,
            422,
        )
        self.assertEqual(
            operator.post(
                url, headers=h, json=self.payload(boxes_packed=-5)
            ).status_code,
            422,
        )
        self.assertEqual(
            operator.post(
                url, headers=h, json=self.payload(classification="CALCULATED")
            ).status_code,
            422,
        )
        self.assertEqual(
            operator.post(
                url, headers=h, json=self.payload(unexpected="x")
            ).status_code,
            422,
        )
        self.assertEqual(
            operator.post(
                url,
                headers=h,
                json=self.payload(field_id="00000000-0000-0000-0000-000000000000"),
            ).status_code,
            404,
        )
        missing_property = (
            f"{self.base()}/properties/00000000-0000-0000-0000-000000000000"
            "/harvest-records"
        )
        self.assertEqual(operator.get(missing_property, headers=h).status_code, 404)

    def test_correction_flow_and_conflict(self) -> None:
        url = f"{self.base()}/properties/{self.property.id}/harvest-records"
        manager, h = self.client("MANAGER")
        original = manager.post(url, headers=h, json=self.payload()).json()
        correction = {
            "correction_reason": "caixas contadas errado",
            "harvest_date": "2026-10-15",
            "boxes_packed": 110,
            "recorded_by": "Encarregado",
            "source_reference": "conferência no galpão",
        }
        corr_url = f"{self.base()}/harvest-records/{original['id']}/corrections"
        first = manager.post(corr_url, headers=h, json=correction)
        self.assertEqual(first.status_code, 201)
        self.assertEqual(first.json()["supersedes_id"], original["id"])
        second = manager.post(corr_url, headers=h, json=correction)
        self.assertEqual(second.status_code, 409)
        self.assertEqual(second.json()["error"]["code"], "HARVEST_CONFLICT")

        current = manager.get(url, headers=h).json()["items"]
        self.assertEqual([item["id"] for item in current], [first.json()["id"]])
        history = manager.get(url + "?include_superseded=true", headers=h).json()[
            "items"
        ]
        self.assertEqual(len(history), 2)

        no_reason = dict(correction)
        del no_reason["correction_reason"]
        self.assertEqual(
            manager.post(corr_url, headers=h, json=no_reason).status_code, 422
        )
        missing = f"{self.base()}/harvest-records/00000000-0000-0000-0000-000000000000/corrections"
        self.assertEqual(
            manager.post(missing, headers=h, json=correction).status_code, 404
        )

    def test_discards_and_summary_over_the_api(self) -> None:
        operator, h = self.client("OPERATOR")
        analyst, h_analyst = self.client("ANALYST")
        records_url = f"{self.base()}/properties/{self.property.id}/harvest-records"
        discards_url = f"{self.base()}/properties/{self.property.id}/harvest-discards"
        summary_url = f"{self.base()}/properties/{self.property.id}/harvest-summary"

        operator.post(records_url, headers=h, json=self.payload())
        discard = {
            "field_id": self.field_a.id,
            "discard_date": "2026-10-15",
            "reason": "STAIN",
            "quantity": 8,
            "unit": "BOXES",
            "recorded_by": "Encarregado",
            "source_reference": "caderno",
        }
        created = operator.post(discards_url, headers=h, json=discard)
        self.assertEqual(created.status_code, 201)
        self.assertEqual(
            operator.post(
                discards_url, headers=h, json={**discard, "reason": "ROTTEN"}
            ).status_code,
            422,
        )
        self.assertEqual(
            operator.post(
                discards_url, headers=h, json={**discard, "reason": "OTHER"}
            ).status_code,
            422,
        )

        corr = operator.post(
            f"{self.base()}/harvest-discards/{created.json()['id']}/corrections",
            headers=h,
            json={
                "correction_reason": "contagem refeita",
                "discard_date": "2026-10-15",
                "reason": "STAIN",
                "quantity": 9,
                "unit": "BOXES",
                "recorded_by": "Encarregado",
                "source_reference": "caderno",
            },
        )
        self.assertEqual(corr.status_code, 201)

        listed = analyst.get(discards_url, headers=h_analyst)
        self.assertEqual(len(listed.json()["items"]), 1)
        self.assertEqual(listed.json()["items"][0]["quantity"], 9)

        summary = analyst.get(summary_url, headers=h_analyst)
        self.assertEqual(summary.status_code, 200)
        data = summary.json()
        a = next(i for i in data["fields"] if i["field_id"] == self.field_a.id)
        self.assertEqual(a["discards_by_unit"]["BOXES"]["total"], 9)
        b = next(i for i in data["fields"] if i["field_id"] == self.field_b.id)
        self.assertTrue(b["no_harvest_records"])
        self.assertEqual(
            analyst.get(summary_url + "?date_from=bad", headers=h_analyst).status_code,
            422,
        )

    def test_other_tenant_identity_is_rejected(self) -> None:
        other = self.app.create_tenant("Intruder Tenant")
        client = TestClient(
            create_app(
                self.app,
                DevelopmentIdentityProvider(
                    "intruder-token",
                    AuthContext(
                        "intruder", other.id, roles=frozenset({"TENANT_ADMIN"})
                    ),
                ),
            )
        )
        url = f"{self.base()}/properties/{self.property.id}/harvest-records"
        headers = {"Authorization": "Bearer intruder-token"}
        self.assertEqual(client.get(url, headers=headers).status_code, 403)
        self.assertEqual(
            client.post(url, headers=headers, json=self.payload()).status_code, 403
        )


if __name__ == "__main__":
    unittest.main()
