import type { RecordItem, RecordKind } from "../../api/corrections";

export interface FieldDef {
  key: string;
  label: string;
  kind: "text" | "date" | "int" | "number" | "select";
  required?: boolean;
  /** Number must be greater than zero (otherwise zero or more). */
  positive?: boolean;
  options?: Array<{ value: string; label: string }>;
}

export interface KindConfig {
  label: string;
  fields: FieldDef[];
  describe: (item: RecordItem, fieldName: (id: unknown) => string) => string;
}

const opts = (pairs: Array<[string, string]>) => pairs.map(([value, label]) => ({ value, label }));
const UNITS3 = opts([["BOXES", "caixas"], ["KG", "kg"], ["BUNCHES", "cachos"]]);
const notes: FieldDef = { key: "notes", label: "Observações", kind: "text" };
const txt = (value: unknown): string => (value === null || value === undefined || value === "" ? "sem registro" : String(value));

export const KINDS: Record<RecordKind, KindConfig> = {
  harvest: {
    label: "Colheita",
    fields: [
      { key: "harvest_date", label: "Data da colheita", kind: "date", required: true },
      { key: "bunches_harvested", label: "Cachos colhidos", kind: "int" },
      { key: "boxes_packed", label: "Caixas embaladas", kind: "int" },
      { key: "weight_kg", label: "Peso (kg)", kind: "number" },
      { key: "cut_criterion", label: "Critério de corte", kind: "text" },
      notes,
    ],
    describe: (i, name) => `${txt(i.harvest_date)} — ${name(i.field_id)} — ${txt(i.boxes_packed)} caixas, ${txt(i.weight_kg)} kg`,
  },
  discard: {
    label: "Descarte",
    fields: [
      { key: "discard_date", label: "Data do descarte", kind: "date", required: true },
      {
        key: "reason", label: "Motivo", kind: "select", required: true,
        options: opts([["STAIN", "Mancha"], ["MECHANICAL_DAMAGE", "Dano mecânico"], ["CALIBER", "Calibre"], ["OTHER", "Outro"]]),
      },
      { key: "quantity", label: "Quantidade", kind: "number", required: true },
      { key: "unit", label: "Unidade", kind: "select", required: true, options: UNITS3 },
      notes,
    ],
    describe: (i, name) => `${txt(i.discard_date)} — ${name(i.field_id)} — ${txt(i.quantity)} ${txt(i.unit)}`,
  },
  fertilization: {
    label: "Adubação",
    fields: [
      { key: "application_date", label: "Data da aplicação", kind: "date", required: true },
      { key: "product_name", label: "Produto", kind: "text", required: true },
      {
        key: "product_type", label: "Tipo de produto", kind: "select", required: true,
        options: opts([
          ["MINERAL_FERTILIZER", "Adubo mineral"], ["ORGANIC_FERTILIZER", "Adubo orgânico"],
          ["LIMING", "Calagem"], ["FOLIAR", "Foliar"], ["OTHER", "Outro"],
        ]),
      },
      { key: "quantity", label: "Quantidade", kind: "number" },
      { key: "quantity_unit", label: "Unidade", kind: "select", options: opts([["KG", "kg"], ["G", "g"], ["L", "litros"], ["ML", "ml"]]) },
      { key: "area_applied_ha", label: "Área aplicada (ha)", kind: "number", positive: true },
      { key: "application_method", label: "Forma de aplicação", kind: "text" },
      { key: "cost_brl", label: "Custo (R$)", kind: "number" },
      { key: "applied_by", label: "Aplicado por", kind: "text", required: true },
      notes,
    ],
    describe: (i, name) => `${txt(i.application_date)} — ${name(i.field_id)} — ${txt(i.product_name)}`,
  },
  cost: {
    label: "Custo",
    fields: [
      { key: "entry_date", label: "Data", kind: "date", required: true },
      {
        key: "category", label: "Categoria", kind: "select", required: true,
        options: opts([
          ["LABOR", "Mão de obra"], ["PESTICIDE", "Defensivos"], ["FUEL", "Combustível"], ["MAINTENANCE", "Manutenção"],
          ["PACKAGING", "Embalagem"], ["TRANSPORT", "Transporte"], ["OTHER", "Outro"],
        ]),
      },
      { key: "description", label: "Descrição", kind: "text", required: true },
      { key: "amount_brl", label: "Valor (R$)", kind: "number", required: true },
      notes,
    ],
    describe: (i) => `${txt(i.entry_date)} — ${txt(i.description)} — R$ ${txt(i.amount_brl)}`,
  },
  sale: {
    label: "Venda",
    fields: [
      { key: "sale_date", label: "Data da venda", kind: "date", required: true },
      { key: "buyer_name", label: "Comprador", kind: "text", required: true },
      { key: "quantity", label: "Quantidade", kind: "number" },
      { key: "quantity_unit", label: "Unidade da quantidade", kind: "select", options: UNITS3 },
      { key: "unit_price_brl", label: "Preço por unidade (R$)", kind: "number" },
      { key: "price_unit", label: "Unidade do preço", kind: "select", options: UNITS3 },
      { key: "total_amount_brl", label: "Valor total (R$)", kind: "number" },
      { key: "expected_payment_date", label: "Previsão de pagamento", kind: "date" },
      notes,
    ],
    describe: (i) => `${txt(i.sale_date)} — ${txt(i.buyer_name)} — total R$ ${txt(i.total_amount_brl)}`,
  },
  payment: {
    label: "Recebimento",
    fields: [
      { key: "payment_date", label: "Data do recebimento", kind: "date", required: true },
      { key: "amount_brl", label: "Valor recebido (R$)", kind: "number", required: true, positive: true },
      { key: "method", label: "Forma (Pix, dinheiro…)", kind: "text" },
      notes,
    ],
    describe: (i) => `${txt(i.payment_date)} — R$ ${txt(i.amount_brl)}`,
  },
  stock: {
    label: "Estoque",
    fields: [
      { key: "movement_date", label: "Data", kind: "date", required: true },
      { key: "movement_type", label: "Tipo", kind: "select", required: true, options: opts([["IN", "Entrada"], ["OUT", "Saída"]]) },
      { key: "item_name", label: "Insumo", kind: "text", required: true },
      { key: "unit", label: "Unidade", kind: "select", required: true, options: opts([["KG", "kg"], ["L", "litros"], ["UNIT", "unidades"]]) },
      { key: "quantity", label: "Quantidade", kind: "number", required: true, positive: true },
      { key: "counterparty", label: "Fornecedor ou destino", kind: "text" },
      notes,
    ],
    describe: (i) => `${txt(i.movement_date)} — ${i.movement_type === "OUT" ? "Saída" : "Entrada"} — ${txt(i.item_name)} — ${txt(i.quantity)} ${txt(i.unit)}`,
  },
};

/** Turns the typed strings into the API payload; unknown optional values become null, never zero. */
export function buildPayload(
  config: KindConfig,
  values: Record<string, string>,
): { payload: Record<string, unknown> } | { error: string } {
  const payload: Record<string, unknown> = {};
  for (const def of config.fields) {
    const raw = (values[def.key] ?? "").trim();
    if (raw === "") {
      if (def.required) return { error: `Preencha: ${def.label}.` };
      payload[def.key] = null;
      continue;
    }
    if (def.kind === "int" || def.kind === "number") {
      const value = Number(raw.replace(",", "."));
      const minOk = def.positive ? value > 0 : value >= 0;
      if (!Number.isFinite(value) || !minOk || (def.kind === "int" && !Number.isInteger(value))) {
        return { error: `Valor inválido em: ${def.label}.` };
      }
      payload[def.key] = value;
    } else {
      payload[def.key] = raw;
    }
  }
  for (const [key, label] of [
    ["recorded_by", "Corrigido por"],
    ["source_reference", "Origem da correção"],
    ["correction_reason", "Motivo da correção"],
  ] as const) {
    const raw = (values[key] ?? "").trim();
    if (!raw) return { error: `Preencha: ${label}.` };
    payload[key] = raw;
  }
  return { payload };
}
