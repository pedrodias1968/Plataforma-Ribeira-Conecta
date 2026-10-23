import { useEffect, useRef, useState, type KeyboardEvent as ReactKeyboardEvent, type ReactNode } from "react";
import { BananaPlant, SceneDefs, SceneLabel } from "./EcosystemArt";
import { BUSHES, GROUND, MOTES, PLANTS, RIDGES, RIVER, TOWER_BRACES } from "./ecosystemSceneData";
import { StatusTag, type Status } from "./StatusTag";
import "./EcosystemJourney.css";

/**
 * Cena rolável do ecossistema: um vale com bananais, rio, torre de rede e
 * câmera. A câmera da cena acompanha o capítulo que o visitante está lendo,
 * reage ao mouse (profundidade) e ao scroll. É uma ilustração: nada aqui
 * representa uma propriedade, medição ou instalação real.
 */

export type ChapterId = "vale" | "conectividade" | "seguranca" | "gestao" | "territorio";

type Chapter = {
  id: ChapterId;
  label: string;
  /** Hotspot da cena que este capítulo destaca. */
  spot: Exclude<ChapterId, "vale"> | null;
  focus: { x: number; y: number; scale: number };
  kicker?: string;
  title?: string;
  text?: string;
  note?: string;
  status?: Status;
  link?: { href: string; label: string };
};

const CHAPTERS: Chapter[] = [
  { id: "vale", label: "O vale", spot: null, focus: { x: 1000, y: 450, scale: 0.82 } },
  {
    id: "conectividade",
    label: "Conectividade",
    spot: "conectividade",
    focus: { x: 640, y: 520, scale: 1.6 },
    kicker: "01 · Conectividade rural",
    title: "Rede onde a roça precisa.",
    text: "Infraestrutura digital gerenciada para a propriedade: distribuição da rede interna, Wi-Fi e enlaces entre as áreas de trabalho.",
    note: "Não somos provedor de internet: o produtor mantém o próprio link.",
    status: "planned",
  },
  {
    id: "seguranca",
    label: "Câmeras",
    spot: "seguranca",
    focus: { x: 1190, y: 540, scale: 1.8 },
    kicker: "02 · Câmeras de segurança",
    title: "Olho na propriedade, na mesma rede.",
    text: "Câmeras de segurança (CFTV) instaladas e gerenciadas sobre a rede da propriedade, em vez de um sistema separado.",
    note: "Escopo e condições de oferta ainda em definição.",
    status: "planned",
  },
  {
    id: "gestao",
    label: "Gestão",
    spot: "gestao",
    focus: { x: 1000, y: 610, scale: 1.7 },
    kicker: "03 · Gestão da banana",
    title: "Do cacho ao caixa, por talhão.",
    text: "Colheita, adubação, estoque, custos e vendas registrados por talhão. Dado que ninguém anotou aparece como “sem registro”.",
    status: "building",
    link: { href: "#erp", label: "Ver os módulos" },
  },
  {
    id: "territorio",
    label: "Território",
    spot: "territorio",
    focus: { x: 1000, y: 600, scale: 1.45 },
    kicker: "04 · Inteligência territorial",
    title: "O mapa que junta tudo.",
    text: "Limite da propriedade, vegetação por satélite e rios do Vale do Ribeira, a partir de fontes oficiais abertas.",
    status: "ready",
    link: { href: "#mapa", label: "Abrir o mapa interativo" },
  },
];

function useMediaQuery(query: string, initial = false) {
  const [matches, setMatches] = useState(initial);
  useEffect(() => {
    if (typeof window.matchMedia !== "function") return;
    const media = window.matchMedia(query);
    const update = () => setMatches(media.matches);
    update();
    media.addEventListener("change", update);
    return () => media.removeEventListener("change", update);
  }, [query]);
  return matches;
}

export function EcosystemJourney({ hero }: { hero: ReactNode }) {
  const [active, setActive] = useState<ChapterId>("vale");
  const [hover, setHover] = useState<ChapterId | null>(null);
  const rootRef = useRef<HTMLDivElement>(null);
  const sceneRef = useRef<SVGSVGElement>(null);
  const chapterRefs = useRef<Partial<Record<ChapterId, HTMLElement | null>>>({});
  const narrow = useMediaQuery("(max-width: 960px)");

  // Capítulo ativo = o que cruza o meio da tela.
  useEffect(() => {
    if (typeof IntersectionObserver === "undefined") return;
    const observer = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) setActive(entry.target.getAttribute("data-chapter") as ChapterId);
        }
      },
      { rootMargin: "-45% 0px -45% 0px", threshold: 0 },
    );
    Object.values(chapterRefs.current).forEach((el) => el && observer.observe(el));
    return () => observer.disconnect();
  }, []);

  // Profundidade: mouse e scroll viram variáveis CSS, sem re-render.
  useEffect(() => {
    const root = rootRef.current;
    const scene = sceneRef.current;
    if (!root || !scene || typeof window.matchMedia !== "function") return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

    let frame = 0;
    let px = 0;
    let py = 0;
    const apply = () => {
      frame = 0;
      const rect = root.getBoundingClientRect();
      const span = Math.max(1, rect.height - window.innerHeight);
      const progress = Math.min(1, Math.max(0, -rect.top / span));
      scene.style.setProperty("--px", px.toFixed(3));
      scene.style.setProperty("--py", py.toFixed(3));
      scene.style.setProperty("--sp", progress.toFixed(3));
    };
    const schedule = () => {
      if (!frame) frame = window.requestAnimationFrame(apply);
    };
    const onPointer = (event: PointerEvent) => {
      if (event.pointerType !== "mouse") return;
      px = (event.clientX / window.innerWidth - 0.5) * 2;
      py = (event.clientY / window.innerHeight - 0.5) * 2;
      schedule();
    };
    apply();
    root.addEventListener("pointermove", onPointer, { passive: true });
    window.addEventListener("scroll", schedule, { passive: true });
    return () => {
      root.removeEventListener("pointermove", onPointer);
      window.removeEventListener("scroll", schedule);
      if (frame) window.cancelAnimationFrame(frame);
    };
  }, []);

  const current = CHAPTERS.find((chapter) => chapter.id === active) ?? CHAPTERS[0];
  const lit = hover ?? current.spot;
  const target = narrow ? { x: 800, y: 450 } : { x: active === "vale" ? 1120 : 1040, y: 450 };
  const focus = current.focus;
  const tx = target.x - focus.x * focus.scale;
  const ty = target.y - focus.y * focus.scale;

  const goTo = (id: ChapterId) => {
    chapterRefs.current[id]?.scrollIntoView({ behavior: "smooth", block: "center" });
  };

  const spot = (id: Exclude<ChapterId, "vale">) => {
    const state = lit === null ? "" : lit === id ? " is-on" : " is-dim";
    return `spot${state}`;
  };
  const spotHandlers = (id: Exclude<ChapterId, "vale">) => ({
    onPointerEnter: () => setHover(id),
    onPointerLeave: () => setHover(null),
    onFocus: () => setHover(id),
    onBlur: () => setHover(null),
    onClick: () => goTo(id),
    onKeyDown: (event: ReactKeyboardEvent) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        goTo(id);
      }
    },
  });

  return (
    <div className="journey" ref={rootRef}>
      <div className="journey-stage">
        <svg
          ref={sceneRef}
          className="scene"
          viewBox="0 0 1600 900"
          preserveAspectRatio="xMidYMid slice"
          role="img"
          aria-label="Ilustração do Vale do Ribeira com bananais, rio, torre de rede e câmera de segurança"
        >
          <SceneDefs />

          <g className="world" style={{ transform: `translate(${tx}px, ${ty}px) scale(${focus.scale})` }}>
            <rect x="-900" y="-600" width="3400" height="2400" fill="url(#sky)" />
            <rect x="600" y="-300" width="1400" height="1000" fill="url(#sun)" />
            <circle className="sun-core" cx="1250" cy="262" r="70" fill="url(#sun-core)" />
            <g className="rays" aria-hidden="true">
              <path d="M1250 262 L640 900 L860 900Z" fill="url(#ray)" />
              <path d="M1250 262 L1060 900 L1220 900Z" fill="url(#ray)" />
            </g>

            <g className="layer layer-far">
              <path d={RIDGES.far[0].d} fill={RIDGES.far[0].fill} />
              <ellipse className="mist" cx="420" cy="318" rx="560" ry="38" fill="url(#mist)" />
              <path d={RIDGES.far[1].d} fill={RIDGES.far[1].fill} />
              <ellipse className="mist mist-slow" cx="1160" cy="372" rx="640" ry="42" fill="url(#mist)" />
            </g>
            <g className="layer layer-mid">
              <path d={RIDGES.mid[0].d} fill={RIDGES.mid[0].fill} />
              <ellipse className="mist" cx="760" cy="468" rx="760" ry="46" fill="url(#mist)" />
              <path d={RIDGES.mid[1].d} fill={RIDGES.mid[1].fill} />
            </g>

            <g className="layer layer-near">
              <path d={GROUND} fill="url(#ground)" />
              <g fill="none" stroke="#000" strokeOpacity="0.18" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
                <path d="M806 584 Q1180 548 1566 572" />
                <path d="M800 616 Q1180 582 1574 604" />
                <path d="M792 648 Q1150 616 1580 636" />
              </g>
              {BUSHES.map((bush) => (
                <g key={`${bush.x}-${bush.y}`} aria-hidden="true">
                  <ellipse cx={bush.x} cy={bush.y} rx={bush.r * 1.5} ry={bush.r} fill="#17301d" />
                  <ellipse cx={bush.x - bush.r * 0.4} cy={bush.y - bush.r * 0.35} rx={bush.r * 0.8} ry={bush.r * 0.55} fill="#21402a" opacity="0.7" />
                </g>
              ))}

              <path d={RIVER} fill="none" stroke="#14231a" strokeOpacity="0.85" strokeWidth="74" strokeLinecap="round" />
              <path d={RIVER} fill="none" stroke="#7fb3e0" strokeOpacity="0.35" strokeWidth="56" strokeLinecap="round" />
              <path d={RIVER} fill="none" stroke="url(#water)" strokeWidth="50" strokeLinecap="round" />
              <path className="river-flow" d={RIVER} fill="none" stroke="#c9e3ff" strokeOpacity="0.35" strokeWidth="2.2" strokeLinecap="round" />
              <path className="river-glint" d={RIVER} fill="none" stroke="#f6dc86" strokeOpacity="0.45" strokeWidth="3" strokeLinecap="round" />
              <path className={`river-hi${lit === "territorio" ? " is-on" : ""}`} d={RIVER} fill="none" stroke="url(#scene-hatch)" strokeWidth="130" strokeLinecap="round" />

              {PLANTS.map((plant) => (
                <BananaPlant key={`${plant.x.toFixed(1)}-${plant.y.toFixed(1)}`} plant={plant} />
              ))}

              {/* Território: talhões sobre o bananal. Cores ilustrativas. */}
              <g className={`parcels${lit === "territorio" ? " is-on" : ""}`} aria-hidden="true">
                {[
                  { d: "M780 553 Q852 542 925 540 Q938 588 950 636 Q876 643 800 650 Q790 600 780 553Z", fill: "#5fbf6f" },
                  { d: "M925 540 Q1002 534 1080 536 Q1096 582 1110 628 Q1030 630 950 636 Q938 588 925 540Z", fill: "#e9c54a" },
                  { d: "M1080 536 Q1160 540 1240 550 Q1256 598 1268 646 Q1189 637 1110 628 Q1096 582 1080 536Z", fill: "#a7c957" },
                ].map((shape, index) => (
                  <path key={shape.d} d={shape.d} fill={shape.fill} fillOpacity="0.42" stroke="#0b110d" strokeOpacity="0.6" strokeWidth="1.5" strokeLinejoin="round" style={{ transitionDelay: `${index * 80}ms` }} />
                ))}
                <path d="M768 548 Q1010 526 1250 538 Q1268 596 1282 656 Q1036 650 790 664 Q776 606 768 548Z" fill="none" stroke="#e9c54a" strokeWidth="3" strokeDasharray="12 8" strokeLinejoin="round" />
                <SceneLabel x={900} y={516} text="NDVI · exemplo fictício" />
              </g>

              {/* Gestão: etiquetas de registro ao lado das plantas. */}
              <g className={`tags${lit === "gestao" ? " is-on" : ""}`} aria-hidden="true">
                {[
                  { x: 870, y: 470, label: "Colheita", to: [930, 566] },
                  { x: 1060, y: 446, label: "Adubação", to: [1060, 590] },
                  { x: 1240, y: 478, label: "Custo por kg", to: [1200, 600] },
                ].map((tag, index) => (
                  <g key={tag.label} style={{ transitionDelay: `${index * 90}ms` }}>
                    <path d={`M${tag.x} ${tag.y + 14} Q${tag.x} ${(tag.y + tag.to[1]) / 2} ${tag.to[0]} ${tag.to[1]}`} fill="none" stroke="#e9c54a" strokeOpacity="0.7" strokeWidth="1.6" strokeDasharray="3 5" strokeLinecap="round" />
                    <circle cx={tag.to[0]} cy={tag.to[1]} r="4" fill="#e9c54a" />
                    <SceneLabel x={tag.x} y={tag.y} text={tag.label} />
                  </g>
                ))}
              </g>

              {MOTES.map((mote) => (
                <circle
                  key={`${mote.x.toFixed(0)}-${mote.y.toFixed(0)}`}
                  className="mote"
                  cx={mote.x}
                  cy={mote.y}
                  r={mote.r}
                  style={{ animationDelay: `${mote.delay.toFixed(2)}s`, animationDuration: `${mote.dur.toFixed(2)}s` }}
                />
              ))}
            </g>

            {/* Conectividade: torre treliçada, enlace e Wi-Fi no galpão. */}
            <g className={spot("conectividade")} role="button" tabIndex={0} aria-label="Conectividade rural, ver capítulo" {...spotHandlers("conectividade")}>
              <rect x="496" y="390" width="130" height="250" fill="transparent" />
              <g className="rings" aria-hidden="true">
                <circle className="ring" cx="560" cy="430" r="150" />
                <circle className="ring" cx="560" cy="430" r="150" style={{ animationDelay: "1.1s" }} />
                <circle className="ring" cx="560" cy="430" r="150" style={{ animationDelay: "2.2s" }} />
              </g>
              <ellipse cx="560" cy="628" rx="34" ry="5" fill="#000" opacity="0.35" />
              <path d="M560 470 L498 630 M560 470 L624 630 M560 540 L484 632 M560 540 L638 632" fill="none" stroke="#dfe3d6" strokeOpacity="0.16" strokeWidth="1" />
              <path d={TOWER_BRACES} fill="none" stroke="#b9bfae" strokeOpacity="0.85" strokeWidth="1.3" />
              <path d="M540 624 L555 450 M580 624 L565 450" fill="none" stroke="url(#metal)" strokeWidth="3.4" strokeLinecap="round" />
              <path d="M560 450 L560 404" stroke="#d8dccb" strokeWidth="2" strokeLinecap="round" />
              <rect x="546" y="446" width="28" height="4" rx="2" fill="#d8dccb" />
              <rect x="543" y="420" width="6" height="22" rx="2" fill="url(#cam-g)" />
              <rect x="571" y="420" width="6" height="22" rx="2" fill="url(#cam-g)" />
              <ellipse cx="560" cy="432" rx="6" ry="7" fill="url(#cam-g)" />
              <circle className="beacon" cx="560" cy="402" r="16" fill="url(#glow)" />
              <circle cx="560" cy="402" r="3.4" fill="#f6dc86" />
              <path className="link" d="M566 426 C622 446 700 500 742 548" fill="none" stroke="#e9c54a" strokeWidth="2.4" strokeDasharray="6 10" strokeLinecap="round" />
              <g className="wifi" aria-hidden="true">
                <path d="M729 540 C737 532 747 532 755 540" fill="none" stroke="#e9c54a" strokeWidth="2.6" strokeLinecap="round" />
                <path d="M720 530 C733 516 751 516 764 530" fill="none" stroke="#e9c54a" strokeWidth="2.6" strokeLinecap="round" opacity="0.7" />
                <path d="M711 520 C729 500 755 500 773 520" fill="none" stroke="#e9c54a" strokeWidth="2.6" strokeLinecap="round" opacity="0.4" />
              </g>
              <SceneLabel x={560} y={664} text="Conectividade" />
            </g>

            {/* Galpão de beneficiamento (ponto de rede), com luz acesa. */}
            <g aria-hidden="true">
              <ellipse cx="742" cy="630" rx="70" ry="7" fill="#000" opacity="0.35" />
              <ellipse className="lamp-spill" cx="742" cy="634" rx="46" ry="7" fill="#e9c54a" opacity="0.16" />
              <path d="M698 590 L786 590 L786 628 L698 628Z" fill="url(#wall-g)" />
              <path d="M698 590 L786 590" stroke="#000" strokeOpacity="0.35" strokeWidth="3" />
              <path d="M680 595 L742 552 L804 595 L796 597 L742 560 L688 597Z" fill="url(#roof-g)" />
              <path d="M690 593 L742 557 L794 593" fill="none" stroke="#c9cfc3" strokeOpacity="0.35" strokeWidth="1" />
              <rect x="726" y="600" width="32" height="28" rx="2" fill="url(#bay-g)" />
              <path d="M726 600 L758 600 M742 600 L742 628" stroke="#2a362c" strokeWidth="1.5" />
              <rect x="704" y="600" width="13" height="10" rx="1.5" fill="#f6dc86" opacity="0.6" />
              <rect x="767" y="600" width="13" height="10" rx="1.5" fill="#f6dc86" opacity="0.6" />
              <circle cx="742" cy="604" r="20" fill="url(#glow)" opacity="0.35" />
            </g>

            {/* Segurança: poste, câmera e campo de visão. */}
            <g className={spot("seguranca")} role="button" tabIndex={0} aria-label="Câmeras de segurança, ver capítulo" {...spotHandlers("seguranca")}>
              <rect x="1160" y="440" width="110" height="200" fill="transparent" />
              <ellipse cx="1231" cy="633" rx="12" ry="3" fill="#000" opacity="0.4" />
              <path d="M1227 633 L1228.5 470 L1233.5 470 L1235 633Z" fill="url(#pole-g)" />
              <rect x="1224" y="560" width="14" height="17" rx="3" fill="#36453b" stroke="#ece8da" strokeOpacity="0.2" />
              <path d="M1236 570 C1240 580 1238 600 1236 630" fill="none" stroke="#0b110d" strokeWidth="1.4" />
              <g className="cam">
                <polygon className="fov" points="1196,478 900,560 920,660" fill="url(#fov-g)" stroke="#e9c54a" strokeOpacity="0.45" strokeDasharray="6 8" strokeLinejoin="round" />
                <path d="M1231 470 L1231 486 L1224 486" fill="none" stroke="#a7ae9f" strokeWidth="3" strokeLinecap="round" />
                <path d="M1201 466 L1238 466 Q1245 466 1245 473 L1245 480 Q1245 487 1238 487 L1207 487 Q1201 487 1201 481 Z" fill="url(#cam-g)" />
                <path d="M1195 462 L1243 462 Q1248 462 1248 466 L1195 466 Q1193 464 1195 462Z" fill="#cdd1c6" />
                <circle cx="1201" cy="476.5" r="8.5" fill="#1b2420" stroke="#6f776c" strokeWidth="1.2" />
                <circle cx="1201" cy="476.5" r="5.2" fill="url(#lens-g)" />
                <circle cx="1199.3" cy="474.6" r="1.6" fill="#ffffff" opacity="0.75" />
                <circle className="lens-glow" cx="1201" cy="476.5" r="14" fill="url(#glow)" />
                <circle className="rec" cx="1239" cy="471" r="1.9" fill="#e9c54a" />
              </g>
              <SceneLabel x={1231} y={666} text="Câmeras" />
            </g>

            {/* Gestão e território: rótulos ancorados no bananal. */}
            <g className={spot("gestao")} role="button" tabIndex={0} aria-label="Gestão da banana, ver capítulo" {...spotHandlers("gestao")}>
              <rect x="800" y="548" width="740" height="120" fill="transparent" />
              <SceneLabel x={1000} y={702} text="Gestão da banana" />
            </g>
            <g className={spot("territorio")} role="button" tabIndex={0} aria-label="Inteligência territorial, ver capítulo" {...spotHandlers("territorio")}>
              <circle cx="1470" cy="360" r="28" fill="transparent" />
              <circle cx="1470" cy="360" r="18" fill="url(#glow)" opacity="0.6" />
              <circle cx="1470" cy="360" r="6" fill="#f6dc86" />
              <circle className="ping" cx="1470" cy="360" r="8" fill="none" stroke="#e9c54a" strokeWidth="2" />
              <SceneLabel x={1470} y={398} text="Território" />
            </g>

            <g className="layer layer-front" aria-hidden="true">
              <g className="front-plant" transform="translate(1590 978) scale(2.2)">
                <use href="#plant-a" />
              </g>
              <g className="front-plant" transform="translate(1470 1018) scale(-1.7 1.7)">
                <use href="#plant-b" />
              </g>
            </g>
          </g>

          <rect className="vignette" x="0" y="0" width="1600" height="900" fill="url(#vignette)" pointerEvents="none" />
        </svg>

        <p className="scene-flag">Ilustração do Vale do Ribeira · não representa uma propriedade real</p>

        <nav className="rail" aria-label="Capítulos do ecossistema">
          {CHAPTERS.map((chapter) => (
            <button
              key={chapter.id}
              type="button"
              className={`rail-item${active === chapter.id ? " is-active" : ""}`}
              aria-current={active === chapter.id ? "step" : undefined}
              onClick={() => goTo(chapter.id)}
              onPointerEnter={() => chapter.spot && setHover(chapter.id)}
              onPointerLeave={() => setHover(null)}
            >
              <span className="rail-dot" aria-hidden="true" />
              {chapter.label}
            </button>
          ))}
        </nav>
      </div>

      <div className="journey-chapters">
        {CHAPTERS.map((chapter) => (
          <section
            key={chapter.id}
            id={chapter.id === "vale" ? "inicio" : chapter.id}
            className={`chapter${active === chapter.id ? " is-active" : ""}`}
            data-chapter={chapter.id}
            ref={(el) => {
              chapterRefs.current[chapter.id] = el;
            }}
          >
            <div className="chapter-card">
              {chapter.id === "vale" ? (
                hero
              ) : (
                <>
                  <p className="kicker">{chapter.kicker}</p>
                  <h2>{chapter.title}</h2>
                  <p className="chapter-text">{chapter.text}</p>
                  {chapter.status && <StatusTag status={chapter.status} />}
                  {chapter.note && <p className="note">{chapter.note}</p>}
                  {chapter.link && (
                    <a className="text-link" href={chapter.link.href}>
                      {chapter.link.label}
                    </a>
                  )}
                </>
              )}
            </div>
          </section>
        ))}
      </div>
    </div>
  );
}
