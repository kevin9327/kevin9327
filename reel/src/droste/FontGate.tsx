/**
 * Gates rendering on fonts so no frame is ever laid out with fallback metrics
 * (that drift would break the bit-exact seam and every charXs / measure() layout).
 */
import React, {useEffect, useState} from 'react';
import {cancelRender, continueRender, delayRender} from 'remotion';
import {F, measure} from '../lib/theme';

export const fontSpecs = () => [
  `700 104px "${F.mono}"`,
  `400 36px "${F.mono}"`,
  `104px "${F.cartoon}"`,
  `30px "${F.hand}"`,
];

export const FontGate: React.FC<{warm: [string, string, number][]; children: React.ReactNode}> = ({warm, children}) => {
  const [handle] = useState(() => delayRender('fonts'));
  const [ready, setReady] = useState(false);
  useEffect(() => {
    let alive = true;
    const specs = fontSpecs();
    (async () => {
      await Promise.all(specs.map((s) => document.fonts.load(s)));
      await document.fonts.ready;
      const bad = specs.filter((s) => !document.fonts.check(s));
      if (bad.length) throw new Error(`FontGate: fonts not loaded: ${bad.join(' | ')}`);
      for (const [text, font, size] of warm) {
        measure(text, font, size);
        for (const ch of text) measure(ch, font, size);
      }
      if (alive) setReady(true);
    })().catch((e) => cancelRender(e));
    return () => {
      alive = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  useEffect(() => {
    if (ready) continueRender(handle);
  }, [ready, handle]);
  return ready ? <>{children}</> : null;
};
