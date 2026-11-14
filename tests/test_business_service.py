"""Unit tests for ribeira_platform.business_service.

Covers the pure helpers and the main orchestration logic of
``BusinessApplication`` using in-memory fakes for the store and repository.
No database, network or external provider is required. Infrastructure paths
that depend on real SQL persistence are exercised through the fake repository
only where the service logic itself is under test; the remaining persistence
paths are skipped with an explicit reason.
"""

from __future__ import annotations

import unittest
from contextlib import contextmanager
from decimal import Decimal

from ribeira_platform.business import (
    Asset,
    CapitalBreakdown,
    CommercialClassification,
    ConditionState,
    OperationalCapacityPolicy,
    OpportunityClassification,
    PricingPolicyVersion,
    PricingStatus,
    ProspectScoringFactor,
    ProspectScoringModelVersion,
)
from ribeira_platform.business_service import (
    BusinessApplication,
    OpportunityQualification,
)
from ribeira_platform.epistemology import DataClassification
from ribeira_platform.models import new_id


class _FakeConnection:
    def executescript(self, script: str) -> None:
        del script

    def execute(self, *args, **kwargs):
        raise AssertionError("unexpected SQL execution in unit test")


class _FakeStore:
    def __init__(self) -> None:
        self.connection = _FakeConnection()
        self.audits: list[tuple] = []
        self.evidence: dict[tuple[str, str], object] = {}
        self.properties: dict[tuple[str, str], object] = {}

    @contextmanager
    def tenant_transaction(self, tenant_id, platform_admin=False):
        del tenant_id, platform_admin
        yield self

    def audit(self, *args) -> None:
        self.audits.append(args)

    def evidence_for_reference(self, tenant_id: str, reference_id: str):
        return self.evidence.get((tenant_id, reference_id))

    def create_evidence(self, item):
        self.evidence[(item.tenant_id, item.reference_id)] = item
        return item

    def get_property(self, tenant_id: str, property_id: str):
        return self.properties.get((tenant_id, property_id))


class _FakeRepository:
    def __init__(self) -> None:
        self.customers: list = []
        self.assets: list = []
        self.opportunities: list = []
        self.opportunity_evidence: list = []
        self.pricing_version = None
        self.capacity_policy = None
        self.rule = None
        self.evidence_ids: set[str] = set()
        self.assets_by_id: dict[tuple[str, str], Asset] = {}

    def create_customer(self, item):
        self.customers.append(item)
        return item

    def create_asset(self, item):
        self.assets.append(item)
        self.assets_by_id[(item.tenant_id, item.id)] = item
        return item

    def get_asset(self, tenant_id: str, asset_id: str):
        return self.assets_by_id.get((tenant_id, asset_id))

    def get_pricing_policy_version(self, tenant_id, policy_id, version=None):
        del tenant_id, policy_id, version
        return self.pricing_version

    def active_capacity_policy(self, tenant_id, capacity_type, at):
        del tenant_id, capacity_type, at
        return self.capacity_policy

    def get_commercial_rule_version(self, tenant_id, rule_id, version=None):
        del tenant_id, rule_id, version
        return self.rule

    def evidence_exists(self, tenant_id: str, evidence_id: str) -> bool:
        del tenant_id
        return evidence_id in self.evidence_ids

    def create_opportunity(self, item):
        self.opportunities.append(item)
        return item

    def create_opportunity_evidence(self, *args) -> None:
        self.opportunity_evidence.append(args)


def _application() -> tuple[BusinessApplication, _FakeStore, _FakeRepository]:
    store = _FakeStore()
    app = BusinessApplication(store)
    repository = _FakeRepository()
    app.repository = repository
    return app, store, repository


def _asset(tenant_id: str, **overrides) -> Asset:
    values = {
        "id": new_id(),
        "tenant_id": tenant_id,
        "asset_type": "IRRIGATION_PUMP",
        "name": "Pump A",
        "serial_number": None,
        "status": "ACTIVE",
        "property_id": None,
        "site_id": None,
        "classification": CommercialClassification.CONFIRMED,
    }
    values.update(overrides)
    return Asset(**values)


def _pricing_version() -> PricingPolicyVersion:
    return PricingPolicyVersion(
        id=new_id(),
        tenant_id="tenant-1",
        policy_id="policy-1",
        version=1,
        status="ACTIVE",
        lower_threshold=Decimal("1000"),
        lower_rate=Decimal("0.1"),
        lower_minimum=Decimal("100"),
        upper_rate=Decimal("0.2"),
        upper_minimum=Decimal("200"),
        currency="BRL",
        valid_from="2026-01-01T00:00:00+00:00",
        valid_until=None,
        created_by="creator",
        approved_by="approver",
        classification=CommercialClassification.CONFIRMED,
        source="unit-test",
    )


class EvidenceClassificationTests(unittest.TestCase):
    def test_every_commercial_classification_maps_to_evidence_classification(
        self,
    ) -> None:
        expected = {
            CommercialClassification.CONFIRMED: DataClassification.MANUAL_CONFIRMED,
            CommercialClassification.OBSERVED: DataClassification.OBSERVED,
            CommercialClassification.MANUAL_CONFIRMED: DataClassification.MANUAL_CONFIRMED,
            CommercialClassification.CALCULATED: DataClassification.CALCULATED,
            CommercialClassification.ASSUMPTION: DataClassification.ASSUMPTION,
            CommercialClassification.SIMULATION: DataClassification.SIMULATED,
            CommercialClassification.UNKNOWN: DataClassification.UNKNOWN,
        }
        for source, target in expected.items():
            with self.subTest(source=source):
                self.assertEqual(
                    BusinessApplication._asset_evidence_classification(source),
                    target,
                )


class OpportunityQualificationTests(unittest.TestCase):
    def test_value_object_is_frozen(self) -> None:
        qualification = OpportunityQualification(
            condition=None, opportunity=None, status="INCONCLUSIVE", missing_data=[]
        )
        with self.assertRaises(Exception):
            qualification.status = "QUALIFIED"  # type: ignore[misc]


class CreateCustomerTests(unittest.TestCase):
    def test_create_customer_persists_confirmed_record_and_audits(self) -> None:
        app, store, repository = _application()
        customer = app.create_customer(
            "tenant-1", "Fazenda Ribeira", actor="operator"
        )
        self.assertEqual(customer.tenant_id, "tenant-1")
        self.assertEqual(customer.display_name, "Fazenda Ribeira")
        self.assertEqual(customer.classification, CommercialClassification.CONFIRMED)
        self.assertEqual(repository.customers, [customer])
        self.assertEqual(len(store.audits), 1)
        self.assertEqual(store.audits[0][2], "CUSTOMER_CREATED")

    def test_create_customer_accepts_explicit_identifier(self) -> None:
        app, _, _ = _application()
        customer = app.create_customer(
            "tenant-1", "Cliente", customer_id="customer-fixed"
        )
        self.assertEqual(customer.id, "customer-fixed")


class RegisterAssetTests(unittest.TestCase):
    def test_register_asset_creates_evidence_and_audit(self) -> None:
        app, store, repository = _application()
        asset = _asset("tenant-1")
        returned = app.register_asset(asset, actor="operator")
        self.assertIs(returned, asset)
        self.assertEqual(repository.assets, [asset])
        evidence = store.evidence[(asset.tenant_id, asset.id)]
        self.assertEqual(evidence.evidence_type, "ASSET_REGISTRATION")
        self.assertEqual(
            evidence.classification, DataClassification.MANUAL_CONFIRMED
        )
        self.assertEqual(len(store.audits), 1)
        self.assertEqual(store.audits[0][2], "ASSET_REGISTERED")

    def test_register_asset_reuses_existing_evidence(self) -> None:
        app, store, _ = _application()
        asset = _asset("tenant-1")
        app.register_asset(asset, actor="operator")
        app.register_asset(asset, actor="operator")
        self.assertEqual(len(store.evidence), 1)

    def test_register_asset_rejects_unknown_property(self) -> None:
        app, _, _ = _application()
        asset = _asset("tenant-1", property_id="missing-property")
        with self.assertRaises(LookupError):
            app.register_asset(asset, actor="operator")


class AssetForRuleEvaluationTests(unittest.TestCase):
    def test_missing_asset_raises_lookup_error(self) -> None:
        app, _, _ = _application()
        with self.assertRaises(LookupError):
            app.asset_for_rule_evaluation("tenant-1", "missing")

    def test_asset_without_property_is_rejected(self) -> None:
        app, _, repository = _application()
        asset = _asset("tenant-1")
        repository.create_asset(asset)
        with self.assertRaises(ValueError):
            app.asset_for_rule_evaluation("tenant-1", asset.id)

    def test_asset_linked_to_property_is_returned(self) -> None:
        app, store, repository = _application()
        asset = _asset("tenant-1", property_id="property-1")
        repository.create_asset(asset)
        store.properties[("tenant-1", "property-1")] = object()
        self.assertIs(
            app.asset_for_rule_evaluation("tenant-1", asset.id), asset
        )


class SimulatePriceTests(unittest.TestCase):
    def test_missing_policy_returns_incomplete_pricing(self) -> None:
        app, _, _ = _application()
        result = app.simulate_price(
            "tenant-1",
            "policy-1",
            CapitalBreakdown(Decimal("5000"), Decimal("1000"), Decimal("500")),
        )
        self.assertEqual(result.status, PricingStatus.INCOMPLETE_PRICING)
        self.assertIsNone(result.result)
        self.assertIn("active_pricing_policy_version", result.missing_data)
        self.assertTrue(result.simulation)

    def test_present_policy_is_priced_as_simulation(self) -> None:
        app, _, repository = _application()
        repository.pricing_version = _pricing_version()
        result = app.simulate_price(
            "tenant-1",
            "policy-1",
            CapitalBreakdown(Decimal("5000"), Decimal("1000"), Decimal("500")),
        )
        self.assertEqual(result.status, PricingStatus.COMPLETE)
        self.assertEqual(result.result, Decimal("700"))
        self.assertTrue(result.simulation)


class EvaluateCapacityTests(unittest.TestCase):
    def test_missing_policy_returns_unknown(self) -> None:
        app, _, _ = _application()
        evaluation = app.evaluate_capacity("tenant-1", Decimal("10"), "AREA")
        self.assertEqual(evaluation.status.value, "UNKNOWN")
        self.assertIsNone(evaluation.current_capacity)

    def test_request_above_policy_requires_gate(self) -> None:
        app, _, repository = _application()
        repository.capacity_policy = OperationalCapacityPolicy(
            id=new_id(),
            tenant_id="tenant-1",
            scope="TENANT",
            capacity_type="AREA",
            value=Decimal("100"),
            unit="ha",
            effective_from="2026-01-01T00:00:00+00:00",
            effective_until=None,
            status="ACTIVE",
            created_by="creator",
            approved_by="approver",
            source="unit-test",
            classification=CommercialClassification.CONFIRMED,
        )
        evaluation = app.evaluate_capacity("tenant-1", Decimal("150"), "AREA")
        self.assertEqual(evaluation.status.value, "CAPACITY_GATE_REQUIRED")
        self.assertEqual(evaluation.difference, Decimal("50"))


class QualifyOpportunityTests(unittest.TestCase):
    def test_missing_rule_is_inconclusive(self) -> None:
        app, _, _ = _application()
        qualification = app.qualify_opportunity(
            "tenant-1", "customer-1", None, "rule-1", {}, actor="operator"
        )
        self.assertEqual(qualification.status, "INCONCLUSIVE")
        self.assertIsNone(qualification.opportunity)
        self.assertEqual(qualification.missing_data, ["active_commercial_rule"])

    def test_unknown_fact_is_inconclusive(self) -> None:
        app, _, repository = _application()
        repository.rule = {
            "condition": {"fact": "area", "operator": "gt", "value": 10},
            "action": {"opportunity_type": "IRRIGATION"},
            "version": 1,
        }
        qualification = app.qualify_opportunity(
            "tenant-1", "customer-1", None, "rule-1", {}, actor="operator"
        )
        self.assertEqual(qualification.status, "INCONCLUSIVE")
        self.assertEqual(qualification.condition.state, ConditionState.UNKNOWN)
        self.assertIn("area", qualification.missing_data)

    def test_false_condition_is_not_applicable(self) -> None:
        app, _, repository = _application()
        repository.rule = {
            "condition": {"fact": "area", "operator": "gt", "value": 10},
            "action": {"opportunity_type": "IRRIGATION"},
            "version": 1,
        }
        qualification = app.qualify_opportunity(
            "tenant-1", "customer-1", None, "rule-1", {"area": 5}, actor="operator"
        )
        self.assertEqual(qualification.status, "NOT_APPLICABLE")
        self.assertIsNone(qualification.opportunity)

    def test_true_condition_without_evidence_is_inconclusive(self) -> None:
        app, _, repository = _application()
        repository.rule = {
            "condition": {
                "fact": "area",
                "operator": "gt",
                "value": 10,
                "evidence_ids": ["evidence-1"],
            },
            "action": {"opportunity_type": "IRRIGATION"},
            "version": 1,
        }
        qualification = app.qualify_opportunity(
            "tenant-1", "customer-1", None, "rule-1", {"area": 20}, actor="operator"
        )
        self.assertEqual(qualification.status, "INCONCLUSIVE")
        self.assertEqual(
            qualification.missing_data,
            ["valid_evidence_for_commercial_conclusion"],
        )

    def test_true_condition_with_evidence_creates_opportunity(self) -> None:
        app, store, repository = _application()
        repository.evidence_ids.add("evidence-1")
        repository.rule = {
            "condition": {
                "fact": "area",
                "operator": "gt",
                "value": 10,
                "evidence_ids": ["evidence-1"],
            },
            "action": {"opportunity_type": "IRRIGATION"},
            "version": 2,
        }
        qualification = app.qualify_opportunity(
            "tenant-1",
            "customer-1",
            "property-1",
            "rule-1",
            {"area": 20},
            actor="operator",
            classification=OpportunityClassification.CONFIRMED_NEED,
        )
        self.assertEqual(qualification.status, "QUALIFIED")
        self.assertIsNotNone(qualification.opportunity)
        self.assertEqual(len(repository.opportunities), 1)
        self.assertEqual(repository.opportunities[0].rule_version, 2)
        self.assertEqual(repository.opportunity_evidence[0][3], "RULE_SUPPORT")
        self.assertEqual(store.audits[-1][2], "COMMERCIAL_OPPORTUNITY_CREATED")


class ScoreProspectTests(unittest.TestCase):
    def _model(self, unknown_policy: str = "IGNORE") -> ProspectScoringModelVersion:
        return ProspectScoringModelVersion(
            id="model-version-1",
            tenant_id="tenant-1",
            model_id="model-1",
            version=1,
            status="ACTIVE",
            unknown_policy=unknown_policy,
            valid_from="2026-01-01T00:00:00+00:00",
            valid_until=None,
            created_by="creator",
            approved_by="approver",
        )

    def _factor(self, key: str, points: int, unknown_policy: str) -> ProspectScoringFactor:
        return ProspectScoringFactor(
            id=new_id(),
            tenant_id="tenant-1",
            model_version_id="model-version-1",
            factor_key=key,
            description=key,
            condition={"fact": key, "operator": "eq", "value": True},
            points=points,
            unknown_policy=unknown_policy,
            status="ACTIVE",
        )

    def test_known_factors_accumulate_score(self) -> None:
        result = BusinessApplication.score_prospect(
            self._model(),
            [
                self._factor("has_water", 10, "IGNORE"),
                self._factor("has_road", 5, "IGNORE"),
            ],
            {"has_water": True, "has_road": True},
        )
        self.assertEqual(result.score, Decimal("15"))
        self.assertEqual(len(result.positive_factors), 2)

    def test_unknown_factor_with_block_policy_blocks_score(self) -> None:
        result = BusinessApplication.score_prospect(
            self._model(),
            [self._factor("has_water", 10, "BLOCK")],
            {},
        )
        self.assertIsNone(result.score)
        self.assertEqual(len(result.unknown_factors), 1)

    def test_unknown_factor_with_penalize_policy_reduces_score(self) -> None:
        result = BusinessApplication.score_prospect(
            self._model(),
            [self._factor("has_water", 10, "PENALIZE")],
            {},
        )
        self.assertEqual(result.score, Decimal("-10"))


class ValidationGuardTests(unittest.TestCase):
    def test_active_pricing_version_requires_distinct_approver(self) -> None:
        app, _, _ = _application()
        version = _pricing_version()
        version = PricingPolicyVersion(
            **{**version.__dict__, "approved_by": version.created_by}
        )
        with self.assertRaises(ValueError):
            app.create_pricing_policy_version(version, actor="operator")

    def test_active_capacity_policy_requires_distinct_approver(self) -> None:
        app, _, _ = _application()
        policy = OperationalCapacityPolicy(
            id=new_id(),
            tenant_id="tenant-1",
            scope="TENANT",
            capacity_type="AREA",
            value=Decimal("100"),
            unit="ha",
            effective_from="2026-01-01T00:00:00+00:00",
            effective_until=None,
            status="ACTIVE",
            created_by="creator",
            approved_by="creator",
            source="unit-test",
            classification=CommercialClassification.CONFIRMED,
        )
        with self.assertRaises(ValueError):
            app.create_capacity_policy(policy, actor="operator")

    def test_active_commercial_rule_requires_distinct_approver(self) -> None:
        app, _, _ = _application()
        with self.assertRaises(ValueError):
            app.create_commercial_rule_version(
                "tenant-1",
                "Rule",
                {"fact": "x", "operator": "eq", "value": 1},
                {"opportunity_type": "IRRIGATION"},
                created_by="creator",
                approved_by="creator",
                status="ACTIVE",
            )

    def test_link_customer_property_rejects_naive_timestamp(self) -> None:
        app, _, _ = _application()
        with self.assertRaises(ValueError):
            app.link_customer_property(
                "tenant-1",
                "customer-1",
                "property-1",
                "OWNER",
                "2026-01-01T00:00:00",
                None,
                "operator",
            )


class PersistencePathSkipTests(unittest.TestCase):
    @unittest.skip(
        "requires real SQL persistence (SQLite/Postgres) for repository writes"
    )
    def test_contract_and_subscription_persistence(self) -> None:
        self.skipTest("infrastructure persistence path")

    @unittest.skip(
        "requires real SQL persistence (SQLite/Postgres) for repository writes"
    )
    def test_mrr_calculation_persistence(self) -> None:
        self.skipTest("infrastructure persistence path")


if __name__ == "__main__":
    unittest.main()
