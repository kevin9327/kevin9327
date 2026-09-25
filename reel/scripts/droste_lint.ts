/**
 * Droste contract lint. Run:
 *   npx esbuild scripts/droste_lint.ts --bundle --platform=node --format=esm --outfile=out/droste_lint.mjs && node out/droste_lint.mjs
 * Prints a table and ends with 'LINT OK' (exit 0) or 'LINT FAIL' (exit 1).
 */
import {bugEyeLocal, bugEyeWorld, bugMatrix, heroEyeLocal, heroEyeWorld, heroMatrix, matApply} from '../src/lib/geom';
import type {BugPose, HeroPose} from '../src/lib/geom';
import {DofU, Dof, PORTAL_CLIP, lintCamera, view} from '../src/droste/camera';
import {BUG_PUPIL, CLIP, FREEZE_L0, FREEZE_L1, PORTALS, PUPIL_R2, SLEEP_L0, ZOOM_PER_LOOP, clipGauge} from '../src/droste/portals';
import {DATA, EV, FACETS, SEG, T, fmtDate} from '../src/droste/timeline';
import type {Clip} from '../src/droste/types';
import {l0Pose} from '../src/droste/levels/L0.pose';
import {l1Pose} from '../src/droste/levels/L1.pose';

const fails: string[] = [];
const check = (ok: boolean, msg: string) => {
  if (!ok) fails.push(msg);
  return ok;
};
const pad = (s: string | number, n: number) => String(s).padEnd(n);
const near = (a: number, b: number, rel = 0.01) => Math.abs(a - b) <= rel * Math.abs(b) + 1e-9;

/** Deep equality that treats missing and undefined keys alike. */
const deq = (a: unknown, b: unknown): boolean => {
  if (a === b) return true;
  if (typeof a !== typeof b || a === null || b === null || typeof a !== 'object') return false;
  if (Array.isArray(a) !== Array.isArray(b)) return false;
  const ka = Object.keys(a as object).filter((k) => (a as Record<string, unknown>)[k] !== undefined);
  const kb = Object.keys(b as object).filter((k) => (b as Record<string, unknown>)[k] !== undefined);
  if (ka.length !== kb.length) return false;
  return ka.every((k) => deq((a as Record<string, unknown>)[k], (b as Record<string, unknown>)[k]));
};

const clipDiff = (a: Clip | null, b: Clip): number => {
  if (!a || a.kind !== b.kind) return Infinity;
  if (a.kind === 'ellipse' && b.kind === 'ellipse') {
    return Math.max(Math.abs(a.cx - b.cx), Math.abs(a.cy - b.cy), Math.abs(a.rx - b.rx), Math.abs(a.ry - b.ry), Math.abs(a.rot - b.rot));
  }
  if (a.kind === 'poly' && b.kind === 'poly') {
    if (a.pts.length !== b.pts.length) return Infinity;
    return Math.max(...a.pts.map((p, i) => Math.max(Math.abs(p[0] - b.pts[i][0]), Math.abs(p[1] - b.pts[i][1]))));
  }
  return Infinity;
};

/* 1. DATA guards (timeline throws at import; re-assert here for the report) */
const sum = (xs: number[]) => xs.reduce((a, b) => a + b, 0);
check(sum(DATA.all.map((r) => r.merged)) === DATA.total, 'sum(all.merged) !== total');
check(sum(DATA.deltas) === DATA.total, 'sum(deltas) !== total');
check(DATA.deltas[0] === DATA.series[0].total, 'deltas[0] !== series[0].total');
check(DATA.deltas.every((d, i) => i === 0 || d === DATA.series[i].total - DATA.series[i - 1].total), 'deltas mismatch');
check(DATA.all.length === DATA.repos, 'all.length !== repos');
check(DATA.series.length === DATA.days + 1, 'series.length !== days + 1');
check(FACETS.length === DATA.repos && sum(FACETS.map((f) => f.merged)) === DATA.total, 'FACETS do not sum to total');
check(fmtDate(DATA.series[0].date) === 'JUL 18' && fmtDate(DATA.series[DATA.days].date) === 'SEP 25', 'fmtDate endpoints');
const bloomDays = DATA.deltas.filter((d) => d > 0).length;
console.log(`DATA  total=${DATA.total} repos=${DATA.repos} days=${DATA.days} bloomDays=${bloomDays} ${fmtDate(DATA.start)}..${fmtDate(DATA.end)}`);

/* FACETS order = the spec's list */
const SPEC_ORDER =
  '-1,0|1,-1|1,0|-1,1|0,-1|0,1|2,-1|-2,1|-2,0|2,-2|2,0|-2,2|-1,-1|1,-2|1,1|-1,2|-3,1|3,-2|3,-1|-3,2|4,-2|-4,2|-3,0|3,-3|3,0|-3,3|-4,1|4,-3|4,-1|-4,3|-5,2|5,-3';
check(FACETS.map((f) => `${f.q},${f.r}`).join('|') === SPEC_ORDER, 'FACETS cell order differs from spec');
check(FACETS[0].tOn === EV.cascade[0] && FACETS[FACETS.length - 1].tOn === EV.cascade[1], 'FACETS tOn range != EV.cascade');
check(FACETS.every((f) => f.tOn % 2 === 0), 'odd facet tOn');

/* 2. SEG contiguous 0..T, even boundaries */
check(SEG[0].f0 === 0 && SEG[SEG.length - 1].f1 === T, 'SEG does not span 0..T');
SEG.forEach((s, i) => {
  check(s.f1 > s.f0, `SEG ${s.n} empty`);
  if (i > 0) check(s.f0 === SEG[i - 1].f1, `SEG ${s.n} not contiguous`);
  check(s.f0 % 2 === 0 && s.f1 % 2 === 0, `SEG ${s.n} odd boundary`);
  if (i > 0) check(s.D0 === SEG[i - 1].D1, `SEG ${s.n} depth jump`);
});

/* 3. EV even, windows >= 2 frames */
for (const [k, v] of Object.entries(EV)) {
  const arr = Array.isArray(v) ? v : [v];
  arr.forEach((x) => check(x % 2 === 0, `EV.${k} has odd value ${x}`));
  if (Array.isArray(v) && v.length === 2 && k !== 'bites') check(v[1] - v[0] >= 2, `EV.${k} lasts < 2 frames`);
}
for (let i = 1; i < EV.bites.length; i++) check(EV.bites[i] - EV.bites[i - 1] >= 2, 'EV.bites spacing < 2');

/* 4. periodic side channels */
check(T % 12 === 0, 'T % 12 !== 0 (Boil3 cycle)');
check(T % 4 === 0, 'T % 4 !== 0 (ZoomLines seed)');

/* 5. camera: zoom / roll per output frame */
console.log('\nSEG        f0   f1   D0   D1   zoom/out  roll/out  maxVel');
const {perSeg} = lintCamera();
for (const r of perSeg) {
  const s = SEG.find((x) => x.n === r.n)!;
  let maxVel = 0;
  for (let f = s.f0; f < s.f1; f++) maxVel = Math.max(maxVel, view(f).vel);
  console.log(
    `${pad(r.n, 10)} ${pad(s.f0, 4)} ${pad(s.f1, 4)} ${pad(s.D0, 4)} ${pad(s.D1, 4)} ${pad(r.maxZoomPerOut.toFixed(3), 9)} ${pad(r.maxRollPerOut.toFixed(3), 9)} ${maxVel.toFixed(3)}`,
  );
  check(r.maxZoomPerOut <= 1.25, `${r.n}: zoom ${r.maxZoomPerOut.toFixed(4)}x > 1.25 per output frame`);
  check(r.maxRollPerOut <= 1.0, `${r.n}: roll ${r.maxRollPerOut.toFixed(3)} deg > 1.0 per output frame`);
  if (s.D0 === s.D1) check(maxVel < 0.12, `${r.n}: hold has zoom velocity ${maxVel.toFixed(3)} (ZoomLines would draw)`);
}
const EXPECT_PEAK: Record<string, number> = {diveA: 1.241, diveB: 1.248, diveC: 1.247, diveD1: 1.245, diveD2: 1.204};
for (const [n, e] of Object.entries(EXPECT_PEAK)) {
  const r = perSeg.find((x) => x.n === n)!;
  check(Math.abs(r.maxZoomPerOut - e) < 0.004, `${n}: peak zoom ${r.maxZoomPerOut.toFixed(4)} != spec ${e}`);
}

/* 6. live portal clip == frozen CLIP[k] in every frame the camera is between level k and k+1 */
let clipChecked = 0;
for (const s of SEG) {
  const between = s.D0 !== s.D1 || s.D0 % 1 !== 0;
  if (!between) continue;
  const k = ((Math.floor(Math.min(s.D0, s.D1)) % 4) + 4) % 4;
  for (let f = s.f0; f < s.f1; f++) {
    const d = clipDiff(PORTAL_CLIP[k](f), CLIP[k]);
    check(d < 1e-9, `${s.n} f${f}: portalClip L${k} differs from CLIP[${k}] by ${d}`);
    clipChecked++;
  }
}

/* 7. poses: seam SLEEP, dive freezes */
for (let f = 370; f < 384; f++) check(deq(l0Pose(f), SLEEP_L0), `l0Pose(${f}) != SLEEP_L0`);
for (let f = 0; f < 10; f++) check(deq(l0Pose(f), SLEEP_L0), `l0Pose(${f}) != SLEEP_L0`);
for (let f = 370; f < 384; f++) for (let g = 0; g < 10; g++) check(deq(l0Pose(f), l0Pose(g)), `l0Pose(${f}) != l0Pose(${g})`);
check(PORTAL_CLIP[0](0) === null && PORTAL_CLIP[0](383) === null, 'portal A open across the seam');
for (let f = EV.freezeA; f < 72; f++) check(deq(l0Pose(f), FREEZE_L0), `l0Pose(${f}) != FREEZE_L0 (Dive A)`);
for (let f = EV.freezeB; f < 152; f++) {
  const p = l1Pose(f) as unknown as Record<string, unknown>;
  const ok = Object.entries(FREEZE_L1).every(([k, v]) => deq(p[k], v)) && p.hideEye === 'R';
  check(ok, `l1Pose(${f}) != FREEZE_L1 + hideEye R (Dive B)`);
}

/* 8. depth across the seam */
for (let f = 354; f < 384; f++) check(Dof(f) % 4 === 0, `Dof(${f}) = ${Dof(f)} not 0 mod 4`);
for (let f = 0; f < 18; f++) check(Dof(f) % 4 === 0, `Dof(${f}) = ${Dof(f)} not 0 mod 4`);
check(DofU(-1) === DofU(0) && DofU(T) === DofU(0) + 4, 'DofU not continuous across the seam');
const v0 = view(0);
const vT = view(T);
check(deq(v0, vT), 'view(384) != view(0)');
check(deq(view(383).levels, v0.levels) && view(383).vel === 0 && v0.vel === 0, 'camera not static across the seam');
check(v0.levels.length === 1 && deq(v0.levels[0].M, [1, 0, 0, 1, 0, 0]), 'frame 0 is not L0 alone at identity');

/* 9. portal numbers */
const EXP_S = [48.92, 29.76, 10.545, 30.14];
const EXP_Z: [number, number][] = [[1021.8, 186.0], [857.6, 229.8], [600, 250], [1138.0, 330.8]];
console.log('\nPORTAL  s         theta  zStar                 clipR');
PORTALS.forEach((P, k) => {
  const c = CLIP[k];
  const cr = c.kind === 'ellipse' ? Math.sqrt(c.rx * c.ry) : PUPIL_R2;
  console.log(`${pad('ABCD'[k], 7)} ${pad(P.s.toFixed(4), 9)} ${pad(P.theta, 6)} (${P.zStar[0].toFixed(2)}, ${P.zStar[1].toFixed(2)})`.padEnd(46) + cr.toFixed(3));
  check(near(P.s, EXP_S[k]), `PORTALS[${k}].s ${P.s} not within 1% of ${EXP_S[k]}`);
  check(near(P.zStar[0], EXP_Z[k][0]) && near(P.zStar[1], EXP_Z[k][1]), `PORTALS[${k}].zStar off`);
});
check(near(ZOOM_PER_LOOP, 4.6e5), `zoom per loop ${ZOOM_PER_LOOP} not ~4.6e5`);
check(near(PUPIL_R2, 65.476, 0.001), `PUPIL_R2 ${PUPIL_R2}`);
check(near(BUG_PUPIL, 0.282, 0.01), `BUG_PUPIL ${BUG_PUPIL}`);
console.log(`zoom/loop=${ZOOM_PER_LOOP.toExponential(3)} PUPIL_R2=${PUPIL_R2.toFixed(3)} BUG_PUPIL=${BUG_PUPIL.toFixed(4)} clipsChecked=${clipChecked}`);

/* 10. geometry: *EyeWorld is exactly the image of the drawn local eye under *Matrix (drawing and portals cannot drift) */
let geoMax = 0;
const heroPoses: HeroPose[] = [
  FREEZE_L0,
  {x: 300, y: 200, s: 1.3, dir: -1, lean: 12, squash: 1.35, look: 0.5, lookUp: 1, eyes: 2},
  {x: 50, y: -40, s: 0.4, dir: 1, lean: -20, squash: 0.2, look: -1, lookUp: -0.5, eyes: 0.55},
];
const bugPoses: BugPose[] = [
  FREEZE_L1,
  {x: 400, y: 172, s: 1.4, dir: -1, rot: 10, stretch: 0.9, eyes: 0.8, gaze: [1.5, 0.5]},
  {x: -30, y: 90, s: 3.4, dir: 1, rot: -6, stretch: 1.3, eyes: 1.6, pupil: 0.2},
];
for (const p of heroPoses) {
  for (const w of ['L', 'R'] as const) {
    const e = heroEyeLocal(p, w);
    const E = heroEyeWorld(p, w);
    for (let i = 0; i < 16; i++) {
      const a = (i / 16) * 2 * Math.PI;
      const q = matApply(heroMatrix(p), [e.cx + e.rx * Math.cos(a), e.cy + e.ry * Math.sin(a)]);
      geoMax = Math.max(geoMax, Math.abs(clipGauge(E, [q[0] - E.cx, q[1] - E.cy]) - 1));
    }
  }
}
for (const p of bugPoses) {
  for (const w of ['L', 'R'] as const) {
    const e = bugEyeLocal(p, w);
    const E = bugEyeWorld(p, w);
    for (let i = 0; i < 16; i++) {
      const a = (i / 16) * 2 * Math.PI;
      const q = matApply(bugMatrix(p), [e.cx + e.r * Math.cos(a), e.cy + e.r * Math.sin(a)]);
      geoMax = Math.max(geoMax, Math.abs(clipGauge(E, [q[0] - E.cx, q[1] - E.cy]) - 1));
    }
  }
}
check(geoMax < 1e-9, `eye geometry: world ellipse off by gauge ${geoMax}`);
const bl = bugEyeLocal({}, 'L');
const br = bugEyeLocal({}, 'R');
const hr = heroEyeLocal({}, 'R');
check(bl.px === 33.5 && bl.py === -10.5 && br.px === 44.5 && bl.r === 5.5 && bl.pr === 2.6 && hr.cx === 13 && hr.cy === -18, 'default eye geometry changed (reel regression risk)');
console.log(`geometry: max gauge error ${geoMax.toExponential(2)} over ${(heroPoses.length + bugPoses.length) * 32} samples`);

/* 11. chain sanity on every frame */
let maxChain = 0;
for (let f = 0; f < T; f++) {
  const v = view(f);
  maxChain = Math.max(maxChain, v.levels.length);
  check(v.levels.length >= 1 && v.levels.length <= 4, `f${f}: chain length ${v.levels.length}`);
  check(v.levels.every((lv) => lv.M.every(Number.isFinite) && Number.isFinite(lv.px) && Number.isFinite(lv.blur)), `f${f}: non-finite view`);
  check(v.levels[0].depth === 0 && v.levels.slice(1).every((lv) => lv.blur === 0), `f${f}: blur on a non-current level`);
}
console.log(`chain: max ${maxChain} levels`);

if (fails.length) {
  console.log('\n' + fails.slice(0, 60).map((s) => 'FAIL ' + s).join('\n'));
  if (fails.length > 60) console.log(`... and ${fails.length - 60} more`);
  console.log('LINT FAIL');
  process.exit(1);
}
console.log('\nLINT OK');
