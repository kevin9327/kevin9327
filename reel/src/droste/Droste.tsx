/** "535, All the Way Down": the endless recursive zoom. Registered as 'Droste' (384 f) and 'DrosteSeam' (385 f). */
import React from 'react';
import {useCurrentFrame} from 'remotion';
import {F} from '../lib/theme';
import {FontGate} from './FontGate';
import type {DrosteProps} from './fx';
import {LEVELS} from './levels';
import {Stack} from './Stack';
import {FACETS, loopF} from './timeline';

const warm = (): [string, string, number][] => [
  ['kevin9327', F.mono, 104],
  [' ~ $', F.mono, 104],
  ...FACETS.map((fc) => [fc.repo, F.mono, 1] as [string, string, number]),
  ...LEVELS.flatMap((L) => L.warm ?? []),
];

/** Input props (byte levers): {cornea?: 'gl'|'svg', zoomLines?: boolean, impact?: boolean}; all default on. */
export const Droste: React.FC<DrosteProps> = ({zoomLines}) => {
  const f = loopF(useCurrentFrame());
  return (
    <FontGate warm={warm()}>
      <Stack f={f} zoomLines={zoomLines !== false} />
    </FontGate>
  );
};
