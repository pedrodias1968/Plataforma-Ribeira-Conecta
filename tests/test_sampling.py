"""Unit tests for the Smart Soil Sampling pure domain model.

Evidence First: management zones are derived geometry (not legal/cadastral
boundaries) and suggested sample points are DERIVED_LOCATION (not measurements).
These tests intentionally do not assert any agronomic rule.
"""

from __future__ import annotations

import json
import unittest

from pyproj import Transformer
from shapely.geometry import Point, shape

from ribeira_platform.epistemology import DataClassification
from ribeira_platform.sampling import (
    ConfirmedSampleLocation,
    ManagementZone,
    SamplingValidationError,
    SuggestedSamplePoint,
    confirmed_locations_to_feature_collection,
    confirm_sample_location,
    reproject_sample_points,
    sample_points_to_feature_collection,
    sirgas2000_utm_crs_for,
    suggest_grid_sample_points,
    suggest_grid_sample_points_for_lonlat_field,
    suggest_zone_sample_points,
    validate_management_zone,
    zones_to_feature_collection,
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


class SuggestZoneSamplePointsTest(unittest.TestCase):
    def _zone(
        self,
        zone_id: str = "zone-1",
        field_id: str = "field-1",
        geometry: dict | None = None,
        derivation_method: str = "TERRAIN_VARIABILITY",
        inputs: tuple[str, ...] = ("dem",),
    ) -> ManagementZone:
        return ManagementZone(
            zone_id=zone_id,
            field_id=field_id,
            geometry=geometry if geometry is not None else POLYGON_GEOJSON,
            derivation_method=derivation_method,
            method_version="v1",
            inputs=inputs,
        )

    def test_returns_one_point_per_zone_preserving_order(self) -> None:
        zones = [
            self._zone("zone-a"),
            self._zone("zone-b"),
            self._zone("zone-c"),
        ]
        points = suggest_zone_sample_points(zones)
        self.assertEqual(len(points), 3)
        self.assertEqual(
            [p.zone_id for p in points], ["zone-a", "zone-b", "zone-c"]
        )

    def test_point_lies_inside_its_zone(self) -> None:
        zone = self._zone()
        points = suggest_zone_sample_points([zone])
        polygon = shape(zone.geometry)
        x, y = points[0].geometry["coordinates"]
        self.assertTrue(polygon.representative_point().equals(Point(x, y)))

    def test_point_id_is_deterministic(self) -> None:
        first = suggest_zone_sample_points(
            [self._zone()], generated_at="2026-01-01T00:00:00Z"
        )
        second = suggest_zone_sample_points(
            [self._zone()], generated_at="2026-01-01T00:00:00Z"
        )
        self.assertEqual(first[0].point_id, second[0].point_id)

    def test_zone_id_and_field_id_are_propagated(self) -> None:
        zone = self._zone(zone_id="zone-9", field_id="field-9")
        points = suggest_zone_sample_points([zone])
        self.assertEqual(points[0].zone_id, "zone-9")
        self.assertEqual(points[0].field_id, "field-9")

    def test_points_are_derived_locations(self) -> None:
        points = suggest_zone_sample_points([self._zone()])
        self.assertEqual(points[0].status, "DERIVED_LOCATION")
        self.assertEqual(points[0].classification, DataClassification.DERIVED)
        self.assertEqual(
            points[0].derivation_method, "ZONE_REPRESENTATIVE_POINT"
        )

    def test_accepts_multipolygon_zone(self) -> None:
        zone = self._zone(geometry=MULTIPOLYGON_GEOJSON)
        points = suggest_zone_sample_points([zone])
        self.assertEqual(len(points), 1)
        self.assertEqual(points[0].zone_id, "zone-1")

    def test_rejects_empty_sequence(self) -> None:
        with self.assertRaises(SamplingValidationError):
            suggest_zone_sample_points([])

    def test_rejects_non_management_zone_item(self) -> None:
        with self.assertRaises(SamplingValidationError):
            suggest_zone_sample_points([self._zone(), object()])  # type: ignore[list-item]

    def test_rejects_duplicate_zone_id(self) -> None:
        with self.assertRaises(SamplingValidationError):
            suggest_zone_sample_points(
                [self._zone("zone-dup"), self._zone("zone-dup", field_id="field-2")]
            )

    def test_rejects_invalid_zone_geometry(self) -> None:
        zone = self._zone(geometry=BOWTIE_GEOJSON, derivation_method="TERRAIN_VARIABILITY")
        with self.assertRaises(SamplingValidationError):
            suggest_zone_sample_points([zone])

    def test_rejects_zone_with_empty_inputs(self) -> None:
        zone = self._zone(inputs=())
        with self.assertRaises(SamplingValidationError):
            suggest_zone_sample_points([zone])


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


class FeatureCollectionSerializationTest(unittest.TestCase):
    def _zone(self, zone_id: str = "zone-1", **overrides):
        values = dict(
            zone_id=zone_id,
            field_id="field-1",
            geometry={"type": "Polygon", "coordinates": POLYGON_GEOJSON["coordinates"]},
            derivation_method="TERRAIN_VARIABILITY",
            method_version="v1",
            inputs=("dem", "sentinel2"),
            generated_at="2026-01-01T00:00:00Z",
            limitations=("derived_only",),
        )
        values.update(overrides)
        return ManagementZone(**values)

    def _point(self, point_id: str = "point-1", **overrides):
        values = dict(
            point_id=point_id,
            field_id="field-1",
            geometry={"type": "Point", "coordinates": [-46.99, -24.01]},
            derivation_method="ZONE_CENTROID",
            zone_id="zone-1",
            generated_at="2026-01-01T00:00:00Z",
        )
        values.update(overrides)
        return SuggestedSamplePoint(**values)

    def _confirmed(self, point_id: str = "confirmed-1", **overrides):
        values = dict(
            point_id=point_id,
            field_id="field-1",
            suggested_point_id="point-1",
            geometry={"type": "Point", "coordinates": [-46.99, -24.01]},
            confirmed_by="tech-1",
            confirmed_at="2026-01-02T00:00:00Z",
            adjusted=False,
            adjustment_note=None,
        )
        values.update(overrides)
        return ConfirmedSampleLocation(**values)

    def test_empty_sequence_yields_no_features(self) -> None:
        for serializer in (
            zones_to_feature_collection,
            sample_points_to_feature_collection,
            confirmed_locations_to_feature_collection,
        ):
            result = serializer([])
            self.assertEqual(result, {"type": "FeatureCollection", "features": []})

    def test_zones_feature_count_and_json_dumpable(self) -> None:
        result = zones_to_feature_collection([self._zone("z1"), self._zone("z2")])
        self.assertEqual(result["type"], "FeatureCollection")
        self.assertEqual(len(result["features"]), 2)
        json.dumps(result)

    def test_zones_classification_is_serialized_as_string(self) -> None:
        feature = zones_to_feature_collection([self._zone()])["features"][0]
        self.assertEqual(feature["properties"]["classification"], "DERIVED")

    def test_zones_inputs_and_limitations_become_lists(self) -> None:
        props = zones_to_feature_collection([self._zone()])["features"][0]["properties"]
        self.assertEqual(props["inputs"], ["dem", "sentinel2"])
        self.assertEqual(props["limitations"], ["derived_only"])
        self.assertIsInstance(props["inputs"], list)
        self.assertIsInstance(props["limitations"], list)

    def test_zones_geometry_identical_to_original(self) -> None:
        zone = self._zone()
        feature = zones_to_feature_collection([zone])["features"][0]
        self.assertEqual(feature["geometry"], zone.geometry)
        self.assertIs(feature["geometry"], zone.geometry)

    def test_zones_order_preserved(self) -> None:
        result = zones_to_feature_collection(
            [self._zone("z1"), self._zone("z2"), self._zone("z3")]
        )
        ids = [f["properties"]["zone_id"] for f in result["features"]]
        self.assertEqual(ids, ["z1", "z2", "z3"])

    def test_zones_original_object_unchanged(self) -> None:
        zone = self._zone()
        before = (
            zone.geometry,
            zone.inputs,
            zone.limitations,
            zone.classification,
        )
        zones_to_feature_collection([zone])
        self.assertEqual(
            (zone.geometry, zone.inputs, zone.limitations, zone.classification),
            before,
        )

    def test_zones_reject_wrong_item_type(self) -> None:
        with self.assertRaises(SamplingValidationError):
            zones_to_feature_collection([self._zone(), object()])

    def test_points_feature_collection(self) -> None:
        result = sample_points_to_feature_collection([self._point("p1"), self._point("p2")])
        self.assertEqual(len(result["features"]), 2)
        json.dumps(result)
        props = result["features"][0]["properties"]
        self.assertEqual(props["classification"], "DERIVED")
        self.assertEqual(props["status"], "DERIVED_LOCATION")
        self.assertEqual(props["zone_id"], "zone-1")
        self.assertEqual(result["features"][0]["geometry"], self._point().geometry)

    def test_points_none_zone_id_stays_none(self) -> None:
        props = sample_points_to_feature_collection(
            [self._point(zone_id=None)]
        )["features"][0]["properties"]
        self.assertIsNone(props["zone_id"])

    def test_points_excludes_geometry_from_properties(self) -> None:
        props = sample_points_to_feature_collection([self._point()])["features"][0][
            "properties"
        ]
        self.assertNotIn("geometry", props)

    def test_points_reject_wrong_item_type(self) -> None:
        with self.assertRaises(SamplingValidationError):
            sample_points_to_feature_collection([self._point(), object()])

    def test_confirmed_locations_feature_collection(self) -> None:
        result = confirmed_locations_to_feature_collection(
            [self._confirmed("c1"), self._confirmed("c2")]
        )
        self.assertEqual(len(result["features"]), 2)
        json.dumps(result)
        props = result["features"][0]["properties"]
        self.assertEqual(props["classification"], "MANUAL_CONFIRMED")
        self.assertEqual(props["suggested_point_id"], "point-1")
        self.assertIsNone(props["adjustment_note"])
        self.assertFalse(props["adjusted"])

    def test_confirmed_locations_order_preserved(self) -> None:
        result = confirmed_locations_to_feature_collection(
            [self._confirmed("c1"), self._confirmed("c2")]
        )
        ids = [f["properties"]["point_id"] for f in result["features"]]
        self.assertEqual(ids, ["c1", "c2"])

    def test_confirmed_locations_geometry_identical(self) -> None:
        location = self._confirmed()
        feature = confirmed_locations_to_feature_collection([location])["features"][0]
        self.assertEqual(feature["geometry"], location.geometry)

    def test_confirmed_locations_reject_wrong_item_type(self) -> None:
        with self.assertRaises(SamplingValidationError):
            confirmed_locations_to_feature_collection([self._confirmed(), object()])

    def test_confirmed_locations_original_object_unchanged(self) -> None:
        location = self._confirmed()
        before = (location.geometry, location.classification, location.adjustment_note)
        confirmed_locations_to_feature_collection([location])
        self.assertEqual(
            (location.geometry, location.classification, location.adjustment_note),
            before,
        )


class ReprojectSamplePointsTest(unittest.TestCase):
    PROJECTED_CRS = "EPSG:31983"
    GEOGRAPHIC_CRS = "EPSG:4326"

    def _point(
        self,
        point_id: str = "point-1",
        zone_id: str | None = "zone-1",
        coordinates: tuple[float, float] = (500000.0, 7300000.0),
    ) -> SuggestedSamplePoint:
        return SuggestedSamplePoint(
            point_id=point_id,
            field_id="field-1",
            geometry={"type": "Point", "coordinates": list(coordinates)},
            derivation_method="REGULAR_GRID",
            zone_id=zone_id,
            generated_at="2026-01-01T00:00:00Z",
        )

    def test_round_trip_returns_original_point(self) -> None:
        original = self._point()
        forward = reproject_sample_points(
            [original], self.PROJECTED_CRS, self.GEOGRAPHIC_CRS
        )
        back = reproject_sample_points(
            forward, self.GEOGRAPHIC_CRS, self.PROJECTED_CRS
        )
        result_x, result_y = back[0].geometry["coordinates"]
        self.assertAlmostEqual(result_x, original.geometry["coordinates"][0], places=6)
        self.assertAlmostEqual(result_y, original.geometry["coordinates"][1], places=6)

    def test_output_is_lon_lat_in_valid_range(self) -> None:
        result = reproject_sample_points(
            [self._point()], self.PROJECTED_CRS, self.GEOGRAPHIC_CRS
        )
        lon, lat = result[0].geometry["coordinates"]
        self.assertGreaterEqual(lon, -180.0)
        self.assertLessEqual(lon, 180.0)
        self.assertGreaterEqual(lat, -90.0)
        self.assertLessEqual(lat, 90.0)

    def test_matches_pyproj_reference(self) -> None:
        original = self._point()
        transformer = Transformer.from_crs(
            self.PROJECTED_CRS, self.GEOGRAPHIC_CRS, always_xy=True
        )
        expected_lon, expected_lat = transformer.transform(
            original.geometry["coordinates"][0],
            original.geometry["coordinates"][1],
        )
        result = reproject_sample_points(
            [original], self.PROJECTED_CRS, self.GEOGRAPHIC_CRS
        )
        lon, lat = result[0].geometry["coordinates"]
        self.assertAlmostEqual(lon, expected_lon, places=9)
        self.assertAlmostEqual(lat, expected_lat, places=9)

    def test_preserves_all_other_fields(self) -> None:
        original = self._point(point_id="p-42", zone_id="zone-9")
        result = reproject_sample_points(
            [original], self.PROJECTED_CRS, self.GEOGRAPHIC_CRS
        )[0]
        self.assertEqual(result.point_id, original.point_id)
        self.assertEqual(result.zone_id, original.zone_id)
        self.assertEqual(result.status, original.status)
        self.assertEqual(result.classification, original.classification)
        self.assertEqual(result.derivation_method, original.derivation_method)
        self.assertEqual(result.generated_at, original.generated_at)
        self.assertEqual(result.field_id, original.field_id)

    def test_original_object_unchanged(self) -> None:
        original = self._point()
        before = original.geometry["coordinates"][:]
        reproject_sample_points(
            [original], self.PROJECTED_CRS, self.GEOGRAPHIC_CRS
        )
        self.assertEqual(original.geometry["coordinates"], before)

    def test_returns_new_objects(self) -> None:
        original = self._point()
        result = reproject_sample_points(
            [original], self.PROJECTED_CRS, self.GEOGRAPHIC_CRS
        )
        self.assertIsNot(result[0], original)

    def test_preserves_order(self) -> None:
        points = [
            self._point("p1", coordinates=(500000.0, 7300000.0)),
            self._point("p2", coordinates=(501000.0, 7301000.0)),
            self._point("p3", coordinates=(502000.0, 7302000.0)),
        ]
        result = reproject_sample_points(
            points, self.PROJECTED_CRS, self.GEOGRAPHIC_CRS
        )
        self.assertEqual([p.point_id for p in result], ["p1", "p2", "p3"])

    def test_none_zone_id_preserved(self) -> None:
        original = self._point(zone_id=None)
        result = reproject_sample_points(
            [original], self.PROJECTED_CRS, self.GEOGRAPHIC_CRS
        )[0]
        self.assertIsNone(result.zone_id)

    def test_empty_sequence_returns_empty_tuple(self) -> None:
        result = reproject_sample_points([], self.PROJECTED_CRS)
        self.assertEqual(result, ())

    def test_rejects_missing_source_crs(self) -> None:
        with self.assertRaises(SamplingValidationError):
            reproject_sample_points([self._point()], None)

    def test_rejects_invalid_source_crs(self) -> None:
        with self.assertRaises(SamplingValidationError):
            reproject_sample_points([self._point()], "not-a-crs")

    def test_rejects_invalid_target_crs(self) -> None:
        with self.assertRaises(SamplingValidationError):
            reproject_sample_points(
                [self._point()], self.PROJECTED_CRS, "not-a-crs"
            )

    def test_rejects_wrong_item_type(self) -> None:
        with self.assertRaises(SamplingValidationError):
            reproject_sample_points([object()], self.PROJECTED_CRS)

    def test_rejects_non_point_geometry(self) -> None:
        bad = SuggestedSamplePoint(
            point_id="bad",
            field_id="field-1",
            geometry={
                "type": "LineString",
                "coordinates": [[0.0, 0.0], [1.0, 1.0]],
            },
            derivation_method="REGULAR_GRID",
        )
        with self.assertRaises(SamplingValidationError):
            reproject_sample_points([bad], self.PROJECTED_CRS)

    def test_rejects_non_finite_result(self) -> None:
        original = self._point(coordinates=(float("inf"), float("inf")))
        with self.assertRaises(SamplingValidationError):
            reproject_sample_points(
                [original], self.PROJECTED_CRS, self.GEOGRAPHIC_CRS
            )


class LonLatGridSamplingTest(unittest.TestCase):
    """Lon/lat field polygons are projected before building a metric grid.

    Evidence First: the field is stored in EPSG:4326 while the grid needs a
    projected CRS in metres. These tests build the reference square in
    EPSG:31983 (Vale do Ribeira), convert its corners to lon/lat with pyproj
    inside the test and verify the round-trip behaviour.
    """

    CENTER_LON = -47.9
    CENTER_LAT = -24.5
    UTM_CRS = "EPSG:31983"

    def _lonlat_square_from_metres(self, size_m: float = 200.0) -> dict:
        to_utm = Transformer.from_crs(
            "EPSG:4326", self.UTM_CRS, always_xy=True
        )
        cx, cy = to_utm.transform(self.CENTER_LON, self.CENTER_LAT)
        half = size_m / 2.0
        corners_utm = [
            (cx - half, cy - half),
            (cx + half, cy - half),
            (cx + half, cy + half),
            (cx - half, cy + half),
            (cx - half, cy - half),
        ]
        to_lonlat = Transformer.from_crs(
            self.UTM_CRS, "EPSG:4326", always_xy=True
        )
        ring = [list(to_lonlat.transform(x, y)) for x, y in corners_utm]
        return {"type": "Polygon", "coordinates": [ring]}

    def test_crs_is_sirgas2000_utm_zone_23s(self) -> None:
        polygon = self._lonlat_square_from_metres()
        crs = sirgas2000_utm_crs_for(polygon)
        self.assertEqual(crs, "EPSG:31983")

    def test_grid_spacing_50_yields_16_points(self) -> None:
        polygon = self._lonlat_square_from_metres()
        crs, points = suggest_grid_sample_points_for_lonlat_field(
            "field-1", polygon, 50.0
        )
        self.assertEqual(crs, "EPSG:31983")
        self.assertEqual(len(points), 16)

    def test_all_points_inside_field_and_valid_lonlat(self) -> None:
        polygon = self._lonlat_square_from_metres()
        field = shape(polygon)
        _, points = suggest_grid_sample_points_for_lonlat_field(
            "field-1", polygon, 50.0
        )
        for point in points:
            lon, lat = point.geometry["coordinates"]
            self.assertTrue(-180.0 <= lon <= 180.0)
            self.assertTrue(-90.0 <= lat <= 90.0)
            self.assertTrue(field.contains(Point(lon, lat)))

    def test_deterministic_output(self) -> None:
        polygon = self._lonlat_square_from_metres()
        first = suggest_grid_sample_points_for_lonlat_field(
            "field-1", polygon, 50.0, generated_at="2026-01-01T00:00:00+00:00"
        )
        second = suggest_grid_sample_points_for_lonlat_field(
            "field-1", polygon, 50.0, generated_at="2026-01-01T00:00:00+00:00"
        )
        self.assertEqual(first, second)

    def test_rejects_geometry_outside_coverage(self) -> None:
        outside = {
            "type": "Polygon",
            "coordinates": [
                [[10.0, 50.0], [10.001, 50.0], [10.001, 50.001],
                 [10.0, 50.001], [10.0, 50.0]]
            ],
        }
        with self.assertRaises(SamplingValidationError):
            sirgas2000_utm_crs_for(outside)
        with self.assertRaises(SamplingValidationError):
            suggest_grid_sample_points_for_lonlat_field(
                "field-1", outside, 50.0
            )

    def test_rejects_invalid_geometry(self) -> None:
        bowtie = {
            "type": "Polygon",
            "coordinates": [
                [[0.0, 0.0], [1.0, 1.0], [1.0, 0.0], [0.0, 1.0], [0.0, 0.0]]
            ],
        }
        with self.assertRaises(SamplingValidationError):
            suggest_grid_sample_points_for_lonlat_field(
                "field-1", bowtie, 50.0
            )

    def test_rejects_out_of_range_lonlat(self) -> None:
        out_of_range = {
            "type": "Polygon",
            "coordinates": [
                [[200.0, -24.5], [200.001, -24.5], [200.001, -24.499],
                 [200.0, -24.499], [200.0, -24.5]]
            ],
        }
        with self.assertRaises(SamplingValidationError):
            suggest_grid_sample_points_for_lonlat_field(
                "field-1", out_of_range, 50.0
            )

    def test_max_points_is_respected(self) -> None:
        polygon = self._lonlat_square_from_metres()
        with self.assertRaises(SamplingValidationError):
            suggest_grid_sample_points_for_lonlat_field(
                "field-1", polygon, 1.0, max_points=16
            )
