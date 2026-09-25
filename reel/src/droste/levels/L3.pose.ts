/**
 * L3 (merge garden) clocks. Pure: imports only anim, timeline and types (no React, no remotion), so the camera
 * and the lint can run it in Node.
 *
 * Everything L3 draws is a function of the L3 clock g = min(f, L3_FREEZE). From f286 (the start of Dive D1)
 * nothing in L3 changes, which keeps the silence beat (f314-331) bit-identical.
 */
import {back, lerpc, pop30} from '../anim';
import {DATA, EV, RING, SEGN, loopF} from '../timeline';
import type {Clip} from '../types';

/** From this frame on L3 is frozen (all blooms, the counter pop and the ring have landed). */
export const L3_FREEZE = SEGN.diveD1.f0;

/** The L3 clock: the loop frame, frozen at L3_FREEZE. */
export const l3Clock = (f: number) => Math.min(loopF(f), L3_FREEZE);

/**
 * Head clock d(f), in day index 0..DATA.days:
 * - f < write0: 0
 * - write0..plateau[0]: 0 -> 21 linear
 * - plateau: 21 -> 31 linear (the real Aug 9-18 stall; no blooms because the deltas are 0)
 * - crescendo: 31 -> 69 ease-in u^2 (September)
 * - from ring[0]: 69
 */
export function l3Day(f: number): number {
  const g = loopF(f);
  if (g < EV.write0) return 0;
  if (g < EV.plateau[0]) return lerpc(g, [EV.write0, EV.plateau[0]], [0, 21]);
  if (g < EV.plateau[1]) return lerpc(g, EV.plateau, [21, 31]);
  if (g < EV.crescendo[1]) return lerpc(g, EV.crescendo, [31, DATA.days], (u) => u * u);
  return DATA.days;
}

/** Merged total at fractional day d: linear interpolation of the real series totals. */
export const l3Value = (d: number) => {
  const i = Math.max(0, Math.min(DATA.days, Math.floor(d)));
  const j = Math.min(DATA.days, i + 1);
  const a = DATA.series[i].total;
  return a + (DATA.series[j].total - a) * (d - i);
};

/** Counter value v(f): 0 before the write-on starts, else the series total at d(f). */
export const l3Count = (f: number) => (loopF(f) < EV.write0 ? 0 : l3Value(l3Day(f)));

/**
 * Odometer wheel positions [hundreds, tens, ones] (continuous; digit = floor(p) mod 10, rolling by frac(p)).
 * ones = v mod 10; tens = floor(v/10) + max(0, (v mod 10) - 9); hundreds = floor(v/100) + max(0, (v mod 100) - 99).
 */
export const odometer = (v: number): [number, number, number] => {
  const ones = v % 10;
  const tens = Math.floor(v / 10) + Math.max(0, (v % 10) - 9);
  const hundreds = Math.floor(v / 100) + Math.max(0, (v % 100) - 99);
  return [hundreds, tens, ones];
};

/** The honest 108 stall: the counter is gray while 21 < d < 32. */
export const l3Stalled = (f: number) => {
  const d = l3Day(f);
  return d > 21 && d < 32;
};

/** First even frame with d(f) >= i (the frame the head passes day i). */
const tDayOf = (i: number) => {
  for (let f = EV.write0; f <= EV.crescendo[1]; f += 2) if (l3Day(f) >= i) return f;
  return EV.crescendo[1];
};
/** Bloom frame per day index (every day, including zero-delta days). */
export const BLOOM_AT: number[] = DATA.deltas.map((_, i) => tDayOf(i));

/**
 * Bloom scale of day i: pop30(f, tDay(i), 10, 200) (0 at tDay, overshoots, settles). Blooms that land in the
 * last frames of the crescendo cannot settle before the freeze, so over EV.ring the spring is blended onto its
 * rest value and is exactly 1 from L3_FREEZE (all petals bloomed, nothing moves in the silence beat).
 */
export const l3Bloom = (f: number, i: number) => {
  const g = l3Clock(f);
  const t0 = BLOOM_AT[i];
  if (g < t0) return 0;
  if (g >= L3_FREEZE) return 1;
  const p = pop30(g, t0, 10, 200);
  const w = lerpc(g, EV.ring, [0, 1]);
  return p + (1 - p) * w;
};

/** HEAD ring radius: 0 -> 22 with back ease over EV.ring, exactly RING.r from f286. */
export function l3RingR(f: number): number {
  return lerpc(l3Clock(f), EV.ring, [0, RING.r], back);
}

/**
 * Counter pop: scale 1.15 -> 1 from EV.ring[0] (pop30, a stiff spring so it has landed by the freeze);
 * exactly 1 from L3_FREEZE.
 */
export const l3CounterScale = (f: number) => {
  const g = l3Clock(f);
  if (g < EV.ring[0] || g >= L3_FREEZE) return 1;
  return 1.15 - 0.15 * pop30(g, EV.ring[0], 30, 1200);
};

/** Portal D = the ring interior on f282-353 (it equals CLIP[3] from f286); null otherwise (and while r = 0). */
export function l3PortalClip(f: number): Clip | null {
  const g = loopF(f);
  if (g < EV.ring[0] || g >= SEGN.diveD2.f1) return null;
  const r = l3RingR(g);
  if (r <= 0) return null;
  return {kind: 'ellipse', cx: RING.cx, cy: RING.cy, rx: r, ry: r, rot: 0};
}
