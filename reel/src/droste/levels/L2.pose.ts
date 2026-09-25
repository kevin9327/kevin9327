/**
 * L2 (the Bug's compound eye): pure timing and geometry. No React, no remotion, no theme.ts.
 * Imported by camera.ts and the lint (Node), and by L2Eye.tsx / Cornea.tsx (browser).
 *
 * Every frame here is the GLOBAL loop frame f (0..383). L2 is only in the camera chain on f106..235
 * (inside the Bug's right eye during Dive B, at identity f152..203, zooming past during Dive C).
 */
import {C} from '../../lib/palette';
import {clamp01, eio, eo, lerpc, lod, pop30} from '../anim';
import {CLIP} from '../portals';
import type {Facet} from '../timeline';
import {CENTER, EV, FACETS, HEX_R, SEGN, hexCenter} from '../timeline';
import type {Clip} from '../types';

/** Portal C = the centre hex (600,250), R=72. Constant (the child L3 owns it for the whole window). */
export function l2PortalClip(_f: number): Clip {
  return CLIP[2];
}

/* ----------------------------------------------------------------- cells */

export type L2Cell = {q: number; r: number; x: number; y: number; centre: boolean; fc: Facet | null};

const facetAt = new Map<string, Facet>(FACETS.map((fc) => [fc.q + ',' + fc.r, fc]));

/** Every lattice cell whose centre is within 760 u of (600,250). */
export const L2_CELLS: L2Cell[] = (() => {
  const out: L2Cell[] = [];
  for (let q = -8; q <= 8; q++) {
    for (let r = -10; r <= 10; r++) {
      const [x, y] = hexCenter(q, r);
      if (Math.hypot(x - CENTER[0], y - CENTER[1]) > 760) continue;
      out.push({q, r, x, y, centre: q === 0 && r === 0, fc: facetAt.get(q + ',' + r) ?? null});
    }
  }
  return out;
})();

/** Cells whose hex can touch the level-space box [x0,y0,x1,y1] (a viewRect already padded by R). */
export const cellsIn = (box: [number, number, number, number]) =>
  L2_CELLS.filter((c) => c.x >= box[0] && c.x <= box[2] && c.y >= box[1] && c.y <= box[3]);

/** Flat-top hex vertices about (x, y), optionally squashed horizontally by sx (the flip). */
export const hexVerts = (x: number, y: number, R = HEX_R, sx = 1): [number, number][] =>
  Array.from({length: 6}, (_, i) => [x + sx * R * Math.cos((i * Math.PI) / 3), y + R * Math.sin((i * Math.PI) / 3)] as [number, number]);

export const polyD = (pts: [number, number][]) => 'M' + pts.map((p) => p[0].toFixed(3) + ' ' + p[1].toFixed(3)).join('L') + 'Z';

/* ----------------------------------------------------------------- state */

const RANK_COLORS = [C.green, C.blue, C.purple, C.orange];
/** Lit colour: ranks 1-8 cycle green / blue / purple / orange; ranks 9-32 paperShade. */
export const litColor = (fc: Facet) => (fc.rank <= 8 ? RANK_COLORS[(fc.rank - 1) % 4] : C.paperShade);

/** Frame after which nothing in L2 changes (the glint ends, Dive C starts). */
export const L2_FREEZE = SEGN.diveC.f0;

/**
 * Flip of a facet at frame f (about its centre, horizontally):
 * null = not lit yet (unlit paper); 0.15 = edge-on sliver [tOn, tOn+2); 1.12 = overshoot [tOn+2, tOn+4); 1 = lit.
 */
export const flipX = (f: number, fc: Facet): number | null => {
  const d = Math.min(f, L2_FREEZE) - fc.tOn;
  if (d < 0) return null;
  if (d < 2) return 0.15;
  if (d < 4) return 1.12;
  return 1;
};

/** Count-up shown on a facet: 0 at tOn+2, its real merged count by tOn+10 (ease-out). */
export const countUp = (f: number, fc: Facet) => Math.round(fc.merged * eo(clamp01((Math.min(f, L2_FREEZE) - fc.tOn - 2) / 8)));

/* ------------------------------------------------------------------ slam */

/**
 * The centre '535' pop (stateless spring, damping 8, stiffness 220), held at its f204 value afterwards (freeze).
 * The spring starts one output frame before EV.slam so the number is ON the impact frame (spec: pop30(f, 188) is
 * still 0 at f188, which flashed an empty frame), and the f198 legibility frame sits at 0.974 instead of the
 * 0.946 undershoot (72 px at 880 wide, under the 73 px gate).
 */
export const SLAM_T0 = EV.slam - 2;
export const slamT = (f: number) => pop30(Math.min(f, L2_FREEZE), SLAM_T0, 8, 220);
export const isImpact = (f: number) => f >= EV.impact[0] && f < EV.impact[1];
/** Centre-hex rim flash in green on f188..191. */
export const rimFlash = (f: number) => f >= EV.slam && f < EV.slam + 4;
/** 'merged · N repos' shows from two frames after the slam. */
export const sublineOn = (f: number) => f >= EV.slam + 2;

/* ------------------------------------------------------------------- LOD */

/** Stub -> lattice crossfade (circle -> hex, cream -> facet state). */
export const detailT = (px: number) => lod(px, 0.06, 0.12);
/** Groove opacity: 0.85 * crossfade * anti-shimmer. */
export const grooveA = (px: number) => 0.85 * detailT(px) * lod(3 * px, 0.6, 1.2);
/** Groove width in level units: 3 u, but never thinner than 1 screen px. */
export const grooveW = (px: number) => Math.max(3, 1 / Math.max(px, 1e-6));
/** Dive C: the '535' and the subline fade as L2 zooms past. */
export const overlayFade = (px: number) => 1 - lod(px, 1.4, 2.6);

/* ---------------------------------------------------------------- cornea */

/** Glint band position: resting at -0.4, sweeps to 1.4 (off frame) over EV.glint. */
export const sweep = (f: number) => (f < EV.glint[0] ? -0.4 : lerpc(Math.min(f, L2_FREEZE), EV.glint, [-0.4, 1.4], eio));
/**
 * Cornea opacity: in with LOD, out as L2 zooms past, hidden on the impact frame.
 * Fades in over px 0.3-0.5 (spec: 0.1-0.25) so it lands AFTER the grooves, which the anti-shimmer term
 * lod(3px, 0.6, 1.2) holds back to px 0.2-0.4; earlier, the highlights read as dust on a lattice-less disc.
 */
export const corneaFade = (f: number, px: number, impactOn: boolean) =>
  lod(px, 0.3, 0.5) * (1 - lod(px, 1.6, 2.4)) * (impactOn && isImpact(f) ? 0 : 1);

/** Cornea light, highlight thresholds and glint direction (shared by the GL shader and the SVG fallback). */
export const CORNEA = {
  light: [-0.5, -0.6, 0.62] as [number, number, number],
  glintDir: [1, -0.55] as [number, number],
  hi: 0.55,
  band: 0.22,
  color: '#fffaf0',
  hiA: 0.9,
  bandA: 0.35,
  glintA: 0.85,
};
