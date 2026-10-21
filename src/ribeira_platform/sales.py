"""Sales and receivables (vendas e recebimentos).

Evidence-First sale and payment records. Records are append-only and tenant
scoped. An amount, quantity, price or due date that was not informed stays None
(UNKNOWN): the total is never computed from quantity times price, and an
unknown total never produces a balance. A correction is a new record that
supersedes the previous one. A payment points to the sale version it was
registered against; balances follow the correction chain of the sale.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
import math
from typing import Any, Iterable

from .epistemology import DataClassification
from .harvest import clean_optional, parse_filter_date
from .models import now_utc

SALE_UNITS = ("BOXES", "KG", "BUNCHES")


class SalesValidationError(ValueError):
    pass


class SalesConflict(ValueError):
    """The record was already corrected, or targets a superseded sale."""


@dataclass(frozen=True)
class SaleRecord:
    id: str
    tenant_id: str
    property_id: str
    sale_date: str
    buyer_name: str
    quantity: float | None
    quantity_unit: str | None
    unit_price_brl: float | None
    price_unit: str | None
    total_amount_brl: float | None
    expected_payment_date: str | None
    recorded_by: str
    source_reference: str
    classification: DataClassification
    notes: str | None = None
    supersedes_id: str | None = None
    created_at: str = field(default_factory=now_utc)


@dataclass(frozen=True)
class PaymentRecord:
    id: str
    tenant_id: str
    property_id: str
    sale_id: str
    payment_date: str
    amount_brl: float
    method: str | None
    recorded_by: str
    source_reference: str
    classification: DataClassification
    notes: str | None = None
    supersedes_id: str | None = None
    created_at: str = field(default_factory=now_utc)


def _number(value: Any, name: str, *, positive: bool = False) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or value < 0
        or (positive and value == 0)
    ):
        kind = "positive" if positive else "non-negative"
        raise SalesValidationError(f"{name} must be a {kind} number")
    return round(float(value), 3)


def _money(value: Any, name: str, *, positive: bool = False) -> float:
    _number(value, name, positive=positive)
    return round(float(value), 2)


def _unit(value: str | None, name: str) -> str:
    if value not in SALE_UNITS:
        raise SalesValidationError(f"{name} must be one of {', '.join(SALE_UNITS)}")
    return value


def validate_sale(
    *,
    sale_date: str,
    quantity: float | None,
    quantity_unit: str | None,
    unit_price_brl: float | None,
    price_unit: str | None,
    total_amount_brl: float | None,
    expected_payment_date: str | None,
) -> tuple[
    float | None, str | None, float | None, str | None, float | None, str | None
]:
    """Validate a sale; absent values stay None and nothing is computed."""
    if (quantity is None) != (quantity_unit is None):
        raise SalesValidationError(
            "quantity and quantity_unit must be informed together or both left out"
        )
    if (unit_price_brl is None) != (price_unit is None):
        raise SalesValidationError(
            "unit_price_brl and price_unit must be informed together or both left out"
        )
    if quantity is None and total_amount_brl is None:
        raise SalesValidationError(
            "inform the quantity or the total amount of the sale"
        )
    amount = qty_unit = price = price_u = total = None
    if quantity is not None:
        amount = _number(quantity, "quantity")
        qty_unit = _unit(quantity_unit, "quantity_unit")
    if unit_price_brl is not None:
        price = _money(unit_price_brl, "unit_price_brl")
        price_u = _unit(price_unit, "price_unit")
    if total_amount_brl is not None:
        total = _money(total_amount_brl, "total_amount_brl")
    due: str | None = None
    if expected_payment_date is not None:
        due = parse_filter_date(expected_payment_date, label="expected_payment_date")
        if due is not None and due < sale_date:
            raise SalesValidationError(
                "expected_payment_date cannot be before the sale date"
            )
    return amount, qty_unit, price, price_u, total, due


def validate_payment_amount(amount_brl: float) -> float:
    return _money(amount_brl, "amount_brl", positive=True)


def _chain_roots(sales: list[SaleRecord]) -> dict[str, str]:
    by_id = {item.id: item for item in sales}
    roots: dict[str, str] = {}
    for item in sales:
        current = item
        seen = {current.id}
        while current.supersedes_id and current.supersedes_id in by_id:
            current = by_id[current.supersedes_id]
            if current.id in seen:
                break
            seen.add(current.id)
        roots[item.id] = current.id
    return roots


def _status(total: float | None, received: float) -> str:
    if total is None:
        return "AMOUNT_UNKNOWN"
    if received == 0:
        return "OPEN"
    if round(received, 2) < round(total, 2):
        return "PARTIAL"
    if round(received, 2) == round(total, 2):
        return "PAID"
    return "OVERPAID"


def summarize_sales(
    *,
    property_id: str,
    all_sales: list[SaleRecord],
    payments: list[PaymentRecord],
    date_from: str | None,
    date_to: str | None,
    as_of: date,
) -> dict[str, Any]:
    """Receivables for current sales in a period.

    Totals add only informed amounts. A sale without a total has no balance and
    is never counted as paid, open or zero. Quantities and prices are grouped by
    unit and never combined across units. Payments registered against any
    version of a sale count for its current version.
    """
    roots = _chain_roots(all_sales)
    superseded = {item.supersedes_id for item in all_sales if item.supersedes_id}
    current = [item for item in all_sales if item.id not in superseded]
    in_period = [
        item
        for item in current
        if (date_from is None or item.sale_date >= date_from)
        and (date_to is None or item.sale_date <= date_to)
    ]
    paid_by_root: dict[str, float] = {}
    for payment in payments:
        root = roots.get(payment.sale_id)
        if root is not None:
            paid_by_root[root] = paid_by_root.get(root, 0.0) + payment.amount_brl

    today = as_of.isoformat()
    sales_out: list[dict[str, Any]] = []
    quantity_by_unit: dict[str, float] = {}
    latest_price: dict[str, dict[str, Any]] = {}
    by_buyer: dict[str, dict[str, Any]] = {}
    totals_known: list[float] = []
    outstanding = overdue = 0.0
    received_on_known = received_on_unknown = 0.0
    status_counts: dict[str, int] = {}
    for sale in sorted(in_period, key=lambda item: (item.sale_date, item.created_at)):
        received = round(paid_by_root.get(roots[sale.id], 0.0), 2)
        status = _status(sale.total_amount_brl, received)
        balance = (
            round(sale.total_amount_brl - received, 2)
            if sale.total_amount_brl is not None
            else None
        )
        is_overdue = (
            balance is not None
            and balance > 0
            and sale.expected_payment_date is not None
            and sale.expected_payment_date < today
        )
        status_counts[status] = status_counts.get(status, 0) + 1
        if sale.total_amount_brl is not None:
            totals_known.append(sale.total_amount_brl)
            received_on_known += received
            if balance is not None and balance > 0:
                outstanding += balance
                if is_overdue:
                    overdue += balance
        else:
            received_on_unknown += received
        if sale.quantity is not None and sale.quantity_unit is not None:
            quantity_by_unit[sale.quantity_unit] = round(
                quantity_by_unit.get(sale.quantity_unit, 0.0) + sale.quantity, 3
            )
        if sale.unit_price_brl is not None and sale.price_unit is not None:
            previous = latest_price.get(sale.price_unit)
            if previous is None or sale.sale_date >= previous["sale_date"]:
                latest_price[sale.price_unit] = {
                    "sale_date": sale.sale_date,
                    "unit_price_brl": sale.unit_price_brl,
                }
        key = sale.buyer_name.casefold()
        buyer = by_buyer.setdefault(
            key,
            {"buyer_name": sale.buyer_name, "sale_count": 0, "outstanding_brl": 0.0},
        )
        buyer["sale_count"] += 1
        if balance is not None and balance > 0:
            buyer["outstanding_brl"] = round(buyer["outstanding_brl"] + balance, 2)
        sales_out.append(
            {
                "sale_id": sale.id,
                "sale_date": sale.sale_date,
                "buyer_name": sale.buyer_name,
                "quantity": sale.quantity,
                "quantity_unit": sale.quantity_unit,
                "unit_price_brl": sale.unit_price_brl,
                "price_unit": sale.price_unit,
                "total_amount_brl": sale.total_amount_brl,
                "expected_payment_date": sale.expected_payment_date,
                "received_brl": received,
                "balance_brl": balance,
                "status": status,
                "overdue": is_overdue,
            }
        )
    return {
        "property_id": property_id,
        "date_from": date_from,
        "date_to": date_to,
        "as_of": today,
        "classification": DataClassification.CALCULATED.value,
        "sale_count": len(in_period),
        "sales": sales_out,
        "status_counts": status_counts,
        "total_known_brl": round(sum(totals_known), 2) if totals_known else None,
        "sales_without_total": sum(
            1 for item in in_period if item.total_amount_brl is None
        ),
        "received_on_known_total_brl": round(received_on_known, 2),
        "received_on_unknown_total_brl": round(received_on_unknown, 2),
        "outstanding_brl": round(outstanding, 2) if totals_known else None,
        "overdue_brl": round(overdue, 2) if totals_known else None,
        "quantity_by_unit": quantity_by_unit,
        "latest_price_by_unit": latest_price,
        "by_buyer": sorted(by_buyer.values(), key=lambda item: item["buyer_name"]),
        "limitations": [
            "totals add only amounts that were informed; a sale without a total has no balance and is not counted as open, paid or zero",
            "the total is never computed from quantity times unit price",
            "quantities and prices are grouped by unit and never combined across units",
            "overdue means the expected payment date passed with a positive balance; sales without an expected date are never overdue",
            "only current records are summarized; corrected records are kept as history",
        ],
    }


SQLITE_SALES_SCHEMA = """
CREATE TABLE IF NOT EXISTS sale_record (
 id TEXT PRIMARY KEY,
 tenant_id TEXT NOT NULL,
 property_id TEXT NOT NULL,
 sale_date TEXT NOT NULL,
 buyer_name TEXT NOT NULL,
 quantity REAL,
 quantity_unit TEXT,
 unit_price_brl REAL,
 price_unit TEXT,
 total_amount_brl REAL,
 expected_payment_date TEXT,
 recorded_by TEXT NOT NULL,
 source_reference TEXT NOT NULL,
 classification TEXT NOT NULL,
 notes TEXT,
 supersedes_id TEXT,
 created_at TEXT NOT NULL,
 UNIQUE(tenant_id, id)
);
CREATE INDEX IF NOT EXISTS sale_record_property_idx
 ON sale_record(tenant_id, property_id, sale_date DESC);
CREATE UNIQUE INDEX IF NOT EXISTS sale_record_single_correction_idx
 ON sale_record(tenant_id, supersedes_id) WHERE supersedes_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS payment_record (
 id TEXT PRIMARY KEY,
 tenant_id TEXT NOT NULL,
 property_id TEXT NOT NULL,
 sale_id TEXT NOT NULL,
 payment_date TEXT NOT NULL,
 amount_brl REAL NOT NULL,
 method TEXT,
 recorded_by TEXT NOT NULL,
 source_reference TEXT NOT NULL,
 classification TEXT NOT NULL,
 notes TEXT,
 supersedes_id TEXT,
 created_at TEXT NOT NULL,
 UNIQUE(tenant_id, id)
);
CREATE INDEX IF NOT EXISTS payment_record_property_idx
 ON payment_record(tenant_id, property_id, payment_date DESC);
CREATE UNIQUE INDEX IF NOT EXISTS payment_record_single_correction_idx
 ON payment_record(tenant_id, supersedes_id) WHERE supersedes_id IS NOT NULL;
"""

SALE_COLUMNS = (
    "id",
    "tenant_id",
    "property_id",
    "sale_date",
    "buyer_name",
    "quantity",
    "quantity_unit",
    "unit_price_brl",
    "price_unit",
    "total_amount_brl",
    "expected_payment_date",
    "recorded_by",
    "source_reference",
    "classification",
    "notes",
    "supersedes_id",
    "created_at",
)

PAYMENT_COLUMNS = (
    "id",
    "tenant_id",
    "property_id",
    "sale_id",
    "payment_date",
    "amount_brl",
    "method",
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


def _optional_text(value: Any) -> str | None:
    return _text(value) if value is not None else None


def _row(row: Any, columns: tuple[str, ...]) -> dict[str, Any]:
    return dict(row) if hasattr(row, "keys") else dict(zip(columns, row))


class SalesRepository:
    """Append-only repository for sales and payments (SQLite and PostgreSQL)."""

    def __init__(self, store: Any) -> None:
        self.store = store
        self.connection = store.connection
        self.postgres = store.__class__.__name__ == "PostgresStore"
        if not self.postgres:
            self.connection.executescript(SQLITE_SALES_SCHEMA)

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

    def create_sale(self, item: SaleRecord) -> SaleRecord:
        self._insert(
            "sale_record",
            SALE_COLUMNS,
            [
                item.id,
                item.tenant_id,
                item.property_id,
                item.sale_date,
                item.buyer_name,
                item.quantity,
                item.quantity_unit,
                item.unit_price_brl,
                item.price_unit,
                item.total_amount_brl,
                item.expected_payment_date,
                item.recorded_by,
                item.source_reference,
                item.classification.value,
                item.notes,
                item.supersedes_id,
                item.created_at,
            ],
        )
        return item

    def create_payment(self, item: PaymentRecord) -> PaymentRecord:
        self._insert(
            "payment_record",
            PAYMENT_COLUMNS,
            [
                item.id,
                item.tenant_id,
                item.property_id,
                item.sale_id,
                item.payment_date,
                item.amount_brl,
                item.method,
                item.recorded_by,
                item.source_reference,
                item.classification.value,
                item.notes,
                item.supersedes_id,
                item.created_at,
            ],
        )
        return item

    def get_sale(self, tenant_id: str, sale_id: str) -> SaleRecord | None:
        p = self.placeholder
        row = self._execute(
            f"SELECT {', '.join(SALE_COLUMNS)} FROM sale_record "
            f"WHERE tenant_id = {p} AND id = {p}",
            [tenant_id, sale_id],
        ).fetchone()
        return self._hydrate_sale(row) if row else None

    def get_payment(self, tenant_id: str, payment_id: str) -> PaymentRecord | None:
        p = self.placeholder
        row = self._execute(
            f"SELECT {', '.join(PAYMENT_COLUMNS)} FROM payment_record "
            f"WHERE tenant_id = {p} AND id = {p}",
            [tenant_id, payment_id],
        ).fetchone()
        return self._hydrate_payment(row) if row else None

    def _corrected(self, table: str, tenant_id: str, record_id: str) -> bool:
        p = self.placeholder
        return (
            self._execute(
                f"SELECT 1 FROM {table} WHERE tenant_id = {p} AND supersedes_id = {p}",
                [tenant_id, record_id],
            ).fetchone()
            is not None
        )

    def sale_was_corrected(self, tenant_id: str, sale_id: str) -> bool:
        return self._corrected("sale_record", tenant_id, sale_id)

    def payment_was_corrected(self, tenant_id: str, payment_id: str) -> bool:
        return self._corrected("payment_record", tenant_id, payment_id)

    def _list(
        self,
        table: str,
        columns: tuple[str, ...],
        date_column: str,
        tenant_id: str,
        property_id: str,
        extra: list[tuple[str, Any]],
        date_from: str | None,
        date_to: str | None,
        include_superseded: bool,
    ) -> list[Any]:
        p = self.placeholder
        params: list[Any] = [tenant_id, property_id]
        clauses = ["r.tenant_id = " + p, "r.property_id = " + p]
        for column, value in extra:
            clauses.append(f"r.{column} = {p}")
            params.append(value)
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
        return list(
            self._execute(
                f"SELECT {', '.join('r.' + column for column in columns)} "
                f"FROM {table} r WHERE {' AND '.join(clauses)} "
                f"ORDER BY r.{date_column} DESC, r.created_at DESC, r.id",
                params,
            ).fetchall()
        )

    def list_sales(
        self,
        tenant_id: str,
        property_id: str,
        *,
        date_from: str | None = None,
        date_to: str | None = None,
        include_superseded: bool = False,
    ) -> list[SaleRecord]:
        rows = self._list(
            "sale_record",
            SALE_COLUMNS,
            "sale_date",
            tenant_id,
            property_id,
            [],
            date_from,
            date_to,
            include_superseded,
        )
        return [self._hydrate_sale(row) for row in rows]

    def list_payments(
        self,
        tenant_id: str,
        property_id: str,
        *,
        sale_id: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        include_superseded: bool = False,
    ) -> list[PaymentRecord]:
        extra = [("sale_id", sale_id)] if sale_id is not None else []
        rows = self._list(
            "payment_record",
            PAYMENT_COLUMNS,
            "payment_date",
            tenant_id,
            property_id,
            extra,
            date_from,
            date_to,
            include_superseded,
        )
        return [self._hydrate_payment(row) for row in rows]

    @staticmethod
    def _hydrate_sale(row: Any) -> SaleRecord:
        data = _row(row, SALE_COLUMNS)
        return SaleRecord(
            id=str(data["id"]),
            tenant_id=str(data["tenant_id"]),
            property_id=str(data["property_id"]),
            sale_date=_text(data["sale_date"]),
            buyer_name=str(data["buyer_name"]),
            quantity=_optional_float(data["quantity"]),
            quantity_unit=data["quantity_unit"],
            unit_price_brl=_optional_float(data["unit_price_brl"]),
            price_unit=data["price_unit"],
            total_amount_brl=_optional_float(data["total_amount_brl"]),
            expected_payment_date=_optional_text(data["expected_payment_date"]),
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
    def _hydrate_payment(row: Any) -> PaymentRecord:
        data = _row(row, PAYMENT_COLUMNS)
        return PaymentRecord(
            id=str(data["id"]),
            tenant_id=str(data["tenant_id"]),
            property_id=str(data["property_id"]),
            sale_id=str(data["sale_id"]),
            payment_date=_text(data["payment_date"]),
            amount_brl=float(data["amount_brl"]),
            method=data["method"],
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
    "PaymentRecord",
    "SaleRecord",
    "SalesConflict",
    "SalesRepository",
    "SalesValidationError",
    "clean_optional",
    "summarize_sales",
    "validate_payment_amount",
    "validate_sale",
]
