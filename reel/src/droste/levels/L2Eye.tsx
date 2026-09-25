/**
 * L2: the Bug's compound eye. 32 facets (one per repo, rank order, rings outward), '535' in the centre.
 *
 * Layers
 * - Base: cream eye-white, the flat-top hex lattice (fills + one groove path), the facet flip tiles.
 *   Below px 0.06 it is ONLY cream + a night circle r = PUPIL_R2 (the stub that matches the Bug's left pupil).
 * - Html (Cornea.tsx): the cel cornea highlights + glint (WebGL2, SVG fallback).
 * - Overlay (above the cornea, so it never washes the print out): facet names and counts, the stub tip mask,
 *   the centre rim flash, the '535' slam and its subline.
 * - Impact (f188-189): Base and Overlay go through the two-tone filter; the cornea hides.
 * The centre hex is portal C: L3 (night) owns it. L2 never draws inside it except the stub circle, the impact
 * frame's ink fill and the '535' overlay (which fades out during Dive C).
 */
import React from 'react';
import {C} from '../../lib/palette';
import {F, measure} from '../../lib/theme';
import {clamp01, eo, mixHex} from '../anim';
import {viewRect} from '../camera';
import {Impact2ToneDefs, PopNumber, drosteProps} from '../fx';
import {PUPIL_R2} from '../portals';
import type {Facet} from '../timeline';
import {CENTER, DATA, EV, FACETS, HEX_R} from '../timeline';
import type {LevelModule, LevelRenderProps} from '../types';
import {Cornea} from './Cornea';
import {
  cellsIn,
  countUp,
  detailT,
  flipX,
  grooveA,
  grooveW,
  hexVerts,
  isImpact,
  L2_FREEZE,
  l2PortalClip,
  litColor,
  overlayFade,
  polyD,
  rimFlash,
  slamT,
  sublineOn,
} from './L2.pose';

const LV = 2;
const idOf = (kind: string, layer: string) => kind + '-L' + LV + '-' + layer;
/** Flip about the facet centre as one matrix (x' = sx x + (1 - sx) cx). */
const flipMat = (sx: number, cx: number) => 'matrix(' + [sx, 0, 0, 1, cx * (1 - sx), 0].join(' ') + ')';

/** Socket colour seen behind a facet while it flips edge-on (a mid shadow tone, not a black hole). */
const SOCKET = C.pencil;

/* ------------------------------------------------------------ name layout */

type NameLayout = {lines: {text: string; dy: number}[]; size: number};
const nameCache = new Map<string, NameLayout>();
/**
 * size = min(17, 118 / measure(name, mono, 1)); below 13 split at '-' into 2 lines sized to the longer part.
 * One line at y-18.
 * Two lines: the spec's y-30 / y-12 put the second line's descenders into the Luckiest count (cap top ~y-14),
 * so the pair sits at y-38.5 / y-21, the longer part goes BELOW (the hex is wider there) and is sized to fit the
 * hex at that height (100 u instead of 118 u).
 */
const nameLayout = (name: string): NameLayout => {
  const hit = nameCache.get(name);
  if (hit) return hit;
  const one = Math.min(17, 118 / measure(name, F.mono, 1));
  let out: NameLayout = {lines: [{text: name, dy: -18}], size: one};
  if (one < 13) {
    let best: [string, string] | null = null;
    for (let i = 0; i < name.length; i++) {
      if (name[i] !== '-') continue;
      const cand: [string, string] = [name.slice(0, i + 1), name.slice(i + 1)];
      const worse = (p: [string, string]) => Math.max(p[0].length, p[1].length);
      if (!best || worse(cand) < worse(best) || (worse(cand) === worse(best) && cand[1].length > best[1].length)) best = cand;
    }
    if (best) {
      const longer = best[0].length >= best[1].length ? best[0] : best[1];
      out = {lines: [{text: best[0], dy: -38.5}, {text: best[1], dy: -21}], size: Math.min(17, 100 / measure(longer, F.mono, 1))};
    }
  }
  if (typeof document !== 'undefined' && document.fonts.check('700 17px "' + F.mono + '"')) nameCache.set(name, out);
  return out;
};

/* ------------------------------------------------------------------ Base */

const Base: React.FC<LevelRenderProps> = ({f, px, M, layer}) => {
  const t = detailT(px);
  const impact = drosteProps().impact && isImpact(f);
  const cells = t > 0 ? cellsIn(viewRect(M, HEX_R)) : [];
  const ga = grooveA(px);
  const flipping: {fc: Facet; sx: number}[] = [];

  const fills = cells.map((c) => {
    let fill: string;
    if (c.centre) fill = C.night;
    else if (!c.fc) fill = C.paper;
    else {
      const sx = flipX(f, c.fc);
      if (sx === null) fill = C.paper;
      else if (sx === 1) fill = litColor(c.fc);
      else {
        flipping.push({fc: c.fc, sx});
        fill = SOCKET;
      }
    }
    return <path key={c.q + ',' + c.r} d={polyD(hexVerts(c.x, c.y))} fill={c.centre ? fill : mixHex(C.cream, fill, t)} />;
  });

  const content = (
    <>
      <rect x={-1e5} y={-1e5} width={2e5} height={2e5} fill={C.cream} />
      {t < 1 ? <circle cx={CENTER[0]} cy={CENTER[1]} r={PUPIL_R2} fill={C.night} opacity={1 - t} /> : null}
      {fills}
      {ga > 0 ? (
        <path
          d={cells.map((c) => polyD(hexVerts(c.x, c.y))).join('')}
          fill="none"
          stroke={C.ink}
          strokeWidth={grooveW(px)}
          strokeOpacity={ga}
          strokeLinejoin="round"
        />
      ) : null}
      {flipping.map(({fc, sx}) => (
        <path
          key={'flip' + fc.rank}
          d={polyD(hexVerts(fc.x, fc.y, HEX_R, sx))}
          fill={litColor(fc)}
          stroke={C.ink}
          strokeWidth={3}
          strokeLinejoin="round"
        />
      ))}
    </>
  );
  if (!impact) return <g>{content}</g>;
  const id = idOf('impact', layer);
  return (
    <g>
      <defs>
        <Impact2ToneDefs id={id} dark={C.ink} light={C.cream} />
      </defs>
      <g filter={'url(#' + id + ')'}>{content}</g>
    </g>
  );
};

/* --------------------------------------------------------------- Overlay */

const FacetText: React.FC<{fc: Facet; f: number}> = ({fc, f}) => {
  const sx = flipX(f, fc);
  // No print on the edge-on sliver frame; it rides the flip overshoot, then settles.
  if (sx === null || sx < 1) return null;
  const n = String(countUp(f, fc));
  const tf = sx === 1 ? undefined : flipMat(sx, fc.x);
  if (!fc.named) {
    return (
      <text x={fc.x} y={fc.y + 9} transform={tf} textAnchor="middle" fontFamily={F.mono} fontWeight={700} fontSize={24} fill={C.ink}>
        {n}
      </text>
    );
  }
  const nl = nameLayout(fc.repo);
  return (
    <g transform={tf}>
      {nl.lines.map((ln) => (
        <text key={ln.dy} x={fc.x} y={fc.y + ln.dy} textAnchor="middle" fontFamily={F.mono} fontWeight={700} fontSize={nl.size} fill={C.ink}>
          {ln.text}
        </text>
      ))}
      <text
        x={fc.x}
        y={fc.y + 16}
        textAnchor="middle"
        fontFamily={F.cartoon}
        fontSize={40}
        fill={C.ink}
        stroke={C.cream}
        strokeWidth={5}
        strokeLinejoin="round"
        style={{paintOrder: 'stroke'}}
      >
        {n}
      </text>
    </g>
  );
};

const HEX_C = polyD(hexVerts(CENTER[0], CENTER[1]));
const TIP_BOX = 'M' + [CENTER[0] - 80, CENTER[1] - 80].join(' ') + 'h160v160h-160Z';
const circleD = (cx: number, cy: number, r: number) =>
  'M' + (cx - r) + ' ' + cy + 'a' + [r, r, 0, 1, 0, 2 * r, 0].join(' ') + 'a' + [r, r, 0, 1, 0, -2 * r, 0].join(' ') + 'Z';

const SUBLINE = () => 'merged · ' + DATA.repos + ' repos';
const SUB_SIZE = 22;
/**
 * The spec puts the subline at (600,302), but at 22 u it is 224 u wide, the centre hex is 144 u, and the ring of
 * top-10 names sits exactly there (openpost, tick-stock-panel): cream on cream, text on text. So it is the eye's
 * caption instead: centred under the lattice at y 478, on a night plate, where no facet carries print.
 */
const SUB_Y = 478;
/** 'merged · N repos': cream mono on a night plate; rises in from under the frame edge as the slam's follow-through. */
const Subline: React.FC<{f: number}> = ({f}) => {
  const w = measure(SUBLINE(), F.mono, SUB_SIZE);
  const h = 32;
  const rise = 36 * (1 - eo(clamp01((Math.min(f, L2_FREEZE) - (EV.slam + 2)) / 6)));
  return (
    <g transform={rise ? 'translate(0 ' + rise.toFixed(3) + ')' : undefined}>
      <rect x={600 - w / 2 - 14} y={SUB_Y - 23} width={w + 28} height={h} rx={h / 2} fill={C.night} />
      <text x={600} y={SUB_Y} textAnchor="middle" fontFamily={F.mono} fontWeight={700} fontSize={SUB_SIZE} fill={C.cream} style={{whiteSpace: 'pre'}}>
        {SUBLINE()}
      </text>
    </g>
  );
};

const Overlay: React.FC<LevelRenderProps> = ({f, px, M, layer}) => {
  const t = detailT(px);
  const impact = drosteProps().impact && isImpact(f);
  const box = viewRect(M, HEX_R);
  const texts = FACETS.filter((fc) => fc.x >= box[0] && fc.x <= box[2] && fc.y >= box[1] && fc.y <= box[3]);
  const o = overlayFade(px);
  const st = slamT(f);
  const tipId = idOf('tip', layer);

  const content = (
    <>
      {/* Stub: L3's night hex pokes past the night circle at its six tips; mask them back to cream until the crossfade. */}
      {t < 1 ? (
        <>
          <defs>
            <clipPath id={tipId} clipPathUnits="userSpaceOnUse">
              <path d={HEX_C} />
            </clipPath>
          </defs>
          <path d={TIP_BOX + circleD(CENTER[0], CENTER[1], PUPIL_R2)} fillRule="evenodd" fill={C.cream} opacity={1 - t} clipPath={'url(#' + tipId + ')'} />
        </>
      ) : null}
      {impact ? <path d={HEX_C} fill={C.ink} /> : null}
      {texts.map((fc) => (
        <FacetText key={fc.rank} fc={fc} f={f} />
      ))}
      {rimFlash(f) ? <path d={HEX_C} fill="none" stroke={C.green} strokeWidth={6} strokeLinejoin="round" /> : null}
      {o > 0 ? (
        <g opacity={o}>
          <PopNumber text={String(DATA.total)} x={600} y={262} size={104} t={st} fill={C.cream} stroke={C.ink} strokeW={10} />
          {sublineOn(f) ? <Subline f={f} /> : null}
        </g>
      ) : null}
    </>
  );
  if (!impact) return <g>{content}</g>;
  const id = idOf('impact', layer);
  return (
    <g>
      <defs>
        <Impact2ToneDefs id={id} dark={C.ink} light={C.cream} />
      </defs>
      <g filter={'url(#' + id + ')'}>{content}</g>
    </g>
  );
};

export const L2: LevelModule = {
  id: 2,
  stub: C.cream,
  Base,
  Overlay,
  Html: Cornea,
  portalClip: l2PortalClip,
  // The caption, and every candidate line of a split name (prefix keeps its '-'), so nothing measures cold.
  warm: [
    [SUBLINE(), F.mono, SUB_SIZE] as [string, string, number],
    ...FACETS.filter((fc) => fc.named).flatMap((fc) =>
      Array.from(fc.repo)
        .map((ch, i) => (ch === '-' ? [fc.repo.slice(0, i + 1), fc.repo.slice(i + 1)] : []))
        .flat()
        .map((s) => [s, F.mono, 1] as [string, string, number]),
    ),
  ],
};
