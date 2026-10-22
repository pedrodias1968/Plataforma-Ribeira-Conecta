import { useEffect, useState, type FormEvent } from "react";
import "@fontsource-variable/bricolage-grotesque";
import "@fontsource/ibm-plex-mono/400.css";
import "@fontsource/ibm-plex-mono/500.css";
import "./LandingPage.css";
import { EcosystemJourney } from "./EcosystemJourney";
import { StatusTag, type Status } from "./StatusTag";
import { WebGisMock } from "./WebGisMock";

const CONTACT = "contato@ribeiraconecta.com.br";

const LAYER_ROWS: Array<{ name: string; text: string; status: Status }> = [
  { name: "Propriedade e talhões", text: "Limite desenhado ou importado (GeoJSON, KML/KMZ), com histórico de cada alteração.", status: "ready" },
  { name: "Vegetação por satélite", text: "NDVI por talhão a partir do Sentinel-2, com máscara de nuvens e comparação entre datas.", status: "ready" },
  { name: "Hidrologia do Vale do Ribeira", text: "Nível de rios e chuva a partir de fontes oficiais (SP Águas e ANA), no contexto da propriedade.", status: "ready" },
  { name: "Gestão da operação", text: "Colheita, adubação, estoque, custos e vendas registrados por talhão, no mesmo mapa.", status: "building" },
];

const AUDIENCES = [
  {
    who: "Produtores",
    text: "Veja a propriedade no mapa, acompanhe a vegetação e os rios, e registre colheita, adubação, custos e vendas por talhão.",
    href: "#erp",
    cta: "Ver a gestão da banana",
  },
  {
    who: "Investidores",
    text: "Produto em construção com base técnica auditável: dados separados por produtor, registros que não são apagados e um quadro público do que já funciona.",
    href: "#estagio",
    cta: "Ver o estágio atual",
  },
  {
    who: "Parceiros",
    text: "Cooperativas, associações, consultorias e empresas de conectividade e insumos: dados territoriais compartilhados com permissão do produtor, a partir de fontes oficiais abertas.",
    href: "#contato",
    cta: "Propor uma parceria",
  },
];

const ERP_MODULES: Array<[string, string]> = [
  ["Colheita por talhão", "Cachos, caixas, peso e descarte."],
  ["Adubação e insumos", "O que foi aplicado, onde e quando."],
  ["Estoque de insumos", "Entradas, saídas e saldo por produto."],
  ["Custos por talhão e por kg", "Custo registrado; sem dado, mostra “sem registro”."],
  ["Vendas e recebimentos", "Comprador, valor a receber e prazo."],
  ["Relatório para o contador", "Vendas e custos do período em planilha."],
];

const STAGES: Array<{ status: Status; title: string; items: string[] }> = [
  {
    status: "ready",
    title: "Funcionando",
    items: ["Cadastro de propriedade e talhões", "Mapa e índice de vegetação por satélite", "Painel de hidrologia"],
  },
  {
    status: "building",
    title: "Em desenvolvimento",
    items: ["Colheita, adubação e estoque", "Custos, vendas e relatório para o contador", "Correção de registros com histórico"],
  },
  {
    status: "planned",
    title: "Em planejamento",
    items: ["Conectividade rural: rede interna, Wi-Fi e enlaces", "Câmeras de segurança (CFTV) sobre a mesma rede"],
  },
];

const NAV = [
  ["inicio", "Ecossistema"],
  ["mapa", "Mapa"],
  ["erp", "Gestão da banana"],
  ["estagio", "Estágio"],
  ["contato", "Contato"],
] as const;

export function LandingPage() {
  const [scrolled, setScrolled] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 8);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  const handleContact = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const field = (key: string) => String(data.get(key) ?? "");
    const body = [`Nome: ${field("name")}`, `E-mail: ${field("email")}`, `Telefone: ${field("phone")}`, "", field("message")].join("\n");
    const subject = `Contato pelo site (${field("profile")})`;
    window.location.href = `mailto:${CONTACT}?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
  };

  return (
    <div className="landing-page">
      <header className={`site-header${scrolled ? " is-scrolled" : ""}`}>
        <div className="site-header-inner">
          <a className="brand" href="/" aria-label="Ribeira Conecta, início">
            <svg viewBox="0 0 24 24" aria-hidden="true" className="brand-mark">
              <path d="M3 17c4-1 6-5 9-5s5 2 9 1" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
              <path d="M3 12c4-1 6-5 9-5s5 2 9 1" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" opacity="0.5" />
            </svg>
            Ribeira Conecta
          </a>
          <nav id="site-nav" className={`site-nav${menuOpen ? " is-open" : ""}`} aria-label="Principal">
            {NAV.map(([id, label]) => (
              <a key={id} href={`#${id}`} onClick={() => setMenuOpen(false)}>
                {label}
              </a>
            ))}
          </nav>
          <div className="site-actions">
            <a href="/?entrar=1" className="btn btn-ghost">Entrar</a>
            <a href={`mailto:${CONTACT}`} className="btn btn-solid">Falar com a equipe</a>
          </div>
          <button type="button" className="menu-btn" aria-label="Menu" aria-expanded={menuOpen} aria-controls="site-nav" onClick={() => setMenuOpen((open) => !open)}>
            <span aria-hidden="true">{menuOpen ? "Fechar" : "Menu"}</span>
          </button>
        </div>
      </header>

      <main>
        <EcosystemJourney
          hero={
            <>
              <p className="kicker">Vale do Ribeira · ecossistema para a propriedade rural</p>
              <h1>Do sinal ao cacho, a propriedade conectada.</h1>
              <p className="lede">
                Rede e câmeras de segurança, gestão da banana e inteligência territorial no mesmo ecossistema.
                Para produtores, investidores e parceiros.
              </p>
              <div className="hero-actions">
                <a href={`mailto:${CONTACT}?subject=Demonstra%C3%A7%C3%A3o`} className="btn btn-solid btn-lg">Agendar demonstração</a>
                <a href="#conectividade" className="btn btn-ghost btn-lg">Ver o ecossistema</a>
              </div>
            </>
          }
        />

        <section id="mapa" className="band">
          <div className="wrap split">
            <div className="split-head">
              <p className="kicker">Inteligência territorial</p>
              <h2>Uma camada de cada vez, sobre o mesmo território.</h2>
              <p className="muted">
                O Vale do Ribeira vive de banana e de rio. A plataforma junta o que hoje está espalhado em
                cadernos, planilhas e portais públicos.
              </p>
            </div>
            <ol className="ledger">
              {LAYER_ROWS.map((row, index) => (
                <li key={row.name} className="ledger-row">
                  <span className="mono index">{String(index + 1).padStart(2, "0")}</span>
                  <div>
                    <h3>{row.name}</h3>
                    <p>{row.text}</p>
                  </div>
                  <StatusTag status={row.status} />
                </li>
              ))}
            </ol>
          </div>
          <div className="wrap demo">
            <WebGisMock />
          </div>
        </section>

        <section id="publicos" className="band band-alt">
          <div className="wrap">
            <p className="kicker">Para quem</p>
            <h2>Uma base de dados, três formas de valor.</h2>
            <div className="columns">
              {AUDIENCES.map((audience, index) => (
                <article key={audience.who} className="column">
                  <span className="mono index">{String(index + 1).padStart(2, "0")}</span>
                  <h3>{audience.who}</h3>
                  <p>{audience.text}</p>
                  <a href={audience.href} className="text-link">{audience.cta}</a>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section id="erp" className="band">
          <div className="wrap split">
            <div className="split-head">
              <p className="kicker">Gestão da banana</p>
              <h2>ERP Especializado em Bananicultura</h2>
              <p className="muted">
                Desenhado a partir de entrevistas com produtores. Dado que o produtor não anotou aparece
                como “sem registro”: o sistema não inventa valores.
              </p>
              <p className="note">Ainda não está disponível para contratação.</p>
            </div>
            <ul className="ledger ledger-plain">
              {ERP_MODULES.map(([title, text]) => (
                <li key={title} className="ledger-row">
                  <div>
                    <h3>{title}</h3>
                    <p>{text}</p>
                  </div>
                  <StatusTag status="building" />
                </li>
              ))}
            </ul>
          </div>
        </section>

        <section id="estagio" className="band band-alt">
          <div className="wrap">
            <p className="kicker">Estágio</p>
            <h2>Em que estágio estamos.</h2>
            <p className="muted lead-narrow">
              Preferimos mostrar o que existe de verdade. Os selos desta página seguem o estado real do desenvolvimento.
            </p>
            <div className="columns">
              {STAGES.map((stage) => (
                <div key={stage.title} className="column">
                  <StatusTag status={stage.status} />
                  <ul className="plain-list">
                    {stage.items.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section id="sobre" className="band">
          <div className="wrap split">
            <div className="split-head">
              <p className="kicker">Sobre</p>
              <h2>Ribeira Conecta</h2>
            </div>
            <div className="prose">
              <p>
                Startup do Vale do Ribeira, região produtora de banana. Reunimos infraestrutura digital para a
                propriedade rural (rede, Wi-Fi e câmeras de segurança) e uma plataforma de gestão e inteligência
                territorial, para transformar informação em decisão de campo.
              </p>
            </div>
          </div>
        </section>

        <section id="contato" className="band band-alt">
          <div className="wrap split">
            <div className="split-head">
              <p className="kicker">Contato</p>
              <h2>Converse com nossa equipe.</h2>
              <p className="muted">Demonstração, parceria ou dúvida: escolha o seu perfil e escreva.</p>
              <a className="text-link mono" href={`mailto:${CONTACT}`}>{CONTACT}</a>
            </div>
            <form className="form" onSubmit={handleContact}>
              <label>
                Nome
                <input type="text" name="name" required autoComplete="name" />
              </label>
              <label>
                E-mail
                <input type="email" name="email" required autoComplete="email" />
              </label>
              <label>
                Eu sou
                <select name="profile" defaultValue="Produtor">
                  <option>Produtor</option>
                  <option>Investidor</option>
                  <option>Parceiro</option>
                  <option>Outro</option>
                </select>
              </label>
              <label>
                Telefone
                <input type="tel" name="phone" autoComplete="tel" />
              </label>
              <label className="form-wide">
                Mensagem
                <textarea name="message" rows={4} required />
              </label>
              <button type="submit" className="btn btn-solid">Enviar mensagem</button>
            </form>
          </div>
        </section>
      </main>

      <footer className="site-footer">
        <div className="wrap footer-inner">
          <span className="brand-plain">Ribeira Conecta</span>
          <span className="muted">Ecossistema digital para a cadeia da banana.</span>
          <span className="muted mono">© 2026 Ribeira Conecta</span>
        </div>
      </footer>
    </div>
  );
}
