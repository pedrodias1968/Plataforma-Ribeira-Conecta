"""Costs by field (custos por talhão).

Evidence-First manual cost entries. Entries are append-only and tenant scoped.
A cost is allocated to one field or stays property-wide; property-wide costs
are never spread over fields. Fertilizer costs are recorded in the fertilization
module, so manual entries do not accept that category and nothing is counted
twice. A cost per kg is shown only when the cost and the harvest weight of the
field are both known for the period.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Any, Iterable

from .epistemology import DataClassification
from .fertilization import FertilizationRecord
from .harvest import HarvestRecord, clean_optional
from .models import now_utc

COST_CATEGORIES = (
    "LABOR",
    "PESTICIDE",
    "FUEL",
    "MAINTENANCE",
    "PACKAGING",
    "TRANSPORT",
    "OTHER",
)


class CostValidationError(ValueError):
    pass


class CostConflict(ValueError):
    """The entry was already corrected by a newer entry."""


@dataclass(frozen=True)
class CostEntry:
    """One cost, allocated to a field or property-wide (field_id None)."""

    id: str
    tenant_id: str
    property_id: str
    field_id: str | None
    entry_date: str
    category: str
    description: str
    amount_brl: float
    recorded_by: str
    source_reference: str
    classification: DataClassification
    notes: str | None = None
    supersedes_id: str | None = None
    created_at: str = field(default_factory=now_utc)


def validate_cost(
    category: str, amount_brl: float, notes: str | None
) -> tuple[float, str | None]:
    if category == "FERTILIZER":
        raise CostValidationError(
            "fertilizer costs are recorded in the fertilization module"
        )
    if category not in COST_CATEGORIES:
        raise CostValidationError(
            f"category must be one of {', '.join(COST_CATEGORIES)}"
        )
    if (
        isinstance(amount_brl, bool)
        or not isinstance(amount_brl, (int, float))
        or not math.isfinite(amount_brl)
        or amount_brl < 0
    ):
        raise CostValidationError("amount_brl must be a non-negative number")
    cleaned = clean_optional(notes, "notes")
    if category == "OTHER" and cleaned is None:
        raise CostValidationError("notes are required when category is OTHER")
    return round(float(amount_brl), 2), cleaned


def _manual_block(entries: list[CostEntry]) -> dict[str, Any]:
    by_category: dict[str, float] = {}
    for item in entries:
        by_category[item.category] = round(
            by_category.get(item.category, 0.0) + item.amount_brl, 2
        )
    return {
        "entry_count": len(entries),
        "total": round(sum(item.amount_brl for item in entries), 2)
        if entries
        else None,
        "by_category": by_category,
    }


def _fertilization_block(records: list[FertilizationRecord]) -> dict[str, Any]:
    costs = [item.cost_brl for item in records if item.cost_brl is not None]
    return {
        "record_count": len(records),
        "total": round(sum(costs), 2) if costs else None,
        "records_with_value": len(costs),
        "records_without_value": len(records) - len(costs),
    }


def _weight_block(records: list[HarvestRecord]) -> dict[str, Any]:
    weights = [item.weight_kg for item in records if item.weight_kg is not None]
    return {
        "record_count": len(records),
        "weight_kg_total": round(sum(weights), 3) if weights else None,
        "records_with_weight": len(weights),
        "records_without_weight": len(records) - len(weights),
    }


def _allocated(manual: dict[str, Any], fert: dict[str, Any]) -> float | None:
    parts = [value for value in (manual["total"], fert["total"]) if value is not None]
    return round(sum(parts), 2) if parts else None


def _cost_per_kg(
    allocated: float | None, harvest: dict[str, Any]
) -> tuple[float | None, str | None]:
    """Cost per kg only when cost and complete harvest weight are known."""
    if allocated is None:
        return None, "NO_COST_DATA"
    if harvest["record_count"] == 0 or harvest["weight_kg_total"] is None:
        return None, "NO_WEIGHT_DATA"
    if harvest["records_without_weight"] > 0:
        return None, "SOME_HARVEST_WITHOUT_WEIGHT"
    if harvest["weight_kg_total"] <= 0:
        return None, "NO_WEIGHT_DATA"
    return round(allocated / harvest["weight_kg_total"], 4), None


def summarize_costs(
    *,
    property_id: str,
    fields: Iterable[tuple[str, str]],
    entries: list[CostEntry],
    fertilization: list[FertilizationRecord],
    harvest: list[HarvestRecord],
    date_from: str | None,
    date_to: str | None,
) -> dict[str, Any]:
    """Cost per field, property-wide costs apart, and cost per kg when computable."""
    per_field: list[dict[str, Any]] = []
    for field_id, field_name in fields:
        manual = _manual_block([e for e in entries if e.field_id == field_id])
        fert = _fertilization_block(
            [r for r in fertilization if r.field_id == field_id]
        )
        crop = _weight_block([r for r in harvest if r.field_id == field_id])
        allocated = _allocated(manual, fert)
        per_kg, reason = _cost_per_kg(allocated, crop)
        per_field.append(
            {
                "field_id": field_id,
                "field_name": field_name,
                "manual_cost": manual,
                "fertilization_cost": fert,
                "allocated_cost_total": allocated,
                "cost_is_partial": fert["records_without_value"] > 0,
                "harvest": crop,
                "cost_per_kg": per_kg,
                "cost_per_kg_unavailable_reason": reason,
            }
        )
    unallocated = _manual_block([e for e in entries if e.field_id is None])
    return {
        "property_id": property_id,
        "date_from": date_from,
        "date_to": date_to,
        "classification": DataClassification.CALCULATED.value,
        "fields": per_field,
        "unallocated_cost": unallocated,
        "limitations": [
            "totals add only costs that were recorded; a field without cost records has unknown cost, not zero cost",
            "property-wide costs are shown apart and are not spread over fields",
            "fertilizer cost comes from the fertilization records; applications without a cost make the total partial",
            "cost per kg appears only when the field has cost and every harvest record in the period has a weight",
            "costs and harvest are matched by calendar period only; a cost paid in the period may belong to another harvest",
        ],
    }


SQLITE_COST_SCHEMA = """
CREATE TABLE IF NOT EXISTS cost_entry (
 id TEXT PRIMARY KEY,
 tenant_id TEXT NOT NULL,
 property_id TEXT NOT NULL,
 field_id TEXT,
 entry_date TEXT NOT NULL,
 category TEXT NOT NULL,
 description TEXT NOT NULL,
 amount_brl REAL NOT NULL,
 recorded_by TEXT NOT NULL,
 source_reference TEXT NOT NULL,
 classification TEXT NOT NULL,
 notes TEXT,
 supersedes_id TEXT,
 created_at TEXT NOT NULL,
 UNIQUE(tenant_id, id)
);
CREATE INDEX IF NOT EXISTS cost_entry_property_idx
 ON cost_entry(tenant_id, property_id, entry_date DESC);
CREATE UNIQUE INDEX IF NOT EXISTS cost_entry_single_correction_idx
 ON cost_entry(tenant_id, supersedes_id) WHERE supersedes_id IS NOT NULL;
"""

COLUMNS = (
    "id",
    "tenant_id",
    "property_id",
    "field_id",
    "entry_date",
    "category",
    "description",
    "amount_brl",
    "recorded_by",
    "source_reference",
    "classification",
    "notes",
    "supersedes_id",
    "created_at",
)


def _text(value: Any) -> str:
    return value.isoformat() if hasattr(value, "isoformat") else str(value)


class CostRepository:
    """Append-only repository for cost entries (SQLite and PostgreSQL)."""

    def __init__(self, store: Any) -> None:
        self.store = store
        self.connection = store.connection
        self.postgres = store.__class__.__name__ == "PostgresStore"
        if not self.postgres:
            self.connection.executescript(SQLITE_COST_SCHEMA)

    @property
    def placeholder(self) -> str:
        return "%s" if self.postgres else "?"

    def _execute(self, sql: str, params: Iterable[Any] = ()) -> Any:
        return self.connection.execute(sql, tuple(params))

    def create(self, item: CostEntry) -> CostEntry:
        p = self.placeholder
        self._execute(
            f"INSERT INTO cost_entry ({', '.join(COLUMNS)}) "
            f"VALUES ({', '.join([p] * len(COLUMNS))})",
            [
                item.id,
                item.tenant_id,
                item.property_id,
                item.field_id,
                item.entry_date,
                item.category,
                item.description,
                item.amount_brl,
                item.recorded_by,
                item.source_reference,
                item.classification.value,
                item.notes,
                item.supersedes_id,
                item.created_at,
            ],
        )
        return item

    def get(self, tenant_id: str, entry_id: str) -> CostEntry | None:
        p = self.placeholder
        row = self._execute(
            f"SELECT {', '.join(COLUMNS)} FROM cost_entry "
            f"WHERE tenant_id = {p} AND id = {p}",
            [tenant_id, entry_id],
        ).fetchone()
        return self._hydrate(row) if row else None

    def was_corrected(self, tenant_id: str, entry_id: str) -> bool:
        p = self.placeholder
        return (
            self._execute(
                f"SELECT 1 FROM cost_entry WHERE tenant_id = {p} AND supersedes_id = {p}",
                [tenant_id, entry_id],
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
    ) -> list[CostEntry]:
        p = self.placeholder
        params: list[Any] = [tenant_id, property_id]
        clauses = ["r.tenant_id = " + p, "r.property_id = " + p]
        if field_id is not None:
            clauses.append(f"r.field_id = {p}")
            params.append(field_id)
        if date_from is not None:
            clauses.append(f"r.entry_date >= {p}")
            params.append(date_from)
        if date_to is not None:
            clauses.append(f"r.entry_date <= {p}")
            params.append(date_to)
        if not include_superseded:
            clauses.append(
                "NOT EXISTS (SELECT 1 FROM cost_entry s "
                "WHERE s.tenant_id = r.tenant_id AND s.supersedes_id = r.id)"
            )
        rows = self._execute(
            f"SELECT {', '.join('r.' + column for column in COLUMNS)} "
            f"FROM cost_entry r WHERE {' AND '.join(clauses)} "
            "ORDER BY r.entry_date DESC, r.created_at DESC, r.id",
            params,
        ).fetchall()
        return [self._hydrate(row) for row in rows]

    @staticmethod
    def _hydrate(row: Any) -> CostEntry:
        data = dict(row) if hasattr(row, "keys") else dict(zip(COLUMNS, row))
        return CostEntry(
            id=str(data["id"]),
            tenant_id=str(data["tenant_id"]),
            property_id=str(data["property_id"]),
            field_id=str(data["field_id"]) if data["field_id"] else None,
            entry_date=_text(data["entry_date"]),
            category=str(data["category"]),
            description=str(data["description"]),
            amount_brl=float(data["amount_brl"]),
            recorded_by=str(data["recorded_by"]),
            source_reference=str(data["source_reference"]),
            classification=DataClassification(data["classification"]),
            notes=data["notes"],
            supersedes_id=(
                str(data["supersedes_id"]) if data["supersedes_id"] else None
            ),
            created_at=_text(data["created_at"]),
        )
