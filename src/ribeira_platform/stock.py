"""Input stock (estoque de insumos).

Evidence-First stock movements. Movements are append-only and tenant scoped.
Quantity is positive; the movement type gives the direction (IN or OUT). The
balance of an item is computed per item name (case-insensitive) and unit, never
across units, and is never clamped at zero: a negative balance is reported as
such because it means the opening stock was not registered. A correction is a
new movement that supersedes the previous one. Stock is independent from the
fertilization records: an application does not move stock by itself.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
import math
from typing import Any, Iterable

from .epistemology import DataClassification
from .harvest import clean_optional
from .models import now_utc

STOCK_UNITS = ("KG", "L", "UNIT")
MOVEMENT_TYPES = ("IN", "OUT")


class StockValidationError(ValueError):
    pass


class StockConflict(ValueError):
    """The movement was already corrected by a newer movement."""


@dataclass(frozen=True)
class StockMovement:
    id: str
    tenant_id: str
    property_id: str
    movement_date: str
    movement_type: str
    item_name: str
    unit: str
    quantity: float
    counterparty: str | None
    recorded_by: str
    source_reference: str
    classification: DataClassification
    notes: str | None = None
    supersedes_id: str | None = None
    created_at: str = field(default_factory=now_utc)


def validate_movement(
    movement_type: str, unit: str, quantity: float, counterparty: str | None
) -> tuple[float, str | None]:
    if movement_type not in MOVEMENT_TYPES:
        raise StockValidationError(
            f"movement_type must be one of {', '.join(MOVEMENT_TYPES)}"
        )
    if unit not in STOCK_UNITS:
        raise StockValidationError(f"unit must be one of {', '.join(STOCK_UNITS)}")
    if (
        isinstance(quantity, bool)
        or not isinstance(quantity, (int, float))
        or not math.isfinite(quantity)
        or quantity <= 0
    ):
        raise StockValidationError("quantity must be a number greater than zero")
    return round(float(quantity), 3), clean_optional(counterparty, "counterparty")


def summarize_stock(
    property_id: str,
    movements: list[StockMovement],
    *,
    as_of: date,
) -> dict[str, Any]:
    """Balance per item and unit from the current movements up to ``as_of``."""
    cutoff = as_of.isoformat()
    items: dict[tuple[str, str], dict[str, Any]] = {}
    for move in movements:
        if move.movement_date > cutoff:
            continue
        key = (move.item_name.strip().casefold(), move.unit)
        row = items.setdefault(
            key,
            {
                "item_name": move.item_name,
                "unit": move.unit,
                "entries": 0.0,
                "exits": 0.0,
                "movement_count": 0,
                "last_movement_date": move.movement_date,
            },
        )
        if move.movement_type == "IN":
            row["entries"] += move.quantity
        else:
            row["exits"] += move.quantity
        row["movement_count"] += 1
        row["last_movement_date"] = max(row["last_movement_date"], move.movement_date)
    out = []
    for row in sorted(
        items.values(), key=lambda r: (r["item_name"].casefold(), r["unit"])
    ):
        balance = round(row["entries"] - row["exits"], 3)
        out.append(
            {
                "item_name": row["item_name"],
                "unit": row["unit"],
                "entries": round(row["entries"], 3),
                "exits": round(row["exits"], 3),
                "balance": balance,
                "negative_balance": balance < 0,
                "movement_count": row["movement_count"],
                "last_movement_date": row["last_movement_date"],
            }
        )
    return {
        "property_id": property_id,
        "as_of": cutoff,
        "classification": DataClassification.CALCULATED.value,
        "items": out,
        "items_with_negative_balance": sum(1 for r in out if r["negative_balance"]),
        "limitations": [
            "O saldo é entradas menos saídas registradas; estoque inicial não registrado não é conhecido.",
            "Saldo negativo indica saída sem entrada registrada; não é ajustado para zero.",
            "Itens com unidades diferentes nunca são somados.",
            "A adubação registrada não baixa o estoque automaticamente.",
        ],
    }


SQLITE_STOCK_SCHEMA = """
CREATE TABLE IF NOT EXISTS stock_movement (
 id TEXT PRIMARY KEY,
 tenant_id TEXT NOT NULL,
 property_id TEXT NOT NULL,
 movement_date TEXT NOT NULL,
 movement_type TEXT NOT NULL,
 item_name TEXT NOT NULL,
 unit TEXT NOT NULL,
 quantity REAL NOT NULL,
 counterparty TEXT,
 recorded_by TEXT NOT NULL,
 source_reference TEXT NOT NULL,
 classification TEXT NOT NULL,
 notes TEXT,
 supersedes_id TEXT,
 created_at TEXT NOT NULL,
 UNIQUE(tenant_id, id)
);
CREATE INDEX IF NOT EXISTS stock_movement_property_idx
 ON stock_movement(tenant_id, property_id, movement_date DESC);
CREATE UNIQUE INDEX IF NOT EXISTS stock_movement_single_correction_idx
 ON stock_movement(tenant_id, supersedes_id) WHERE supersedes_id IS NOT NULL;
"""

STOCK_COLUMNS = (
    "id",
    "tenant_id",
    "property_id",
    "movement_date",
    "movement_type",
    "item_name",
    "unit",
    "quantity",
    "counterparty",
    "recorded_by",
    "source_reference",
    "classification",
    "notes",
    "supersedes_id",
    "created_at",
)


def _text(value: Any) -> str:
    return value.isoformat() if hasattr(value, "isoformat") else str(value)


def _row(row: Any) -> dict[str, Any]:
    return dict(row) if hasattr(row, "keys") else dict(zip(STOCK_COLUMNS, row))


class StockRepository:
    """Append-only repository for stock movements (SQLite and PostgreSQL)."""

    def __init__(self, store: Any) -> None:
        self.store = store
        self.connection = store.connection
        self.postgres = store.__class__.__name__ == "PostgresStore"
        if not self.postgres:
            self.connection.executescript(SQLITE_STOCK_SCHEMA)

    @property
    def placeholder(self) -> str:
        return "%s" if self.postgres else "?"

    def _execute(self, sql: str, params: Iterable[Any] = ()) -> Any:
        return self.connection.execute(sql, tuple(params))

    def create(self, item: StockMovement) -> StockMovement:
        p = self.placeholder
        self._execute(
            f"INSERT INTO stock_movement ({', '.join(STOCK_COLUMNS)}) "
            f"VALUES ({', '.join([p] * len(STOCK_COLUMNS))})",
            [
                item.id,
                item.tenant_id,
                item.property_id,
                item.movement_date,
                item.movement_type,
                item.item_name,
                item.unit,
                item.quantity,
                item.counterparty,
                item.recorded_by,
                item.source_reference,
                item.classification.value,
                item.notes,
                item.supersedes_id,
                item.created_at,
            ],
        )
        return item

    def _hydrate(self, row: Any) -> StockMovement:
        data = _row(row)
        return StockMovement(
            id=_text(data["id"]),
            tenant_id=_text(data["tenant_id"]),
            property_id=_text(data["property_id"]),
            movement_date=_text(data["movement_date"]),
            movement_type=data["movement_type"],
            item_name=data["item_name"],
            unit=data["unit"],
            quantity=float(data["quantity"]),
            counterparty=data["counterparty"],
            recorded_by=data["recorded_by"],
            source_reference=data["source_reference"],
            classification=DataClassification(data["classification"]),
            notes=data["notes"],
            supersedes_id=_text(data["supersedes_id"])
            if data["supersedes_id"] is not None
            else None,
            created_at=_text(data["created_at"]),
        )

    def get(self, tenant_id: str, movement_id: str) -> StockMovement | None:
        p = self.placeholder
        row = self._execute(
            f"SELECT {', '.join(STOCK_COLUMNS)} FROM stock_movement "
            f"WHERE tenant_id = {p} AND id = {p}",
            [tenant_id, movement_id],
        ).fetchone()
        return self._hydrate(row) if row else None

    def was_corrected(self, tenant_id: str, movement_id: str) -> bool:
        p = self.placeholder
        return (
            self._execute(
                f"SELECT 1 FROM stock_movement WHERE tenant_id = {p} AND supersedes_id = {p}",
                [tenant_id, movement_id],
            ).fetchone()
            is not None
        )

    def list(
        self,
        tenant_id: str,
        property_id: str,
        *,
        date_from: str | None = None,
        date_to: str | None = None,
        include_superseded: bool = False,
    ) -> list[StockMovement]:
        p = self.placeholder
        params: list[Any] = [tenant_id, property_id]
        clauses = ["r.tenant_id = " + p, "r.property_id = " + p]
        if date_from is not None:
            clauses.append(f"r.movement_date >= {p}")
            params.append(date_from)
        if date_to is not None:
            clauses.append(f"r.movement_date <= {p}")
            params.append(date_to)
        if not include_superseded:
            clauses.append(
                "NOT EXISTS (SELECT 1 FROM stock_movement s "
                "WHERE s.tenant_id = r.tenant_id AND s.supersedes_id = r.id)"
            )
        rows = self._execute(
            f"SELECT {', '.join('r.' + c for c in STOCK_COLUMNS)} FROM stock_movement r "
            f"WHERE {' AND '.join(clauses)} "
            "ORDER BY r.movement_date DESC, r.created_at DESC, r.id",
            params,
        ).fetchall()
        return [self._hydrate(row) for row in rows]


__all__ = [
    "StockConflict",
    "StockMovement",
    "StockRepository",
    "StockValidationError",
    "summarize_stock",
    "validate_movement",
]
