// Check for the ship-share Worker: node share/worker/test.mjs
import assert from 'node:assert/strict';
import worker, { footer, inject } from './worker.mjs';

const fake = () => {
  const m = new Map();
  return {
    m,
    async get(k) {
      return m.has(k) ? { text: async () => m.get(k), json: async () => JSON.parse(m.get(k)), body: m.get(k) } : null;
    },
    async put(k, v) { m.set(k, typeof v === 'string' ? v : new TextDecoder().decode(v)); },
    async delete(keys) { for (const k of [].concat(keys)) m.delete(k); },
    // Pages of two, like R2's pages of 1000, so a delete has to follow the cursor.
    async list({ prefix, cursor }) {
      const all = [...m.keys()].filter((k) => k.startsWith(prefix) && (!cursor || k > cursor)).sort();
      const truncated = all.length > 2;
      return { objects: all.slice(0, 2).map((key) => ({ key })), truncated, cursor: truncated ? all[1] : undefined };
    },
  };
};
const env = { SHARE: fake(), SHARE_TOKEN: 't0k' };
const base = 'https://share.peteknowsai.xyz';
const auth = { authorization: 'Bearer t0k' };
const call = (method, path, { body, headers } = {}) =>
  worker.fetch(new Request(base + path, { method, body, headers }), env);
const put = (id, name, body, headers = auth) => call('PUT', `/api/${id}?name=${name}`, { body, headers });
const page = (body) => `<html><body><p>${body}</p></body></html>`;

// 1. no auth
assert.equal((await put('abc123', 'x', page('one'), {})).status, 401);
assert.deepEqual(await (await put('abc123', 'x', page('one'), {})).json(), { error: 'unauthorized' });
assert.equal((await put('abc123', 'x', page('one'), { authorization: 'Bearer wrong' })).status, 401);
assert.equal((await put('abc123', 'x', page('one'), { ...auth, 'content-length': String(21 * 1024 * 1024) })).status, 413);
assert.equal((await worker.fetch(new Request(base + '/api/abc123?name=x', { method: 'PUT', body: 'x', headers: auth }), { SHARE: fake() })).status, 401, 'unset secret rejects');

// 2. bad id / name
assert.equal((await put('ABC!!1', 'x', page('one'))).status, 400);
assert.equal((await put('abc123', 'Bad%20Name', page('one'))).status, 400);

// 3. first version
let r = await put('abc123', 'x', page('one'));
assert.equal(r.status, 200);
let j = await r.json();
assert.equal(j.url, `${base}/abc123/x`);
assert.equal(j.version, 1); assert.equal(j.versions, 1); assert.equal(j.changed, true);
assert.match(j.at, /^\d{4}-\d{2}-\d{2}T/);

// 4. same bytes
j = await (await put('abc123', 'x', page('one'))).json();
assert.deepEqual([j.version, j.versions, j.changed], [1, 1, false]);
assert.equal([...env.SHARE.m.keys()].filter((k) => k.endsWith('.html')).length, 1);

// 5. new bytes
j = await (await put('abc123', 'x', page('two'))).json();
assert.deepEqual([j.version, j.versions, j.changed], [2, 2, true]);

// 6. latest page
r = await call('GET', '/abc123/x');
assert.equal(r.status, 200);
assert.match(r.headers.get('content-type'), /^text\/html/);
assert.equal(r.headers.get('x-robots-tag'), 'noindex, nofollow');
assert.equal(r.headers.get('referrer-policy'), 'no-referrer');
let html = await r.text();
assert.match(html, /two/);
assert.match(html, /Version 2 of 2/);
assert.match(html, /href="\?v=1"/);
assert.match(html, /<template shadowrootmode="open">/);
assert.ok(html.indexOf('ship-share-foot') < html.lastIndexOf('</body>'), 'footer sits before </body>');
assert.ok(html.indexOf('</p>') < html.indexOf('ship-share-foot'), 'footer follows the content');

// 7. older version
html = await (await call('GET', '/abc123/x?v=1')).text();
assert.match(html, /one/);
assert.match(html, /version 1 of 2/);
assert.match(html, /See the latest/);
assert.match(html, /class="latest" href="\/abc123\/x"/);
assert.match(html, /<a href="\/abc123\/x">›<\/a>/, 'next of v1 is the latest');
assert.match(html, /<a class="off">‹<\/a>/, 'previous disabled');

// 8. one version only
await put('one111', 'solo', page('solo'));
html = await (await call('GET', '/one111/solo')).text();
assert.doesNotMatch(html, / of /);
assert.doesNotMatch(html, /‹/);

// 9. name is cosmetic
assert.match(await (await call('GET', '/abc123/anything-else')).text(), /two/);

// 10. unknown
for (const p of ['/zzzzzz/x', '/abc123/x?v=9', '/abc123/x?v=0', '/abc123/x?v=abc']) {
  r = await call('GET', p);
  assert.equal(r.status, 404, p);
  assert.match(await r.text(), /isn't shared anymore/);
  assert.equal(r.headers.get('x-robots-tag'), 'noindex, nofollow');
}

// 11. delete
assert.equal((await call('DELETE', '/api/abc123')).status, 401);
assert.deepEqual(await (await call('DELETE', '/api/abc123', { headers: auth })).json(), { deleted: 3 });
assert.equal((await call('GET', '/abc123/x')).status, 404);
assert.deepEqual(await (await call('DELETE', '/api/abc123', { headers: auth })).json(), { deleted: 0 });

// 12. inject
const F = '<F>';
assert.equal(inject('<p>no body</p>', F), '<p>no body</p><F>');
assert.equal(inject('<BODY>a</BODY>', F), '<BODY>a<F></BODY>');
assert.equal(inject('<body><template><body>x</body></template>y</body>', F), '<body><template><body>x</body></template>y<F></body>');
assert.equal(inject('<body>a</body>\n</html>\n', F), '<body>a<F></body>\n</html>\n');
assert.equal(inject('<body><script>const m = "</body>";</script>', F), '<body><script>const m = "</body>";</script><F>');

// 13. root
assert.equal((await call('GET', '/')).status, 404);
assert.equal((await call('GET', '/abc123')).status, 404);

// 14. footer dates in PT
const meta = { name: 'x', versions: [{ n: 1, at: '2026-10-12T18:20:00Z' }, { n: 2, at: '2026-10-14T21:10:00Z' }] };
let f = footer(meta, 2);
assert.match(f, /Shared by&nbsp;<b>Pete McCarthy<\/b>&nbsp;· updated Oct 14, 2:10 PM/);
assert.match(f, /Shared by&nbsp;<b>Pete<\/b>&nbsp;· Oct 14/);
assert.match(f, /2 of 2/);
assert.match(f, /^<div style="height:34px"><\/div><div id="ship-share-foot"><template shadowrootmode="open"><style>/);
assert.match(f, /@media \(max-width: ?500px\)/);
f = footer({ id: 'abc123', ...meta }, 1);
assert.match(f, /version 1 of 2<\/b>, from Oct 12/);
assert.match(f, /foot v old/);

console.log('share worker ok');
