import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { CorrectionsApi, CorrectionsApiError, type RecordItem } from "../../api/corrections";
import type { FieldContext } from "../../types/farm360";
import { CorrectionsPanel } from "./CorrectionsPanel";
import { buildPayload, KINDS } from "./kinds";

const sale: RecordItem = {
  id: "s1",
  sale_date: "2026-10-01",
  buyer_name: "Silva",
  quantity: 100,
  quantity_unit: "BOXES",
  unit_price_brl: null,
  price_unit: null,
  total_amount_brl: 3000,
  expected_payment_date: "2026-10-15",
  notes: null,
};

function fakeApi(overrides: Partial<Record<keyof CorrectionsApi, unknown>> = {}) {
  return {
    list: vi.fn().mockResolvedValue([sale]),
    correct: vi.fn().mockResolvedValue({}),
    ...overrides,
  } as unknown as CorrectionsApi;
}

function renderPanel(api: CorrectionsApi) {
  return render(<CorrectionsPanel fields={[] as FieldContext[]} tenantId="t1" propertyId="p1" apiBaseUrl="" token="x" api={api} />);
}

function change(label: string | RegExp, value: string) {
  fireEvent.change(screen.getByLabelText(label), { target: { value } });
}

afterEach(cleanup);

describe("buildPayload", () => {
  it("keeps blank optional values as null, never zero", () => {
    const result = buildPayload(KINDS.sale, {
      sale_date: "2026-10-01", buyer_name: "Silva", total_amount_brl: "3000,50",
      recorded_by: "G", source_reference: "caderno", correction_reason: "erro",
    });
    expect(result).toMatchObject({
      payload: { quantity: null, quantity_unit: null, unit_price_brl: null, total_amount_brl: 3000.5, notes: null },
    });
  });

  it("rejects missing required fields, bad numbers and a missing reason", () => {
    const base = { recorded_by: "G", source_reference: "x", correction_reason: "erro" };
    expect(buildPayload(KINDS.payment, { payment_date: "2026-10-01", amount_brl: "0", ...base })).toHaveProperty("error");
    expect(buildPayload(KINDS.payment, { payment_date: "", amount_brl: "5", ...base })).toHaveProperty("error");
    expect(buildPayload(KINDS.harvest, { harvest_date: "2026-10-01", boxes_packed: "1,5", ...base })).toHaveProperty("error");
    expect(buildPayload(KINDS.stock, { movement_date: "2026-10-01", movement_type: "IN", item_name: "U", unit: "KG", quantity: "3", recorded_by: "G", source_reference: "x", correction_reason: " " })).toHaveProperty("error");
  });
});

describe("CorrectionsPanel", () => {
  it("lists current records and sends a correction with its reason", async () => {
    const api = fakeApi();
    renderPanel(api);
    expect(await screen.findByText(/2026-10-01 — Silva — total R\$ 3000/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Corrigir" }));
    expect(screen.getByLabelText("Comprador")).toHaveValue("Silva");
    change("Valor total (R$)", "2800");
    change("Motivo da correção", "total errado");
    change("Corrigido por", "Gerente");
    change("Origem da correção", "nota fiscal");
    fireEvent.click(screen.getByRole("button", { name: "Salvar correção" }));
    await waitFor(() => expect(api.correct).toHaveBeenCalled());
    const [tenant, kind, id, payload] = vi.mocked(api.correct).mock.calls[0];
    expect([tenant, kind, id]).toEqual(["t1", "sale", "s1"]);
    expect(payload).toMatchObject({ total_amount_brl: 2800, correction_reason: "total errado", unit_price_brl: null });
  });

  it("requires a reason before sending", async () => {
    const api = fakeApi();
    renderPanel(api);
    await screen.findByText(/Silva/);
    fireEvent.click(screen.getByRole("button", { name: "Corrigir" }));
    change("Corrigido por", "Gerente");
    change("Origem da correção", "nota");
    fireEvent.click(screen.getByRole("button", { name: "Salvar correção" }));
    expect(await screen.findByText(/Preencha: Motivo da correção/)).toBeInTheDocument();
    expect(api.correct).not.toHaveBeenCalled();
  });

  it("explains an already-corrected record and refreshes", async () => {
    const api = fakeApi({ correct: vi.fn().mockRejectedValue(new CorrectionsApiError(409, "conflict")) });
    renderPanel(api);
    await screen.findByText(/Silva/);
    fireEvent.click(screen.getByRole("button", { name: "Corrigir" }));
    change("Motivo da correção", "x");
    change("Corrigido por", "G");
    change("Origem da correção", "x");
    fireEvent.click(screen.getByRole("button", { name: "Salvar correção" }));
    expect(await screen.findByText(/já foi corrigido/)).toBeInTheDocument();
    expect(api.list).toHaveBeenCalledTimes(2);
  });

  it("loads the list of the chosen kind and explains missing permission", async () => {
    const api = fakeApi({ list: vi.fn().mockRejectedValue(new CorrectionsApiError(403, "forbidden")) });
    renderPanel(api);
    expect(await screen.findByText(/não tem acesso a estes registros/)).toBeInTheDocument();
    change("Tipo de registro", "stock");
    await waitFor(() => expect(api.list).toHaveBeenLastCalledWith("t1", "p1", "stock"));
  });
});
