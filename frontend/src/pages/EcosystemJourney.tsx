import { useEffect, useRef, useState, type KeyboardEvent as ReactKeyboardEvent, type ReactNode } from "react";
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

type Plant = { x: number; y: number; s: number; bunch: boolean; delay: number };

function buildPlants(): Plant[] {
  const rows = [
    { y: 572, s: 0.32, x0: 830, x1: 1520, step: 44 },
    { y: 606, s: 0.38, x0: 820, x1: 1520, step: 52 },
    { y: 640, s: 0.45, x0: 810, x1: 1540, step: 60 },
  ];
  const out: Plant[] = [];
  rows.forEach((row, r) => {
    for (let x = row.x0, i = 0; x <= row.x1; x += row.step, i += 1) {
      out.push({
        x,
        y: row.y + Math.sin(x / 150) * 8,
        s: row.s,
        bunch: (i + r) % 3 !== 1,
        delay: ((i * 7 + r * 3) % 10) / 4,
      });
    }
  });
  return out;
}

const PLANTS = buildPlants();

const RIVER = "M-600 720 C-200 690 100 700 300 690 C480 740 560 770 760 726 S1180 640 1650 700 S2000 740 2300 700";

const PARCEL_SHAPES: Array<{ points: string; fill: string }> = [
  { points: "780,552 925,540 950,636 800,650", fill: "#5fbf6f" },
  { points: "925,540 1080,536 1110,628 950,636", fill: "#e9c54a" },
  { points: "1080,536 1240,550 1268,646 1110,628", fill: "#a7c957" },
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

function Banana({ plant }: { plant: Plant }) {
  return (
    <g transform={`translate(${plant.x} ${plant.y}) scale(${plant.s})`}>
      <g className="plant" style={{ animationDelay: `${plant.delay}s` }}>
        <use href="#banana-leaves" />
        {plant.bunch && <use href="#bunch" />}
      </g>
    </g>
  );
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
          <defs>
            <radialGradient id="sun" gradientUnits="userSpaceOnUse" cx="1250" cy="170" r="380">
              <stop offset="0%" stopColor="#e9c54a" stopOpacity="0.26" />
              <stop offset="100%" stopColor="#e9c54a" stopOpacity="0" />
            </radialGradient>
            <linearGradient id="ridge-far" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#1b2d22" />
              <stop offset="100%" stopColor="#0f1a13" />
            </linearGradient>
            <linearGradient id="mist" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#ece8da" stopOpacity="0" />
              <stop offset="50%" stopColor="#ece8da" stopOpacity="0.05" />
              <stop offset="100%" stopColor="#ece8da" stopOpacity="0" />
            </linearGradient>
            <linearGradient id="sky" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#0a100c" />
              <stop offset="100%" stopColor="#14231a" />
            </linearGradient>
            <pattern id="scene-hatch" width="14" height="14" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
              <line x1="0" y1="0" x2="0" y2="14" stroke="rgba(110,168,254,0.5)" strokeWidth="3" />
            </pattern>
            <g id="banana-leaves">
              <path d="M-3 0 C-3 -40 -2 -70 0 -100 L5 -100 C4 -70 5 -40 4 0 Z" fill="#2a4a33" />
              <path d="M2 -100 C-30 -122 -72 -114 -98 -86 C-62 -102 -30 -99 2 -100Z" fill="#2e7d4f" />
              <path d="M3 -100 C36 -122 78 -114 104 -86 C68 -102 36 -99 3 -100Z" fill="#3f9560" />
              <path d="M2 -100 C-12 -136 -32 -152 -58 -160 C-38 -136 -22 -120 2 -100Z" fill="#3f9560" />
              <path d="M3 -100 C18 -136 38 -152 64 -160 C44 -136 28 -120 3 -100Z" fill="#2e7d4f" />
              <path d="M2 -100 C0 -132 4 -152 14 -170 C13 -142 10 -122 3 -100Z" fill="#5fbf6f" />
            </g>
            <g id="bunch">
              <path d="M4 -96 C14 -92 16 -70 10 -62 C4 -66 2 -84 4 -96Z" fill="#e9c54a" />
              <path d="M10 -94 C20 -88 20 -68 14 -60 C10 -66 8 -82 10 -94Z" fill="#c9a62f" />
            </g>
          </defs>

          <g
            className="world"
            style={{ transform: `translate(${tx}px, ${ty}px) scale(${focus.scale})` }}
          >
            <rect x="-900" y="-600" width="3400" height="2400" fill="url(#sky)" />
            <rect x="700" y="-300" width="1200" height="900" fill="url(#sun)" />

            <g className="layer layer-far">
              <path d="M-900 330 L-600 320 C-200 200 300 300 460 190 S760 120 900 220 S1180 160 1300 90 S1500 150 1600 110 L2200 170 L2200 1400 L-900 1400Z" fill="url(#ridge-far)" />
              <path d="M-600 360 C-300 300 0 340 200 290 M900 250 C1100 200 1350 210 1600 160" fill="none" stroke="rgba(236,232,218,0.07)" strokeWidth="2" />
            </g>
            <g className="layer layer-mid">
              <path d="M-900 480 L-600 470 C-300 360 360 440 520 360 S800 300 960 380 S1250 320 1400 270 S1550 320 1600 300 L2200 340 L2200 1400 L-900 1400Z" fill="#14231a" />
              <path d="M-600 450 C-200 380 120 430 300 400 M900 400 C1100 350 1300 360 1600 330" fill="none" stroke="rgba(236,232,218,0.08)" strokeWidth="2" />
              <rect x="-900" y="400" width="3400" height="240" fill="url(#mist)" />
            </g>
            <g className="layer layer-near">
              <path d="M-900 660 L-600 650 C-200 590 220 640 480 610 S800 590 1000 590 S1400 540 1600 580 L2200 600 L2200 1400 L-900 1400Z" fill="#1a2d21" />
              <path className="river" d={RIVER} fill="none" stroke="#1f4f9c" strokeOpacity="0.62" strokeWidth="46" strokeLinecap="round" />
              <path className="river-flow" d={RIVER} fill="none" stroke="#5b9cf0" strokeOpacity="0.55" strokeWidth="4" strokeLinecap="round" />
              <path className={`river-hi${lit === "territorio" ? " is-on" : ""}`} d={RIVER} fill="none" stroke="url(#scene-hatch)" strokeWidth="130" strokeLinecap="round" />

              {PLANTS.map((plant) => (
                <Banana key={`${plant.x}-${plant.y}`} plant={plant} />
              ))}

              {/* Território: talhões sobre o bananal. Cores ilustrativas. */}
              <g className={`parcels${lit === "territorio" ? " is-on" : ""}`} aria-hidden="true">
                {PARCEL_SHAPES.map((shape, index) => (
                  <polygon key={shape.points} points={shape.points} fill={shape.fill} fillOpacity="0.5" stroke="#0b110d" strokeWidth="2" style={{ transitionDelay: `${index * 80}ms` }} />
                ))}
                <polygon points="770,546 1250,538 1280,654 790,664" fill="none" stroke="#e9c54a" strokeWidth="3" strokeDasharray="12 8" strokeLinejoin="round" />
                <text x="790" y="528" className="scene-tag">NDVI · exemplo fictício</text>
              </g>

              {/* Gestão: etiquetas de registro ao lado das plantas. */}
              <g className={`tags${lit === "gestao" ? " is-on" : ""}`} aria-hidden="true">
                {[
                  { x: 840, y: 480, label: "Colheita", to: [930, 570] },
                  { x: 1010, y: 452, label: "Adubação", to: [1040, 600] },
                  { x: 1150, y: 486, label: "Custo por kg", to: [1190, 604] },
                ].map((tag, index) => (
                  <g key={tag.label} style={{ transitionDelay: `${index * 90}ms` }}>
                    <line x1={tag.x + 60} y1={tag.y + 30} x2={tag.to[0]} y2={tag.to[1]} stroke="#e9c54a" strokeOpacity="0.6" strokeWidth="2" strokeDasharray="4 6" />
                    <rect x={tag.x} y={tag.y} width="150" height="34" rx="6" fill="#111a14" stroke="#e9c54a" strokeOpacity="0.7" />
                    <text x={tag.x + 75} y={tag.y + 23} textAnchor="middle" className="scene-tag">{tag.label}</text>
                  </g>
                ))}
              </g>
            </g>

            {/* Conectividade: torre, enlaces e Wi-Fi no galpão. */}
            <g className={spot("conectividade")} role="button" tabIndex={0} aria-label="Conectividade rural, ver capítulo" {...spotHandlers("conectividade")}>
              <rect x="496" y="400" width="130" height="230" fill="transparent" />
              <g transform="translate(196 0)">
              <g className="rings" aria-hidden="true">
                <circle className="ring" cx="364" cy="436" r="150" />
                <circle className="ring" cx="364" cy="436" r="150" style={{ animationDelay: "1.1s" }} />
                <circle className="ring" cx="364" cy="436" r="150" style={{ animationDelay: "2.2s" }} />
              </g>
              <path d="M342 622 L364 442 L386 622 M350 568 L378 568 M355 526 L373 526 M359 486 L369 486 M350 568 L373 526 M378 568 L355 526 M355 526 L369 486 M373 526 L359 486" fill="none" stroke="#ece8da" strokeOpacity="0.8" strokeWidth="3" strokeLinejoin="round" />
              <rect x="355" y="426" width="18" height="12" rx="2" fill="#ece8da" />
              <circle cx="364" cy="420" r="5" fill="#e9c54a" />
              </g>
              <path className="link" d="M566 440 C620 470 690 520 742 566" fill="none" stroke="#e9c54a" strokeWidth="2.5" strokeDasharray="6 10" />
              <g className="wifi" aria-hidden="true">
                <path d="M722 546 C734 534 750 534 762 546" fill="none" stroke="#e9c54a" strokeWidth="3" strokeLinecap="round" />
                <path d="M712 534 C730 514 754 514 772 534" fill="none" stroke="#e9c54a" strokeWidth="3" strokeLinecap="round" opacity="0.7" />
              </g>
              <text x="560" y="660" textAnchor="middle" className="scene-label">Conectividade</text>
            </g>

            {/* Galpão de beneficiamento (ponto de rede). */}
            <g aria-hidden="true">
              <path d="M690 588 L742 556 L794 588Z" fill="#24352a" stroke="#ece8da" strokeOpacity="0.5" />
              <rect x="700" y="588" width="84" height="38" fill="#1c2c22" stroke="#ece8da" strokeOpacity="0.4" />
              <rect x="728" y="602" width="22" height="24" fill="#0b110d" />
            </g>

            {/* Segurança: poste, câmera e campo de visão. */}
            <g className={spot("seguranca")} role="button" tabIndex={0} aria-label="Câmeras de segurança, ver capítulo" {...spotHandlers("seguranca")}>
              <rect x="1160" y="440" width="110" height="190" fill="transparent" />
              <rect x="1226" y="470" width="8" height="160" fill="#2b3b30" />
              <g className="cam">
                <polygon className="fov" points="1196,478 900,560 920,660" fill="#e9c54a" fillOpacity="0.16" stroke="#e9c54a" strokeOpacity="0.5" strokeDasharray="8 8" />
                <rect x="1196" y="464" width="48" height="20" rx="4" fill="#24352a" stroke="#ece8da" strokeOpacity="0.8" strokeWidth="2" />
                <circle cx="1196" cy="474" r="6" fill="#e9c54a" />
                <circle className="rec" cx="1236" cy="470" r="3" fill="#e9c54a" />
              </g>
              <text x="1230" y="662" textAnchor="middle" className="scene-label">Câmeras</text>
            </g>

            {/* Gestão e território: rótulos ancorados no bananal. */}
            <g className={spot("gestao")} role="button" tabIndex={0} aria-label="Gestão da banana, ver capítulo" {...spotHandlers("gestao")}>
              <rect x="800" y="548" width="740" height="120" fill="transparent" />
              <text x="1000" y="700" textAnchor="middle" className="scene-label">Gestão da banana</text>
            </g>
            <g className={spot("territorio")} role="button" tabIndex={0} aria-label="Inteligência territorial, ver capítulo" {...spotHandlers("territorio")}>
              <circle cx="1470" cy="360" r="26" fill="transparent" />
              <circle cx="1470" cy="360" r="8" fill="#e9c54a" />
              <circle className="ping" cx="1470" cy="360" r="8" fill="none" stroke="#e9c54a" strokeWidth="2" />
              <text x="1470" y="402" textAnchor="middle" className="scene-label">Território</text>
            </g>

            <g className="layer layer-front" aria-hidden="true">
              <g transform="translate(1580 970) scale(1.9)"><use href="#banana-leaves" /><use href="#bunch" /></g>
            </g>
          </g>
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
