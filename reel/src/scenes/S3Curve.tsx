import React from 'react';
import {AbsoluteFill, useCurrentFrame} from 'remotion';
import data from '../data.json';
import {Bug, Hero} from '../lib/characters';
import {Boil, Film, Splat} from '../lib/fx';
import {C, F, H, W, back, charXs, ei, eio, eo, jit, lerp, pop} from '../lib/theme';

const series = data.series as {date: string; total: number}[];
const N = series.length;
const TOTAL = data.total as number;
const DX = 70;
const ys = (total: number) => 900 - (total / TOTAL) * 640;
const BR = [C.green, C.purple, C.blue, C.orange];
const MON = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC'];
const fmt = (d: string) => `${MON[Number(d.slice(5, 7)) - 1]} ${Number(d.slice(8, 10))}`;

const totalAt = (t: number) => {
  const i = Math.max(0, Math.min(N - 1, Math.floor(t)));
  const j = Math.min(N - 1, i + 1);
  return series[i].total + (series[j].total - series[i].total) * (t - i);
};

/** 10–14 s. Color floods in; the real cumulative merge curve becomes the ground; 535 lands. */
export const S3Curve: React.FC = () => {
  const f = useCurrentFrame();
  const t = lerp(f, [4, 90], [0, N - 1], eio);
  const hx = t * DX;
  const hy = ys(totalAt(t));
  const camX = 760 - hx;
  const camY = 640 - hy;
  const slope = Math.atan2(ys(totalAt(Math.min(N - 1, t + 0.6))) - hy, 0.6 * DX) * (180 / Math.PI);
  const shown = Math.round(totalAt(t));
  const date = series[Math.max(0, Math.min(N - 1, Math.round(t)))].date;

  // 535 slam
  const slam = pop(f, 90, 9, 170);
  const DS = 560;
  const {xs, width} = charXs('535', F.cartoon, DS);
  const d0 = W / 2 - width / 2;
  const squash3 = f < 103 ? 1 : f < 108 ? lerp(f, [103, 106], [1, 0.68], eo) : 0.68 + 0.32 * pop(f, 108, 6, 260);
  const launch = lerp(f, [108, 119], [0, 1], (u) => u * u);
  const landY = 760 - DS * 0.72 * squash3;
  const heroOn3 = f >= 99;
  const shake = f >= 90 && f < 96 ? jit(f, 7, 16, 1) : 0;

  const pts = series.map((p, i) => [i * DX, ys(p.total)] as const);
  const lit = pts.filter((_, i) => i <= t).map(([x, y]) => `${x},${y}`);
  lit.push(`${hx},${hy}`);
  const allPath = pts.map(([x, y]) => `${x},${y}`).join(' ');

  return (
    <AbsoluteFill style={{background: C.night}}>
      <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`}>
        <defs>
          <Boil id="b3" f={f} scale={2.6} />
          <linearGradient id="area" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0" stopColor={C.orange} stopOpacity={0.45} />
            <stop offset="1" stopColor={C.orange} stopOpacity={0} />
          </linearGradient>
          <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="9" />
          </filter>
        </defs>
        {/* grid */}
        <g opacity={lerp(f, [0, 10], [0, 0.5])}>
          {Array.from({length: 26}, (_, i) => (
            <line key={`v${i}`} x1={((i * 80 + camX * 0.4) % W + W) % W} y1={0} x2={((i * 80 + camX * 0.4) % W + W) % W} y2={H} stroke="#21262d" strokeWidth={2} />
          ))}
          {Array.from({length: 15}, (_, i) => (
            <line key={`h${i}`} x1={0} y1={((i * 80 + camY * 0.4) % H + H) % H} x2={W} y2={((i * 80 + camY * 0.4) % H + H) % H} stroke="#21262d" strokeWidth={2} />
          ))}
        </g>
        <g transform={`translate(${shake} ${shake * 0.6})`} opacity={1 - lerp(f, [88, 96], [0, 0.75])}>
          <g transform={`translate(${camX} ${camY})`}>
            {/* branches merging into the curve */}
            {series.map((p, i) => {
              const m = i === 0 ? p.total : p.total - series[i - 1].total;
              if (m <= 0) return null;
              const x = i * DX;
              const y = ys(p.total);
              const up = i % 2 === 0 ? -1 : 1;
              const reveal = lerp(hx, [x - 900, x - 200], [0, 1]);
              const col = BR[i % 4];
              const w = 3 + Math.min(10, m) * 0.7;
              const d = `M ${x - 260} ${y + up * (150 + Math.min(m, 20) * 9)} C ${x - 120} ${y + up * 120}, ${x - 60} ${y}, ${x} ${y}`;
              return (
                <path key={`br${i}`} d={d} stroke={col} strokeWidth={w} fill="none" strokeLinecap="round" strokeDasharray={600} strokeDashoffset={600 * (1 - reveal)} opacity={0.9} />
              );
            })}
            <polyline points={allPath} stroke="#30363d" strokeWidth={6} fill="none" strokeDasharray="10 12" />
            <polygon points={`0,1400 ${lit.join(' ')} ${hx},1400`} fill="url(#area)" />
            <polyline points={lit.join(' ')} stroke={C.orange} strokeWidth={16} fill="none" filter="url(#glow)" opacity={0.7} />
            <polyline points={lit.join(' ')} stroke={C.orange} strokeWidth={8} fill="none" strokeLinejoin="round" />
            {series.map((p, i) => {
              const m = i === 0 ? p.total : p.total - series[i - 1].total;
              if (m <= 0) return null;
              const x = i * DX;
              const y = ys(p.total);
              const passed = t >= i;
              const age = (t - i) * 3;
              return (
                <g key={`c${i}`}>
                  <circle cx={x} cy={y} r={7 + Math.sqrt(m) * 3} fill={C.night} stroke={passed ? BR[i % 4] : '#30363d'} strokeWidth={5} />
                  {passed && age < 12 ? (
                    <g opacity={1 - age / 12}>
                      <circle cx={x} cy={y} r={20 + age * 9} fill="none" stroke={BR[i % 4]} strokeWidth={4} />
                      <text x={x} y={y - 40 - age * 6} fontFamily={F.cartoon} fontSize={44 + Math.min(m, 20)} fill={BR[i % 4]} textAnchor="middle">
                        +{m}
                      </text>
                    </g>
                  ) : null}
                </g>
              );
            })}
            {/* the hero surfing a commit node up the curve */}
            <g transform={`translate(${hx} ${hy}) rotate(${slope})`}>
              <circle cx={0} cy={-34} r={34} fill={C.night} stroke={C.orange} strokeWidth={8} />
              <line x1={0} y1={-34} x2={Math.cos(f * 0.9) * 30} y2={-34 + Math.sin(f * 0.9) * 30} stroke={C.orange} strokeWidth={6} />
              {!heroOn3 ? (
                <Hero x={0} y={-68 - 92 * 1.55} s={1.55} f={f} arms="up" mood="grin" lean={-6} boilId="b3" squash={1 + Math.sin(f * 0.5) * 0.04} />
              ) : null}
            </g>
          </g>
        </g>
        {/* HUD */}
        <g opacity={lerp(f, [2, 10, 86, 94], [0, 1, 1, 0])}>
          <text x={110} y={140} fontFamily={F.mono} fontSize={30} fill={C.gray} letterSpacing={4}>
            MERGED INTO OTHER PEOPLE'S REPOS
          </text>
          <text x={100} y={310} fontFamily={F.cartoon} fontSize={190} fill={C.orange}>
            {shown}
          </text>
          <text x={110} y={380} fontFamily={F.mono} fontSize={40} fill={C.cream}>
            JUL 18 → {fmt(date)}
          </text>
        </g>
        {/* 535 */}
        {f >= 90 ? (
          <g>
            <Splat x={W / 2} y={560} r={lerp(f, [90, 97], [0, 640], eo)} color={C.orange} seed={21} o={lerp(f, [90, 100], [0.5, 0])} />
            <g transform={`translate(${W / 2} 560) scale(${0.3 + 0.7 * slam}) translate(${-W / 2} -560)`} fontFamily={F.cartoon} fontSize={DS}>
              {['5', '3', '5'].map((ch, i) => {
                const x = d0 + xs[i];
                const sq = i === 1 ? squash3 : 1;
                return (
                  <g key={i} transform={`translate(0 760) scale(1 ${sq}) translate(0 -760)`}>
                    <text x={x} y={760} fill={C.orange} stroke={C.black} strokeWidth={18} paintOrder="stroke" filter="url(#b3)">
                      {ch}
                    </text>
                  </g>
                );
              })}
            </g>
            {f >= 95 ? (
              <Bug x={d0 + xs[1] + 150} y={lerp(f, [95, 99, 108, 116], [640, 300, 300, -300], eio)} s={1.5} f={f} run={f} boilId="b3" rim={C.cream} rot={-10} />
            ) : null}
            {heroOn3 ? (
              <Hero
                x={d0 + xs[1] + 160}
                y={f < 103 ? lerp(f, [99, 103], [-200, landY - 92 * 1.8], ei) : landY - 92 * 1.8 - launch * 1300}
                s={1.8}
                f={f}
                arms={f < 108 ? 'idle' : 'up'}
                jump={f < 103 || f >= 108}
                mood={f < 108 ? 'determined' : 'grin'}
                squash={f >= 103 && f < 108 ? squash3 : 1 + launch * 0.4}
                boilId="b3"
                rim={C.cream}
              />
            ) : null}
          </g>
        ) : null}
        {/* color flood intro */}
        {f < 12 ? (
          <g>
            {[C.orange, C.green, C.purple, C.blue].map((c, i) => (
              <Splat key={i} x={[500, 1500, 1100, 300][i]} y={[300, 700, 250, 900][i]} r={lerp(f, [i, 10], [0, 700], back)} color={c} seed={i + 3} o={lerp(f, [4, 12], [1, 0])} />
            ))}
          </g>
        ) : null}
      </svg>
      <Film f={f + 600} dark strength={0.35} />
    </AbsoluteFill>
  );
};
