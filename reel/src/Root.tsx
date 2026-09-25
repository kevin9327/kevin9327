import React from 'react';
import {Composition} from 'remotion';
import {Reel} from './Reel';
import {Droste} from './droste/Droste';

export const Root: React.FC = () => (
  <>
    <Composition id="ProfileReel" component={Reel} durationInFrames={900} fps={30} width={1920} height={1080} />
    <Composition id="Droste" component={Droste} durationInFrames={384} fps={30} width={1200} height={500} defaultProps={{}} />
    <Composition id="DrosteSeam" component={Droste} durationInFrames={385} fps={30} width={1200} height={500} defaultProps={{}} />
  </>
);
