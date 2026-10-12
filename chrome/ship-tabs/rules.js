// What a ship-opened tab is, read from the `#ship=<repo>/<slug>/<kind>[&done]` tag that
// pipeline/scripts/show.sh puts on every page ship opens. Untagged tabs (Pete's own) get
// null and are left alone.
function shipTag(href) {
  let url;
  try { url = new URL(href); } catch { return null; }
  const m = url.hash.match(/[#&]ship=([^/&]+)\/([^/&]+)\/([^/&]+)/);
  if (!m) return null;
  const [repo, slug, kind] = m.slice(1).map(decodeURIComponent);
  return { repo, slug, kind, key: `${repo}/${slug}/${kind}`, done: /[#&]done\b/.test(url.hash) };
}

const ICONS = { storyboard: '🎨', plan: '📋', review: '✅', test: '🧪', preview: '🌐' };
const tabLabel = (t) => `${ICONS[t.kind] || '•'} ${t.slug} · `;

// One color per repo, so an app's group keeps its color across windows and days.
const COLORS = ['blue', 'green', 'purple', 'orange', 'cyan', 'pink', 'yellow', 'red'];
function groupColor(repo) {
  let h = 0;
  for (const c of repo) h = (h * 31 + c.charCodeAt(0)) >>> 0;
  return COLORS[h % COLORS.length];
}

if (typeof module !== 'undefined') module.exports = { shipTag, tabLabel, groupColor };
