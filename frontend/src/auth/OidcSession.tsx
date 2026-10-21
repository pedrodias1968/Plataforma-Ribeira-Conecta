import { useEffect, useRef, useState } from "react";
import { exchangeAuthorizationCode, oidcAuthorizationUrl, type OidcBrowserConfiguration } from "./oidc";

export function OidcSession({ config, children, autoStart = false }: { config: OidcBrowserConfiguration; children: (token: string) => React.ReactNode; autoStart?: boolean }) {
  const started = useRef(false);
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [failure, setFailure] = useState<string | null>(null);

  useEffect(() => {
    const query = new URLSearchParams(window.location.search);
    const code = query.get("code");
    if (!code) {
      if (autoStart && !query.has("error") && !started.current) {
        started.current = true;
        void oidcAuthorizationUrl(config).then((url) => window.location.assign(url)).catch(() => setFailure("Não foi possível iniciar a autenticação OIDC."));
      }
      return;
    }
    void exchangeAuthorizationCode(config, code, query.get("state"))
      .then((token) => {
        window.history.replaceState({}, "", config.redirectUri);
        setAccessToken(token);
      })
      .catch(() => setFailure("Não foi possível concluir a autenticação OIDC."));
  }, [config, autoStart]);

  if (failure) return <main className="state">{failure}</main>;
  if (accessToken) return <>{children(accessToken)}</>;
  return <main className="state"><button onClick={() => void oidcAuthorizationUrl(config).then((url) => window.location.assign(url))}>Entrar</button></main>;
}
