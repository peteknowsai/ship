// node chrome/ship-tabs/test.mjs — the URL rules, then the real extension in Chrome for
// Testing (a throwaway profile, its window parked off-screen): open ship-shaped tabs and read back the groups.
import { createRequire } from 'node:module';
import { spawn } from 'node:child_process';
import { mkdtempSync, mkdirSync, writeFileSync, readFileSync, readdirSync, existsSync, rmSync } from 'node:fs';
import { createServer } from 'node:http';
import { tmpdir, homedir } from 'node:os';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const { shipGroup } = createRequire(import.meta.url)('./rules.js');
let fails = 0;
const check = (name, ok) => { console.log(`  ${ok ? 'ok  ' : 'FAIL'} ${name}`); if (!ok) fails++; };

check('a spec file is a doc', shipGroup('file:///Users/pete/Projects/app.feature-x/specs/designs/x.html') === 'ship docs');
check('a shot is a doc', shipGroup('file:///Users/pete/Projects/app/.ship-shots/x/1.png') === 'ship docs');
check('a localhost dev server is a test', shipGroup('http://localhost:3218/home') === 'ship test');
check('a *.localhost host is a test', shipGroup('http://swain.localhost:3000/') === 'ship test');
check('a Vercel branch preview is a test', shipGroup('https://cells-git-feature-x-pkai.vercel.app/') === 'ship test');
check('a production vercel.app is left alone', shipGroup('https://cells.vercel.app/') === null);
check('any other page is left alone', shipGroup('https://github.com/peteknowsai/ship') === null);
check('a stray file is left alone', shipGroup('file:///Users/pete/Downloads/a.html') === null);

// The live part needs a Chrome for Testing build (branded Chrome ignores --load-extension).
const cache = join(homedir(), '.cache/puppeteer/chrome');
const build = existsSync(cache) && readdirSync(cache).filter((d) => d.startsWith('mac_')).sort().pop();
if (!build) {
  console.log('  skip live check: no Chrome for Testing in ~/.cache/puppeteer');
} else {
  const bin = join(cache, build, 'chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing');
  const tmp = mkdtempSync(join(tmpdir(), 'ship-tabs-'));
  mkdirSync(join(tmp, 'repo/specs'), { recursive: true });
  writeFileSync(join(tmp, 'repo/specs/card.html'), '<title>card</title>card');
  const server = createServer((_, res) => res.end('<title>app</title>app')).listen(0);
  const port = server.address().port;
  const chrome = spawn(bin, [/* headless has no tab strip, so no tabGroups API: a real window, parked off-screen */
    '--window-position=-4000,-4000', '--window-size=500,400', '--remote-debugging-port=0', `--user-data-dir=${join(tmp, 'profile')}`,
    `--load-extension=${here}`, `--disable-extensions-except=${here}`, '--no-first-run', 'about:blank'], { stdio: 'ignore' });
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  try {
    for (let i = 0; i < 100 && !existsSync(join(tmp, 'profile/DevToolsActivePort')); i++) await sleep(100);
    const [dport, path] = readFileSync(join(tmp, 'profile/DevToolsActivePort'), 'utf8').trim().split('\n');
    const ws = new WebSocket(`ws://127.0.0.1:${dport}${path}`);
    await new Promise((r) => ws.addEventListener('open', r, { once: true }));
    let id = 0; const waiting = new Map();
    ws.addEventListener('message', (e) => { const m = JSON.parse(e.data); waiting.get(m.id)?.(m); });
    const send = (method, params = {}, sessionId) => new Promise((r) => { waiting.set(++id, r); ws.send(JSON.stringify({ id, method, params, sessionId })); });

    // Chrome runs its own extension workers too; ours is the one named "Ship tabs". Wait for
    // it before opening tabs, since in real use it is running before any tab opens.
    const ours = async () => {
      const { result } = await send('Target.getTargets');
      for (const t of result.targetInfos.filter((t) => t.type === 'service_worker')) {
        const { result: a } = await send('Target.attachToTarget', { targetId: t.targetId, flatten: true });
        const { result: r } = await send('Runtime.evaluate', { returnByValue: true, expression: 'chrome.runtime.getManifest().name' }, a.sessionId);
        if (r.result.value === 'Ship tabs') return a;
      }
    };
    let att;
    for (let i = 0; i < 50 && !att; i++) { att = await ours(); if (!att) await sleep(100); }
    check('the extension loaded', !!att);
    for (const url of [`file://${join(tmp, 'repo/specs/card.html')}`, `http://localhost:${port}/`,
                       `http://127.0.0.1:${port}/two`, 'about:blank#elsewhere']) {
      await send('Target.createTarget', { url });
    }
    await sleep(1500);
    const { result: out } = await send('Runtime.evaluate', { awaitPromise: true, returnByValue: true, expression:
      `(async () => { const g = await chrome.tabGroups.query({}); const t = await chrome.tabs.query({});
        return { groups: g.map((x) => ({ id: x.id, title: x.title, color: x.color })),
                 tabs: t.map((x) => ({ url: x.url, groupId: x.groupId })) }; })()` }, att.sessionId);
    const { groups, tabs } = out.result.value;
    const inGroup = (title) => tabs.filter((t) => t.groupId === groups.find((g) => g.title === title)?.id).map((t) => t.url);
    check('one "ship docs" group, blue, holding the spec', groups.filter((g) => g.title === 'ship docs').length === 1 &&
      groups.find((g) => g.title === 'ship docs').color === 'blue' && inGroup('ship docs').some((u) => u.endsWith('/specs/card.html')));
    check('one "ship test" group, green, holding both local tabs', groups.filter((g) => g.title === 'ship test').length === 1 &&
      groups.find((g) => g.title === 'ship test').color === 'green' && inGroup('ship test').length === 2);
    check('other tabs stay ungrouped', tabs.filter((t) => t.url.startsWith('about:blank')).every((t) => t.groupId === -1));
    ws.close();
  } finally {
    chrome.kill(); server.close();
    await sleep(300); rmSync(tmp, { recursive: true, force: true });
  }
}
console.log(`ship-tabs test: ${fails} failed`);
process.exit(fails ? 1 : 0);
