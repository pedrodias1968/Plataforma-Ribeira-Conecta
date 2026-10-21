import type { CostCategory, CostFieldSummary } from "../../api/costs";

export const CATEGORY_LABELS: Record<CostCategory, string> = {
  LABOR: "Mão de obra",
  PESTICIDE: "Defensivos",
  FUEL: "Combustível",
  MAINTENANCE: "Manutenção",
  PACKAGING: "Embalagem",
  TRANSPORT: "Transporte",
  OTHER: "Outro",
};

const REASON_LABELS: Record<NonNullable<CostFieldSummary["cost_per_kg_unavailable_reason"]>, string> = {
  NO_COST_DATA: "sem custo registrado",
  NO_WEIGHT_DATA: "sem peso de colheita",
  SOME_HARVEST_WITHOUT_WEIGHT: "há colheita sem peso informado",
};

const MONEY = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });
const WEIGHT = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 3 });

/** Unknown stays unknown: a missing total is never shown as R$ 0,00. */
export function moneyLabel(value: number | null): string {
  return value === null ? "sem registro" : MONEY.format(value);
}

export function allocatedCostLabel(item: CostFieldSummary): string {
  if (item.allocated_cost_total === null) return "sem registro";
  const partial = item.cost_is_partial
    ? ` (parcial: ${item.fertilization_cost.records_without_value} adubação(ões) sem custo)`
    : "";
  return `${MONEY.format(item.allocated_cost_total)}${partial}`;
}

export function weightLabel(item: CostFieldSummary): string {
  return item.harvest.weight_kg_total === null ? "sem registro" : `${WEIGHT.format(item.harvest.weight_kg_total)} kg`;
}

/** Cost per kg is shown only when the server could compute it; otherwise say why not. */
export function costPerKgLabel(item: CostFieldSummary): string {
  if (item.cost_per_kg !== null) return `${MONEY.format(item.cost_per_kg)}/kg`;
  const reason = item.cost_per_kg_unavailable_reason;
  return reason ? `indisponível — ${REASON_LABELS[reason]}` : "indisponível";
}
