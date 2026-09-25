/**
 * M1: L0 "kevin9327 ~ $" pose table for the Hero (the block cursor).
 * Pure: imports only geom, timeline, portals, anim and palette (camera.ts and the lint import it in Node).
 *
 * Global loop frames (30 fps comp, even frames ship at 15 fps):
 *   [370,384) + [0,10)  SLEEP      the literal SLEEP_L0 (seam: bit-identical on both sides)
 *   10-11               TAKE       eyes snap to 2.0, stretched tall 1.35, mouth 'o', arms up (+ hull smear at f10)
 *   12-17               settle     eyes 2.0 -> 1.7 (eo), squash 1.35 -> 0.9 -> 1 (eio)
 *   18-281              FREEZE_L0  the literal portal-A pose (Dive A; not visible after f71)
 *   282-355             AWAKE      eyes 1.25, looking up at the lens (inside HEAD, Dive D2, landing)
 *   322-325             AWAKE+blink (the silence beat's only motion)
 *   356-359             look down  lookUp 1 -> 0 (eio)
 *   360-367             grin + wave, wink LEFT on 362-367 (the right eye is the portal);
 *                       squash accent 1.06 -> 0.96 -> 1 on 360-364 (perk up on the grin, land on the wink)
 *   368-369             drowsy     eyes 0.55
 */
import {heroEyeWorld} from '../../lib/geom';
import type {HeroPose} from '../../lib/geom';
import {eio, eo, lerpc} from '../anim';
import {FREEZE_L0, SLEEP_L0} from '../portals';
import {EV, SEGN, loopF} from '../timeline';
import type {Clip} from '../types';

/** f10-11: the wake take. */
export const TAKE_L0: HeroPose = {...FREEZE_L0, eyes: 2.0, squash: 1.35, mood: 'o', arms: 'up'};

/** f282-355: awake inside HEAD and while landing home, looking up at the lens. */
export const AWAKE_L0: HeroPose = {...FREEZE_L0, eyes: 1.25, lookUp: 1, mood: 'smile', arms: 'idle'};
const AWAKE_BLINK_L0: HeroPose = {...AWAKE_L0, blink: true};

/** Squash accents on the grin (perk up) and the wink (land). */
const PERK_SQ = [1.06, 0.96];

/** Home, after the look-down: lookUp 0. */
const HOME_L0: HeroPose = {...AWAKE_L0, lookUp: 0};

export function l0Pose(f: number): HeroPose {
  const g = loopF(f);
  // seam: the literal SLEEP constant on [370,384) and [0,10)
  if (g >= EV.sleep || g < EV.take) return SLEEP_L0;
  // wake take (2 frames), then the settle
  if (g < EV.settleA) return TAKE_L0;
  if (g < EV.freezeA) {
    return {
      ...FREEZE_L0,
      eyes: lerpc(g, [EV.settleA, EV.freezeA], [TAKE_L0.eyes!, FREEZE_L0.eyes!], eo),
      squash: lerpc(g, [EV.settleA, EV.settleA + 2, EV.freezeA], [TAKE_L0.squash!, 0.9, 1], eio),
    };
  }
  // Dive A and the rest of the loop until the ring opens: the literal freeze constant
  if (g < EV.ring[0]) return FREEZE_L0;
  // inside HEAD (D1, silence, D2) and the first frames home
  if (g < EV.lookDown[0]) {
    return g >= EV.blink[0] && g < EV.blink[1] ? AWAKE_BLINK_L0 : AWAKE_L0;
  }
  if (g < EV.lookDown[1]) return {...AWAKE_L0, lookUp: lerpc(g, EV.lookDown, [1, 0], eio)};
  if (g < EV.grin[1]) {
    // the grin perks him up (stretch 1.06), the wink lands with a small squash (0.96), then he settles on 1
    const perk = lerpc(g, [EV.grin[0], EV.wink[0], EV.wink[0] + 2], [PERK_SQ[0], PERK_SQ[1], 1], eio);
    const grin: HeroPose = {...HOME_L0, mood: 'grin', arms: 'wave', squash: perk};
    return g >= EV.wink[0] && g < EV.wink[1] ? {...grin, wink: 'L'} : grin;
  }
  // drowsy (EV.drowsy), then SLEEP from EV.sleep (handled above)
  return {...HOME_L0, eyes: 0.55};
}

/**
 * Portal A (the right eye) while that eye is open; null while it is shut (blink, wink R, proud).
 * Equals CLIP[0] on f18-71 because the pose there is the literal FREEZE_L0.
 */
export function l0PortalClip(f: number): Clip | null {
  const p = l0Pose(f);
  if (p.blink || p.wink === 'R' || p.mood === 'proud') return null;
  return heroEyeWorld(p, 'R');
}

/** True on the one frame that carries the take's hull smear (f10). */
export const l0Smear = (f: number) => loopF(f) === EV.take;

/** The window in which L0 can be on screen (for documentation / checks): [282, 384) and [0, 72). */
export const L0_WINDOW = {from: EV.ring[0], to: SEGN.diveA.f1};
