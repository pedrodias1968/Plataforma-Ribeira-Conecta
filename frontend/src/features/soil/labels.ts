import type { SoilLabValueKey } from "../../api/soil";

export const NUMBER = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 3 });

/** Valores do laudo, na ordem em que costumam aparecer. */
export const LAB_FIELDS: Array<{ key: SoilLabValueKey; label: string; unit: string }> = [
  { key: "ph_h2o", label: "pH em água", unit: "" },
  { key: "ph_cacl2", label: "pH em CaCl₂", unit: "" },
  { key: "organic_matter_g_dm3", label: "Matéria orgânica", unit: "g/dm³" },
  { key: "phosphorus_mg_dm3", label: "Fósforo (P)", unit: "mg/dm³" },
  { key: "potassium_cmolc_dm3", label: "Potássio (K)", unit: "cmolc/dm³" },
  { key: "calcium_cmolc_dm3", label: "Cálcio (Ca)", unit: "cmolc/dm³" },
  { key: "magnesium_cmolc_dm3", label: "Magnésio (Mg)", unit: "cmolc/dm³" },
  { key: "aluminum_cmolc_dm3", label: "Alumínio (Al)", unit: "cmolc/dm³" },
  { key: "potential_acidity_h_al", label: "H+Al", unit: "cmolc/dm³" },
  { key: "cation_exchange_capacity_cec", label: "CTC", unit: "cmolc/dm³" },
  { key: "base_saturation_percent", label: "Saturação por bases (V%)", unit: "%" },
  { key: "clay_percent", label: "Argila", unit: "%" },
  { key: "silt_percent", label: "Silte", unit: "%" },
  { key: "sand_percent", label: "Areia", unit: "%" },
];

/** Valor ausente do laudo é "sem registro", nunca zero. */
export function valueLabel(value: number | null | undefined, unit: string): string {
  if (value === null || value === undefined) return "sem registro";
  return unit ? `${NUMBER.format(value)} ${unit}` : NUMBER.format(value);
}

export function formatDate(iso: string): string {
  const [year, month, day] = iso.slice(0, 10).split("-");
  return day && month && year ? `${day}/${month}/${year}` : iso;
}

export function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

/** Texto vazio = desconhecido (null); texto inválido = NaN. */
export function parseOptional(text: string): number | null {
  const trimmed = text.trim().replace(",", ".");
  if (trimmed === "") return null;
  const value = Number(trimmed);
  return Number.isFinite(value) ? value : Number.NaN;
}
