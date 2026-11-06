"""Unit tests for ribeira_platform.models.

Covers the pure helpers and dataclass contract only. No database, network or
external provider is required: every case here is deterministic and local.
Persistence of these models is exercised by the integration suite and is not
duplicated here.
"""

from __future__ import annotations

import unittest
import uuid
from dataclasses import FrozenInstanceError
from datetime import datetime, timezone
from decimal import Decimal

from ribeira_platform.epistemology import DataClassification, QualityFlag
from ribeira_platform.models import (
    DecisionResult,
    FetchResult,
    Observation,
    Property,
    RuleDefinition,
    Source,
    Tenant,
    now_utc,
    new_id,
    to_jsonable,
)


class NowUtcTests(unittest.TestCase):
    def test_returns_iso_formatted_string(self) -> None:
        value = now_utc()
        self.assertIsInstance(value, str)
        parsed = datetime.fromisoformat(value)
        self.assertEqual(parsed.year, datetime.now(timezone.utc).year)

    def test_value_carries_utc_offset(self) -> None:
        parsed = datetime.fromisoformat(now_utc())
        self.assertIsNotNone(parsed.tzinfo)
        self.assertEqual(parsed.utcoffset(), timezone.utc.utcoffset(None))


class NewIdTests(unittest.TestCase):
    def test_returns_uuid_string(self) -> None:
        value = new_id()
        self.assertIsInstance(value, str)
        self.assertEqual(str(uuid.UUID(value)), value)

    def test_each_call_is_unique(self) -> None:
        self.assertNotEqual(new_id(), new_id())


class DataclassContractTests(unittest.TestCase):
    def test_tenant_defaults_created_at(self) -> None:
        tenant = Tenant(id="t1", name="Fazenda")
        self.assertEqual(tenant.id, "t1")
        self.assertEqual(tenant.name, "Fazenda")
        self.assertIsInstance(tenant.created_at, str)

    def test_property_defaults_are_evidence_first(self) -> None:
        prop = Property(id="p1", tenant_id="t1", name="Talhao")
        self.assertIsNone(prop.geometry_geojson)
        self.assertIsNone(prop.geometry_crs)
        self.assertEqual(prop.classification, DataClassification.MANUAL_CONFIRMED)
        self.assertIsNone(prop.updated_at)

    def test_source_status_defaults_to_configured(self) -> None:
        source = Source(
            id="s1",
            tenant_id="t1",
            name="Estacao",
            source_type="HYDROLOGY",
            provider="SP_AGUAS",
        )
        self.assertEqual(source.status, "CONFIGURED")
        self.assertIsNone(source.endpoint)

    def test_observation_defaults_are_observed_and_valid(self) -> None:
        obs = Observation(
            id="o1",
            tenant_id="t1",
            property_id="p1",
            source_id="s1",
            metric="RAINFALL",
            value=12.5,
            unit="mm",
            observation_timestamp="2026-09-11T10:59:10+00:00",
        )
        self.assertEqual(obs.classification, DataClassification.OBSERVED)
        self.assertEqual(obs.quality_flag, QualityFlag.VALID)

    def test_observation_allows_unknown_value(self) -> None:
        obs = Observation(
            id="o2",
            tenant_id="t1",
            property_id="p1",
            source_id="s1",
            metric="RIVER_LEVEL",
            value=None,
            unit=None,
            observation_timestamp="2026-09-11T10:59:10+00:00",
        )
        self.assertIsNone(obs.value)

    def test_models_are_frozen(self) -> None:
        tenant = Tenant(id="t1", name="Fazenda")
        with self.assertRaises(FrozenInstanceError):
            tenant.name = "other"  # type: ignore[misc]

    def test_fetch_result_defaults_classification_to_unknown(self) -> None:
        result = FetchResult(
            status="SOURCE_UNAVAILABLE", observations=[], message="no data"
        )
        self.assertEqual(result.source_classification, DataClassification.UNKNOWN)
        self.assertEqual(result.observations, [])


class ToJsonableTests(unittest.TestCase):
    def test_decimal_is_rendered_without_scientific_notation(self) -> None:
        self.assertEqual(to_jsonable(Decimal("123.4500")), "123.4500")

    def test_enum_is_reduced_to_its_value(self) -> None:
        self.assertEqual(to_jsonable(DataClassification.OBSERVED), "OBSERVED")
        self.assertEqual(to_jsonable(QualityFlag.STALE), "STALE")

    def test_dataclass_is_converted_recursively(self) -> None:
        tenant = Tenant(id="t1", name="Fazenda")
        payload = to_jsonable(tenant)
        self.assertEqual(payload["id"], "t1")
        self.assertEqual(payload["name"], "Fazenda")
        self.assertIsInstance(payload["created_at"], str)

    def test_nested_dataclass_fields_are_converted(self) -> None:
        prop = Property(id="p1", tenant_id="t1", name="Talhao")
        result = DecisionResult(
            decision=_make_decision(prop),
            alert=None,
            action=None,
        )
        payload = to_jsonable(result)
        self.assertEqual(payload["decision"]["classification"], "OBSERVED")
        self.assertIsNone(payload["alert"])

    def test_list_and_dict_are_converted_elementwise(self) -> None:
        payload = to_jsonable([Decimal("1.5"), {"k": DataClassification.DERIVED}])
        self.assertEqual(payload, ["1.5", {"k": "DERIVED"}])

    def test_scalars_pass_through_unchanged(self) -> None:
        self.assertEqual(to_jsonable(5), 5)
        self.assertEqual(to_jsonable("x"), "x")
        self.assertIsNone(to_jsonable(None))


def _make_decision(prop: Property):
    from ribeira_platform.epistemology import DecisionStatus
    from ribeira_platform.models import Decision

    return Decision(
        id="d1",
        tenant_id=prop.tenant_id,
        property_id=prop.id,
        conclusion="test",
        classification=DataClassification.OBSERVED,
        status=DecisionStatus.INCONCLUSIVE,
        evidence_ids=[],
        rule_id=None,
        rule_version=None,
        model_id=None,
        model_version=None,
        confidence=None,
        limitations=[],
        missing_data=[],
        conflicts=[],
        recommended_action=None,
    )


class ModelImportSmokeTests(unittest.TestCase):
    def test_core_models_are_importable_and_distinct(self) -> None:
        self.assertIsNot(Tenant, Property)
        self.assertIsNot(Observation, Source)
        self.assertIsNot(RuleDefinition, Source)


if __name__ == "__main__":
    unittest.main()
