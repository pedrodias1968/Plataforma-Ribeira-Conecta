import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { HarvestApi, HarvestApiError, type HarvestSummary } from "../../api/harvest";
import type { FieldContext } from "../../types/farm360";
import { HarvestPanel, measureLabel } from "./HarvestPanel";

const measure = (total: number | null, without = 0) => ({
  total,
  records_with_value: total === null ? 0 : 1,
  records_without_value: without,
});

const emptyBlock = {
  record_count: 0,
  discard_record_count: 0,
  bunches_harvested: measure(null),
  boxes_packed: measure(null),
  weight_kg: measure(null),
  discards_by_unit: {},
};

const summary: HarvestSummary = {
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
      no_harvest_records: false,
      record_count: 1,
      boxes_packed: measure(120),
      discards_by_unit: { BOXES: { total: 7, by_reason: { STAIN: 7 } } },
    },
    { ...emptyBlock, field_id: "f2", field_name: "Talhão B", no_harvest_records: true },
  ],
};

const fields = [
  { id: "f1", name: "Talhão A" },
  { id: "f2", name: "Talhão B" },
] as FieldContext[];

function fakeApi(overrides: Partial<Record<keyof HarvestApi, unknown>> = {}) {
  return {
    summary: vi.fn().mockResolvedValue(summary),
    createRecord: vi.fn().mockResolvedValue({}),
    createDiscard: vi.fn().mockResolvedValue({}),
    ...overrides,
  } as unknown as HarvestApi;
}

function renderPanel(api: HarvestApi) {
  return render(<HarvestPanel fields={fields} tenantId="t1" propertyId="p1" apiBaseUrl="" token="x" api={api} />);
}

afterEach(cleanup);

describe("HarvestPanel", () => {
  it("shows missing measures as 'sem registro', never as zero", async () => {
    renderPanel(fakeApi());
    expect(await screen.findByText("120 caixas")).toBeInTheDocument();
    expect(screen.getAllByText("sem registro").length).toBeGreaterThan(0);
    expect(screen.getByText("sem registro de colheita")).toBeInTheDocument();
    expect(screen.getByText("7 caixas (Mancha 7)")).toBeInTheDocument();
    expect(screen.queryByText(/^0 /)).not.toBeInTheDocument();
  });

  it("measureLabel flags records without the measure", () => {
    expect(measureLabel(measure(10, 2), "kg")).toContain("2 registro(s) sem esta medida");
    expect(measureLabel(measure(null), "kg")).toBe("sem registro");
  });

  it("sends blank measures as null", async () => {
    const api = fakeApi();
    renderPanel(api);
    await screen.findByText("120 caixas");
    fireEvent.change(screen.getByLabelText("Talhão"), { target: { value: "f1" } });
    fireEvent.change(screen.getByLabelText("Caixas embaladas"), { target: { value: "90" } });
    fireEvent.change(screen.getByLabelText("Registrado por"), { target: { value: "Encarregado" } });
    fireEvent.change(screen.getByLabelText(/Origem do dado/), { target: { value: "caderno" } });
    fireEvent.click(screen.getByRole("button", { name: "Salvar registro" }));
    await waitFor(() => expect(api.createRecord).toHaveBeenCalled());
    expect(vi.mocked(api.createRecord).mock.calls[0][2]).toMatchObject({
      field_id: "f1",
      boxes_packed: 90,
      bunches_harvested: null,
      weight_kg: null,
    });
  });

  it("requires at least one measure", async () => {
    const api = fakeApi();
    renderPanel(api);
    await screen.findByText("120 caixas");
    fireEvent.change(screen.getByLabelText("Talhão"), { target: { value: "f1" } });
    fireEvent.change(screen.getByLabelText("Registrado por"), { target: { value: "Encarregado" } });
    fireEvent.change(screen.getByLabelText(/Origem do dado/), { target: { value: "caderno" } });
    fireEvent.click(screen.getByRole("button", { name: "Salvar registro" }));
    expect(await screen.findByText(/Informe ao menos uma medida/)).toBeInTheDocument();
    expect(api.createRecord).not.toHaveBeenCalled();
  });

  it("explains missing permission", async () => {
    renderPanel(fakeApi({ summary: vi.fn().mockRejectedValue(new HarvestApiError(403, "forbidden")) }));
    expect(await screen.findByText(/não tem acesso aos registros de colheita/)).toBeInTheDocument();
  });
});
