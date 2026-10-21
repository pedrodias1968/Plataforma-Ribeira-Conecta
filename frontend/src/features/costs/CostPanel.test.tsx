import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { CostApi, CostApiError, type CostFieldSummary, type CostSummary } from "../../api/costs";
import type { FieldContext } from "../../types/farm360";
import { CostPanel } from "./CostPanel";
import { costPerKgLabel, moneyLabel } from "./labels";

const noManual = { entry_count: 0, total: null, by_category: {} };
const noFert = { record_count: 0, total: null, records_with_value: 0, records_without_value: 0 };
const noHarvest = { record_count: 0, weight_kg_total: null, records_with_weight: 0, records_without_weight: 0 };

const withCost: CostFieldSummary = {
  field_id: "f1",
  field_name: "Talhão A",
  manual_cost: { entry_count: 1, total: 300, by_category: { LABOR: 300 } },
  fertilization_cost: { record_count: 2, total: 100, records_with_value: 1, records_without_value: 1 },
  allocated_cost_total: 400,
  cost_is_partial: true,
  harvest: { record_count: 2, weight_kg_total: 400, records_with_weight: 2, records_without_weight: 0 },
  cost_per_kg: 1,
  cost_per_kg_unavailable_reason: null,
};

const noData: CostFieldSummary = {
  field_id: "f2",
  field_name: "Talhão B",
  manual_cost: noManual,
  fertilization_cost: noFert,
  allocated_cost_total: null,
  cost_is_partial: false,
  harvest: noHarvest,
  cost_per_kg: null,
  cost_per_kg_unavailable_reason: "NO_COST_DATA",
};

const summary: CostSummary = {
  property_id: "p1",
  date_from: null,
  date_to: null,
  classification: "CALCULATED",
  limitations: [],
  unallocated_cost: { entry_count: 1, total: 1000, by_category: { FUEL: 1000 } },
  fields: [withCost, noData],
};

const fields = [
  { id: "f1", name: "Talhão A" },
  { id: "f2", name: "Talhão B" },
] as FieldContext[];

function fakeApi(overrides: Partial<Record<keyof CostApi, unknown>> = {}) {
  return {
    summary: vi.fn().mockResolvedValue(summary),
    createEntry: vi.fn().mockResolvedValue({}),
    ...overrides,
  } as unknown as CostApi;
}

function renderPanel(api: CostApi) {
  return render(<CostPanel fields={fields} tenantId="t1" propertyId="p1" apiBaseUrl="" token="x" api={api} />);
}

function change(label: string | RegExp, value: string) {
  fireEvent.change(screen.getByLabelText(label), { target: { value } });
}

afterEach(cleanup);

describe("CostPanel", () => {
  it("shows cost per kg when computable and says why when not, never zero", async () => {
    renderPanel(fakeApi());
    expect(await screen.findByText(/R\$\s*1,00\/kg/)).toBeInTheDocument();
    expect(screen.getByText("indisponível — sem custo registrado")).toBeInTheDocument();
    expect(screen.getByText(/parcial: 1 adubação\(ões\) sem custo/)).toBeInTheDocument();
    expect(screen.getByText(/sítio inteiro \(não rateados entre talhões\): R\$\s*1\.000,00/i)).toBeInTheDocument();
    expect(screen.queryByText(/R\$\s*0,00/)).not.toBeInTheDocument();
  });

  it("label helpers keep unknown as unknown", () => {
    expect(moneyLabel(null)).toBe("sem registro");
    expect(costPerKgLabel(noData)).toBe("indisponível — sem custo registrado");
    expect(costPerKgLabel({ ...noData, cost_per_kg_unavailable_reason: "SOME_HARVEST_WITHOUT_WEIGHT" })).toBe(
      "indisponível — há colheita sem peso informado",
    );
  });

  it("sends a property-wide cost with null field", async () => {
    const api = fakeApi();
    renderPanel(api);
    await screen.findByText(/R\$\s*1,00\/kg/);
    change("Descrição", "Diesel do trator");
    change(/Valor/, "250,50");
    change("Registrado por", "Gerente");
    change(/Origem do dado/, "nota fiscal");
    fireEvent.click(screen.getByRole("button", { name: "Salvar custo" }));
    await waitFor(() => expect(api.createEntry).toHaveBeenCalled());
    expect(vi.mocked(api.createEntry).mock.calls[0][2]).toMatchObject({
      field_id: null,
      description: "Diesel do trator",
      amount_brl: 250.5,
      category: "LABOR",
    });
  });

  it("requires a value instead of assuming zero", async () => {
    const api = fakeApi();
    renderPanel(api);
    await screen.findByText(/R\$\s*1,00\/kg/);
    change("Descrição", "Diárias");
    change("Registrado por", "Gerente");
    change(/Origem do dado/, "caderno");
    fireEvent.click(screen.getByRole("button", { name: "Salvar custo" }));
    expect(await screen.findByText(/Informe o valor em reais/)).toBeInTheDocument();
    expect(api.createEntry).not.toHaveBeenCalled();
  });

  it("explains missing permission", async () => {
    renderPanel(fakeApi({ summary: vi.fn().mockRejectedValue(new CostApiError(403, "forbidden")) }));
    expect(await screen.findByText(/não tem acesso aos custos/)).toBeInTheDocument();
  });
});
