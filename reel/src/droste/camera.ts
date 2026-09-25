/** The log-spiral Droste camera. Pure (no React / remotion). */
import {matApply, matInv} from '../lib/geom';
import type {Mat} from '../lib/geom';
import {smoothstep} from './anim';
import {PORTALS} from './portals';
import {CENTER, H, SEG, STUB, T, W, loopF} from './timeline';
import type {Clip, LevelView, View} from './types';
import {l0PortalClip} from './levels/L0.pose';
import {l1PortalClip} from './levels/L1.pose';
import {l2PortalClip} from './levels/L2.pose';
import {l3PortalClip} from './levels/L3.pose';

/** Live portal clip of level k (to level k+1), in level k's coordinates. */
export const PORTAL_CLIP: ((f: number) => Clip | null)[] = [l0PortalClip, l1PortalClip, l2PortalClip, l3PortalClip];

/* --------------------------------------------------------------- complex */

export type Cx = [number, number];
export const cmul = (a: Cx, b: Cx): Cx => [a[0] * b[0] - a[1] * b[1], a[0] * b[1] + a[1] * b[0]];
export const cadd = (a: Cx, b: Cx): Cx => [a[0] + b[0], a[1] + b[1]];
export const csub = (a: Cx, b: Cx): Cx => [a[0] - b[0], a[1] - b[1]];
export const cabs = (a: Cx) => Math.hypot(a[0], a[1]);
export const carg = (a: Cx) => Math.atan2(a[1], a[0]);
/** |A|^u e^{i u arg A} */
export const cpow = (A: Cx, u: number): Cx => {
  const r = Math.pow(cabs(A), u);
  const t = carg(A) * u;
  return [r * Math.cos(t), r * Math.sin(t)];
};

/** Similarity z -> al z + be (z = x + i y, y down; multiplying by e^{i t} = SVG rotate(t)). */
export type Sim = {al: Cx; be: Cx};
export const simToMat = (s: Sim): Mat => [s.al[0], s.al[1], -s.al[1], s.al[0], s.be[0], s.be[1]];
const simCompose = (outer: Sim, inner: Sim): Sim => ({al: cmul(outer.al, inner.al), be: cadd(cmul(outer.al, inner.be), outer.be)});
/** Portal k as a similarity: child (k+1) coords -> parent (k) coords, z -> a (z - C) + p. */
export const portalSim = (k: number): Sim => {
  const P = PORTALS[k];
  return {al: P.a, be: csub(P.p, cmul(P.a, CENTER))};
};

/* ------------------------------------------------------------------ clips */

export const matScaleOf = (M: Mat) => Math.hypot(M[0], M[1]);
export const matRotDegOf = (M: Mat) => (Math.atan2(M[1], M[0]) * 180) / Math.PI;

/** Map a level-space clip to screen space through a similarity matrix. */
export const clipToScreen = (clip: Clip, M: Mat): Clip => {
  if (clip.kind === 'ellipse') {
    const [cx, cy] = matApply(M, [clip.cx, clip.cy]);
    const k = matScaleOf(M);
    return {kind: 'ellipse', cx, cy, rx: clip.rx * k, ry: clip.ry * k, rot: clip.rot + matRotDegOf(M)};
  }
  return {kind: 'poly', pts: clip.pts.map((p) => matApply(M, p))};
};

/** sqrt(rx*ry) for ellipses; area-equivalent radius for polygons. */
export const clipRadius = (clip: Clip) => {
  if (clip.kind === 'ellipse') return Math.sqrt(Math.abs(clip.rx * clip.ry));
  let a = 0;
  const p = clip.pts;
  for (let i = 0; i < p.length; i++) {
    const q = p[(i + 1) % p.length];
    a += p[i][0] * q[1] - q[0] * p[i][1];
  }
  return Math.sqrt(Math.abs(a / 2) / Math.PI);
};

/** Level-space bounding box [x0, y0, x1, y1] of the screen frame under M, expanded by pad (for culling). */
export const viewRect = (M: Mat, pad = 0): [number, number, number, number] => {
  const inv = matInv(M);
  const pts = [[0, 0], [W, 0], [0, H], [W, H]].map((p) => matApply(inv, p as [number, number]));
  const xs = pts.map((p) => p[0]);
  const ys = pts.map((p) => p[1]);
  return [Math.min(...xs) - pad, Math.min(...ys) - pad, Math.max(...xs) + pad, Math.max(...ys) + pad];
};

/* ----------------------------------------------------------------- depth */

/** Depth D(f): piecewise from SEG; smoothstep inside dives. f is wrapped with loopF. */
export const Dof = (frame: number) => {
  const f = loopF(frame);
  for (const s of SEG) {
    if (f >= s.f0 && f < s.f1) {
      if (s.D0 === s.D1) return s.D0;
      return s.D0 + (s.D1 - s.D0) * smoothstep((f - s.f0) / (s.f1 - s.f0));
    }
  }
  return SEG[SEG.length - 1].D1;
};

/** Unwrapped depth: continuous across the seam (adds 4 per loop). */
export const DofU = (t: number) => Dof(t) + 4 * Math.floor(t / T);

/** Rack-focus blur (CSS px) for the depth-0 level. */
export const blurFor = (px: number, vel: number) =>
  px <= 2 ? 0 : Math.min(8, 3.2 * Math.log(px / 2)) + Math.min(3, 12 * Math.max(0, vel - 0.1));

/* ------------------------------------------------------------------ view */

export const view = (frame: number): View => {
  const f = loopF(frame);
  const D = Dof(f);
  const fl = Math.floor(D);
  const c = ((fl % 4) + 4) % 4;
  const u = D - fl;
  const P = PORTALS[c];
  const Au = cpow(P.A, u);
  let S: Sim = {al: Au, be: csub(P.zStar, cmul(Au, P.zStar))};
  const vel = Math.abs(DofU(f + 1) - DofU(f - 1)) * Math.log(P.s);
  const levels: LevelView[] = [];
  const clips: Clip[] = [];
  for (let j = 0; j < 4; j++) {
    const k = ((c + j) % 4) as 0 | 1 | 2 | 3;
    const M = simToMat(S);
    const px = cabs(S.al);
    levels.push({k, depth: j, M, px, clips: clips.slice(), blur: j === 0 ? blurFor(px, vel) : 0, kind: 'level'});
    if (j === 3) break;
    const live = PORTAL_CLIP[k](f);
    if (!live) break;
    const sc = clipToScreen(live, M);
    clips.push(sc);
    const kn = ((k + 1) % 4) as 0 | 1 | 2 | 3;
    S = simCompose(S, portalSim(k));
    if (clipRadius(sc) < 2) {
      levels.push({k: kn, depth: j + 1, M: simToMat(S), px: cabs(S.al), clips: clips.slice(), blur: 0, kind: 'stub', stubColor: STUB[kn]});
      break;
    }
  }
  return {f, D, c, u, levels, fixed: [P.zStar[0], P.zStar[1]], vel, rollDeg: (carg(Au) * 180) / Math.PI};
};

/* ------------------------------------------------------------------ lint */

/** Per segment: max zoom factor and max roll (deg) between consecutive OUTPUT frames (2 comp frames). */
export const lintCamera = () => {
  const perSeg = SEG.map((s) => {
    const c = ((Math.floor(Math.min(s.D0, s.D1)) % 4) + 4) % 4;
    const P = PORTALS[c];
    let maxZoomPerOut = 1;
    let maxRollPerOut = 0;
    for (let f = s.f0; f < s.f1; f++) {
      const dD = Math.abs(DofU(f + 2) - DofU(f));
      maxZoomPerOut = Math.max(maxZoomPerOut, Math.exp(dD * Math.log(P.s)));
      maxRollPerOut = Math.max(maxRollPerOut, dD * Math.abs(P.theta));
    }
    return {n: s.n, maxZoomPerOut, maxRollPerOut};
  });
  return {perSeg};
};
