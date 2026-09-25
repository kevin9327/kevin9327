/** Pure, dependency-free animation helpers (no remotion import), so pose files and the lint run in Node. */

const T_LOOP = 384;

export const clamp01 = (x: number) => (x < 0 ? 0 : x > 1 ? 1 : x);

/** Cubic easings matching remotion Easing.out/in/inOut(Easing.cubic). */
export const ei = (t: number) => t * t * t;
export const eo = (t: number) => 1 - (1 - t) * (1 - t) * (1 - t);
export const eio = (t: number) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);
/** Easing.out(Easing.back(o)): overshoots then settles on 1. */
export const back = (t: number, o = 1.8) => {
  const u = 1 - t;
  return 1 - u * u * ((o + 1) * u - o);
};
export const smoothstep = (x: number) => {
  const t = clamp01(x);
  return t * t * (3 - 2 * t);
};

/**
 * Clamped piecewise-linear interpolation (like remotion interpolate with clamp on both ends);
 * `ease` is applied to each segment's local t.
 */
export const lerpc = (f: number, ins: number[], outs: number[], ease?: (t: number) => number) => {
  if (ins.length !== outs.length || ins.length < 2) throw new Error('lerpc: ins/outs length mismatch');
  if (f <= ins[0]) return outs[0];
  const n = ins.length - 1;
  if (f >= ins[n]) return outs[n];
  let i = 0;
  while (i < n - 1 && f >= ins[i + 1]) i++;
  const span = ins[i + 1] - ins[i];
  let t = span === 0 ? 1 : (f - ins[i]) / span;
  if (ease) t = ease(t);
  return outs[i] + (outs[i + 1] - outs[i]) * t;
};

/**
 * Stateless spring 0 -> 1 (overshoots). Re-integrates semi-implicit Euler at dt 1/30 per frame
 * (4 sub-steps per frame for accuracy) from `at` up to f, capped at 120 frames. 0 when f < at.
 * Deterministic under out-of-order rendering.
 */
export const pop30 = (f: number, at: number, damping = 9, stiffness = 180, mass = 0.6) => {
  if (f < at) return 0;
  const n = Math.min(120, Math.floor(f - at));
  const SUB = 4;
  const dt = 1 / 30 / SUB;
  let x = 0;
  let v = 0;
  for (let i = 0; i < n * SUB; i++) {
    const a = (-stiffness * (x - 1) - damping * v) / mass;
    v += a * dt;
    x += v * dt;
  }
  return x;
};

const wrapT = (t: number) => ((t % T_LOOP) + T_LOOP) % T_LOOP;

/**
 * Follow-through: a damped follower chasing target(t), re-integrated over the last `win` frames
 * of WRAPPED time, so it is stateless and periodic in T. Starts at rest on target(f - win).
 */
export const springAt = (f: number, target: (t: number) => number, k = 0.25, damp = 0.35, win = 48) => {
  const t0 = f - win;
  let x = target(wrapT(t0));
  let v = 0;
  for (let t = t0 + 1; t <= f; t++) {
    const a = k * (target(wrapT(t)) - x) - damp * v;
    v += a;
    x += v;
  }
  return x;
};

/**
 * Hit-stop character clock. During [at, at+len) the clock is frozen on the pose of frame at-1;
 * afterwards the clock runs len frames behind. Holds must be sorted and non-overlapping.
 */
export const hitStop = (f: number, holds: {at: number; len: number}[]) => {
  let lost = 0;
  for (const h of holds) {
    if (f >= h.at) lost += Math.min(h.len, f - h.at + 1);
  }
  return f - lost;
};

export const onTwos = (f: number) => f - (((f % 2) + 2) % 2);

/** Level-of-detail fade: 0 below lo, 1 above hi, smoothstep between. */
export const lod = (v: number, lo: number, hi: number) => smoothstep((v - lo) / (hi - lo));

const hex2 = (h: string) => {
  const s = h.replace('#', '');
  return [parseInt(s.slice(0, 2), 16), parseInt(s.slice(2, 4), 16), parseInt(s.slice(4, 6), 16)];
};
/** Mix two #rrggbb colours; t clamped to 0..1. */
export const mixHex = (a: string, b: string, t: number) => {
  const u = clamp01(t);
  const A = hex2(a);
  const B = hex2(b);
  return (
    '#' +
    A.map((v, i) => Math.round(v + (B[i] - v) * u).toString(16).padStart(2, '0')).join('')
  );
};

/** Deterministic hash noise in [0,1) (same hash as theme.ts rnd). */
export const rnd = (n: number) => {
  const x = Math.sin(n * 127.1 + 311.7) * 43758.5453;
  return x - Math.floor(x);
};
