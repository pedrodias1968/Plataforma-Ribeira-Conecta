/** Dados da cena do ecossistema, gerados de forma determinística. */

/** Gerador pseudoaleatório determinístico (mulberry32). */
export function rng(seed: number) {
  let a = seed;
  return () => {
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

type Wave = [amp: number, len: number, phase: number];

/** Linha de serra com textura de copa de mata (pequenas ondulações). */
function ridgePath(base: number, waves: Wave[], canopy: number, step: number, seed: number) {
  const random = rng(seed);
  const yAt = (x: number) => waves.reduce((y, [amp, len, phase]) => y + amp * Math.sin(x / len + phase), base);
  let d = `M-900 1500 L-900 ${yAt(-900).toFixed(1)}`;
  for (let x = -900 + step; x <= 2500; x += step) {
    const cx = x - step / 2;
    d += ` Q${cx.toFixed(1)} ${(yAt(cx) - canopy * (0.3 + random())).toFixed(1)} ${x.toFixed(1)} ${yAt(x).toFixed(1)}`;
  }
  return `${d} L2500 1500 Z`;
}

export const RIDGES = {
  far: [
    { d: ridgePath(230, [[72, 240, 0.5], [34, 97, 1.9], [12, 41, 0.7]], 3, 14, 11), fill: "url(#ridge-1)" },
    { d: ridgePath(305, [[58, 210, 2.4], [26, 83, 0.4], [10, 37, 1.1]], 5, 14, 23), fill: "url(#ridge-2)" },
  ],
  mid: [
    { d: ridgePath(395, [[52, 190, 1.3], [22, 71, 2.6], [9, 31, 0.2]], 7, 12, 37), fill: "url(#ridge-3)" },
    { d: ridgePath(478, [[38, 170, 0.1], [18, 63, 1.7], [6, 23, 0.9]], 9, 11, 41), fill: "url(#ridge-4)" },
  ],
};

export const RIVER = "M-600 720 C-200 690 100 700 300 690 C480 740 560 770 760 726 S1180 640 1650 700 S2000 740 2300 700";

export const GROUND =
  "M-900 660 L-600 650 C-200 596 220 640 480 612 S800 592 1000 590 S1400 542 1600 580 L2500 600 L2500 1500 L-900 1500Z";

export type PlantVariant = "a" | "b" | "c";
export type Plant = { x: number; y: number; s: number; variant: PlantVariant; flip: boolean; delay: number };

export const PLANTS: Plant[] = (() => {
  const random = rng(7);
  const rows = [
    { y: 566, s: 0.31, x0: 846, x1: 1560, step: 40, jitterY: 6 },
    { y: 598, s: 0.37, x0: 830, x1: 1560, step: 48, jitterY: 6 },
    { y: 630, s: 0.44, x0: 816, x1: 1570, step: 56, jitterY: 3 },
  ];
  const out: Plant[] = [];
  for (const row of rows) {
    for (let x = row.x0; x <= row.x1; x += row.step) {
      const px = x + (random() - 0.5) * row.step * 0.55;
      const r = random();
      const variant: PlantVariant = r < 0.45 ? "a" : r < 0.85 ? "b" : "c";
      out.push({
        x: px,
        y: row.y + Math.sin(px / 150) * 8 + (random() - 0.5) * row.jitterY * 2,
        s: row.s * (0.86 + random() * 0.28) * (variant === "c" ? 0.78 : 1),
        variant,
        flip: random() < 0.5,
        delay: random() * 3,
      });
    }
  }
  return out.sort((p, q) => p.y - q.y);
})();

export const BUSHES = (() => {
  const random = rng(19);
  return Array.from({ length: 11 }, (_, i) => ({
    x: 30 + i * 46 + random() * 20,
    y: 640 + random() * 18,
    r: 9 + random() * 10,
  }));
})();

export const MOTES = (() => {
  const random = rng(31);
  return Array.from({ length: 18 }, () => ({
    x: 560 + random() * 1000,
    y: 400 + random() * 240,
    r: 1.2 + random() * 1.4,
    delay: random() * 6,
    dur: 5 + random() * 5,
  }));
})();

/** Travessas da torre treliçada entre as duas pernas. */
export const TOWER_BRACES = (() => {
  const top = 450;
  const bottom = 624;
  const leftAt = (y: number) => 540 + ((bottom - y) / (bottom - top)) * 15;
  const rightAt = (y: number) => 580 - ((bottom - y) / (bottom - top)) * 15;
  const levels = [624, 596, 570, 546, 524, 504, 486, 470, 456];
  let d = "";
  for (let i = 0; i < levels.length - 1; i += 1) {
    const y0 = levels[i];
    const y1 = levels[i + 1];
    d += `M${leftAt(y0).toFixed(1)} ${y0} L${rightAt(y1).toFixed(1)} ${y1} `;
    d += `M${rightAt(y0).toFixed(1)} ${y0} L${leftAt(y1).toFixed(1)} ${y1} `;
    d += `M${leftAt(y1).toFixed(1)} ${y1} L${rightAt(y1).toFixed(1)} ${y1} `;
  }
  return d.trim();
})();

