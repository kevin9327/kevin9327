/**
 * L1 "caught red-handed": a five-line diff. The Bug munches the removed line 'ship(pr);' one character per bite
 * while 'await review(pr);' and 'await merge(pr);' type in; at `caught` it freezes (hit-stop), a '!' pops, and it
 * does a take into the lens, settling on FREEZE_L1 with pinpoint pupils. Its right eye is portal B (L2 draws it).
 */
import React from 'react';
import {Bug} from '../../lib/characters';
import type {BugPose} from '../../lib/geom';
import {C} from '../../lib/palette';
import {F} from '../../lib/theme';
import {lod} from '../anim';
import {Boil3, HullSmear, PopNumber} from '../fx';
import {DATA, EV, SEGN} from '../timeline';
import type {LevelModule, LevelRenderProps} from '../types';
import {
  ADV, BASE_Y, CODE_X, INDENT, MERGE, REVIEW, SHIP, bugHullPts, l1Caret, l1Crumbs, l1MouthOpen, l1PortalClip, l1Pose, l1Smear,
} from './L1.pose';

type Tok = [string, string];

/** Per-character colours for a token list. */
const chars = (toks: Tok[]): Tok[] => toks.flatMap(([t, c]) => Array.from(t).map((ch) => [ch, c] as Tok));
/** Re-join consecutive same-colour characters into tspans. */
const runs = (cs: Tok[]): Tok[] =>
  cs.reduce<Tok[]>((acc, [ch, c]) => {
    const last = acc[acc.length - 1];
    if (last && last[1] === c) last[0] += ch;
    else acc.push([ch, c]);
    return acc;
  }, []);

const LINE1: Tok[] = [['for', C.purple], [' (', C.cream], ['const', C.purple], [' pr ', C.cream], ['of', C.purple], [' prs) {', C.cream]];
const SHIP_C = chars([['ship', C.blue], ['(pr);', C.cream]]);
const REVIEW_C = chars([['await', C.purple], [' ', C.cream], ['review', C.blue], ['(pr);', C.cream]]);
const MERGE_C = chars([['await', C.purple], [' ', C.cream], ['merge', C.blue], ['(pr);', C.cream]]);
const LINE5: Tok[] = [['}', C.cream], ['  // merged ', C.gray], [`×${DATA.total}`, C.green]];

if (SHIP_C.length !== SHIP.length || REVIEW_C.length !== REVIEW.length || MERGE_C.length !== MERGE.length) {
  throw new Error('L1: token colours out of sync with the pose-file strings');
}

/** Baseline of the '!' (level u): line 1's cap tops sit at about y 84. */
const BANG_Y = 70;

const MARKS: (null | '-' | '+')[] = [null, '-', '+', '+', null];
const BANDS: [number, string][] = [
  [134, C.red],
  [204, C.green],
  [274, C.green],
];

const CodeLine: React.FC<{i: number; toks: Tok[]; x: number}> = ({i, toks, x}) =>
  toks.length ? (
    <text x={x} y={BASE_Y[i]} fontFamily={F.mono} fontWeight={400} fontSize={36} style={{whiteSpace: 'pre'}}>
      {toks.map(([t, c], j) => (
        <tspan key={j} fill={c}>
          {t}
        </tspan>
      ))}
    </text>
  ) : null;

/** Speed streaks for the take smear: 3 cream lines along the lunge, trailing back past the anticipation pose. */
const TakeStreaks: React.FC<{from: BugPose; to: BugPose}> = ({from, to}) => {
  const dx = to.x - from.x;
  const dy = to.y - from.y;
  const len = Math.hypot(dx, dy);
  const nx = -dy / len;
  const ny = dx / len;
  return (
    <g stroke={C.cream} strokeLinecap="round" fill="none" opacity={0.8}>
      {[
        [-46, -0.42, 0.3, 6],
        [4, -0.62, 0.12, 8],
        [50, -0.36, 0.34, 6],
      ].map(([o, a, b, w], i) => (
        <line
          key={i}
          x1={from.x + dx * a + nx * o}
          y1={from.y + dy * a + ny * o}
          x2={from.x + dx * b + nx * o}
          y2={from.y + dy * b + ny * o}
          strokeWidth={w}
        />
      ))}
    </g>
  );
};

/**
 * Open jaws drawn in the Bug's own local frame (same nested transform as <Bug>, same boil filter so it wobbles in
 * sync). The ink ellipse covers the Bug's mouth line and stays inside the head, clear of the eye whites.
 */
const OpenMouth: React.FC<{p: BugPose; boilId?: string}> = ({p, boilId}) => {
  const st = p.stretch ?? 1;
  const jaw = <ellipse cx={38} cy={0.5} rx={9} ry={5.5} fill={C.ink} />;
  return (
    <g transform={`translate(${p.x} ${p.y}) scale(${(p.s ?? 1) * (p.dir ?? 1)} ${p.s ?? 1}) rotate(${p.rot ?? 0})`}>
      <g filter={boilId ? `url(#${boilId})` : undefined}>
        {st === 1 ? jaw : <g transform={`translate(0 40) scale(${1 / Math.sqrt(st)} ${st}) translate(0 -40)`}>{jaw}</g>}
      </g>
    </g>
  );
};

const Base: React.FC<LevelRenderProps> = ({f, px, boil: stackBoil}) => {
  const pose = l1Pose(f);
  const frozen = f >= EV.freezeB && f < SEGN.diveB.f1;
  // No boil while frozen: the left eye must match L2's (unboiled) right-eye stub pixel for pixel at the handoff.
  const boil = stackBoil && !frozen;
  const tO = lod(26 * px, 3, 5);
  const bO = lod(70 * px, 2, 4);
  const boilId = 'boil-L1-base';

  const line2 = runs(SHIP_C.slice(0, SHIP.length - pose.eaten));
  const line3 = runs(REVIEW_C.slice(0, pose.typed3));
  const line4 = runs(MERGE_C.slice(0, pose.typed4));
  const codeX = CODE_X + INDENT * ADV;
  const caret = l1Caret(f);
  const smear = l1Smear(f);
  const crumbs = l1Crumbs(f);

  // '!' above the Bug's head, in the empty band above line 1. It follows the head when the Bug turns round for the
  // anticipation (dir flips -1 -> +1), so it does not hang behind the tail; BANG_Y keeps clear of line 1's cap tops.
  const bangX = pose.x + (pose.dir ?? 1) * 44;

  const txt = (el: React.ReactNode) => (tO > 0 ? <g opacity={tO}>{el}</g> : null);
  const bug = (
    <>
      {smear ? <HullSmear from={bugHullPts(smear.from)} to={bugHullPts(smear.to)} fill={C.red} stroke={C.ink} strokeW={5} /> : null}
      {smear?.speed ? <TakeStreaks from={smear.from} to={smear.to} /> : null}
      <Bug
        x={pose.x}
        y={pose.y}
        s={pose.s}
        dir={pose.dir}
        rot={pose.rot}
        stretch={pose.stretch}
        eyes={pose.eyes}
        pupil={pose.pupil}
        gaze={pose.gaze}
        antenna={pose.antenna}
        run={pose.run ?? null}
        hideEye={pose.hideEye}
        f={f}
        rim={C.cream}
        pupilColor={C.night}
        boilId={boil ? boilId : undefined}
      />
      {l1MouthOpen(f) ? <OpenMouth p={pose} boilId={boil ? boilId : undefined} /> : null}
    </>
  );
  // Layering: the Bug lives in line 2's row, in front of the line it eats. While it is small (munch .. anticipation)
  // the other rows are drawn over its thin antennae / legs so the typed lines stay readable; from the take on it
  // lunges at the lens, in front of everything.
  const front = f >= EV.takeB && f < SEGN.diveB.f1;

  return (
    <g>
      {boil ? (
        <defs>
          <Boil3 id={boilId} f={f} />
        </defs>
      ) : null}
      <rect x={-1e5} y={-1e5} width={2e5} height={2e5} fill={C.night} />
      {bO > 0 ? (
        <g opacity={bO}>
          {BANDS.map(([y, c]) => (
            <rect key={y} x={0} y={y} width={1200} height={70} fill={c} opacity={0.16} />
          ))}
        </g>
      ) : null}
      {txt(
        <>
          {BASE_Y.map((y, i) => (
            <text key={`n${i}`} x={70} y={y} textAnchor="end" fontFamily={F.mono} fontWeight={400} fontSize={30} fill={C.gray}>
              {String(i + 1)}
            </text>
          ))}
          {MARKS.map((m, i) =>
            m ? (
              <text key={`m${i}`} x={92} y={BASE_Y[i]} fontFamily={F.mono} fontWeight={700} fontSize={36} fill={m === '-' ? C.red : C.green}>
                {m}
              </text>
            ) : null,
          )}
          <CodeLine i={1} toks={line2} x={codeX} />
        </>,
      )}
      {front ? null : bug}
      {txt(
        <>
          <CodeLine i={0} toks={LINE1} x={CODE_X} />
          <CodeLine i={2} toks={line3} x={codeX} />
          <CodeLine i={3} toks={line4} x={codeX} />
          <CodeLine i={4} toks={LINE5} x={CODE_X} />
          {caret ? <rect x={codeX + caret[1] * ADV} y={BASE_Y[caret[0]] - 30} width={ADV} height={40} fill={C.cream} /> : null}
        </>,
      )}
      {front ? bug : null}
      {crumbs.map((c, i) => (
        <rect
          key={i}
          x={c.x - c.size / 2}
          y={c.y - c.size / 2}
          width={c.size}
          height={c.size}
          fill={c.color}
          transform={`rotate(${c.rot} ${c.x} ${c.y})`}
        />
      ))}
      {pose.bang > 0 ? (
        <g transform={`rotate(-8 ${bangX} ${BANG_Y})`}>
          <PopNumber text="!" x={bangX} y={BANG_Y} size={56} t={pose.bang} fill={C.cream} stroke={C.ink} strokeW={6} />
        </g>
      ) : null}
    </g>
  );
};

export const L1: LevelModule = {
  id: 1,
  stub: C.night,
  Base,
  portalClip: l1PortalClip,
  warm: [
    ['for (const pr of prs) {', F.mono, 36],
    [`  ${SHIP}`, F.mono, 36],
    [`  ${REVIEW}`, F.mono, 36],
    [`  ${MERGE}`, F.mono, 36],
    ['!', F.cartoon, 56],
  ],
};
