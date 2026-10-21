"""Fertilization and inputs by field (adubação e insumos por talhão).

Evidence-First application records. Records are append-only, tenant scoped and
bound to a field of a property. A quantity, area or cost that was not recorded
stays None (UNKNOWN); it is never turned into zero. A correction is a new
record that supersedes the previous one, so history is preserved.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Any, Iterable

from .epistemology import DataClassification
from .harvest import clean_optional, clean_required
from .models import now_utc

PRODUCT_TYPES = (
    "MINERAL_FERTILIZER",
    "ORGANIC_FERTILIZER",
    "LIMING",
    "FOLIAR",
    "OTHER",
)
QUANTITY_UNITS = ("KG", "G", "L", "ML")


class FertilizationValidationError(ValueError):
    pass


class FertilizationConflict(ValueError):
    """The record was already corrected by a newer record."""


@dataclass(frozen=True)
class FertilizationRecord:
    """One application of a product on one field on one date."""

    id: str
    tenant_id: str
    property_id: str
    field_id: str
    application_date: str
    product_name: str
    product_type: str
    quantity: float | None
    quantity_unit: str | None
    area_applied_ha: float | None
    application_method: str | None
    cost_brl: float | None
    applied_by: str
    recorded_by: str
    source_reference: str
    classification: DataClassification
    notes: str | None = None
    supersedes_id: str | None = None
    created_at: str = field(default_factory=now_utc)


def _non_negative(value: Any, name: str, *, positive: bool = False) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or value < 0
        or (positive and value == 0)
    ):
        kind = "positive" if positive else "non-negative"
        raise FertilizationValidationError(f"{name} must be a {kind} number")
    return round(float(value), 3)


def validate_application(
    product_type: str,
    quantity: float | None,
    quantity_unit: str | None,
    area_applied_ha: float | None,
    cost_brl: float | None,
    notes: str | None,
) -> tuple[float | None, str | None, float | None, float | None, str | None]:
    """Validate an application; absent quantity, area and cost stay None."""
    if product_type not in PRODUCT_TYPES:
        raise FertilizationValidationError(
            f"product_type must be one of {', '.join(PRODUCT_TYPES)}"
        )
    if (quantity is None) != (quantity_unit is None):
        raise FertilizationValidationError(
            "quantity and quantity_unit must be informed together or both left out"
        )
    amount: float | None = None
    if quantity is not None:
        assert quantity_unit is not None
        if quantity_unit not in QUANTITY_UNITS:
            raise FertilizationValidationError(
                f"quantity_unit must be one of {', '.join(QUANTITY_UNITS)}"
            )
        amount = _non_negative(quantity, "quantity")
    area = (
        _non_negative(area_applied_ha, "area_applied_ha", positive=True)
        if area_applied_ha is not None
        else None
    )
    cost = _non_negative(cost_brl, "cost_brl") if cost_brl is not None else None
    cleaned_notes = clean_optional(notes, "notes")
    if product_type == "OTHER" and cleaned_notes is None:
        raise FertilizationValidationError(
            "notes are required when product_type is OTHER"
        )
    return amount, quantity_unit, area, cost, cleaned_notes


def _field_block(records: list[FertilizationRecord]) -> dict[str, Any]:
    quantities: dict[str, float] = {}
    for item in records:
        if item.quantity is not None and item.quantity_unit is not None:
            quantities[item.quantity_unit] = round(
                quantities.get(item.quantity_unit, 0.0) + item.quantity, 3
            )
    with_cost = [item.cost_brl for item in records if item.cost_brl is not None]
    return {
        "record_count": len(records),
        "last_application_date": max(
            (item.application_date for item in records), default=None
        ),
        "products": sorted({item.product_name for item in records}),
        "quantity_by_unit": quantities,
        "records_without_quantity": sum(1 for item in records if item.quantity is None),
        "cost_brl": {
            "total": round(sum(with_cost), 2) if with_cost else None,
            "records_with_value": len(with_cost),
            "records_without_value": len(records) - len(with_cost),
        },
    }


def summarize_fertilization(
    *,
    property_id: str,
    fields: Iterable[tuple[str, str]],
    records: list[FertilizationRecord],
    date_from: str | None,
    date_to: str | None,
) -> dict[str, Any]:
    """Aggregate current records per field.

    Quantities are summed per unit and never across units. Cost adds only the
    records that have a cost. No dose per hectare is computed: it would need an
    applied area that is often not recorded.
    """
    per_field: list[dict[str, Any]] = []
    for field_id, field_name in fields:
        field_records = [item for item in records if item.field_id == field_id]
        block = _field_block(field_records)
        block.update(
            {
                "field_id": field_id,
                "field_name": field_name,
                "no_fertilization_records": not field_records,
            }
        )
        per_field.append(block)
    return {
        "property_id": property_id,
        "date_from": date_from,
        "date_to": date_to,
        "classification": DataClassification.CALCULATED.value,
        "fields": per_field,
        "property_totals": _field_block(records),
        "limitations": [
            "totals add only what was recorded; a missing quantity or cost is unknown, not zero",
            "quantities in different units are never combined and no dose per hectare is computed",
            "a field without records in the period has no fertilization evidence; it does not mean it was not fertilized",
            "only current records are summarized; corrected records are kept as history",
        ],
    }


SQLITE_FERTILIZATION_SCHEMA = """
CREATE TABLE IF NOT EXISTS fertilization_record (
 id TEXT PRIMARY KEY,
 tenant_id TEXT NOT NULL,
 property_id TEXT NOT NULL,
 field_id TEXT NOT NULL,
 application_date TEXT NOT NULL,
 product_name TEXT NOT NULL,
 product_type TEXT NOT NULL,
 quantity REAL,
 quantity_unit TEXT,
 area_applied_ha REAL,
 application_method TEXT,
 cost_brl REAL,
 applied_by TEXT NOT NULL,
 recorded_by TEXT NOT NULL,
 source_reference TEXT NOT NULL,
 classification TEXT NOT NULL,
 notes TEXT,
 supersedes_id TEXT,
 created_at TEXT NOT NULL,
 UNIQUE(tenant_id, id)
);
CREATE INDEX IF NOT EXISTS fertilization_record_property_idx
 ON fertilization_record(tenant_id, property_id, application_date DESC);
CREATE UNIQUE INDEX IF NOT EXISTS fertilization_record_single_correction_idx
 ON fertilization_record(tenant_id, supersedes_id) WHERE supersedes_id IS NOT NULL;
"""

COLUMNS = (
    "id",
    "tenant_id",
    "property_id",
    "field_id",
    "application_date",
    "product_name",
    "product_type",
    "quantity",
    "quantity_unit",
    "area_applied_ha",
    "application_method",
    "cost_brl",
    "applied_by",
    "recorded_by",
    "source_reference",
    "classification",
    "notes",
    "supersedes_id",
    "created_at",
)


def _text(value: Any) -> str:
    return value.isoformat() if hasattr(value, "isoformat") else str(value)


def _optional_float(value: Any) -> float | None:
    return float(value) if value is not None else None


class FertilizationRepository:
    """Append-only repository for fertilization records (SQLite and PostgreSQL)."""

    def __init__(self, store: Any) -> None:
        self.store = store
        self.connection = store.connection
        self.postgres = store.__class__.__name__ == "PostgresStore"
        if not self.postgres:
            self.connection.executescript(SQLITE_FERTILIZATION_SCHEMA)

    @property
    def placeholder(self) -> str:
        return "%s" if self.postgres else "?"

    def _execute(self, sql: str, params: Iterable[Any] = ()) -> Any:
        return self.connection.execute(sql, tuple(params))

    def create(self, item: FertilizationRecord) -> FertilizationRecord:
        p = self.placeholder
        self._execute(
            f"INSERT INTO fertilization_record ({', '.join(COLUMNS)}) "
            f"VALUES ({', '.join([p] * len(COLUMNS))})",
            [
                item.id,
                item.tenant_id,
                item.property_id,
                item.field_id,
                item.application_date,
                item.product_name,
                item.product_type,
                item.quantity,
                item.quantity_unit,
                item.area_applied_ha,
                item.application_method,
                item.cost_brl,
                item.applied_by,
                item.recorded_by,
                item.source_reference,
                item.classification.value,
                item.notes,
                item.supersedes_id,
                item.created_at,
            ],
        )
        return item

    def get(self, tenant_id: str, record_id: str) -> FertilizationRecord | None:
        p = self.placeholder
        row = self._execute(
            f"SELECT {', '.join(COLUMNS)} FROM fertilization_record "
            f"WHERE tenant_id = {p} AND id = {p}",
            [tenant_id, record_id],
        ).fetchone()
        return self._hydrate(row) if row else None

    def was_corrected(self, tenant_id: str, record_id: str) -> bool:
        p = self.placeholder
        return (
            self._execute(
                "SELECT 1 FROM fertilization_record "
                f"WHERE tenant_id = {p} AND supersedes_id = {p}",
                [tenant_id, record_id],
            ).fetchone()
            is not None
        )

    def list(
        self,
        tenant_id: str,
        property_id: str,
        *,
        field_id: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        include_superseded: bool = False,
    ) -> list[FertilizationRecord]:
        p = self.placeholder
        params: list[Any] = [tenant_id, property_id]
        clauses = ["r.tenant_id = " + p, "r.property_id = " + p]
        if field_id is not None:
            clauses.append(f"r.field_id = {p}")
            params.append(field_id)
        if date_from is not None:
            clauses.append(f"r.application_date >= {p}")
            params.append(date_from)
        if date_to is not None:
            clauses.append(f"r.application_date <= {p}")
            params.append(date_to)
        if not include_superseded:
            clauses.append(
                "NOT EXISTS (SELECT 1 FROM fertilization_record s "
                "WHERE s.tenant_id = r.tenant_id AND s.supersedes_id = r.id)"
            )
        rows = self._execute(
            f"SELECT {', '.join('r.' + column for column in COLUMNS)} "
            f"FROM fertilization_record r WHERE {' AND '.join(clauses)} "
            "ORDER BY r.application_date DESC, r.created_at DESC, r.id",
            params,
        ).fetchall()
        return [self._hydrate(row) for row in rows]

    @staticmethod
    def _hydrate(row: Any) -> FertilizationRecord:
        data = dict(row) if hasattr(row, "keys") else dict(zip(COLUMNS, row))
        return FertilizationRecord(
            id=str(data["id"]),
            tenant_id=str(data["tenant_id"]),
            property_id=str(data["property_id"]),
            field_id=str(data["field_id"]),
            application_date=_text(data["application_date"]),
            product_name=str(data["product_name"]),
            product_type=str(data["product_type"]),
            quantity=_optional_float(data["quantity"]),
            quantity_unit=data["quantity_unit"],
            area_applied_ha=_optional_float(data["area_applied_ha"]),
            application_method=data["application_method"],
            cost_brl=_optional_float(data["cost_brl"]),
            applied_by=str(data["applied_by"]),
            recorded_by=str(data["recorded_by"]),
            source_reference=str(data["source_reference"]),
            classification=DataClassification(data["classification"]),
            notes=data["notes"],
            supersedes_id=(
                str(data["supersedes_id"]) if data["supersedes_id"] else None
            ),
            created_at=_text(data["created_at"]),
        )


__all__ = [
    "FertilizationConflict",
    "FertilizationRecord",
    "FertilizationRepository",
    "FertilizationValidationError",
    "clean_optional",
    "clean_required",
    "summarize_fertilization",
    "validate_application",
]
