import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react";

import {
  FertilizationApi,
  FertilizationApiError,
  type FertilizationSummary,
  type ProductType,
  type QuantityUnit,
} from "../../api/fertilization";
import type { FieldContext } from "../../types/farm360";
import { costLabel, dateLabel, PRODUCT_TYPE_LABELS, quantityLabel, UNIT_LABELS } from "./labels";

function optionalNumber(value: string): number | null {
  const text = value.trim().replace(",", ".");
  if (text === "") return null;
  const parsed = Number(text);
  return Number.isFinite(parsed) ? parsed : Number.NaN;
}

function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

export function FertilizationPanel({ fields, tenantId, propertyId, apiBaseUrl, token, api: injectedApi }: {
  fields: FieldContext[];
  tenantId: string;
  propertyId: string;
  apiBaseUrl: string;
  token: string;
  api?: FertilizationApi;
}) {
  const api = useMemo(() => injectedApi ?? new FertilizationApi(apiBaseUrl, token), [injectedApi, apiBaseUrl, token]);
  const [summary, setSummary] = useState<FertilizationSummary | null>(null);
  const [loadState, setLoadState] = useState<"loading" | "ready" | "forbidden" | "error">("loading");
  const [fieldId, setFieldId] = useState("");
  const [date, setDate] = useState(todayIso());
  const [productName, setProductName] = useState("");
  const [productType, setProductType] = useState<ProductType>("MINERAL_FERTILIZER");
  const [quantity, setQuantity] = useState("");
  const [unit, setUnit] = useState<QuantityUnit>("KG");
  const [area, setArea] = useState("");
  const [method, setMethod] = useState("");
  const [cost, setCost] = useState("");
  const [appliedBy, setAppliedBy] = useState("");
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
      setLoadState(error instanceof FertilizationApiError && error.status === 403 ? "forbidden" : "error");
    }
  }, [api, tenantId, propertyId]);

  useEffect(() => {
    void load();
  }, [load]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setMessage(null);
    if (!fieldId) return setMessage("Escolha o talhão.");
    if (!productName.trim()) return setMessage("Informe o produto.");
    if (!appliedBy.trim() || !recordedBy.trim() || !sourceReference.trim()) {
      return setMessage("Informe quem aplicou, quem registrou e a origem (ex.: caderno).");
    }
    if (productType === "OTHER" && !notes.trim()) return setMessage("Para o tipo “Outro”, descreva nas observações.");
    const amount = optionalNumber(quantity);
    const areaValue = optionalNumber(area);
    const costValue = optionalNumber(cost);
    if ([amount, areaValue, costValue].some((value) => value !== null && (Number.isNaN(value) || value < 0))) {
      return setMessage("Use apenas números iguais ou maiores que zero.");
    }
    if (areaValue === 0) return setMessage("A área aplicada deve ser maior que zero ou ficar em branco.");
    setSaving(true);
    try {
      await api.createRecord(tenantId, propertyId, {
        field_id: fieldId,
        application_date: date,
        product_name: productName.trim(),
        product_type: productType,
        quantity: amount,
        quantity_unit: amount === null ? null : unit,
        area_applied_ha: areaValue,
        application_method: method.trim() || null,
        cost_brl: costValue,
        applied_by: appliedBy.trim(),
        recorded_by: recordedBy.trim(),
        source_reference: sourceReference.trim(),
        notes: notes.trim() || null,
      });
      setMessage("Registro salvo.");
      setProductName("");
      setQuantity("");
      setArea("");
      setCost("");
      setNotes("");
      await load();
    } catch (error) {
      setMessage(
        error instanceof FertilizationApiError && error.status === 403
          ? "Seu perfil não pode registrar adubação."
          : "Não foi possível salvar o registro. Confira os dados e tente novamente.",
      );
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="fertilization-panel" aria-labelledby="fertilization-title">
      <h2 id="fertilization-title">Adubação e insumos por talhão</h2>
      {loadState === "loading" && <p>Carregando adubação…</p>}
      {loadState === "forbidden" && <p>Seu perfil não tem acesso aos registros de adubação.</p>}
      {loadState === "error" && <p>Não foi possível carregar a adubação agora.</p>}
      {loadState === "ready" && summary && (
        <>
          {summary.fields.length === 0 ? (
            <p>Cadastre talhões para registrar a adubação.</p>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Talhão</th>
                  <th>Última aplicação</th>
                  <th>Produtos</th>
                  <th>Quantidade</th>
                  <th>Custo</th>
                </tr>
              </thead>
              <tbody>
                {summary.fields.map((item) => (
                  <tr key={item.field_id}>
                    <td>{item.field_name}</td>
                    {item.no_fertilization_records ? (
                      <td colSpan={4}>sem registro de adubação</td>
                    ) : (
                      <>
                        <td>{dateLabel(item.last_application_date)}</td>
                        <td>{item.products.join(", ")}</td>
                        <td>{quantityLabel(item)}</td>
                        <td>{costLabel(item.cost_brl)}</td>
                      </>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          <ul className="limitations">
            <li>Totais somam apenas o que foi registrado; quantidade ou custo em branco é desconhecido, não zero.</li>
            <li>Unidades diferentes não são somadas e não há cálculo de dose por hectare.</li>
          </ul>
        </>
      )}

      {fields.length > 0 && (
        <form onSubmit={submit} aria-label="Registrar adubação">
          <fieldset>
            <legend>Nova aplicação</legend>
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
            <label>Produto<input value={productName} onChange={(event) => setProductName(event.target.value)} /></label>
            <label>
              Tipo
              <select value={productType} onChange={(event) => setProductType(event.target.value as ProductType)}>
                {(Object.keys(PRODUCT_TYPE_LABELS) as ProductType[]).map((key) => (
                  <option key={key} value={key}>{PRODUCT_TYPE_LABELS[key]}</option>
                ))}
              </select>
            </label>
            <label>Quantidade<input inputMode="decimal" value={quantity} onChange={(event) => setQuantity(event.target.value)} /></label>
            <label>
              Unidade
              <select value={unit} onChange={(event) => setUnit(event.target.value as QuantityUnit)}>
                {(Object.keys(UNIT_LABELS) as QuantityUnit[]).map((key) => (
                  <option key={key} value={key}>{UNIT_LABELS[key]}</option>
                ))}
              </select>
            </label>
            <label>Área aplicada (ha)<input inputMode="decimal" value={area} onChange={(event) => setArea(event.target.value)} /></label>
            <label>Forma de aplicação<input value={method} onChange={(event) => setMethod(event.target.value)} /></label>
            <label>Custo (R$)<input inputMode="decimal" value={cost} onChange={(event) => setCost(event.target.value)} /></label>
            <label>Aplicado por<input value={appliedBy} onChange={(event) => setAppliedBy(event.target.value)} /></label>
            <label>Registrado por<input value={recordedBy} onChange={(event) => setRecordedBy(event.target.value)} /></label>
            <label>Origem do dado (caderno, nota…)<input value={sourceReference} onChange={(event) => setSourceReference(event.target.value)} /></label>
            <label>Observações<input value={notes} onChange={(event) => setNotes(event.target.value)} /></label>
            <button type="submit" disabled={saving}>{saving ? "Salvando…" : "Salvar aplicação"}</button>
            {message && <p role="status">{message}</p>}
          </fieldset>
        </form>
      )}
    </section>
  );
}
