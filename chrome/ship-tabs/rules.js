// Which group a URL belongs in: ship's docs (the storyboard, plan and review cards and
// shots, opened from a repo's specs/ or docs/ home) or a running app ship put up for
// testing (a localhost dev server, or a Vercel branch preview). null leaves the tab alone.
function shipGroup(href) {
  let url;
  try { url = new URL(href); } catch { return null; }
  if (url.protocol === 'file:' && /\/(specs|docs|\.ship-shots)\//.test(url.pathname)) return 'ship docs';
  const host = url.hostname;
  if (['localhost', '127.0.0.1', '[::1]'].includes(host) || host.endsWith('.localhost')) return 'ship test';
  if (/-git-[a-z0-9-]+\.vercel\.app$/.test(host)) return 'ship test';
  return null;
}

if (typeof module !== 'undefined') module.exports = { shipGroup };
