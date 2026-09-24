import React from 'react';
import {AbsoluteFill, useCurrentFrame} from 'remotion';
import data from '../data.json';
import {Bug, Hero} from '../lib/characters';
import {Boil, Film, Speed, Stamp} from '../lib/fx';
import {C, F, H, W, eo, jit, lerp, measure, rnd} from '../lib/theme';

const ALL = (data.all as {repo: string; merged: number}[]).filter((r) => r.repo !== 'OpenCADStudio');
const REPOS = data.repos as number;
const DURS = [15, 15, 15, 12, 10, 9, 8, 6, 5, 4, 3, 3, 3, 3, 3, 3, 3];
const STARTS = DURS.reduce<number[]>((acc, d, i) => [...acc, i === 0 ? 0 : acc[i - 1] + DURS[i - 1]], []);
const STYLES = [
  {bg: C.orange, fg: C.black, sub: C.black},
  {bg: C.night, fg: C.cream, sub: C.green},
  {bg: C.paper, fg: C.ink, sub: C.red},
  {bg: C.green, fg: C.night, sub: C.night},
  {bg: C.purple, fg: C.cream, sub: C.cream},
];

/** 22–26 s. Repo names slam past, cuts accelerating from 0.5 s to 0.1 s. */
export const S6Blitz: React.FC = () => {
  const f = useCurrentFrame();
  let k = 0;
  for (let i = 0; i < DURS.length; i++) if (f >= STARTS[i]) k = i;
  const lf = f - STARTS[k];
  const dur = DURS[k];
  const u = lf / Math.max(1, dur - 1);
  const repo = ALL[k % ALL.length];
  const st = STYLES[k % STYLES.length];
  const tiny = k % 3 === 2;
  const maxW = tiny ? 760 : 1640;
  const baseSize = tiny ? 96 : 260;
  const size = Math.min(baseSize, (baseSize * maxW) / Math.max(1, measure(repo.repo, F.cartoon, baseSize)));
  const punch = lerp(lf, [0, Math.min(4, dur)], [1.18, 1], eo);
  const tilt = (rnd(k * 5.3) - 0.5) * 8;
  const heroX = lerp(u, [0, 1], [tiny ? 700 : 260, tiny ? 1220 : 1680]);
  const heroArc = Math.sin(u * Math.PI) * (tiny ? 60 : 180);

  return (
    <AbsoluteFill style={{background: st.bg}}>
      <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`}>
        <defs>
          <Boil id="b6" f={f} scale={2.4} />
        </defs>
        <Speed f={f} n={16} color={st.fg} o={0.18} />
        <g transform={`translate(${W / 2 + jit(f, k, 6, 1)} ${H / 2}) rotate(${tilt}) scale(${punch}) translate(${-W / 2} ${-H / 2})`}>
          {tiny ? (
            <g>
              <rect x={W / 2 - 430} y={430} width={860} height={250} rx={28} fill={C.cream} stroke={C.ink} strokeWidth={8} />
              <text x={W / 2} y={545} textAnchor="middle" fontFamily={F.cartoon} fontSize={size} fill={C.ink}>
                {repo.repo}
              </text>
              <text x={W / 2} y={630} textAnchor="middle" fontFamily={F.mono} fontSize={44} fill={C.green} fontWeight={700}>
                {repo.merged} merged
              </text>
              <Hero x={heroX} y={430 - 92 * 0.8 - heroArc} s={0.8} f={f} jump arms="up" mood="grin" boilId="b6" />
            </g>
          ) : (
            <g>
              <text x={W / 2} y={600} textAnchor="middle" fontFamily={F.cartoon} fontSize={size} fill={st.fg} filter="url(#b6)">
                {repo.repo}
              </text>
              <text x={W / 2} y={740} textAnchor="middle" fontFamily={F.mono} fontSize={64} fill={st.sub} fontWeight={700}>
                {repo.merged} merged
              </text>
              {dur >= 8 ? <Hero x={heroX} y={380 - heroArc} s={1.25} f={f} jump arms="up" mood="grin" boilId="b6" rim={st.bg === C.night ? C.cream : undefined} /> : null}
              {dur >= 8 && k % 2 === 1 ? <Bug x={W - heroX} y={860 - heroArc * 0.4} s={1} f={f} fixed boilId="b6" /> : null}
            </g>
          )}
          {dur >= 10 ? <Stamp text="MERGED" x={W / 2 + 470} y={860} color={st.bg === C.purple ? C.cream : C.purple} t={Math.min(1, lf / 5)} rot={-10} size={70} /> : null}
        </g>
        <text x={60} y={80} fontFamily={F.mono} fontSize={30} fill={st.fg} opacity={0.75} letterSpacing={3}>
          REPO {k + 1} / {REPOS}
        </text>
      </svg>
      {st.bg === C.paper ? <Film f={f + 1200} strength={0.7} /> : null}
    </AbsoluteFill>
  );
};
