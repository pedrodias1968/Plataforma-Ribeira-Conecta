import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { FertilizationApi, FertilizationApiError, type FertilizationSummary } from "../../api/fertilization";
import type { FieldContext } from "../../types/farm360";
import { FertilizationPanel } from "./FertilizationPanel";
import { costLabel, quantityLabel } from "./labels";

const emptyBlock = {
  record_count: 0,
  last_application_date: null,
  products: [],
  quantity_by_unit: {},
  records_without_quantity: 0,
  cost_brl: { total: null, records_with_value: 0, records_without_value: 0 },
};

const summary: FertilizationSummary = {
  property_id: "p1",
  date_from: null,
  date_to: null,
  classification: "CALCULATED",
  limitations: [],
  property_totals: emptyBlock,
  fields: [
    {
      ...emptyBlock,
      field_id: "f1",
      field_name: "Talhão A",
      no_fertilization_records: false,
      record_count: 2,
      last_application_date: "2026-10-12",
      products: ["Ureia"],
      quantity_by_unit: { KG: 50, L: 10 },
      records_without_quantity: 1,
      cost_brl: { total: 200, records_with_value: 1, records_without_value: 1 },
    },
    { ...emptyBlock, field_id: "f2", field_name: "Talhão B", no_fertilization_records: true },
  ],
};

const fields = [
  { id: "f1", name: "Talhão A" },
  { id: "f2", name: "Talhão B" },
] as FieldContext[];

function fakeApi(overrides: Partial<Record<keyof FertilizationApi, unknown>> = {}) {
  return {
    summary: vi.fn().mockResolvedValue(summary),
    createRecord: vi.fn().mockResolvedValue({}),
    ...overrides,
  } as unknown as FertilizationApi;
}

function renderPanel(api: FertilizationApi) {
  return render(<FertilizationPanel fields={fields} tenantId="t1" propertyId="p1" apiBaseUrl="" token="x" api={api} />);
}

function change(label: string | RegExp, value: string) {
  fireEvent.change(screen.getByLabelText(label), { target: { value } });
}

afterEach(cleanup);

describe("FertilizationPanel", () => {
  it("lists units separately and flags unknown values instead of showing zero", async () => {
    renderPanel(fakeApi());
    expect(await screen.findByText(/50 kg · 10 L/)).toBeInTheDocument();
    expect(screen.getByText(/1 aplicação\(ões\) sem quantidade/)).toBeInTheDocument();
    expect(screen.getByText(/1 aplicação\(ões\) sem custo informado/)).toBeInTheDocument();
    expect(screen.getByText("12/10/2026")).toBeInTheDocument();
    expect(screen.getByText("sem registro de adubação")).toBeInTheDocument();
  });

  it("label helpers never turn unknown into zero", () => {
    expect(costLabel(emptyBlock.cost_brl)).toBe("sem registro");
    expect(quantityLabel(emptyBlock)).toBe("sem registro");
  });

  it("sends blank quantity, area and cost as null", async () => {
    const api = fakeApi();
    renderPanel(api);
    await screen.findByText(/50 kg · 10 L/);
    change("Talhão", "f1");
    change("Produto", "Ureia");
    change("Aplicado por", "João");
    change("Registrado por", "Encarregado");
    change(/Origem do dado/, "caderno");
    fireEvent.click(screen.getByRole("button", { name: "Salvar aplicação" }));
    await waitFor(() => expect(api.createRecord).toHaveBeenCalled());
    expect(vi.mocked(api.createRecord).mock.calls[0][2]).toMatchObject({
      field_id: "f1",
      product_name: "Ureia",
      quantity: null,
      quantity_unit: null,
      area_applied_ha: null,
      cost_brl: null,
    });
  });

  it("sends the unit only with a quantity", async () => {
    const api = fakeApi();
    renderPanel(api);
    await screen.findByText(/50 kg · 10 L/);
    change("Talhão", "f1");
    change("Produto", "Ureia");
    change("Quantidade", "25,5");
    change("Aplicado por", "João");
    change("Registrado por", "Encarregado");
    change(/Origem do dado/, "caderno");
    fireEvent.click(screen.getByRole("button", { name: "Salvar aplicação" }));
    await waitFor(() => expect(api.createRecord).toHaveBeenCalled());
    expect(vi.mocked(api.createRecord).mock.calls[0][2]).toMatchObject({ quantity: 25.5, quantity_unit: "KG" });
  });

  it("requires the product and the field", async () => {
    const api = fakeApi();
    renderPanel(api);
    await screen.findByText(/50 kg · 10 L/);
    fireEvent.click(screen.getByRole("button", { name: "Salvar aplicação" }));
    expect(await screen.findByText("Escolha o talhão.")).toBeInTheDocument();
    expect(api.createRecord).not.toHaveBeenCalled();
  });

  it("explains missing permission", async () => {
    renderPanel(fakeApi({ summary: vi.fn().mockRejectedValue(new FertilizationApiError(403, "forbidden")) }));
    expect(await screen.findByText(/não tem acesso aos registros de adubação/)).toBeInTheDocument();
  });
});
