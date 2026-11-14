"""Smart Soil Sampling domain model (management zones and suggested points).

Evidence-First pure domain model. This module contains no database, network,
API, raster or migration logic. Management zones are derived geometry that
support sampling planning; they are neither property nor cadastral boundaries.
A suggested sample point is a DERIVED_LOCATION, not a soil measurement.
"""

from __future__ import annotations

import math
import uuid
from dataclasses import dataclass, field, replace
from typing import Any

from pyproj import CRS, Transformer
from pyproj.aoi import AreaOfInterest
from pyproj.database import query_utm_crs_info
from pyproj.exceptions import CRSError
from shapely.errors import GEOSException
from shapely.geometry import Point, mapping, shape
from shapely.ops import transform
from shapely.validation import explain_validity

from .epistemology import DataClassification
from .models import now_utc


_ALLOWED_ZONE_TYPES = ("Polygon", "MultiPolygon")

_GRID_NAMESPACE = uuid.UUID("6f4f2c31-2f3a-5f5c-8d0e-9c8b7a6d5e4f")
_GRID_DERIVATION_METHOD = "REGULAR_GRID"


class SamplingValidationError(ValueError):
    pass


def _reject_if_invalid(geom, label: str) -> None:
    """Reject topologically invalid geometry without silently repairing it.

    Evidence First: an invalid geometry (e.g. a self-intersecting "bow-tie"
    polygon) is rejected explicitly. The caller's geometry is never silently
    repaired or mutated.
    """
    if not geom.is_valid:
        raise SamplingValidationError(
            f"{label} is invalid: {explain_validity(geom)}"
        )


@dataclass(frozen=True)
class ManagementZone:
    """Versioned derived management zone used to plan soil sampling.

    Evidence First: a management zone is NOT a legal or cadastral boundary.
    It is derived geometry with an explicit derivation method, version, inputs
    and limitations. Its classification is fixed as DERIVED.
    """

    zone_id: str
    field_id: str
    geometry: dict[str, Any]
    derivation_method: str
    method_version: str
    inputs: tuple[str, ...]
    generated_at: str = field(default_factory=now_utc)
    limitations: tuple[str, ...] = ()
    classification: DataClassification = DataClassification.DERIVED


@dataclass(frozen=True)
class SuggestedSamplePoint:
    """Proposed soil sample location derived from a management zone.

    Evidence First: a suggested sample point is a DERIVED_LOCATION, not a
    measurement. It remains a recommendation until a technician confirms and
    performs collection.
    """

    point_id: str
    field_id: str
    geometry: dict[str, Any]
    derivation_method: str
    zone_id: str | None = None
    status: str = "DERIVED_LOCATION"
    classification: DataClassification = DataClassification.DERIVED
    generated_at: str = field(default_factory=now_utc)


def validate_management_zone(
    geometry: dict[str, Any],
    derivation_method: str,
    inputs: tuple[str, ...] | list[str],
) -> None:
    """Validate a management zone geometry and its derivation metadata.

    Rejects invalid, empty or wrong-type geometry, empty derivation_method and
    empty inputs. Does not invent agronomic rules.
    """
    if not isinstance(geometry, dict):
        raise SamplingValidationError("geometry must be a dict")

    geometry_type = geometry.get("type")
    if geometry_type not in _ALLOWED_ZONE_TYPES:
        raise SamplingValidationError(
            "geometry type must be 'Polygon' or 'MultiPolygon'"
        )

    if not geometry.get("coordinates"):
        raise SamplingValidationError("geometry coordinates must not be empty")

    try:
        zone_shape = shape(geometry)
    except (GEOSException, ValueError, TypeError) as exc:
        raise SamplingValidationError(f"invalid geometry: {exc}") from exc

    if zone_shape.is_empty:
        raise SamplingValidationError("geometry must not be empty")

    _reject_if_invalid(zone_shape, "geometry")

    if not isinstance(derivation_method, str) or not derivation_method.strip():
        raise SamplingValidationError("derivation_method must not be empty")

    if not inputs:
        raise SamplingValidationError("inputs must not be empty")


def _require_projected_metre_crs(crs: CRS | object | None) -> CRS:
    """Require a projected, metre-based CRS before building a metric grid.

    Mirrors the intent of the terrain CRS guard without importing its private
    helper: a geographic (degree-based) or missing CRS cannot express spacing in
    metres and must be rejected explicitly.
    """
    parsed = CRS.from_user_input(crs) if crs is not None else None
    if parsed is None or not parsed.is_projected:
        raise SamplingValidationError(
            "grid sampling CRS must be projected (metres), not geographic"
        )
    units = {axis.unit_name.lower() for axis in parsed.axis_info if axis.unit_name}
    if not any("metre" in unit or "meter" in unit for unit in units):
        raise SamplingValidationError("grid sampling CRS units must be metres")
    return parsed


def suggest_grid_sample_points(
    field_id: str,
    field_geometry: dict[str, Any],
    crs: CRS | object | None,
    spacing_m: float,
    generated_at: str | None = None,
    *,
    max_points: int = 10000,
) -> tuple[SuggestedSamplePoint, ...]:
    """Suggest soil sample points on a deterministic regular grid.

    Evidence First: the result is a set of DERIVED_LOCATION recommendations
    computed from geometry alone. It is not a measurement, not a diagnosis and
    carries no agronomic interpretation. The grid is anchored at cell centres,
    so it is fully reproducible for identical input.

    Requires a projected, metre-based CRS (geographic or missing CRS is
    rejected). ``spacing_m`` must be strictly positive. When no grid centre
    falls inside the polygon (e.g. the polygon is smaller than the spacing), a
    single fallback point is returned at the geometry's representative point.

    Rejects a geometry whose bounding box is under 1 metre in both axes with a
    ``SamplingValidationError`` mentioning ``lon/lat``: such an extent indicates
    coordinates supplied in lon/lat degrees rather than projected metres. The
    1 metre limit is a technical guard against mixed lon/lat + projected-CRS
    input, not an agronomic rule. Use
    ``suggest_grid_sample_points_for_lonlat_field`` for lon/lat geometry.
    """
    if not isinstance(spacing_m, (int, float)) or isinstance(spacing_m, bool):
        raise SamplingValidationError("spacing_m must be a positive number")
    if not math.isfinite(spacing_m):
        raise SamplingValidationError("spacing_m must be a finite number")
    if spacing_m <= 0:
        raise SamplingValidationError("spacing_m must be greater than zero")

    _require_projected_metre_crs(crs)

    if not isinstance(field_geometry, dict):
        raise SamplingValidationError("field_geometry must be a dict")

    geometry_type = field_geometry.get("type")
    if geometry_type not in _ALLOWED_ZONE_TYPES:
        raise SamplingValidationError(
            "field_geometry type must be 'Polygon' or 'MultiPolygon'"
        )

    if not field_geometry.get("coordinates"):
        raise SamplingValidationError("field_geometry coordinates must not be empty")

    try:
        polygon = shape(field_geometry)
    except (GEOSException, ValueError, TypeError) as exc:
        raise SamplingValidationError(f"invalid field_geometry: {exc}") from exc

    if polygon.is_empty:
        raise SamplingValidationError("field_geometry must not be empty")

    _reject_if_invalid(polygon, "field_geometry")

    if not isinstance(max_points, int) or isinstance(max_points, bool):
        raise SamplingValidationError("max_points must be an integer")
    if max_points <= 0:
        raise SamplingValidationError("max_points must be greater than zero")

    min_x, min_y, max_x, max_y = polygon.bounds

    if (max_x - min_x) < 1.0 and (max_y - min_y) < 1.0:
        raise SamplingValidationError(
            "field_geometry extent is under 1 metre in the projected CRS; "
            "coordinates look like lon/lat degrees - project them to metres or "
            "use suggest_grid_sample_points_for_lonlat_field"
        )

    half = spacing_m / 2.0

    estimated_cells = ((max_x - min_x) / spacing_m) * ((max_y - min_y) / spacing_m)
    if estimated_cells > max_points:
        raise SamplingValidationError(
            "grid would generate too many sample points: estimated "
            f"{int(estimated_cells)} cells exceeds max_points={max_points}"
        )

    coordinates: list[tuple[float, float]] = []
    y = min_y + half
    while y < max_y:
        x = min_x + half
        while x < max_x:
            candidate = Point(x, y)
            if polygon.contains(candidate):
                coordinates.append((x, y))
            x += spacing_m
        y += spacing_m

    if not coordinates:
        fallback = polygon.representative_point()
        coordinates.append((fallback.x, fallback.y))

    points: list[SuggestedSamplePoint] = []
    for x, y in coordinates:
        key = f"{field_id}|{x:.6f}|{y:.6f}|{_GRID_DERIVATION_METHOD}"
        point_id = str(uuid.uuid5(_GRID_NAMESPACE, key))
        kwargs: dict[str, Any] = {}
        if generated_at is not None:
            kwargs["generated_at"] = generated_at
        points.append(
            SuggestedSamplePoint(
                point_id=point_id,
                field_id=field_id,
                geometry={"type": "Point", "coordinates": [x, y]},
                derivation_method=_GRID_DERIVATION_METHOD,
                **kwargs,
            )
        )

    return tuple(points)


_ZONE_NAMESPACE = uuid.UUID("b2d5f8a3-4e6c-5b7d-9e0f-1a2b3c4d5e6f")
_ZONE_DERIVATION_METHOD = "ZONE_REPRESENTATIVE_POINT"


def suggest_zone_sample_points(
    zones: tuple[ManagementZone, ...] | list[ManagementZone],
    generated_at: str | None = None,
) -> tuple[SuggestedSamplePoint, ...]:
    """Suggest exactly one sample point per already-delineated management zone.

    Evidence First: the result is DERIVED_LOCATION, not a measurement and not an
    agronomic prescription. Exactly one point per zone is returned, using each
    zone's ``representative_point()``. The number of points per zone and any
    sampling density are agronomic rules that are NOT decided here.

    Each zone is validated before use. Empty input, non-ManagementZone items
    and duplicate ``zone_id`` values are rejected. Zone order is preserved.
    """
    if not isinstance(zones, (tuple, list)):
        raise SamplingValidationError("zones must be a sequence of ManagementZone")
    if len(zones) == 0:
        raise SamplingValidationError("zones must not be empty")

    seen_zone_ids: set[str] = set()
    points: list[SuggestedSamplePoint] = []

    for zone in zones:
        if not isinstance(zone, ManagementZone):
            raise SamplingValidationError("each zone must be a ManagementZone")
        if zone.zone_id in seen_zone_ids:
            raise SamplingValidationError(f"duplicate zone_id: {zone.zone_id}")
        seen_zone_ids.add(zone.zone_id)

        validate_management_zone(
            zone.geometry, zone.derivation_method, zone.inputs
        )

        representative = shape(zone.geometry).representative_point()
        x, y = representative.x, representative.y

        key = f"{zone.zone_id}|{x:.6f}|{y:.6f}|{_ZONE_DERIVATION_METHOD}"
        point_id = str(uuid.uuid5(_ZONE_NAMESPACE, key))

        kwargs: dict[str, Any] = {}
        if generated_at is not None:
            kwargs["generated_at"] = generated_at

        points.append(
            SuggestedSamplePoint(
                point_id=point_id,
                field_id=zone.field_id,
                geometry={"type": "Point", "coordinates": [x, y]},
                derivation_method=_ZONE_DERIVATION_METHOD,
                zone_id=zone.zone_id,
                **kwargs,
            )
        )

    return tuple(points)


def reproject_sample_points(
    points: tuple[SuggestedSamplePoint, ...] | list[SuggestedSamplePoint],
    source_crs: CRS | object | None,
    target_crs: CRS | object | str = "EPSG:4326",
) -> tuple[SuggestedSamplePoint, ...]:
    """Reproject suggested sample points between coordinate reference systems.

    Evidence First: this is a pure coordinate transformation. It changes only
    each point's geometry; every other field (``point_id``, ``zone_id``,
    ``status``, ``classification``, ``derivation_method``, ``generated_at``) is
    preserved unchanged and the input objects are never mutated. New objects are
    returned in the same order as the input.

    The grid is normally generated in the talhão's projected CRS (metres) while
    the standard GeoJSON (RFC 7946) representation uses EPSG:4326 lon/lat, so
    this conversion is required before serializing to a standard map.

    ``source_crs`` and ``target_crs`` are parsed with pyproj and rejected when
    missing or invalid. A non-``SuggestedSamplePoint`` item, a non-``Point``
    geometry or a non-finite resulting coordinate is rejected explicitly. An
    empty input returns an empty tuple.
    """
    if not isinstance(points, (tuple, list)):
        raise SamplingValidationError(
            "points must be a sequence of SuggestedSamplePoint"
        )

    try:
        source = CRS.from_user_input(source_crs) if source_crs is not None else None
    except (CRSError, ValueError, TypeError) as exc:
        raise SamplingValidationError(f"invalid source_crs: {exc}") from exc
    if source is None:
        raise SamplingValidationError("source_crs is required")

    try:
        target = CRS.from_user_input(target_crs) if target_crs is not None else None
    except (CRSError, ValueError, TypeError) as exc:
        raise SamplingValidationError(f"invalid target_crs: {exc}") from exc
    if target is None:
        raise SamplingValidationError("target_crs is required")

    transformer = Transformer.from_crs(source, target, always_xy=True)

    reprojected: list[SuggestedSamplePoint] = []
    for point in points:
        if not isinstance(point, SuggestedSamplePoint):
            raise SamplingValidationError(
                f"points must contain SuggestedSamplePoint, got {type(point).__name__}"
            )

        geometry = point.geometry
        if not isinstance(geometry, dict) or geometry.get("type") != "Point":
            raise SamplingValidationError(
                "sample point geometry must be a Point"
            )
        coordinates = geometry.get("coordinates")
        if not coordinates or len(coordinates) != 2:
            raise SamplingValidationError(
                "Point coordinates must have two numbers"
            )

        try:
            x, y = transformer.transform(coordinates[0], coordinates[1])
        except (CRSError, ValueError, TypeError) as exc:
            raise SamplingValidationError(f"reprojection failed: {exc}") from exc

        if not (math.isfinite(x) and math.isfinite(y)):
            raise SamplingValidationError(
                "reprojected coordinate must be finite"
            )

        reprojected.append(
            replace(
                point,
                geometry={"type": "Point", "coordinates": [x, y]},
            )
        )

    return tuple(reprojected)


def sirgas2000_utm_crs_for(geometry_lonlat: dict[str, Any]) -> str:
    """Select the SIRGAS 2000 UTM CRS covering a lon/lat geometry.

    Evidence First: the CRS is chosen deterministically from the geometry's
    centroid using pyproj's official SIRGAS 2000 UTM database. If no UTM zone
    covers the centroid (outside SIRGAS 2000 coverage) a
    ``SamplingValidationError`` is raised; when more than one CRS matches, the
    lowest EPSG code is chosen so the result is reproducible.
    """
    if not isinstance(geometry_lonlat, dict):
        raise SamplingValidationError("geometry_lonlat must be a dict")

    try:
        geometry = shape(geometry_lonlat)
    except (GEOSException, ValueError, TypeError) as exc:
        raise SamplingValidationError(f"invalid geometry: {exc}") from exc

    if geometry.is_empty:
        raise SamplingValidationError("geometry must not be empty")

    centroid = geometry.centroid
    area_of_interest = AreaOfInterest(
        centroid.x, centroid.y, centroid.x, centroid.y
    )
    candidates = query_utm_crs_info(
        datum_name="SIRGAS 2000", area_of_interest=area_of_interest
    )
    if not candidates:
        raise SamplingValidationError(
            "geometry is outside SIRGAS 2000 UTM coverage"
        )

    chosen = min(candidates, key=lambda info: int(info.code))
    return f"EPSG:{chosen.code}"


def suggest_grid_sample_points_for_lonlat_field(
    field_id: str,
    field_geometry_lonlat: dict[str, Any],
    spacing_m: float,
    generated_at: str | None = None,
    *,
    max_points: int = 10000,
) -> tuple[str, tuple[SuggestedSamplePoint, ...]]:
    """Suggest a metric grid for a lon/lat (EPSG:4326) field polygon.

    Evidence First: talhões are stored in EPSG:4326, but a metric grid requires a
    projected CRS in metres. This helper validates the lon/lat polygon, selects
    the SIRGAS 2000 UTM CRS covering it, projects the polygon, runs the regular
    grid and reprojects the resulting DERIVED_LOCATION points back to EPSG:4326.

    It returns ``(crs_usado, points)`` where ``crs_usado`` is the projected CRS
    actually used (e.g. ``"EPSG:31983"``). No measurement or agronomic rule is
    introduced.
    """
    if not isinstance(field_geometry_lonlat, dict):
        raise SamplingValidationError("field_geometry_lonlat must be a dict")

    geometry_type = field_geometry_lonlat.get("type")
    if geometry_type not in _ALLOWED_ZONE_TYPES:
        raise SamplingValidationError(
            "field_geometry_lonlat type must be 'Polygon' or 'MultiPolygon'"
        )

    if not field_geometry_lonlat.get("coordinates"):
        raise SamplingValidationError(
            "field_geometry_lonlat coordinates must not be empty"
        )

    try:
        polygon_lonlat = shape(field_geometry_lonlat)
    except (GEOSException, ValueError, TypeError) as exc:
        raise SamplingValidationError(
            f"invalid field_geometry_lonlat: {exc}"
        ) from exc

    if polygon_lonlat.is_empty:
        raise SamplingValidationError("field_geometry_lonlat must not be empty")

    _reject_if_invalid(polygon_lonlat, "field_geometry_lonlat")

    min_lon, min_lat, max_lon, max_lat = polygon_lonlat.bounds
    if not (-180.0 <= min_lon and max_lon <= 180.0):
        raise SamplingValidationError(
            "field_geometry_lonlat longitude must be within [-180, 180]"
        )
    if not (-90.0 <= min_lat and max_lat <= 90.0):
        raise SamplingValidationError(
            "field_geometry_lonlat latitude must be within [-90, 90]"
        )

    crs_usado = sirgas2000_utm_crs_for(field_geometry_lonlat)

    transformer = Transformer.from_crs("EPSG:4326", crs_usado, always_xy=True)
    polygon_projected = transform(transformer.transform, polygon_lonlat)

    projected_points = suggest_grid_sample_points(
        field_id,
        mapping(polygon_projected),
        crs_usado,
        spacing_m,
        generated_at,
        max_points=max_points,
    )

    points_lonlat = reproject_sample_points(
        projected_points, crs_usado, "EPSG:4326"
    )
    return crs_usado, points_lonlat


_CONFIRM_NAMESPACE = uuid.UUID("a1c4e7b2-3d5f-4a6b-8c9d-0e1f2a3b4c5d")


@dataclass(frozen=True)
class ConfirmedSampleLocation:
    """Technician-confirmed sampling location for a field.

    Evidence First: confirming a location is a MANUAL_CONFIRMED planning act.
    It is NOT a collected soil sample and NOT a laboratory result. No
    measurement is created here. The confirmed location always keeps a link to
    the original suggested point through ``suggested_point_id``; the original
    suggestion is never mutated.
    """

    point_id: str
    field_id: str
    suggested_point_id: str
    geometry: dict[str, Any]
    confirmed_by: str
    confirmed_at: str
    adjusted: bool
    adjustment_note: str | None = None
    classification: DataClassification = DataClassification.MANUAL_CONFIRMED


def _validate_point_geometry(geometry: dict[str, Any]) -> Point:
    if not isinstance(geometry, dict):
        raise SamplingValidationError("geometry must be a dict")
    if geometry.get("type") != "Point":
        raise SamplingValidationError("geometry type must be 'Point'")
    coordinates = geometry.get("coordinates")
    if not coordinates or len(coordinates) != 2:
        raise SamplingValidationError("Point coordinates must have two numbers")
    try:
        return shape(geometry)
    except (GEOSException, ValueError, TypeError) as exc:
        raise SamplingValidationError(f"invalid geometry: {exc}") from exc


def _validate_field_polygon(field_geometry: dict[str, Any]):
    if not isinstance(field_geometry, dict):
        raise SamplingValidationError("field_geometry must be a dict")
    geometry_type = field_geometry.get("type")
    if geometry_type not in _ALLOWED_ZONE_TYPES:
        raise SamplingValidationError(
            "field_geometry type must be 'Polygon' or 'MultiPolygon'"
        )
    if not field_geometry.get("coordinates"):
        raise SamplingValidationError("field_geometry coordinates must not be empty")
    try:
        polygon = shape(field_geometry)
    except (GEOSException, ValueError, TypeError) as exc:
        raise SamplingValidationError(f"invalid field_geometry: {exc}") from exc
    if polygon.is_empty:
        raise SamplingValidationError("field_geometry must not be empty")
    _reject_if_invalid(polygon, "field_geometry")
    return polygon


def confirm_sample_location(
    suggestion: SuggestedSamplePoint,
    field_geometry: dict[str, Any],
    confirmed_by: str,
    adjusted_geometry: dict[str, Any] | None = None,
    adjustment_note: str | None = None,
    confirmed_at: str | None = None,
) -> ConfirmedSampleLocation:
    """Confirm a suggested sample location, optionally adjusted by a technician.

    Evidence First: the result is a MANUAL_CONFIRMED planning location. It is
    neither a collected sample nor a laboratory result; no measurement is
    produced. The original suggestion is left untouched and the confirmed
    location always retains ``suggested_point_id`` as its link back to it.

    Without ``adjusted_geometry`` the suggested point geometry is used and
    ``adjusted`` is False. With an adjustment the point must be a GeoJSON Point
    inside the field polygon and ``adjustment_note`` must be non-empty.
    ``confirmed_by`` is mandatory.
    """
    if not isinstance(confirmed_by, str) or not confirmed_by.strip():
        raise SamplingValidationError("confirmed_by must not be empty")

    if not isinstance(suggestion, SuggestedSamplePoint):
        raise SamplingValidationError("suggestion must be a SuggestedSamplePoint")

    field_polygon = _validate_field_polygon(field_geometry)

    if adjusted_geometry is None:
        geometry = suggestion.geometry
        adjusted = False
        note: str | None = None
    else:
        if not isinstance(adjustment_note, str) or not adjustment_note.strip():
            raise SamplingValidationError(
                "adjustment_note must not be empty when adjusting a location"
            )
        point = _validate_point_geometry(adjusted_geometry)
        if not field_polygon.contains(point):
            raise SamplingValidationError(
                "adjusted_geometry must be inside the field polygon"
            )
        geometry = adjusted_geometry
        adjusted = True
        note = adjustment_note

    x, y = geometry["coordinates"]
    key = (
        f"{suggestion.point_id}|{confirmed_by}|{x:.6f}|{y:.6f}|"
        f"{'ADJUSTED' if adjusted else 'AS_SUGGESTED'}"
    )
    point_id = str(uuid.uuid5(_CONFIRM_NAMESPACE, key))

    if confirmed_at is None:
        confirmed_at = now_utc()

    return ConfirmedSampleLocation(
        point_id=point_id,
        field_id=suggestion.field_id,
        suggested_point_id=suggestion.point_id,
        geometry=geometry,
        confirmed_by=confirmed_by,
        confirmed_at=confirmed_at,
        adjusted=adjusted,
        adjustment_note=note,
    )


def _serialize_property_value(value: Any) -> Any:
    if isinstance(value, DataClassification):
        return str(value)
    if isinstance(value, tuple):
        return list(value)
    return value


def _to_feature_collection(
    items: Any,
    expected_type: type,
    label: str,
) -> dict[str, Any]:
    features: list[dict[str, Any]] = []
    for item in items:
        if not isinstance(item, expected_type):
            raise SamplingValidationError(
                f"{label} item must be a {expected_type.__name__}"
            )
        properties = {
            field_name: _serialize_property_value(getattr(item, field_name))
            for field_name in item.__dataclass_fields__
            if field_name != "geometry"
        }
        features.append(
            {
                "type": "Feature",
                "geometry": item.geometry,
                "properties": properties,
            }
        )
    return {"type": "FeatureCollection", "features": features}


def zones_to_feature_collection(zones: Any) -> dict[str, Any]:
    """Serialize management zones as a GeoJSON FeatureCollection.

    Pure serialization: geometry is passed through unchanged, every other
    dataclass field becomes a property and no new property is invented.
    """
    return _to_feature_collection(zones, ManagementZone, "management zone")


def sample_points_to_feature_collection(points: Any) -> dict[str, Any]:
    """Serialize suggested sample points as a GeoJSON FeatureCollection."""
    return _to_feature_collection(points, SuggestedSamplePoint, "sample point")


def confirmed_locations_to_feature_collection(locations: Any) -> dict[str, Any]:
    """Serialize confirmed sample locations as a GeoJSON FeatureCollection."""
    return _to_feature_collection(
        locations, ConfirmedSampleLocation, "confirmed location"
    )
