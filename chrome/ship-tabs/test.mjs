// node chrome/ship-tabs/test.mjs — the tag rules, then the real extension in Chrome for
// Testing (a throwaway profile, its window parked off-screen): open tagged tabs, read back groups and titles.
import { createRequire } from 'node:module';
import { spawn } from 'node:child_process';
import { mkdtempSync, mkdirSync, writeFileSync, readFileSync, readdirSync, existsSync, rmSync } from 'node:fs';
import { createServer } from 'node:http';
import { tmpdir, homedir } from 'node:os';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const { shipTag, tabLabel, groupColor } = createRequire(import.meta.url)('./rules.js');
let fails = 0;
const check = (name, ok) => { console.log(`  ${ok ? 'ok  ' : 'FAIL'} ${name}`); if (!ok) fails++; };

const t = shipTag('file:///w/specs/designs/x.html#ship=eca-finder/smarter-search/storyboard');
check('a tag names the repo, slug and kind', t && t.repo === 'eca-finder' && t.slug === 'smarter-search' && t.kind === 'storyboard' && !t.done);
check('a tag after the app\'s own hash still reads', shipTag('http://localhost:3007/#tab=2&ship=app/x/test')?.kind === 'test');
check('done rides on the tag', shipTag('file:///r/card.html#ship=app/x/review&done').done === true);
check('an untagged tab is left alone', shipTag('http://localhost:3218/home') === null && shipTag('https://github.com/x#ship') === null);
check('the label says what the tab is', tabLabel(t) === '🎨 smarter-search · ');
check('a repo keeps one color', groupColor('eca-finder') === groupColor('eca-finder'));

// The live part needs a Chrome for Testing build (branded Chrome ignores --load-extension).
const cache = join(homedir(), '.cache/puppeteer/chrome');
const build = process.argv.includes('--live') && existsSync(cache) && readdirSync(cache).filter((d) => d.startsWith('mac_')).sort().pop();
if (!build) {
  console.log('  skip live check: pass --live (opens Chrome for Testing in the background; needs it in ~/.cache/puppeteer)');
} else {
  const bin = join(cache, build, 'chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing');
  const tmp = mkdtempSync(join(tmpdir(), 'ship-tabs-'));
  mkdirSync(join(tmp, 'repo/specs'), { recursive: true });
  writeFileSync(join(tmp, 'repo/specs/card.html'), '<title>card</title>card');
  const server = createServer((_, res) => res.end('<title>app</title>app')).listen(0);
  const port = server.address().port;
  // Headless has no tab strip, so no tabGroups API: a real window, parked off-screen and
  // launched with `open -g` so it never takes the screen from Pete.
  const app = bin.replace(/\/Contents\/MacOS\/.*$/, '');
  spawn('open', ['-g', '-n', '-a', app, '--args',
    '--window-position=-4000,-4000', '--window-size=500,400', '--remote-debugging-port=0', `--user-data-dir=${join(tmp, 'profile')}`,
    `--load-extension=${here}`, `--disable-extensions-except=${here}`, '--no-first-run', 'about:blank'], { stdio: 'ignore' });
  const chrome = { kill: () => spawn('pkill', ['-f', join(tmp, 'profile')]) };
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
    const state = async () => {
      const { result: out } = await send('Runtime.evaluate', { awaitPromise: true, returnByValue: true, expression:
        `(async () => { const g = await chrome.tabGroups.query({}); const t = await chrome.tabs.query({});
          return { groups: g.map((x) => ({ id: x.id, title: x.title, color: x.color })),
                   tabs: t.map((x) => ({ id: x.id, url: x.url, title: x.title, groupId: x.groupId, active: x.active })) }; })()` }, att.sessionId);
      return out.result.value;
    };
    const open = async (url) => { await send('Target.createTarget', { url }); await sleep(1200); return state(); };
    const card = `file://${join(tmp, 'repo/specs/card.html')}`;
    const site = `http://localhost:${port}`;

    let s = await open('about:blank#mine');
    const mine = s.tabs.find((x) => x.url.endsWith('#mine')).id;
    s = await open(`${card}#ship=app/s1/storyboard`);
    const g = s.groups.find((x) => x.title === 'app');
    check('a ship page joins its app\'s group', g && s.tabs.some((x) => x.groupId === g.id && x.url.includes('s1/storyboard')));
    check('the group keeps the repo\'s color', g?.color === groupColor('app'));
    check('Pete keeps the tab he was on', s.tabs.find((x) => x.id === mine)?.active === true);
    s = await open(`${card}#ship=app/s1/storyboard`);
    check('a redo replaces the old tab', s.tabs.filter((x) => x.url.includes('s1/storyboard')).length === 1);
    s = await open(`${site}/#ship=app/s1/test`);
    s = await open(`${site}/#ship=app/s2/test`);
    check('both ships share the app\'s one group', s.groups.filter((x) => x.title === 'app').length === 1 &&
      s.tabs.filter((x) => x.groupId === g?.id).length === 3);
    check('a test tab is titled with its ship', s.tabs.some((x) => x.title === '🧪 s1 · app'));
    const s1test = s.tabs.find((x) => x.url.includes('s1/test')).id;
    await send('Runtime.evaluate', { expression: `chrome.tabs.update(${s1test}, { url: '${site}/two' })` }, att.sessionId);
    await sleep(1200); s = await state();
    check('the title survives a page load', s.tabs.find((x) => x.id === s1test)?.title === '🧪 s1 · app');
    s = await open(`${card}#ship=app/s1/review&done`);
    check('done closes the ship\'s other tabs, not its review or another ship\'s',
      !s.tabs.some((x) => x.url.includes('s1/storyboard') || x.id === s1test) &&
      s.tabs.some((x) => x.url.includes('s1/review')) && s.tabs.some((x) => x.url.includes('s2/test')));
    s = await open(`${site}/plain`);
    check('an untagged tab stays ungrouped', s.tabs.find((x) => x.url.endsWith('/plain'))?.groupId === -1);
    ws.close();
  } finally {
    chrome.kill(); server.close();
    await sleep(300); rmSync(tmp, { recursive: true, force: true });
  }
}
console.log(`ship-tabs test: ${fails} failed`);
process.exit(fails ? 1 : 0);
