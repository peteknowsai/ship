// What a ship tab is. Pages ship opens through pipeline/scripts/show.sh carry a
// `#ship=<repo>/<slug>/<kind>[&done]` tag; a ship doc opened any other way (an older
// session's bare `open`, a click in Finder) is read from its path instead. Anything else
// (Pete's own tabs) gets null and is left alone.
function shipTag(href) {
  let url;
  try { url = new URL(href); } catch { return null; }
  const m = url.hash.match(/[#&]ship=([^/&]+)\/([^/&]+)\/([^/&]+)/);
  if (m) {
    const [repo, slug, kind] = m.slice(1).map(decodeURIComponent);
    return { repo, slug, kind, key: `${repo}/${slug}/${kind}`, done: /[#&]done\b/.test(url.hash) };
  }
  return url.protocol === 'file:' ? docTag(decodeURIComponent(url.pathname)) : null;
}

// specs/designs/YYYY-MM-DD-<slug>.html is a storyboard, specs/plans/go-card-<slug>.html a
// plan card, specs/plans/review-<slug>.html a review card; any other page in a docs home
// joins its repo's group as a doc. The repo is the worktree's, else the folder above the
// docs home. Redrawn rounds of one card share a key, so only the newest stays open.
function docTag(path) {
  const home = path.match(/^(.*)\/(specs|docs)\/(.+)$/) || path.match(/^(.*)\/(\.ship-shots)\/(.+)$/);
  if (!home) return null;
  const [, root, , rest] = home;
  const tree = root.match(/\/\.worktrees\/([^/]+)\/([^/]+)$/);
  const repo = tree ? tree[1] : root.split('/').pop();
  const file = rest.split('/').pop().replace(/\.html?$/, '');
  const name = file.replace(/^\d{4}-\d{2}-\d{2}-/, '');
  let kind = 'doc', slug = name;
  if (home[2] === '.ship-shots') { kind = 'shots'; slug = rest.split('/')[0]; }
  else if (/^designs\//.test(rest)) kind = 'storyboard';
  else if (/^go-card-/.test(name)) { kind = 'plan'; slug = name.slice(8); }
  else if (/^(review|test-card)-/.test(name)) { kind = 'review'; slug = name.replace(/^(review|test-card)-/, ''); }
  const card = ['storyboard', 'plan', 'review'].includes(kind);
  return { repo, slug, kind, key: card ? `${repo}/${slug}/${kind}` : path, done: false, inferred: true };
}

const ICONS = { storyboard: '🎨', plan: '📋', review: '✅', test: '🧪', preview: '🌐', shots: '📸', doc: '📄' };
// What the tab strip and side panel show: the kind, the app and the ship, then the page's
// own title ("🎨 eca-finder · smarter-search · storyboard r2").
const tabLabel = (t) => `${ICONS[t.kind] || '•'} ${t.repo} · ${t.slug} · `;

// Two groups per window, whatever the app (Pete, 2026-10-14: "fewer groups, the things
// labeled inside"): docs for everything ship shows him to read, test for the running apps.
const GROUPS = { docs: { title: '📐 docs', color: 'blue' }, test: { title: '🧪 test', color: 'green' } };
const groupOf = (t) => GROUPS[t.kind === 'test' || t.kind === 'preview' ? 'test' : 'docs'];
// Groups earlier versions made (one per repo, or "ship docs"/"ship test"): a tab still in
// one is loose, not a tab Pete placed.
const oldGroup = (title, t) => title === t.repo || title === 'ship docs' || title === 'ship test';

const STALE_MS = 3 * 24 * 3600 * 1000; // a worktree lives a day or two; its pages a little longer

// The sweep over every open tab, as a plan the background applies: loose ship tabs join
// the docs or test group, older copies of one page close (the newest tab wins,
// and takes focus if Pete was on a copy it replaced), and a worktree's doc nobody has
// looked at in three days closes. Tabs in a group Pete chose stay where he put them.
function sweepPlan(tabs, now) {
  const close = new Set(), group = [], label = [], activate = [], newest = new Map();
  for (const t of tabs) {
    const tag = shipTag(t.url || '');
    if (!tag || t.pinned) continue;
    const key = tag.key;
    const kept = newest.get(key);
    if (kept) {
      const [old, keep] = kept.id < t.id ? [kept, t] : [t, kept];
      close.add(old.id); newest.set(key, keep);
      if (old.active) activate.push(keep.id);
    } else newest.set(key, t);
    const tree = /^file:\/\/.*\/\.worktrees\//.test(t.url);
    if (tree && !t.active && t.lastAccessed && now - t.lastAccessed > STALE_MS) close.add(t.id);
  }
  for (const t of tabs) {
    const tag = shipTag(t.url || '');
    if (!tag || close.has(t.id) || t.pinned) continue;
    label.push({ id: t.id, tag });
    if (t.groupId === -1 || oldGroup(t.groupTitle, tag)) group.push({ id: t.id, windowId: t.windowId, group: groupOf(tag) });
  }
  return { close: [...close], group, label, activate: activate.filter((id) => !close.has(id)) };
}

if (typeof module !== 'undefined') module.exports = { shipTag, tabLabel, groupOf, GROUPS, sweepPlan, STALE_MS };
