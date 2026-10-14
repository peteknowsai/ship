// share.peteknowsai.xyz serves versioned, unlisted copies of ship docs in the ship-share R2 bucket.
// Layout: <id>/meta.json = {name, versions:[{n, at, sha}]}, <id>/<n>.html.
// PUT /api/<id>?name=<name> (bearer) adds a version when the bytes changed; DELETE /api/<id> removes
// the doc; GET /<id>/<name>[?v=n] serves a version with the footer drawn in at serve time.

const ID = /^[a-z0-9]{6}$/;
const NAME = /^[a-z0-9-]{1,80}$/;
const MAX = 20 * 1024 * 1024;
const ROBOTS = { 'x-robots-tag': 'noindex, nofollow' };
const PAGE = {
  ...ROBOTS,
  'content-type': 'text/html; charset=utf-8',
  'cache-control': 'no-cache',
  'referrer-policy': 'no-referrer',
};

const json = (obj, status = 200) =>
  new Response(JSON.stringify(obj), { status, headers: { ...ROBOTS, 'content-type': 'application/json' } });
const gone = () =>
  new Response(
    '<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Not shared</title><p style="font:16px -apple-system,BlinkMacSystemFont,sans-serif;margin:40px;color:#6e6e73">This page isn\'t shared anymore.</p>',
    { status: 404, headers: PAGE },
  );

const sha256 = async (bytes) =>
  [...new Uint8Array(await crypto.subtle.digest('SHA-256', bytes))].map((b) => b.toString(16).padStart(2, '0')).join('');

const fmt = (iso, opts) =>
  new Intl.DateTimeFormat('en-US', { timeZone: 'America/Los_Angeles', month: 'short', day: 'numeric', ...opts })
    .format(new Date(iso))
    .replace(/ /g, ' ');
const stamp = (iso) => fmt(iso, { hour: 'numeric', minute: '2-digit' });
const day = (iso) => fmt(iso);

// CSS from the storyboard's client-a, client-old and client-phone frames, plus the long/short swap.
const CSS = `
.foot{position:fixed;left:0;right:0;bottom:0;height:34px;background:#fff;border-top:1px solid #d2d2d7;display:flex;align-items:center;justify-content:center;font-size:12px;color:#6e6e73;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif;margin:0;box-sizing:border-box;z-index:2147483646}
.foot b{color:#1d1d1f;font-weight:600}
.foot.v{justify-content:space-between;padding:0 16px}
.vers{display:flex;align-items:center;gap:6px;color:#1d1d1f}
.vers a{display:inline-grid;place-items:center;width:24px;height:22px;border-radius:6px;border:1px solid #d2d2d7;color:#1d1d1f;text-decoration:none;font-size:15px;line-height:1}
.vers a.off{color:#c7c7cc;border-color:#ececf0}
.vers .lbl{padding:0 4px}
.foot.old{background:#fff8e6;border-top-color:#f0d58c;color:#7a5a00}
.foot .latest{font-weight:600;color:#2d5bd6;text-decoration:none;margin-left:10px}
.short{display:none}
@media (max-width:500px){.long{display:none}.short{display:inline}}
`.trim();

// The footer under a shared page: a spacer so the page's last line clears it, then the bar in a
// declarative shadow root so the page's own CSS can't restyle it. `n` is the version shown.
export function footer(meta, n) {
  const N = meta.versions.length;
  const cur = meta.versions.find((v) => v.n === n);
  const latest = `/${meta.id}/${meta.name}`;
  let body;
  if (N === 1) {
    body = `<div class="foot"><span class="long">Shared by&nbsp;<b>Pete McCarthy</b>&nbsp;· updated ${stamp(cur.at)}</span><span class="short">Shared by&nbsp;<b>Pete</b>&nbsp;· ${day(cur.at)}</span></div>`;
  } else {
    const prev = n > 1 ? `<a href="?v=${n - 1}">‹</a>` : '<a class="off">‹</a>';
    const next = n >= N ? '<a class="off">›</a>' : `<a href="${n + 1 === N ? latest : `?v=${n + 1}`}">›</a>`;
    const vers = `<span class="vers">${prev}<span class="lbl"><span class="long">Version ${n} of ${N}</span><span class="short">${n} of ${N}</span></span>${next}</span>`;
    const left =
      n === N
        ? `<span><span class="long">Shared by&nbsp;<b>Pete McCarthy</b>&nbsp;· updated ${stamp(cur.at)}</span><span class="short">Shared by&nbsp;<b>Pete</b>&nbsp;· ${day(cur.at)}</span></span>`
        : `<span><span class="long">You're looking at <b style="color:#7a5a00">version ${n} of ${N}</b>, from ${day(cur.at)}</span><span class="short"><b style="color:#7a5a00">Version ${n}</b>, from ${day(cur.at)}</span><a class="latest" href="${latest}">See the latest →</a></span>`;
    body = `<div class="foot v${n === N ? '' : ' old'}">${left}${vers}</div>`;
  }
  return `<div style="height:34px"></div><div id="ship-share-foot"><template shadowrootmode="open"><style>${CSS}</style>${body}</template></div>`;
}

// Put the footer before the page's closing </body>, or at the end when there is none. Only
// a </body> with nothing but </html> and whitespace after it counts: one inside a script's
// string is not the page's.
export function inject(html, foot) {
  const m = html.match(/<\/body\s*>(\s*<\/html\s*>)?\s*$/i);
  return m ? html.slice(0, m.index) + foot + html.slice(m.index) : html + foot;
}

export default {
  async fetch(req, env) {
    const url = new URL(req.url);
    const api = url.pathname.match(/^\/api\/([^/]+)$/);
    if (api) {
      if (!env.SHARE_TOKEN || req.headers.get('authorization') !== `Bearer ${env.SHARE_TOKEN}`) return json({ error: 'unauthorized' }, 401);
      const id = api[1];
      if (!ID.test(id)) return json({ error: 'bad id' }, 400);
      if (req.method === 'DELETE') {
        // R2 lists 1000 keys a page; delete page by page until the doc is gone.
        let deleted = 0, cursor;
        do {
          const page = await env.SHARE.list({ prefix: `${id}/`, cursor });
          const keys = page.objects.map((o) => o.key);
          if (keys.length) await env.SHARE.delete(keys);
          deleted += keys.length;
          cursor = page.truncated ? page.cursor : undefined;
        } while (cursor);
        return json({ deleted });
      }
      if (req.method !== 'PUT') return json({ error: 'method' }, 405);
      const name = url.searchParams.get('name') || '';
      if (!NAME.test(name)) return json({ error: 'bad name' }, 400);
      if (Number(req.headers.get('content-length')) > MAX) return json({ error: 'too big' }, 413);
      const bytes = await req.arrayBuffer();
      if (bytes.byteLength > MAX) return json({ error: 'too big' }, 413);
      const metaKey = `${id}/meta.json`;
      const old = await env.SHARE.get(metaKey);
      const meta = old ? await old.json() : { versions: [] };
      const sha = await sha256(bytes);
      const last = meta.versions[meta.versions.length - 1];
      const changed = !last || last.sha !== sha;
      let cur = last;
      if (changed) {
        cur = { n: (last?.n || 0) + 1, at: new Date().toISOString(), sha };
        meta.versions.push(cur);
        await env.SHARE.put(`${id}/${cur.n}.html`, bytes);
      }
      if (changed || meta.name !== name) {
        meta.name = name;
        await env.SHARE.put(metaKey, JSON.stringify(meta));
      }
      return json({ url: `${url.origin}/${id}/${name}`, version: cur.n, versions: meta.versions.length, changed, at: cur.at });
    }

    const m = url.pathname.match(/^\/([a-z0-9]{6})\/[a-z0-9-]{1,80}$/);
    if (!m) return gone();
    const id = m[1];
    const obj = await env.SHARE.get(`${id}/meta.json`);
    if (!obj) return gone();
    const meta = await obj.json();
    const N = meta.versions.length;
    const v = url.searchParams.get('v');
    const n = v === null ? N : /^\d+$/.test(v) ? Number(v) : 0;
    if (n < 1 || n > N) return gone();
    const html = await env.SHARE.get(`${id}/${n}.html`);
    if (!html) return gone();
    return new Response(inject(await html.text(), footer({ id, ...meta }, n)), { headers: PAGE });
  },
};
