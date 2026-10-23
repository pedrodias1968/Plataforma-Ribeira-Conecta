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
    // A landing é carregada sob demanda e tem uma cena SVG grande: a primeira importação fria pode passar de 5 s.
    expect(await screen.findByText(/ERP Especializado em Bananicultura/, {}, { timeout: 15000 })).toBeInTheDocument();
    expect(screen.queryByText(/Configuração OIDC necessária/)).not.toBeInTheDocument();
  }, 20000);

  it("keeps the authenticated app (and its config check) outside landing mode", async () => {
    vi.stubEnv("VITE_RIBEIRA_SITE_MODE", "");
    vi.stubEnv("VITE_RIBEIRA_AUTH_MODE", "development");
    vi.stubEnv("VITE_RIBEIRA_PUBLIC_ORIGIN", "");
    vi.stubEnv("VITE_RIBEIRA_API_URL", "");
    vi.stubEnv("VITE_RIBEIRA_TENANT_ID", "");
    const { default: App } = await import("./App");
    render(<App />);
    expect(screen.getByText(/Configuração/)).toBeInTheDocument();
  });

  describe("origem pública (OIDC)", () => {
    const oidcEnv = () => {
      vi.stubEnv("VITE_RIBEIRA_SITE_MODE", "");
      vi.stubEnv("VITE_RIBEIRA_AUTH_MODE", "oidc");
      vi.stubEnv("VITE_RIBEIRA_PUBLIC_ORIGIN", "https://app.example.test");
      vi.stubEnv("VITE_RIBEIRA_TENANT_ID", "tenant");
      vi.stubEnv("VITE_RIBEIRA_OIDC_AUDIENCE", "aud");
      vi.stubEnv("VITE_RIBEIRA_OIDC_AUTHORIZATION_ENDPOINT", "https://idp.example.test/authorize");
      vi.stubEnv("VITE_RIBEIRA_OIDC_TOKEN_ENDPOINT", "https://idp.example.test/token");
      vi.stubEnv("VITE_RIBEIRA_OIDC_CLIENT_ID", "client");
      vi.stubEnv("VITE_RIBEIRA_OIDC_REDIRECT_URI", "https://app.example.test/");
    };

    it("mostra a landing em / e oferece o botão Entrar", async () => {
      oidcEnv();
      window.history.replaceState({}, "", "/");
      const { default: App } = await import("./App");
      render(<App />);
      expect(await screen.findByText(/ERP Especializado em Bananicultura/)).toBeInTheDocument();
      expect(screen.getAllByRole("link", { name: "Entrar" })[0]).toHaveAttribute("href", "/?entrar=1");
    });

    it("abre o fluxo de login quando a URL pede para entrar", async () => {
      oidcEnv();
      window.history.replaceState({}, "", "/?entrar=1");
      const { default: App } = await import("./App");
      render(<App />);
      expect(screen.queryByText(/ERP Especializado em Bananicultura/)).not.toBeInTheDocument();
      window.history.replaceState({}, "", "/");
    });
  });
});
