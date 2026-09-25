import React from 'react';
import {C, hose} from './theme';
import {bugEyeLocal, heroEyeLocal} from './geom';
import type {Arms, Mood} from './geom';

export type {Arms, Mood};

type Pt = [number, number];

export type HeroProps = {
  x: number;
  y: number;
  s?: number;
  dir?: 1 | -1;
  f: number;
  run?: number | null;
  jump?: boolean;
  look?: number;
  lookUp?: number;
  blink?: boolean;
  squash?: number;
  lean?: number;
  arms?: Arms;
  mood?: Mood;
  eyes?: number;
  pencil?: boolean;
  boilId?: string;
  body?: string;
  opacity?: number;
  rim?: string;
  /** Pupil fill (default C.ink). */
  pupil?: string;
  /** While that eye is open, skip its pupil ellipse and wedge (a child level owns the region). */
  portalEye?: 'L' | 'R';
  /** Draw that eye as a blink arc. */
  wink?: 'L' | 'R';
};

const glove = (p: Pt, key: string) => (
  <g key={key}>
    <circle cx={p[0]} cy={p[1]} r={13} fill={C.cream} stroke={C.ink} strokeWidth={4.5} />
    <path d={`M ${p[0] - 7} ${p[1] - 9} q 7 -5 14 0`} stroke={C.ink} strokeWidth={3} fill="none" strokeLinecap="round" />
  </g>
);

/** The hero: a terminal block cursor that grew pie-cut eyes, gloves and rubber-hose limbs. */
export const Hero: React.FC<HeroProps> = ({
  x, y, s = 1, dir = 1, f, run = null, jump = false, look = 0, lookUp = 0, blink = false, squash = 1, lean = 0,
  arms = 'idle', mood = 'smile', eyes = 1, pencil = false, boilId, body = C.cream, opacity = 1, rim,
  pupil = C.ink, portalEye, wink,
}) => {
  const limb = (d: string, w: number) => (
    <>
      {rim ? <path d={d} stroke={rim} strokeWidth={w + 7} fill="none" strokeLinecap="round" /> : null}
      <path d={d} stroke={C.ink} strokeWidth={w} fill="none" strokeLinecap="round" />
    </>
  );
  const p = run ?? 0;
  const running = run !== null && run !== undefined;
  // legs
  const hipL: Pt = [-14, 46];
  const hipR: Pt = [14, 46];
  let footL: Pt;
  let footR: Pt;
  if (jump) {
    footL = [-26, 78];
    footR = [22, 70];
  } else if (running) {
    footL = [-14 + Math.sin(p) * 34, 92 - Math.max(0, -Math.cos(p)) * 18];
    footR = [14 + Math.sin(p + Math.PI) * 34, 92 - Math.max(0, Math.cos(p)) * 18];
  } else {
    footL = [-20, 92];
    footR = [20, 92];
  }
  // arms
  const shL: Pt = [-31, -2];
  const shR: Pt = [31, -2];
  let hL: Pt;
  let hR: Pt;
  let bL = 12;
  let bR = -12;
  switch (arms) {
    case 'run':
      hL = [-34 + 30 * Math.sin(p), 34 - 14 * Math.abs(Math.cos(p))];
      hR = [34 - 30 * Math.sin(p), 34 - 14 * Math.abs(Math.cos(p))];
      break;
    case 'up':
      hL = [-50, -92];
      hR = [50, -92];
      bL = -10;
      bR = 10;
      break;
    case 'grab':
      hL = [44, -70];
      hR = [70, -46];
      bL = -18;
      bR = -14;
      break;
    case 'draw':
      hL = [-40, 34];
      hR = [74 + 10 * Math.sin(f * 0.7), -12 + 9 * Math.cos(f * 1.1)];
      bR = -16;
      break;
    case 'proud':
      hL = [-26, 30];
      hR = [26, 30];
      bL = 30;
      bR = -30;
      break;
    case 'wave':
      hL = [-46, 34];
      hR = [60, -78 + 10 * Math.sin(f * 0.8)];
      bR = -14;
      break;
    case 'hold':
      hL = [52, 4];
      hR = [60, -20];
      bL = -16;
      bR = -16;
      break;
    default:
      hL = [-46, 36];
      hR = [46, 36];
  }
  const sq = Math.max(0.35, squash);
  const sx = 1 / Math.sqrt(sq);
  const ex = look * 6;
  const eye = (which: 'L' | 'R') => {
    const cx = which === 'L' ? -13 : 13;
    const g = heroEyeLocal({look, lookUp, eyes}, which);
    const ry = g.ry;
    const rx = g.rx;
    if (blink || wink === which) return <path d={`M ${cx - rx} ${-18} q ${rx} 6 ${rx * 2} 0`} stroke={C.ink} strokeWidth={5} fill="none" strokeLinecap="round" />;
    if (mood === 'proud') return <path d={`M ${cx - rx} ${-14} q ${rx} -12 ${rx * 2} 0`} stroke={C.ink} strokeWidth={5} fill="none" strokeLinecap="round" />;
    if (portalEye === which) return null;
    return (
      <g>
        <ellipse cx={g.cx} cy={g.cy} rx={rx} ry={ry} fill={pupil} />
        <path d={g.wedge} fill={body} />
      </g>
    );
  };
  const mouth = () => {
    switch (mood) {
      case 'o':
        return <ellipse cx={ex * 0.5} cy={16} rx={7} ry={10} fill={C.ink} />;
      case 'grin':
        return <path d="M -16 8 Q 0 30 16 8 Z" fill={C.ink} stroke={C.ink} strokeWidth={3} strokeLinejoin="round" />;
      case 'determined':
        return <path d="M -12 14 Q 0 10 12 14" stroke={C.ink} strokeWidth={5} fill="none" strokeLinecap="round" />;
      default:
        return <path d="M -14 9 Q 0 24 14 9" stroke={C.ink} strokeWidth={5} fill="none" strokeLinecap="round" />;
    }
  };
  return (
    <g transform={`translate(${x} ${y}) scale(${s * dir} ${s}) rotate(${lean})`} opacity={opacity}>
      <g filter={boilId ? `url(#${boilId})` : undefined}>
        <g transform={`translate(0 ${92 * (1 - sq)}) scale(${sx} ${sq})`}>
          {/* back leg + arm */}
          {limb(hose(hipL[0], hipL[1], footL[0], footL[1], 9), 9)}
          {limb(hose(shL[0], shL[1], hL[0], hL[1], bL), 9)}
          {/* body = the block cursor */}
          <rect x={-32} y={-48} width={64} height={96} rx={13} fill={body} stroke={C.ink} strokeWidth={5.5} />
          {mood === 'determined' ? (
            <g stroke={C.ink} strokeWidth={5} strokeLinecap="round">
              <path d={`M ${-22 + ex} -38 L ${-6 + ex} -32`} />
              <path d={`M ${22 + ex} -38 L ${6 + ex} -32`} />
            </g>
          ) : null}
          {eye('L')}
          {eye('R')}
          {mouth()}
          {/* front leg + arm */}
          {limb(hose(hipR[0], hipR[1], footR[0], footR[1], -9), 9)}
          <ellipse cx={footL[0] + 9} cy={footL[1] + 3} rx={18} ry={10} fill={C.ink} stroke={rim ?? C.ink} strokeWidth={rim ? 4 : 0} />
          <ellipse cx={footR[0] + 9} cy={footR[1] + 3} rx={18} ry={10} fill={C.ink} stroke={rim ?? C.ink} strokeWidth={rim ? 4 : 0} />
          <ellipse cx={footR[0] + 14} cy={footR[1] - 1} rx={5} ry={2.5} fill={C.cream} opacity={0.7} />
          {limb(hose(shR[0], shR[1], hR[0], hR[1], bR), 9)}
          {glove(hL, 'gl')}
          {pencil ? (
            <g transform={`translate(${hR[0]} ${hR[1]}) rotate(38)`}>
              <rect x={-8} y={-84} width={16} height={78} rx={2} fill="#f2c14e" stroke={C.ink} strokeWidth={4} />
              <rect x={-8} y={-96} width={16} height={14} rx={3} fill="#e89a9a" stroke={C.ink} strokeWidth={4} />
              <path d="M -8 -6 L 0 16 L 8 -6 Z" fill="#e9d3a6" stroke={C.ink} strokeWidth={4} strokeLinejoin="round" />
              <path d="M -3 8 L 0 16 L 3 8 Z" fill={C.ink} />
            </g>
          ) : null}
          {glove(hR, 'gr')}
        </g>
      </g>
    </g>
  );
};

export type BugProps = {
  x: number;
  y: number;
  s?: number;
  dir?: 1 | -1;
  f: number;
  run?: number | null;
  fixed?: boolean;
  dizzy?: boolean;
  shell?: string;
  boilId?: string;
  opacity?: number;
  rot?: number;
  rim?: string;
  /** Eye-white scale (default 1). */
  eyes?: number;
  /** Pupil scale (default 1). */
  pupil?: number;
  /** Pupil offset per unit eyes (default [1.5, 0.5]). */
  gaze?: [number, number];
  /** Pupil fill (default C.ink). */
  pupilColor?: string;
  /** Skip that eye's white and pupil (a child level owns the region). */
  hideEye?: 'L' | 'R';
  /** Degrees; rotates each antenna path and its tip about its base (30,-22) / (38,-20). */
  antenna?: number;
  /** Squash/stretch about the feet line y=40 (default 1). */
  stretch?: number;
};

/** The bug: a scurrying red ✗ with rubber legs. Fixed, it becomes a green ✓ with wings. */
export const Bug: React.FC<BugProps> = ({
  x, y, s = 1, dir = 1, f, run = null, fixed = false, dizzy = false, shell, boilId, opacity = 1, rot = 0, rim,
  eyes = 1, pupil = 1, gaze, pupilColor = C.ink, hideEye, antenna = 0, stretch = 1,
}) => {
  const p = run ?? 0;
  const color = shell ?? (fixed ? C.green : C.red);
  const legs = [-18, 0, 18].map((bx, i) => {
    const ph = p + i * 2.1;
    const fx = bx + (run !== null ? Math.sin(ph) * 11 : 0) + 4;
    const fy = 40 - (run !== null ? Math.max(0, Math.cos(ph)) * 9 : 0);
    return (
      <g key={i}>
        {rim ? <path d={hose(bx, 14, fx, fy, 7)} stroke={rim} strokeWidth={12} fill="none" strokeLinecap="round" /> : null}
        <path d={hose(bx, 14, fx, fy, 7)} stroke={C.ink} strokeWidth={6} fill="none" strokeLinecap="round" />
      </g>
    );
  });
  const flap = 0.35 + 0.65 * Math.abs(Math.sin(f * 1.7));
  const eL = bugEyeLocal({eyes, pupil, gaze}, 'L');
  const eR = bugEyeLocal({eyes, pupil, gaze}, 'R');
  const ant = (i: 0 | 1, el: React.ReactElement) =>
    antenna === 0 ? el : <g transform={i === 0 ? `rotate(${antenna} 30 -22)` : `rotate(${antenna} 38 -20)`}>{el}</g>;
  const content = (
    <>
        {fixed ? (
          <g opacity={0.85}>
            <ellipse cx={-8} cy={-24} rx={28} ry={12} transform={`rotate(-28 -8 -24) scale(1 ${flap})`} fill={C.cream} stroke={C.ink} strokeWidth={3} />
            <ellipse cx={8} cy={-24} rx={28} ry={12} transform={`rotate(24 8 -24) scale(1 ${flap})`} fill={C.cream} stroke={C.ink} strokeWidth={3} />
          </g>
        ) : null}
        {fixed ? null : legs}
        {rim ? (
          antenna === 0 ? (
            <path d="M 30 -22 Q 28 -46 44 -50 M 38 -20 Q 48 -42 62 -38" stroke={rim} strokeWidth={10} fill="none" strokeLinecap="round" />
          ) : (
            <>
              {ant(0, <path d="M 30 -22 Q 28 -46 44 -50" stroke={rim} strokeWidth={10} fill="none" strokeLinecap="round" />)}
              {ant(1, <path d="M 38 -20 Q 48 -42 62 -38" stroke={rim} strokeWidth={10} fill="none" strokeLinecap="round" />)}
            </>
          )
        ) : null}
        {ant(0, <path d="M 30 -22 Q 28 -46 44 -50" stroke={C.ink} strokeWidth={4} fill="none" strokeLinecap="round" />)}
        {ant(1, <path d="M 38 -20 Q 48 -42 62 -38" stroke={C.ink} strokeWidth={4} fill="none" strokeLinecap="round" />)}
        {ant(0, <circle cx={44} cy={-50} r={5} fill={C.ink} />)}
        {ant(1, <circle cx={62} cy={-38} r={5} fill={C.ink} />)}
        <ellipse cx={0} cy={0} rx={36} ry={25} fill={color} stroke={C.ink} strokeWidth={5.5} />
        {fixed ? (
          <path d="M -15 0 L -4 12 L 16 -13" stroke={C.cream} strokeWidth={8} fill="none" strokeLinecap="round" strokeLinejoin="round" />
        ) : (
          <g stroke={C.cream} strokeWidth={8} strokeLinecap="round">
            <path d="M -12 -12 L 12 12" />
            <path d="M 12 -12 L -12 12" />
          </g>
        )}
        <circle cx={36} cy={-6} r={16} fill={color} stroke={C.ink} strokeWidth={5} />
        {hideEye === 'L' ? null : <circle cx={eL.cx} cy={eL.cy} r={eL.r} fill={C.cream} />}
        {hideEye === 'R' ? null : <circle cx={eR.cx} cy={eR.cy} r={eR.r} fill={C.cream} />}
        {hideEye === 'L' ? null : <circle cx={eL.px} cy={eL.py} r={eL.pr} fill={pupilColor} />}
        {hideEye === 'R' ? null : <circle cx={eR.px} cy={eR.py} r={eR.pr} fill={pupilColor} />}
        <path d={fixed ? 'M 31 -1 Q 38 6 45 -1' : 'M 31 1 Q 38 -3 45 1'} stroke={C.ink} strokeWidth={3} fill="none" strokeLinecap="round" />
        {dizzy
          ? [0, 1, 2].map((i) => {
              const a = f * 0.25 + (i * Math.PI * 2) / 3;
              return (
                <text key={i} x={36 + Math.cos(a) * 34} y={-44 + Math.sin(a) * 9} fontSize={20} textAnchor="middle" fill={C.orange}>
                  ✦
                </text>
              );
            })
          : null}
    </>
  );
  return (
    <g transform={`translate(${x} ${y}) scale(${s * dir} ${s}) rotate(${rot})`} opacity={opacity}>
      <g filter={boilId ? `url(#${boilId})` : undefined}>
        {stretch === 1 ? content : <g transform={`translate(0 40) scale(${1 / Math.sqrt(stretch)} ${stretch}) translate(0 -40)`}>{content}</g>}
      </g>
    </g>
  );
};
