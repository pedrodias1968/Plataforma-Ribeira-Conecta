"""Smart Soil Sampling domain model (management zones and suggested points).

Evidence-First pure domain model. This module contains no database, network,
API, raster or migration logic. Management zones are derived geometry that
support sampling planning; they are neither property nor cadastral boundaries.
A suggested sample point is a DERIVED_LOCATION, not a soil measurement.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from pyproj import CRS
from shapely.errors import GEOSException
from shapely.geometry import Point, shape

from .epistemology import DataClassification
from .models import now_utc


_ALLOWED_ZONE_TYPES = ("Polygon", "MultiPolygon")

_GRID_NAMESPACE = uuid.UUID("6f4f2c31-2f3a-5f5c-8d0e-9c8b7a6d5e4f")
_GRID_DERIVATION_METHOD = "REGULAR_GRID"


class SamplingValidationError(ValueError):
    pass


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
    """
    if not isinstance(spacing_m, (int, float)) or isinstance(spacing_m, bool):
        raise SamplingValidationError("spacing_m must be a positive number")
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

    min_x, min_y, max_x, max_y = polygon.bounds
    half = spacing_m / 2.0

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
