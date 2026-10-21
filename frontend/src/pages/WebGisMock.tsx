import { useEffect, useState, type KeyboardEvent, type ReactNode } from "react";
import "./WebGisMock.css";

/**
 * Illustration of the product's WebGIS screen. Every shape and number is
 * fictional (no real property, boundary or measurement) and the component says
 * so on screen. The layer chips and parcel selection really work, but the data
 * behind them is invented; the real data lives in the authenticated app.
 */
type Parcel = {
  id: string;
  label: string;
  points: string;
  fill: string;
  ndvi: string;
  scene: string;
  at: [number, number];
};

const PARCELS: Parcel[] = [
  { id: "a", label: "A", points: "860,250 990,230 1040,310 950,350 870,330", fill: "#2e7d4f", ndvi: "0,71", scene: "Sentinel-2 · 15 set.", at: [945, 292] },
  { id: "b", label: "B", points: "990,230 1120,250 1130,350 1040,310", fill: "#5fbf6f", ndvi: "0,64", scene: "Sentinel-2 · 15 set.", at: [1070, 288] },
  { id: "c", label: "C", points: "870,330 950,350 970,440 880,450 840,390", fill: "#a7c957", ndvi: "0,48", scene: "Sentinel-2 · 15 set.", at: [905, 395] },
  { id: "d", label: "D", points: "950,350 1040,310 1130,350 1110,440 970,440", fill: "#e9c54a", ndvi: "0,39", scene: "Sentinel-2 · 10 set.", at: [1040, 392] },
  { id: "e", label: "E", points: "880,450 970,440 1110,440 1080,520 930,530", fill: "#b5651d", ndvi: "0,22", scene: "Sentinel-2 · 10 set.", at: [1000, 488] },
];

const LAYERS = [
  { key: "boundary", label: "Limite" },
  { key: "parcels", label: "Talhões" },
  { key: "ndvi", label: "NDVI" },
  { key: "water", label: "Água e inundação" },
] as const;

type LayerKey = (typeof LAYERS)[number]["key"];

const RIVER = "M0 640 C240 590 420 720 700 690 S 1000 780 1300 740 S 1500 650 1600 700";

const WIDE_VIEWBOX = "0 0 1600 900";
const NARROW_VIEWBOX = "770 180 470 470";

function useViewBox() {
  const [viewBox, setViewBox] = useState(WIDE_VIEWBOX);
  useEffect(() => {
    if (typeof window.matchMedia !== "function") return;
    const query = window.matchMedia("(max-width: 960px)");
    const update = () => setViewBox(query.matches ? NARROW_VIEWBOX : WIDE_VIEWBOX);
    update();
    query.addEventListener("change", update);
    return () => query.removeEventListener("change", update);
  }, []);
  return viewBox;
}

export function WebGisMock({ children }: { children?: ReactNode }) {
  const [layers, setLayers] = useState<Record<LayerKey, boolean>>({ boundary: true, parcels: true, ndvi: true, water: false });
  const [selectedId, setSelectedId] = useState("c");
  const viewBox = useViewBox();
  const selected = PARCELS.find((parcel) => parcel.id === selectedId) ?? PARCELS[2];

  const toggle = (key: LayerKey) => setLayers((current) => ({ ...current, [key]: !current[key] }));
  const onParcelKey = (event: KeyboardEvent<SVGGElement>, id: string) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      setSelectedId(id);
    }
  };

  return (
    <div className="stage">
      <svg className="stage-map" viewBox={viewBox} preserveAspectRatio="xMidYMid slice" role="img" aria-label="Mapa ilustrativo com talhões coloridos por NDVI">
        <defs>
          <pattern id="stage-grid" width="80" height="80" patternUnits="userSpaceOnUse">
            <path d="M 80 0 L 0 0 0 80" fill="none" stroke="rgba(236,232,218,0.05)" strokeWidth="1" />
          </pattern>
          <pattern id="stage-hatch" width="14" height="14" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
            <line x1="0" y1="0" x2="0" y2="14" stroke="rgba(110,168,254,0.45)" strokeWidth="3" />
          </pattern>
        </defs>
        <rect width="1600" height="900" fill="#0b110d" />
        <rect width="1600" height="900" fill="url(#stage-grid)" />
        <g fill="none" stroke="rgba(236,232,218,0.07)" strokeWidth="1.5">
          <path d="M0 210 C260 150 430 290 700 230 S 1080 110 1600 190" />
          <path d="M0 270 C260 210 430 350 700 290 S 1080 170 1600 250" />
          <path d="M0 330 C260 270 430 410 700 350 S 1080 230 1600 310" />
          <path d="M0 830 C300 790 520 880 900 830 S 1400 780 1600 820" />
        </g>
        <path d="M1220 560 L1420 520 L1520 640 L1380 700 L1230 650 Z" fill="#14301f" fillOpacity="0.55" />
        <path d="M120 120 L330 90 L420 190 L300 270 L140 230 Z" fill="#14301f" fillOpacity="0.45" />
        <path className="stage-river" d={RIVER} fill="none" stroke="#1f4f9c" strokeOpacity="0.6" strokeWidth="58" strokeLinecap="round" />
        <path className="stage-river-flow" d={RIVER} fill="none" stroke="#5b9cf0" strokeOpacity="0.55" strokeWidth="26" strokeLinecap="round" />
        {layers.water && (
          <path className="stage-layer" d={RIVER} fill="none" stroke="url(#stage-hatch)" strokeWidth="190" strokeLinecap="round" opacity="0.9" />
        )}
        {layers.parcels &&
          PARCELS.map((parcel, index) => (
            <g
              key={parcel.id}
              className={`stage-parcel${parcel.id === selectedId ? " is-selected" : ""}`}
              style={{ animationDelay: `${index * 70}ms` }}
              role="button"
              tabIndex={0}
              aria-pressed={parcel.id === selectedId}
              aria-label={`Talhão ${parcel.label} (exemplo fictício)`}
              onClick={() => setSelectedId(parcel.id)}
              onKeyDown={(event) => onParcelKey(event, parcel.id)}
            >
              <polygon
                points={parcel.points}
                fill={layers.ndvi ? parcel.fill : "#26352b"}
                fillOpacity={layers.ndvi ? 0.8 : 0.9}
                stroke={parcel.id === selectedId ? "#ece8da" : "#0b110d"}
                strokeWidth={parcel.id === selectedId ? 4 : 2}
                strokeLinejoin="round"
              />
              <text x={parcel.at[0]} y={parcel.at[1]} textAnchor="middle" className="stage-parcel-label">
                {parcel.label}
              </text>
            </g>
          ))}
        {layers.boundary && (
          <polygon className="stage-layer" points="840,215 1150,215 1160,540 905,555 820,395" fill="none" stroke="#e9c54a" strokeWidth="3" strokeDasharray="14 8" strokeLinejoin="round" />
        )}
        {[[850, 237], [1132, 232], [890, 540]].map(([x, y]) => (
          <g key={`${x}-${y}`} aria-hidden="true">
            <circle cx={x} cy={y} r="11" fill="#e9c54a" stroke="#0b110d" strokeWidth="3" />
          </g>
        ))}
        <g transform="translate(60 840)" aria-hidden="true">
          <rect width="120" height="5" fill="#ece8da" fillOpacity="0.85" />
          <text y="26" className="stage-scale">300 m</text>
        </g>
      </svg>

      <div className="stage-top">
        <div className="stage-chips" role="group" aria-label="Camadas do mapa ilustrativo">
          {LAYERS.map((layer) => (
            <button key={layer.key} type="button" className="stage-chip" aria-pressed={layers[layer.key]} onClick={() => toggle(layer.key)}>
              {layer.label}
            </button>
          ))}
        </div>
        <span className="stage-flag">Ilustração · dados fictícios</span>
      </div>

      <aside className="stage-info" aria-live="polite">
        <span className="stage-info-kicker">Talhão {selected.label} · exemplo</span>
        <dl>
          <div><dt>NDVI médio</dt><dd>{selected.ndvi} <small>(fictício)</small></dd></div>
          <div><dt>Cena</dt><dd>{selected.scene}</dd></div>
          <div><dt>Cobertura de nuvens</dt><dd>sem dado</dd></div>
        </dl>
        <p>Dado ausente aparece como “sem dado”, nunca como zero.</p>
      </aside>

      <div className="stage-legend">
        <span>−1 solo/água</span>
        <span className="stage-ramp" aria-hidden="true" />
        <span>+1 vegetação</span>
        <span className="stage-note">Limite e talhões desenhados para ilustração. Não representam uma propriedade real.</span>
      </div>

      {children && <div className="stage-copy">{children}</div>}
    </div>
  );
}
