/**
 * M1: L0 "kevin9327 ~ $". The poster (frame 0 and the 1.6 s seam hold), the wake take, and home.
 *
 * Level coordinates (1200 x 500), night background. Everything shown comes from DATA; the only identity string
 * is 'kevin9327'. The Hero is the block cursor in the cell after 'kevin9327 ~ $ ' (x 969.6..1032, i.e. the 15th
 * 0.6 em cell of the 104 u prompt: 96 + 14 * 62.4 .. 96 + 15 * 62.4), centred at FREEZE_L0.x = 1000.8.
 * Portal A is the Hero's right eye: while it is open the Base leaves that eye empty (portalEye 'R'), L1 fills it
 * with night, and the Overlay puts the cream pie-cut wedge back on top of L1.
 */
import React from 'react';
import {Hero} from '../../lib/characters';
import {heroEyeLocal, heroMatrix, matApply, matStr} from '../../lib/geom';
import type {HeroPose} from '../../lib/geom';
import {C} from '../../lib/palette';
import {F, charXs} from '../../lib/theme';
import {lod} from '../anim';
import {Boil3, HullSmear} from '../fx';
import {DATA, FACETS} from '../timeline';
import type {LevelModule, LevelRenderProps} from '../types';
import {TAKE_L0, l0PortalClip, l0Pose, l0Smear} from './L0.pose';
import {SLEEP_L0} from '../portals';

/* ---------------------------------------------------------------- layout */

const X0 = 96;
const CONTEXT = {text: "# pull requests merged into other people's repos", y: 104, size: 28};
const PROMPT = {user: 'kevin9327', tail: ' ~ $', y: 236, size: 104};
const STATS = {y: 372, size: 46};
const RULE = {y: 400, h: 14, w: 1008};
const BOIL_SCALE = 2.0;
/**
 * Cream rim on the hose limbs and shoes, as the reel does on every night background (S1/S3/S4/S6): with no rim the
 * ink limbs vanish on night (#17130e on #0d1117) and the gloves float; the body, eyes and portal are unaffected.
 */
const HERO_RIM = C.cream;

const RANK_COLORS = [C.green, C.blue, C.purple, C.orange];
const TAIL_COLORS = [C.pencil, C.gray];

/** LOD: a text element fades in as its cap height on screen grows from 3 to 5 u. */
const textO = (size: number, px: number) => lod(0.73 * size * px, 3, 5);

/**
 * Grayscale text AA. Chrome paints SVG text straight onto the opaque page with LCD sub-pixel AA, which leaves
 * blue / orange fringes on the cream prompt (orthogonal chroma p99 ~46 even after the 2x -> 1x LANCZOS) and made
 * the prompt's edge pixels differ by 1-2 LSB between a cold and a warm tab at --scale=2 (seam gate). Painting the
 * text through a no-op filter renders it into a transparent offscreen, which forces grayscale AA. sRGB so the
 * filter does not round-trip the colours through linearRGB. Used only while px <= 2: above that the depth-0 level
 * is CSS-blurred (camera blurFor), which already rasterizes offscreen, and a user-space filter region at 48x would
 * be needlessly huge.
 */
const AA_MAX_PX = 2;
const AA_BOX = {x: 40, y: 40, w: 980, h: 372};
const GrayAA: React.FC<{id: string}> = ({id}) => (
  <filter id={id} filterUnits="userSpaceOnUse" x={AA_BOX.x} y={AA_BOX.y} width={AA_BOX.w} height={AA_BOX.h} colorInterpolationFilters="sRGB">
    <feOffset dx={0} dy={0} />
  </filter>
);

/* ------------------------------------------------------------------ rule */

/** 32 bands in rank order, width proportional to merged, no gaps (each band overlaps the next by 0.6 u). */
const BANDS = (() => {
  let x = X0;
  return FACETS.map((fc, i) => {
    const w = (RULE.w * fc.merged) / DATA.total;
    const band = {
      key: fc.repo,
      x,
      w: w + (i < FACETS.length - 1 ? 0.6 : 0),
      fill: fc.rank <= 10 ? RANK_COLORS[(fc.rank - 1) % RANK_COLORS.length] : TAIL_COLORS[(fc.rank - 11) % TAIL_COLORS.length],
    };
    x += w;
    return band;
  });
})();

const Rule: React.FC<{opacity: number}> = ({opacity}) =>
  opacity <= 0 ? null : (
    <g opacity={opacity}>
      {BANDS.map((b) => (
        <rect key={b.key} x={b.x} y={RULE.y} width={b.w} height={RULE.h} fill={b.fill} />
      ))}
    </g>
  );

/* ------------------------------------------------------------ hull smear */

type P2 = [number, number];

/** The body rect (x -32..32, y -48..48, rx 13) sampled along its rounded corners, in the Hero's innermost frame. */
const BODY_PTS: P2[] = (() => {
  const r = 13;
  const pts: P2[] = [];
  const corners: [number, number, number][] = [
    [32 - r, -48 + r, -90],
    [32 - r, 48 - r, 0],
    [-32 + r, 48 - r, 90],
    [-32 + r, -48 + r, 180],
  ];
  for (const [cx, cy, a0] of corners) {
    for (let i = 0; i <= 4; i++) {
      const a = ((a0 + (i * 90) / 4) * Math.PI) / 180;
      pts.push([cx + r * Math.cos(a), cy + r * Math.sin(a)]);
    }
  }
  return pts;
})();

const bodyWorld = (p: HeroPose): P2[] => {
  const m = heroMatrix(p);
  return BODY_PTS.map((q) => matApply(m, q));
};

/** f10: the convex hull of the sleeping body and the stretched take body, cream with the body's ink line. */
const TakeSmear: React.FC<{filter?: string}> = ({filter}) => (
  <g filter={filter}>
    <HullSmear from={bodyWorld(SLEEP_L0)} to={bodyWorld(TAKE_L0)} fill={C.cream} stroke={C.ink} strokeW={5.5 * (SLEEP_L0.s ?? 1)} />
  </g>
);

/* ------------------------------------------------------------------ base */

const Base: React.FC<LevelRenderProps> = ({f, px, boil, layer}) => {
  const pose = l0Pose(f);
  const open = l0PortalClip(f) !== null;
  const boilId = `boil-L0-${layer}`;
  const tailX = X0 + charXs(PROMPT.user, F.mono, PROMPT.size).width;
  const oContext = textO(CONTEXT.size, px);
  const oPrompt = textO(PROMPT.size, px);
  const oStats = textO(STATS.size, px);
  const aaId = `aa-L0-${layer}`;
  const textAA = px <= AA_MAX_PX && oContext + oPrompt + oStats > 0;
  return (
    <g>
      {boil ? (
        <defs>
          <Boil3 id={boilId} f={f} scale={BOIL_SCALE} />
        </defs>
      ) : null}
      <rect x={-1e5} y={-1e5} width={2e5} height={2e5} fill={C.night} />
      {textAA ? (
        <defs>
          <GrayAA id={aaId} />
        </defs>
      ) : null}
      <g filter={textAA ? `url(#${aaId})` : undefined}>
        {oContext > 0 ? (
          <text x={X0} y={CONTEXT.y} fontFamily={F.mono} fontWeight={400} fontSize={CONTEXT.size} fill={C.gray} opacity={oContext} style={{whiteSpace: 'pre'}}>
            {CONTEXT.text}
          </text>
        ) : null}
        {oPrompt > 0 ? (
          <g opacity={oPrompt}>
            <text x={X0} y={PROMPT.y} fontFamily={F.mono} fontWeight={700} fontSize={PROMPT.size} fill={C.cream} style={{whiteSpace: 'pre'}}>
              {PROMPT.user}
            </text>
            <text x={tailX} y={PROMPT.y} fontFamily={F.mono} fontWeight={700} fontSize={PROMPT.size} fill={C.gray} style={{whiteSpace: 'pre'}}>
              {PROMPT.tail}
            </text>
          </g>
        ) : null}
        {oStats > 0 ? (
          <text x={X0} y={STATS.y} fontFamily={F.mono} fontWeight={700} fontSize={STATS.size} opacity={oStats} style={{whiteSpace: 'pre'}}>
            <tspan fill={C.green}>{String(DATA.total)}</tspan>
            <tspan fill={C.cream}> MERGED</tspan>
            <tspan fill={C.gray}> · </tspan>
            <tspan fill={C.green}>{String(DATA.repos)}</tspan>
            <tspan fill={C.cream}> REPOS</tspan>
            <tspan fill={C.gray}> · </tspan>
            <tspan fill={C.green}>{String(DATA.days)}</tspan>
            <tspan fill={C.cream}> DAYS</tspan>
          </text>
        ) : null}
      </g>
      <Rule opacity={lod(RULE.h * px, 1, 2)} />
      {l0Smear(f) ? <TakeSmear filter={boil ? `url(#${boilId})` : undefined} /> : null}
      <Hero {...pose} f={f} pupil={C.night} portalEye={open ? 'R' : undefined} boilId={boil ? boilId : undefined} rim={HERO_RIM} />
    </g>
  );
};

/* --------------------------------------------------------------- overlay */

/**
 * The right eye's cream pie-cut wedge, drawn ABOVE L1 while portal A is open (it streaks past the lens in Dive A).
 * It boils with the same noise field as the Hero (the filter sits in the Hero's outer frame) so both eyes wobble alike.
 */
const Overlay: React.FC<LevelRenderProps> = ({f, boil, layer}) => {
  if (l0PortalClip(f) === null) return null;
  const pose = l0Pose(f);
  const wedge = <path d={heroEyeLocal(pose, 'R').wedge} fill={C.cream} />;
  if (!boil) return <g transform={matStr(heroMatrix(pose))}>{wedge}</g>;
  const boilId = `boil-L0-${layer}`;
  const s = pose.s ?? 1;
  const sq = Math.max(0.35, pose.squash ?? 1);
  return (
    <>
      <defs>
        <Boil3 id={boilId} f={f} scale={BOIL_SCALE} />
      </defs>
      <g transform={`translate(${pose.x} ${pose.y}) scale(${s * (pose.dir ?? 1)} ${s}) rotate(${pose.lean ?? 0})`}>
        <g filter={`url(#${boilId})`}>
          <g transform={`translate(0 ${92 * (1 - sq)}) scale(${1 / Math.sqrt(sq)} ${sq})`}>{wedge}</g>
        </g>
      </g>
    </>
  );
};

export const L0: LevelModule = {
  id: 0,
  stub: C.night,
  Base,
  Overlay,
  portalClip: l0PortalClip,
  warm: [
    [CONTEXT.text, F.mono, CONTEXT.size],
    [PROMPT.user, F.mono, PROMPT.size],
    [PROMPT.tail, F.mono, PROMPT.size],
  ],
};
