import React from 'react';
import {AbsoluteFill, useCurrentFrame} from 'remotion';
import {Bug, Hero} from '../lib/characters';
import {Boil, Film, HandText, Splat} from '../lib/fx';
import {C, F, H, W, eio, ei, jit, lerp, measure, pop} from '../lib/theme';

const LANES = [400, 640, 880];
const MONO = 40;
const HERO_S = 1.6;
const SPEED = 17;
const HERO_SCREEN_X = 640;
const JUMP = 12;
const FS = 82;

const CODE = [
  "if (total === 0) return null;   // 0/0 is NaN, not null   ·   rows.sort((a, b) => a.period_end - b.period_end)   ·   if (total === 0) return null;   ·   ",
  "- ts = datetime.utcnow()   + ts = cn_now()   ·   - open(path)   + open(path, encoding='utf-8')   ·   - return value * 100   + return value   ·   ",
  "for (const f of chunk) { if (binary(f)) continue; }   ·   git -c core.quotepath=false grep   ·   Duration::try_from_secs_f64(s).ok()   ·   ",
];

const FACTS = [
  {t: 8, text: '0/0 is NaN, not null', x: 640, y: 215, r: -3},
  {t: 42, text: "1.23% became 'up 123%'", x: 1280, y: 225, r: 2.5},
  {t: 76, text: 'UTC midnight ate 9 hours', x: 700, y: 230, r: 2},
  {t: 110, text: "None became the string 'None'", x: 1180, y: 210, r: -2},
  {t: 142, text: 'cp949 could not encode a dash', x: 960, y: 225, r: 1},
];

type Sched = [number, number][];
const HERO_PLAN: Sched = [[0, 1], [30, 0], [66, 2], [104, 1], [140, 0]];
const BUG_PLAN: Sched = [[0, 1], [20, 0], [56, 2], [94, 1], [130, 0]];

const worldX = (f: number) => 300 + f * SPEED;
const feet = (lane: number) => LANES[lane] + 8;

/** y of feet and whether airborne, for a lane plan with parabolic hops. */
const track = (plan: Sched, f: number) => {
  let lane = plan[0][1];
  for (let i = 1; i < plan.length; i++) {
    const [t0, to] = plan[i];
    if (f < t0) break;
    const from = plan[i - 1][1];
    if (f < t0 + JUMP) {
      const u = (f - t0) / JUMP;
      const y = feet(from) + (feet(to) - feet(from)) * eio(u) - Math.sin(u * Math.PI) * 170;
      return {y, air: true, lane: to};
    }
    lane = to;
  }
  return {y: feet(lane), air: false, lane};
};

/** x-intervals of each lane the hero has already run across (these get inked). */
const inked = (f: number) => {
  const out: [number, number][][] = LANES.map(() => []);
  for (let i = 0; i < HERO_PLAN.length; i++) {
    const [t0, lane] = HERO_PLAN[i];
    const start = i === 0 ? 0 : t0 + JUMP;
    const end = i + 1 < HERO_PLAN.length ? HERO_PLAN[i + 1][0] : 999;
    if (f <= start) continue;
    out[lane].push([worldX(start) - 30, worldX(Math.min(end, f)) + 20]);
  }
  return out;
};

/** 4–10 s. Chase across lines of code; every step inks the pencil line underfoot. */
export const S2Chase: React.FC = () => {
  const f = useCurrentFrame();
  const hx = worldX(f);
  const cam = hx - HERO_SCREEN_X;
  const hero = track(HERO_PLAN, f);
  const bug = track(BUG_PLAN, f);
  const bugX = hx + 500 + Math.sin(f * 0.13) * 50;
  const ink = inked(f);
  const intro = lerp(f, [0, 8], [1, 0], eio);
  const out = lerp(f, [162, 178], [0, 1], ei);

  const steps: number[] = [];
  for (let t = 4; t <= f; t += 7) {
    if (!track(HERO_PLAN, t).air) steps.push(t);
  }

  return (
    <AbsoluteFill style={{background: C.paper}}>
      <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`}>
        <defs>
          <Boil id="b2" f={f} scale={3} />
          {ink.map((iv, lane) => (
            <clipPath id={`ink${lane}`} key={lane}>
              {iv.map(([a, b], j) => (
                <rect key={j} x={a} y={LANES[lane] - 80} width={Math.max(0, b - a)} height={120} />
              ))}
            </clipPath>
          ))}
        </defs>
        {/* animation-paper details: ruled lines + registration peg holes */}
        {Array.from({length: 14}, (_, i) => (
          <line key={i} x1={0} y1={80 + i * 74} x2={W} y2={80 + i * 74} stroke="#cdbf9f" strokeWidth={1.5} opacity={0.5} />
        ))}
        <g fill="#cbbd9c">
          <circle cx={W / 2 - 220} cy={46} r={16} />
          <rect x={W / 2 - 60} y={34} width={120} height={24} rx={12} />
          <circle cx={W / 2 + 220} cy={46} r={16} />
        </g>
        {/* facts: handwritten, then erased */}
        {FACTS.map((fa, i) => {
          const lt = f - fa.t;
          if (lt < 0 || lt > 30) return null;
          const s = 0.5 + 0.5 * pop(f, fa.t, 8, 220);
          const erase = lerp(lt, [22, 30], [0, 1], eio);
          const tw = measure(fa.text, F.hand, FS);
          const ex = fa.x - tw / 2 - 60 + erase * (tw + 120);
          return (
            <g key={i}>
              <defs>
                <clipPath id={`er${i}`}>
                  <rect x={ex} y={0} width={W} height={400} />
                </clipPath>
              </defs>
              <g clipPath={`url(#er${i})`} transform={`translate(${fa.x} ${fa.y}) scale(${s}) translate(${-fa.x} ${-fa.y})`} filter="url(#b2)">
                <HandText text={fa.text} x={fa.x} y={fa.y} size={FS} progress={lerp(lt, [0, 12], [0, 1])} font={F.hand} color={C.ink} rotate={fa.r} stroke={2.5} />
                <path
                  d={`M ${fa.x - tw / 2} ${fa.y + 30} q ${tw / 4} 16 ${tw / 2} 0 t ${tw / 2} 4`}
                  stroke={C.red}
                  strokeWidth={7}
                  fill="none"
                  strokeLinecap="round"
                  strokeDasharray={tw + 40}
                  strokeDashoffset={(tw + 40) * (1 - lerp(lt, [8, 16], [0, 1]))}
                  transform={`rotate(${fa.r} ${fa.x} ${fa.y})`}
                />
              </g>
              {erase > 0 && erase < 1 ? (
                <g transform={`translate(${ex} ${fa.y - 20}) rotate(-12)`}>
                  <rect x={-36} y={-44} width={72} height={88} rx={10} fill="#e9a3a3" stroke={C.ink} strokeWidth={4} />
                  <rect x={-36} y={10} width={72} height={34} rx={6} fill="#6f8fb3" stroke={C.ink} strokeWidth={4} />
                </g>
              ) : null}
            </g>
          );
        })}
        <g transform={`translate(${-cam + intro * 900} 0)`}>
          {/* pencil layer */}
          {LANES.map((y, lane) => (
            <g key={`p${lane}`}>
              <line x1={0} y1={y + 12} x2={4200} y2={y + 12} stroke={C.pencil} strokeWidth={3} strokeDasharray="14 10" />
              <text x={40} y={y} fontFamily={F.mono} fontSize={MONO} fill={C.pencil} opacity={0.75}>
                {CODE[lane]}
                {CODE[lane]}
              </text>
            </g>
          ))}
          {/* ink layer, only where the hero has run */}
          {LANES.map((y, lane) => (
            <g key={`i${lane}`} clipPath={`url(#ink${lane})`}>
              <line x1={0} y1={y + 12} x2={4200} y2={y + 12} stroke={C.ink} strokeWidth={6} />
              <text x={40} y={y} fontFamily={F.mono} fontSize={MONO} fill={C.ink} fontWeight={700}>
                {CODE[lane]}
                {CODE[lane]}
              </text>
            </g>
          ))}
          {steps.map((t) => (
            <Splat key={t} x={worldX(t) - 10} y={track(HERO_PLAN, t).y + 6} r={9} seed={t} o={0.85} />
          ))}
          <Bug x={bugX} y={bug.y - 42 * 1.55} s={1.55} f={f} run={f * 1.1} boilId="b2" rot={bug.air ? -18 : jit(f, 2, 4, 2)} />
          <Hero
            x={hx}
            y={hero.y - 92 * HERO_S}
            s={HERO_S}
            f={f}
            run={hero.air ? null : f * 0.75}
            jump={hero.air}
            arms={hero.air ? 'up' : 'run'}
            mood="determined"
            look={1}
            lean={hero.air ? -6 : 8}
            boilId="b2"
          />
        </g>
        {out > 0 ? <Splat x={HERO_SCREEN_X} y={hero.y - 100} r={out * 2600} color={C.night} seed={9} /> : null}
      </svg>
      <Film f={f + 300} strength={1 - out} />
    </AbsoluteFill>
  );
};
