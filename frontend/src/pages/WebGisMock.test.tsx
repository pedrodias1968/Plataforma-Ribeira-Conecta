import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { WebGisMock } from "./WebGisMock";

afterEach(cleanup);

describe("WebGisMock", () => {
  it("says on screen that the map is an illustration with fictional data", () => {
    render(<WebGisMock />);
    expect(screen.getByText("Ilustração · dados fictícios")).toBeInTheDocument();
    expect(screen.getByText(/Não representam uma propriedade real/)).toBeInTheDocument();
    expect(screen.getByText(/nunca como zero/)).toBeInTheDocument();
  });

  it("toggles layers and selects a parcel without leaving the illustration", () => {
    render(<WebGisMock />);
    const water = screen.getByRole("button", { name: "Água e inundação" });
    expect(water).toHaveAttribute("aria-pressed", "false");
    fireEvent.click(water);
    expect(water).toHaveAttribute("aria-pressed", "true");

    fireEvent.click(screen.getByRole("button", { name: "Talhão A (exemplo fictício)" }));
    expect(screen.getByText(/Talhão A · exemplo/)).toBeInTheDocument();
    expect(screen.getByText(/0,71/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Talhões" }));
    expect(screen.queryByRole("button", { name: "Talhão A (exemplo fictício)" })).not.toBeInTheDocument();
  });

  it("renders the hero copy passed as children", () => {
    render(<WebGisMock><h1>Título</h1></WebGisMock>);
    expect(screen.getByRole("heading", { name: "Título" })).toBeInTheDocument();
  });
});
