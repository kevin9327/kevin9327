import type React from 'react';
import type {Mat} from '../lib/geom';

export type {Mat};

/** Screen-space (or level-space) clip. Ellipse rot is in degrees (SVG convention, y down). */
export type Clip =
  | {kind: 'ellipse'; cx: number; cy: number; rx: number; ry: number; rot: number}
  | {kind: 'poly'; pts: [number, number][]};

/**
 * Props every level layer receives.
 * - f: GLOBAL loop frame 0..383 (already loopF-wrapped). Local time = f - window start.
 * - px: the level's on-screen scale (1 = identity, <1 inside a portal, >1 zooming past).
 * - M: level -> screen matrix (the Stack already wraps Base/Overlay in it; use it only for culling / LOD).
 * - boil: 0.35 <= px <= 1.05.
 * - layer: which layer is being drawn (use it in filter ids: `boil-L{k}-{layer}`).
 * - visible: false only for an always-mounted Html layer whose level is not in the chain.
 */
export type LevelRenderProps = {f: number; px: number; M: Mat; boil: boolean; layer: 'base' | 'overlay'; visible: boolean};

export type LevelModule = {
  id: 0 | 1 | 2 | 3;
  /** Colour this level's frame shows at tiny px; must equal the parent's pupil colour (STUB[id]). */
  stub: string;
  Base: React.FC<LevelRenderProps>;
  Overlay?: React.FC<LevelRenderProps>;
  Html?: React.FC<LevelRenderProps & {clips: Clip[]}>;
  /** Live clip of the portal to level id+1, in THIS level's coordinates; null when closed. */
  portalClip: (f: number) => Clip | null;
  /** Optional [text, font, size] triples to prewarm theme.measure() in FontGate. */
  warm?: [string, string, number][];
};

export type LevelView = {
  k: 0 | 1 | 2 | 3;
  depth: number;
  M: Mat;
  px: number;
  /** Ancestor portal clips in SCREEN space, outermost first. */
  clips: Clip[];
  blur: number;
  kind: 'level' | 'stub';
  stubColor?: string;
};

export type View = {
  f: number;
  D: number;
  c: number;
  u: number;
  levels: LevelView[];
  /** Camera fixed point (zStar of the current portal) in screen space. */
  fixed: [number, number];
  /** Zoom velocity in e-folds per OUTPUT frame (2 comp frames). */
  vel: number;
  rollDeg: number;
};
