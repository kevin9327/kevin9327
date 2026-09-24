import React from 'react';
import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {Bug, Hero} from '../lib/characters';
import {Boil, HandText, Splat, Stamp} from '../lib/fx';
import {C, F, H, W, eio, eo, lerp, pop} from '../lib/theme';

/** 18–22 s. Sudden silence on clean paper. A patch is drawn, the stamp flips to PASSED, the bug turns into a ✓. */
export const S5Fix: React.FC = () => {
  const f = useCurrentFrame();

  const walk = lerp(f, [4, 16], [0, 1], eio);
  const hx = 420 + walk * 300;
  const drawing = f >= 16 && f < 40;
  const vP = lerp(f, [16, 26], [0, 1], eio);
  const hP = lerp(f, [27, 37], [0, 1], eio);
  const bandage = pop(f, 38, 8, 220);
  const flipOut = lerp(f, [44, 50], [1, 0], eio);
  const flipIn = lerp(f, [50, 57], [0, 1], eo);
  const open = lerp(f, [54, 66], [0, 1], eio);
  const morph = f >= 60;
  const flyT = Math.max(0, f - 62);
  const bx = morph ? 960 + Math.sin(flyT * 0.16) * 140 * lerp(f, [62, 80], [0, 1]) : 960;
  const by = morph ? 610 - lerp(f, [60, 84], [0, 170], eo) + Math.cos(flyT * 0.22) * 20 : 620;
  const lx = 810 - open * 260;
  const rx = 1110 + open * 260;

  return (
    <AbsoluteFill style={{background: '#f8f4ea'}}>
      <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`}>
        <defs>
          <Boil id="b5" f={f} scale={2.2} />
        </defs>
        <g transform="translate(960 600) scale(1.18) translate(-960 -600)">
        <line x1={0} y1={892} x2={W} y2={892} stroke={C.ink} strokeWidth={4} opacity={0.2} />
        {/* the cage */}
        <g stroke={C.ink} strokeWidth={18} fill="none" strokeLinecap="round" strokeLinejoin="round" filter="url(#b5)" opacity={1 - open * 0.8}>
          <path d={`M ${lx + 60} 420 L ${lx} 420 L ${lx} 800 L ${lx + 60} 800`} />
          <path d={`M ${rx - 60} 420 L ${rx} 420 L ${rx} 800 L ${rx - 60} 800`} />
        </g>
        {/* the bug */}
        {!morph ? (
          <Bug x={960} y={640} s={1.7} f={f} boilId="b5" rot={f < 44 ? 0 : -6} />
        ) : (
          <Bug x={bx} y={by} s={1.6} f={f} fixed boilId="b5" rot={Math.sin(flyT * 0.3) * 10} />
        )}
        {f >= 58 && f < 70 ? <Splat x={960} y={630} r={lerp(f, [58, 64], [30, 190])} color={C.green} seed={51} o={lerp(f, [58, 70], [0.7, 0])} /> : null}
        {/* the patch: a diff "+" drawn in green, then it becomes a bandage */}
        {!morph ? (
          bandage < 0.05 ? (
            <g stroke={C.green} strokeWidth={22} strokeLinecap="round" filter="url(#b5)">
              <path d="M 960 540 L 960 720" strokeDasharray={180} strokeDashoffset={180 * (1 - vP)} />
              <path d="M 870 630 L 1050 630" strokeDasharray={180} strokeDashoffset={180 * (1 - hP)} />
            </g>
          ) : (
            <g transform={`translate(960 628) rotate(-28) scale(${0.6 + 0.4 * bandage})`} filter="url(#b5)">
              <rect x={-110} y={-30} width={220} height={60} rx={28} fill="#e9c9a0" stroke={C.ink} strokeWidth={6} />
              <rect x={-38} y={-24} width={76} height={48} rx={10} fill="#f3e3c6" stroke={C.ink} strokeWidth={4} />
              <path d="M -16 0 L 16 0 M 0 -16 L 0 16" stroke={C.green} strokeWidth={9} strokeLinecap="round" />
            </g>
          )
        ) : null}
        {/* stamp flip */}
        {f < 50 ? <Stamp text="FAILED" x={960} y={290} color={C.red} t={1} rot={-7} size={120} flip={flipOut} /> : null}
        {f >= 50 ? <Stamp text="PASSED" x={960} y={290} color={C.green} t={1} rot={-7} size={120} flip={flipIn} /> : null}
        <Hero
          x={hx}
          y={800 - 92 * 1.5}
          s={1.5}
          f={f}
          run={f >= 4 && f < 16 ? f * 0.6 : null}
          arms={drawing ? 'draw' : f >= 60 ? 'proud' : 'idle'}
          pencil
          mood={f >= 58 ? 'grin' : 'determined'}
          look={f >= 64 ? 0.6 : 1}
          lookUp={f >= 64 ? 1 : 0}
          boilId="b5"
          blink={f >= 96 && f < 99}
        />
        </g>
        {f >= 70 ? (
          <HandText text="fails before. passes after." x={960} y={1010} size={70} progress={lerp(f, [70, 100], [0, 1])} font={F.hand} color={C.ink} stroke={2.5} />
        ) : null}
      </svg>
    </AbsoluteFill>
  );
};
