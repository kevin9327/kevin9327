import React from 'react';
import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {Bug, Hero} from '../lib/characters';
import {Boil, Film, Speed, Splat} from '../lib/fx';
import {C, F, H, W, back, charXs, eio, eo, jit, lerp, pop, rnd} from '../lib/theme';

const MONO = 64;
const CW = MONO * 0.6;
const X0 = 560;
const L1 = 420;
const L2 = 510;
const L3 = 600;
const TITLE = "FIXING OTHER PEOPLE'S BUGS";

/** 0–4 s. A failing test's ✗ sprouts legs and bolts; the prompt cursor wakes up and hijacks the title. */
export const S1Terminal: React.FC = () => {
  const f = useCurrentFrame();

  const whip = f >= 106 ? Math.pow(f - 106, 2) * 16 : 0;
  const shake = (f >= 48 && f < 54) || (f >= 112 && f < 117) ? jit(f, 3, 14, 1) : 0;
  const push = lerp(f, [0, 40], [1.08, 1], eo);

  // birth shockwave blows the terminal lines apart
  const blast = lerp(f, [48, 60], [0, 1], eo);
  const lineStyle = (i: number) => ({
    transform: `translate(${blast * (i === 0 ? -300 : 260)}px, ${blast * (i === 0 ? -260 : 320)}px) rotate(${blast * (i === 0 ? -14 : 11)}deg)`,
    opacity: 1 - blast,
  });

  const l1 = 'npm test'.slice(0, Math.max(0, Math.floor(f * 1.8)));
  const l1done = f >= 5;
  const l2on = f >= 7;
  const l2 = '1 failed · only in production'.slice(0, Math.max(0, Math.floor((f - 9) * 2.6)));

  // the ✗ wakes up as a bug and bolts off screen
  const wake = pop(f, 12, 7, 220);
  const bugRun = f >= 18;
  const t = Math.max(0, f - 18);
  const bugX = X0 + 20 + (bugRun ? Math.pow(t, 1.45) * 38 : 0);
  const bugY = L2 - 22 - wake * 30 - (bugRun ? Math.abs(Math.sin(f * 0.8)) * 60 : 0);
  const bugS = 0.3 + 1.9 * wake;

  // cursor -> hero
  const cursorX = X0 + CW * 2;
  const blinkOn = Math.floor(f / 8) % 2 === 0;
  const grow = lerp(f, [38, 48], [0, 1], eio);
  const born = f >= 48;
  const bornPop = pop(f, 48, 6, 200);
  const S = 2.5;
  const settle = lerp(f, [48, 60], [0, 1], eo);
  const feetY = L3 + settle * 200;
  const baseX = cursorX + 20 + settle * 180;
  let heroY = feetY - 92 * S;
  let look = 0;
  let eyes = 1;
  let mood: 'smile' | 'o' | 'grin' | 'determined' = 'smile';
  let arms: 'idle' | 'up' | 'grab' = 'idle';
  let jump = false;
  if (f >= 60 && f < 67) look = -1;
  if (f >= 67 && f < 74) look = 1;
  if (f >= 74 && f < 88) {
    eyes = 1.4;
    mood = 'o';
    heroY -= Math.sin(lerp(f, [74, 82], [0, Math.PI])) * 60;
  }
  const leap = lerp(f, [94, 103], [0, 1], eio);
  const fall = lerp(f, [104, 118], [0, 1], (u) => u * u);
  let heroX = baseX;
  if (f >= 94) {
    heroY = feetY - 92 * S - leap * 520 + fall * 720;
    heroX = baseX + leap * 220 + fall * 120;
    arms = f < 104 ? 'up' : 'grab';
    jump = true;
    mood = 'determined';
  }

  // title: typed, then yanked down letter by letter
  const typed = Math.max(0, Math.floor((f - 80) * 1.3));
  const TS = 120;
  const {xs, width} = charXs(TITLE, F.cartoon, TS);
  const tx0 = W / 2 - width / 2;
  const yank = Math.max(0, f - 103);
  const grabI = 9;

  return (
    <AbsoluteFill style={{background: C.black}}>
      <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`}>
        <defs>
          <Boil id="b1" f={f} scale={3.4} />
        </defs>
        <g transform={`translate(${W / 2 - whip + shake} ${H / 2}) scale(${push}) translate(${-W / 2} ${-H / 2})`}>
          <g fontFamily={F.mono} fontSize={MONO} fill={C.cream}>
            <g style={lineStyle(0)}>
              <text x={X0} y={L1}>
                <tspan fill={C.gray}>$ </tspan>
                {l1}
              </text>
            </g>
            {l2on ? (
              <g style={lineStyle(1)}>
                <text x={X0 + CW * 2} y={L2} fill={C.gray}>
                  {l2}
                </text>
              </g>
            ) : null}
            {l1done && !born ? (
              <text x={X0} y={L3} fill={C.gray}>
                ${' '}
              </text>
            ) : null}
          </g>
          {!l1done && blinkOn ? <rect x={X0 + CW * (2 + l1.length)} y={L1 - 50} width={CW} height={64} fill={C.cream} /> : null}
          {l2on && wake < 0.05 ? (
            <g stroke={C.red} strokeWidth={10} strokeLinecap="round" transform={`translate(${X0 + 20} ${L2 - 22})`}>
              <path d="M -16 -16 L 16 16" />
              <path d="M 16 -16 L -16 16" />
            </g>
          ) : null}
          {l2on && wake >= 0.05 && bugX < W + 300 ? (
            <Bug rim={C.cream} x={bugX} y={bugY} s={bugS} f={f} run={bugRun ? f * 0.95 : null} boilId="b1" rot={bugRun ? -8 : jit(f, 5, 6, 2)} />
          ) : null}
          {bugRun && f < 36 ? <Speed f={f} n={9} color={C.red} y0={L2 - 140} y1={L2 + 40} o={0.55} /> : null}
          {/* cursor wakes */}
          {l1done && !born ? (
            <rect
              x={cursorX - grow * 40}
              y={L3 - 50 - grow * 150}
              width={CW + grow * 80}
              height={64 + grow * 150}
              rx={grow * 26}
              fill={blinkOn || grow > 0 ? C.cream : 'transparent'}
            />
          ) : null}
          {born && f < 64 ? (
            <g>
              <circle cx={baseX} cy={feetY - 130} r={lerp(f, [48, 62], [40, 900], eo)} fill="none" stroke={C.cream} strokeWidth={lerp(f, [48, 62], [26, 2])} opacity={lerp(f, [48, 62], [0.9, 0])} />
              <circle cx={baseX} cy={feetY - 130} r={lerp(f, [50, 64], [20, 620], eo)} fill="none" stroke={C.red} strokeWidth={lerp(f, [50, 64], [10, 1])} opacity={lerp(f, [50, 64], [0.7, 0])} />
            </g>
          ) : null}
          {born ? (
            <Hero
              x={heroX}
              y={heroY}
              s={S * (0.55 + 0.45 * bornPop)}
              f={f}
              look={look}
              eyes={eyes}
              mood={mood}
              arms={arms}
              jump={jump}
              squash={lerp(f, [48, 52, 57], [1.7, 0.75, 1], back)}
              boilId="b1"
              rim={C.cream}
              blink={f >= 89 && f < 92}
            />
          ) : null}
          <g fontFamily={F.cartoon} fontSize={TS}>
            {TITLE.split('').map((ch, i) => {
              if (i >= typed) return null;
              const d = Math.abs(i - grabI) * 0.3;
              const u = Math.max(0, yank - d);
              const gx = tx0 + xs[i] + (yank > 0 ? (rnd(i * 3.1) - 0.4) * u * 18 : 0);
              const gy = 250 + (yank > 0 ? Math.min(900, 0.5 * 4.2 * u * u) : 0);
              const rot = yank > 0 ? (rnd(i * 7.7) - 0.5) * u * 26 : jit(f, i, 1.8);
              const pulled = f >= 101 && f < 104 && Math.abs(i - grabI) < 3 ? 26 : 0;
              return (
                <text key={i} x={gx} y={gy + pulled} fill={C.cream} transform={`rotate(${rot} ${gx + 30} ${gy - 40})`} filter="url(#b1)">
                  {ch}
                </text>
              );
            })}
          </g>
        </g>
        {f >= 56 && f < 100 ? (
          <g opacity={lerp(f, [56, 64, 90, 100], [0, 1, 1, 0])}>
            <defs>
              <radialGradient id="iris" cx={heroX / W} cy={(heroY + 20) / H} r="0.42">
                <stop offset="0.45" stopColor="#000" stopOpacity={0} />
                <stop offset="1" stopColor="#000" stopOpacity={0.85} />
              </radialGradient>
            </defs>
            <rect width={W} height={H} fill="url(#iris)" />
          </g>
        ) : null}
        {f >= 106 ? <Speed f={f} n={24} color={C.cream} o={lerp(f, [106, 112], [0, 0.65])} /> : null}
      </svg>
      <Film f={f} dark strength={0.8} />
    </AbsoluteFill>
  );
};
