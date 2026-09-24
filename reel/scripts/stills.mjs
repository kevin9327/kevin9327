// node scripts/stills.mjs <prefix> <frame> <frame> ...  -> out/stills/<prefix>_<frame>.png, then a contact sheet
import path from 'node:path';
import {execFileSync} from 'node:child_process';
import {bundle} from '@remotion/bundler';
import {openBrowser, renderStill, selectComposition} from '@remotion/renderer';

const [prefix, ...frames] = process.argv.slice(2);
const serveUrl = await bundle({entryPoint: path.resolve('src/index.ts')});
const browser = await openBrowser('chrome');
const composition = await selectComposition({serveUrl, id: 'ProfileReel', puppeteerInstance: browser});
const files = [];
for (const fr of frames.map(Number)) {
  const output = path.resolve(`out/stills/${prefix}_${fr}.png`);
  await renderStill({composition, serveUrl, output, frame: fr, puppeteerInstance: browser});
  files.push(output);
}
await browser.close({silent: true});
execFileSync('python', ['scripts/sheet.py', path.resolve(`out/sheet_${prefix}.png`), ...files], {stdio: 'inherit'});
console.log('sheet', `out/sheet_${prefix}.png`);
