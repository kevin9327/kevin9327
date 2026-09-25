/**
 * L1 "caught red-handed": pose table for the Bug plus the diff's typing / eating state. PURE (no React, no remotion):
 * imports only lib/geom, lib/palette, droste/anim, droste/portals, droste/timeline and droste/types, so camera.ts
 * and the lint can run it in Node.
 *
 * Window (global loop frames): MUNCH [bites[0]-2, caught), CAUGHT hit-stop [caught, anticip), ANTICIPATION
 * [anticip, takeB), TAKE SMEAR [takeB, settleB), SETTLE [settleB, freezeB), FREEZE [freezeB, diveB.f1).
 * Everywhere else: the rest pose (MUNCH at bite 0, nothing eaten, nothing typed).
 */
import {BUG_GAZE, bugMatrix, matApply} from '../../lib/geom';
import type {BugPose} from '../../lib/geom';
import {C} from '../../lib/palette';
import {back, eo, hitStop, lerpc, pop30, rnd, springAt} from '../anim';
import {CLIP, FREEZE_L1} from '../portals';
import {EV, SEGN, loopF} from '../timeline';
import type {Clip} from '../types';

export type L1Pose = BugPose & {hideEye?: 'R'; typed3: number; typed4: number; eaten: number; bang: number};

/* ------------------------------------------------------------ diff layout */

export const CODE_X = 130;
/** JetBrains Mono advance = 0.6 em; code is 36 u. */
export const ADV = 21.6;
export const BASE_Y = [110, 180, 250, 320, 390];
export const INDENT = 2;
export const SHIP = 'ship(pr);';
export const REVIEW = 'await review(pr);';
export const MERGE = 'await merge(pr);';

/** x of the right edge of an indented code line holding n characters (after the indent). */
export const lineEnd = (n: number) => CODE_X + (INDENT + n) * ADV;

/* --------------------------------------------------------------- timing */

const BITE = EV.bites[1] - EV.bites[0];
/** First bite cycle starts 2 frames (the anticipation) before the first bite lands. */
const W0 = EV.bites[0] - 2;
const W1 = SEGN.diveB.f1;
const inWin = (g: number) => g >= W0 && g < W1;

const MUNCH = {y: 172, s: 1.4, off: 46, lunge: 14};

/** Characters of 'ship(pr);' eaten by frame g (one per EV.bites frame, from the right). */
export const eatenAt = (g: number) => (inWin(g) ? EV.bites.filter((b) => b <= g).length : 0);

const typedIn = (g: number, w: [number, number], n: number) =>
  !inWin(g) || g < w[0] ? 0 : g >= w[1] ? n : Math.min(n, Math.floor(((g - w[0]) * n) / (w[1] - w[0])));

/** Caret: [line index, character column after the indent] while typing, else null. */
export const l1Caret = (f: number): [number, number] | null => {
  const g = loopF(f);
  if (g >= EV.type3[0] && g < EV.type3[1]) return [2, typedIn(g, EV.type3, REVIEW.length)];
  if (g >= EV.type4[0] && g < EV.type4[1]) return [3, typedIn(g, EV.type4, MERGE.length)];
  return null;
};

/* ---------------------------------------------------------------- munch */

const munchX = (eaten: number) => lineEnd(SHIP.length - eaten) + MUNCH.off;

/** Antenna target during the munch (deg): swept back in the anticipation, flung forward by the lunge. */
const antTarget = (t: number) => {
  if (t < W0 || t >= EV.caught) return 0;
  const p = (t - W0) % BITE;
  return p < 2 ? -15 : p < 4 ? 20 : 0;
};
/** Stateless-spring follow-through on the antenna (lags the body by about a frame, overshoots). */
const munchAntenna = (c: number) => springAt(c, antTarget, 0.5, 0.45, 24);

/** Munch pose on the (hit-stopped) character clock c in [W0, caught). */
const munchPose = (c: number): BugPose => {
  const p = (c - W0) % BITE;
  const x = munchX(eatenAt(c));
  const base: BugPose = {x, y: MUNCH.y, s: MUNCH.s, dir: -1, rot: 0, stretch: 1, eyes: 1, pupil: 1, gaze: BUG_GAZE, antenna: munchAntenna(c), run: null};
  if (p < 2) return {...base, rot: 10, stretch: 0.9};
  if (p < 4) return {...base, x: x - MUNCH.lunge, rot: -4, stretch: 1.15};
  return {...base, stretch: p < 6 ? 0.94 : 1.04};
};

/** The rest pose (MUNCH at bite 0, nothing eaten): everywhere outside the window. */
const REST: L1Pose = {
  x: munchX(0), y: MUNCH.y, s: MUNCH.s, dir: -1, rot: 0, stretch: 1, eyes: 1, pupil: 1, gaze: BUG_GAZE, antenna: 0, run: null,
  typed3: 0, typed4: 0, eaten: 0, bang: 0,
};

/* ----------------------------------------------------- caught .. freeze */

const HOLD = [{at: EV.caught, len: EV.anticip - EV.caught}];
/** Antenna twang: an impulse at `caught`, stateless spring (k 1.6, damp 0.3) -> +25, -17, +12, -8 deg on the even frames. */
const TWANG_K = 1.6;
const twang = (g: number) => springAt(g, (t) => (t >= EV.caught && t < EV.caught + 1 ? 25 / TWANG_K : 0), TWANG_K, 0.3, 16);

const ANTIC_X = munchX(EV.bites.length);
const antic = (g: number): BugPose => ({
  x: ANTIC_X, y: MUNCH.y, s: MUNCH.s, dir: 1, rot: -6, stretch: 0.72, eyes: 0.8, pupil: 1, gaze: [0.6, 0.2],
  antenna: munchAntenna(EV.caught - 1) + twang(g), run: null,
});

const FZ = FREEZE_L1;
const TAKE_T = 0.6;
const TAKE: BugPose = {
  x: ANTIC_X + (FZ.x - ANTIC_X) * TAKE_T,
  y: MUNCH.y + (FZ.y - MUNCH.y) * TAKE_T,
  s: 3.4, dir: 1, rot: 0, stretch: 1.3, eyes: 1.6, pupil: 0.2, gaze: [0, 0], antenna: 30, run: null,
};

const settle = (g: number): BugPose => {
  // t runs 0 at the last smear frame (takeB+1) .. 1 at freezeB.
  const a = EV.settleB - 1;
  const t = (g - a) / (EV.freezeB - a);
  const k = eo(t);
  const L = (from: number, to: number, e: number) => from + (to - from) * e;
  return {
    x: L(TAKE.x, FZ.x, k),
    y: L(TAKE.y, FZ.y, k),
    s: L(TAKE.s!, FZ.s!, back(t, 2.2)),
    dir: 1,
    rot: 0,
    stretch: lerpc(g, [a, EV.settleB, EV.settleB + 2, EV.freezeB], [TAKE.stretch!, 0.93, 1.03, FZ.stretch!]),
    eyes: L(TAKE.eyes!, FZ.eyes!, k),
    pupil: L(TAKE.pupil!, FZ.pupil!, k),
    gaze: [0, 0],
    antenna: lerpc(g, [a, EV.settleB, EV.settleB + 2, EV.freezeB], [TAKE.antenna!, -14, 6, FZ.antenna!]),
    run: null,
  };
};

/* ----------------------------------------------------------------- pose */

export function l1Pose(f: number): L1Pose {
  const g = loopF(f);
  if (!inWin(g) || g < W0) return REST;
  const eaten = eatenAt(g);
  const typed3 = typedIn(g, EV.type3, REVIEW.length);
  const typed4 = typedIn(g, EV.type4, MERGE.length);
  // The '!' is already 3 frames into its pop on the hit-stop frame, so it reads at full size on output frame caught/2.
  const bang = g >= EV.caught && g < EV.takeB ? pop30(g, EV.caught - 3) : 0;
  const extra = {typed3, typed4, eaten, bang};
  if (g >= EV.freezeB) return {...FREEZE_L1, hideEye: 'R', ...extra};
  if (g >= EV.settleB) return {...settle(g), ...extra};
  if (g >= EV.takeB) return {...TAKE, ...extra};
  if (g >= EV.anticip) return {...antic(g), ...extra};
  const c = hitStop(g, HOLD);
  const pose = munchPose(c);
  if (g >= EV.caught) return {...pose, antenna: (pose.antenna ?? 0) + twang(g), ...extra};
  return {...pose, ...extra};
}

/** Portal B (the Bug's right eye white) on [freezeB, diveB.f1); null otherwise. Equals CLIP[1]. */
export function l1PortalClip(f: number): Clip | null {
  const g = loopF(f);
  return g >= EV.freezeB && g < W1 ? CLIP[1] : null;
}

/* ------------------------------------------------------ effects (pure) */

type P2 = [number, number];

/** Silhouette key points (body ellipse + head circle, outline included) of a pose, in level coordinates. */
export const bugHullPts = (p: BugPose): P2[] => {
  const M = bugMatrix(p);
  const pts: P2[] = [];
  for (let i = 0; i < 16; i++) {
    const a = (i / 16) * Math.PI * 2;
    pts.push(matApply(M, [38.75 * Math.cos(a), 27.75 * Math.sin(a)]));
  }
  for (let i = 0; i < 12; i++) {
    const a = (i / 12) * Math.PI * 2;
    pts.push(matApply(M, [36 + 18.5 * Math.cos(a), -6 + 18.5 * Math.sin(a)]));
  }
  return pts;
};

/** Smear frames: the bite lunges (phase 2-3 of each cycle) and the take (takeB, 2 frames). */
export const l1Smear = (f: number): {from: BugPose; to: BugPose; speed: boolean} | null => {
  const g = loopF(f);
  if (g >= EV.takeB && g < EV.settleB) return {from: antic(EV.takeB - 1), to: TAKE, speed: true};
  if (g < W0 || g >= EV.caught) return null;
  const p = (g - W0) % BITE;
  if (p < 2 || p >= 4) return null;
  return {from: munchPose(g - p + 1), to: munchPose(g), speed: false};
};

/** Bite anticipation (phases 0-1 of each munch cycle): the jaws are open, so the lunge reads as a chomp. */
export const l1MouthOpen = (f: number) => {
  const g = loopF(f);
  return g >= W0 && g < EV.caught && (g - W0) % BITE < 2;
};

/** The Bug's mouth (level coordinates) in a pose. */
export const bugMouth = (p: BugPose): P2 => matApply(bugMatrix(p), [40, 0]);

export type Crumb = {x: number; y: number; size: number; rot: number; color: string};
/** Crumb square size (u). */
const CRUMB = 6;

/**
 * Chew crumbs: 3 per bite, on ballistic arcs from the mouth at the bite frame, visible in chew phases 4-7.
 * On the hit-stop clock, so the last bite's crumbs hang frozen in the air during the CAUGHT hold.
 */
export const l1Crumbs = (f: number): Crumb[] => {
  const g = loopF(f);
  if (g < W0 || g >= EV.anticip) return [];
  const c = hitStop(g, HOLD);
  const p = (c - W0) % BITE;
  if (p < 4) return [];
  const bite = Math.floor((c - W0) / BITE);
  const m = bugMouth(munchPose(EV.bites[bite]));
  const tau = p - 1;
  return [0, 1, 2].map((j) => {
    const r1 = rnd(bite * 7 + j);
    const r2 = rnd(bite * 7 + j + 0.37);
    // Spray fan out of the mouth, forward (the Bug faces -x while munching) and up, clear of its own red head,
    // so the crumbs read against the band and the night; all fall under gravity.
    const vx = [-3, -6, -8.5][j] + 2 * (r1 - 0.5);
    const vy = [-10.5, -8, -4.5][j] + 2 * (r2 - 0.5);
    return {
      x: m[0] + vx * tau,
      y: m[1] + vy * tau + 0.5 * 2.2 * tau * tau,
      size: CRUMB,
      rot: 90 * r1 + 40 * tau,
      color: j === 1 ? C.red : C.cream,
    };
  });
};
