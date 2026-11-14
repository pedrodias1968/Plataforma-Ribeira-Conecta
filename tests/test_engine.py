"""Unit tests for ribeira_platform.engine.

Covers the deterministic decision logic only. No database, network or external
provider is required: the storage collaborator is replaced with a local fake so
every case is deterministic. Real SQLiteStore persistence is covered by the
integration suite and is explicitly skipped here.
"""

from __future__ import annotations

import unittest

from ribeira_platform.engine import DecisionEngine, EvidenceEngine
from ribeira_platform.epistemology import (
    DataClassification,
    DecisionStatus,
    QualityFlag,
    RuleAuthority,
)
from ribeira_platform.models import (
    Action,
    Alert,
    Decision,
    Evidence,
    Observation,
    Property,
    RuleDefinition,
)

TENANT = "tenant-engine"
PROPERTY_ID = "property-engine"
PROPERTY = Property(id=PROPERTY_ID, tenant_id=TENANT, name="Fazenda Engine")


def make_rule(
    *,
    rule_id: str = "rule-1",
    version: int = 1,
    metric: str = "soil_moisture",
    operator: str = "<",
    threshold: float = 0.3,
    severity: str = "HIGH",
    scope_type: str = "TENANT",
    scope_customer_id: str | None = None,
) -> RuleDefinition:
    return RuleDefinition(
        id=rule_id,
        tenant_id=TENANT,
        version=version,
        name="Rule " + rule_id,
        authority=RuleAuthority.REGRA_RIBEIRA,
        metric=metric,
        operator=operator,
        threshold=threshold,
        unit="unit",
        severity=severity,
        status="ACTIVE",
        approved_by="agronomist",
        valid_from="2026-01-01T00:00:00+00:00",
        scope_type=scope_type,
        scope_customer_id=scope_customer_id,
    )


def make_observation(
    *,
    observation_id: str = "observation-1",
    value: float | None = 0.2,
    metric: str = "soil_moisture",
    quality_flag: QualityFlag = QualityFlag.VALID,
    observation_timestamp: str = "2026-09-11T10:00:00+00:00",
    classification: DataClassification = DataClassification.OBSERVED,
) -> Observation:
    return Observation(
        id=observation_id,
        tenant_id=TENANT,
        property_id=PROPERTY_ID,
        source_id="source-1",
        metric=metric,
        value=value,
        unit="unit",
        observation_timestamp=observation_timestamp,
        classification=classification,
        quality_flag=quality_flag,
    )


class FakeStore:
    """Minimal in-memory collaborator exposing only the methods engine uses."""

    def __init__(
        self,
        *,
        observations: list[Observation] | None = None,
        rules: list[RuleDefinition] | None = None,
        evidence_by_reference: dict[tuple[str, str], Evidence] | None = None,
    ) -> None:
        self.observations = list(observations or [])
        self.rules = list(rules or [])
        self.evidence_by_reference = dict(evidence_by_reference or {})
        self.created_evidence: list[Evidence] = []
        self.created_decisions: list[Decision] = []
        self.created_alerts: list[Alert] = []
        self.created_actions: list[Action] = []
        self.audits: list[dict[str, object]] = []
        self.active_rules_calls: list[
            tuple[str, str, str | None, str | None, str | None]
        ] = []

    def observations_for_property(
        self, tenant_id: str, property_id: str
    ) -> list[Observation]:
        return [
            item
            for item in self.observations
            if item.tenant_id == tenant_id and item.property_id == property_id
        ]

    def evidence_for_reference(
        self, tenant_id: str, reference_id: str
    ) -> Evidence | None:
        return self.evidence_by_reference.get((tenant_id, reference_id))

    def create_evidence(self, item: Evidence) -> Evidence:
        self.created_evidence.append(item)
        self.evidence_by_reference[(item.tenant_id, item.reference_id)] = item
        return item

    def active_rules(
        self,
        tenant_id: str,
        metric: str,
        property_id: str | None = None,
        asset_id: str | None = None,
        field_id: str | None = None,
    ) -> list[RuleDefinition]:
        self.active_rules_calls.append(
            (tenant_id, metric, property_id, asset_id, field_id)
        )
        return list(self.rules)

    def create_decision(self, item: Decision) -> Decision:
        self.created_decisions.append(item)
        return item

    def create_alert(self, item: Alert) -> Alert:
        self.created_alerts.append(item)
        return item

    def create_action(self, item: Action) -> Action:
        self.created_actions.append(item)
        return item

    def audit(
        self,
        tenant_id: str,
        actor: str,
        event_type: str,
        entity_type: str,
        entity_id: str,
        payload: dict[str, object],
        event_id: str,
        created_at: str,
    ) -> None:
        self.audits.append(
            {
                "tenant_id": tenant_id,
                "actor": actor,
                "event_type": event_type,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "payload": payload,
                "event_id": event_id,
                "created_at": created_at,
            }
        )


class MatchesOperatorTests(unittest.TestCase):
    def test_less_than(self) -> None:
        rule = make_rule(operator="<", threshold=1.0)
        self.assertTrue(DecisionEngine._matches(rule, 0.5))
        self.assertFalse(DecisionEngine._matches(rule, 1.0))
        self.assertFalse(DecisionEngine._matches(rule, 2.0))

    def test_less_than_or_equal(self) -> None:
        rule = make_rule(operator="<=", threshold=1.0)
        self.assertTrue(DecisionEngine._matches(rule, 1.0))
        self.assertFalse(DecisionEngine._matches(rule, 1.1))

    def test_greater_than(self) -> None:
        rule = make_rule(operator=">", threshold=1.0)
        self.assertTrue(DecisionEngine._matches(rule, 2.0))
        self.assertFalse(DecisionEngine._matches(rule, 1.0))

    def test_greater_than_or_equal(self) -> None:
        rule = make_rule(operator=">=", threshold=1.0)
        self.assertTrue(DecisionEngine._matches(rule, 1.0))
        self.assertFalse(DecisionEngine._matches(rule, 0.9))

    def test_equal(self) -> None:
        rule = make_rule(operator="==", threshold=1.0)
        self.assertTrue(DecisionEngine._matches(rule, 1.0))
        self.assertFalse(DecisionEngine._matches(rule, 1.0001))

    def test_unsupported_operator_raises_value_error(self) -> None:
        with self.assertRaisesRegex(ValueError, "unsupported operator: !="):
            DecisionEngine._matches(make_rule(operator="!="), 1.0)


class EvidenceEngineTests(unittest.TestCase):
    def test_creates_observation_evidence_with_provenance(self) -> None:
        store = FakeStore()
        engine = EvidenceEngine(store)
        observation = make_observation(
            classification=DataClassification.OFFICIAL_SOURCE
        )

        evidence = engine.evidence_for_observation(observation)

        self.assertEqual(len(store.created_evidence), 1)
        self.assertIs(store.created_evidence[0], evidence)
        self.assertTrue(evidence.id)
        self.assertEqual(evidence.tenant_id, TENANT)
        self.assertEqual(evidence.evidence_type, "OBSERVATION")
        self.assertEqual(evidence.reference_id, observation.id)
        self.assertEqual(evidence.classification, DataClassification.OFFICIAL_SOURCE)
        self.assertEqual(evidence.source_id, "source-1")
        self.assertEqual(evidence.observed_at, observation.observation_timestamp)
        self.assertEqual(
            evidence.transformation,
            "canonical observation persisted without imputation",
        )
        self.assertEqual(
            evidence.limitations,
            ["sensor/source quality is not independently validated by this slice"],
        )

    def test_reuses_existing_evidence_for_same_reference(self) -> None:
        observation = make_observation()
        existing = Evidence(
            id="existing-evidence",
            tenant_id=TENANT,
            evidence_type="OBSERVATION",
            reference_id=observation.id,
            classification=DataClassification.OBSERVED,
            source_id="source-1",
            observed_at=observation.observation_timestamp,
        )
        store = FakeStore(evidence_by_reference={(TENANT, observation.id): existing})
        engine = EvidenceEngine(store)

        evidence = engine.evidence_for_observation(observation)

        self.assertIs(evidence, existing)
        self.assertEqual(store.created_evidence, [])

    def test_repeated_calls_return_same_created_evidence(self) -> None:
        store = FakeStore()
        engine = EvidenceEngine(store)
        observation = make_observation()

        first = engine.evidence_for_observation(observation)
        second = engine.evidence_for_observation(observation)

        self.assertIs(first, second)
        self.assertEqual(len(store.created_evidence), 1)


class TemporalDeltaInvalidInputTests(unittest.TestCase):
    def _assert_inconclusive_provenance(self, result, evidence_id: str | None) -> None:
        decision = result.decision
        self.assertEqual(decision.tenant_id, TENANT)
        self.assertEqual(decision.property_id, PROPERTY_ID)
        self.assertEqual(decision.classification, DataClassification.UNKNOWN)
        self.assertEqual(decision.status, DecisionStatus.INCONCLUSIVE)
        self.assertEqual(
            decision.conclusion,
            "O delta temporal de NDVI não possui proveniência válida para avaliação.",
        )
        expected = [evidence_id] if evidence_id is not None else []
        self.assertEqual(decision.evidence_ids, expected)
        self.assertIsNone(decision.rule_id)
        self.assertIsNone(decision.rule_version)
        self.assertEqual(
            decision.missing_data, ["valid_ndvi_temporal_delta_provenance"]
        )
        self.assertEqual(
            decision.limitations,
            [
                "delta temporal sem proveniência completa não pode acionar recomendação operacional"
            ],
        )
        self.assertIsNone(result.alert)
        self.assertIsNone(result.action)

    def test_invalid_provenance_is_inconclusive(self) -> None:
        store = FakeStore()
        engine = DecisionEngine(store)

        result = engine.evaluate_temporal_delta(
            TENANT, PROPERTY, "product-1", 0.5, "evidence-1", False
        )

        self._assert_inconclusive_provenance(result, "evidence-1")
        self.assertEqual(store.active_rules_calls, [])
        self.assertEqual(len(store.created_decisions), 1)
        self.assertEqual(
            store.audits[0]["payload"]["reason"],
            "derived_product_provenance_invalid",
        )

    def test_missing_mean_delta_is_inconclusive(self) -> None:
        store = FakeStore()
        engine = DecisionEngine(store)

        result = engine.evaluate_temporal_delta(
            TENANT, PROPERTY, "product-1", None, None, True
        )

        self._assert_inconclusive_provenance(result, None)
        self.assertEqual(store.active_rules_calls, [])
        self.assertEqual(len(store.created_decisions), 1)


class TemporalDeltaRuleSelectionTests(unittest.TestCase):
    metric = "ndvi_temporal_delta_mean"

    def test_missing_rule_is_inconclusive(self) -> None:
        store = FakeStore(rules=[])
        engine = DecisionEngine(store)

        result = engine.evaluate_temporal_delta(
            TENANT, PROPERTY, "product-1", 0.5, "evidence-1", True
        )

        decision = result.decision
        self.assertEqual(decision.classification, DataClassification.UNKNOWN)
        self.assertEqual(decision.status, DecisionStatus.INCONCLUSIVE)
        self.assertEqual(
            decision.conclusion,
            "Não há regra ativa versionada para avaliar a média do delta temporal de NDVI.",
        )
        self.assertEqual(decision.missing_data, ["active_rule:" + self.metric])
        self.assertIsNone(decision.rule_id)
        self.assertIsNone(result.alert)
        self.assertIsNone(result.action)
        self.assertEqual(store.audits[0]["payload"]["reason"], "rule_missing")
        self.assertEqual(
            store.active_rules_calls,
            [(TENANT, self.metric, PROPERTY_ID, None, None)],
        )

    def test_asset_scope_is_rejected(self) -> None:
        store = FakeStore(rules=[make_rule(metric=self.metric, scope_type="ASSET")])
        engine = DecisionEngine(store)

        with self.assertRaisesRegex(
            ValueError,
            "temporal delta evaluation does not support asset or field scope",
        ):
            engine.evaluate_temporal_delta(
                TENANT, PROPERTY, "product-1", 0.5, "evidence-1", True
            )

    def test_equally_specific_rules_are_conflicting(self) -> None:
        rules = [
            make_rule(
                rule_id="property-a",
                version=1,
                metric=self.metric,
                scope_type="PROPERTY",
            ),
            make_rule(
                rule_id="property-b",
                version=2,
                metric=self.metric,
                scope_type="PROPERTY",
            ),
        ]
        store = FakeStore(rules=rules)
        engine = DecisionEngine(store)

        result = engine.evaluate_temporal_delta(
            TENANT, PROPERTY, "product-1", 0.5, "evidence-1", True
        )

        decision = result.decision
        self.assertEqual(decision.classification, DataClassification.CONFLICTING)
        self.assertEqual(decision.status, DecisionStatus.CONFLICTING)
        self.assertEqual(decision.selected_rule_scope_type, "PROPERTY")
        self.assertIsNone(decision.rule_id)
        self.assertEqual(decision.conflicts[0]["type"], "equally_specific_active_rules")
        self.assertEqual(decision.conflicts[0]["scope_type"], "PROPERTY")
        self.assertEqual(
            decision.conflicts[0]["rule_versions"],
            [
                {"rule_id": "property-a", "version": 1},
                {"rule_id": "property-b", "version": 2},
            ],
        )
        self.assertIsNone(result.alert)
        self.assertIsNone(result.action)
        self.assertEqual(store.audits[0]["payload"]["reason"], "rule_ambiguity")

    def test_field_scope_wins_over_property(self) -> None:
        field_rule = make_rule(
            rule_id="field-rule",
            metric=self.metric,
            scope_type="FIELD",
            operator="<",
            threshold=0.4,
        )
        property_rule = make_rule(
            rule_id="property-rule",
            metric=self.metric,
            scope_type="PROPERTY",
            operator="<",
            threshold=0.4,
        )
        store = FakeStore(rules=[property_rule, field_rule])
        engine = DecisionEngine(store)

        result = engine.evaluate_temporal_delta(
            TENANT,
            PROPERTY,
            "product-1",
            0.5,
            "evidence-1",
            True,
            field_id="field-1",
            field_boundary_version=3,
            field_boundary_checksum="checksum-3",
        )

        decision = result.decision
        self.assertEqual(decision.rule_id, "field-rule")
        self.assertEqual(decision.selected_rule_scope_type, "FIELD")
        self.assertEqual(decision.subject_field_id, "field-1")
        self.assertEqual(decision.subject_field_boundary_version, 3)
        self.assertEqual(decision.subject_field_boundary_checksum, "checksum-3")
        self.assertEqual(decision.status, DecisionStatus.NO_TRIGGER)

    def test_field_scope_is_ignored_without_field_context(self) -> None:
        field_rule = make_rule(
            rule_id="field-rule", metric=self.metric, scope_type="FIELD"
        )
        property_rule = make_rule(
            rule_id="property-rule", metric=self.metric, scope_type="PROPERTY"
        )
        store = FakeStore(rules=[field_rule, property_rule])
        engine = DecisionEngine(store)

        result = engine.evaluate_temporal_delta(
            TENANT, PROPERTY, "product-1", 0.5, "evidence-1", True
        )

        self.assertEqual(result.decision.rule_id, "property-rule")

    def test_customer_scope_snapshots_customer_context(self) -> None:
        rule = make_rule(
            metric=self.metric,
            scope_type="CUSTOMER",
            scope_customer_id="customer-1",
            operator="<",
            threshold=0.4,
        )
        store = FakeStore(rules=[rule])
        engine = DecisionEngine(store)

        result = engine.evaluate_temporal_delta(
            TENANT, PROPERTY, "product-1", 0.5, "evidence-1", True
        )

        self.assertEqual(result.decision.selected_rule_scope_type, "CUSTOMER")
        self.assertEqual(result.decision.subject_customer_id, "customer-1")


class TemporalDeltaOutcomeTests(unittest.TestCase):
    metric = "ndvi_temporal_delta_mean"

    def test_triggered_rule_creates_alert_and_action(self) -> None:
        rule = make_rule(
            metric=self.metric, operator="<", threshold=0.5, severity="HIGH"
        )
        store = FakeStore(rules=[rule])
        engine = DecisionEngine(store)

        result = engine.evaluate_temporal_delta(
            TENANT,
            PROPERTY,
            "product-1",
            0.2,
            "evidence-1",
            True,
            actor="agronomist",
        )

        decision = result.decision
        self.assertEqual(decision.classification, DataClassification.DERIVED)
        self.assertEqual(decision.status, DecisionStatus.ACTIONABLE)
        self.assertEqual(decision.rule_id, rule.id)
        self.assertEqual(decision.rule_version, rule.version)
        self.assertEqual(
            decision.conclusion,
            "A média do delta temporal de NDVI atingiu o limiar configurado; "
            "recomenda-se inspeção de campo direcionada, sem inferir diagnóstico.",
        )
        self.assertEqual(
            decision.recommended_action,
            {
                "type": "targeted_field_inspection",
                "automated": False,
                "derived_product_id": "product-1",
                "metric": self.metric,
                "responsible_user_id": None,
                "deadline": None,
            },
        )
        self.assertIsNotNone(result.alert)
        self.assertIsNotNone(result.action)
        assert result.alert is not None
        assert result.action is not None
        self.assertEqual(result.alert.alert_type, "RULE_TRIGGERED")
        self.assertEqual(result.alert.severity, "HIGH")
        self.assertEqual(
            result.alert.title,
            "Delta temporal de NDVI requer inspeção de campo direcionada",
        )
        self.assertEqual(result.alert.decision_id, decision.id)
        self.assertEqual(
            result.action.action_type,
            "targeted field inspection recommendation",
        )
        self.assertEqual(result.action.decision_id, decision.id)
        self.assertEqual(store.audits[0]["payload"]["reason"], "rule_triggered")
        self.assertEqual(store.audits[0]["payload"]["alert_id"], result.alert.id)
        self.assertEqual(store.audits[0]["payload"]["action_id"], result.action.id)

    def test_not_triggered_rule_creates_no_alert_or_action(self) -> None:
        rule = make_rule(metric=self.metric, operator="<", threshold=0.5)
        store = FakeStore(rules=[rule])
        engine = DecisionEngine(store)

        result = engine.evaluate_temporal_delta(
            TENANT, PROPERTY, "product-1", 0.9, "evidence-1", True
        )

        decision = result.decision
        self.assertEqual(decision.classification, DataClassification.DERIVED)
        self.assertEqual(decision.status, DecisionStatus.NO_TRIGGER)
        self.assertEqual(
            decision.conclusion,
            "A média do delta temporal de NDVI não atingiu o limiar configurado.",
        )
        self.assertIsNone(decision.recommended_action)
        self.assertIsNone(result.alert)
        self.assertIsNone(result.action)
        self.assertEqual(store.created_alerts, [])
        self.assertEqual(store.created_actions, [])
        self.assertEqual(store.audits[0]["payload"]["reason"], "rule_not_triggered")


class EvaluateContextEvidenceTests(unittest.TestCase):
    def test_asset_without_evidence_is_inconclusive(self) -> None:
        store = FakeStore(rules=[make_rule()])
        engine = DecisionEngine(store)

        result = engine.evaluate(TENANT, PROPERTY, asset_id="asset-1")

        decision = result.decision
        self.assertEqual(decision.classification, DataClassification.UNKNOWN)
        self.assertEqual(decision.status, DecisionStatus.INCONCLUSIVE)
        self.assertEqual(
            decision.conclusion,
            "Não há evidência de registro disponível para usar o ativo como contexto da regra.",
        )
        self.assertEqual(decision.missing_data, ["asset_registration_evidence"])
        self.assertEqual(decision.subject_asset_id, "asset-1")
        self.assertIn(
            "o ativo é contexto factual de aplicabilidade; não é uma medição",
            decision.limitations,
        )
        self.assertEqual(
            store.audits[0]["payload"]["reason"],
            "asset_context_evidence_missing",
        )
        self.assertEqual(store.active_rules_calls, [])

    def test_field_without_evidence_is_inconclusive(self) -> None:
        store = FakeStore(rules=[make_rule()])
        engine = DecisionEngine(store)

        result = engine.evaluate(
            TENANT,
            PROPERTY,
            field_id="field-1",
            field_boundary_version=2,
            field_boundary_checksum="checksum-2",
        )

        decision = result.decision
        self.assertEqual(decision.classification, DataClassification.UNKNOWN)
        self.assertEqual(decision.status, DecisionStatus.INCONCLUSIVE)
        self.assertEqual(
            decision.conclusion,
            "Não há evidência de registro disponível para usar o talhão como contexto da regra.",
        )
        self.assertEqual(decision.missing_data, ["field_registration_evidence"])
        self.assertEqual(decision.subject_field_id, "field-1")
        self.assertEqual(decision.subject_field_boundary_version, 2)
        self.assertEqual(decision.subject_field_boundary_checksum, "checksum-2")
        self.assertIn(
            "o talhão é contexto operacional não legal; não é evidência de cultura, solo ou diagnóstico",
            decision.limitations,
        )
        self.assertEqual(
            store.audits[0]["payload"]["reason"],
            "field_context_evidence_missing",
        )

    def test_missing_rule_is_inconclusive(self) -> None:
        store = FakeStore(rules=[])
        engine = DecisionEngine(store)

        result = engine.evaluate(TENANT, PROPERTY)

        decision = result.decision
        self.assertEqual(decision.classification, DataClassification.UNKNOWN)
        self.assertEqual(decision.status, DecisionStatus.INCONCLUSIVE)
        self.assertEqual(
            decision.conclusion,
            "Não há regra ativa versionada para avaliar umidade do solo.",
        )
        self.assertEqual(decision.missing_data, ["active_rule:soil_moisture"])
        self.assertIsNone(decision.rule_id)
        self.assertEqual(store.audits[0]["payload"]["reason"], "rule_missing")
        self.assertEqual(
            store.active_rules_calls,
            [(TENANT, "soil_moisture", PROPERTY_ID, None, None)],
        )

    def test_equally_specific_rules_are_conflicting(self) -> None:
        rules = [
            make_rule(rule_id="property-a", version=1, scope_type="PROPERTY"),
            make_rule(rule_id="property-b", version=2, scope_type="PROPERTY"),
        ]
        store = FakeStore(rules=rules)
        engine = DecisionEngine(store)

        result = engine.evaluate(TENANT, PROPERTY)

        decision = result.decision
        self.assertEqual(decision.classification, DataClassification.CONFLICTING)
        self.assertEqual(decision.status, DecisionStatus.CONFLICTING)
        self.assertEqual(decision.selected_rule_scope_type, "PROPERTY")
        self.assertEqual(decision.conflicts[0]["type"], "equally_specific_active_rules")
        self.assertEqual(
            decision.recommended_action,
            {"type": "resolve_rule_conflict", "responsible_user_id": None},
        )
        self.assertIsNone(result.alert)
        self.assertIsNone(result.action)
        self.assertEqual(store.audits[0]["payload"]["reason"], "rule_scope_conflict")

    def test_missing_valid_observation_is_inconclusive(self) -> None:
        store = FakeStore(
            observations=[make_observation(quality_flag=QualityFlag.STALE)],
            rules=[make_rule()],
        )
        engine = DecisionEngine(store)

        result = engine.evaluate(TENANT, PROPERTY)

        decision = result.decision
        self.assertEqual(decision.classification, DataClassification.UNKNOWN)
        self.assertEqual(decision.status, DecisionStatus.INCONCLUSIVE)
        self.assertEqual(
            decision.conclusion,
            "Não há evidência suficiente para avaliar a umidade do solo.",
        )
        self.assertEqual(decision.missing_data, ["soil_moisture observation"])
        self.assertEqual(decision.rule_id, "rule-1")
        self.assertEqual(store.audits[0]["payload"]["reason"], "missing_observation")
        self.assertEqual(store.created_alerts, [])
        self.assertEqual(store.created_actions, [])

    def test_conflicting_observations_create_alert_and_action(self) -> None:
        observations = [
            make_observation(
                observation_id="obs-a",
                value=0.2,
                observation_timestamp="2026-09-11T10:00:00+00:00",
            ),
            make_observation(
                observation_id="obs-b",
                value=0.4,
                observation_timestamp="2026-09-11T10:00:00+00:00",
            ),
        ]
        store = FakeStore(observations=observations, rules=[make_rule()])
        engine = DecisionEngine(store)

        result = engine.evaluate(TENANT, PROPERTY)

        decision = result.decision
        self.assertEqual(decision.classification, DataClassification.CONFLICTING)
        self.assertEqual(decision.status, DecisionStatus.CONFLICTING)
        self.assertEqual(
            decision.conclusion,
            "Conclusão inconclusiva devido a dados conflitantes de umidade do solo.",
        )
        self.assertEqual(decision.rule_id, "rule-1")
        self.assertEqual(
            decision.conflicts[0]["timestamp"], "2026-09-11T10:00:00+00:00"
        )
        self.assertEqual(decision.conflicts[0]["values"], [0.2, 0.4])
        self.assertEqual(decision.conflicts[0]["observation_ids"], ["obs-a", "obs-b"])
        self.assertEqual(
            decision.recommended_action,
            {"type": "resolve_data_conflict", "responsible_user_id": None},
        )
        self.assertIsNotNone(result.alert)
        self.assertIsNotNone(result.action)
        assert result.alert is not None
        assert result.action is not None
        self.assertEqual(result.alert.alert_type, "DATA_CONFLICT")
        self.assertEqual(result.alert.severity, "HIGH")
        self.assertEqual(result.action.action_type, "resolver conflito de dados")
        self.assertEqual(store.audits[0]["payload"]["reason"], "data_conflict")

    def test_triggered_rule_creates_alert_and_action(self) -> None:
        rule = make_rule(operator="<", threshold=0.3, severity="HIGH")
        store = FakeStore(observations=[make_observation(value=0.2)], rules=[rule])
        engine = DecisionEngine(store)

        result = engine.evaluate(TENANT, PROPERTY)

        decision = result.decision
        self.assertEqual(decision.classification, DataClassification.INFERRED)
        self.assertEqual(decision.status, DecisionStatus.ACTIONABLE)
        self.assertEqual(decision.rule_id, rule.id)
        self.assertEqual(decision.rule_version, rule.version)
        self.assertEqual(
            decision.conclusion,
            "Foi observada umidade do solo abaixo do limiar configurado; "
            "isso sugere possível estresse hídrico e requer inspeção.",
        )
        self.assertIn(
            "a observação não determina sozinha a causa agronômica",
            decision.limitations,
        )
        self.assertIn(
            "satélite ou sensor isolado não confirma doença",
            decision.limitations,
        )
        self.assertEqual(
            decision.recommended_action,
            {
                "type": "field_inspection",
                "responsible_user_id": None,
                "deadline": None,
            },
        )
        self.assertIsNotNone(result.alert)
        self.assertIsNotNone(result.action)
        assert result.alert is not None
        assert result.action is not None
        self.assertEqual(result.alert.alert_type, "RULE_TRIGGERED")
        self.assertEqual(result.alert.severity, "HIGH")
        self.assertEqual(
            result.alert.title,
            "Possível estresse hídrico: inspeção recomendada",
        )
        self.assertEqual(result.action.action_type, "inspeção de campo")
        self.assertEqual(store.audits[0]["payload"]["reason"], "rule_triggered")

    def test_not_triggered_rule_creates_no_alert_or_action(self) -> None:
        rule = make_rule(operator="<", threshold=0.3)
        store = FakeStore(observations=[make_observation(value=0.9)], rules=[rule])
        engine = DecisionEngine(store)

        result = engine.evaluate(TENANT, PROPERTY)

        decision = result.decision
        self.assertEqual(decision.classification, DataClassification.CALCULATED)
        self.assertEqual(decision.status, DecisionStatus.NO_TRIGGER)
        self.assertEqual(
            decision.conclusion,
            "A medição mais recente não acionou o limiar da regra ativa.",
        )
        self.assertIsNone(decision.recommended_action)
        self.assertIsNone(result.alert)
        self.assertIsNone(result.action)
        self.assertEqual(store.created_alerts, [])
        self.assertEqual(store.created_actions, [])
        self.assertEqual(store.audits[0]["payload"]["reason"], "rule_not_triggered")

    def test_uses_latest_observation_by_timestamp(self) -> None:
        observations = [
            make_observation(
                observation_id="old",
                value=0.1,
                observation_timestamp="2026-09-11T09:00:00+00:00",
            ),
            make_observation(
                observation_id="new",
                value=0.9,
                observation_timestamp="2026-09-11T11:00:00+00:00",
            ),
        ]
        rule = make_rule(operator="<", threshold=0.3)
        store = FakeStore(observations=observations, rules=[rule])
        engine = DecisionEngine(store)

        result = engine.evaluate(TENANT, PROPERTY)

        self.assertEqual(result.decision.status, DecisionStatus.NO_TRIGGER)


class EvaluateContextEvidenceExtensionsTests(unittest.TestCase):
    def test_asset_evidence_enables_asset_context(self) -> None:
        store = FakeStore(
            observations=[make_observation(value=0.2)],
            rules=[make_rule()],
        )
        engine = DecisionEngine(store)

        result = engine.evaluate(
            TENANT,
            PROPERTY,
            asset_id="asset-1",
            asset_evidence_id="asset-evidence-1",
        )

        decision = result.decision
        self.assertEqual(decision.status, DecisionStatus.ACTIONABLE)
        self.assertEqual(decision.subject_asset_id, "asset-1")
        self.assertIn("asset-evidence-1", decision.evidence_ids)
        self.assertEqual(decision.evidence_ids[-1], "asset-evidence-1")
        self.assertIn(
            "o ativo é contexto factual de aplicabilidade; não é uma medição",
            decision.limitations,
        )
        self.assertEqual(
            store.active_rules_calls,
            [(TENANT, "soil_moisture", PROPERTY_ID, "asset-1", None)],
        )

    def test_asset_scope_rule_wins_over_property(self) -> None:
        rules = [
            make_rule(
                rule_id="property-rule",
                scope_type="PROPERTY",
                operator="<",
                threshold=0.3,
            ),
            make_rule(
                rule_id="asset-rule",
                scope_type="ASSET",
                operator="<",
                threshold=0.3,
            ),
        ]
        store = FakeStore(observations=[make_observation(value=0.2)], rules=rules)
        engine = DecisionEngine(store)

        result = engine.evaluate(
            TENANT,
            PROPERTY,
            asset_id="asset-1",
            asset_evidence_id="asset-evidence-1",
        )

        self.assertEqual(result.decision.rule_id, "asset-rule")
        self.assertEqual(result.decision.selected_rule_scope_type, "ASSET")

    def test_field_evidence_enables_field_context(self) -> None:
        store = FakeStore(
            observations=[make_observation(value=0.2)],
            rules=[make_rule()],
        )
        engine = DecisionEngine(store)

        result = engine.evaluate(
            TENANT,
            PROPERTY,
            field_id="field-1",
            field_evidence_id="field-evidence-1",
            field_boundary_version=4,
            field_boundary_checksum="checksum-4",
        )

        decision = result.decision
        self.assertEqual(decision.subject_field_id, "field-1")
        self.assertEqual(decision.subject_field_boundary_version, 4)
        self.assertEqual(decision.subject_field_boundary_checksum, "checksum-4")
        self.assertIn("field-evidence-1", decision.evidence_ids)
        self.assertIn(
            "o talhão é contexto operacional não legal; "
            "não é evidência de cultura, solo ou diagnóstico",
            decision.limitations,
        )
        self.assertEqual(
            store.active_rules_calls,
            [(TENANT, "soil_moisture", PROPERTY_ID, None, "field-1")],
        )

    def test_asset_and_field_context_limitations_are_both_recorded(self) -> None:
        store = FakeStore(
            observations=[make_observation(value=0.2)],
            rules=[make_rule()],
        )
        engine = DecisionEngine(store)

        result = engine.evaluate(
            TENANT,
            PROPERTY,
            asset_id="asset-1",
            asset_evidence_id="asset-evidence-1",
            field_id="field-1",
            field_evidence_id="field-evidence-1",
        )

        decision = result.decision
        self.assertEqual(decision.subject_asset_id, "asset-1")
        self.assertEqual(decision.subject_field_id, "field-1")
        self.assertIn(
            "o ativo é contexto factual de aplicabilidade; não é uma medição",
            decision.limitations,
        )
        self.assertIn(
            "o talhão é contexto operacional não legal; "
            "não é evidência de cultura, solo ou diagnóstico",
            decision.limitations,
        )

    def test_no_observations_yields_empty_evidence_ids(self) -> None:
        store = FakeStore(rules=[make_rule()])
        engine = DecisionEngine(store)

        result = engine.evaluate(TENANT, PROPERTY)

        decision = result.decision
        self.assertEqual(decision.evidence_ids, [])
        self.assertEqual(decision.missing_data, ["soil_moisture observation"])
        self.assertEqual(decision.rule_id, "rule-1")
        self.assertEqual(store.audits[0]["payload"]["reason"], "missing_observation")


class EvaluateObservationEdgeCaseTests(unittest.TestCase):
    def test_same_timestamp_same_value_is_not_a_conflict(self) -> None:
        observations = [
            make_observation(
                observation_id="obs-a",
                value=0.9,
                observation_timestamp="2026-09-11T10:00:00+00:00",
            ),
            make_observation(
                observation_id="obs-b",
                value=0.9,
                observation_timestamp="2026-09-11T10:00:00+00:00",
            ),
        ]
        store = FakeStore(observations=observations, rules=[make_rule()])
        engine = DecisionEngine(store)

        result = engine.evaluate(TENANT, PROPERTY)

        self.assertEqual(result.decision.status, DecisionStatus.NO_TRIGGER)
        self.assertEqual(result.decision.conflicts, [])
        self.assertIsNone(result.alert)
        self.assertIsNone(result.action)

    def test_null_value_observation_is_ignored(self) -> None:
        store = FakeStore(
            observations=[make_observation(value=None)], rules=[make_rule()]
        )
        engine = DecisionEngine(store)

        result = engine.evaluate(TENANT, PROPERTY)

        decision = result.decision
        self.assertEqual(decision.status, DecisionStatus.INCONCLUSIVE)
        self.assertEqual(
            decision.conclusion,
            "Não há evidência suficiente para avaliar a umidade do solo.",
        )
        self.assertEqual(decision.rule_id, "rule-1")
        self.assertEqual(decision.evidence_ids, [])

    def test_customer_scope_conflict_snapshots_single_customer(self) -> None:
        rules = [
            make_rule(
                rule_id="customer-a",
                version=1,
                scope_type="CUSTOMER",
                scope_customer_id="customer-1",
            ),
            make_rule(
                rule_id="customer-b",
                version=2,
                scope_type="CUSTOMER",
                scope_customer_id="customer-1",
            ),
        ]
        store = FakeStore(rules=rules)
        engine = DecisionEngine(store)

        result = engine.evaluate(TENANT, PROPERTY)

        decision = result.decision
        self.assertEqual(decision.status, DecisionStatus.CONFLICTING)
        self.assertEqual(decision.selected_rule_scope_type, "CUSTOMER")
        self.assertEqual(decision.subject_customer_id, "customer-1")

    def test_customer_scope_conflict_with_distinct_customers_is_not_snapshotted(
        self,
    ) -> None:
        rules = [
            make_rule(
                rule_id="customer-a",
                version=1,
                scope_type="CUSTOMER",
                scope_customer_id="customer-1",
            ),
            make_rule(
                rule_id="customer-b",
                version=2,
                scope_type="CUSTOMER",
                scope_customer_id="customer-2",
            ),
        ]
        store = FakeStore(rules=rules)
        engine = DecisionEngine(store)

        result = engine.evaluate(TENANT, PROPERTY)

        self.assertEqual(result.decision.status, DecisionStatus.CONFLICTING)
        self.assertIsNone(result.decision.subject_customer_id)

    def test_audit_records_actor_status_and_rule(self) -> None:
        store = FakeStore(
            observations=[make_observation(value=0.2)], rules=[make_rule()]
        )
        engine = DecisionEngine(store)

        engine.evaluate(TENANT, PROPERTY, actor="agronomist")

        audit = store.audits[0]
        self.assertEqual(audit["actor"], "agronomist")
        self.assertEqual(audit["event_type"], "DECISION_CREATED")
        self.assertEqual(audit["entity_type"], "decision")
        self.assertEqual(audit["payload"]["status"], DecisionStatus.ACTIONABLE.value)
        self.assertEqual(audit["payload"]["rule_id"], "rule-1")
        self.assertIsNone(audit["payload"]["subject_asset_id"])
        self.assertIsNone(audit["payload"]["subject_field_id"])


class InfrastructureBoundTests(unittest.TestCase):
    @unittest.skip("requires SQLiteStore persistence; covered by integration tests")
    def test_real_store_persistence(self) -> None:
        pass


if __name__ == "__main__":
    unittest.main()
