import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { SoilApi, SoilApiError, type SoilLabAnalysis, type SoilSamplePoint } from "../../api/soil";
import type { FieldContext } from "../../types/farm360";
import { valueLabel } from "./labels";
import { SoilPanel } from "./SoilPanel";

afterEach(cleanup);

const field = { id: "f1", name: "Talhão A" } as FieldContext;
const sample: SoilSamplePoint = {
  id: "s1", tenant_id: "t", property_id: "p", field_id: "f1", sample_code: "T1-0-20", depth_top_cm: 0, depth_bottom_cm: 20,
  collection_date: "2026-10-01", collector_name: "Ana", location_geojson: { type: "Point", coordinates: [-47.85, -24.49] },
  location_crs: "EPSG:4326", classification: "MANUAL_CONFIRMED", source_reference: "GPS", status: "COLLECTED", created_at: "2026-10-01T10:00:00Z",
};
const analysis = {
  id: "a1", sample_point_id: "s1", lab_name: "Lab X", report_number: "123", report_date: "2026-10-10",
  ph_h2o: 5.6, ph_cacl2: null, organic_matter_g_dm3: null, phosphorus_mg_dm3: null, potassium_cmolc_dm3: null, calcium_cmolc_dm3: null,
  magnesium_cmolc_dm3: null, aluminum_cmolc_dm3: null, potential_acidity_h_al: null, cation_exchange_capacity_cec: null,
  base_saturation_percent: null, clay_percent: null, silt_percent: null, sand_percent: null, created_at: "2026-10-10T10:00:00Z",
} satisfies SoilLabAnalysis;

function fakeApi(overrides: Record<string, unknown> = {}) {
  return {
    samples: vi.fn().mockResolvedValue([sample]),
    analyses: vi.fn().mockResolvedValue([analysis]),
    createSample: vi.fn().mockResolvedValue(sample),
    createAnalysis: vi.fn().mockResolvedValue(analysis),
    ...overrides,
  } as unknown as SoilApi;
}

async function renderPanel(api: SoilApi) {
  render(<SoilPanel fields={[field]} tenantId="t" propertyId="p" apiBaseUrl="/api" token="x" api={api} />);
  await act(async () => { await Promise.resolve(); await Promise.resolve(); });
}

describe("SoilPanel", () => {
  it("shows missing lab values as 'sem registro', never zero", async () => {
    await renderPanel(fakeApi());
    expect(screen.getByText("T1-0-20")).toBeInTheDocument();
    expect(screen.getByText("5,6")).toBeInTheDocument();
    expect(screen.getAllByText("sem registro")).toHaveLength(2);
    expect(valueLabel(null, "%")).toBe("sem registro");
    expect(valueLabel(0, "%")).toBe("0 %");
  });

  it("requires coordinates and sends blank lab values as null", async () => {
    const api = fakeApi();
    await renderPanel(api);
    fireEvent.change(screen.getByLabelText("Código da amostra"), { target: { value: "T2" } });
    fireEvent.change(screen.getByLabelText("Coletado por"), { target: { value: "Ana" } });
    fireEvent.change(screen.getByLabelText("Origem do dado (GPS, caderno…)"), { target: { value: "GPS" } });
    fireEvent.click(screen.getByRole("button", { name: "Salvar amostra" }));
    expect(screen.getByText(/longitude e latitude/)).toBeInTheDocument();
    expect(api.createSample).not.toHaveBeenCalled();

    fireEvent.change(screen.getByLabelText("Amostra"), { target: { value: "s1" } });
    fireEvent.change(screen.getByLabelText("Laboratório"), { target: { value: "Lab X" } });
    fireEvent.change(screen.getByLabelText("Número do laudo"), { target: { value: "9" } });
    fireEvent.change(screen.getByLabelText("pH em água"), { target: { value: "5,8" } });
    await act(async () => { fireEvent.click(screen.getByRole("button", { name: "Salvar laudo" })); });
    const payload = vi.mocked(api.createAnalysis).mock.calls[0][2];
    expect(payload.ph_h2o).toBe(5.8);
    expect(payload.calcium_cmolc_dm3).toBeNull();
    expect(payload.base_saturation_percent).toBeNull();
  });

  it("explains when the profile has no soil access", async () => {
    await renderPanel(fakeApi({ samples: vi.fn().mockRejectedValue(new SoilApiError(403, "forbidden")) }));
    expect(screen.getByText(/não tem acesso às análises de solo/)).toBeInTheDocument();
  });
});
