import { useCallback, useEffect, useMemo, useState, type FormEvent } from "react";

import { SalesApi, SalesApiError, type SaleUnit, type SalesSummary } from "../../api/sales";
import { formatDate, moneyLabel, quantityLabel, statusLabel, UNIT_LABELS } from "./labels";

function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

function parseOptional(text: string): number | null | "invalid" {
  if (text.trim() === "") return null;
  const value = Number(text.trim().replace(",", "."));
  return Number.isFinite(value) && value >= 0 ? value : "invalid";
}

export function SalesPanel({ tenantId, propertyId, apiBaseUrl, token, api: injectedApi }: {
  tenantId: string;
  propertyId: string;
  apiBaseUrl: string;
  token: string;
  api?: SalesApi;
}) {
  const api = useMemo(() => injectedApi ?? new SalesApi(apiBaseUrl, token), [injectedApi, apiBaseUrl, token]);
  const [summary, setSummary] = useState<SalesSummary | null>(null);
  const [loadState, setLoadState] = useState<"loading" | "ready" | "forbidden" | "error">("loading");
  const [saleDate, setSaleDate] = useState(todayIso());
  const [buyer, setBuyer] = useState("");
  const [quantity, setQuantity] = useState("");
  const [quantityUnit, setQuantityUnit] = useState<SaleUnit>("BOXES");
  const [price, setPrice] = useState("");
  const [total, setTotal] = useState("");
  const [expected, setExpected] = useState("");
  const [recordedBy, setRecordedBy] = useState("");
  const [sourceReference, setSourceReference] = useState("");
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [paySaleId, setPaySaleId] = useState("");
  const [payDate, setPayDate] = useState(todayIso());
  const [payAmount, setPayAmount] = useState("");
  const [payMethod, setPayMethod] = useState("");
  const [payBy, setPayBy] = useState("");
  const [paySource, setPaySource] = useState("");
  const [payMessage, setPayMessage] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      setSummary(await api.summary(tenantId, propertyId));
      setLoadState("ready");
    } catch (error) {
      setSummary(null);
      setLoadState(error instanceof SalesApiError && error.status === 403 ? "forbidden" : "error");
    }
  }, [api, tenantId, propertyId]);

  useEffect(() => {
    void load();
  }, [load]);

  async function submitSale(event: FormEvent) {
    event.preventDefault();
    setMessage(null);
    if (!buyer.trim()) return setMessage("Informe o comprador.");
    if (!recordedBy.trim() || !sourceReference.trim()) return setMessage("Informe quem registrou e a origem (ex.: caderno, nota).");
    const qty = parseOptional(quantity);
    const unitPrice = parseOptional(price);
    const totalValue = parseOptional(total);
    if (qty === "invalid" || unitPrice === "invalid" || totalValue === "invalid") {
      return setMessage("Use números zero ou maiores nos campos de quantidade, preço e total.");
    }
    if (qty === null && totalValue === null) return setMessage("Informe a quantidade ou o valor total da venda.");
    setSaving(true);
    try {
      await api.createSale(tenantId, propertyId, {
        sale_date: saleDate,
        buyer_name: buyer.trim(),
        quantity: qty,
        quantity_unit: qty === null ? null : quantityUnit,
        unit_price_brl: unitPrice,
        price_unit: unitPrice === null ? null : quantityUnit,
        total_amount_brl: totalValue,
        expected_payment_date: expected || null,
        recorded_by: recordedBy.trim(),
        source_reference: sourceReference.trim(),
        notes: null,
      });
      setMessage("Venda salva.");
      setBuyer("");
      setQuantity("");
      setPrice("");
      setTotal("");
      setExpected("");
      await load();
    } catch (error) {
      setMessage(
        error instanceof SalesApiError && error.status === 403
          ? "Seu perfil não pode registrar vendas."
          : "Não foi possível salvar a venda. Confira os dados e tente novamente.",
      );
    } finally {
      setSaving(false);
    }
  }

  async function submitPayment(event: FormEvent) {
    event.preventDefault();
    setPayMessage(null);
    if (!paySaleId) return setPayMessage("Escolha a venda.");
    if (!payBy.trim() || !paySource.trim()) return setPayMessage("Informe quem registrou e a origem (ex.: extrato, recibo).");
    const value = Number(payAmount.trim().replace(",", "."));
    if (payAmount.trim() === "" || !Number.isFinite(value) || value <= 0) {
      return setPayMessage("Informe o valor recebido, maior que zero.");
    }
    try {
      await api.createPayment(tenantId, paySaleId, {
        payment_date: payDate,
        amount_brl: value,
        method: payMethod.trim() || null,
        recorded_by: payBy.trim(),
        source_reference: paySource.trim(),
        notes: null,
      });
      setPayMessage("Recebimento salvo.");
      setPayAmount("");
      await load();
    } catch (error) {
      setPayMessage(
        error instanceof SalesApiError && error.status === 403
          ? "Seu perfil não pode registrar recebimentos."
          : "Não foi possível salvar o recebimento. Confira os dados e tente novamente.",
      );
    }
  }

  return (
    <section className="sales-panel" aria-labelledby="sales-title">
      <h2 id="sales-title">Vendas e recebimentos</h2>
      {loadState === "loading" && <p>Carregando vendas…</p>}
      {loadState === "forbidden" && <p>Seu perfil não tem acesso às vendas.</p>}
      {loadState === "error" && <p>Não foi possível carregar as vendas agora.</p>}
      {loadState === "ready" && summary && (
        <>
          {summary.sales.length === 0 ? (
            <p>Nenhuma venda registrada.</p>
          ) : (
            <table>
              <thead>
                <tr>
                  <th>Data</th>
                  <th>Comprador</th>
                  <th>Quantidade</th>
                  <th>Total</th>
                  <th>Recebido</th>
                  <th>A receber</th>
                  <th>Previsão</th>
                  <th>Situação</th>
                </tr>
              </thead>
              <tbody>
                {summary.sales.map((row) => (
                  <tr key={row.sale_id}>
                    <td>{formatDate(row.sale_date)}</td>
                    <td>{row.buyer_name}</td>
                    <td>{quantityLabel(row)}</td>
                    <td>{moneyLabel(row.total_amount_brl)}</td>
                    <td>{moneyLabel(row.received_brl)}</td>
                    <td>{moneyLabel(row.balance_brl)}</td>
                    <td>{formatDate(row.expected_payment_date)}</td>
                    <td>{statusLabel(row)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
          <p>Total a receber (vendas com valor informado): {moneyLabel(summary.outstanding_brl)}</p>
          <p>Em atraso: {moneyLabel(summary.overdue_brl)}</p>
          {summary.sales_without_total > 0 && (
            <p>{summary.sales_without_total} venda(s) sem valor total — o saldo delas é desconhecido.</p>
          )}
          <ul className="limitations">
            <li>O total nunca é calculado por quantidade × preço; vale o que foi registrado.</li>
            <li>Valor sem registro é desconhecido, não zero.</li>
          </ul>
        </>
      )}

      <form onSubmit={submitSale} aria-label="Registrar venda">
        <fieldset>
          <legend>Nova venda</legend>
          <label>Data da venda<input type="date" value={saleDate} max={todayIso()} onChange={(e) => setSaleDate(e.target.value)} /></label>
          <label>Comprador<input value={buyer} onChange={(e) => setBuyer(e.target.value)} /></label>
          <label>Quantidade<input inputMode="decimal" value={quantity} onChange={(e) => setQuantity(e.target.value)} /></label>
          <label>
            Unidade
            <select value={quantityUnit} onChange={(e) => setQuantityUnit(e.target.value as SaleUnit)}>
              {(Object.keys(UNIT_LABELS) as SaleUnit[]).map((key) => (
                <option key={key} value={key}>{UNIT_LABELS[key]}</option>
              ))}
            </select>
          </label>
          <label>Preço por unidade (R$)<input inputMode="decimal" value={price} onChange={(e) => setPrice(e.target.value)} /></label>
          <label>Valor total (R$)<input inputMode="decimal" value={total} onChange={(e) => setTotal(e.target.value)} /></label>
          <label>Previsão de pagamento<input type="date" value={expected} onChange={(e) => setExpected(e.target.value)} /></label>
          <label>Registrado por<input value={recordedBy} onChange={(e) => setRecordedBy(e.target.value)} /></label>
          <label>Origem do dado (caderno, nota…)<input value={sourceReference} onChange={(e) => setSourceReference(e.target.value)} /></label>
          <button type="submit" disabled={saving}>{saving ? "Salvando…" : "Salvar venda"}</button>
          {message && <p role="status">{message}</p>}
        </fieldset>
      </form>

      {loadState === "ready" && summary && summary.sales.length > 0 && (
        <form onSubmit={submitPayment} aria-label="Registrar recebimento">
          <fieldset>
            <legend>Novo recebimento</legend>
            <label>
              Venda
              <select value={paySaleId} onChange={(e) => setPaySaleId(e.target.value)}>
                <option value="">Escolha…</option>
                {summary.sales.map((row) => (
                  <option key={row.sale_id} value={row.sale_id}>
                    {formatDate(row.sale_date)} — {row.buyer_name}
                  </option>
                ))}
              </select>
            </label>
            <label>Data do recebimento<input type="date" value={payDate} max={todayIso()} onChange={(e) => setPayDate(e.target.value)} /></label>
            <label>Valor recebido (R$)<input inputMode="decimal" value={payAmount} onChange={(e) => setPayAmount(e.target.value)} /></label>
            <label>Forma (Pix, dinheiro…)<input value={payMethod} onChange={(e) => setPayMethod(e.target.value)} /></label>
            <label>Registrado por (recebimento)<input value={payBy} onChange={(e) => setPayBy(e.target.value)} /></label>
            <label>Origem (extrato, recibo…)<input value={paySource} onChange={(e) => setPaySource(e.target.value)} /></label>
            <button type="submit">Salvar recebimento</button>
            {payMessage && <p role="status">{payMessage}</p>}
          </fieldset>
        </form>
      )}
    </section>
  );
}
