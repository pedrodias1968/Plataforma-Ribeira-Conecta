import "./WebGisMock.css";

/**
 * Illustration of the product's WebGIS screen. Every shape and number is
 * fictional (no real property, boundary or measurement) and the component says
 * so on screen. It is decorative: the real data lives in the authenticated app.
 */
const PARCELS: Array<{ id: string; points: string; fill: string; label: string }> = [
  { id: "a", points: "430,150 560,130 610,210 520,250 440,230", fill: "#15803d", label: "A" },
  { id: "b", points: "560,130 690,150 700,250 610,210", fill: "#4ade80", label: "B" },
  { id: "c", points: "440,230 520,250 540,340 450,350 410,290", fill: "#a3e635", label: "C" },
  { id: "d", points: "520,250 610,210 700,250 680,340 540,340", fill: "#facc15", label: "D" },
  { id: "e", points: "450,350 540,340 680,340 650,420 500,430", fill: "#b45309", label: "E" },
];

export function WebGisMock() {
  return (
    <figure className="webgis" aria-label="Ilustração da tela de mapa da plataforma, com dados fictícios">
      <div className="webgis-bar" aria-hidden="true">
        <span className="webgis-search">Ir para coordenadas</span>
        <span className="webgis-chip">Medir distância</span>
        <span className="webgis-chip">Medir área</span>
        <span className="webgis-chip">Centralizar sítio</span>
        <span className="webgis-flag">Ilustração · dados fictícios</span>
      </div>
      <div className="webgis-body">
        <aside className="webgis-layers" aria-hidden="true">
          <strong>Camadas</strong>
          <label><input type="checkbox" checked readOnly tabIndex={-1} /> Limite da propriedade</label>
          <label><input type="checkbox" checked readOnly tabIndex={-1} /> Talhões</label>
          <label><input type="checkbox" checked readOnly tabIndex={-1} /> NDVI (Sentinel-2)</label>
          <label><input type="checkbox" readOnly tabIndex={-1} /> Inundação e água</label>
          <label><input type="checkbox" readOnly tabIndex={-1} /> Solo e laboratório</label>
        </aside>
        <svg className="webgis-map" viewBox="0 0 1000 520" role="img" aria-label="Mapa ilustrativo com talhões coloridos por NDVI">
          <defs>
            <pattern id="webgis-grid" width="50" height="50" patternUnits="userSpaceOnUse">
              <path d="M 50 0 L 0 0 0 50" fill="none" stroke="rgba(148,163,184,0.08)" strokeWidth="1" />
            </pattern>
            <linearGradient id="webgis-ramp" x1="0" x2="1">
              <stop offset="0" stopColor="#92400e" />
              <stop offset="0.5" stopColor="#facc15" />
              <stop offset="1" stopColor="#15803d" />
            </linearGradient>
          </defs>
          <rect width="1000" height="520" fill="#0d1712" />
          <rect width="1000" height="520" fill="url(#webgis-grid)" />
          <path d="M0 330 C150 280 250 400 380 360 S 520 470 700 430 S 900 330 1000 380" fill="none" stroke="#1d4ed8" strokeOpacity="0.55" strokeWidth="46" strokeLinecap="round" />
          <path d="M0 330 C150 280 250 400 380 360 S 520 470 700 430 S 900 330 1000 380" fill="none" stroke="#3b82f6" strokeOpacity="0.5" strokeWidth="26" strokeLinecap="round" />
          <path d="M60 80 L220 60 L300 140 L210 200 L80 170 Z" fill="#14532d" fillOpacity="0.35" />
          <path d="M760 60 L930 90 L960 200 L820 230 L740 150 Z" fill="#14532d" fillOpacity="0.3" />
          <polygon points="410,110 720,110 740,450 480,450 395,300" fill="none" stroke="#34d399" strokeWidth="3" strokeLinejoin="round" />
          {PARCELS.map((parcel) => (
            <g key={parcel.id}>
              <polygon points={parcel.points} fill={parcel.fill} fillOpacity="0.72" stroke="#0d1712" strokeWidth="2" />
            </g>
          ))}
          {[[500, 190, "A"], [640, 185, "B"], [480, 295, "C"], [605, 290, "D"], [575, 385, "E"]].map(([x, y, name]) => (
            <text key={String(name)} x={Number(x)} y={Number(y)} fill="#f8fafc" fontSize="22" fontWeight="700" textAnchor="middle">{name}</text>
          ))}
          {[[440, 140], [700, 130], [470, 420]].map(([x, y]) => (
            <g key={`${x}-${y}`}>
              <circle cx={x} cy={y} r="11" fill="#f59e0b" stroke="#0d1712" strokeWidth="3" />
              <rect x={Number(x) - 4} y={Number(y) - 3} width="8" height="6" fill="#0d1712" />
            </g>
          ))}
          <g transform="translate(24 470)">
            <rect width="110" height="6" fill="#f8fafc" fillOpacity="0.8" />
            <text y="24" fill="#cbd5e1" fontSize="14">300 m</text>
          </g>
        </svg>
        <aside className="webgis-info" aria-hidden="true">
          <strong>Talhão C (exemplo)</strong>
          <dl>
            <dt>NDVI médio</dt><dd>0,48 (fictício)</dd>
            <dt>Cena</dt><dd>Sentinel-2 · 15 set.</dd>
            <dt>Cobertura de nuvens</dt><dd>sem dado</dd>
          </dl>
          <p>Dado ausente aparece como “sem dado”, nunca como zero.</p>
        </aside>
      </div>
      <figcaption className="webgis-legend">
        <span>−1 solo/água</span>
        <span className="webgis-ramp" aria-hidden="true" />
        <span>+1 vegetação</span>
        <span className="webgis-note">Limite e talhões desenhados para ilustração. Não representam uma propriedade real.</span>
      </figcaption>
    </figure>
  );
}
