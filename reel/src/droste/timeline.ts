/** The single timing and data source for "535, All the Way Down". Pure: no React, no remotion. */
import {C} from '../lib/palette';
import data from '../data.json';

export const T = 384;
export const FPS = 30;
export const OUT_STEP = 2;
export const W = 1200;
export const H = 500;

export type Seg = {n: string; f0: number; f1: number; D0: number; D1: number};

// Keep one segment per line in this exact shape: scripts/droste_webp.py parses it.
export const SEG: Seg[] = [
  {n: 'L0open', f0: 0, f1: 18, D0: 0, D1: 0},
  {n: 'diveA', f0: 18, f1: 72, D0: 0, D1: 1},
  {n: 'L1', f0: 72, f1: 106, D0: 1, D1: 1},
  {n: 'diveB', f0: 106, f1: 152, D0: 1, D1: 2},
  {n: 'L2', f0: 152, f1: 204, D0: 2, D1: 2},
  {n: 'diveC', f0: 204, f1: 236, D0: 2, D1: 3},
  {n: 'L3', f0: 236, f1: 286, D0: 3, D1: 3},
  {n: 'diveD1', f0: 286, f1: 314, D0: 3, D1: 3.6},
  {n: 'silence', f0: 314, f1: 332, D0: 3.6, D1: 3.6},
  {n: 'diveD2', f0: 332, f1: 354, D0: 3.6, D1: 4},
  {n: 'L0close', f0: 354, f1: 384, D0: 4, D1: 4},
];

/** Segments by name, e.g. SEGN.diveB.f1 === 152. */
export const SEGN: Record<string, Seg> = Object.fromEntries(SEG.map((s) => [s.n, s]));

/** Event frames (all even). Single numbers are instants; pairs are [start, end) windows. */
export const EV = {
  take: 10,
  settleA: 12,
  freezeA: 18,
  bites: [38, 46, 54, 62, 70, 78, 86],
  type3: [72, 86] as [number, number],
  type4: [86, 92] as [number, number],
  caught: 92,
  anticip: 96,
  takeB: 100,
  settleB: 102,
  freezeB: 106,
  cascade: [156, 184] as [number, number],
  slam: 188,
  impact: [188, 190] as [number, number],
  glint: [192, 204] as [number, number],
  write0: 238,
  plateau: [252, 264] as [number, number],
  crescendo: [264, 282] as [number, number],
  ring: [282, 286] as [number, number],
  hand: [244, 266] as [number, number],
  blink: [322, 326] as [number, number],
  lookDown: [356, 360] as [number, number],
  grin: [360, 368] as [number, number],
  wink: [362, 368] as [number, number],
  drowsy: [368, 370] as [number, number],
  sleep: 370,
};

/** Portal roll per level transition, degrees: A (L0->L1), B (L1->L2), C (L2->L3), D (L3->L0). */
export const THETA = [-8, 10, 0, -6];
export const CENTER: [number, number] = [600, 250];
export const HEX_R = 72;
export const RING = {cx: 1120, cy: 330, r: 22, stroke: 4};
/** Colour each level shows at tiny px (= the parent's pupil colour). */
export const STUB = [C.night, C.night, C.cream, C.night];

export const loopF = (frame: number) => ((frame % T) + T) % T;

/* ------------------------------------------------------------------ DATA */

type SeriesPt = {date: string; total: number};
type RepoRow = {repo: string; merged: number};

const series = (data as {series: SeriesPt[]}).series;
const all = (data as {all: RepoRow[]}).all;
const deltas = series.map((p, i) => (i === 0 ? p.total : p.total - series[i - 1].total));

export const DATA = {
  total: data.total as number,
  repos: data.repos as number,
  days: data.days as number,
  start: data.start as string,
  end: data.end as string,
  series,
  all,
  deltas,
};

const sum = (xs: number[]) => xs.reduce((a, b) => a + b, 0);
const guard = (ok: boolean, msg: string) => {
  if (!ok) throw new Error(`DATA guard failed: ${msg}`);
};
guard(sum(all.map((r) => r.merged)) === DATA.total, 'sum(all.merged) === total');
guard(sum(deltas) === DATA.total, 'sum(deltas) === total');
guard(series[series.length - 1].total === DATA.total, 'series[last].total === total');
guard(deltas.every((d) => d >= 0), 'deltas >= 0');
guard(all.length === DATA.repos, 'all.length === repos');
guard(series.length === DATA.days + 1, 'series.length === days + 1');
guard(series[0].date === DATA.start && series[series.length - 1].date === DATA.end, 'series spans start..end');

/* ---------------------------------------------------------------- FACETS */

export type Facet = {rank: number; repo: string; merged: number; q: number; r: number; x: number; y: number; tOn: number; named: boolean};

/** Flat-top axial cell centre, R = HEX_R. */
export const hexCenter = (q: number, r: number): [number, number] => [
  CENTER[0] + 1.5 * HEX_R * q,
  CENTER[1] + Math.sqrt(3) * HEX_R * (r + q / 2),
];

const facetCells = (() => {
  const cells: {q: number; r: number; x: number; y: number; d: number; a: number}[] = [];
  for (let q = -8; q <= 8; q++) {
    for (let r = -8; r <= 8; r++) {
      if (q === 0 && r === 0) continue;
      const [x, y] = hexCenter(q, r);
      if (x < 36 || x > 1164 || y < 36 || y > 464) continue;
      const d = Math.round(Math.hypot((x - CENTER[0]) / 1.6, y - CENTER[1]) * 1000) / 1000;
      cells.push({q, r, x, y, d, a: Math.atan2(y - CENTER[1], x - CENTER[0])});
    }
  }
  cells.sort((p, q2) => p.d - q2.d || p.a - q2.a);
  return cells;
})();

guard(facetCells.length >= DATA.repos, 'enough facet cells');

export const FACETS: Facet[] = all.map((row, i) => {
  const rank = i + 1;
  const cell = facetCells[i];
  return {
    rank,
    repo: row.repo,
    merged: row.merged,
    q: cell.q,
    r: cell.r,
    x: cell.x,
    y: cell.y,
    tOn: 156 + 2 * Math.round(14 * Math.sqrt((rank - 1) / 31)),
    named: rank <= 10,
  };
});

const MON = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC'];
/** '2026-07-18' -> 'JUL 18' */
export const fmtDate = (iso: string) => {
  const [, m, d] = iso.split('-').map(Number);
  return `${MON[m - 1]} ${d}`;
};

/** Segment containing loop frame f. */
export const segAt = (f: number) => {
  const g = loopF(f);
  return SEG.find((s) => g >= s.f0 && g < s.f1) ?? SEG[SEG.length - 1];
};
