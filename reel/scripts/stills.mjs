// node scripts/stills.mjs <prefix> <frame> <frame> ...  -> out/stills/<prefix>_<frame>.png, then a contact sheet
// env: ENTRY (default src/index.ts), COMP (default ProfileReel), GL (e.g. "angle" for WebGL on the GPU),
//      PROPS (JSON input props, e.g. '{"clean":true}'), SCALE (e.g. 0.5)
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {bundle} from '@remotion/bundler';
import {openBrowser, renderStill, selectComposition} from '@remotion/renderer';

const [prefix, ...frames] = process.argv.slice(2);
const entry = process.env.ENTRY || 'src/index.ts';
const id = process.env.COMP || 'ProfileReel';
const chromiumOptions = process.env.GL ? {gl: process.env.GL} : {};
const inputProps = process.env.PROPS ? JSON.parse(process.env.PROPS) : {};
const scale = process.env.SCALE ? Number(process.env.SCALE) : 1;

const serveUrl = await bundle({entryPoint: path.resolve(entry)});
const browser = await openBrowser('chrome', {chromiumOptions});
const composition = await selectComposition({serveUrl, id, inputProps, puppeteerInstance: browser});
const files = [];
for (const fr of frames.map(Number)) {
  const output = path.resolve(`out/stills/${prefix}_${fr}.png`);
  await renderStill({composition, serveUrl, output, frame: fr, inputProps, scale, chromiumOptions, puppeteerInstance: browser});
  files.push(output);
}
await browser.close({silent: true});
execFileSync('python', ['scripts/sheet.py', path.resolve(`out/sheet_${prefix}.png`), ...files], {stdio: 'inherit'});
console.log('sheet', `out/sheet_${prefix}.png`);
