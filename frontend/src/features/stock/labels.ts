import type { MovementType, StockItem, StockUnit } from "../../api/stock";

export const UNIT_LABELS: Record<StockUnit, string> = {
  KG: "kg",
  L: "litros",
  UNIT: "unidades",
};

export const TYPE_LABELS: Record<MovementType, string> = {
  IN: "Entrada",
  OUT: "Saída",
};

const NUMBER = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 3 });

export function quantityLabel(value: number, unit: StockUnit): string {
  return `${NUMBER.format(value)} ${UNIT_LABELS[unit]}`;
}

/** A negative balance is shown as is and explained, never as zero. */
export function balanceLabel(item: StockItem): string {
  const base = quantityLabel(item.balance, item.unit);
  return item.negative_balance ? `${base} — saída sem entrada registrada` : base;
}

export function formatDate(iso: string): string {
  const [year, month, day] = iso.split("-");
  return `${day}/${month}/${year}`;
}
