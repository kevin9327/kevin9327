import React from 'react';
import {Composition} from 'remotion';
import {Reel} from './Reel';

export const Root: React.FC = () => (
  <Composition id="ProfileReel" component={Reel} durationInFrames={900} fps={30} width={1920} height={1080} />
);
