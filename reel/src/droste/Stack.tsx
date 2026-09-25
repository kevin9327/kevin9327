/**
 * The Droste compositor. One absolutely positioned <svg> per level layer:
 *   1. night AbsoluteFill
 *   2. Base layers, outer -> inner (each: screen-space clipPaths of its ancestors, nested, then matrix(M))
 *      A 'stub' entry fills its portal clip with the stub colour instead of drawing the level.
 *   3. Html then Overlay layers, inner -> outer (same clips / matrix / blur). Html layers are ALWAYS mounted
 *      (visible=false when their level is not in the chain) so e.g. a WebGL context is created once per tab.
 *   4. ZoomLines at view.fixed.
 * Only the depth-0 level is blurred (CSS filter). Layers are drawn PAD units larger than the frame on every
 * side so the blur's edge falloff stays outside the visible 1200x500 frame (no dark fringe on cream L2).
 */
import React from 'react';
import {AbsoluteFill} from 'remotion';
import {matStr} from '../lib/geom';
import {C} from '../lib/palette';
import {view} from './camera';
import {ZoomLines} from './fx';
import {LEVELS} from './levels';
import {H, STUB, W} from './timeline';
import type {Clip, LevelRenderProps, LevelView} from './types';

export const PAD = 48;

const layerStyle = (blur: number): React.CSSProperties => ({
  position: 'absolute',
  left: -PAD,
  top: -PAD,
  width: W + 2 * PAD,
  height: H + 2 * PAD,
  filter: blur > 0 ? `blur(${blur}px)` : undefined,
});

export const ClipShape: React.FC<{c: Clip; fill?: string}> = ({c, fill}) =>
  c.kind === 'ellipse' ? (
    <ellipse cx={c.cx} cy={c.cy} rx={c.rx} ry={c.ry} transform={c.rot ? `rotate(${c.rot} ${c.cx} ${c.cy})` : undefined} fill={fill} />
  ) : (
    <polygon points={c.pts.map((p) => `${p[0]},${p[1]}`).join(' ')} fill={fill} />
  );

/** An svg layer with the given screen-space clips nested around its content. */
const ClipLayer: React.FC<{id: string; clips: Clip[]; blur: number; children: React.ReactNode}> = ({id, clips, blur, children}) => (
  <svg width={W + 2 * PAD} height={H + 2 * PAD} viewBox={`${-PAD} ${-PAD} ${W + 2 * PAD} ${H + 2 * PAD}`} style={layerStyle(blur)}>
    {clips.length ? (
      <defs>
        {clips.map((c, i) => (
          <clipPath key={i} id={`${id}-c${i}`} clipPathUnits="userSpaceOnUse">
            <ClipShape c={c} />
          </clipPath>
        ))}
      </defs>
    ) : null}
    {clips.reduceRight<React.ReactNode>((acc, _c, i) => <g clipPath={`url(#${id}-c${i})`}>{acc}</g>, children)}
  </svg>
);

const propsFor = (lv: LevelView, f: number, layer: 'base' | 'overlay'): LevelRenderProps => ({
  f,
  px: lv.px,
  M: lv.M,
  boil: lv.px >= 0.35 && lv.px <= 1.05,
  layer,
  visible: true,
});

export const Stack: React.FC<{f: number; zoomLines?: boolean}> = ({f, zoomLines = true}) => {
  const v = view(f);
  const chain = v.levels;
  const bases = chain.map((lv) => {
    const id = `dz-L${lv.k}-base`;
    if (lv.kind === 'stub') {
      const last = lv.clips[lv.clips.length - 1];
      return (
        <ClipLayer key={`base-${lv.k}`} id={id} clips={lv.clips.slice(0, -1)} blur={lv.blur}>
          <ClipShape c={last} fill={lv.stubColor ?? STUB[lv.k]} />
        </ClipLayer>
      );
    }
    const L = LEVELS[lv.k];
    return (
      <ClipLayer key={`base-${lv.k}`} id={id} clips={lv.clips} blur={lv.blur}>
        <g transform={matStr(lv.M)}>
          <L.Base {...propsFor(lv, f, 'base')} />
        </g>
      </ClipLayer>
    );
  });

  // Html + Overlay, inner -> outer. Html layers of levels outside the chain stay mounted, hidden.
  const tops: React.ReactNode[] = [];
  const inChain = new Set(chain.filter((lv) => lv.kind === 'level').map((lv) => lv.k));
  for (const L of LEVELS) {
    if (L.Html && !inChain.has(L.id)) {
      tops.push(
        <div key={`html-${L.id}`} style={{position: 'absolute', left: 0, top: 0, width: W, height: H}}>
          <L.Html f={f} px={0} M={[1, 0, 0, 1, 0, 0]} boil={false} layer="overlay" visible={false} clips={[]} />
        </div>,
      );
    }
  }
  for (const lv of chain.slice().reverse()) {
    if (lv.kind === 'stub') continue;
    const L = LEVELS[lv.k];
    if (L.Html) {
      tops.push(
        <div key={`html-${L.id}`} style={{position: 'absolute', left: 0, top: 0, width: W, height: H, filter: lv.blur > 0 ? `blur(${lv.blur}px)` : undefined}}>
          <L.Html {...propsFor(lv, f, 'overlay')} clips={lv.clips} />
        </div>,
      );
    }
    if (L.Overlay) {
      tops.push(
        <ClipLayer key={`ov-${L.id}`} id={`dz-L${lv.k}-overlay`} clips={lv.clips} blur={lv.blur}>
          <g transform={matStr(lv.M)}>
            <L.Overlay {...propsFor(lv, f, 'overlay')} />
          </g>
        </ClipLayer>,
      );
    }
  }

  const lineColor = STUB[v.c] === C.cream ? C.ink : C.cream;
  return (
    <AbsoluteFill style={{background: C.night, overflow: 'hidden'}}>
      {bases}
      {tops}
      {zoomLines && v.vel >= 0.12 ? (
        <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} style={{position: 'absolute', left: 0, top: 0}}>
          <ZoomLines f={f} cx={v.fixed[0]} cy={v.fixed[1]} vel={v.vel} color={lineColor} />
        </svg>
      ) : null}
    </AbsoluteFill>
  );
};
