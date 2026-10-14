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
const require = createRequire(import.meta.url);
const { shipTag, tabLabel, groupOf, GROUPS, sweepPlan, STALE_MS, shareable } = require('./rules.js');
const { shareView, relTime } = require('./share.js');
let fails = 0;
const check = (name, ok) => { console.log(`  ${ok ? 'ok  ' : 'FAIL'} ${name}`); if (!ok) fails++; };

const t = shipTag('file:///w/specs/designs/x.html#ship=eca-finder/smarter-search/storyboard');
check('a tag names the repo, slug and kind', t && t.repo === 'eca-finder' && t.slug === 'smarter-search' && t.kind === 'storyboard' && !t.done);
check('a tag after the app\'s own hash still reads', shipTag('http://localhost:3007/#tab=2&ship=app/x/test')?.kind === 'test');
check('done rides on the tag', shipTag('file:///r/card.html#ship=app/x/review&done').done === true);
check('an untagged tab is left alone', shipTag('http://localhost:3218/home') === null && shipTag('https://github.com/x#ship') === null);
check('the label says what the tab is, for which app and ship', tabLabel(t) === '🎨 eca-finder · smarter-search · ');
check('docs and cards go to docs, running apps to test', groupOf(t) === GROUPS.docs && groupOf(shipTag('http://localhost:1/#ship=a/b/test')) === GROUPS.test &&
  groupOf(shipTag('https://x-git-b.vercel.app/#ship=a/b/preview')) === GROUPS.test && groupOf(shipTag('file:///p/app/docs/n.html')) === GROUPS.docs);

const wt = 'file:///Users/pete/Projects/.worktrees/app/feature-x';
const doc = (u) => shipTag(u) || {};
check('an untagged storyboard in a worktree reads as that ship\'s storyboard',
  doc(`${wt}/specs/designs/2026-10-08-x.html`).key === 'app/x/storyboard');
check('plan and review cards read from their names', doc('file:///p/app/specs/plans/go-card-x.html').key === 'app/x/plan' &&
  doc('file:///p/app/specs/plans/review-x.html').key === 'app/x/review');
check('any other docs-home page joins its repo, keyed by its own path', doc('file:///p/app/docs/notes.html').repo === 'app' &&
  doc('file:///p/app/docs/notes.html').key === '/p/app/docs/notes.html');
check('a stray file is still left alone', shipTag('file:///Users/pete/Downloads/a.html') === null);

const now = 1e13, tab = (id, url, more = {}) => ({ id, url, windowId: 1, groupId: -1, active: false, pinned: false, lastAccessed: now, ...more });
let p = sweepPlan([tab(1, `${wt}/specs/designs/2026-10-08-x.html`, { active: true }), tab(2, `${wt}/specs/designs/2026-10-08-x.html#ship=app/x/storyboard`),
                   tab(3, 'https://github.com/'), tab(4, 'file:///p/app/docs/notes.html', { groupId: 9 })], now);
check('the sweep closes the older copy of a page and moves Pete to the newer', p.close.join() === '1' && p.activate.join() === '2');
check('it groups the loose ship tab, never Pete\'s own or one he grouped', p.group.map((g) => g.id).join() === '2' && p.group[0].group === GROUPS.docs);
check('it labels every ship tab it keeps', p.label.map((l) => l.id).join() === '2,4');
p = sweepPlan([tab(8, 'file:///p/app/docs/n.html', { groupId: 3, groupTitle: 'app' }), tab(9, 'http://localhost:1/#ship=app/x/test', { groupId: 4, groupTitle: 'ship test' })], now);
check('tabs in an earlier version\'s groups move to docs and test', p.group.map((g) => `${g.id}:${g.group.title}`).join() === '8:📐 docs,9:🧪 test');
p = sweepPlan([tab(5, `${wt}/specs/plans/review-x.html`, { lastAccessed: now - STALE_MS - 1 }),
               tab(6, 'file:///p/app/specs/plans/review-y.html', { lastAccessed: now - STALE_MS - 1 }),
               tab(7, `${wt}/docs/a.html`, { lastAccessed: now - STALE_MS - 1, active: true })], now);
check('a worktree page untouched for three days closes; main\'s docs and the tab Pete is on stay', p.close.join() === '5');

// The Share button: which tabs get one, and what it draws in each state.
const sh = (u) => shareable(shipTag(u), u);
check('a ship doc on disk can be shared: storyboard, plan, review, doc and shots',
  sh(`${wt}/specs/designs/2026-10-08-x.html`) && sh('file:///p/app/specs/plans/go-card-x.html#ship=app/x/plan') &&
  sh('file:///p/app/specs/plans/review-x.html') && sh('file:///p/app/docs/notes.html') && sh('file:///p/app/.ship-shots/x/1.html'));
check('a running app is not, nor any http page', !sh('http://localhost:1/#ship=a/b/test') && !sh('https://x.vercel.app/#ship=a/b/preview') &&
  !sh('http://localhost:1/#ship=a/b/storyboard'));
check('Pete\'s own file:// tab gets no button', shipTag('file:///Users/pete/Downloads/x.html') === null && !sh('file:///Users/pete/Downloads/x.html') && !shareable(null, 'file:///x'));

const url = 'https://share.peteknowsai.xyz/k3x9p2/smarter-search-storyboard';
const has = (html, ...parts) => parts.every((x) => html.includes(x));
let v = shareView({ mode: 'idle' });
check('idle: the Share button with the link icon, no tooltip', has(v, '>Share</button>', '<svg', 'M10 14a4') && !v.includes('Publish a link'));
check('hover: the tooltip above it', has(shareView({ mode: 'idle', hover: true }), 'Publish a link anyone can open · <b>share.peteknowsai.xyz</b>', 'Share</button>'));
check('sharing: a spinner and Sharing…', has(shareView({ mode: 'sharing' }), 'class="spin"', 'Sharing…'));
v = shareView({ mode: 'copied', url });
check('copied: the panel with the link, Copy again and Open, the button reads Shared',
  has(v, 'Link copied', 'Paste it anywhere. It always shows this page\'s newest version.', 'share.peteknowsai.xyz/<em>k3x9p2</em>/smarter-search-storyboard', '>Copy again</button>', '>Open</button>', 'Shared</button>'));
const at = (ms) => new Date(now - ms).toISOString();
check('shared: Shared · updated just now right after a redraw', has(shareView({ mode: 'shared', at: at(10e3) }, now), 'Shared', '· updated just now'));
check('shared: three hours on, just Shared', !shareView({ mode: 'shared', at: at(3 * 3600e3) }, now).includes('updated'));
const panel = (version, versions) => shareView({ mode: 'panel', version, versions, url });
check('panel: version 3 live, 1 and 2 behind, Copy link, Open, Stop sharing',
  has(panel(3, 3), 'Version 3 is live · versions 1 and 2 kept behind it', '>Copy link</button>', '>Open</button>', '>Stop sharing</button>', 'k3x9p2'));
check('panel: one, two and five versions read right', has(panel(1, 1), 'Version 1 is live<') && has(panel(2, 2), 'Version 2 is live · version 1 kept behind it') &&
  has(panel(5, 5), 'Version 5 is live · versions 1 to 4 kept behind it'));
v = shareView({ mode: 'error', error: 'X didn\'t answer.' });
check('error: Couldn\'t share, the reason, Try again, the button back to Share', has(v, 'Couldn\'t share', 'X didn\'t answer.', '>Try again</button>', '>Share</button>'));
check('relTime: just now, minutes, then nothing', relTime(at(30e3), now) === 'just now' && relTime(at(5 * 60e3), now) === '5 min ago' && relTime(at(60 * 60e3), now) === '');
v = shareView({ mode: 'copied', url: 'https://x/<b>/y' }) + shareView({ mode: 'error', error: '<b>' });
check('every string from state is escaped', has(v, '&lt;b&gt;') && !v.includes('<b>'));

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
    const g = s.groups.find((x) => x.title === GROUPS.docs.title);
    check('a ship doc joins the docs group, blue', g?.color === 'blue' && s.tabs.some((x) => x.groupId === g.id && x.url.includes('s1/storyboard')));
    check('Pete keeps the tab he was on', s.tabs.find((x) => x.id === mine)?.active === true);
    s = await open(`${card}#ship=app/s1/storyboard`);
    check('a redo replaces the old tab', s.tabs.filter((x) => x.url.includes('s1/storyboard')).length === 1);
    s = await open(`${site}/#ship=app/s1/test`);
    s = await open(`${site}/#ship=app/s2/test`);
    const tg = s.groups.find((x) => x.title === GROUPS.test.title);
    check('both ships\' apps share the one test group, green', s.groups.filter((x) => x.title === GROUPS.test.title).length === 1 &&
      tg?.color === 'green' && s.tabs.filter((x) => x.groupId === tg.id).length === 2);
    check('a test tab is titled with its app and ship', s.tabs.some((x) => x.title === '🧪 app · s1 · app'));
    const s1test = s.tabs.find((x) => x.url.includes('s1/test')).id;
    await send('Runtime.evaluate', { expression: `chrome.tabs.update(${s1test}, { url: '${site}/two' })` }, att.sessionId);
    await sleep(1200); s = await state();
    check('the title survives a page load', s.tabs.find((x) => x.id === s1test)?.title === '🧪 app · s1 · app');
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
