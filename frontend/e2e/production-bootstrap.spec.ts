import { expect, test } from "@playwright/test";

const bootstrapFailures = [
  "Configuração necessária: informe VITE_RIBEIRA_PUBLIC_ORIGIN ou VITE_RIBEIRA_API_URL, e VITE_RIBEIRA_TENANT_ID.",
  "Configuração de origem pública necessária.",
  "Configuração OIDC necessária.",
  "Modo de autenticação inválido.",
];

test("production candidate boots the public landing with an OIDC login entry", async ({ page }) => {
  const scriptResponses: string[] = [];
  page.on("response", response => {
    if (/\/assets\/index-.*\.js(?:\?|$)/.test(response.url())) {
      scriptResponses.push(`${response.status()}:${response.headers()["content-type"] ?? ""}`);
    }
  });

  await page.goto("/", { waitUntil: "networkidle" });
  for (const failure of bootstrapFailures) {
    await expect(page.getByText(failure, { exact: true })).toHaveCount(0);
  }
  // Em "/" aparece a landing pública; o login começa pelo link Entrar (/?entrar=1).
  const login = page.getByRole("link", { name: "Entrar" }).first();
  await expect(login).toBeVisible();
  await expect(login).toHaveAttribute("href", "/?entrar=1");
  expect(scriptResponses.some(item => item.startsWith("200:") && /javascript/i.test(item))).toBe(true);
});
