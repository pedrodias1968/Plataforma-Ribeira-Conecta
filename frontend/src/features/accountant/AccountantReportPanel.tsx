import { useMemo, useState, type FormEvent } from "react";

import { AccountantApi, AccountantApiError, type AccountantReport } from "../../api/accountant";
import { moneyLabel } from "../sales/labels";
import { buildAccountantCsv, downloadCsv } from "./csv";

function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

function monthStartIso(): string {
  return `${todayIso().slice(0, 8)}01`;
}

export function AccountantReportPanel({ tenantId, propertyId, apiBaseUrl, token, api: injectedApi, onDownload = downloadCsv }: {
  tenantId: string;
  propertyId: string;
  apiBaseUrl: string;
  token: string;
  api?: AccountantApi;
  onDownload?: (filename: string, content: string) => void;
}) {
  const api = useMemo(() => injectedApi ?? new AccountantApi(apiBaseUrl, token), [injectedApi, apiBaseUrl, token]);
  const [dateFrom, setDateFrom] = useState(monthStartIso());
  const [dateTo, setDateTo] = useState(todayIso());
  const [report, setReport] = useState<AccountantReport | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function generate(event: FormEvent) {
    event.preventDefault();
    setMessage(null);
    if (!dateFrom || !dateTo) return setMessage("Informe as duas datas do período.");
    if (dateFrom > dateTo) return setMessage("A data inicial não pode ser depois da final.");
    setLoading(true);
    try {
      setReport(await api.report(tenantId, propertyId, dateFrom, dateTo));
    } catch (error) {
      setReport(null);
      setMessage(
        error instanceof AccountantApiError && error.status === 403
          ? "Seu perfil não tem acesso ao relatório para o contador."
          : "Não foi possível gerar o relatório agora.",
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="accountant-panel" aria-labelledby="accountant-title">
      <h2 id="accountant-title">Relatório para o contador</h2>
      <form onSubmit={generate} aria-label="Gerar relatório para o contador">
        <label>De<input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} /></label>
        <label>Até<input type="date" value={dateTo} max={todayIso()} onChange={(e) => setDateTo(e.target.value)} /></label>
        <button type="submit" disabled={loading}>{loading ? "Gerando…" : "Gerar relatório"}</button>
      </form>
      {message && <p role="status">{message}</p>}
      {report && (
        <>
          <p>Período: {report.date_from} a {report.date_to}</p>
          <ul>
            <li>Vendas no período: {report.sales.sale_count}</li>
            <li>Total das vendas com valor informado: {moneyLabel(report.sales.total_known_brl)}</li>
            <li>A receber: {moneyLabel(report.sales.outstanding_brl)}</li>
            <li>Em atraso: {moneyLabel(report.sales.overdue_brl)}</li>
            <li>Custos do sítio inteiro (sem rateio): {moneyLabel(report.costs.unallocated_cost.total)}</li>
          </ul>
          {report.sales.sales_without_total > 0 && (
            <p>{report.sales.sales_without_total} venda(s) sem valor total — saldo desconhecido.</p>
          )}
          <ul className="limitations">
            {report.limitations.map((text) => (
              <li key={text}>{text}</li>
            ))}
          </ul>
          <button
            type="button"
            onClick={() => onDownload(`relatorio-contador-${report.date_from}-a-${report.date_to}.csv`, buildAccountantCsv(report))}
          >
            Baixar planilha (CSV)
          </button>
        </>
      )}
    </section>
  );
}
