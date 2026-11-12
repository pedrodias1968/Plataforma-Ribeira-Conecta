"""Unit tests for the Smart Soil Sampling pure domain model.

Evidence First: management zones are derived geometry (not legal/cadastral
boundaries) and suggested sample points are DERIVED_LOCATION (not measurements).
These tests intentionally do not assert any agronomic rule.
"""

from __future__ import annotations

import unittest

from ribeira_platform.epistemology import DataClassification
from ribeira_platform.sampling import (
    ConfirmedSampleLocation,
    ManagementZone,
    SamplingValidationError,
    SuggestedSamplePoint,
    confirm_sample_location,
    suggest_grid_sample_points,
    validate_management_zone,
)


PROJECTED_CRS = "EPSG:31983"

SQUARE_METRES_GEOJSON = {
    "type": "Polygon",
    "coordinates": [[[0.0, 0.0], [100.0, 0.0], [100.0, 100.0], [0.0, 100.0], [0.0, 0.0]]],
}

SMALL_SQUARE_METRES_GEOJSON = {
    "type": "Polygon",
    "coordinates": [[[0.0, 0.0], [10.0, 0.0], [10.0, 10.0], [0.0, 10.0], [0.0, 0.0]]],
}

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

BOWTIE_GEOJSON = {
    "type": "Polygon",
    "coordinates": [[[0.0, 0.0], [10.0, 10.0], [10.0, 0.0], [0.0, 10.0], [0.0, 0.0]]],
}


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

    def test_rejects_self_intersecting_bowtie(self) -> None:
        with self.assertRaises(SamplingValidationError) as ctx:
            validate_management_zone(BOWTIE_GEOJSON, "METHOD", ("dem",))
        self.assertIn("invalid", str(ctx.exception).lower())

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


class SuggestGridSamplePointsTest(unittest.TestCase):
    def test_known_square_yields_expected_count(self) -> None:
        points = suggest_grid_sample_points(
            "field-1", SQUARE_METRES_GEOJSON, PROJECTED_CRS, 25.0
        )
        self.assertEqual(len(points), 16)

    def test_small_polygon_yields_single_fallback_point(self) -> None:
        points = suggest_grid_sample_points(
            "field-1", SMALL_SQUARE_METRES_GEOJSON, PROJECTED_CRS, 25.0
        )
        self.assertEqual(len(points), 1)
        x, y = points[0].geometry["coordinates"]
        self.assertTrue(0.0 <= x <= 10.0)
        self.assertTrue(0.0 <= y <= 10.0)

    def test_rejects_geographic_crs(self) -> None:
        with self.assertRaises(SamplingValidationError):
            suggest_grid_sample_points(
                "field-1", POLYGON_GEOJSON, "EPSG:4326", 25.0
            )

    def test_rejects_missing_crs(self) -> None:
        with self.assertRaises(SamplingValidationError):
            suggest_grid_sample_points(
                "field-1", SQUARE_METRES_GEOJSON, None, 25.0
            )

    def test_rejects_zero_spacing(self) -> None:
        with self.assertRaises(SamplingValidationError):
            suggest_grid_sample_points(
                "field-1", SQUARE_METRES_GEOJSON, PROJECTED_CRS, 0.0
            )

    def test_rejects_negative_spacing(self) -> None:
        with self.assertRaises(SamplingValidationError):
            suggest_grid_sample_points(
                "field-1", SQUARE_METRES_GEOJSON, PROJECTED_CRS, -5.0
            )

    def test_same_input_yields_same_output(self) -> None:
        first = suggest_grid_sample_points(
            "field-1", SQUARE_METRES_GEOJSON, PROJECTED_CRS, 25.0,
            generated_at="2026-01-01T00:00:00Z",
        )
        second = suggest_grid_sample_points(
            "field-1", SQUARE_METRES_GEOJSON, PROJECTED_CRS, 25.0,
            generated_at="2026-01-01T00:00:00Z",
        )
        self.assertEqual(
            tuple(p.point_id for p in first),
            tuple(p.point_id for p in second),
        )

    def test_all_points_inside_polygon(self) -> None:
        from shapely.geometry import Point, shape

        polygon = shape(SQUARE_METRES_GEOJSON)
        points = suggest_grid_sample_points(
            "field-1", SQUARE_METRES_GEOJSON, PROJECTED_CRS, 25.0
        )
        for point in points:
            x, y = point.geometry["coordinates"]
            self.assertTrue(polygon.contains(Point(x, y)))

    def test_points_are_derived_locations(self) -> None:
        points = suggest_grid_sample_points(
            "field-1", SQUARE_METRES_GEOJSON, PROJECTED_CRS, 25.0
        )
        for point in points:
            self.assertEqual(point.status, "DERIVED_LOCATION")
            self.assertEqual(point.classification, DataClassification.DERIVED)
            self.assertEqual(point.derivation_method, "REGULAR_GRID")
            self.assertTrue(point.point_id)

    def test_distinct_points_have_distinct_ids(self) -> None:
        points = suggest_grid_sample_points(
            "field-1", SQUARE_METRES_GEOJSON, PROJECTED_CRS, 25.0
        )
        ids = [p.point_id for p in points]
        self.assertEqual(len(ids), len(set(ids)))

    def test_rejects_self_intersecting_bowtie(self) -> None:
        with self.assertRaises(SamplingValidationError) as ctx:
            suggest_grid_sample_points(
                "field-1", BOWTIE_GEOJSON, PROJECTED_CRS, 1.0
            )
        self.assertIn("invalid", str(ctx.exception).lower())

    def test_rejects_grid_exceeding_default_max_points(self) -> None:
        with self.assertRaises(SamplingValidationError) as ctx:
            suggest_grid_sample_points(
                "field-1", SQUARE_METRES_GEOJSON, PROJECTED_CRS, 0.5
            )
        self.assertIn("max_points", str(ctx.exception))

    def test_accepts_grid_within_custom_max_points(self) -> None:
        points = suggest_grid_sample_points(
            "field-1", SQUARE_METRES_GEOJSON, PROJECTED_CRS, 25.0, max_points=100
        )
        self.assertEqual(len(points), 16)

    def test_rejects_non_positive_max_points(self) -> None:
        with self.assertRaises(SamplingValidationError):
            suggest_grid_sample_points(
                "field-1", SQUARE_METRES_GEOJSON, PROJECTED_CRS, 25.0, max_points=0
            )


class ConfirmSampleLocationTest(unittest.TestCase):
    def _suggestion(self) -> SuggestedSamplePoint:
        return SuggestedSamplePoint(
            point_id="suggested-1",
            field_id="field-1",
            geometry={"type": "Point", "coordinates": [50.0, 50.0]},
            derivation_method="REGULAR_GRID",
        )

    def test_without_adjustment_uses_suggested_geometry(self) -> None:
        suggestion = self._suggestion()
        confirmed = confirm_sample_location(
            suggestion, SQUARE_METRES_GEOJSON, "tech-1"
        )
        self.assertEqual(confirmed.geometry, suggestion.geometry)
        self.assertFalse(confirmed.adjusted)
        self.assertIsNone(confirmed.adjustment_note)

    def test_confirmed_classification_is_manual_confirmed(self) -> None:
        confirmed = confirm_sample_location(
            self._suggestion(), SQUARE_METRES_GEOJSON, "tech-1"
        )
        self.assertEqual(
            confirmed.classification, DataClassification.MANUAL_CONFIRMED
        )

    def test_link_to_suggested_point_is_kept(self) -> None:
        suggestion = self._suggestion()
        confirmed = confirm_sample_location(
            suggestion, SQUARE_METRES_GEOJSON, "tech-1"
        )
        self.assertEqual(confirmed.suggested_point_id, suggestion.point_id)
        self.assertEqual(confirmed.field_id, suggestion.field_id)

    def test_original_suggestion_is_not_mutated(self) -> None:
        suggestion = self._suggestion()
        before = (
            suggestion.point_id,
            suggestion.field_id,
            dict(suggestion.geometry),
        )
        confirm_sample_location(suggestion, SQUARE_METRES_GEOJSON, "tech-1")
        self.assertEqual(suggestion.point_id, before[0])
        self.assertEqual(suggestion.field_id, before[1])
        self.assertEqual(suggestion.geometry, before[2])

    def test_adjusted_location_inside_field(self) -> None:
        confirmed = confirm_sample_location(
            self._suggestion(),
            SQUARE_METRES_GEOJSON,
            "tech-1",
            adjusted_geometry={"type": "Point", "coordinates": [10.0, 10.0]},
            adjustment_note="moved to avoid a rock",
        )
        self.assertTrue(confirmed.adjusted)
        self.assertEqual(
            confirmed.geometry, {"type": "Point", "coordinates": [10.0, 10.0]}
        )
        self.assertEqual(confirmed.adjustment_note, "moved to avoid a rock")

    def test_rejects_adjusted_location_outside_field(self) -> None:
        with self.assertRaises(SamplingValidationError):
            confirm_sample_location(
                self._suggestion(),
                SQUARE_METRES_GEOJSON,
                "tech-1",
                adjusted_geometry={"type": "Point", "coordinates": [500.0, 500.0]},
                adjustment_note="outside",
            )

    def test_rejects_self_intersecting_bowtie_field(self) -> None:
        with self.assertRaises(SamplingValidationError) as ctx:
            confirm_sample_location(self._suggestion(), BOWTIE_GEOJSON, "tech-1")
        self.assertIn("invalid", str(ctx.exception).lower())

    def test_rejects_adjustment_without_note(self) -> None:
        with self.assertRaises(SamplingValidationError):
            confirm_sample_location(
                self._suggestion(),
                SQUARE_METRES_GEOJSON,
                "tech-1",
                adjusted_geometry={"type": "Point", "coordinates": [10.0, 10.0]},
            )

    def test_rejects_blank_adjustment_note(self) -> None:
        with self.assertRaises(SamplingValidationError):
            confirm_sample_location(
                self._suggestion(),
                SQUARE_METRES_GEOJSON,
                "tech-1",
                adjusted_geometry={"type": "Point", "coordinates": [10.0, 10.0]},
                adjustment_note="   ",
            )

    def test_rejects_empty_confirmed_by(self) -> None:
        with self.assertRaises(SamplingValidationError):
            confirm_sample_location(self._suggestion(), SQUARE_METRES_GEOJSON, "")

    def test_rejects_blank_confirmed_by(self) -> None:
        with self.assertRaises(SamplingValidationError):
            confirm_sample_location(
                self._suggestion(), SQUARE_METRES_GEOJSON, "   "
            )

    def test_rejects_non_point_adjustment_geometry(self) -> None:
        with self.assertRaises(SamplingValidationError):
            confirm_sample_location(
                self._suggestion(),
                SQUARE_METRES_GEOJSON,
                "tech-1",
                adjusted_geometry=SQUARE_METRES_GEOJSON,
                adjustment_note="not a point",
            )

    def test_confirmed_at_defaults_to_utc_iso(self) -> None:
        confirmed = confirm_sample_location(
            self._suggestion(), SQUARE_METRES_GEOJSON, "tech-1"
        )
        self.assertTrue(confirmed.confirmed_at)
        self.assertIn("+00:00", confirmed.confirmed_at)

    def test_confirmed_at_can_be_provided(self) -> None:
        confirmed = confirm_sample_location(
            self._suggestion(),
            SQUARE_METRES_GEOJSON,
            "tech-1",
            confirmed_at="2026-01-01T00:00:00Z",
        )
        self.assertEqual(confirmed.confirmed_at, "2026-01-01T00:00:00Z")

    def test_deterministic_point_id(self) -> None:
        first = confirm_sample_location(
            self._suggestion(), SQUARE_METRES_GEOJSON, "tech-1"
        )
        second = confirm_sample_location(
            self._suggestion(), SQUARE_METRES_GEOJSON, "tech-1"
        )
        self.assertEqual(first.point_id, second.point_id)

    def test_confirmed_location_is_frozen(self) -> None:
        confirmed = confirm_sample_location(
            self._suggestion(), SQUARE_METRES_GEOJSON, "tech-1"
        )
        with self.assertRaises(Exception):
            confirmed.adjusted = True  # type: ignore[misc]

    def test_is_not_a_sample_point_or_lab_analysis(self) -> None:
        confirmed = confirm_sample_location(
            self._suggestion(), SQUARE_METRES_GEOJSON, "tech-1"
        )
        self.assertIsInstance(confirmed, ConfirmedSampleLocation)
        self.assertFalse(hasattr(confirmed, "value"))
        self.assertFalse(hasattr(confirmed, "lab_result"))


if __name__ == "__main__":
    unittest.main()
