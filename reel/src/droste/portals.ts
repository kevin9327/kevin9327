/** The numeric portal contract between levels. Pure. */
import {bugEyeWorld, heroEyeWorld} from '../lib/geom';
import type {BugPose, HeroPose} from '../lib/geom';
import {CENTER, HEX_R, RING, THETA, W, H} from './timeline';
import type {Clip} from './types';

export type Cx = [number, number];

/** Flat-top regular hexagon (vertices at 0, 60, ... degrees). */
export const hexPoly = (cx: number, cy: number, R: number): Clip => ({
  kind: 'poly',
  pts: Array.from({length: 6}, (_, i) => [cx + R * Math.cos((i * Math.PI) / 3), cy + R * Math.sin((i * Math.PI) / 3)] as [number, number]),
});

/** L0 frozen pose during Dive A (f18-71): portal A = its right eye. */
export const FREEZE_L0: HeroPose = {x: 1000.8, y: 206, s: 0.975, dir: 1, eyes: 1.7, squash: 1, lean: 0, look: 0, lookUp: 0, blink: false, mood: 'o', arms: 'up'};

/**
 * L0 SLEEP pose: frames [370,384) and [0,10) (the seam). Eyes shut (blink), so portal A is closed.
 * The lint asserts l0Pose(370..383) and l0Pose(0..9) deep-equal this object.
 */
export const SLEEP_L0: HeroPose = {x: 1000.8, y: 206, s: 0.975, dir: 1, eyes: 1, squash: 1, lean: 0, look: 0, lookUp: 0, blink: true, mood: 'smile', arms: 'idle'};

const FREEZE_L1_BASE: BugPose = {x: 720, y: 262, s: 3, dir: 1, rot: 0, stretch: 1, eyes: 1.35, gaze: [0, 0], antenna: 0, run: null};

const clipCenter = (c: Clip): Cx => {
  if (c.kind === 'ellipse') return [c.cx, c.cy];
  const n = c.pts.length;
  return [c.pts.reduce((a, p) => a + p[0], 0) / n, c.pts.reduce((a, p) => a + p[1], 0) / n];
};

/** Gauge function of a convex clip about its centre: 1 on the boundary, <1 inside. v is relative to the centre. */
export const clipGauge = (c: Clip, v: Cx) => {
  if (c.kind === 'ellipse') {
    const r = (-c.rot * Math.PI) / 180;
    const x = v[0] * Math.cos(r) - v[1] * Math.sin(r);
    const y = v[0] * Math.sin(r) + v[1] * Math.cos(r);
    return Math.hypot(x / c.rx, y / c.ry);
  }
  const [cx, cy] = clipCenter(c);
  let g = 0;
  for (let i = 0; i < c.pts.length; i++) {
    const a = c.pts[i];
    const b = c.pts[(i + 1) % c.pts.length];
    let nx = b[1] - a[1];
    let ny = -(b[0] - a[0]);
    const len = Math.hypot(nx, ny);
    nx /= len;
    ny /= len;
    let d = nx * (a[0] - cx) + ny * (a[1] - cy);
    if (d < 0) {
      nx = -nx;
      ny = -ny;
      d = -d;
    }
    g = Math.max(g, (nx * v[0] + ny * v[1]) / d);
  }
  return g;
};

/** Smallest s (times margin) such that the child's 1200x500 frame, rotated by theta and scaled 1/s, fits inside the clip. */
export const fitScale = (clip: Clip, thetaDeg: number, margin = 1.02) => {
  const t = (thetaDeg * Math.PI) / 180;
  let g = 0;
  for (const [sx, sy] of [[1, 1], [1, -1], [-1, 1], [-1, -1]]) {
    const vx = (sx * W) / 2;
    const vy = (sy * H) / 2;
    g = Math.max(g, clipGauge(clip, [vx * Math.cos(t) - vy * Math.sin(t), vx * Math.sin(t) + vy * Math.cos(t)]));
  }
  return margin * g;
};

/** Frozen portal clips, each in its parent level's coordinates. */
export const CLIP: Clip[] = [
  heroEyeWorld(FREEZE_L0, 'R'),
  bugEyeWorld(FREEZE_L1_BASE, 'R'),
  hexPoly(CENTER[0], CENTER[1], HEX_R),
  {kind: 'ellipse', cx: RING.cx, cy: RING.cy, rx: RING.r, ry: RING.r, rot: 0},
];

const cdiv = (a: Cx, b: Cx): Cx => {
  const d = b[0] * b[0] + b[1] * b[1];
  return [(a[0] * b[0] + a[1] * b[1]) / d, (a[1] * b[0] - a[0] * b[1]) / d];
};

export type Portal = {
  /** zoom factor child -> parent */
  s: number;
  theta: number;
  /** portal centre in the parent (frozen) */
  p: Cx;
  /** child -> parent: z -> a (z - C) + p, a = e^{i theta} / s */
  a: Cx;
  /** parent -> child (inverse): z -> A z + B */
  A: Cx;
  B: Cx;
  /** fixed point of the inverse map = camera fixed point during the dive */
  zStar: Cx;
};

export const PORTALS: Portal[] = CLIP.map((clip, k) => {
  const theta = THETA[k];
  const s = fitScale(clip, theta);
  const p = clipCenter(clip);
  const t = (theta * Math.PI) / 180;
  const a: Cx = [Math.cos(t) / s, Math.sin(t) / s];
  const A = cdiv([1, 0], a);
  const pa = cdiv(p, a);
  const B: Cx = [CENTER[0] - pa[0], CENTER[1] - pa[1]];
  const zStar = cdiv(B, [1 - A[0], -A[1]]);
  return {s, theta, p, a, A, B, zStar};
});

/** Area-equivalent radius of the centre hex (R=72): 72*sqrt(3*sqrt(3)/(2*PI)) ~ 65.476. */
export const PUPIL_R2 = HEX_R * Math.sqrt((3 * Math.sqrt(3)) / (2 * Math.PI));

/** Bug pupil scale that makes its frozen pinpoint exactly the size of L2's centre facet at handoff (~0.2820). */
export const BUG_PUPIL = PUPIL_R2 / PORTALS[1].s / (2.6 * 3);

/** L1 frozen pose during Dive B (f106-151): portal B = its right eye (drawn by L2 via hideEye 'R'). */
export const FREEZE_L1: BugPose = {...FREEZE_L1_BASE, pupil: BUG_PUPIL};

/** Total zoom per loop = product of the four s. */
export const ZOOM_PER_LOOP = PORTALS.reduce((a, p) => a * p.s, 1);
