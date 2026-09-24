import React from 'react';
import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {Bug, Hero} from '../lib/characters';
import {Boil, Film, HandText, Splat, Stamp} from '../lib/fx';
import {C, F, H, W, ei, eio, eo, jit, lerp, pop} from '../lib/theme';

const ARROW = 'M 0 0 L 0 46 L 11 35 L 20 55 L 28 51 L 19 32 L 34 32 Z';

/** Mouse arrow path: enters, then darts around with the bug riding it. */
const arrowAt = (f: number): [number, number] => {
  if (f < 14) return [lerp(f, [0, 14], [1780, 1420], eo), lerp(f, [0, 14], [960, 640], eo)];
  const u = f - 14;
  return [960 + 560 * Math.sin(u * 0.105 + 0.95), 560 + 250 * Math.sin(u * 0.21 + 0.3)];
};

/** 14–18 s. The bug hijacks the real mouse cursor; the hero grabs it, it becomes a pencil, a test cage is drawn. */
export const S4Cursor: React.FC = () => {
  const f = useCurrentFrame();
  const grabbed = f >= 60;
  const [ax, ay] = arrowAt(Math.min(f, 60));

  // hero: falls in from the launch, chases, leaps, grabs
  let hx: number;
  let hy: number;
  let air = false;
  if (f < 18) {
    hx = 560;
    hy = lerp(f, [4, 18], [-420, 780], ei);
    air = true;
  } else if (f < 52) {
    const [tx] = arrowAt(f - 6);
    hx = 560 + (tx - 560) * lerp(f, [18, 52], [0.2, 0.85], eio);
    hy = 780 - Math.abs(Math.sin(f * 0.35)) * 40;
  } else if (f < 60) {
    const [tx, ty] = arrowAt(60);
    hx = lerp(f, [52, 60], [arrowAt(46)[0] * 0.85 + 84, tx], eio);
    hy = lerp(f, [52, 60], [780, ty + 120], eio) - Math.sin(lerp(f, [52, 60], [0, Math.PI])) * 160;
    air = true;
  } else if (f < 66) {
    const [tx, ty] = arrowAt(60);
    hx = lerp(f, [60, 66], [tx, 470], eio);
    hy = lerp(f, [60, 66], [ty + 120, 800], ei);
    air = true;
  } else if (f < 78) {
    // draws the left bracket
    hx = 470;
    hy = 800;
  } else if (f < 83) {
    // hops over the cage
    hx = lerp(f, [78, 83], [470, 1450], eio);
    hy = 800 - Math.sin(lerp(f, [78, 83], [0, Math.PI])) * 280;
    air = true;
  } else {
    // draws the right bracket, facing back
    hx = 1450;
    hy = 800;
  }
  const heroS = 1.8;
  const drawing = (f >= 66 && f < 78) || (f >= 83 && f < 94);
  const push = lerp(f, [58, 74], [1, 1.2], eio);

  // cage
  const leftP = lerp(f, [66, 78], [0, 1]);
  const rightP = lerp(f, [83, 93], [0, 1]);
  const close = pop(f, 94, 7, 240);
  const lx = 640 + close * 170;
  const rx = 1280 - close * 170;
  const bugX = grabbed ? lerp(f, [60, 70], [ax, 960], eio) : ax + 40;
  const bugY = grabbed ? lerp(f, [60, 70], [ay - 30, 600], eo) : ay - 30;
  const failed = pop(f, 100, 8, 200);
  const shake = f >= 100 && f < 106 ? jit(f, 4, 18, 1) : 0;

  return (
    <AbsoluteFill style={{background: `radial-gradient(ellipse at 50% 55%, ${C.night2} 0%, ${C.night} 70%)`}}>
      <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`}>
        <defs>
          <Boil id="b4" f={f} scale={3} />
        </defs>
        <g transform={`translate(${shake} ${shake * 0.5}) translate(960 610) scale(${push}) translate(-960 -610)`}>
          {/* floor line */}
          <line x1={0} y1={892} x2={W} y2={892} stroke="#30363d" strokeWidth={4} strokeDasharray="18 14" />
          {/* the cage, drawn by hand */}
          <g stroke={C.cream} strokeWidth={18} fill="none" strokeLinecap="round" strokeLinejoin="round" filter="url(#b4)">
            <path d={`M ${lx + 60} 420 L ${lx} 420 L ${lx} 800 L ${lx + 60} 800`} strokeDasharray={560} strokeDashoffset={560 * (1 - leftP)} />
            <path d={`M ${rx - 60} 420 L ${rx} 420 L ${rx} 800 L ${rx - 60} 800`} strokeDasharray={560} strokeDashoffset={560 * (1 - rightP)} />
          </g>
          {/* mouse arrow (until grabbed) */}
          {!grabbed ? (
            <g transform={`translate(${ax} ${ay}) scale(3) rotate(${jit(f, 9, 8, 2)})`}>
              <path d={ARROW} fill="#fff" stroke="#000" strokeWidth={2.5} strokeLinejoin="round" />
            </g>
          ) : null}
          {grabbed && f < 70 ? <Splat x={ax} y={ay} r={lerp(f, [60, 66], [20, 140])} color={C.cream} seed={31} o={lerp(f, [60, 70], [0.8, 0])} /> : null}
          <Bug
            x={bugX}
            y={bugY + (f >= 94 ? close * 20 : 0)}
            s={grabbed ? 2 : 1.6}
            f={f}
            run={grabbed ? null : f}
            dizzy={f >= 70}
            boilId="b4"
            rim={C.cream}
            rot={grabbed ? jit(f, 3, 5, 3) : -20}
          />
          <Hero
            x={hx}
            y={hy - 92 * heroS}
            s={heroS}
            dir={f >= 81 ? -1 : 1}
            f={f}
            run={air || drawing || f >= 94 ? null : f * 0.8}
            jump={air}
            arms={drawing ? 'draw' : air ? 'grab' : f >= 94 ? 'proud' : 'run'}
            pencil={f >= 62}
            mood={drawing ? 'determined' : 'grin'}
            look={1}
            boilId="b4"
            rim={C.cream}
          />
          <Stamp text="FAILED" x={960} y={290} color={C.red} t={failed} rot={-7} size={120} />
        </g>
        {f >= 102 ? (
          <HandText text="first, a test that fails" x={960} y={1010} size={62} progress={lerp(f, [102, 118], [0, 1])} font={F.hand} color={C.cream} stroke={2} />
        ) : null}
      </svg>
      <Film f={f + 900} dark strength={0.35} />
    </AbsoluteFill>
  );
};
