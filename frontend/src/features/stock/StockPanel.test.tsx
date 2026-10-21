import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { StockApi, StockApiError, type StockItem, type StockSummary } from "../../api/stock";
import { StockPanel } from "./StockPanel";
import { balanceLabel } from "./labels";

const positive: StockItem = {
  item_name: "Ureia",
  unit: "KG",
  entries: 100,
  exits: 30,
  balance: 70,
  negative_balance: false,
  movement_count: 2,
  last_movement_date: "2026-10-05",
};

const negative: StockItem = {
  item_name: "Calcário",
  unit: "KG",
  entries: 0,
  exits: 15,
  balance: -15,
  negative_balance: true,
  movement_count: 1,
  last_movement_date: "2026-10-06",
};

const summary: StockSummary = {
  property_id: "p1",
  as_of: "2026-10-20",
  items: [negative, positive],
  items_with_negative_balance: 1,
  limitations: [],
};

function fakeApi(overrides: Partial<Record<keyof StockApi, unknown>> = {}) {
  return {
    summary: vi.fn().mockResolvedValue(summary),
    createMovement: vi.fn().mockResolvedValue({}),
    ...overrides,
  } as unknown as StockApi;
}

function renderPanel(api: StockApi) {
  return render(<StockPanel tenantId="t1" propertyId="p1" apiBaseUrl="" token="x" api={api} />);
}

function change(label: string | RegExp, value: string) {
  fireEvent.change(screen.getByLabelText(label), { target: { value } });
}

afterEach(cleanup);

describe("StockPanel", () => {
  it("shows a negative balance as is, with an explanation, never as zero", async () => {
    renderPanel(fakeApi());
    expect(await screen.findByText(/-15 kg — saída sem entrada registrada/)).toBeInTheDocument();
    expect(screen.getByText("70 kg")).toBeInTheDocument();
  });

  it("label helper keeps the negative sign", () => {
    expect(balanceLabel(negative)).toContain("-15");
  });

  it("sends an exit with its unit", async () => {
    const api = fakeApi();
    renderPanel(api);
    await screen.findByText("70 kg");
    change("Tipo", "OUT");
    change("Insumo", "Ureia");
    change("Quantidade", "12,5");
    change("Registrado por", "Encarregado");
    change(/Origem do dado/, "caderno");
    fireEvent.click(screen.getByRole("button", { name: "Salvar movimentação" }));
    await waitFor(() => expect(api.createMovement).toHaveBeenCalled());
    expect(vi.mocked(api.createMovement).mock.calls[0][2]).toMatchObject({
      movement_type: "OUT",
      item_name: "Ureia",
      unit: "KG",
      quantity: 12.5,
      counterparty: null,
    });
  });

  it("requires a positive quantity instead of assuming one", async () => {
    const api = fakeApi();
    renderPanel(api);
    await screen.findByText("70 kg");
    change("Insumo", "Ureia");
    change("Registrado por", "Encarregado");
    change(/Origem do dado/, "caderno");
    fireEvent.click(screen.getByRole("button", { name: "Salvar movimentação" }));
    expect(await screen.findByText(/Informe a quantidade, maior que zero/)).toBeInTheDocument();
    expect(api.createMovement).not.toHaveBeenCalled();
  });

  it("explains missing permission", async () => {
    renderPanel(fakeApi({ summary: vi.fn().mockRejectedValue(new StockApiError(403, "forbidden")) }));
    expect(await screen.findByText(/não tem acesso ao estoque/)).toBeInTheDocument();
  });
});
