import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react";

import { CostApi, CostApiError, type CostCategory, type CostSummary } from "../../api/costs";
import type { FieldContext } from "../../types/farm360";
import { allocatedCostLabel, CATEGORY_LABELS, costPerKgLabel, moneyLabel, weightLabel } from "./labels";

function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

export function CostPanel({ fields, tenantId, propertyId, apiBaseUrl, token, api: injectedApi }: {
  fields: FieldContext[];
  tenantId: string;
  propertyId: string;
  apiBaseUrl: string;
  token: string;
  api?: CostApi;
}) {
  const api = useMemo(() => injectedApi ?? new CostApi(apiBaseUrl, token), [injectedApi, apiBaseUrl, token]);
  const [summary, setSummary] = useState<CostSummary | null>(null);
  const [loadState, setLoadState] = useState<"loading" | "ready" | "forbidden" | "error">("loading");
  const [fieldId, setFieldId] = useState("");
  const [date, setDate] = useState(todayIso());
  const [category, setCategory] = useState<CostCategory>("LABOR");
  const [description, setDescription] = useState("");
  const [amount, setAmount] = useState("");
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
      setLoadState(error instanceof CostApiError && error.status === 403 ? "forbidden" : "error");
    }
  }, [api, tenantId, propertyId]);

  useEffect(() => {
    void load();
  }, [load]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setMessage(null);
    if (!description.trim()) return setMessage("Descreva o custo.");
    if (!recordedBy.trim() || !sourceReference.trim()) return setMessage("Informe quem registrou e a origem (ex.: caderno, nota).");
    if (category === "OTHER" && !notes.trim()) return setMessage("Para a categoria “Outro”, descreva nas observações.");
    const value = Number(amount.trim().replace(",", "."));
    if (amount.trim() === "" || !Number.isFinite(value) || value < 0) {
      return setMessage("Informe o valor em reais (zero ou mais).");
    }
    setSaving(true);
    try {
      await api.createEntry(tenantId, propertyId, {
        field_id: fieldId || null,
        entry_date: date,
        category,
        description: description.trim(),
        amount_brl: value,
        recorded_by: recordedBy.trim(),
        source_reference: sourceReference.trim(),
        notes: notes.trim() || null,
      });
      setMessage("Registro salvo.");
      setDescription("");
      setAmount("");
      setNotes("");
      await load();
    } catch (error) {
      setMessage(
        error instanceof CostApiError && error.status === 403
          ? "Seu perfil não pode registrar custos."
          : "Não foi possível salvar o registro. Confira os dados e tente novamente.",
      );
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="cost-panel" aria-labelledby="cost-title">
      <h2 id="cost-title">Custos por talhão e por kg</h2>
      {loadState === "loading" && <p>Carregando custos…</p>}
      {loadState === "forbidden" && <p>Seu perfil não tem acesso aos custos.</p>}
      {loadState === "error" && <p>Não foi possível carregar os custos agora.</p>}
      {loadState === "ready" && summary && (
        <>
          {summary.fields.length === 0 ? (
            <p>Cadastre talhões para acompanhar custos.</p>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Talhão</th>
                  <th>Custo do talhão</th>
                  <th>Peso colhido</th>
                  <th>Custo por kg</th>
                </tr>
              </thead>
              <tbody>
                {summary.fields.map((item) => (
                  <tr key={item.field_id}>
                    <td>{item.field_name}</td>
                    <td>{allocatedCostLabel(item)}</td>
                    <td>{weightLabel(item)}</td>
                    <td>{costPerKgLabel(item)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          <p>
            Custos do sítio inteiro (não rateados entre talhões): {moneyLabel(summary.unallocated_cost.total)}
          </p>
          <ul className="limitations">
            <li>O custo de adubo vem do registro de adubação; não lance adubo aqui.</li>
            <li>Custo sem registro é desconhecido, não zero. O custo por kg só aparece com custo e peso completos no período.</li>
          </ul>
        </>
      )}

      <form onSubmit={submit} aria-label="Registrar custo">
        <fieldset>
          <legend>Novo custo</legend>
          <label>
            Talhão
            <select value={fieldId} onChange={(event) => setFieldId(event.target.value)}>
              <option value="">Sítio inteiro (sem rateio)</option>
              {fields.map((field) => (
                <option key={field.id} value={field.id}>{field.name}</option>
              ))}
            </select>
          </label>
          <label>
            Data
            <input type="date" value={date} max={todayIso()} onChange={(event) => setDate(event.target.value)} />
          </label>
          <label>
            Categoria
            <select value={category} onChange={(event) => setCategory(event.target.value as CostCategory)}>
              {(Object.keys(CATEGORY_LABELS) as CostCategory[]).map((key) => (
                <option key={key} value={key}>{CATEGORY_LABELS[key]}</option>
              ))}
            </select>
          </label>
          <label>Descrição<input value={description} onChange={(event) => setDescription(event.target.value)} /></label>
          <label>Valor (R$)<input inputMode="decimal" value={amount} onChange={(event) => setAmount(event.target.value)} /></label>
          <label>Registrado por<input value={recordedBy} onChange={(event) => setRecordedBy(event.target.value)} /></label>
          <label>Origem do dado (caderno, nota…)<input value={sourceReference} onChange={(event) => setSourceReference(event.target.value)} /></label>
          <label>Observações<input value={notes} onChange={(event) => setNotes(event.target.value)} /></label>
          <button type="submit" disabled={saving}>{saving ? "Salvando…" : "Salvar custo"}</button>
          {message && <p role="status">{message}</p>}
        </fieldset>
      </form>
    </section>
  );
}
