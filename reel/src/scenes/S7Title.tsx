import React from 'react';
import {AbsoluteFill, interpolateColors, useCurrentFrame} from 'remotion';
import data from '../data.json';
import {Bug, Hero} from '../lib/characters';
import {Boil, Film, HandText} from '../lib/fx';
import {C, F, H, W, charXs, ei, eio, eo, lerp, measure, pop} from '../lib/theme';

const NAME = 'kevin9327';
const NS = 240;
const BASE = 520;
const MONO = 64;
const CW = MONO * 0.6;
const X0 = 560;
const L1 = 420;

/** 26–30 s. The hero hand-draws the name and the numbers, then everything crumples back into the prompt cursor. */
export const S7Title: React.FC = () => {
  const f = useCurrentFrame();
  const {xs, width} = charXs(NAME, F.cartoon, NS);
  const x0 = W / 2 - width / 2;
  const p = lerp(f, [2, 40], [0, 1], eio);
  const edge = x0 + p * width;
  const sub = `${data.total} merged · ${data.repos} repos · ${data.days} days`;
  const subN = Math.max(0, Math.floor((f - 44) * 1.6));

  // crumple back into the terminal cursor
  const cr = lerp(f, [86, 102], [0, 1], ei);
  const cx = X0 + CW * 2 + CW / 2;
  const cy = L1 - 25;
  const pivotX = 960 + (cx - 960) * cr;
  const pivotY = 520 + (cy - 520) * cr;
  const bg = interpolateColors(f, [88, 100], [C.paper, C.black]);
  const endPrompt = f >= 100;
  const blinkOn = f < 108 || f >= 114;

  const proud = f >= 62;
  const heroX = proud ? lerp(f, [58, 66], [edge + 110, x0 + width + 150], eio) : edge + 110;
  const iDotX = x0 + xs[3] + measure('i', F.cartoon, NS) / 2;
  const land = lerp(f, [66, 80], [0, 1], eo);

  return (
    <AbsoluteFill style={{background: bg}}>
      <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`}>
        <defs>
          <Boil id="b7" f={f} scale={2.6} />
        </defs>
        {!endPrompt ? (
          <g transform={`translate(${pivotX} ${pivotY}) rotate(${cr * 480}) scale(${1 - cr * 0.985}) translate(-960 -520)`}>
            <g filter="url(#b7)">
              <HandText text={NAME} x={x0} y={BASE} size={NS} progress={p} font={F.cartoon} color={C.ink} anchor="start" stroke={5} />
            </g>
            <path
              d={`M ${x0} ${BASE + 40} q ${width / 2} 26 ${width} -6`}
              stroke={C.orange}
              strokeWidth={16}
              fill="none"
              strokeLinecap="round"
              strokeDasharray={width + 80}
              strokeDashoffset={(width + 80) * (1 - lerp(f, [38, 48], [0, 1]))}
            />
            <text x={960} y={680} textAnchor="middle" fontFamily={F.mono} fontSize={54} fill={C.ink} fontWeight={700}>
              {sub.slice(0, subN)}
            </text>
            <Hero
              x={heroX}
              y={640 - 92 * 1.3}
              s={1.3}
              dir={proud ? 1 : -1}
              f={f}
              arms={proud ? 'proud' : 'draw'}
              pencil={!proud}
              mood={proud ? 'proud' : 'determined'}
              squash={proud ? 1 + 0.05 * pop(f, 62, 6, 200) : 1}
              boilId="b7"
            />
            {f >= 64 ? (
              <Bug
                x={lerp(land, [0, 1], [1900, iDotX])}
                y={lerp(land, [0, 1], [120, BASE - NS * 0.82]) - Math.sin(land * Math.PI) * 120}
                s={0.62}
                f={f}
                fixed
                boilId="b7"
              />
            ) : null}
          </g>
        ) : (
          <g transform={`translate(${W / 2} ${H / 2}) scale(1.08) translate(${-W / 2} ${-H / 2})`}>
            <text x={X0} y={L1} fontFamily={F.mono} fontSize={MONO} fill={C.gray}>
              ${' '}
            </text>
            {blinkOn ? <rect x={X0 + CW * 2} y={L1 - 50} width={CW} height={64} fill={C.cream} /> : null}
          </g>
        )}
      </svg>
      <Film f={f + 1500} dark={f >= 94} strength={f >= 94 ? 0.8 : 0.55} />
    </AbsoluteFill>
  );
};
