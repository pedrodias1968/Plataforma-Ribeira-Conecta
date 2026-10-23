import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import type { Farm360Api } from "../api/client";
import { BananaManagementPage } from "./BananaManagementPage";

vi.mock("../features/harvest/HarvestPanel", () => ({ HarvestPanel: ({ fields }: { fields: unknown[] }) => <div>painel colheita ({fields.length} talhões)</div> }));
vi.mock("../features/fertilization/FertilizationPanel", () => ({ FertilizationPanel: () => <div>painel adubação</div> }));
vi.mock("../features/stock/StockPanel", () => ({ StockPanel: () => <div>painel estoque</div> }));
vi.mock("../features/costs/CostPanel", () => ({ CostPanel: () => <div>painel custos</div> }));
vi.mock("../features/sales/SalesPanel", () => ({ SalesPanel: () => <div>painel vendas</div> }));
vi.mock("../features/accountant/AccountantReportPanel", () => ({ AccountantReportPanel: () => <div>painel contador</div> }));
vi.mock("../features/corrections/CorrectionsPanel", () => ({ CorrectionsPanel: () => <div>painel correções</div> }));

afterEach(cleanup);

function fakeApi(items = [{ id: "p1", name: "Sítio Teste" }], fields = [{ id: "f1", name: "Talhão A" }]) {
  return {
    portfolio: vi.fn().mockResolvedValue({ items }),
    fields: vi.fn().mockResolvedValue({ property_id: "p1", items: fields }),
  } as unknown as Farm360Api;
}

describe("BananaManagementPage", () => {
  it("selects the only property and shows one module at a time", async () => {
    const onSelect = vi.fn();
    const api = fakeApi();
    const { rerender } = render(<BananaManagementPage api={api} apiBaseUrl="/api" tenantId="t" token="x" onSelectProperty={onSelect} />);
    await act(async () => { await Promise.resolve(); });
    expect(onSelect).toHaveBeenCalledWith("p1");

    rerender(<BananaManagementPage api={api} apiBaseUrl="/api" tenantId="t" token="x" propertyId="p1" onSelectProperty={onSelect} />);
    await act(async () => { await Promise.resolve(); });
    expect(screen.getByText("painel colheita (1 talhões)")).toBeInTheDocument();
    expect(screen.queryByText("painel vendas")).not.toBeInTheDocument();

    fireEvent.click(screen.getByRole("tab", { name: "Vendas" }));
    expect(screen.getByRole("tab", { name: "Vendas" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByText("painel vendas")).toBeInTheDocument();

    fireEvent.keyDown(screen.getByRole("tab", { name: "Vendas" }), { key: "ArrowRight" });
    expect(screen.getByText("painel contador")).toBeInTheDocument();
  });

  it("explains when the property has no fields yet", async () => {
    render(<BananaManagementPage api={fakeApi(undefined, [])} apiBaseUrl="/api" tenantId="t" token="x" propertyId="p1" onSelectProperty={vi.fn()} />);
    await act(async () => { await Promise.resolve(); });
    expect(screen.getByText(/ainda não tem talhões cadastrados/)).toBeInTheDocument();
  });
});
