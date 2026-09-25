/**
 * L3: the merge garden. 535 petals, one per merged PR, bloom day by day along the real 69-day timeline;
 * a rolling odometer counts them (and stalls, in gray, through the real Aug 9-18 plateau); the head leaps
 * into the HEAD ring, whose interior is the portal back to L0.
 *
 * Level coordinates 1200x500, night background. Everything is driven by the L3 clock (L3.pose.ts), which is
 * frozen from f286 so nothing in L3 moves during Dive D1, the silence beat or Dive D2.
 */
import React from 'react';
import {C} from '../../lib/palette';
import {F} from '../../lib/theme';
import {HandText} from '../../lib/fx';
import {lerpc, lod, mixHex, pop30} from '../anim';
import {hullPath} from '../fx';
import {DATA, EV, RING, fmtDate} from '../timeline';
import type {LevelModule, LevelRenderProps} from '../types';
import {BLOOM_AT, L3_FREEZE, l3Bloom, l3Clock, l3Count, l3CounterScale, l3Day, l3PortalClip, l3RingR, l3Stalled, odometer} from './L3.pose';

/* ---------------------------------------------------------------- layout */

const TRUNK_Y = 330;
const xDay = (d: number) => 80 + 14 * d;
const X_END = xDay(DATA.days);
/** Tick days: the first day, every 1st of a month, the last day (= 0, 14, 45, 69 for this data). */
const TICKS = [0, ...DATA.series.map((p, i) => (i > 0 && i < DATA.days && p.date.endsWith('-01') ? i : -1)).filter((i) => i > 0), DATA.days];
const TICK_Y0 = 335;
const TICK_Y1 = 345;
const TICK_LABEL_Y = 366;

const ODO = {x: 440, y: 62, w: 58, h: 100, gap: 6, cells: 3, size: 88, rx: 10};
const ODO_W = ODO.cells * ODO.w + (ODO.cells - 1) * ODO.gap;
const ODO_CX = ODO.x + ODO_W / 2;
const ODO_CY = ODO.y + ODO.h / 2;
/** Digit baseline: JetBrains Mono cap height is 0.73 em, centred in the cell. */
const ODO_BASE = ODO_CY + (0.73 * ODO.size) / 2;

const KEY = 'every petal = 1 merged PR';
/** HandText outline width: thinner than the reel's 3 so the 30 u marker key stays crisp at 880 px. */
const KEY_STROKE = 1.4;
const HEAD_LABEL_Y = 294;

const textO = (size: number, px: number) => lod(0.73 * size * px, 3, 5);
/**
 * The axis labels (ticks, HEAD) also fade OUT once L3 is zoomed past 4-6x in Dive D1. In the silence beat they
 * would otherwise sit at the frame edges as blurred slivers of 150 px letters, and Chrome's GPU raster of
 * glyphs that large under the CSS blur is not bit-deterministic at --scale=2 (+-1 LSB between identical frames).
 */
const bigO = (px: number) => 1 - lod(px, 4, 6);

/* ---------------------------------------------------------------- petals */

type P2 = [number, number];

/** Petal colour by day index: [0, 34, 69] -> [blue, purple, green]. */
const petalColor = (i: number) => (i <= 34 ? mixHex(C.blue, C.purple, i / 34) : mixHex(C.purple, C.green, (i - 34) / 35));

type Fan = {i: number; k: number; L: number; h: number; c: number; color: string; rootR: number};

/**
 * One fan per day with k = deltas[i] > 0 petals. Petal j points (-60 + 120 (j + 0.5) / k) degrees from vertical,
 * length 24 + 2.9 k. The petal is a daisy petal (tapered root, strap body, round tip) whose width is sized to its
 * angular slot, so dense fans read as countable petals (scalloped tips) and sparse ones as sprouts; never under
 * the spec's 3.2 u. Filled shapes only; the night rim is a paint-order stroke under the fill (no hairlines).
 */
const FANS: Fan[] = DATA.deltas.flatMap((k, i) => {
  if (k <= 0) return [];
  const L = 24 + 2.9 * k;
  const slot = (0.85 * L * ((120 * Math.PI) / 180)) / k;
  const w = Math.max(3.2, Math.min(0.72 * slot, 0.26 * L));
  const h = w / 2;
  return [{i, k, L, h, c: Math.min(1.15 * h, 0.3 * L), color: petalColor(i), rootR: 2 + 0.9 * Math.sqrt(k)}];
});

/* Dev assert: one petal per merged PR, every day's petals equal its delta. */
{
  const count = FANS.reduce((a, fan) => a + fan.k, 0);
  const perDay = FANS.every((fan) => fan.k === DATA.deltas[fan.i]) && FANS.length === DATA.deltas.filter((k) => k > 0).length;
  if (count !== DATA.total || !perDay) throw new Error(`L3: petal count ${count} != ${DATA.total} or a day's petals != its delta`);
  if (fmtDate(DATA.series[TICKS[0]].date) !== fmtDate(DATA.start) || fmtDate(DATA.series[TICKS[TICKS.length - 1]].date) !== fmtDate(DATA.end)) {
    throw new Error('L3: tick labels do not span start..end');
  }
}

const K = 0.5523;
/**
 * Petal outline (tip up, root at 0,0) as cubic segments [c1, c2, end][]: a daisy petal. A short tapered base
 * (hidden under the trunk and root dot), a strap of full width 2h, and a round tip of height c.
 */
const petalSegs = (L: number, h: number, c: number): [P2, P2, P2][] => {
  const y = -(L - c);
  const yb = Math.max(0.3 * y, -0.3 * L);
  return [
    [[0.75 * h, 0.08 * y], [h, 0.18 * y], [h, yb]],
    [[h, yb + (y - yb) / 3], [h, yb + (2 * (y - yb)) / 3], [h, y]],
    [[h, y - K * c], [K * h, -L], [0, -L]],
    [[-K * h, -L], [-h, y - K * c], [-h, y]],
    [[-h, yb + (2 * (y - yb)) / 3], [-h, yb + (y - yb) / 3], [-h, yb]],
    [[-h, 0.18 * y], [-0.75 * h, 0.08 * y], [-0.5 * h, 0]],
  ];
};

const n2 = (v: number) => (Math.abs(v) < 0.005 ? '0' : v.toFixed(2));

/** Petal bend (fraction of L at the tip). Negative = cupped toward the fan's centre line, like a flower head. */
const BEND = -0.1;

/**
 * The whole fan as one path (root at 0,0): petals rotated by spread * angle_j and scaled by s. Each petal is
 * bent (rubber-hose style) toward the fan's centre line by BEND * L * t^2 (t = 0 at the root, 1 at the tip);
 * a lone petal leans left or right by day parity so single-PR days read as sprouts, not tally marks.
 */
const fanPath = (fan: Fan, s: number, spread: number) => {
  const Ls = fan.L * s;
  const segs = petalSegs(Ls, fan.h * Math.max(0.35, Math.min(1, s)), fan.c * Math.max(0.35, Math.min(1, s)));
  let d = '';
  for (let j = 0; j < fan.k; j++) {
    const a0 = -60 + (120 * (j + 0.5)) / fan.k;
    const a = (spread * a0 * Math.PI) / 180;
    const ca = Math.cos(a);
    const sa = Math.sin(a);
    const b = BEND * Ls * (fan.k === 1 ? (fan.i % 2 ? 0.6 : -0.6) : a0 / 60);
    const r = (p: P2) => {
      const t = Ls > 0 ? -p[1] / Ls : 0;
      const x = p[0] + b * t * t;
      return `${n2(x * ca - p[1] * sa)} ${n2(x * sa + p[1] * ca)}`;
    };
    const e0 = segs[segs.length - 1][2];
    d += `M${r([-e0[0], e0[1]])}`;
    for (const [c1, c2, e] of segs) d += `C${r(c1)} ${r(c2)} ${r(e)}`;
    d += 'Z';
  }
  return d;
};

const restPath = new Map<number, string>();
const fanPathAt = (fan: Fan, s: number) => {
  if (s === 1) {
    let p = restPath.get(fan.i);
    if (!p) {
      p = fanPath(fan, 1, 1);
      restPath.set(fan.i, p);
    }
    return p;
  }
  // The fan unfurls as it springs up: spread follows the same spring (overshoot included).
  return fanPath(fan, s, 0.35 + 0.65 * s);
};

/* ------------------------------------------------------------- odometer */

/**
 * One odometer wheel at position p (digit = floor(p) mod 10, rolling up by frac(p)). While the wheel spins faster
 * than it can be read, the drum is drawn a digit either side and given a vertical motion blur (sd in u), so it
 * reads as spinning instead of strobing half-digits; it snaps crisp the frame it lands.
 */
const OdoWheel: React.FC<{p: number; x: number; fill: string; blur: number; id: string}> = ({p, x, fill, blur, id}) => {
  const n = Math.floor(p + 1e-9);
  const fr = Math.max(0, p - n);
  const common = {x, textAnchor: 'middle' as const, fontFamily: F.mono, fontWeight: 700, fontSize: ODO.size, fill};
  const rows = blur > 0 ? [-1, 0, 1, 2] : fr > 0.001 ? [0, 1] : [0];
  const digits = rows.map((o) => (
    <text key={o} {...common} y={ODO_BASE + (o - fr) * ODO.h}>
      {String((((n + o) % 10) + 10) % 10)}
    </text>
  ));
  if (blur <= 0) return <>{digits}</>;
  return (
    <>
      <filter id={id} x="-20%" y="-20%" width="140%" height="140%" colorInterpolationFilters="sRGB">
        <feGaussianBlur stdDeviation={`0 ${blur}`} />
      </filter>
      <g filter={`url(#${id})`}>{digits}</g>
    </>
  );
};

/** Wheel speed (digits per comp frame) -> vertical blur sd in u; 0 while the wheel moves < 0.6 digit per output frame. */
const wheelBlur = (speed: number) => (speed < 0.3 ? 0 : Math.min(16, 8 * speed));

const Odometer: React.FC<{f: number; px: number; layer: string}> = ({f, px, layer}) => {
  const g = l3Clock(f);
  const snap = (x: number) => (Math.abs(x - Math.round(x)) < 1e-6 ? Math.round(x) : x);
  const v = snap(l3Count(g));
  const cols = odometer(v);
  // Forward difference: the wheels are sharp on the frame the count lands (f282) and through the stall.
  const vn = g >= L3_FREEZE ? v : snap(l3Count(g + 1));
  const next = odometer(vn);
  // Unwrapped wheel travel to the next frame (the ones wheel is v itself, unwrapped).
  const speed = [Math.abs(next[0] - cols[0]), Math.abs(next[1] - cols[1]), Math.abs(vn - v)];
  const fill = g >= EV.ring[0] ? C.green : l3Stalled(g) ? C.gray : C.cream;
  const sc = l3CounterScale(g);
  const strokeO = lod(3 * px, 0.6, 1.2);
  const digitO = textO(ODO.size, px);
  return (
    <g transform={sc === 1 ? undefined : `translate(${ODO_CX} ${ODO_CY}) scale(${sc}) translate(${-ODO_CX} ${-ODO_CY})`}>
      <defs>
        {cols.map((_, j) => (
          <clipPath key={j} id={`l3-odo-${layer}-${j}`}>
            <rect x={ODO.x + j * (ODO.w + ODO.gap) + 1.5} y={ODO.y + 1.5} width={ODO.w - 3} height={ODO.h - 3} rx={ODO.rx - 1.5} />
          </clipPath>
        ))}
      </defs>
      {cols.map((p, j) => {
        const x = ODO.x + j * (ODO.w + ODO.gap);
        return (
          <g key={j}>
            <rect
              x={x}
              y={ODO.y}
              width={ODO.w}
              height={ODO.h}
              rx={ODO.rx}
              fill={C.night2}
              stroke={strokeO > 0 ? C.gray : undefined}
              strokeWidth={strokeO > 0 ? 3 : undefined}
              strokeOpacity={strokeO > 0 && strokeO < 1 ? strokeO : undefined}
            />
            {digitO > 0 ? (
              <g clipPath={`url(#l3-odo-${layer}-${j})`} opacity={digitO < 1 ? digitO : undefined}>
                <OdoWheel p={p} x={x + ODO.w / 2} fill={fill} blur={wheelBlur(speed[j])} id={`l3-odo-mb-${layer}-${j}`} />
              </g>
            ) : null}
          </g>
        );
      })}
    </g>
  );
};

/* ------------------------------------------------------------------ head */

const circlePts = (cx: number, cy: number, r: number, n = 12): P2[] =>
  Array.from({length: n}, (_, i) => [cx + r * Math.cos((i / n) * 2 * Math.PI), cy + r * Math.sin((i / n) * 2 * Math.PI)] as P2);

/** The write head: a green dot with a velocity smear (the hull of its last comp-frame position and now). */
const Head: React.FC<{g: number}> = ({g}) => {
  if (g < EV.write0) return null;
  if (g >= EV.ring[0]) {
    // f282: the head leaps from the trunk into the ring (one output frame of hull smear).
    if (g !== EV.ring[0]) return null;
    const tail = xDay(l3Day(g - 1));
    return <path d={hullPath([...circlePts(tail, TRUNK_Y, 2), ...circlePts(RING.cx, RING.cy, 8)])} fill={C.green} />;
  }
  const x = xDay(l3Day(g));
  const r = 7 * pop30(g, EV.write0 - 2, 14, 400);
  const tail = g > EV.write0 ? xDay(l3Day(g - 1)) : x;
  if (x - tail < 2) return <circle cx={x} cy={TRUNK_Y} r={r} fill={C.green} />;
  return <path d={hullPath([...circlePts(tail, TRUNK_Y, 0.5 * r), ...circlePts(x, TRUNK_Y, r)])} fill={C.green} />;
};

/* ------------------------------------------------------------------ base */

const Base: React.FC<LevelRenderProps> = ({f, px, layer}) => {
  const g = l3Clock(f);
  const d = l3Day(g);
  const writing = g >= EV.write0;
  const xHead = xDay(d);
  const r = l3RingR(g);
  const trunkO = lod(4 * px, 0.6, 1.2);
  const tickO = textO(20, px) * bigO(px);
  const labelO = textO(24, px);
  const dateO = textO(30, px);
  const keyO = textO(30, px);
  const keyP = lerpc(g, EV.hand, [0, 1]);
  const headO = textO(20, px) * bigO(px);
  const popShift = ((l3CounterScale(g) - 1) * ODO_W) / 2;
  return (
    <g>
      <rect x={-1e5} y={-1e5} width={2e5} height={2e5} fill={C.night} />

      {/* petals: one path per fan, a night rim (paint-order stroke) separates overlapping fans */}
      {writing
        ? FANS.map((fan) => {
            const s = l3Bloom(g, fan.i);
            if (s <= 0.001) return null;
            return (
              <path
                key={fan.i}
                d={fanPathAt(fan, s)}
                transform={`translate(${xDay(fan.i)} ${TRUNK_Y})`}
                fill={fan.color}
                stroke={C.night}
                strokeWidth={2.4}
                strokeLinejoin="round"
                style={{paintOrder: 'stroke'}}
              />
            );
          })
        : null}

      {/* trunk: gray ahead of the head, cream behind it; ticks; connector into the ring */}
      {trunkO > 0 ? (
        <g opacity={trunkO < 1 ? trunkO : undefined}>
          <line x1={xDay(0)} y1={TRUNK_Y} x2={X_END} y2={TRUNK_Y} stroke={C.gray} strokeOpacity={0.35} strokeWidth={4} strokeLinecap="round" />
          {writing ? <line x1={xDay(0)} y1={TRUNK_Y} x2={xHead} y2={TRUNK_Y} stroke={C.cream} strokeWidth={4} strokeLinecap="round" /> : null}
          {g >= EV.ring[0] ? <line x1={X_END} y1={TRUNK_Y} x2={RING.cx - r - 4} y2={TRUNK_Y} stroke={C.cream} strokeWidth={4} /> : null}
          {TICKS.map((i) => (
            <line key={i} x1={xDay(i)} y1={TICK_Y0} x2={xDay(i)} y2={TICK_Y1} stroke={C.gray} strokeWidth={3} strokeLinecap="round" />
          ))}
        </g>
      ) : null}

      {/* root dots: the commit nodes the head plants as it passes each day */}
      {writing
        ? FANS.map((fan) =>
            g >= BLOOM_AT[fan.i] ? <circle key={fan.i} cx={xDay(fan.i)} cy={TRUNK_Y} r={fan.rootR} fill={C.cream} /> : null,
          )
        : null}

      <Head g={g} />

      {tickO > 0 ? (
        <g opacity={tickO < 1 ? tickO : undefined} fontFamily={F.mono} fontWeight={700} fontSize={20} fill={C.gray} textAnchor="middle">
          {TICKS.map((i) => (
            <text key={i} x={xDay(i)} y={TICK_LABEL_Y}>
              {fmtDate(DATA.series[i].date)}
            </text>
          ))}
        </g>
      ) : null}

      <Odometer f={g} px={px} layer={layer} />
      {labelO > 0 ? (
        <text x={424 - popShift} y={124} textAnchor="end" fontFamily={F.mono} fontWeight={700} fontSize={24} fill={C.gray} opacity={labelO < 1 ? labelO : undefined}>
          MERGED
        </text>
      ) : null}
      {dateO > 0 ? (
        <text x={640 + popShift} y={124} fontFamily={F.mono} fontWeight={700} fontSize={30} fill={C.cream} opacity={dateO < 1 ? dateO : undefined}>
          {fmtDate(DATA.series[Math.round(d)].date)}
        </text>
      ) : null}

      {keyO > 0 && keyP > 0 ? (
        <g opacity={keyO < 1 ? keyO : undefined}>
          <HandText text={KEY} x={600} y={452} size={30} progress={keyP} font={F.hand} color={C.cream} anchor="middle" stroke={KEY_STROKE} />
        </g>
      ) : null}

      {/* HEAD ring (its interior is portal D: L0 draws there) */}
      {g >= EV.ring[0] ? <circle cx={RING.cx} cy={RING.cy} r={r + 3} fill="none" stroke={C.green} strokeWidth={RING.stroke} /> : null}
      {g >= EV.ring[0] + 2 && headO > 0 ? (
        <text
          x={RING.cx}
          y={HEAD_LABEL_Y - (g < L3_FREEZE ? 5 : 0)}
          textAnchor="middle"
          fontFamily={F.mono}
          fontWeight={700}
          fontSize={20}
          fill={C.green}
          opacity={headO < 1 ? headO : undefined}
        >
          HEAD
        </text>
      ) : null}
    </g>
  );
};

export const L3: LevelModule = {id: 3, stub: C.night, Base, portalClip: l3PortalClip};
