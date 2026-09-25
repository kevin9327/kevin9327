/**
 * Pure geometry (no React, no remotion): the single source of truth for character transforms and eye geometry.
 * characters.tsx draws its eyes with these functions and src/droste/portals.ts fits portal clips with them,
 * so drawing and portal geometry cannot drift apart.
 */

export type Arms = 'idle' | 'run' | 'up' | 'grab' | 'draw' | 'proud' | 'wave' | 'hold';
export type Mood = 'smile' | 'o' | 'grin' | 'determined' | 'proud';

/** SVG matrix(a b c d e f): (x, y) -> (a x + c y + e, b x + d y + f). */
export type Mat = [number, number, number, number, number, number];

export type HeroPose = {
  x: number;
  y: number;
  s?: number;
  dir?: 1 | -1;
  lean?: number;
  squash?: number;
  look?: number;
  lookUp?: number;
  eyes?: number;
  blink?: boolean;
  wink?: 'L' | 'R';
  mood?: Mood;
  arms?: Arms;
};

export type BugPose = {
  x: number;
  y: number;
  s?: number;
  dir?: 1 | -1;
  rot?: number;
  stretch?: number;
  eyes?: number;
  pupil?: number;
  gaze?: [number, number];
  antenna?: number;
  run?: number | null;
};

export type EllipseClip = {kind: 'ellipse'; cx: number; cy: number; rx: number; ry: number; rot: number};

const DEG = Math.PI / 180;

export const MAT_ID: Mat = [1, 0, 0, 1, 0, 0];

/** a . b (apply b first, then a) */
export const matMul = (a: Mat, b: Mat): Mat => [
  a[0] * b[0] + a[2] * b[1],
  a[1] * b[0] + a[3] * b[1],
  a[0] * b[2] + a[2] * b[3],
  a[1] * b[2] + a[3] * b[3],
  a[0] * b[4] + a[2] * b[5] + a[4],
  a[1] * b[4] + a[3] * b[5] + a[5],
];

export const matApply = (m: Mat, p: [number, number]): [number, number] => [
  m[0] * p[0] + m[2] * p[1] + m[4],
  m[1] * p[0] + m[3] * p[1] + m[5],
];

export const matInv = (m: Mat): Mat => {
  const det = m[0] * m[3] - m[1] * m[2];
  const a = m[3] / det;
  const b = -m[1] / det;
  const c = -m[2] / det;
  const d = m[0] / det;
  return [a, b, c, d, -(a * m[4] + c * m[5]), -(b * m[4] + d * m[5])];
};

export const matTranslate = (x: number, y: number): Mat => [1, 0, 0, 1, x, y];
export const matScale = (sx: number, sy: number): Mat => [sx, 0, 0, sy, 0, 0];
export const matRotate = (deg: number): Mat => {
  const c = Math.cos(deg * DEG);
  const s = Math.sin(deg * DEG);
  return [c, s, -s, c, 0, 0];
};
export const matStr = (m: Mat) => `matrix(${m[0]} ${m[1]} ${m[2]} ${m[3]} ${m[4]} ${m[5]})`;

const chain = (...ms: Mat[]) => ms.reduce((acc, m) => matMul(acc, m), MAT_ID);

/* ------------------------------------------------------------------ Hero */

const heroSq = (p: HeroPose) => Math.max(0.35, p.squash ?? 1);

/** translate(x y) scale(s*dir s) rotate(lean) translate(0 92*(1-sq)) scale(1/sqrt(sq) sq), exactly as <Hero> nests it. */
export const heroMatrix = (p: HeroPose): Mat => {
  const s = p.s ?? 1;
  const dir = p.dir ?? 1;
  const sq = heroSq(p);
  return chain(
    matTranslate(p.x, p.y),
    matScale(s * dir, s),
    matRotate(p.lean ?? 0),
    matTranslate(0, 92 * (1 - sq)),
    matScale(1 / Math.sqrt(sq), sq),
  );
};

/**
 * Eye in the Hero's innermost (squashed) frame. Arithmetic order mirrors the original characters.tsx code
 * so the emitted SVG numbers are bit-identical (ProfileReel regression gate).
 */
export const heroEyeLocal = (
  p: Pick<HeroPose, 'look' | 'lookUp' | 'eyes'>,
  which: 'L' | 'R',
): {cx: number; cy: number; rx: number; ry: number; wedge: string} => {
  const base = which === 'L' ? -13 : 13;
  const ex = (p.look ?? 0) * 6;
  const ey = -(p.lookUp ?? 0) * 5;
  const eyes = p.eyes ?? 1;
  const ry = 14 * eyes;
  const rx = 8 * eyes;
  return {
    cx: base + ex,
    cy: -18 + ey,
    rx,
    ry,
    wedge: `M ${base + ex + 1} ${-18 + ey - ry * 0.45} l ${rx * 0.9} ${-ry * 0.5} l 0 ${ry * 0.75} z`,
  };
};

/** Screen-space (parent level) ellipse of the Hero's eye. */
export const heroEyeWorld = (p: HeroPose, which: 'L' | 'R'): EllipseClip => {
  const e = heroEyeLocal(p, which);
  const s = p.s ?? 1;
  const dir = p.dir ?? 1;
  const sq = heroSq(p);
  const [cx, cy] = matApply(heroMatrix(p), [e.cx, e.cy]);
  return {kind: 'ellipse', cx, cy, rx: e.rx * s * (1 / Math.sqrt(sq)), ry: e.ry * s * sq, rot: dir * (p.lean ?? 0)};
};

/* ------------------------------------------------------------------- Bug */

/** translate(x y) scale(s*dir s) rotate(rot), then about the feet line y=40: translate(0 40) scale(1/sqrt(st) st) translate(0 -40). */
export const bugMatrix = (p: BugPose): Mat => {
  const s = p.s ?? 1;
  const dir = p.dir ?? 1;
  const st = p.stretch ?? 1;
  return chain(
    matTranslate(p.x, p.y),
    matScale(s * dir, s),
    matRotate(p.rot ?? 0),
    matTranslate(0, 40),
    matScale(1 / Math.sqrt(st), st),
    matTranslate(0, -40),
  );
};

export const BUG_GAZE: [number, number] = [1.5, 0.5];

/** Eye white (cx, cy, r) and pupil (px, py, pr) in the Bug's local frame. Defaults reproduce 32/43, -11, 5.5 and 33.5/44.5, -10.5, 2.6. */
export const bugEyeLocal = (
  p: Pick<BugPose, 'eyes' | 'pupil' | 'gaze'>,
  which: 'L' | 'R',
): {cx: number; cy: number; r: number; px: number; py: number; pr: number} => {
  const eyes = p.eyes ?? 1;
  const g = p.gaze ?? BUG_GAZE;
  const cx = which === 'L' ? 32 : 43;
  const cy = -11;
  return {cx, cy, r: 5.5 * eyes, px: cx + g[0] * eyes, py: cy + g[1] * eyes, pr: 2.6 * (p.pupil ?? 1)};
};

/** Screen-space (parent level) ellipse of the Bug's eye WHITE. */
export const bugEyeWorld = (p: BugPose, which: 'L' | 'R'): EllipseClip => {
  const e = bugEyeLocal(p, which);
  const s = p.s ?? 1;
  const dir = p.dir ?? 1;
  const st = p.stretch ?? 1;
  const [cx, cy] = matApply(bugMatrix(p), [e.cx, e.cy]);
  return {kind: 'ellipse', cx, cy, rx: e.r * s * (1 / Math.sqrt(st)), ry: e.r * s * st, rot: dir * (p.rot ?? 0)};
};
