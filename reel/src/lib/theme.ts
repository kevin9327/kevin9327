import {loadFont as loadCartoon} from '@remotion/google-fonts/LuckiestGuy';
import {loadFont as loadMono} from '@remotion/google-fonts/JetBrainsMono';
import {loadFont as loadHand} from '@remotion/google-fonts/PermanentMarker';
import {Easing, interpolate, spring} from 'remotion';
import {C} from './palette';

export const F = {
  cartoon: loadCartoon('normal', {subsets: ['latin']}).fontFamily,
  mono: loadMono('normal', {weights: ['400', '700'], subsets: ['latin']}).fontFamily,
  hand: loadHand('normal', {subsets: ['latin']}).fontFamily,
};

export {C};

export const W = 1920;
export const H = 1080;
export const FPS = 30;

export const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;

export const lerp = (f: number, input: number[], output: number[], easing?: (t: number) => number) =>
  interpolate(f, input, output, {...clamp, easing});

export const eo = Easing.out(Easing.cubic);
export const ei = Easing.in(Easing.cubic);
export const eio = Easing.inOut(Easing.cubic);
export const back = Easing.out(Easing.back(1.8));

export const pop = (f: number, at: number, damping = 9, stiffness = 180) =>
  spring({frame: f - at, fps: FPS, config: {damping, stiffness, mass: 0.6}});

/** Deterministic hash noise in [0,1). */
export const rnd = (n: number) => {
  const x = Math.sin(n * 127.1 + 311.7) * 43758.5453;
  return x - Math.floor(x);
};

/** Small per-frame jitter that changes every `hold` frames: the "boil" of hand-drawn animation. */
export const jit = (f: number, key: number, amp: number, hold = 3) => (rnd(Math.floor(f / hold) * 13.37 + key) - 0.5) * 2 * amp;

const widthCache = new Map<string, number>();
let measureCtx: CanvasRenderingContext2D | null = null;
/** Real advance width of `text` in a loaded web font (falls back to 0.6em per char until the font is ready). */
export const measure = (text: string, font: string, size: number) => {
  const key = `${font}|${size}|${text}`;
  const hit = widthCache.get(key);
  if (hit !== undefined) return hit;
  if (typeof document === 'undefined') return text.length * size * 0.6;
  measureCtx = measureCtx ?? document.createElement('canvas').getContext('2d');
  if (!measureCtx) return text.length * size * 0.6;
  measureCtx.font = `${size}px "${font}"`;
  const w = measureCtx.measureText(text).width;
  if (document.fonts.check(measureCtx.font)) widthCache.set(key, w);
  return w;
};

/** x offsets of each character of `text` laid out from x0. */
export const charXs = (text: string, font: string, size: number, x0 = 0) => {
  const xs: number[] = [];
  let x = x0;
  for (const ch of text) {
    xs.push(x);
    x += measure(ch, font, size);
  }
  return {xs, width: x - x0};
};

/** Rubber-hose limb: quadratic curve bowed sideways by `bend`. */
export const hose = (x1: number, y1: number, x2: number, y2: number, bend: number) => {
  const mx = (x1 + x2) / 2;
  const my = (y1 + y2) / 2;
  const dx = x2 - x1;
  const dy = y2 - y1;
  const len = Math.hypot(dx, dy) || 1;
  const cx = mx - (dy / len) * bend;
  const cy = my + (dx / len) * bend;
  return `M ${x1} ${y1} Q ${cx} ${cy} ${x2} ${y2}`;
};
