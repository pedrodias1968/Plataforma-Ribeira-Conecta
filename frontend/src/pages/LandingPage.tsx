import { useEffect, useState, type FormEvent } from "react";
import "@fontsource-variable/bricolage-grotesque";
import "@fontsource/ibm-plex-mono/400.css";
import "@fontsource/ibm-plex-mono/500.css";
import "./LandingPage.css";
import { EcosystemJourney } from "./EcosystemJourney";
import { PropertyAnalyses } from "./PropertyAnalyses";
import { StatusTag, type Status } from "./StatusTag";
import { WebGisMock } from "./WebGisMock";

const CONTACT = "contato@ribeiraconecta.com.br";

const SOCIAL = [
  {
    name: "LinkedIn",
    href: "https://www.linkedin.com/company/ribeira-conecta",
    icon: "M4.98 3.5a2.5 2.5 0 1 1 0 5 2.5 2.5 0 0 1 0-5ZM3 9.5h4V21H3V9.5Zm6.5 0h3.8v1.6h.06c.53-1 1.82-2.06 3.75-2.06 4 0 4.74 2.64 4.74 6.07V21h-4v-5.2c0-1.24-.02-2.84-1.73-2.84-1.73 0-2 1.35-2 2.75V21h-4V9.5Z",
  },
  {
    name: "Instagram",
    href: "https://www.instagram.com/ribeiraconecta/",
    icon: "M12 7.4a4.6 4.6 0 1 0 0 9.2 4.6 4.6 0 0 0 0-9.2Zm0 7.6a3 3 0 1 1 0-6 3 3 0 0 1 0 6Zm4.8-8.9a1.08 1.08 0 1 1 0 2.16 1.08 1.08 0 0 1 0-2.16ZM12 3.5c-2.3 0-2.6 0-3.5.05-3.1.14-4.8 1.86-4.95 4.95C3.5 9.4 3.5 9.7 3.5 12s0 2.6.05 3.5c.14 3.1 1.86 4.8 4.95 4.95.9.04 1.2.05 3.5.05s2.6 0 3.5-.05c3.1-.14 4.8-1.86 4.95-4.95.04-.9.05-1.2.05-3.5s0-2.6-.05-3.5c-.14-3.1-1.86-4.8-4.95-4.95-.9-.04-1.2-.05-3.5-.05Zm0 1.55c2.27 0 2.54 0 3.43.05 2.3.1 3.37 1.2 3.47 3.47.04.9.05 1.16.05 3.43s0 2.54-.05 3.43c-.1 2.26-1.17 3.37-3.47 3.47-.9.04-1.16.05-3.43.05s-2.54 0-3.43-.05c-2.3-.1-3.37-1.21-3.47-3.47C5.06 14.54 5.05 14.27 5.05 12s0-2.54.05-3.43c.1-2.27 1.18-3.37 3.47-3.47.89-.04 1.16-.05 3.43-.05Z",
  },
] as const;

function SocialLinks({ className }: { className?: string }) {
  return (
    <ul className={`social${className ? ` ${className}` : ""}`} aria-label="Redes sociais">
      {SOCIAL.map((item) => (
        <li key={item.name}>
          <a href={item.href} target="_blank" rel="noopener noreferrer" aria-label={`Ribeira Conecta no ${item.name} (abre em nova aba)`}>
            <svg viewBox="0 0 24 24" aria-hidden="true"><path d={item.icon} fill="currentColor" /></svg>
            <span>{item.name}</span>
          </a>
        </li>
      ))}
    </ul>
  );
}

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

type BananaItem = { title: string; text: string };

const BANANA_GROUPS: Array<{ status: Status; title: string; intro: string; items: BananaItem[] }> = [
  {
    status: "ready",
    title: "Já funciona no mapa",
    intro: "O bananal visto de cima, talhão por talhão.",
    items: [
      { title: "Vigor do bananal por satélite", text: "Índice de vegetação (NDVI) por talhão, com máscara de nuvens e comparação entre datas." },
      { title: "Exposição a cheias", text: "Cruzamento da propriedade com a cheia de setembro de 2026 no Vale do Ribeira, com a origem de cada dado." },
    ],
  },
  {
    status: "building",
    title: "Em desenvolvimento",
    intro: "A rotina do bananal, do cacho colhido ao dinheiro recebido.",
    items: [
      { title: "Colheita por talhão", text: "Cachos, caixas, peso e descarte de cada colheita." },
      { title: "Adubação e insumos", text: "O que foi aplicado, em qual talhão e quando." },
      { title: "Estoque de insumos", text: "Entradas, saídas e saldo por produto e unidade." },
      { title: "Custos por talhão e por kg", text: "Custo registrado de cada talhão; o custo por kg só aparece com custo e peso completos." },
      { title: "Vendas e recebimentos", text: "Comprador, valor a receber e prazo de cada venda." },
      { title: "Relatório para o contador", text: "Vendas e custos do período em planilha." },
      { title: "Correção de registros", text: "Nada é apagado: cada correção fica no histórico." },
    ],
  },
  {
    status: "planned",
    title: "Próximas etapas para a banana",
    intro: "Do solo à decisão de manejo, com validação agronômica.",
    items: [
      { title: "Análise de solo por talhão", text: "Amostras georreferenciadas e laudos de laboratório: pH, matéria orgânica, fósforo, potássio, CTC e saturação por bases." },
      { title: "Amostragem inteligente", text: "Zonas de manejo a partir do relevo e do histórico do satélite, para saber onde coletar cada amostra." },
      { title: "Calagem e adubação para a banana", text: "Recomendações por talhão a partir dos laudos, para a banana no Vale do Ribeira, validadas por agrônomo." },
      { title: "Aptidão da área para banana", text: "Relevo, declividade, drenagem, chuva, temperatura, água e histórico de cheias, com resultado explicado." },
      { title: "Inspeção do bananal", text: "Registro de vistorias em campo. Diagnóstico de doença só com validação de especialista." },
    ],
  },
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
    items: [
      "Conectividade rural: rede interna, Wi-Fi e enlaces",
      "Câmeras de segurança (CFTV) sobre a mesma rede",
      "Análises fundiárias, ambientais e de crédito rural",
      "Solo, amostragem e aptidão para banana",
    ],
  },
];

const NAV = [
  ["inicio", "Ecossistema"],
  ["mapa", "Mapa"],
  ["analises", "Análises"],
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
                <a href="#conectividade" className="btn btn-glass btn-lg">Ver o ecossistema</a>
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

        <PropertyAnalyses />

        <section id="publicos" className="band">
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

        <section id="erp" className="band band-alt">
          <div className="wrap split">
            <div className="split-head">
              <p className="kicker">Gestão da banana</p>
              <h2>ERP Especializado em Bananicultura</h2>
              <p className="muted">
                Desenhado a partir de entrevistas com produtores do Vale do Ribeira. Tudo é registrado por talhão,
                no mesmo mapa da propriedade: um módulo básico para todo produtor e módulos adicionais conforme a
                realidade de cada sítio.
              </p>
              <p className="note">Dado que o produtor não anotou aparece como “sem registro”: o sistema não inventa valores. Ainda não está disponível para contratação.</p>
            </div>
            <div className="banana-groups">
              {BANANA_GROUPS.map((group) => (
                <div key={group.title} className={`banana-group banana-${group.status}`}>
                  <div className="banana-group-head">
                    <div>
                      <h3>{group.title}</h3>
                      <p>{group.intro}</p>
                    </div>
                    <StatusTag status={group.status} />
                  </div>
                  <ul className="banana-list">
                    {group.items.map((item) => (
                      <li key={item.title}>
                        <h4>{item.title}</h4>
                        <p>{item.text}</p>
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section id="estagio" className="band">
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

        <section id="sobre" className="band band-alt">
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

        <section id="contato" className="band">
          <div className="wrap split">
            <div className="split-head">
              <p className="kicker">Contato</p>
              <h2>Converse com nossa equipe.</h2>
              <p className="muted">Demonstração, parceria ou dúvida: escolha o seu perfil e escreva.</p>
              <a className="text-link mono" href={`mailto:${CONTACT}`}>{CONTACT}</a>
              <SocialLinks className="social-contact" />
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
          <SocialLinks />
          <span className="muted mono">© 2026 Ribeira Conecta</span>
        </div>
      </footer>
    </div>
  );
}
