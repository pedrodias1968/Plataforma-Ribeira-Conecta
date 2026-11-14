import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { SoilApi, SoilApiError, type SamplingGridPreview } from "../../api/soil";
import type { FieldContext } from "../../types/farm360";
import { SamplingPreview } from "./SamplingPreview";

afterEach(cleanup);

const field = { id: "f1", name: "Talhão A" } as FieldContext;

const preview: SamplingGridPreview = {
  field_id: "f1",
  property_id: "p",
  status: "PREVIEW_NOT_PERSISTED",
  projected_crs: "EPSG:31983",
  spacing_m: 50,
  derivation_method: "REGULAR_GRID",
  points: {
    type: "FeatureCollection",
    features: [
      {
        type: "Feature",
        geometry: { type: "Point", coordinates: [-47.85123456, -24.49123456] },
        properties: {},
      },
      {
        type: "Feature",
        geometry: { type: "Point", coordinates: [-47.8515, -24.4915] },
        properties: {},
      },
    ],
  },
};

function fakeApi(overrides: Record<string, unknown> = {}) {
  return {
    samplingGridPreview: vi.fn().mockResolvedValue(preview),
    ...overrides,
  } as unknown as SoilApi;
}

function renderPreview(api: SoilApi) {
  render(<SamplingPreview fields={[field]} tenantId="t" propertyId="p" api={api} />);
}

describe("SamplingPreview", () => {
  it("keeps the generate button disabled until a field and positive spacing exist", async () => {
    const api = fakeApi();
    renderPreview(api);
    const button = screen.getByRole("button", { name: "Gerar prévia" });
    expect(button).toBeDisabled();

    fireEvent.change(screen.getByLabelText("Talhão"), { target: { value: "f1" } });
    expect(button).toBeDisabled();

    fireEvent.change(screen.getByLabelText("Espaçamento (m)"), { target: { value: "0" } });
    expect(button).toBeDisabled();

    fireEvent.change(screen.getByLabelText("Espaçamento (m)"), { target: { value: "50" } });
    expect(button).toBeEnabled();
  });

  it("calls samplingGridPreview with the selected field and spacing", async () => {
    const api = fakeApi();
    renderPreview(api);
    fireEvent.change(screen.getByLabelText("Talhão"), { target: { value: "f1" } });
    fireEvent.change(screen.getByLabelText("Espaçamento (m)"), { target: { value: "50" } });
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "Gerar prévia" }));
    });
    expect(api.samplingGridPreview).toHaveBeenCalledWith("t", "p", "f1", 50);
  });

  it("shows the not-saved warning and the number of points", async () => {
    const api = fakeApi();
    renderPreview(api);
    fireEvent.change(screen.getByLabelText("Talhão"), { target: { value: "f1" } });
    fireEvent.change(screen.getByLabelText("Espaçamento (m)"), { target: { value: "50" } });
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "Gerar prévia" }));
    });
    expect(screen.getByText(/Prévia não salva/)).toBeInTheDocument();
    expect(screen.getByText(/DERIVED_LOCATION/)).toBeInTheDocument();
    const status = screen.getByText(/2 ponto/);
    expect(status.textContent).toContain("EPSG:31983");
    expect(screen.getByText("-47.851235")).toBeInTheDocument();
  });

  it("downloads the exact received FeatureCollection as GeoJSON", async () => {
    const api = fakeApi();
    const blobParts: unknown[] = [];
    class CaptureBlob {
      constructor(parts: BlobPart[]) {
        blobParts.push(parts[0]);
      }
    }
    vi.stubGlobal("Blob", CaptureBlob);
    const createObjectURL = vi.fn().mockReturnValue("blob:preview");
    const revokeObjectURL = vi.fn();
    vi.stubGlobal("URL", { ...URL, createObjectURL, revokeObjectURL });
    renderPreview(api);
    fireEvent.change(screen.getByLabelText("Talhão"), { target: { value: "f1" } });
    fireEvent.change(screen.getByLabelText("Espaçamento (m)"), { target: { value: "50" } });
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "Gerar prévia" }));
    });
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "Baixar GeoJSON" }));
    });
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 0));
    });
    expect(blobParts).toHaveLength(1);
    expect(blobParts[0]).toBe(JSON.stringify(preview.points));
    expect(createObjectURL).toHaveBeenCalledTimes(1);
    expect(revokeObjectURL).toHaveBeenCalledWith("blob:preview");
    vi.unstubAllGlobals();
  });

  it("shows a dedicated message for 403", async () => {
    const api = fakeApi({
      samplingGridPreview: vi.fn().mockRejectedValue(new SoilApiError(403, "forbidden")),
    });
    renderPreview(api);
    fireEvent.change(screen.getByLabelText("Talhão"), { target: { value: "f1" } });
    fireEvent.change(screen.getByLabelText("Espaçamento (m)"), { target: { value: "50" } });
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "Gerar prévia" }));
    });
    expect(screen.getByText("Sem permissão para ver a prévia de amostragem.")).toBeInTheDocument();
  });

  it("shows a dedicated message for 404", async () => {
    const api = fakeApi({
      samplingGridPreview: vi.fn().mockRejectedValue(new SoilApiError(404, "not found")),
    });
    renderPreview(api);
    fireEvent.change(screen.getByLabelText("Talhão"), { target: { value: "f1" } });
    fireEvent.change(screen.getByLabelText("Espaçamento (m)"), { target: { value: "50" } });
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "Gerar prévia" }));
    });
    expect(screen.getByText("Talhão não encontrado.")).toBeInTheDocument();
  });

  it("shows a dedicated message for 422", async () => {
    const api = fakeApi({
      samplingGridPreview: vi.fn().mockRejectedValue(new SoilApiError(422, "unprocessable")),
    });
    renderPreview(api);
    fireEvent.change(screen.getByLabelText("Talhão"), { target: { value: "f1" } });
    fireEvent.change(screen.getByLabelText("Espaçamento (m)"), { target: { value: "50" } });
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "Gerar prévia" }));
    });
    expect(screen.getByText("Espaçamento inválido ou grade grande demais para este talhão.")).toBeInTheDocument();
  });

  const twoFields = [
    { id: "f1", name: "Talhão A" },
    { id: "f2", name: "Talhão B" },
  ] as FieldContext[];

  it("hides the previous preview when the field changes after generating", async () => {
    const api = fakeApi();
    render(<SamplingPreview fields={twoFields} tenantId="t" propertyId="p" api={api} />);
    fireEvent.change(screen.getByLabelText("Talhão"), { target: { value: "f1" } });
    fireEvent.change(screen.getByLabelText("Espaçamento (m)"), { target: { value: "50" } });
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "Gerar prévia" }));
    });
    expect(screen.getByText("-47.851235")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Talhão"), { target: { value: "f2" } });
    expect(screen.queryByText("-47.851235")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Baixar GeoJSON" })).not.toBeInTheDocument();
  });

  it("hides the previous preview when the spacing changes after generating", async () => {
    const api = fakeApi();
    renderPreview(api);
    fireEvent.change(screen.getByLabelText("Talhão"), { target: { value: "f1" } });
    fireEvent.change(screen.getByLabelText("Espaçamento (m)"), { target: { value: "50" } });
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "Gerar prévia" }));
    });
    expect(screen.getByText("-47.851235")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Espaçamento (m)"), { target: { value: "25" } });
    expect(screen.queryByText("-47.851235")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Baixar GeoJSON" })).not.toBeInTheDocument();
  });

  it("ignores a late response for a previously selected field", async () => {
    let resolvePreview!: (value: SamplingGridPreview) => void;
    const deferred = new Promise<SamplingGridPreview>((resolve) => {
      resolvePreview = resolve;
    });
    const api = fakeApi({ samplingGridPreview: vi.fn().mockReturnValue(deferred) });
    render(<SamplingPreview fields={twoFields} tenantId="t" propertyId="p" api={api} />);
    fireEvent.change(screen.getByLabelText("Talhão"), { target: { value: "f1" } });
    fireEvent.change(screen.getByLabelText("Espaçamento (m)"), { target: { value: "50" } });
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "Gerar prévia" }));
    });

    fireEvent.change(screen.getByLabelText("Talhão"), { target: { value: "f2" } });
    await act(async () => {
      resolvePreview(preview);
      await deferred;
    });
    expect(screen.queryByText("-47.851235")).not.toBeInTheDocument();
  });

  it("revokes the object URL asynchronously after the download click", async () => {
    vi.useFakeTimers();
    const api = fakeApi();
    class CaptureBlob {
      constructor(parts: BlobPart[]) {
        void parts;
      }
    }
    vi.stubGlobal("Blob", CaptureBlob);
    const createObjectURL = vi.fn().mockReturnValue("blob:preview");
    const revokeObjectURL = vi.fn();
    vi.stubGlobal("URL", { ...URL, createObjectURL, revokeObjectURL });
    renderPreview(api);
    fireEvent.change(screen.getByLabelText("Talhão"), { target: { value: "f1" } });
    fireEvent.change(screen.getByLabelText("Espaçamento (m)"), { target: { value: "50" } });
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "Gerar prévia" }));
    });
    await act(async () => {
      fireEvent.click(screen.getByRole("button", { name: "Baixar GeoJSON" }));
    });
    expect(revokeObjectURL).not.toHaveBeenCalled();
    await act(async () => {
      vi.runAllTimers();
    });
    expect(revokeObjectURL).toHaveBeenCalledWith("blob:preview");
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });
});
