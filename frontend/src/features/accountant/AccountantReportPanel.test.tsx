import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AccountantApi, AccountantApiError, type AccountantReport } from "../../api/accountant";
import { AccountantReportPanel } from "./AccountantReportPanel";
import { buildAccountantCsv } from "./csv";

const report: AccountantReport = {
  property_id: "p1",
  date_from: "2026-10-01",
  date_to: "2026-10-31",
  as_of: "2026-10-20",
  classification: "CALCULATED",
  limitations: ["Não há resultado/margem."],
  sales: {
    property_id: "p1",
    as_of: "2026-10-20",
    sale_count: 2,
    total_known_brl: 3000,
    sales_without_total: 1,
    received_on_known_total_brl: 1000,
    received_on_unknown_total_brl: 0,
    outstanding_brl: 2000,
    overdue_brl: 2000,
    limitations: [],
    sales: [
      {
        sale_id: "s1", sale_date: "2026-10-01", buyer_name: "Silva; & Filhos", quantity: 100, quantity_unit: "BOXES",
        unit_price_brl: null, price_unit: null, total_amount_brl: 3000, expected_payment_date: "2026-10-15",
        received_brl: 1000, balance_brl: 2000, status: "PARTIAL", overdue: true,
      },
      {
        sale_id: "s2", sale_date: "2026-10-02", buyer_name: "Costa", quantity: null, quantity_unit: null,
        unit_price_brl: null, price_unit: null, total_amount_brl: null, expected_payment_date: null,
        received_brl: 0, balance_brl: null, status: "AMOUNT_UNKNOWN", overdue: false,
      },
    ],
  },
  costs: {
    property_id: "p1",
    date_from: "2026-10-01",
    date_to: "2026-10-31",
    classification: "CALCULATED",
    limitations: [],
    unallocated_cost: { entry_count: 1, total: 200.5, by_category: { FUEL: 200.5 } },
    fields: [
      {
        field_id: "f1", field_name: "Talhão A",
        manual_cost: { entry_count: 0, total: null, by_category: {} },
        fertilization_cost: { record_count: 0, total: null, records_with_value: 0, records_without_value: 0 },
        allocated_cost_total: null, cost_is_partial: false,
        harvest: { record_count: 0, weight_kg_total: null, records_with_weight: 0, records_without_weight: 0 },
        cost_per_kg: null, cost_per_kg_unavailable_reason: "NO_COST_DATA",
      },
    ],
  },
};

afterEach(cleanup);

describe("buildAccountantCsv", () => {
  it("leaves unknown values empty, never zero, and escapes separators", () => {
    const csv = buildAccountantCsv(report);
    const lines = csv.split("\r\n");
    expect(lines).toContain('2026-10-01;"Silva; & Filhos";100;caixas;;3000;1000;2000;2026-10-15;pago em parte;sim');
    expect(lines).toContain("2026-10-02;Costa;;;;;0;;;valor não informado;não");
    expect(lines).toContain("Talhão A;;;;não");
    expect(lines).toContain("Sítio inteiro (sem rateio);200,5;;;");
  });
});

describe("AccountantReportPanel", () => {
  it("generates the report for the period and offers the CSV", async () => {
    const api = { report: vi.fn().mockResolvedValue(report) } as unknown as AccountantApi;
    const onDownload = vi.fn();
    render(<AccountantReportPanel tenantId="t1" propertyId="p1" apiBaseUrl="" token="x" api={api} onDownload={onDownload} />);
    fireEvent.change(screen.getByLabelText("De"), { target: { value: "2026-10-01" } });
    fireEvent.change(screen.getByLabelText("Até"), { target: { value: "2026-10-20" } });
    fireEvent.click(screen.getByRole("button", { name: "Gerar relatório" }));
    expect(await screen.findByText(/Vendas no período: 2/)).toBeInTheDocument();
    expect(api.report).toHaveBeenCalledWith("t1", "p1", "2026-10-01", "2026-10-20");
    expect(screen.getByText(/1 venda\(s\) sem valor total/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Baixar planilha (CSV)" }));
    expect(onDownload).toHaveBeenCalledWith("relatorio-contador-2026-10-01-a-2026-10-31.csv", expect.stringContaining("VENDAS"));
  });

  it("rejects an inverted period without calling the API", async () => {
    const api = { report: vi.fn() } as unknown as AccountantApi;
    render(<AccountantReportPanel tenantId="t1" propertyId="p1" apiBaseUrl="" token="x" api={api} />);
    fireEvent.change(screen.getByLabelText("De"), { target: { value: "2026-10-20" } });
    fireEvent.change(screen.getByLabelText("Até"), { target: { value: "2026-10-01" } });
    fireEvent.click(screen.getByRole("button", { name: "Gerar relatório" }));
    expect(await screen.findByText(/não pode ser depois da final/)).toBeInTheDocument();
    expect(api.report).not.toHaveBeenCalled();
  });

  it("explains missing permission", async () => {
    const api = { report: vi.fn().mockRejectedValue(new AccountantApiError(403, "forbidden")) } as unknown as AccountantApi;
    render(<AccountantReportPanel tenantId="t1" propertyId="p1" apiBaseUrl="" token="x" api={api} />);
    fireEvent.click(screen.getByRole("button", { name: "Gerar relatório" }));
    await waitFor(() => expect(screen.getByText(/não tem acesso ao relatório/)).toBeInTheDocument());
  });
});
