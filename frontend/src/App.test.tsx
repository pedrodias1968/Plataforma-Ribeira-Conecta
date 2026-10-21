import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

afterEach(() => {
  cleanup();
  vi.unstubAllEnvs();
  vi.resetModules();
});

describe("App site mode", () => {
  it("renders only the public landing page when built in landing mode", async () => {
    vi.stubEnv("VITE_RIBEIRA_SITE_MODE", "landing");
    const { default: App } = await import("./App");
    render(<App />);
    expect(await screen.findByText(/ERP Especializado em Bananicultura/)).toBeInTheDocument();
    expect(screen.queryByText(/Configuração OIDC necessária/)).not.toBeInTheDocument();
  });

  it("keeps the authenticated app (and its config check) outside landing mode", async () => {
    vi.stubEnv("VITE_RIBEIRA_SITE_MODE", "");
    const { default: App } = await import("./App");
    render(<App />);
    expect(screen.getByText(/Configuração/)).toBeInTheDocument();
  });
});
