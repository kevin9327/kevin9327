import React from 'react';
import {AbsoluteFill, Sequence} from 'remotion';
import {S1Terminal} from './scenes/S1Terminal';
import {S2Chase} from './scenes/S2Chase';
import {S3Curve} from './scenes/S3Curve';
import {S4Cursor} from './scenes/S4Cursor';
import {S5Fix} from './scenes/S5Fix';
import {S6Blitz} from './scenes/S6Blitz';
import {S7Title} from './scenes/S7Title';
import {C} from './lib/theme';

export const SCENES = [
  {from: 0, dur: 120, C: S1Terminal},
  {from: 120, dur: 180, C: S2Chase},
  {from: 300, dur: 120, C: S3Curve},
  {from: 420, dur: 120, C: S4Cursor},
  {from: 540, dur: 120, C: S5Fix},
  {from: 660, dur: 120, C: S6Blitz},
  {from: 780, dur: 120, C: S7Title},
];

export const Reel: React.FC = () => (
  <AbsoluteFill style={{background: C.black}}>
    {SCENES.map((s, i) => (
      <Sequence key={i} from={s.from} durationInFrames={s.dur}>
        <s.C />
      </Sequence>
    ))}
  </AbsoluteFill>
);
