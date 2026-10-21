"""Harvest by field (colheita por talhão).

Evidence-First harvest and discard records. Records are append-only, tenant
scoped and bound to a field of a property. A measure that was not recorded
stays None (UNKNOWN); it is never turned into zero. A correction is a new
record that supersedes the previous one, so history is preserved.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
import math
from typing import Any, Iterable

from .epistemology import DataClassification
from .models import now_utc

DISCARD_REASONS = ("STAIN", "MECHANICAL_DAMAGE", "CALIBER", "OTHER")
DISCARD_UNITS = ("BOXES", "KG", "BUNCHES")


class HarvestValidationError(ValueError):
    pass


class HarvestConflict(ValueError):
    """The record was already corrected by a newer record."""


@dataclass(frozen=True)
class HarvestRecord:
    """Harvest of one field on one date, with only the measures actually recorded."""

    id: str
    tenant_id: str
    property_id: str
    field_id: str
    harvest_date: str
    bunches_harvested: int | None
    boxes_packed: int | None
    weight_kg: float | None
    cut_criterion: str | None
    recorded_by: str
    source_reference: str
    classification: DataClassification
    notes: str | None = None
    supersedes_id: str | None = None
    created_at: str = field(default_factory=now_utc)


@dataclass(frozen=True)
class HarvestDiscard:
    """Discarded fruit of one field on one date, with reason and unit."""

    id: str
    tenant_id: str
    property_id: str
    field_id: str
    discard_date: str
    reason: str
    quantity: float
    unit: str
    recorded_by: str
    source_reference: str
    classification: DataClassification
    notes: str | None = None
    supersedes_id: str | None = None
    created_at: str = field(default_factory=now_utc)


# A harvest or discard entry is a person's or an instrument's observation. It must
# never be recorded as a calculated, inferred or predicted value.
ALLOWED_CLASSIFICATIONS = (
    DataClassification.OBSERVED,
    DataClassification.MANUAL_CONFIRMED,
)


def validate_classification(value: DataClassification) -> DataClassification:
    if value not in ALLOWED_CLASSIFICATIONS:
        allowed = ", ".join(item.value for item in ALLOWED_CLASSIFICATIONS)
        raise HarvestValidationError(f"classification must be one of {allowed}")
    return value


def parse_filter_date(value: str | None, *, label: str) -> str | None:
    """Date filter: YYYY-MM-DD, no future restriction."""
    if value is None:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date().isoformat()
    except (TypeError, ValueError):
        raise HarvestValidationError(f"{label} must be an ISO date (YYYY-MM-DD)")


def parse_record_date(value: str, *, label: str, today: date | None = None) -> str:
    """Accept only YYYY-MM-DD and reject dates after tomorrow (UTC)."""
    try:
        parsed = datetime.strptime(value, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        raise HarvestValidationError(f"{label} must be an ISO date (YYYY-MM-DD)")
    reference = today or datetime.now(timezone.utc).date()
    # One day of tolerance absorbs the difference between local and UTC dates.
    if parsed > reference + timedelta(days=1):
        raise HarvestValidationError(f"{label} cannot be in the future")
    return parsed.isoformat()


def _clean_text(value: str | None, *, label: str, required: bool) -> str | None:
    if value is None:
        if required:
            raise HarvestValidationError(f"{label} is required")
        return None
    cleaned = value.strip()
    if not cleaned:
        if required:
            raise HarvestValidationError(f"{label} is required")
        return None
    return cleaned


def validate_harvest_measures(
    bunches_harvested: int | None,
    boxes_packed: int | None,
    weight_kg: float | None,
) -> tuple[int | None, int | None, float | None]:
    """At least one measure is required; absent measures stay None."""
    if bunches_harvested is None and boxes_packed is None and weight_kg is None:
        raise HarvestValidationError(
            "at least one of bunches_harvested, boxes_packed or weight_kg must be informed"
        )
    for name, value in (
        ("bunches_harvested", bunches_harvested),
        ("boxes_packed", boxes_packed),
    ):
        if value is not None and (
            isinstance(value, bool) or not isinstance(value, int) or value < 0
        ):
            raise HarvestValidationError(f"{name} must be a non-negative integer")
    weight: float | None = None
    if weight_kg is not None:
        if (
            isinstance(weight_kg, bool)
            or not isinstance(weight_kg, (int, float))
            or not math.isfinite(weight_kg)
            or weight_kg < 0
        ):
            raise HarvestValidationError("weight_kg must be a non-negative number")
        weight = round(float(weight_kg), 3)
    return bunches_harvested, boxes_packed, weight


def validate_harvest_discard(
    reason: str, quantity: float, unit: str, notes: str | None
) -> tuple[float, str | None]:
    if reason not in DISCARD_REASONS:
        raise HarvestValidationError(
            f"reason must be one of {', '.join(DISCARD_REASONS)}"
        )
    if unit not in DISCARD_UNITS:
        raise HarvestValidationError(f"unit must be one of {', '.join(DISCARD_UNITS)}")
    if (
        isinstance(quantity, bool)
        or not isinstance(quantity, (int, float))
        or not math.isfinite(quantity)
        or quantity < 0
    ):
        raise HarvestValidationError("quantity must be a non-negative number")
    cleaned_notes = _clean_text(notes, label="notes", required=False)
    if reason == "OTHER" and cleaned_notes is None:
        raise HarvestValidationError("notes are required when reason is OTHER")
    return round(float(quantity), 3), cleaned_notes


def clean_required(value: str, label: str) -> str:
    cleaned = _clean_text(value, label=label, required=True)
    assert cleaned is not None
    return cleaned


def clean_optional(value: str | None, label: str) -> str | None:
    return _clean_text(value, label=label, required=False)


def _measure_summary(values: list[Any], *, integer: bool) -> dict[str, Any]:
    present = [value for value in values if value is not None]
    total: float | int | None = None
    if present:
        total = int(sum(present)) if integer else round(float(sum(present)), 3)
    return {
        "total": total,
        "records_with_value": len(present),
        "records_without_value": len(values) - len(present),
    }


def _discard_summary(discards: list[HarvestDiscard]) -> dict[str, Any]:
    by_unit: dict[str, Any] = {}
    for item in discards:
        unit = by_unit.setdefault(item.unit, {"total": 0.0, "by_reason": {}})
        unit["total"] = round(unit["total"] + item.quantity, 3)
        reasons = unit["by_reason"]
        reasons[item.reason] = round(reasons.get(item.reason, 0.0) + item.quantity, 3)
    return by_unit


def _block(
    records: list[HarvestRecord], discards: list[HarvestDiscard]
) -> dict[str, Any]:
    return {
        "record_count": len(records),
        "discard_record_count": len(discards),
        "bunches_harvested": _measure_summary(
            [item.bunches_harvested for item in records], integer=True
        ),
        "boxes_packed": _measure_summary(
            [item.boxes_packed for item in records], integer=True
        ),
        "weight_kg": _measure_summary(
            [item.weight_kg for item in records], integer=False
        ),
        "discards_by_unit": _discard_summary(discards),
    }


def summarize_harvest(
    *,
    property_id: str,
    fields: Iterable[tuple[str, str]],
    records: list[HarvestRecord],
    discards: list[HarvestDiscard],
    date_from: str | None,
    date_to: str | None,
) -> dict[str, Any]:
    """Aggregate current records per field.

    Totals add only measures that were recorded. Units are never combined and
    no discard percentage is computed, because the denominator is not defined
    by the recorded data.
    """
    per_field: list[dict[str, Any]] = []
    for field_id, field_name in fields:
        field_records = [item for item in records if item.field_id == field_id]
        field_discards = [item for item in discards if item.field_id == field_id]
        block = _block(field_records, field_discards)
        block.update(
            {
                "field_id": field_id,
                "field_name": field_name,
                "no_harvest_records": not field_records,
            }
        )
        per_field.append(block)
    return {
        "property_id": property_id,
        "date_from": date_from,
        "date_to": date_to,
        "classification": DataClassification.CALCULATED.value,
        "fields": per_field,
        "property_totals": _block(records, discards),
        "limitations": [
            "totals add only measures that were actually recorded; a missing measure is unknown, not zero",
            "quantities in different units are never combined and no discard percentage is computed",
            "a field without records in the period has no harvest evidence; it does not mean zero production",
            "only current records are summarized; corrected records are kept as history",
        ],
    }


SQLITE_HARVEST_SCHEMA = """
CREATE TABLE IF NOT EXISTS harvest_record (
 id TEXT PRIMARY KEY,
 tenant_id TEXT NOT NULL,
 property_id TEXT NOT NULL,
 field_id TEXT NOT NULL,
 harvest_date TEXT NOT NULL,
 bunches_harvested INTEGER,
 boxes_packed INTEGER,
 weight_kg REAL,
 cut_criterion TEXT,
 recorded_by TEXT NOT NULL,
 source_reference TEXT NOT NULL,
 classification TEXT NOT NULL,
 notes TEXT,
 supersedes_id TEXT,
 created_at TEXT NOT NULL,
 UNIQUE(tenant_id, id)
);
CREATE INDEX IF NOT EXISTS harvest_record_property_idx
 ON harvest_record(tenant_id, property_id, harvest_date DESC);
CREATE UNIQUE INDEX IF NOT EXISTS harvest_record_single_correction_idx
 ON harvest_record(tenant_id, supersedes_id) WHERE supersedes_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS harvest_discard (
 id TEXT PRIMARY KEY,
 tenant_id TEXT NOT NULL,
 property_id TEXT NOT NULL,
 field_id TEXT NOT NULL,
 discard_date TEXT NOT NULL,
 reason TEXT NOT NULL,
 quantity REAL NOT NULL,
 unit TEXT NOT NULL,
 notes TEXT,
 recorded_by TEXT NOT NULL,
 source_reference TEXT NOT NULL,
 classification TEXT NOT NULL,
 supersedes_id TEXT,
 created_at TEXT NOT NULL,
 UNIQUE(tenant_id, id)
);
CREATE INDEX IF NOT EXISTS harvest_discard_property_idx
 ON harvest_discard(tenant_id, property_id, discard_date DESC);
CREATE UNIQUE INDEX IF NOT EXISTS harvest_discard_single_correction_idx
 ON harvest_discard(tenant_id, supersedes_id) WHERE supersedes_id IS NOT NULL;
"""

RECORD_COLUMNS = (
    "id",
    "tenant_id",
    "property_id",
    "field_id",
    "harvest_date",
    "bunches_harvested",
    "boxes_packed",
    "weight_kg",
    "cut_criterion",
    "recorded_by",
    "source_reference",
    "classification",
    "notes",
    "supersedes_id",
    "created_at",
)

DISCARD_COLUMNS = (
    "id",
    "tenant_id",
    "property_id",
    "field_id",
    "discard_date",
    "reason",
    "quantity",
    "unit",
    "notes",
    "recorded_by",
    "source_reference",
    "classification",
    "supersedes_id",
    "created_at",
)


def _text(value: Any) -> str:
    return value.isoformat() if hasattr(value, "isoformat") else str(value)


def _row(row: Any, columns: tuple[str, ...]) -> dict[str, Any]:
    return dict(row) if hasattr(row, "keys") else dict(zip(columns, row))


class HarvestRepository:
    """Append-only repository for harvest records and discards (SQLite and PostgreSQL)."""

    def __init__(self, store: Any) -> None:
        self.store = store
        self.connection = store.connection
        self.postgres = store.__class__.__name__ == "PostgresStore"
        if not self.postgres:
            self.connection.executescript(SQLITE_HARVEST_SCHEMA)

    @property
    def placeholder(self) -> str:
        return "%s" if self.postgres else "?"

    def _execute(self, sql: str, params: Iterable[Any] = ()) -> Any:
        return self.connection.execute(sql, tuple(params))

    def _insert(self, table: str, columns: tuple[str, ...], values: list[Any]) -> None:
        p = self.placeholder
        self._execute(
            f"INSERT INTO {table} ({', '.join(columns)}) "
            f"VALUES ({', '.join([p] * len(columns))})",
            values,
        )

    def create_record(self, item: HarvestRecord) -> HarvestRecord:
        self._insert(
            "harvest_record",
            RECORD_COLUMNS,
            [
                item.id,
                item.tenant_id,
                item.property_id,
                item.field_id,
                item.harvest_date,
                item.bunches_harvested,
                item.boxes_packed,
                item.weight_kg,
                item.cut_criterion,
                item.recorded_by,
                item.source_reference,
                item.classification.value,
                item.notes,
                item.supersedes_id,
                item.created_at,
            ],
        )
        return item

    def create_discard(self, item: HarvestDiscard) -> HarvestDiscard:
        self._insert(
            "harvest_discard",
            DISCARD_COLUMNS,
            [
                item.id,
                item.tenant_id,
                item.property_id,
                item.field_id,
                item.discard_date,
                item.reason,
                item.quantity,
                item.unit,
                item.notes,
                item.recorded_by,
                item.source_reference,
                item.classification.value,
                item.supersedes_id,
                item.created_at,
            ],
        )
        return item

    def get_record(self, tenant_id: str, record_id: str) -> HarvestRecord | None:
        p = self.placeholder
        row = self._execute(
            f"SELECT {', '.join(RECORD_COLUMNS)} FROM harvest_record "
            f"WHERE tenant_id = {p} AND id = {p}",
            [tenant_id, record_id],
        ).fetchone()
        return self._hydrate_record(row) if row else None

    def get_discard(self, tenant_id: str, discard_id: str) -> HarvestDiscard | None:
        p = self.placeholder
        row = self._execute(
            f"SELECT {', '.join(DISCARD_COLUMNS)} FROM harvest_discard "
            f"WHERE tenant_id = {p} AND id = {p}",
            [tenant_id, discard_id],
        ).fetchone()
        return self._hydrate_discard(row) if row else None

    def record_was_corrected(self, tenant_id: str, record_id: str) -> bool:
        p = self.placeholder
        return (
            self._execute(
                f"SELECT 1 FROM harvest_record WHERE tenant_id = {p} AND supersedes_id = {p}",
                [tenant_id, record_id],
            ).fetchone()
            is not None
        )

    def discard_was_corrected(self, tenant_id: str, discard_id: str) -> bool:
        p = self.placeholder
        return (
            self._execute(
                f"SELECT 1 FROM harvest_discard WHERE tenant_id = {p} AND supersedes_id = {p}",
                [tenant_id, discard_id],
            ).fetchone()
            is not None
        )

    def _list(
        self,
        table: str,
        columns: tuple[str, ...],
        date_column: str,
        tenant_id: str,
        property_id: str,
        field_id: str | None,
        date_from: str | None,
        date_to: str | None,
        include_superseded: bool,
    ) -> list[Any]:
        p = self.placeholder
        params: list[Any] = [tenant_id, property_id]
        clauses = ["r.tenant_id = " + p, "r.property_id = " + p]
        if field_id is not None:
            clauses.append(f"r.field_id = {p}")
            params.append(field_id)
        if date_from is not None:
            clauses.append(f"r.{date_column} >= {p}")
            params.append(date_from)
        if date_to is not None:
            clauses.append(f"r.{date_column} <= {p}")
            params.append(date_to)
        if not include_superseded:
            clauses.append(
                f"NOT EXISTS (SELECT 1 FROM {table} s "
                "WHERE s.tenant_id = r.tenant_id AND s.supersedes_id = r.id)"
            )
        cursor = self._execute(
            f"SELECT {', '.join('r.' + column for column in columns)} "
            f"FROM {table} r WHERE {' AND '.join(clauses)} "
            f"ORDER BY r.{date_column} DESC, r.created_at DESC, r.id",
            params,
        )
        return list(cursor.fetchall())

    def list_records(
        self,
        tenant_id: str,
        property_id: str,
        *,
        field_id: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        include_superseded: bool = False,
    ) -> list[HarvestRecord]:
        rows = self._list(
            "harvest_record",
            RECORD_COLUMNS,
            "harvest_date",
            tenant_id,
            property_id,
            field_id,
            date_from,
            date_to,
            include_superseded,
        )
        return [self._hydrate_record(row) for row in rows]

    def list_discards(
        self,
        tenant_id: str,
        property_id: str,
        *,
        field_id: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        include_superseded: bool = False,
    ) -> list[HarvestDiscard]:
        rows = self._list(
            "harvest_discard",
            DISCARD_COLUMNS,
            "discard_date",
            tenant_id,
            property_id,
            field_id,
            date_from,
            date_to,
            include_superseded,
        )
        return [self._hydrate_discard(row) for row in rows]

    @staticmethod
    def _hydrate_record(row: Any) -> HarvestRecord:
        data = _row(row, RECORD_COLUMNS)
        return HarvestRecord(
            id=str(data["id"]),
            tenant_id=str(data["tenant_id"]),
            property_id=str(data["property_id"]),
            field_id=str(data["field_id"]),
            harvest_date=_text(data["harvest_date"]),
            bunches_harvested=(
                int(data["bunches_harvested"])
                if data["bunches_harvested"] is not None
                else None
            ),
            boxes_packed=(
                int(data["boxes_packed"]) if data["boxes_packed"] is not None else None
            ),
            weight_kg=(
                float(data["weight_kg"]) if data["weight_kg"] is not None else None
            ),
            cut_criterion=data["cut_criterion"],
            recorded_by=str(data["recorded_by"]),
            source_reference=str(data["source_reference"]),
            classification=DataClassification(data["classification"]),
            notes=data["notes"],
            supersedes_id=(
                str(data["supersedes_id"]) if data["supersedes_id"] else None
            ),
            created_at=_text(data["created_at"]),
        )

    @staticmethod
    def _hydrate_discard(row: Any) -> HarvestDiscard:
        data = _row(row, DISCARD_COLUMNS)
        return HarvestDiscard(
            id=str(data["id"]),
            tenant_id=str(data["tenant_id"]),
            property_id=str(data["property_id"]),
            field_id=str(data["field_id"]),
            discard_date=_text(data["discard_date"]),
            reason=str(data["reason"]),
            quantity=float(data["quantity"]),
            unit=str(data["unit"]),
            recorded_by=str(data["recorded_by"]),
            source_reference=str(data["source_reference"]),
            classification=DataClassification(data["classification"]),
            notes=data["notes"],
            supersedes_id=(
                str(data["supersedes_id"]) if data["supersedes_id"] else None
            ),
            created_at=_text(data["created_at"]),
        )
