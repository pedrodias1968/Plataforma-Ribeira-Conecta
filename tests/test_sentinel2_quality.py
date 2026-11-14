"""Unit tests for ribeira_platform.sentinel2_quality.

Covers the pure, deterministic Sentinel-2 Scene Classification Layer (SCL)
policy: the frozen policy configuration, the ``accepts`` masking helper and the
``record`` provenance snapshot. No database, network or external provider is
required; ``accepts`` only uses NumPy over in-memory arrays. The policy is a
plain value object, so no infrastructure paths need to be skipped.
"""

from __future__ import annotations

import dataclasses
import unittest

import numpy as np

from ribeira_platform.sentinel2_quality import Sentinel2QualityPolicy


class PolicyDefaultsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = Sentinel2QualityPolicy()

    def test_default_identity(self) -> None:
        self.assertEqual(self.policy.policy_id, "SENTINEL2_SCL_CONSERVATIVE_V1")
        self.assertEqual(self.policy.version, 1)

    def test_default_asset_key(self) -> None:
        self.assertEqual(self.policy.scl_asset_key, "SCL_20m")

    def test_default_accepted_classes(self) -> None:
        self.assertEqual(self.policy.accepted_classes, (4, 5, 6))

    def test_default_excluded_classes(self) -> None:
        self.assertEqual(
            self.policy.excluded_classes, (0, 1, 2, 3, 7, 8, 9, 10, 11)
        )

    def test_default_optional_classes(self) -> None:
        self.assertEqual(self.policy.optional_classes, (7,))

    def test_accepted_and_excluded_are_disjoint(self) -> None:
        overlap = set(self.policy.accepted_classes) & set(
            self.policy.excluded_classes
        )
        self.assertEqual(overlap, set())

    def test_optional_classes_are_a_subset_of_excluded(self) -> None:
        self.assertTrue(
            set(self.policy.optional_classes).issubset(
                set(self.policy.excluded_classes)
            )
        )


class PolicyValueObjectTests(unittest.TestCase):
    def test_is_frozen(self) -> None:
        policy = Sentinel2QualityPolicy()
        with self.assertRaises(dataclasses.FrozenInstanceError):
            policy.version = 2  # type: ignore[misc]

    def test_equal_instances_compare_equal(self) -> None:
        self.assertEqual(Sentinel2QualityPolicy(), Sentinel2QualityPolicy())

    def test_custom_override_is_preserved(self) -> None:
        policy = Sentinel2QualityPolicy(
            policy_id="CUSTOM",
            version=3,
            accepted_classes=(4,),
            excluded_classes=(0, 1, 2, 3, 5, 6, 7, 8, 9, 10, 11),
            optional_classes=(),
            scl_asset_key="SCL_10m",
        )
        self.assertEqual(policy.policy_id, "CUSTOM")
        self.assertEqual(policy.version, 3)
        self.assertEqual(policy.accepted_classes, (4,))
        self.assertEqual(policy.optional_classes, ())
        self.assertEqual(policy.scl_asset_key, "SCL_10m")


class AcceptsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = Sentinel2QualityPolicy()

    def test_accepts_array_of_accepted_classes(self) -> None:
        values = np.array([[4, 5, 6], [4, 5, 6]], dtype="uint8")
        mask = self.policy.accepts(values)
        self.assertTrue(mask.all())
        self.assertEqual(mask.shape, values.shape)

    def test_rejects_array_of_excluded_classes(self) -> None:
        values = np.array([[0, 1, 2, 3], [7, 8, 9, 10]], dtype="uint8")
        mask = self.policy.accepts(values)
        self.assertFalse(mask.any())

    def test_mixed_array_selects_only_accepted_classes(self) -> None:
        values = np.array([4, 0, 5, 7, 6, 11], dtype="uint8")
        mask = self.policy.accepts(values)
        np.testing.assert_array_equal(
            mask, np.array([True, False, True, False, True, False])
        )

    def test_accepts_scalar_value(self) -> None:
        self.assertTrue(bool(self.policy.accepts(np.uint8(4))))
        self.assertFalse(bool(self.policy.accepts(np.uint8(3))))

    def test_accepts_empty_array(self) -> None:
        mask = self.policy.accepts(np.array([], dtype="uint8"))
        self.assertEqual(mask.size, 0)
        self.assertFalse(mask.any())

    def test_accepts_returns_boolean_mask(self) -> None:
        mask = self.policy.accepts(np.array([4, 5, 6], dtype="uint8"))
        self.assertEqual(mask.dtype, np.bool_)

    def test_custom_policy_changes_acceptance(self) -> None:
        policy = Sentinel2QualityPolicy(
            accepted_classes=(4,),
            excluded_classes=(5, 6),
        )
        mask = policy.accepts(np.array([4, 5, 6], dtype="uint8"))
        np.testing.assert_array_equal(
            mask, np.array([True, False, False])
        )


class RecordTests(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = Sentinel2QualityPolicy()
        self.record = self.policy.record()

    def test_record_is_a_dict(self) -> None:
        self.assertIsInstance(self.record, dict)

    def test_record_reports_identity(self) -> None:
        self.assertEqual(
            self.record["policy_id"], "SENTINEL2_SCL_CONSERVATIVE_V1"
        )
        self.assertEqual(self.record["version"], 1)
        self.assertEqual(self.record["scl_asset_key"], "SCL_20m")

    def test_record_serializes_class_tuples_as_lists(self) -> None:
        self.assertEqual(self.record["accepted_classes"], [4, 5, 6])
        self.assertEqual(
            self.record["excluded_classes"],
            [0, 1, 2, 3, 7, 8, 9, 10, 11],
        )
        self.assertEqual(self.record["optional_policy_dependent_classes"], [7])

    def test_record_values_are_plain_lists(self) -> None:
        for key in (
            "accepted_classes",
            "excluded_classes",
            "optional_policy_dependent_classes",
        ):
            self.assertIsInstance(self.record[key], list)

    def test_record_matches_policy_configuration(self) -> None:
        self.assertEqual(
            self.record["accepted_classes"],
            list(self.policy.accepted_classes),
        )
        self.assertEqual(
            self.record["excluded_classes"],
            list(self.policy.excluded_classes),
        )

    def test_record_reflects_custom_policy(self) -> None:
        policy = Sentinel2QualityPolicy(
            policy_id="CUSTOM",
            version=2,
            accepted_classes=(4,),
            excluded_classes=(5,),
            optional_classes=(),
        )
        record = policy.record()
        self.assertEqual(record["policy_id"], "CUSTOM")
        self.assertEqual(record["version"], 2)
        self.assertEqual(record["accepted_classes"], [4])
        self.assertEqual(record["excluded_classes"], [5])
        self.assertEqual(record["optional_policy_dependent_classes"], [])


if __name__ == "__main__":
    unittest.main()
