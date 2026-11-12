"""Unit tests for the Smart Soil Sampling pure domain model.

Evidence First: management zones are derived geometry (not legal/cadastral
boundaries) and suggested sample points are DERIVED_LOCATION (not measurements).
These tests intentionally do not assert any agronomic rule.
"""

from __future__ import annotations

import unittest

from ribeira_platform.epistemology import DataClassification
from ribeira_platform.sampling import (
    ManagementZone,
    SamplingValidationError,
    SuggestedSamplePoint,
    validate_management_zone,
)


POLYGON_GEOJSON = {
    "type": "Polygon",
    "coordinates": [
        [
            [-46.995, -24.005],
            [-46.985, -24.005],
            [-46.985, -24.015],
            [-46.995, -24.015],
            [-46.995, -24.005],
        ]
    ],
}

MULTIPOLYGON_GEOJSON = {
    "type": "MultiPolygon",
    "coordinates": [
        [
            [
                [-46.995, -24.005],
                [-46.985, -24.005],
                [-46.985, -24.015],
                [-46.995, -24.015],
                [-46.995, -24.005],
            ]
        ]
    ],
}

POINT_GEOJSON = {"type": "Point", "coordinates": [-46.99, -24.01]}


class ValidateManagementZoneTest(unittest.TestCase):
    def test_accepts_valid_polygon(self) -> None:
        validate_management_zone(POLYGON_GEOJSON, "TERRAIN_VARIABILITY", ("dem",))

    def test_accepts_valid_multipolygon(self) -> None:
        validate_management_zone(
            MULTIPOLYGON_GEOJSON, "TERRAIN_VARIABILITY", ("dem",)
        )

    def test_rejects_non_dict_geometry(self) -> None:
        with self.assertRaises(SamplingValidationError):
            validate_management_zone(None, "METHOD", ("dem",))  # type: ignore[arg-type]

    def test_rejects_wrong_geometry_type(self) -> None:
        with self.assertRaises(SamplingValidationError):
            validate_management_zone(POINT_GEOJSON, "METHOD", ("dem",))

    def test_rejects_empty_coordinates(self) -> None:
        with self.assertRaises(SamplingValidationError):
            validate_management_zone(
                {"type": "Polygon", "coordinates": []}, "METHOD", ("dem",)
            )

    def test_rejects_empty_geometry(self) -> None:
        with self.assertRaises(SamplingValidationError):
            validate_management_zone(
                {"type": "Polygon", "coordinates": [[]]}, "METHOD", ("dem",)
            )

    def test_rejects_invalid_geometry_payload(self) -> None:
        with self.assertRaises(SamplingValidationError):
            validate_management_zone(
                {"type": "Polygon", "coordinates": [[["a", "b"]]]},
                "METHOD",
                ("dem",),
            )

    def test_rejects_empty_derivation_method(self) -> None:
        with self.assertRaises(SamplingValidationError):
            validate_management_zone(POLYGON_GEOJSON, "", ("dem",))

    def test_rejects_blank_derivation_method(self) -> None:
        with self.assertRaises(SamplingValidationError):
            validate_management_zone(POLYGON_GEOJSON, "   ", ("dem",))

    def test_rejects_empty_inputs(self) -> None:
        with self.assertRaises(SamplingValidationError):
            validate_management_zone(POLYGON_GEOJSON, "METHOD", ())


class ManagementZoneModelTest(unittest.TestCase):
    def test_classification_is_fixed_derived(self) -> None:
        zone = ManagementZone(
            zone_id="zone-1",
            field_id="field-1",
            geometry=POLYGON_GEOJSON,
            derivation_method="TERRAIN_VARIABILITY",
            method_version="v1",
            inputs=("dem", "sentinel2"),
        )
        self.assertEqual(zone.classification, DataClassification.DERIVED)

    def test_generated_at_is_populated_by_default(self) -> None:
        zone = ManagementZone(
            zone_id="zone-1",
            field_id="field-1",
            geometry=POLYGON_GEOJSON,
            derivation_method="TERRAIN_VARIABILITY",
            method_version="v1",
            inputs=("dem",),
        )
        self.assertTrue(zone.generated_at)
        self.assertIn("T", zone.generated_at)

    def test_limitations_default_to_empty_tuple(self) -> None:
        zone = ManagementZone(
            zone_id="zone-1",
            field_id="field-1",
            geometry=POLYGON_GEOJSON,
            derivation_method="TERRAIN_VARIABILITY",
            method_version="v1",
            inputs=("dem",),
        )
        self.assertEqual(zone.limitations, ())


class SuggestedSamplePointModelTest(unittest.TestCase):
    def test_defaults_are_derived_location(self) -> None:
        point = SuggestedSamplePoint(
            point_id="point-1",
            field_id="field-1",
            geometry=POINT_GEOJSON,
            derivation_method="ZONE_CENTROID",
        )
        self.assertEqual(point.status, "DERIVED_LOCATION")
        self.assertEqual(point.classification, DataClassification.DERIVED)

    def test_zone_id_is_optional(self) -> None:
        point = SuggestedSamplePoint(
            point_id="point-1",
            field_id="field-1",
            geometry=POINT_GEOJSON,
            derivation_method="ZONE_CENTROID",
        )
        self.assertIsNone(point.zone_id)

    def test_zone_id_can_be_provided(self) -> None:
        point = SuggestedSamplePoint(
            point_id="point-1",
            field_id="field-1",
            zone_id="zone-1",
            geometry=POINT_GEOJSON,
            derivation_method="ZONE_CENTROID",
        )
        self.assertEqual(point.zone_id, "zone-1")


class FrozenModelTest(unittest.TestCase):
    def test_management_zone_is_frozen(self) -> None:
        zone = ManagementZone(
            zone_id="zone-1",
            field_id="field-1",
            geometry=POLYGON_GEOJSON,
            derivation_method="TERRAIN_VARIABILITY",
            method_version="v1",
            inputs=("dem",),
        )
        with self.assertRaises(Exception):
            zone.zone_id = "changed"  # type: ignore[misc]

    def test_suggested_sample_point_is_frozen(self) -> None:
        point = SuggestedSamplePoint(
            point_id="point-1",
            field_id="field-1",
            geometry=POINT_GEOJSON,
            derivation_method="ZONE_CENTROID",
        )
        with self.assertRaises(Exception):
            point.point_id = "changed"  # type: ignore[misc]


class ExceptionHierarchyTest(unittest.TestCase):
    def test_sampling_validation_error_is_value_error(self) -> None:
        self.assertTrue(issubclass(SamplingValidationError, ValueError))


if __name__ == "__main__":
    unittest.main()
