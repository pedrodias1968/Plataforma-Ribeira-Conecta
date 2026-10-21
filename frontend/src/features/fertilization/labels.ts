import type { FertilizationBlock, ProductType, QuantityUnit } from "../../api/fertilization";

export const PRODUCT_TYPE_LABELS: Record<ProductType, string> = {
  MINERAL_FERTILIZER: "Adubo mineral",
  ORGANIC_FERTILIZER: "Adubo orgânico",
  LIMING: "Calagem",
  FOLIAR: "Foliar",
  OTHER: "Outro",
};

export const UNIT_LABELS: Record<QuantityUnit, string> = {
  KG: "kg",
  G: "g",
  L: "L",
  ML: "mL",
};

const NUMBER = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 3 });
const MONEY = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });

/** Unknown stays unknown: a missing cost is never shown as R$ 0,00. */
export function costLabel(cost: FertilizationBlock["cost_brl"]): string {
  if (cost.total === null) return "sem registro";
  const partial =
    cost.records_without_value > 0
      ? ` (${cost.records_without_value} aplicação(ões) sem custo informado)`
      : "";
  return `${MONEY.format(cost.total)}${partial}`;
}

/** Quantities are listed per unit and never combined across units. */
export function quantityLabel(block: FertilizationBlock): string {
  const entries = Object.entries(block.quantity_by_unit) as [QuantityUnit, number][];
  if (entries.length === 0) return "sem registro";
  const text = entries.map(([unit, total]) => `${NUMBER.format(total)} ${UNIT_LABELS[unit]}`).join(" · ");
  return block.records_without_quantity > 0
    ? `${text} (${block.records_without_quantity} aplicação(ões) sem quantidade)`
    : text;
}

export function dateLabel(value: string | null): string {
  if (!value) return "sem registro";
  const [year, month, day] = value.split("-");
  return `${day}/${month}/${year}`;
}
