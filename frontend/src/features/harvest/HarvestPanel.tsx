import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react";

import {
  HarvestApi,
  HarvestApiError,
  type DiscardReason,
  type HarvestBlock,
  type HarvestMeasure,
  type HarvestSummary,
  type HarvestUnit,
} from "../../api/harvest";
import type { FieldContext } from "../../types/farm360";

export const DISCARD_REASON_LABELS: Record<DiscardReason, string> = {
  STAIN: "Mancha",
  MECHANICAL_DAMAGE: "Dano mecânico",
  CALIBER: "Calibre",
  OTHER: "Outro",
};

const UNIT_LABELS: Record<HarvestUnit, string> = {
  BOXES: "caixas",
  KG: "kg",
  BUNCHES: "cachos",
};

const NUMBER = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 3 });

/** Unknown stays unknown: never render a missing total as zero. */
export function measureLabel(measure: HarvestMeasure, unit: string): string {
  if (measure.total === null) return "sem registro";
  const partial =
    measure.records_without_value > 0
      ? ` (${measure.records_without_value} registro(s) sem esta medida)`
      : "";
  return `${NUMBER.format(measure.total)} ${unit}${partial}`;
}

function discardLabel(block: HarvestBlock): string {
  const entries = Object.entries(block.discards_by_unit) as [
    HarvestUnit,
    { total: number; by_reason: Partial<Record<DiscardReason, number>> },
  ][];
  if (entries.length === 0) return "sem registro";
  return entries
    .map(([unit, data]) => {
      const reasons = Object.entries(data.by_reason)
        .map(([reason, quantity]) => `${DISCARD_REASON_LABELS[reason as DiscardReason]} ${NUMBER.format(quantity ?? 0)}`)
        .join(", ");
      return `${NUMBER.format(data.total)} ${UNIT_LABELS[unit]} (${reasons})`;
    })
    .join(" · ");
}

function optionalNumber(value: string): number | null {
  const text = value.trim().replace(",", ".");
  if (text === "") return null;
  const parsed = Number(text);
  return Number.isFinite(parsed) ? parsed : Number.NaN;
}

function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

export function HarvestPanel({ fields, tenantId, propertyId, apiBaseUrl, token, api: injectedApi }: {
  fields: FieldContext[];
  tenantId: string;
  propertyId: string;
  apiBaseUrl: string;
  token: string;
  api?: HarvestApi;
}) {
  const api = useMemo(() => injectedApi ?? new HarvestApi(apiBaseUrl, token), [injectedApi, apiBaseUrl, token]);
  const [summary, setSummary] = useState<HarvestSummary | null>(null);
  const [loadState, setLoadState] = useState<"loading" | "ready" | "forbidden" | "error">("loading");
  const [kind, setKind] = useState<"record" | "discard">("record");
  const [fieldId, setFieldId] = useState("");
  const [date, setDate] = useState(todayIso());
  const [boxes, setBoxes] = useState("");
  const [bunches, setBunches] = useState("");
  const [weight, setWeight] = useState("");
  const [cutCriterion, setCutCriterion] = useState("");
  const [reason, setReason] = useState<DiscardReason>("STAIN");
  const [quantity, setQuantity] = useState("");
  const [unit, setUnit] = useState<HarvestUnit>("BOXES");
  const [recordedBy, setRecordedBy] = useState("");
  const [sourceReference, setSourceReference] = useState("");
  const [notes, setNotes] = useState("");
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setSummary(await api.summary(tenantId, propertyId));
      setLoadState("ready");
    } catch (error) {
      setSummary(null);
      setLoadState(error instanceof HarvestApiError && error.status === 403 ? "forbidden" : "error");
    }
  }, [api, tenantId, propertyId]);

  useEffect(() => {
    void load();
  }, [load]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setMessage(null);
    if (!fieldId) return setMessage("Escolha o talhão.");
    if (!recordedBy.trim() || !sourceReference.trim()) return setMessage("Informe quem registrou e a origem (ex.: caderno, planilha).");
    setSaving(true);
    try {
      if (kind === "record") {
        const measures = [optionalNumber(bunches), optionalNumber(boxes), optionalNumber(weight)];
        if (measures.some((value) => value !== null && (Number.isNaN(value) || value < 0))) {
          return setMessage("Use apenas números iguais ou maiores que zero.");
        }
        if (measures.every((value) => value === null)) {
          return setMessage("Informe ao menos uma medida (cachos, caixas ou peso). Deixe em branco o que não foi medido.");
        }
        await api.createRecord(tenantId, propertyId, {
          field_id: fieldId,
          harvest_date: date,
          bunches_harvested: measures[0],
          boxes_packed: measures[1],
          weight_kg: measures[2],
          cut_criterion: cutCriterion.trim() || null,
          recorded_by: recordedBy.trim(),
          source_reference: sourceReference.trim(),
          notes: notes.trim() || null,
        });
      } else {
        const amount = optionalNumber(quantity);
        if (amount === null || Number.isNaN(amount) || amount < 0) return setMessage("Informe a quantidade descartada.");
        if (reason === "OTHER" && !notes.trim()) return setMessage("Para o motivo “Outro”, descreva nas observações.");
        await api.createDiscard(tenantId, propertyId, {
          field_id: fieldId,
          discard_date: date,
          reason,
          quantity: amount,
          unit,
          recorded_by: recordedBy.trim(),
          source_reference: sourceReference.trim(),
          notes: notes.trim() || null,
        });
      }
      setMessage("Registro salvo.");
      setBoxes("");
      setBunches("");
      setWeight("");
      setQuantity("");
      setNotes("");
      await load();
    } catch (error) {
      setMessage(
        error instanceof HarvestApiError && error.status === 403
          ? "Seu perfil não pode registrar colheita."
          : "Não foi possível salvar o registro. Confira os dados e tente novamente.",
      );
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="harvest-panel" aria-labelledby="harvest-title">
      <h2 id="harvest-title">Colheita por talhão</h2>
      {loadState === "loading" && <p>Carregando colheita…</p>}
      {loadState === "forbidden" && <p>Seu perfil não tem acesso aos registros de colheita.</p>}
      {loadState === "error" && <p>Não foi possível carregar a colheita agora.</p>}
      {loadState === "ready" && summary && (
        <>
          {summary.fields.length === 0 ? (
            <p>Cadastre talhões para registrar a colheita.</p>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Talhão</th>
                  <th>Caixas</th>
                  <th>Cachos</th>
                  <th>Peso</th>
                  <th>Descarte</th>
                </tr>
              </thead>
              <tbody>
                {summary.fields.map((item) => (
                  <tr key={item.field_id}>
                    <td>{item.field_name}</td>
                    {item.no_harvest_records ? (
                      <td colSpan={4}>sem registro de colheita</td>
                    ) : (
                      <>
                        <td>{measureLabel(item.boxes_packed, "caixas")}</td>
                        <td>{measureLabel(item.bunches_harvested, "cachos")}</td>
                        <td>{measureLabel(item.weight_kg, "kg")}</td>
                        <td>{discardLabel(item)}</td>
                      </>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          <ul className="limitations">
            <li>Totais somam apenas o que foi registrado; medida em branco é desconhecida, não zero.</li>
            <li>Unidades de descarte não são somadas entre si e não há percentual de descarte.</li>
          </ul>
        </>
      )}

      {fields.length > 0 && (
        <form onSubmit={submit} aria-label="Registrar colheita ou descarte">
          <fieldset>
            <legend>Novo registro</legend>
            <label>
              Tipo
              <select value={kind} onChange={(event) => setKind(event.target.value as "record" | "discard")}>
                <option value="record">Colheita</option>
                <option value="discard">Descarte</option>
              </select>
            </label>
            <label>
              Talhão
              <select value={fieldId} onChange={(event) => setFieldId(event.target.value)}>
                <option value="">Selecione</option>
                {fields.map((field) => (
                  <option key={field.id} value={field.id}>{field.name}</option>
                ))}
              </select>
            </label>
            <label>
              Data
              <input type="date" value={date} max={todayIso()} onChange={(event) => setDate(event.target.value)} />
            </label>
            {kind === "record" ? (
              <>
                <label>Caixas embaladas<input inputMode="numeric" value={boxes} onChange={(event) => setBoxes(event.target.value)} /></label>
                <label>Cachos colhidos<input inputMode="numeric" value={bunches} onChange={(event) => setBunches(event.target.value)} /></label>
                <label>Peso (kg)<input inputMode="decimal" value={weight} onChange={(event) => setWeight(event.target.value)} /></label>
                <label>Critério de corte<input value={cutCriterion} onChange={(event) => setCutCriterion(event.target.value)} /></label>
              </>
            ) : (
              <>
                <label>
                  Motivo
                  <select value={reason} onChange={(event) => setReason(event.target.value as DiscardReason)}>
                    {(Object.keys(DISCARD_REASON_LABELS) as DiscardReason[]).map((key) => (
                      <option key={key} value={key}>{DISCARD_REASON_LABELS[key]}</option>
                    ))}
                  </select>
                </label>
                <label>Quantidade<input inputMode="decimal" value={quantity} onChange={(event) => setQuantity(event.target.value)} /></label>
                <label>
                  Unidade
                  <select value={unit} onChange={(event) => setUnit(event.target.value as HarvestUnit)}>
                    {(Object.keys(UNIT_LABELS) as HarvestUnit[]).map((key) => (
                      <option key={key} value={key}>{UNIT_LABELS[key]}</option>
                    ))}
                  </select>
                </label>
              </>
            )}
            <label>Registrado por<input value={recordedBy} onChange={(event) => setRecordedBy(event.target.value)} /></label>
            <label>Origem do dado (caderno, planilha…)<input value={sourceReference} onChange={(event) => setSourceReference(event.target.value)} /></label>
            <label>Observações<input value={notes} onChange={(event) => setNotes(event.target.value)} /></label>
            <button type="submit" disabled={saving}>{saving ? "Salvando…" : "Salvar registro"}</button>
            {message && <p role="status">{message}</p>}
          </fieldset>
        </form>
      )}
    </section>
  );
}
