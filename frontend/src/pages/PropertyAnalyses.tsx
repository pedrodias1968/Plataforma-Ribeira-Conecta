import { useEffect, useRef, useState, type KeyboardEvent } from "react";
import { StatusTag } from "./StatusTag";
import "./PropertyAnalyses.css";

/**
 * Análises da propriedade que farão parte da plataforma. Nada desta seção está
 * disponível ainda: tudo aparece como "Em planejamento".
 */

const FLOW: Array<[string, string]> = [
  ["Informe a área", "Desenhe no mapa, envie um arquivo KML, KMZ ou SHP, ou consulte pelo CAR, SIGEF ou SNCI."],
  ["Escolha as análises", "Fundiária, ambiental, uso da terra, solo e clima, ESG, carbono ou crédito rural."],
  ["Cruzamento das fontes", "Bases oficiais e satélite cruzados sobre o mesmo limite, com a origem de cada dado registrada."],
  ["Diagnóstico", "O que foi encontrado, o que não pôde ser verificado e de onde veio cada informação."],
  ["Decisão e documento", "Um relatório para levar ao banco, à cooperativa, ao comprador ou ao consultor."],
];

const GROUPS = [
  { id: "fundiario", label: "Fundiário", title: "Situação fundiária", items: ["Consulta ao CAR, SIGEF e SNCI", "Delimitação e situação cadastral da área"] },
  {
    id: "ambiental",
    label: "Ambiental",
    title: "Sobreposições ambientais",
    items: ["Unidades de conservação, terras indígenas e territórios quilombolas", "Áreas embargadas pelo IBAMA e pelo ICMBio"],
  },
  { id: "uso", label: "Uso da terra", title: "Desmatamento e uso da terra", items: ["Desmatamento pelo PRODES", "Histórico de uso e cobertura da terra"] },
  { id: "solo", label: "Solo e clima", title: "Solo e clima", items: ["Textura, argila e carbono orgânico do solo", "Histórico de chuva e temperatura"] },
  { id: "esg", label: "ESG", title: "ESG e risco socioambiental", items: ["Indicadores socioambientais", "Checagens de conformidade socioambiental"] },
  { id: "carbono", label: "Carbono", title: "Carbono", items: ["Camadas para carbono e monitoramento do território"] },
  {
    id: "credito",
    label: "Crédito rural",
    title: "Crédito rural",
    items: ["Análise orientada ao MCR 2.9, com diagnóstico de risco", "Relatório para o banco ou a cooperativa"],
  },
  { id: "entrega", label: "Entrega", title: "Onde o resultado chega", items: ["Relatório em PDF", "Plataforma web e aplicativo no celular", "Atendimento pelo WhatsApp"] },
] as const;

/** Pilha de camadas do território: a camada do grupo ativo desliza para fora da pilha e acende. */
function LayerStack({ active }: { active: number }) {
  const count = GROUPS.length;
  // Desenha de baixo para cima; a camada ativa por último, para ficar na frente.
  const order = GROUPS.map((_, index) => index)
    .reverse()
    .filter((index) => index !== active)
    .concat(active);
  return (
    <svg className="layer-stack" viewBox="0 0 400 380" role="img" aria-label="Camadas de análise sobre o mesmo território">
      <defs>
        <linearGradient id="plate-on" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#f6dc86" />
          <stop offset="1" stopColor="#c9a62f" />
        </linearGradient>
        <linearGradient id="plate-off" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#2a4131" />
          <stop offset="1" stopColor="#152219" />
        </linearGradient>
      </defs>
      {order.map((index) => {
        const group = GROUPS[index];
        const y = 60 + index * 30;
        const isOn = index === active;
        return (
          <g
            key={group.id}
            className={`plate${isOn ? " is-on" : ""}`}
            style={{ transform: isOn ? `translate(34px, ${y - 22}px)` : `translate(0px, ${y}px)` }}
          >
            <path d="M180 0 L330 50 L180 100 L30 50 Z" fill={isOn ? "url(#plate-on)" : "url(#plate-off)"} stroke={isOn ? "#fff2c4" : "rgba(236,232,218,0.22)"} strokeWidth="1.2" />
            {isOn && (
              <g className="plate-detail" aria-hidden="true">
                <path d="M110 48 Q160 30 210 44 T300 52" fill="none" stroke="#0b110d" strokeOpacity="0.45" strokeWidth="2" />
                <path d="M140 62 L200 40 L250 58 L190 80 Z" fill="none" stroke="#0b110d" strokeOpacity="0.55" strokeWidth="2" strokeDasharray="6 5" />
              </g>
            )}
            <text x="345" y="56" className={`plate-label${isOn ? " is-on" : ""}`}>
              {String(index + 1).padStart(2, "0")}
            </text>
          </g>
        );
      })}
      <text x="20" y="372" className="plate-caption">
        {count} camadas sobre o mesmo limite
      </text>
    </svg>
  );
}

export function PropertyAnalyses() {
  const [active, setActive] = useState(0);
  const [visible, setVisible] = useState(false);
  const flowRef = useRef<HTMLOListElement>(null);
  const tabRefs = useRef<Array<HTMLButtonElement | null>>([]);

  useEffect(() => {
    const el = flowRef.current;
    if (!el) return;
    if (typeof IntersectionObserver === "undefined") {
      setVisible(true);
      return;
    }
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setVisible(true);
          observer.disconnect();
        }
      },
      { threshold: 0.35 },
    );
    observer.observe(el);
    return () => observer.disconnect();
  }, []);

  const onTabKey = (event: KeyboardEvent<HTMLButtonElement>, index: number) => {
    const delta = event.key === "ArrowRight" || event.key === "ArrowDown" ? 1 : event.key === "ArrowLeft" || event.key === "ArrowUp" ? -1 : 0;
    if (!delta) return;
    event.preventDefault();
    const next = (index + delta + GROUPS.length) % GROUPS.length;
    setActive(next);
    tabRefs.current[next]?.focus();
  };

  const group = GROUPS[active];

  return (
    <section id="analises" className="band band-alt analyses">
      <div className="wrap">
        <p className="kicker">Análises da propriedade</p>
        <h2>Da área no mapa a um relatório pronto para decidir.</h2>
        <p className="muted lead-narrow">
          Funcionalidades que vão fazer parte da plataforma. Ainda não estão disponíveis: todas aparecem como “Em planejamento”.
        </p>

        <ol ref={flowRef} className={`flow${visible ? " is-visible" : ""}`}>
          {FLOW.map(([title, text], index) => (
            <li key={title} className="flow-step" style={{ transitionDelay: `${index * 110}ms` }}>
              <span className="flow-dot mono">{String(index + 1).padStart(2, "0")}</span>
              <h3>{title}</h3>
              <p>{text}</p>
            </li>
          ))}
        </ol>

        <div className="analyses-explorer">
          <div className="analyses-visual">
            <LayerStack active={active} />
          </div>
          <div>
            <div className="analyses-tabs" role="tablist" aria-label="Tipos de análise">
              {GROUPS.map((item, index) => (
                <button
                  key={item.id}
                  ref={(el) => {
                    tabRefs.current[index] = el;
                  }}
                  type="button"
                  role="tab"
                  id={`analise-tab-${item.id}`}
                  aria-selected={index === active}
                  aria-controls="analise-painel"
                  tabIndex={index === active ? 0 : -1}
                  className={`analyses-tab${index === active ? " is-active" : ""}`}
                  onClick={() => setActive(index)}
                  onPointerEnter={(event) => event.pointerType === "mouse" && setActive(index)}
                  onKeyDown={(event) => onTabKey(event, index)}
                >
                  {item.label}
                </button>
              ))}
            </div>
            <div id="analise-painel" role="tabpanel" aria-labelledby={`analise-tab-${group.id}`} className="analyses-panel" key={group.id}>
              <div className="analyses-panel-head">
                <h3>{group.title}</h3>
                <StatusTag status="planned" />
              </div>
              <ul>
                {group.items.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
