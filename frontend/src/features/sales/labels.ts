import type { SaleRow, SaleStatus, SaleUnit } from "../../api/sales";

export const UNIT_LABELS: Record<SaleUnit, string> = {
  BOXES: "caixas",
  KG: "kg",
  BUNCHES: "cachos",
};

export const STATUS_LABELS: Record<SaleStatus, string> = {
  AMOUNT_UNKNOWN: "valor não informado",
  OPEN: "em aberto",
  PARTIAL: "pago em parte",
  PAID: "pago",
  OVERPAID: "pago a mais",
};

const MONEY = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });
const NUMBER = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 3 });

/** Unknown stays unknown: a missing value is never shown as R$ 0,00. */
export function moneyLabel(value: number | null): string {
  return value === null ? "sem registro" : MONEY.format(value);
}

export function quantityLabel(row: SaleRow): string {
  if (row.quantity === null || row.quantity_unit === null) return "sem registro";
  return `${NUMBER.format(row.quantity)} ${UNIT_LABELS[row.quantity_unit]}`;
}

export function statusLabel(row: SaleRow): string {
  const base = STATUS_LABELS[row.status];
  return row.overdue ? `${base} — atrasado` : base;
}

export function formatDate(iso: string | null): string {
  if (!iso) return "sem registro";
  const [year, month, day] = iso.split("-");
  return `${day}/${month}/${year}`;
}
