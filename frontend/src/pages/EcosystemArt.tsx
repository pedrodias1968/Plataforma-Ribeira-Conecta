/**
 * Peças de ilustração da cena do ecossistema (SVG). Tudo é desenhado à mão e
 * gerado de forma determinística (sem aleatoriedade em tempo de execução), para
 * a cena ser sempre a mesma e os testes não variarem.
 */

import type { Plant } from "./ecosystemSceneData";

const LEAF = "M0 0 C18 -20 52 -31 86 -23 C101 -19 111 -8 115 4 C103 -4 89 -4 75 0 C51 6 23 9 0 0Z";
const LEAF_RIB = "M0 0 C30 -12 70 -14 115 4";
const LEAF_TEARS = "M38 -11 L42 -25 M60 -12 L66 -26 M83 -8 L92 -17 M50 -6 L48 5 M74 -3 L77 3 M98 -1 L104 -6";
const STEM = "M-6 0 C-5.5 -34 -4.5 -70 -3 -104 L3.5 -104 C5 -70 6 -34 7 0 Z";

const FINGERS = (() => {
  const out: Array<{ x: number; y: number; r: number; s: number }> = [];
  for (let h = 0; h < 5; h += 1) {
    const count = h < 3 ? 6 : 5;
    for (let i = 0; i < count; i += 1) {
      const x = 20 + (i * 16) / (count - 1);
      out.push({ x, y: -86 + h * 8, r: (x - 28) * 2.6, s: 1 - h * 0.06 });
    }
  }
  return out;
})();

function Leaf({ id, fill, tears = 0.55 }: { id: string; fill: string; tears?: number }) {
  return (
    <g id={id}>
      <path d={LEAF} fill={fill} />
      <path d={LEAF_RIB} fill="none" stroke="#c4e39a" strokeOpacity="0.5" strokeWidth="1.4" />
      <path d={LEAF_TEARS} fill="none" stroke="#0b1810" strokeOpacity={tears} strokeWidth="1.3" strokeLinecap="round" />
    </g>
  );
}

/** Gradientes, padrões e as peças reutilizáveis (folhas, cacho, bananeiras). */
export function SceneDefs() {
  return (
    <defs>
      <linearGradient id="sky" gradientUnits="userSpaceOnUse" x1="0" y1="-300" x2="0" y2="640">
        <stop offset="0" stopColor="#050c09" />
        <stop offset="0.45" stopColor="#0d1d16" />
        <stop offset="0.78" stopColor="#1f2f22" />
        <stop offset="1" stopColor="#35402a" />
      </linearGradient>
      <radialGradient id="sun" gradientUnits="userSpaceOnUse" cx="1250" cy="250" r="480">
        <stop offset="0" stopColor="#f6dc86" stopOpacity="0.42" />
        <stop offset="0.35" stopColor="#e9c54a" stopOpacity="0.16" />
        <stop offset="1" stopColor="#e9c54a" stopOpacity="0" />
      </radialGradient>
      <radialGradient id="sun-core" cx="50%" cy="50%" r="50%">
        <stop offset="0" stopColor="#fff2c4" stopOpacity="0.95" />
        <stop offset="0.5" stopColor="#f6dc86" stopOpacity="0.55" />
        <stop offset="1" stopColor="#f6dc86" stopOpacity="0" />
      </radialGradient>
      <linearGradient id="ray" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stopColor="#f6dc86" stopOpacity="0.16" />
        <stop offset="1" stopColor="#f6dc86" stopOpacity="0" />
      </linearGradient>
      <linearGradient id="ridge-1" gradientUnits="userSpaceOnUse" x1="0" y1="140" x2="0" y2="520">
        <stop offset="0" stopColor="#365549" />
        <stop offset="1" stopColor="#1c3129" />
      </linearGradient>
      <linearGradient id="ridge-2" gradientUnits="userSpaceOnUse" x1="0" y1="220" x2="0" y2="560">
        <stop offset="0" stopColor="#2b4639" />
        <stop offset="1" stopColor="#172a20" />
      </linearGradient>
      <linearGradient id="ridge-3" gradientUnits="userSpaceOnUse" x1="0" y1="320" x2="0" y2="620">
        <stop offset="0" stopColor="#22392a" />
        <stop offset="1" stopColor="#12231a" />
      </linearGradient>
      <linearGradient id="ridge-4" gradientUnits="userSpaceOnUse" x1="0" y1="420" x2="0" y2="660">
        <stop offset="0" stopColor="#1c3123" />
        <stop offset="1" stopColor="#0f1f16" />
      </linearGradient>
      <radialGradient id="mist" cx="50%" cy="50%" r="50%">
        <stop offset="0" stopColor="#d9e8d6" stopOpacity="0.16" />
        <stop offset="1" stopColor="#d9e8d6" stopOpacity="0" />
      </radialGradient>
      <linearGradient id="ground" gradientUnits="userSpaceOnUse" x1="0" y1="540" x2="0" y2="900">
        <stop offset="0" stopColor="#2d4b2b" />
        <stop offset="0.35" stopColor="#1d331f" />
        <stop offset="1" stopColor="#0f1d13" />
      </linearGradient>
      <linearGradient id="water" gradientUnits="userSpaceOnUse" x1="0" y1="640" x2="0" y2="780">
        <stop offset="0" stopColor="#4b88c4" />
        <stop offset="1" stopColor="#163f6c" />
      </linearGradient>
      <linearGradient id="leaf-g" x1="0" y1="0" x2="1" y2="0">
        <stop offset="0" stopColor="#2a5c37" />
        <stop offset="0.55" stopColor="#3f8e4f" />
        <stop offset="1" stopColor="#7cbb60" />
      </linearGradient>
      <linearGradient id="leaf-g2" x1="0" y1="0" x2="1" y2="0">
        <stop offset="0" stopColor="#1e4429" />
        <stop offset="0.6" stopColor="#2f6b3d" />
        <stop offset="1" stopColor="#4f8c45" />
      </linearGradient>
      <linearGradient id="leaf-dry-g" x1="0" y1="0" x2="1" y2="0">
        <stop offset="0" stopColor="#4f4226" />
        <stop offset="0.6" stopColor="#857043" />
        <stop offset="1" stopColor="#a68d58" />
      </linearGradient>
      <linearGradient id="stem-g" x1="0" y1="0" x2="1" y2="0">
        <stop offset="0" stopColor="#7d9752" />
        <stop offset="0.5" stopColor="#4f6a37" />
        <stop offset="1" stopColor="#2b3e22" />
      </linearGradient>
      <linearGradient id="fruit-g" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0" stopColor="#d8d264" />
        <stop offset="1" stopColor="#86a03a" />
      </linearGradient>
      <radialGradient id="heart-g" cx="35%" cy="35%" r="70%">
        <stop offset="0" stopColor="#a8475f" />
        <stop offset="1" stopColor="#4e1c2c" />
      </radialGradient>
      <linearGradient id="metal" gradientUnits="userSpaceOnUse" x1="0" y1="440" x2="0" y2="630">
        <stop offset="0" stopColor="#eef0e6" />
        <stop offset="1" stopColor="#7f8777" />
      </linearGradient>
      <radialGradient id="glow" cx="50%" cy="50%" r="50%">
        <stop offset="0" stopColor="#f6dc86" stopOpacity="0.85" />
        <stop offset="1" stopColor="#e9c54a" stopOpacity="0" />
      </radialGradient>
      <linearGradient id="wall-g" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stopColor="#48574a" />
        <stop offset="1" stopColor="#2a362c" />
      </linearGradient>
      <linearGradient id="roof-g" x1="0" y1="0" x2="1" y2="0">
        <stop offset="0" stopColor="#8d968a" />
        <stop offset="0.5" stopColor="#6b7468" />
        <stop offset="1" stopColor="#465045" />
      </linearGradient>
      <linearGradient id="bay-g" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stopColor="#f2d67a" stopOpacity="0.55" />
        <stop offset="1" stopColor="#8a6f24" stopOpacity="0.35" />
      </linearGradient>
      <linearGradient id="pole-g" x1="0" y1="0" x2="1" y2="0">
        <stop offset="0" stopColor="#5d6a60" />
        <stop offset="1" stopColor="#252f28" />
      </linearGradient>
      <linearGradient id="cam-g" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0" stopColor="#f2f3ec" />
        <stop offset="1" stopColor="#959d8f" />
      </linearGradient>
      <radialGradient id="lens-g" cx="40%" cy="40%" r="60%">
        <stop offset="0" stopColor="#4a7fb8" />
        <stop offset="1" stopColor="#070b0d" />
      </radialGradient>
      <linearGradient id="fov-g" gradientUnits="userSpaceOnUse" x1="1198" y1="476" x2="910" y2="610">
        <stop offset="0" stopColor="#e9c54a" stopOpacity="0.38" />
        <stop offset="1" stopColor="#e9c54a" stopOpacity="0.02" />
      </linearGradient>
      <linearGradient id="panel-g" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0" stopColor="#3d7cc9" />
        <stop offset="1" stopColor="#15325e" />
      </linearGradient>
      <linearGradient id="foil-g" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0" stopColor="#f6dc86" />
        <stop offset="0.5" stopColor="#c9a62f" />
        <stop offset="1" stopColor="#8a6a1c" />
      </linearGradient>
      <linearGradient id="beam-g" gradientUnits="userSpaceOnUse" x1="1374" y1="318" x2="1019" y2="600">
        <stop offset="0" stopColor="#f6dc86" stopOpacity="0.32" />
        <stop offset="1" stopColor="#f6dc86" stopOpacity="0.03" />
      </linearGradient>
      <radialGradient id="vignette" cx="50%" cy="45%" r="75%">
        <stop offset="0.6" stopColor="#050a07" stopOpacity="0" />
        <stop offset="1" stopColor="#050a07" stopOpacity="0.75" />
      </radialGradient>
      <pattern id="scene-hatch" width="14" height="14" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
        <line x1="0" y1="0" x2="0" y2="14" stroke="rgba(140,190,255,0.5)" strokeWidth="3" />
      </pattern>

      <Leaf id="leaf" fill="url(#leaf-g)" />
      <Leaf id="leaf-b" fill="url(#leaf-g2)" tears={0.4} />
      <Leaf id="leaf-dry" fill="url(#leaf-dry-g)" tears={0.7} />
      <path id="leaf-young" d="M0 0 C-5 -18 -3 -40 4 -60 C9 -40 9 -18 5 0Z" fill="#8cc66a" />
      <path id="finger" d="M0 0 C-3.2 -5 -2.6 -11 1.6 -14.5 C1.4 -9.5 2.6 -4.6 4.2 0 Z" fill="url(#fruit-g)" />

      <g id="bunch">
        <path d="M3 -98 C18 -104 28 -94 28 -78 L28 -50" fill="none" stroke="#5f7a3a" strokeWidth="3.4" strokeLinecap="round" />
        {FINGERS.map((f) => (
          <use key={`${f.x}-${f.y}`} href="#finger" transform={`translate(${f.x.toFixed(1)} ${f.y}) rotate(${f.r.toFixed(1)}) scale(${f.s.toFixed(2)})`} />
        ))}
        <path d="M28 -50 C34.5 -46 35.5 -36 28 -26 C20.5 -36 21.5 -46 28 -50Z" fill="url(#heart-g)" />
        <path d="M26 -46 C24 -42 24 -36 26.5 -32" fill="none" stroke="#ffffff" strokeOpacity="0.2" strokeWidth="1" />
      </g>

      <g id="stem">
        <path d={STEM} fill="url(#stem-g)" />
        <path d="M-1.5 -8 C-1 -40 -0.6 -70 0 -100" fill="none" stroke="#ffffff" strokeOpacity="0.12" strokeWidth="1" />
      </g>

      <g id="plant-a">
        <ellipse cx="0" cy="1" rx="18" ry="3.6" fill="#000" opacity="0.3" />
        <use href="#leaf-dry" transform="translate(-1 -74) scale(-1 1) rotate(96) scale(0.62)" />
        <use href="#leaf-b" transform="translate(0 -100) scale(-1 1) rotate(-42) scale(0.9)" />
        <use href="#leaf-b" transform="translate(0 -100) rotate(-56) scale(0.86)" />
        <use href="#stem" />
        <use href="#leaf" transform="translate(0 -102) scale(-1 1) rotate(10) scale(1.02)" />
        <use href="#leaf" transform="translate(0 -102) rotate(18) scale(1.06)" />
        <use href="#leaf" transform="translate(0 -104) scale(-1 1) rotate(-70) scale(0.82)" />
        <use href="#leaf" transform="translate(0 -104) rotate(-24) scale(0.95)" />
        <use href="#leaf-young" transform="translate(1 -104) rotate(6)" />
        <use href="#bunch" />
      </g>

      <g id="plant-b">
        <ellipse cx="0" cy="1" rx="18" ry="3.6" fill="#000" opacity="0.3" />
        <use href="#leaf-dry" transform="translate(1 -80) rotate(100) scale(0.66)" />
        <use href="#leaf-dry" transform="translate(-1 -66) scale(-1 1) rotate(92) scale(0.56)" />
        <use href="#leaf-b" transform="translate(0 -100) scale(-1 1) rotate(-30) scale(0.92)" />
        <use href="#leaf-b" transform="translate(0 -100) rotate(-44) scale(0.9)" />
        <use href="#stem" />
        <use href="#leaf" transform="translate(0 -102) scale(-1 1) rotate(24) scale(1)" />
        <use href="#leaf" transform="translate(0 -102) rotate(6) scale(1.04)" />
        <use href="#leaf" transform="translate(0 -104) scale(-1 1) rotate(-52) scale(0.9)" />
        <use href="#leaf" transform="translate(0 -104) rotate(-40) scale(0.86)" />
        <use href="#leaf-young" transform="translate(0 -104) rotate(-8)" />
      </g>

      <g id="plant-c">
        <ellipse cx="0" cy="1" rx="14" ry="3" fill="#000" opacity="0.28" />
        <use href="#leaf-b" transform="translate(0 -100) scale(-1 1) rotate(-20) scale(0.8)" />
        <use href="#stem" />
        <use href="#leaf" transform="translate(0 -102) rotate(-30) scale(0.8)" />
        <use href="#leaf" transform="translate(0 -102) scale(-1 1) rotate(14) scale(0.72)" />
        <use href="#leaf" transform="translate(0 -102) rotate(10) scale(0.76)" />
        <use href="#leaf-young" transform="translate(1 -104) rotate(4) scale(1.1)" />
      </g>
    </defs>
  );
}

export function BananaPlant({ plant }: { plant: Plant }) {
  return (
    <g transform={`translate(${plant.x.toFixed(1)} ${plant.y.toFixed(1)}) scale(${(plant.flip ? -plant.s : plant.s).toFixed(3)} ${plant.s.toFixed(3)})`}>
      <g className="plant" style={{ animationDelay: `${plant.delay.toFixed(2)}s` }}>
        <use href={`#plant-${plant.variant}`} />
      </g>
    </g>
  );
}

/** Etiqueta em pílula ancorada na cena. */
export function SceneLabel({ x, y, text }: { x: number; y: number; text: string }) {
  const width = text.length * 8.2 + 34;
  return (
    <g className="scene-label" aria-hidden="true">
      <rect x={x - width / 2} y={y - 14} width={width} height="28" rx="14" />
      <circle cx={x - width / 2 + 14} cy={y} r="3.2" />
      <text x={x + 6} y={y + 4.2} textAnchor="middle">
        {text}
      </text>
    </g>
  );
}
