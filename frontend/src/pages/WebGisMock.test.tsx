import { cleanup, render, screen } from "@testing-library/react";
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
});
