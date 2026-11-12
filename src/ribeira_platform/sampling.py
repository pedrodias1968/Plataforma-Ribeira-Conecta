"""Smart Soil Sampling domain model (management zones and suggested points).

Evidence-First pure domain model. This module contains no database, network,
API, raster or migration logic. Management zones are derived geometry that
support sampling planning; they are neither property nor cadastral boundaries.
A suggested sample point is a DERIVED_LOCATION, not a soil measurement.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from shapely.errors import GEOSException
from shapely.geometry import shape

from .epistemology import DataClassification
from .models import now_utc


_ALLOWED_ZONE_TYPES = ("Polygon", "MultiPolygon")


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
