import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { PropertyAnalyses } from "./PropertyAnalyses";

afterEach(cleanup);

describe("PropertyAnalyses", () => {
  it("shows the five-step flow and says the analyses are not available yet", () => {
    render(<PropertyAnalyses />);
    for (const step of ["Informe a área", "Escolha as análises", "Cruzamento das fontes", "Diagnóstico", "Decisão e documento"]) {
      expect(screen.getByRole("heading", { name: step })).toBeInTheDocument();
    }
    expect(screen.getByText(/Ainda não estão disponíveis/)).toBeInTheDocument();
    expect(within(screen.getByRole("tabpanel")).getByText("Em planejamento")).toBeInTheDocument();
  });

  it("switches the analysis group by click and by arrow keys", () => {
    render(<PropertyAnalyses />);
    expect(screen.getByRole("tabpanel")).toHaveTextContent(/CAR, SIGEF e SNCI/);

    fireEvent.click(screen.getByRole("tab", { name: "Crédito rural" }));
    expect(screen.getByRole("tab", { name: "Crédito rural" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("tabpanel")).toHaveTextContent(/MCR 2\.9/);

    fireEvent.keyDown(screen.getByRole("tab", { name: "Crédito rural" }), { key: "ArrowRight" });
    expect(screen.getByRole("tab", { name: "Entrega" })).toHaveAttribute("aria-selected", "true");
    expect(screen.getByRole("tabpanel")).toHaveTextContent(/Relatório em PDF/);
  });
});
