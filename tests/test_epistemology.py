"""Unit tests for ribeira_platform.epistemology.

Covers the pure evidence/quality enumeration layer only. No database, network
or external provider is required: every case here is deterministic and local.
"""

from __future__ import annotations

import unittest

from ribeira_platform.epistemology import (
    DataClassification,
    DecisionStatus,
    IngestionStatus,
    QualityFlag,
    RuleAuthority,
)


class DataClassificationTests(unittest.TestCase):
    def test_members_have_exact_expected_values(self) -> None:
        self.assertEqual(
            {member.name: member.value for member in DataClassification},
            {
                "OBSERVED": "OBSERVED",
                "OFFICIAL_SOURCE": "OFFICIAL_SOURCE",
                "MANUAL_CONFIRMED": "MANUAL_CONFIRMED",
                "CALCULATED": "CALCULATED",
                "DERIVED": "DERIVED",
                "INFERRED": "INFERRED",
                "PREDICTED": "PREDICTED",
                "ASSUMPTION": "ASSUMPTION",
                "SIMULATED": "SIMULATED",
                "UNKNOWN": "UNKNOWN",
                "CONFLICTING": "CONFLICTING",
            },
        )

    def test_member_count_is_preserved(self) -> None:
        self.assertEqual(len(DataClassification), 11)

    def test_str_enum_is_usable_as_string(self) -> None:
        self.assertIsInstance(DataClassification.OBSERVED, str)
        self.assertEqual(str(DataClassification.OBSERVED), "OBSERVED")
        self.assertEqual(DataClassification.OBSERVED, "OBSERVED")

    def test_lookup_by_value_round_trips(self) -> None:
        for member in DataClassification:
            self.assertIs(DataClassification(member.value), member)

    def test_unknown_value_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            DataClassification("NOT_A_CLASSIFICATION")


class QualityFlagTests(unittest.TestCase):
    def test_members_have_exact_expected_values(self) -> None:
        self.assertEqual(
            {member.name: member.value for member in QualityFlag},
            {
                "VALID": "VALID",
                "INVALID": "INVALID",
                "STALE": "STALE",
                "UNKNOWN": "UNKNOWN",
                "SOURCE_UNAVAILABLE": "SOURCE_UNAVAILABLE",
                "INVALID_PAYLOAD": "INVALID_PAYLOAD",
                "CONFLICTING": "CONFLICTING",
            },
        )

    def test_member_count_is_preserved(self) -> None:
        self.assertEqual(len(QualityFlag), 7)

    def test_lookup_by_value_round_trips(self) -> None:
        for member in QualityFlag:
            self.assertIs(QualityFlag(member.value), member)

    def test_unknown_value_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            QualityFlag("NOT_A_FLAG")


class IngestionStatusTests(unittest.TestCase):
    def test_members_have_exact_expected_values(self) -> None:
        self.assertEqual(
            {member.name: member.value for member in IngestionStatus},
            {
                "INGESTED": "INGESTED",
                "SOURCE_UNAVAILABLE": "SOURCE_UNAVAILABLE",
                "INVALID_PAYLOAD": "INVALID_PAYLOAD",
                "PARTIAL": "PARTIAL",
            },
        )

    def test_member_count_is_preserved(self) -> None:
        self.assertEqual(len(IngestionStatus), 4)

    def test_lookup_by_value_round_trips(self) -> None:
        for member in IngestionStatus:
            self.assertIs(IngestionStatus(member.value), member)

    def test_unknown_value_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            IngestionStatus("NOT_A_STATUS")


class DecisionStatusTests(unittest.TestCase):
    def test_members_have_exact_expected_values(self) -> None:
        self.assertEqual(
            {member.name: member.value for member in DecisionStatus},
            {
                "ACTIONABLE": "ACTIONABLE",
                "INCONCLUSIVE": "INCONCLUSIVE",
                "CONFLICTING": "CONFLICTING",
                "NO_TRIGGER": "NO_TRIGGER",
            },
        )

    def test_member_count_is_preserved(self) -> None:
        self.assertEqual(len(DecisionStatus), 4)

    def test_lookup_by_value_round_trips(self) -> None:
        for member in DecisionStatus:
            self.assertIs(DecisionStatus(member.value), member)

    def test_unknown_value_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            DecisionStatus("NOT_A_DECISION")


class RuleAuthorityTests(unittest.TestCase):
    def test_members_have_exact_expected_values(self) -> None:
        self.assertEqual(
            {member.name: member.value for member in RuleAuthority},
            {
                "REGRA_RIBEIRA": "REGRA_RIBEIRA",
                "REGRA_CLIENTE": "REGRA_CLIENTE",
                "REGRA_REGULATORIA": "REGRA_REGULATORIA",
                "REGRA_AGRONOMICA": "REGRA_AGRONOMICA",
                "REGRA_TECNICA": "REGRA_TECNICA",
                "REGRA_MODELO": "REGRA_MODELO",
                "REGRA_COMERCIAL": "REGRA_COMERCIAL",
            },
        )

    def test_member_count_is_preserved(self) -> None:
        self.assertEqual(len(RuleAuthority), 7)

    def test_lookup_by_value_round_trips(self) -> None:
        for member in RuleAuthority:
            self.assertIs(RuleAuthority(member.value), member)

    def test_unknown_value_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            RuleAuthority("NOT_AN_AUTHORITY")


class EnumIdentityTests(unittest.TestCase):
    def test_distinct_enum_types_do_not_collide(self) -> None:
        self.assertNotIsInstance(DataClassification.UNKNOWN, QualityFlag)
        self.assertNotIsInstance(QualityFlag.UNKNOWN, DataClassification)
        self.assertIsNot(DataClassification.UNKNOWN, QualityFlag.UNKNOWN)

    def test_members_are_hashable_and_unique_per_type(self) -> None:
        for enum_type in (
            DataClassification,
            QualityFlag,
            IngestionStatus,
            DecisionStatus,
            RuleAuthority,
        ):
            self.assertEqual(len(set(enum_type)), len(enum_type))


if __name__ == "__main__":
    unittest.main()
