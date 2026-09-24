import React from 'react';
import {AbsoluteFill, getInputProps} from 'remotion';
import {C, F, H, W, rnd} from './theme';

/** Displacement filter re-seeded every 3 frames so every line "boils" like hand-drawn animation. */
export const Boil: React.FC<{id: string; f: number; scale?: number; freq?: number}> = ({id, f, scale = 3.2, freq = 0.02}) => (
  <filter id={id} x="-20%" y="-20%" width="140%" height="140%">
    <feTurbulence type="fractalNoise" baseFrequency={freq} numOctaves={2} seed={Math.floor(f / 3) % 89} />
    <feDisplacementMap in="SourceGraphic" scale={scale} />
  </filter>
);

/** Render with --props='{"clean":true}' to drop grain, flicker, scratches and dust: per-frame noise defeats animated-WebP compression and leaves ghosts. */
const CLEAN = (getInputProps() as {clean?: boolean}).clean === true;

/** Aged-film layer: grain, scratches, dust, vignette, flicker. strength 0..1 */
export const Film: React.FC<{f: number; strength?: number; dark?: boolean}> = ({f, strength = 1, dark = false}) => {
  if (strength <= 0) return null;
  const seed = Math.floor(f / 2);
  const scratches = [0, 1].filter((i) => rnd(seed * 7 + i) > 0.72).map((i) => ({
    x: rnd(seed * 3 + i * 11) * W,
    o: 0.08 + rnd(seed + i * 5) * 0.16,
    w: 1 + rnd(seed * 5 + i) * 1.5,
  }));
  const dust = Array.from({length: 5}, (_, i) => ({
    x: rnd(f * 1.7 + i * 29) * W,
    y: rnd(f * 2.3 + i * 17) * H,
    r: 1.5 + rnd(f + i * 3) * 4,
    on: rnd(f * 0.9 + i * 41) > 0.55,
  }));
  const flicker = CLEAN ? 0 : rnd(f * 3.1) * 0.08;
  return (
    <AbsoluteFill style={{pointerEvents: 'none', opacity: strength}}>
      {CLEAN ? null : (
        <svg width={W} height={H} style={{position: 'absolute', mixBlendMode: dark ? 'screen' : 'multiply'}}>
          <filter id={`grain${f}`}>
            <feTurbulence type="fractalNoise" baseFrequency={0.85} numOctaves={2} seed={f % 97} />
            <feColorMatrix type="saturate" values="0" />
          </filter>
          <rect width={W} height={H} filter={`url(#grain${f})`} opacity={dark ? 0.1 : 0.16} />
        </svg>
      )}
      <svg width={W} height={H} style={{position: 'absolute', display: CLEAN ? 'none' : undefined}}>
        {scratches.map((s, i) => (
          <line key={i} x1={s.x} y1={0} x2={s.x + 6} y2={H} stroke={dark ? C.cream : C.ink} strokeWidth={s.w} opacity={s.o} />
        ))}
        {dust.filter((d) => d.on).map((d, i) => (
          <circle key={i} cx={d.x} cy={d.y} r={d.r} fill={dark ? C.cream : C.ink} opacity={0.35} />
        ))}
      </svg>
      <AbsoluteFill style={{background: 'radial-gradient(ellipse at center, rgba(0,0,0,0) 55%, rgba(0,0,0,0.55) 100%)'}} />
      <AbsoluteFill style={{background: '#000', opacity: flicker}} />
    </AbsoluteFill>
  );
};

/** Text that is drawn stroke-first by hand, then inked in. progress 0..1 */
export const HandText: React.FC<{
  text: string;
  x: number;
  y: number;
  size: number;
  progress: number;
  font: string;
  color?: string;
  anchor?: 'start' | 'middle' | 'end';
  rotate?: number;
  stroke?: number;
  letterSpacing?: number;
}> = ({text, x, y, size, progress, font, color = C.ink, anchor = 'middle', rotate = 0, stroke = 3, letterSpacing = 0}) => {
  const draw = Math.min(1, progress / 0.7);
  const fill = Math.max(0, (progress - 0.55) / 0.45);
  const dash = size * 9;
  return (
    <text
      x={x}
      y={y}
      fontFamily={font}
      fontSize={size}
      textAnchor={anchor}
      transform={`rotate(${rotate} ${x} ${y})`}
      fill={color}
      fillOpacity={fill}
      stroke={color}
      strokeWidth={stroke}
      strokeDasharray={dash}
      strokeDashoffset={dash * (1 - draw)}
      strokeLinejoin="round"
      letterSpacing={letterSpacing}
    >
      {text}
    </text>
  );
};

/** Rubber stamp that slams in. t = spring value 0..1 */
export const Stamp: React.FC<{text: string; x: number; y: number; color: string; t: number; rot?: number; size?: number; flip?: number}> = ({
  text, x, y, color, t, rot = -8, size = 120, flip = 1,
}) => {
  if (t <= 0.001) return null;
  const sc = 3 - 2 * t;
  const w = text.length * size * 0.68 + 80;
  const h = size * 1.35;
  return (
    <g transform={`translate(${x} ${y}) rotate(${rot}) scale(${sc * flip} ${sc})`} opacity={Math.min(1, t * 1.5)}>
      <rect x={-w / 2} y={-h / 2} width={w} height={h} rx={16} fill="none" stroke={color} strokeWidth={12} />
      <rect x={-w / 2 + 14} y={-h / 2 + 14} width={w - 28} height={h - 28} rx={10} fill="none" stroke={color} strokeWidth={4} />
      <text x={0} y={size * 0.36} textAnchor="middle" fontSize={size} fill={color} fontFamily={F.cartoon} letterSpacing={6}>
        {text}
      </text>
    </g>
  );
};

/** Speed lines / smear streaks. */
export const Speed: React.FC<{f: number; n?: number; color?: string; y0?: number; y1?: number; o?: number}> = ({f, n = 14, color = C.ink, y0 = 0, y1 = H, o = 0.5}) => (
  <g opacity={o}>
    {Array.from({length: n}, (_, i) => {
      const y = y0 + rnd(i * 9.1 + Math.floor(f / 2)) * (y1 - y0);
      const x = rnd(i * 3.3 + Math.floor(f / 2) * 1.7) * W;
      const len = 120 + rnd(i + f) * 380;
      return <line key={i} x1={x} y1={y} x2={x + len} y2={y} stroke={color} strokeWidth={2 + rnd(i * 5) * 5} strokeLinecap="round" />;
    })}
  </g>
);

/** Ink splat burst: a smooth wobbly blob plus flung drops. */
export const Splat: React.FC<{x: number; y: number; r: number; color?: string; seed?: number; o?: number}> = ({x, y, r, color = C.ink, seed = 1, o = 1}) => {
  if (r <= 0) return null;
  const n = 14;
  const pts = Array.from({length: n}, (_, i) => {
    const a = (i / n) * Math.PI * 2;
    const rr = r * (0.72 + rnd(seed * 17 + i) * 0.42);
    return [x + Math.cos(a) * rr, y + Math.sin(a) * rr];
  });
  const mid = (i: number) => {
    const [ax, ay] = pts[i % n];
    const [bx, by] = pts[(i + 1) % n];
    return [(ax + bx) / 2, (ay + by) / 2];
  };
  let d = `M ${mid(n - 1)[0]} ${mid(n - 1)[1]}`;
  for (let i = 0; i < n; i++) {
    const [mx, my] = mid(i);
    d += ` Q ${pts[i][0]} ${pts[i][1]} ${mx} ${my}`;
  }
  const drops = Array.from({length: 9}, (_, i) => {
    const a = rnd(seed * 3 + i) * Math.PI * 2;
    const dd = r * (1.1 + rnd(seed + i * 7) * 0.7);
    return <circle key={i} cx={x + Math.cos(a) * dd} cy={y + Math.sin(a) * dd} r={r * (0.03 + rnd(i + seed) * 0.08)} fill={color} />;
  });
  return (
    <g opacity={o}>
      <path d={d + ' Z'} fill={color} />
      {drops}
    </g>
  );
};
