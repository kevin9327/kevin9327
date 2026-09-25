/**
 * L2's cel-shaded cornea (the Html layer of L2): a flat two-tone highlight dome per facet plus one glint band.
 *
 * GL path (default): ONE WebGL2 context per tab, created lazily on first draw (never at import: ProfileReel bundles
 * this module too), held in a module singleton together with its canvas. The canvas is re-parented into whatever
 * container is mounted, so a remount never creates a second context. Drawn in useLayoutEffect under
 * delayRender/continueRender; cleared every frame (no accumulated state); throws on context loss.
 * SVG path ({cornea:'svg'}): the same look: a static crescent per facet and the glint as an exact polygon band.
 *
 * Both skip the centre facet: it is portal C, owned by L3.
 */
import React, {useLayoutEffect, useRef} from 'react';
import {continueRender, delayRender, getInputProps} from 'remotion';
import {matInv, matStr} from '../../lib/geom';
import {viewRect} from '../camera';
import {drosteProps} from '../fx';
import {CENTER, H, HEX_R, W} from '../timeline';
import type {Clip, LevelRenderProps} from '../types';
import {CORNEA, cellsIn, corneaFade, hexVerts, polyD, sweep} from './L2.pose';

type CorneaProps = LevelRenderProps & {clips: Clip[]};

/** Alignment check only: {corneaDebug:true} draws the shader's cell edges in red instead of the cornea. */
const debugOn = () => (getInputProps() as {corneaDebug?: boolean}).corneaDebug === true;

/* ------------------------------------------------------------------ GLSL */

const VS = ['#version 300 es', 'in vec2 aPos;', 'void main() { gl_Position = vec4(aPos, 0.0, 1.0); }'].join('\n');

// Plain string (no template literal): the numbers grep only scans JSX text and template literals.
const FS = [
  '#version 300 es',
  'precision highp float;',
  'uniform mat3 uInv;',
  'uniform float uR;',
  'uniform vec2 uC;',
  'uniform vec3 uClip;',
  'uniform float uFade;',
  'uniform float uSweep;',
  'uniform float uKeep;',
  'uniform vec3 uLight;',
  'uniform vec2 uGDir;',
  'uniform vec3 uCol;',
  'uniform vec4 uThr;',
  'uniform vec3 uAlpha;',
  'uniform vec2 uDebug;',
  'out vec4 outColor;',
  'float aastep(float e, float v) {',
  '  float w = max(fwidth(v), 1e-6) * 0.5;',
  '  return smoothstep(e - w, e + w, v);',
  '}',
  'void main() {',
  '  vec2 fc = gl_FragCoord.xy;',
  '  float clipA = 1.0;',
  '  if (uClip.z >= 0.0) clipA = clamp(uClip.z - length(fc - uClip.xy) + 0.5, 0.0, 1.0);',
  '  if (clipA <= 0.0) discard;',
  '  vec2 p = (uInv * vec3(fc, 1.0)).xy;',
  '  vec2 d = p - uC;',
  // flat-top axial: x = 1.5 R q, y = sqrt(3) R (r + q/2)
  '  float q = d.x / (1.5 * uR);',
  '  float r = d.y / (sqrt(3.0) * uR) - 0.5 * q;',
  '  vec3 cube = vec3(q, r, -q - r);',
  '  vec3 rc = round(cube);',
  '  vec3 df = abs(rc - cube);',
  '  if (df.x > df.y && df.x > df.z) rc.x = -rc.y - rc.z;',
  '  else if (df.y > df.z) rc.y = -rc.x - rc.z;',
  '  if (rc.x == 0.0 && rc.y == 0.0 && uDebug.x < 0.5) discard;',
  '  vec2 cen = uC + vec2(1.5 * uR * rc.x, sqrt(3.0) * uR * (rc.y + 0.5 * rc.x));',
  '  vec2 l = p - cen;',
  // stay off the ink groove: distance to the nearest cell edge (flat-top edge normals at 30, 90, 150 deg)
  '  float ap = 0.8660254 * uR;',
  '  float e = max(abs(l.y), max(abs(dot(l, vec2(0.8660254, 0.5))), abs(dot(l, vec2(0.8660254, -0.5)))));',
  '  float inner = aastep(uKeep, ap - e);',
  // alignment check only ({corneaDebug:true}): the shader's own cell edges as a 3-device-px red tent line
  '  if (uDebug.x > 0.5) { float t = clamp(1.0 - (ap - e) * uDebug.y / 1.5, 0.0, 1.0); outColor = vec4(t, 0.0, 0.0, t); return; }',
  '  vec2 lr = l / uR;',
  '  vec3 n = normalize(vec3(0.9 * lr, sqrt(max(0.0, 1.0 - 0.81 * dot(lr, lr)))));',
  '  vec3 L = normalize(uLight);',
  '  float spec = pow(max(dot(reflect(-L, n), vec3(0.0, 0.0, 1.0)), 0.0), 24.0);',
  '  float hi = aastep(uThr.x, spec) * uAlpha.x;',
  '  float band = aastep(uThr.y, spec) * uAlpha.y;',
  '  float b = dot(normalize(uGDir), d / 600.0) + 0.18 * n.x - uSweep;',
  '  float glint = (1.0 - smoothstep(0.035, 0.045 + min(fwidth(b), 0.02), abs(b))) * uAlpha.z;',
  '  float a = max(hi, max(band, glint)) * uFade * clipA * inner;',
  '  outColor = vec4(uCol * a, a);',
  '}',
].join('\n');

/* ------------------------------------------------------------ singleton */

type GLState = {
  canvas: HTMLCanvasElement;
  gl: WebGL2RenderingContext;
  u: Record<string, WebGLUniformLocation | null>;
};
let S: GLState | null = null;

const compile = (gl: WebGL2RenderingContext, type: number, src: string) => {
  const sh = gl.createShader(type);
  if (!sh) throw new Error('Cornea: createShader failed');
  gl.shaderSource(sh, src);
  gl.compileShader(sh);
  if (!gl.getShaderParameter(sh, gl.COMPILE_STATUS)) throw new Error('Cornea: shader compile: ' + gl.getShaderInfoLog(sh));
  return sh;
};

const create = (): GLState => {
  const canvas = document.createElement('canvas');
  canvas.style.position = 'absolute';
  canvas.style.left = '0px';
  canvas.style.top = '0px';
  canvas.style.width = W + 'px';
  canvas.style.height = H + 'px';
  const gl = canvas.getContext('webgl2', {preserveDrawingBuffer: true, premultipliedAlpha: true, antialias: false, alpha: true});
  if (!gl) throw new Error('Cornea: WebGL2 unavailable (render with --gl=angle, or pass {cornea:"svg"})');
  const prog = gl.createProgram();
  if (!prog) throw new Error('Cornea: createProgram failed');
  gl.attachShader(prog, compile(gl, gl.VERTEX_SHADER, VS));
  gl.attachShader(prog, compile(gl, gl.FRAGMENT_SHADER, FS));
  gl.bindAttribLocation(prog, 0, 'aPos');
  gl.linkProgram(prog);
  if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) throw new Error('Cornea: link: ' + gl.getProgramInfoLog(prog));
  gl.useProgram(prog);
  const buf = gl.createBuffer();
  gl.bindBuffer(gl.ARRAY_BUFFER, buf);
  gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), gl.STATIC_DRAW);
  gl.enableVertexAttribArray(0);
  gl.vertexAttribPointer(0, 2, gl.FLOAT, false, 0, 0);
  gl.disable(gl.BLEND);
  gl.disable(gl.DEPTH_TEST);
  const names = ['uInv', 'uR', 'uC', 'uClip', 'uFade', 'uSweep', 'uKeep', 'uLight', 'uGDir', 'uCol', 'uThr', 'uAlpha', 'uDebug'];
  const u: GLState['u'] = {};
  for (const nm of names) u[nm] = gl.getUniformLocation(prog, nm);
  // Static uniforms.
  gl.uniform1f(u.uR, HEX_R);
  gl.uniform2f(u.uC, CENTER[0], CENTER[1]);
  gl.uniform3f(u.uLight, CORNEA.light[0], CORNEA.light[1], CORNEA.light[2]);
  gl.uniform2f(u.uGDir, CORNEA.glintDir[0], CORNEA.glintDir[1]);
  const col = [1, 3, 5].map((i) => parseInt(CORNEA.color.slice(i, i + 2), 16) / 255);
  gl.uniform3f(u.uCol, col[0], col[1], col[2]);
  gl.uniform4f(u.uThr, CORNEA.hi, CORNEA.band, 0, 0);
  gl.uniform3f(u.uAlpha, CORNEA.hiA, CORNEA.bandA, CORNEA.glintA);
  return {canvas, gl, u};
};

/** The tab's one context. A lost context is replaced once; losing it again throws. */
const getGL = (): GLState => {
  if (S && S.gl.isContextLost()) {
    S.canvas.remove();
    S = null;
    const again = create();
    if (again.gl.isContextLost()) throw new Error('Cornea: WebGL context lost');
    S = again;
  }
  if (!S) S = create();
  return S;
};

/** Screen circle of the innermost ancestor clip (portal B is a circle), in CSS px; null = no clip. */
const clipCircle = (clips: Clip[]): [number, number, number] | null => {
  if (!clips.length) return null;
  const c = clips[clips.length - 1];
  if (c.kind === 'ellipse') return [c.cx, c.cy, Math.min(Math.abs(c.rx), Math.abs(c.ry))];
  const n = c.pts.length;
  const cx = c.pts.reduce((a, p) => a + p[0], 0) / n;
  const cy = c.pts.reduce((a, p) => a + p[1], 0) / n;
  return [cx, cy, Math.min(...c.pts.map((p) => Math.hypot(p[0] - cx, p[1] - cy))) * Math.cos(Math.PI / n)];
};

const drawGL = (container: HTMLDivElement, p: CorneaProps, fade: number) => {
  const s = getGL();
  const {canvas, gl, u} = s;
  if (canvas.parentNode !== container) container.appendChild(canvas);
  const dpr = window.devicePixelRatio || 1;
  const w = Math.round(W * dpr);
  const h = Math.round(H * dpr);
  if (canvas.width !== w || canvas.height !== h) {
    canvas.width = w;
    canvas.height = h;
  }
  gl.viewport(0, 0, w, h);
  gl.clearColor(0, 0, 0, 0);
  gl.clear(gl.COLOR_BUFFER_BIT);
  if (p.visible && fade > 0) {
    // device px (origin bottom-left) -> CSS px (y down) -> L2 level coords (inverse of M)
    const iv = matInv(p.M);
    gl.uniformMatrix3fv(u.uInv, false, [
      iv[0] / dpr, iv[1] / dpr, 0,
      -iv[2] / dpr, -iv[3] / dpr, 0,
      iv[2] * H + iv[4], iv[3] * H + iv[5], 1,
    ]);
    const cc = clipCircle(p.clips);
    gl.uniform3f(u.uClip, cc ? cc[0] * dpr : 0, cc ? (H - cc[1]) * dpr : 0, cc ? cc[2] * dpr : -1);
    gl.uniform1f(u.uFade, fade);
    gl.uniform1f(u.uSweep, sweep(p.f));
    // keep off the groove: half its drawn width (3 u), and never less than one device px on screen
    const devPerU = Math.hypot(p.M[0], p.M[1]) * dpr;
    gl.uniform1f(u.uKeep, 1.5 + 1 / Math.max(1e-6, devPerU));
    gl.uniform2f(u.uDebug, debugOn() ? 1 : 0, devPerU);
    gl.drawArrays(gl.TRIANGLES, 0, 3);
  }
  if (gl.isContextLost()) throw new Error('Cornea: WebGL context lost');
};

const CorneaGL: React.FC<CorneaProps> = (p) => {
  const ref = useRef<HTMLDivElement>(null);
  const fade = p.visible ? corneaFade(p.f, p.px, drosteProps().impact) : 0;
  useLayoutEffect(() => {
    const handle = delayRender('cornea');
    if (ref.current) drawGL(ref.current, p, fade);
    continueRender(handle);
  });
  return <div ref={ref} style={{position: 'absolute', left: 0, top: 0, width: W, height: H}} />;
};

/* ------------------------------------------------------------------ SVG */

type P2 = [number, number];
const R = HEX_R;
const GDIR = (() => {
  const g = CORNEA.glintDir;
  const n = Math.hypot(g[0], g[1]);
  return [g[0] / n, g[1] / n] as P2;
})();

/** Clip a convex polygon to the half-plane a.x + b.y + c >= 0 (Sutherland-Hodgman). */
const clipHalf = (pts: P2[], a: number, b: number, c: number): P2[] => {
  const out: P2[] = [];
  for (let i = 0; i < pts.length; i++) {
    const P = pts[i];
    const Q = pts[(i + 1) % pts.length];
    const fp = a * P[0] + b * P[1] + c;
    const fq = a * Q[0] + b * Q[1] + c;
    if (fp >= 0) out.push(P);
    if (fp >= 0 !== fq >= 0) {
      const t = fp / (fp - fq);
      out.push([P[0] + (Q[0] - P[0]) * t, P[1] + (Q[1] - P[1]) * t]);
    }
  }
  return out;
};

/**
 * The glint inside one cell is exactly a strip: n.x = 0.9 lx / R is linear in the cell, so
 * b = b0 + gx lx + gy ly with |b| < 0.04 (the smoothstep midpoint).
 */
const glintPoly = (x: number, y: number, s: number): P2[] => {
  const b0 = (GDIR[0] * (x - CENTER[0]) + GDIR[1] * (y - CENTER[1])) / 600 - s;
  const gx = GDIR[0] / 600 + (0.18 * 0.9) / R;
  const gy = GDIR[1] / 600;
  // in absolute coords: b = gx X + gy Y + (b0 - gx x - gy y)
  const c0 = b0 - gx * x - gy * y;
  let poly = hexVerts(x, y, R - 1.5 * 1.1547);
  poly = clipHalf(poly, gx, gy, c0 + 0.04);
  poly = clipHalf(poly, -gx, -gy, -c0 + 0.04);
  return poly;
};

/** Crescent at (-0.3R, -0.32R), size 0.28R: a disc minus the same disc nudged down-right. */
const crescentD = (x: number, y: number) => {
  const r = 0.14 * R;
  const cx = x - 0.3 * R;
  const cy = y - 0.32 * R;
  const dd = 0.5 * r;
  const ux = Math.SQRT1_2;
  const uy = Math.SQRT1_2;
  const mx = cx + (dd / 2) * ux;
  const my = cy + (dd / 2) * uy;
  const hh = Math.sqrt(r * r - (dd / 2) * (dd / 2));
  const p1: P2 = [mx - hh * uy, my + hh * ux];
  const p2: P2 = [mx + hh * uy, my - hh * ux];
  // outer: the big arc of the first disc from p1 to p2 (away from the nudge); inner: the second disc back to p1
  return (
    'M' + p1[0].toFixed(3) + ' ' + p1[1].toFixed(3) +
    'A' + [r, r, 0, 1, 1, p2[0].toFixed(3), p2[1].toFixed(3)].join(' ') +
    'A' + [r, r, 0, 0, 0, p1[0].toFixed(3), p1[1].toFixed(3)].join(' ') + 'Z'
  );
};

const ClipDef: React.FC<{id: string; c: Clip}> = ({id, c}) => (
  <clipPath id={id} clipPathUnits="userSpaceOnUse">
    {c.kind === 'ellipse' ? (
      <ellipse cx={c.cx} cy={c.cy} rx={c.rx} ry={c.ry} transform={c.rot ? 'rotate(' + [c.rot, c.cx, c.cy].join(' ') + ')' : undefined} />
    ) : (
      <polygon points={c.pts.map((q) => q.join(',')).join(' ')} />
    )}
  </clipPath>
);

const CorneaSvg: React.FC<CorneaProps> = (p) => {
  const fade = p.visible ? corneaFade(p.f, p.px, drosteProps().impact) : 0;
  if (fade <= 0) return null;
  const cells = cellsIn(viewRect(p.M, HEX_R)).filter((c) => !c.centre);
  const s = sweep(p.f);
  const glints = cells.map((c) => glintPoly(c.x, c.y, s)).filter((g) => g.length >= 3);
  const body = (
    <g transform={matStr(p.M)} opacity={fade} fill={CORNEA.color}>
      <path d={cells.map((c) => crescentD(c.x, c.y)).join('')} opacity={CORNEA.hiA} />
      {glints.length ? <path d={glints.map(polyD).join('')} opacity={CORNEA.glintA} /> : null}
    </g>
  );
  return (
    <svg width={W} height={H} viewBox={'0 0 ' + W + ' ' + H} style={{position: 'absolute', left: 0, top: 0}}>
      <defs>
        {p.clips.map((c, i) => (
          <ClipDef key={i} id={'cornea-c' + i} c={c} />
        ))}
      </defs>
      {p.clips.reduceRight<React.ReactNode>((acc, _c, i) => <g clipPath={'url(#cornea-c' + i + ')'}>{acc}</g>, body)}
    </svg>
  );
};

/* ---------------------------------------------------------------- export */

export const Cornea: React.FC<CorneaProps> = (p) => (drosteProps().cornea === 'svg' ? <CorneaSvg {...p} /> : <CorneaGL {...p} />);

