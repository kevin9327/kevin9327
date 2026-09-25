/** Shared Droste effects. The reel's Boil / Film / HandText / Stamp / Speed / Splat live untouched in src/lib/fx.tsx. */
import React from 'react';
import {getInputProps} from 'remotion';
import {F} from '../lib/theme';
import {lerpc, rnd} from './anim';

/** Byte levers (input props). All default to on. */
export type DrosteProps = {cornea?: 'gl' | 'svg'; zoomLines?: boolean; impact?: boolean};
export const drosteProps = (): Required<DrosteProps> => {
  const p = getInputProps() as DrosteProps;
  return {cornea: p.cornea === 'svg' ? 'svg' : 'gl', zoomLines: p.zoomLines !== false, impact: p.impact !== false};
};

/**
 * Boil3: 3 drawings, each held 4 frames (12-frame cycle, divides T=384).
 * Id convention: `boil-L{k}-{layer}`. Use only on characters, only while props.boil.
 * colorInterpolationFilters sRGB: the default linearRGB round-trips 8-bit colours and crushes darks
 * (night #0d1117 came out #0d0d16), which would make a boiled night pupil differ from the child level's night.
 */
export const Boil3: React.FC<{id: string; f: number; scale?: number; freq?: number}> = ({id, f, scale = 2.2, freq = 0.02}) => (
  <filter id={id} x="-20%" y="-20%" width="140%" height="140%" colorInterpolationFilters="sRGB">
    <feTurbulence type="fractalNoise" baseFrequency={freq} numOctaves={2} seed={[7, 41, 83][Math.floor(f / 4) % 3]} />
    <feDisplacementMap in="SourceGraphic" scale={scale} />
  </filter>
);

/** Sparse radial zoom lines about (cx, cy) in screen space; re-seeded every 4 frames (on twos in the output). */
export const ZoomLines: React.FC<{f: number; cx: number; cy: number; vel: number; color: string}> = ({f, cx, cy, vel, color}) => {
  if (vel < 0.12) return null;
  const seed = Math.floor(f / 4);
  const len = 90 + 800 * vel;
  const o = lerpc(vel, [0.12, 0.22], [0, 0.28]);
  return (
    <g opacity={o} stroke={color} strokeWidth={3} strokeLinecap="round">
      {Array.from({length: 14}, (_, i) => {
        const a = ((i + 0.15 + 0.7 * rnd(seed * 31.7 + i * 7.3)) / 14) * Math.PI * 2;
        const r0 = 300 + 60 * rnd(seed * 13.1 + i * 3.7);
        const r1 = r0 + len * (0.7 + 0.3 * rnd(seed * 5.3 + i * 11.9));
        const c = Math.cos(a);
        const s = Math.sin(a);
        return <line key={i} x1={cx + c * r0} y1={cy + s * r0} x2={cx + c * r1} y2={cy + s * r1} />;
      })}
    </g>
  );
};

/**
 * Stroked pop number (Luckiest Guy, paint-order stroke). t is a pop30() value (overshoots past 1);
 * scale = 0.4 + 0.6 t about (x, y). Renders nothing while t <= 0.001.
 */
export const PopNumber: React.FC<{
  text: string;
  x: number;
  y: number;
  size: number;
  t: number;
  fill: string;
  stroke: string;
  strokeW: number;
  anchor?: 'start' | 'middle' | 'end';
  opacity?: number;
}> = ({text, x, y, size, t, fill, stroke, strokeW, anchor = 'middle', opacity = 1}) => {
  if (t <= 0.001) return null;
  const sc = 0.4 + 0.6 * t;
  return (
    <g transform={`translate(${x} ${y}) scale(${sc})`} opacity={opacity}>
      <text
        x={0}
        y={0}
        fontFamily={F.cartoon}
        fontSize={size}
        textAnchor={anchor}
        fill={fill}
        stroke={stroke}
        strokeWidth={strokeW}
        strokeLinejoin="round"
        style={{paintOrder: 'stroke'}}
      >
        {text}
      </text>
    </g>
  );
};

type P2 = [number, number];

/** Convex hull (Andrew monotone chain) as a closed SVG path. */
export const hullPath = (points: P2[]) => {
  const pts = points.slice().sort((a, b) => a[0] - b[0] || a[1] - b[1]);
  if (pts.length < 3) return pts.length ? `M ${pts.map((p) => `${p[0]} ${p[1]}`).join(' L ')} Z` : '';
  const cross = (o: P2, a: P2, b: P2) => (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0]);
  const lower: P2[] = [];
  for (const p of pts) {
    while (lower.length >= 2 && cross(lower[lower.length - 2], lower[lower.length - 1], p) <= 0) lower.pop();
    lower.push(p);
  }
  const upper: P2[] = [];
  for (let i = pts.length - 1; i >= 0; i--) {
    const p = pts[i];
    while (upper.length >= 2 && cross(upper[upper.length - 2], upper[upper.length - 1], p) <= 0) upper.pop();
    upper.push(p);
  }
  const hull = lower.slice(0, -1).concat(upper.slice(0, -1));
  return `M ${hull.map((p) => `${p[0]} ${p[1]}`).join(' L ')} Z`;
};

/** 2-frame smear: the convex hull of two silhouettes' key points (e.g. body corners at two poses). */
export const HullSmear: React.FC<{from: P2[]; to: P2[]; fill: string; stroke: string; strokeW: number}> = ({from, to, fill, stroke, strokeW}) => (
  <path d={hullPath(from.concat(to))} fill={fill} stroke={stroke} strokeWidth={strokeW} strokeLinejoin="round" />
);

const hexRgb = (h: string) => {
  const s = h.replace('#', '');
  return [0, 2, 4].map((i) => parseInt(s.slice(i, i + 2), 16) / 255);
};

/**
 * Two-tone impact filter: luminance -> threshold (discrete [0,0,1]) -> dark / light.
 * Use as filter={`url(#${id})`} on a group drawn at px ~ 1. The filter region is the level frame (userSpaceOnUse,
 * padded 40 u) so the giant background rect does not blow up the filter buffer. sRGB keeps the two colours exact.
 */
export const Impact2ToneDefs: React.FC<{id: string; dark: string; light: string}> = ({id, dark, light}) => {
  const d = hexRgb(dark);
  const l = hexRgb(light);
  const ch = (i: number) => ({type: 'linear' as const, slope: l[i] - d[i], intercept: d[i]});
  return (
    <filter id={id} filterUnits="userSpaceOnUse" x={-40} y={-40} width={1280} height={580} colorInterpolationFilters="sRGB">
      <feColorMatrix type="matrix" values="0.2126 0.7152 0.0722 0 0  0.2126 0.7152 0.0722 0 0  0.2126 0.7152 0.0722 0 0  0 0 0 1 0" />
      <feComponentTransfer>
        <feFuncR type="discrete" tableValues="0 0 1" />
        <feFuncG type="discrete" tableValues="0 0 1" />
        <feFuncB type="discrete" tableValues="0 0 1" />
      </feComponentTransfer>
      <feComponentTransfer>
        <feFuncR {...ch(0)} />
        <feFuncG {...ch(1)} />
        <feFuncB {...ch(2)} />
      </feComponentTransfer>
    </filter>
  );
};
