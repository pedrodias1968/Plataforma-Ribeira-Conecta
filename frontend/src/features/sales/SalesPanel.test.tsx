import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { SalesApi, SalesApiError, type SaleRow, type SalesSummary } from "../../api/sales";
import { SalesPanel } from "./SalesPanel";
import { moneyLabel, quantityLabel, statusLabel } from "./labels";

const overdueSale: SaleRow = {
  sale_id: "s1",
  sale_date: "2026-10-01",
  buyer_name: "Silva",
  quantity: 100,
  quantity_unit: "BOXES",
  unit_price_brl: null,
  price_unit: null,
  total_amount_brl: 3000,
  expected_payment_date: "2026-10-15",
  received_brl: 1000,
  balance_brl: 2000,
  status: "PARTIAL",
  overdue: true,
};

const unknownSale: SaleRow = {
  sale_id: "s2",
  sale_date: "2026-10-02",
  buyer_name: "Costa",
  quantity: null,
  quantity_unit: null,
  unit_price_brl: null,
  price_unit: null,
  total_amount_brl: null,
  expected_payment_date: null,
  received_brl: 0,
  balance_brl: null,
  status: "AMOUNT_UNKNOWN",
  overdue: false,
};

const summary: SalesSummary = {
  property_id: "p1",
  as_of: "2026-10-20",
  sale_count: 2,
  sales: [overdueSale, unknownSale],
  total_known_brl: 3000,
  sales_without_total: 1,
  received_on_known_total_brl: 1000,
  received_on_unknown_total_brl: 0,
  outstanding_brl: 2000,
  overdue_brl: 2000,
  limitations: [],
};

function fakeApi(overrides: Partial<Record<keyof SalesApi, unknown>> = {}) {
  return {
    summary: vi.fn().mockResolvedValue(summary),
    createSale: vi.fn().mockResolvedValue({}),
    createPayment: vi.fn().mockResolvedValue({}),
    ...overrides,
  } as unknown as SalesApi;
}

function renderPanel(api: SalesApi) {
  return render(<SalesPanel tenantId="t1" propertyId="p1" apiBaseUrl="" token="x" api={api} />);
}

function change(label: string | RegExp, value: string) {
  fireEvent.change(screen.getByLabelText(label), { target: { value } });
}

afterEach(cleanup);

describe("SalesPanel", () => {
  it("shows status, overdue and unknown amounts without turning them into zero", async () => {
    renderPanel(fakeApi());
    expect(await screen.findByText("pago em parte — atrasado")).toBeInTheDocument();
    expect(screen.getByText("valor não informado")).toBeInTheDocument();
    expect(screen.getByText(/Total a receber \(vendas com valor informado\): R\$\s*2\.000,00/)).toBeInTheDocument();
    expect(screen.getByText(/1 venda\(s\) sem valor total/)).toBeInTheDocument();
    expect(screen.getAllByText("sem registro").length).toBeGreaterThan(0);
  });

  it("label helpers keep unknown as unknown", () => {
    expect(moneyLabel(null)).toBe("sem registro");
    expect(quantityLabel(unknownSale)).toBe("sem registro");
    expect(statusLabel(unknownSale)).toBe("valor não informado");
  });

  it("sends a sale with only a total and no quantity", async () => {
    const api = fakeApi();
    renderPanel(api);
    await screen.findByText("pago em parte — atrasado");
    change("Comprador", "Atravessador João");
    change("Valor total (R$)", "1.234,50".replace(".", ""));
    change("Registrado por", "Gerente");
    change(/Origem do dado/, "caderno");
    fireEvent.click(screen.getByRole("button", { name: "Salvar venda" }));
    await waitFor(() => expect(api.createSale).toHaveBeenCalled());
    expect(vi.mocked(api.createSale).mock.calls[0][2]).toMatchObject({
      buyer_name: "Atravessador João",
      quantity: null,
      quantity_unit: null,
      total_amount_brl: 1234.5,
    });
  });

  it("requires quantity or total instead of assuming a value", async () => {
    const api = fakeApi();
    renderPanel(api);
    await screen.findByText("pago em parte — atrasado");
    change("Comprador", "Silva");
    change("Registrado por", "Gerente");
    change(/Origem do dado/, "caderno");
    fireEvent.click(screen.getByRole("button", { name: "Salvar venda" }));
    expect(await screen.findByText(/Informe a quantidade ou o valor total/)).toBeInTheDocument();
    expect(api.createSale).not.toHaveBeenCalled();
  });

  it("registers a payment against the chosen sale", async () => {
    const api = fakeApi();
    renderPanel(api);
    await screen.findByText("pago em parte — atrasado");
    change("Venda", "s1");
    change("Valor recebido (R$)", "500");
    change("Registrado por (recebimento)", "Gerente");
    change(/Origem \(extrato/, "extrato");
    fireEvent.click(screen.getByRole("button", { name: "Salvar recebimento" }));
    await waitFor(() => expect(api.createPayment).toHaveBeenCalled());
    expect(vi.mocked(api.createPayment).mock.calls[0][1]).toBe("s1");
    expect(vi.mocked(api.createPayment).mock.calls[0][2]).toMatchObject({ amount_brl: 500, method: null });
  });

  it("explains missing permission", async () => {
    renderPanel(fakeApi({ summary: vi.fn().mockRejectedValue(new SalesApiError(403, "forbidden")) }));
    expect(await screen.findByText(/não tem acesso às vendas/)).toBeInTheDocument();
  });
});
