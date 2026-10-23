import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { LandingPage } from "./LandingPage";

afterEach(cleanup);

describe("LandingPage social links", () => {
  it("links to LinkedIn and Instagram in a new tab", () => {
    render(<LandingPage />);
    const linkedin = screen.getAllByRole("link", { name: /no LinkedIn/ });
    const instagram = screen.getAllByRole("link", { name: /no Instagram/ });
    expect(linkedin[0]).toHaveAttribute("href", "https://www.linkedin.com/company/ribeira-conecta");
    expect(instagram[0]).toHaveAttribute("href", "https://www.instagram.com/ribeiraconecta/");
    expect(linkedin[0]).toHaveAttribute("rel", "noopener noreferrer");
    expect(linkedin.length).toBe(2);
  });
});
