import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react";

import {
  StockApi,
  StockApiError,
  type MovementType,
  type StockSummary,
  type StockUnit,
} from "../../api/stock";
import { balanceLabel, formatDate, quantityLabel, TYPE_LABELS, UNIT_LABELS } from "./labels";

function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

export function StockPanel({ tenantId, propertyId, apiBaseUrl, token, api: injectedApi }: {
  tenantId: string;
  propertyId: string;
  apiBaseUrl: string;
  token: string;
  api?: StockApi;
}) {
  const api = useMemo(() => injectedApi ?? new StockApi(apiBaseUrl, token), [injectedApi, apiBaseUrl, token]);
  const [summary, setSummary] = useState<StockSummary | null>(null);
  const [loadState, setLoadState] = useState<"loading" | "ready" | "forbidden" | "error">("loading");
  const [movementType, setMovementType] = useState<MovementType>("IN");
  const [date, setDate] = useState(todayIso());
  const [itemName, setItemName] = useState("");
  const [unit, setUnit] = useState<StockUnit>("KG");
  const [quantity, setQuantity] = useState("");
  const [counterparty, setCounterparty] = useState("");
  const [recordedBy, setRecordedBy] = useState("");
  const [sourceReference, setSourceReference] = useState("");
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setSummary(await api.summary(tenantId, propertyId));
      setLoadState("ready");
    } catch (error) {
      setSummary(null);
      setLoadState(error instanceof StockApiError && error.status === 403 ? "forbidden" : "error");
    }
  }, [api, tenantId, propertyId]);

  useEffect(() => {
    void load();
  }, [load]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setMessage(null);
    if (!itemName.trim()) return setMessage("Informe o insumo.");
    if (!recordedBy.trim() || !sourceReference.trim()) return setMessage("Informe quem registrou e a origem (ex.: caderno, nota).");
    const value = Number(quantity.trim().replace(",", "."));
    if (quantity.trim() === "" || !Number.isFinite(value) || value <= 0) {
      return setMessage("Informe a quantidade, maior que zero.");
    }
    setSaving(true);
    try {
      await api.createMovement(tenantId, propertyId, {
        movement_date: date,
        movement_type: movementType,
        item_name: itemName.trim(),
        unit,
        quantity: value,
        counterparty: counterparty.trim() || null,
        recorded_by: recordedBy.trim(),
        source_reference: sourceReference.trim(),
        notes: null,
      });
      setMessage("Movimentação salva.");
      setQuantity("");
      setCounterparty("");
      await load();
    } catch (error) {
      setMessage(
        error instanceof StockApiError && error.status === 403
          ? "Seu perfil não pode registrar estoque."
          : "Não foi possível salvar a movimentação. Confira os dados e tente novamente.",
      );
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="stock-panel" aria-labelledby="stock-title">
      <h2 id="stock-title">Estoque de insumos</h2>
      {loadState === "loading" && <p>Carregando estoque…</p>}
      {loadState === "forbidden" && <p>Seu perfil não tem acesso ao estoque.</p>}
      {loadState === "error" && <p>Não foi possível carregar o estoque agora.</p>}
      {loadState === "ready" && summary && (
        <>
          {summary.items.length === 0 ? (
            <p>Nenhuma movimentação registrada.</p>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Insumo</th>
                  <th>Entradas</th>
                  <th>Saídas</th>
                  <th>Saldo</th>
                  <th>Última movimentação</th>
                </tr>
              </thead>
              <tbody>
                {summary.items.map((item) => (
                  <tr key={`${item.item_name.toLowerCase()}-${item.unit}`}>
                    <td>{item.item_name}</td>
                    <td>{quantityLabel(item.entries, item.unit)}</td>
                    <td>{quantityLabel(item.exits, item.unit)}</td>
                    <td>{balanceLabel(item)}</td>
                    <td>{formatDate(item.last_movement_date)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          <ul className="limitations">
            <li>O saldo é entradas menos saídas registradas. Registre o estoque inicial como uma entrada.</li>
            <li>A adubação registrada não baixa o estoque sozinha; lance a saída aqui.</li>
          </ul>
        </>
      )}

      <form onSubmit={submit} aria-label="Registrar movimentação de estoque">
        <fieldset>
          <legend>Nova movimentação</legend>
          <label>
            Tipo
            <select value={movementType} onChange={(e) => setMovementType(e.target.value as MovementType)}>
              {(Object.keys(TYPE_LABELS) as MovementType[]).map((key) => (
                <option key={key} value={key}>{TYPE_LABELS[key]}</option>
              ))}
            </select>
          </label>
          <label>Data<input type="date" value={date} max={todayIso()} onChange={(e) => setDate(e.target.value)} /></label>
          <label>Insumo<input value={itemName} onChange={(e) => setItemName(e.target.value)} /></label>
          <label>Quantidade<input inputMode="decimal" value={quantity} onChange={(e) => setQuantity(e.target.value)} /></label>
          <label>
            Unidade
            <select value={unit} onChange={(e) => setUnit(e.target.value as StockUnit)}>
              {(Object.keys(UNIT_LABELS) as StockUnit[]).map((key) => (
                <option key={key} value={key}>{UNIT_LABELS[key]}</option>
              ))}
            </select>
          </label>
          <label>Fornecedor ou destino<input value={counterparty} onChange={(e) => setCounterparty(e.target.value)} /></label>
          <label>Registrado por<input value={recordedBy} onChange={(e) => setRecordedBy(e.target.value)} /></label>
          <label>Origem do dado (caderno, nota…)<input value={sourceReference} onChange={(e) => setSourceReference(e.target.value)} /></label>
          <button type="submit" disabled={saving}>{saving ? "Salvando…" : "Salvar movimentação"}</button>
          {message && <p role="status">{message}</p>}
        </fieldset>
      </form>
    </section>
  );
}
