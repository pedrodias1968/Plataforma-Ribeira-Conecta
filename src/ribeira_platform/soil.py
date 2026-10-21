"""Soil Intelligence and Smart Soil Sampling foundation.

Evidence-First soil data management: sample points, lab analyses,
agronomic calculations, and strict tenant isolation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
from typing import Any, Iterable

from shapely.geometry import Point as ShapelyPoint, shape

from datetime import datetime, timezone

from .epistemology import DataClassification
from .models import now_utc


def _parse_timestamp(value: str) -> str:
    """Parse ISO-8601 timestamp (datetime or date-only string).

    Accepts timezone-aware datetime strings or date-only strings (YYYY-MM-DD).
    Date-only strings are converted to midnight UTC.
    """
    try:
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            # Date-only or naive datetime - assume midnight UTC
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.isoformat()
    except ValueError:
        raise ValueError(f"Invalid timestamp format: {value}")


class SoilValidationError(ValueError):
    pass


@dataclass(frozen=True)
class SoilSamplePoint:
    """Georeferenced soil sample collection point."""

    id: str
    tenant_id: str
    property_id: str
    field_id: str | None
    sample_code: str
    depth_top_cm: float
    depth_bottom_cm: float
    collection_date: str
    collector_name: str
    location_geojson: dict[str, Any]
    location_crs: str
    classification: DataClassification
    source_reference: str
    status: str = "COLLECTED"
    created_at: str = field(default_factory=now_utc)


@dataclass(frozen=True)
class SoilLabAnalysis:
    """Accredited laboratory chemical and physical soil analysis report."""

    id: str
    tenant_id: str
    sample_point_id: str
    lab_name: str
    report_number: str
    report_date: str
    ph_h2o: float | None = None
    ph_cacl2: float | None = None
    organic_matter_g_dm3: float | None = None
    phosphorus_mg_dm3: float | None = None
    potassium_cmolc_dm3: float | None = None
    calcium_cmolc_dm3: float | None = None
    magnesium_cmolc_dm3: float | None = None
    aluminum_cmolc_dm3: float | None = None
    potential_acidity_h_al: float | None = None
    cation_exchange_capacity_cec: float | None = None
    base_saturation_percent: float | None = None
    clay_percent: float | None = None
    silt_percent: float | None = None
    sand_percent: float | None = None
    raw_attributes: dict[str, Any] = field(default_factory=dict)
    classification: DataClassification = DataClassification.MANUAL_CONFIRMED
    created_at: str = field(default_factory=now_utc)


def compute_soil_derived_indices(
    *,
    calcium: float | None = None,
    magnesium: float | None = None,
    potassium: float | None = None,
    h_al: float | None = None,
    aluminum: float | None = None,
    explicit_cec: float | None = None,
    explicit_v_percent: float | None = None,
) -> dict[str, float | None]:
    """Compute deterministic soil indices according to standard agronomic formulas.

    SB (Soma de Bases) = Ca + Mg + K (cmolc/dm3)
    CTC (Capacidade de Troca Catiônica a pH 7.0) = SB + (H+Al)
    V% (Saturação por Bases) = (SB / CTC) * 100
    m% (Saturação por Alumínio) = (Al / (SB + Al)) * 100
    """
    sb: float | None = None
    if calcium is not None and magnesium is not None and potassium is not None:
        sb = round(calcium + magnesium + potassium, 3)

    cec = explicit_cec
    if cec is None and sb is not None and h_al is not None:
        cec = round(sb + h_al, 3)

    v_percent = explicit_v_percent
    if v_percent is None and sb is not None and cec is not None and cec > 0:
        v_percent = round((sb / cec) * 100.0, 2)

    aluminum_saturation: float | None = None
    if aluminum is not None and sb is not None and (sb + aluminum) > 0:
        aluminum_saturation = round((aluminum / (sb + aluminum)) * 100.0, 2)

    return {
        "sum_of_bases": sb if sb is not None else 0.0,
        "cec": cec if cec is not None else 0.0,
        "base_saturation_percent": v_percent if v_percent is not None else 0.0,
        "aluminum_saturation_percent": aluminum_saturation,
    }


def validate_soil_sample_point(
    location_geojson: dict[str, Any],
    property_geometry: dict[str, Any] | None,
    field_geometry: dict[str, Any] | None = None,
) -> None:
    """Validate sample location coordinates and spatial containment within property/field."""
    if not isinstance(location_geojson, dict):
        raise SoilValidationError("location_geojson must be a dict")
    if location_geojson.get("type") != "Point":
        raise SoilValidationError("location_geojson type must be 'Point'")
    coords = location_geojson.get("coordinates")
    if not isinstance(coords, (list, tuple)) or len(coords) < 2:
        raise SoilValidationError("Point coordinates must have [longitude, latitude]")
    lon, lat = coords[0], coords[1]
    if not (isinstance(lon, (int, float)) and isinstance(lat, (int, float))):
        raise SoilValidationError("Point coordinates must be numeric")
    if not (-180.0 <= lon <= 180.0 and -90.0 <= lat <= 90.0):
        raise SoilValidationError("Point coordinates out of WGS84 range")

    pt = ShapelyPoint(lon, lat)

    if property_geometry:
        prop_shape = shape(property_geometry)
        if not (prop_shape.contains(pt) or prop_shape.touches(pt)):
            raise SoilValidationError(
                "Soil sample point is outside the property boundary"
            )

    if field_geometry:
        field_shape = shape(field_geometry)
        if not (field_shape.contains(pt) or field_shape.touches(pt)):
            raise SoilValidationError("Soil sample point is outside the field boundary")


SQLITE_SOIL_SCHEMA = """
CREATE TABLE IF NOT EXISTS soil_sample_point (
 id TEXT PRIMARY KEY,
 tenant_id TEXT NOT NULL,
 property_id TEXT NOT NULL,
 field_id TEXT,
 sample_code TEXT NOT NULL,
 depth_top_cm REAL NOT NULL,
 depth_bottom_cm REAL NOT NULL,
 collection_date TEXT NOT NULL,
 collector_name TEXT NOT NULL,
 location_geojson TEXT NOT NULL,
 location_crs TEXT NOT NULL,
 classification TEXT NOT NULL,
 source_reference TEXT NOT NULL,
 status TEXT NOT NULL,
 created_at TEXT NOT NULL,
 UNIQUE(tenant_id, id)
);
CREATE INDEX IF NOT EXISTS soil_sample_point_property_idx
 ON soil_sample_point(tenant_id, property_id, created_at DESC);

CREATE TABLE IF NOT EXISTS soil_lab_analysis (
 id TEXT PRIMARY KEY,
 tenant_id TEXT NOT NULL,
 sample_point_id TEXT NOT NULL REFERENCES soil_sample_point(id),
 lab_name TEXT NOT NULL,
 report_number TEXT NOT NULL,
 report_date TEXT NOT NULL,
 ph_h2o REAL,
 ph_cacl2 REAL,
 organic_matter_g_dm3 REAL,
 phosphorus_mg_dm3 REAL,
 potassium_cmolc_dm3 REAL,
 calcium_cmolc_dm3 REAL,
 magnesium_cmolc_dm3 REAL,
 aluminum_cmolc_dm3 REAL,
 potential_acidity_h_al REAL,
 cation_exchange_capacity_cec REAL,
 base_saturation_percent REAL,
 clay_percent REAL,
 silt_percent REAL,
 sand_percent REAL,
 raw_attributes TEXT NOT NULL,
 classification TEXT NOT NULL,
 created_at TEXT NOT NULL,
 UNIQUE(tenant_id, id)
);
CREATE INDEX IF NOT EXISTS soil_lab_analysis_sample_idx
 ON soil_lab_analysis(tenant_id, sample_point_id, created_at DESC);
"""


class SoilRepository:
    """Repository for Soil Intelligence entities (SQLite test and PostgreSQL)."""

    def __init__(self, store: Any) -> None:
        self.store = store
        self.connection = store.connection
        self.postgres = store.__class__.__name__ == "PostgresStore"
        if not self.postgres:
            self.connection.executescript(SQLITE_SOIL_SCHEMA)

    @property
    def placeholder(self) -> str:
        return "%s" if self.postgres else "?"

    def _execute(self, sql: str, params: Iterable[Any] = ()) -> Any:
        return self.connection.execute(sql, tuple(params))

    @staticmethod
    def _timestamp(value: Any) -> str:
        return value.isoformat() if hasattr(value, "isoformat") else str(value)

    def create_sample_point(
        self, item: SoilSamplePoint, *, actor: str
    ) -> SoilSamplePoint:
        p = self.placeholder
        location_column = "location" if self.postgres else "location_geojson"
        location_value = (
            f"ST_SetSRID(ST_GeomFromGeoJSON({p}::text), 4326)" if self.postgres else p
        )
        location_param = json.dumps(item.location_geojson)

        self._execute(
            f"""INSERT INTO soil_sample_point (
                 id, tenant_id, property_id, field_id, sample_code,
                 depth_top_cm, depth_bottom_cm, collection_date, collector_name,
                 {location_column}, location_crs, classification, source_reference,
                 status, created_at
               ) VALUES ({p},{p},{p},{p},{p},{p},{p},{p},{p},{location_value},{p},{p},{p},{p},{p})""",
            [
                item.id,
                item.tenant_id,
                item.property_id,
                item.field_id,
                item.sample_code,
                item.depth_top_cm,
                item.depth_bottom_cm,
                self._timestamp(_parse_timestamp(item.collection_date)),
                item.collector_name,
                location_param,
                item.location_crs,
                item.classification.value,
                item.source_reference,
                item.status,
                self._timestamp(_parse_timestamp(item.created_at)),
            ],
        )
        return item

    def get_sample_point(
        self, tenant_id: str, sample_id: str
    ) -> SoilSamplePoint | None:
        p = self.placeholder
        location_expr = (
            "ST_AsGeoJSON(location)" if self.postgres else "location_geojson"
        )
        cursor = self._execute(
            f"""SELECT id, tenant_id, property_id, field_id, sample_code,
                       depth_top_cm, depth_bottom_cm, collection_date, collector_name,
                       {location_expr} AS location_geojson, location_crs, classification,
                       source_reference, status, created_at
                FROM soil_sample_point
                WHERE tenant_id = {p} AND id = {p}""",
            [tenant_id, sample_id],
        )
        row = cursor.fetchone()
        if not row:
            return None
        return self._hydrate_sample_point(row)

    def list_sample_points(
        self,
        tenant_id: str,
        property_id: str,
        field_id: str | None = None,
    ) -> list[SoilSamplePoint]:
        p = self.placeholder
        location_expr = (
            "ST_AsGeoJSON(location)" if self.postgres else "location_geojson"
        )
        params: list[Any] = [tenant_id, property_id]
        field_clause = ""
        if field_id is not None:
            field_clause = f" AND field_id = {p}"
            params.append(field_id)

        cursor = self._execute(
            f"""SELECT id, tenant_id, property_id, field_id, sample_code,
                       depth_top_cm, depth_bottom_cm, collection_date, collector_name,
                       {location_expr} AS location_geojson, location_crs, classification,
                       source_reference, status, created_at
                FROM soil_sample_point
                WHERE tenant_id = {p} AND property_id = {p}{field_clause}
                ORDER BY created_at DESC""",
            params,
        )
        return [self._hydrate_sample_point(row) for row in cursor.fetchall()]

    def create_lab_analysis(
        self, item: SoilLabAnalysis, *, actor: str
    ) -> SoilLabAnalysis:
        p = self.placeholder
        raw_json = json.dumps(item.raw_attributes)
        raw_expr = f"{p}::jsonb" if self.postgres else p

        self._execute(
            f"""INSERT INTO soil_lab_analysis (
                 id, tenant_id, sample_point_id, lab_name, report_number, report_date,
                 ph_h2o, ph_cacl2, organic_matter_g_dm3, phosphorus_mg_dm3,
                 potassium_cmolc_dm3, calcium_cmolc_dm3, magnesium_cmolc_dm3,
                 aluminum_cmolc_dm3, potential_acidity_h_al, cation_exchange_capacity_cec,
                 base_saturation_percent, clay_percent, silt_percent, sand_percent,
                 raw_attributes, classification, created_at
               ) VALUES ({p},{p},{p},{p},{p},{p},{p},{p},{p},{p},{p},{p},{p},{p},{p},{p},{p},{p},{p},{p},{raw_expr},{p},{p})""",
            [
                item.id,
                item.tenant_id,
                item.sample_point_id,
                item.lab_name,
                item.report_number,
                self._timestamp(_parse_timestamp(item.report_date)),
                item.ph_h2o,
                item.ph_cacl2,
                item.organic_matter_g_dm3,
                item.phosphorus_mg_dm3,
                item.potassium_cmolc_dm3,
                item.calcium_cmolc_dm3,
                item.magnesium_cmolc_dm3,
                item.aluminum_cmolc_dm3,
                item.potential_acidity_h_al,
                item.cation_exchange_capacity_cec,
                item.base_saturation_percent,
                item.clay_percent,
                item.silt_percent,
                item.sand_percent,
                raw_json,
                item.classification.value,
                self._timestamp(_parse_timestamp(item.created_at)),
            ],
        )
        return item

    def list_lab_analyses(
        self, tenant_id: str, sample_point_id: str
    ) -> list[SoilLabAnalysis]:
        p = self.placeholder
        cursor = self._execute(
            f"""SELECT id, tenant_id, sample_point_id, lab_name, report_number, report_date,
                       ph_h2o, ph_cacl2, organic_matter_g_dm3, phosphorus_mg_dm3,
                       potassium_cmolc_dm3, calcium_cmolc_dm3, magnesium_cmolc_dm3,
                       aluminum_cmolc_dm3, potential_acidity_h_al, cation_exchange_capacity_cec,
                       base_saturation_percent, clay_percent, silt_percent, sand_percent,
                       raw_attributes, classification, created_at
                FROM soil_lab_analysis
                WHERE tenant_id = {p} AND sample_point_id = {p}
                ORDER BY report_date DESC, created_at DESC""",
            [tenant_id, sample_point_id],
        )
        return [self._hydrate_lab_analysis(row) for row in cursor.fetchall()]

    def _hydrate_sample_point(self, row: Any) -> SoilSamplePoint:
        data = (
            dict(row)
            if hasattr(row, "keys")
            else {
                "id": row[0],
                "tenant_id": row[1],
                "property_id": row[2],
                "field_id": row[3],
                "sample_code": row[4],
                "depth_top_cm": float(row[5]),
                "depth_bottom_cm": float(row[6]),
                "collection_date": str(row[7]),
                "collector_name": row[8],
                "location_geojson": row[9],
                "location_crs": row[10],
                "classification": row[11],
                "source_reference": row[12],
                "status": row[13],
                "created_at": str(row[14]),
            }
        )
        loc = data["location_geojson"]
        if isinstance(loc, str):
            loc = json.loads(loc)
        return SoilSamplePoint(
            id=str(data["id"]),
            tenant_id=str(data["tenant_id"]),
            property_id=str(data["property_id"]),
            field_id=str(data["field_id"]) if data["field_id"] else None,
            sample_code=str(data["sample_code"]),
            depth_top_cm=float(data["depth_top_cm"]),
            depth_bottom_cm=float(data["depth_bottom_cm"]),
            collection_date=self._timestamp(data["collection_date"]),
            collector_name=str(data["collector_name"]),
            location_geojson=loc,
            location_crs=str(data["location_crs"]),
            classification=DataClassification(data["classification"]),
            source_reference=str(data["source_reference"]),
            status=str(data["status"]),
            created_at=self._timestamp(data["created_at"]),
        )

    def _hydrate_lab_analysis(self, row: Any) -> SoilLabAnalysis:
        data = (
            dict(row)
            if hasattr(row, "keys")
            else {
                "id": row[0],
                "tenant_id": row[1],
                "sample_point_id": row[2],
                "lab_name": row[3],
                "report_number": row[4],
                "report_date": str(row[5]),
                "ph_h2o": row[6],
                "ph_cacl2": row[7],
                "organic_matter_g_dm3": row[8],
                "phosphorus_mg_dm3": row[9],
                "potassium_cmolc_dm3": row[10],
                "calcium_cmolc_dm3": row[11],
                "magnesium_cmolc_dm3": row[12],
                "aluminum_cmolc_dm3": row[13],
                "potential_acidity_h_al": row[14],
                "cation_exchange_capacity_cec": row[15],
                "base_saturation_percent": row[16],
                "clay_percent": row[17],
                "silt_percent": row[18],
                "sand_percent": row[19],
                "raw_attributes": row[20],
                "classification": row[21],
                "created_at": str(row[22]),
            }
        )
        raw = data["raw_attributes"]
        if isinstance(raw, str):
            raw = json.loads(raw)
        return SoilLabAnalysis(
            id=str(data["id"]),
            tenant_id=str(data["tenant_id"]),
            sample_point_id=str(data["sample_point_id"]),
            lab_name=str(data["lab_name"]),
            report_number=str(data["report_number"]),
            report_date=self._timestamp(data["report_date"]),
            ph_h2o=float(data["ph_h2o"]) if data["ph_h2o"] is not None else None,
            ph_cacl2=float(data["ph_cacl2"]) if data["ph_cacl2"] is not None else None,
            organic_matter_g_dm3=float(data["organic_matter_g_dm3"])
            if data["organic_matter_g_dm3"] is not None
            else None,
            phosphorus_mg_dm3=float(data["phosphorus_mg_dm3"])
            if data["phosphorus_mg_dm3"] is not None
            else None,
            potassium_cmolc_dm3=float(data["potassium_cmolc_dm3"])
            if data["potassium_cmolc_dm3"] is not None
            else None,
            calcium_cmolc_dm3=float(data["calcium_cmolc_dm3"])
            if data["calcium_cmolc_dm3"] is not None
            else None,
            magnesium_cmolc_dm3=float(data["magnesium_cmolc_dm3"])
            if data["magnesium_cmolc_dm3"] is not None
            else None,
            aluminum_cmolc_dm3=float(data["aluminum_cmolc_dm3"])
            if data["aluminum_cmolc_dm3"] is not None
            else None,
            potential_acidity_h_al=float(data["potential_acidity_h_al"])
            if data["potential_acidity_h_al"] is not None
            else None,
            cation_exchange_capacity_cec=float(data["cation_exchange_capacity_cec"])
            if data["cation_exchange_capacity_cec"] is not None
            else None,
            base_saturation_percent=float(data["base_saturation_percent"])
            if data["base_saturation_percent"] is not None
            else None,
            clay_percent=float(data["clay_percent"])
            if data["clay_percent"] is not None
            else None,
            silt_percent=float(data["silt_percent"])
            if data["silt_percent"] is not None
            else None,
            sand_percent=float(data["sand_percent"])
            if data["sand_percent"] is not None
            else None,
            raw_attributes=raw or {},
            classification=DataClassification(data["classification"]),
            created_at=self._timestamp(data["created_at"]),
        )
