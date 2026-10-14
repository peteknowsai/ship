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
const tabLabel = (t) => `${ICONS[t.kind] || '•'} ${t.slug} · `;

// One color per repo, so an app's group keeps its color across windows and days.
const COLORS = ['blue', 'green', 'purple', 'orange', 'cyan', 'pink', 'yellow', 'red'];
function groupColor(repo) {
  let h = 0;
  for (const c of repo) h = (h * 31 + c.charCodeAt(0)) >>> 0;
  return COLORS[h % COLORS.length];
}

const STALE_MS = 3 * 24 * 3600 * 1000; // a worktree lives a day or two; its pages a little longer

// The sweep over every open tab, as a plan the background applies: ship tabs left
// ungrouped join their app's group, older copies of one page close (the newest tab wins,
// and takes focus if Pete was on a copy it replaced), and a worktree's doc nobody has
// looked at in three days closes. Tabs in a group Pete chose stay where he put them.
function sweepPlan(tabs, now) {
  const close = new Set(), group = [], activate = [], newest = new Map();
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
    if (tag && !close.has(t.id) && t.groupId === -1 && !t.pinned) group.push({ id: t.id, windowId: t.windowId, repo: tag.repo });
  }
  return { close: [...close], group, activate: activate.filter((id) => !close.has(id)) };
}

if (typeof module !== 'undefined') module.exports = { shipTag, tabLabel, groupColor, sweepPlan, STALE_MS };
