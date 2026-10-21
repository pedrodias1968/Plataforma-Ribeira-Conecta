import type { AccountantReport } from "../../api/accountant";
import { STATUS_LABELS, UNIT_LABELS } from "../sales/labels";

const SEP = ";";

/** Unknown stays empty in the file: never 0, never "N/A". */
function num(value: number | null | undefined): string {
  return value === null || value === undefined ? "" : String(value).replace(".", ",");
}

function cell(value: string | null | undefined): string {
  const text = value ?? "";
  return /[;"\n\r]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
}

function line(values: Array<string | null | undefined>): string {
  return values.map(cell).join(SEP);
}

export function buildAccountantCsv(report: AccountantReport): string {
  const rows: string[] = [];
  rows.push(line(["Relatório para o contador", `${report.date_from} a ${report.date_to}`, `posição em ${report.as_of}`]));
  rows.push("");
  rows.push(line(["VENDAS"]));
  rows.push(
    line([
      "Data", "Comprador", "Quantidade", "Unidade", "Preço unitário (R$)", "Total (R$)",
      "Recebido (R$)", "A receber (R$)", "Previsão de pagamento", "Situação", "Atrasado",
    ]),
  );
  for (const sale of report.sales.sales) {
    rows.push(
      line([
        sale.sale_date,
        sale.buyer_name,
        num(sale.quantity),
        sale.quantity_unit ? UNIT_LABELS[sale.quantity_unit] : "",
        num(sale.unit_price_brl),
        num(sale.total_amount_brl),
        num(sale.received_brl),
        num(sale.balance_brl),
        sale.expected_payment_date ?? "",
        STATUS_LABELS[sale.status],
        sale.overdue ? "sim" : "não",
      ]),
    );
  }
  rows.push("");
  rows.push(line(["CUSTOS"]));
  rows.push(line(["Talhão", "Custo manual (R$)", "Adubação (R$)", "Total do talhão (R$)", "Parcial"]));
  for (const item of report.costs.fields) {
    rows.push(
      line([
        item.field_name,
        num(item.manual_cost.total),
        num(item.fertilization_cost.total),
        num(item.allocated_cost_total),
        item.cost_is_partial ? "sim" : "não",
      ]),
    );
  }
  rows.push(line(["Sítio inteiro (sem rateio)", num(report.costs.unallocated_cost.total), "", "", ""]));
  rows.push("");
  for (const text of report.limitations) rows.push(line([text]));
  return rows.join("\r\n");
}

export function downloadCsv(filename: string, content: string): void {
  const blob = new Blob(["﻿", content], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}
