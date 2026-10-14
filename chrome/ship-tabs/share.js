// The Share button on a ship doc tab. The background injects this after setting
// window.__shipShare = { key, file }; it draws the storyboard's frames in a shadow root
// (the page's CSS can't reach in) and talks to share.py through the background's relay.
// Wrapped so a second injection into the same page redeclares nothing and does nothing.
(() => {
// Frame CSS, verbatim from specs/designs/2026-10-14-doc-share.html, plus the host reset,
// focus rings on the panel's buttons, a still spinner for reduced motion, and a hidden
// status line for screen readers.
const CSS = `
:host{all:initial}
*{box-sizing:border-box}
.share{position:fixed;right:22px;bottom:22px;display:flex;flex-direction:column;align-items:flex-end;gap:10px;z-index:2147483647;font:14px/1.45 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;color:#1d1d1f;-webkit-font-smoothing:antialiased}
.btn{display:inline-flex;align-items:center;gap:8px;height:36px;padding:0 14px 0 12px;border-radius:8px;background:#1d1d1f;color:#fff;
  font:600 13px/1 -apple-system,BlinkMacSystemFont,sans-serif;border:0;box-shadow:0 2px 6px rgba(0,0,0,.18),0 10px 24px rgba(0,0,0,.14);cursor:pointer}
.btn:hover,.btn.hover{background:#3a3a3f}
.btn:focus-visible{outline:2px solid #2d5bd6;outline-offset:3px}
.btn svg{width:16px;height:16px;stroke:currentColor;fill:none;stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round}
.btn .dot{width:8px;height:8px;border-radius:50%;background:#34c759}
.btn .sub{font-weight:500;color:#c7c7cc}
.tip{background:#fff;border-radius:8px;padding:8px 11px;font-size:12px;color:#3a3a3f;box-shadow:0 2px 6px rgba(0,0,0,.1),0 8px 20px rgba(0,0,0,.1)}
.tip b{color:#1d1d1f}
.tip.css{display:none}
.share:hover .tip.css,.share:focus-within .tip.css{display:block}
.spin{width:14px;height:14px;border-radius:50%;border:2px solid rgba(255,255,255,.3);border-top-color:#fff;animation:s .8s linear infinite}
@keyframes s{to{transform:rotate(360deg)}}
.panel{width:340px;background:#fff;border-radius:10px;padding:16px;box-shadow:0 2px 6px rgba(0,0,0,.1),0 16px 40px rgba(0,0,0,.16)}
.panel h3{margin:0 0 4px;font-size:15px;display:flex;align-items:center;gap:8px}
.panel h3 svg{width:18px;height:18px;fill:none;stroke-width:2;stroke-linecap:round;stroke-linejoin:round}
.ok svg{stroke:#248a3d}.bad svg{stroke:#c9341f}
.panel p{margin:0 0 12px;color:#55555a;font-size:13px}
.url{display:block;font:12.5px/1.4 ui-monospace,Menlo,monospace;background:#f4f4f6;border:1px solid #e3e3e8;border-radius:6px;padding:8px 10px;color:#1d1d1f;margin:0 0 12px;word-break:break-all}
.url em{font-style:normal;color:#6e6e73}
.acts{display:flex;gap:8px;align-items:center}
.acts button{font:600 13px/1 -apple-system,sans-serif;height:32px;padding:0 12px;border-radius:7px;border:1px solid #d2d2d7;background:#fff;color:#1d1d1f;cursor:pointer}
.acts button.primary{background:#1d1d1f;border-color:#1d1d1f;color:#fff}
.acts button:hover{background:#f4f4f6}.acts button.primary:hover{background:#3a3a3f}
.acts .stop{margin-left:auto;border:0;background:none;color:#c9341f;padding:0 4px}
.acts .stop:hover{background:none;text-decoration:underline;text-underline-offset:3px}
.meta{font-size:12px;color:#6e6e73;margin:-4px 0 12px}
.acts button:focus-visible{outline:2px solid #2d5bd6;outline-offset:2px}
@media (prefers-reduced-motion:reduce){.spin{animation:none}}
.sr{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap}
`;
const LINK = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1"/><path d="M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1"/></svg>';
const OK = '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M8 12.5l2.7 2.7L16 9.8"/></svg>';
const BAD = '<svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M12 7.5v5.5"/><path d="M12 16.4v.1"/></svg>';
const MISSING = { ok: false, error: "The share helper isn't installed. Run share.py install." };

// Nothing from state lands in a single-quoted attribute, so apostrophes stay readable.
const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

// "updated just now" for the first minute after a redraw, minutes up to an hour, then
// the button is plain "Shared" again.
function relTime(iso, now = Date.now()) {
  const m = Math.floor((now - Date.parse(iso)) / 60000);
  return m < 1 ? 'just now' : m < 60 ? `${m} min ago` : '';
}

// The link as the panel shows it: no scheme, the id dimmed.
const shown = (u) => { const m = String(u ?? '').match(/^https?:\/\/([^/]+)\/([^/]+)\/(.*)$/); return m ? `${esc(m[1])}/<em>${esc(m[2])}</em>/${esc(m[3])}` : esc(u); };
// "versions 1 and 2 kept behind it": the older versions the link still carries.
const behind = (n) => n <= 1 ? '' : n === 2 ? ' · version 1 kept behind it' : n === 3 ? ' · versions 1 and 2 kept behind it' : ` · versions 1 to ${n - 1} kept behind it`;

// One frame of the storyboard as markup: idle, hover, sharing, copied, shared, panel, error.
function shareView(s, now = Date.now()) {
  const share = (sub = '') => `<button class="btn" data-act="share"${s.mode === 'error' ? '' : ' aria-describedby="tip"'}>${LINK}Share</button>${sub}`;
  const shared = (open) => `<button class="btn" data-act="toggle" aria-haspopup="dialog" aria-expanded="${open}"><span class="dot"></span>Shared</button>`;
  const acts = (first) => `<div class="acts"><button class="primary" data-act="copy">${first}</button><button data-act="open">Open</button>`;
  switch (s.mode) {
    case 'sharing': return `<button class="btn" aria-busy="true"><span class="spin"></span>Sharing…</button>`;
    case 'copied': return `<div class="panel ok" role="dialog" aria-labelledby="h"><h3 id="h">${OK}Link copied</h3><p>Paste it anywhere. It always shows this page's newest version.</p>` +
      `<span class="url">${shown(s.url)}</span>${acts('Copy again')}</div></div>${shared(true)}`;
    case 'shared': { const r = relTime(s.at, now); return `<button class="btn" data-act="toggle" aria-haspopup="dialog" aria-expanded="false"><span class="dot"></span>Shared${r ? ` <span class="sub">· updated ${r}</span>` : ''}</button>`; }
    case 'panel': return `<div class="panel" role="dialog" aria-labelledby="h"><h3 id="h">Shared</h3><div class="meta">Version ${esc(s.version)} is live${behind(s.versions)}</div>` +
      `<span class="url">${shown(s.url)}</span>${acts('Copy link')}<button class="stop" data-act="stop">Stop sharing</button></div></div>${shared(true)}`;
    case 'error': return `<div class="panel bad" role="dialog" aria-labelledby="h"><h3 id="h">${BAD}Couldn't share</h3><p>${esc(s.error)}</p>` +
      `<div class="acts"><button class="primary" data-act="share">Try again</button></div></div>${share()}`;
    // The tooltip is always in the idle markup and CSS shows it on hover or focus: a JS
    // re-render on hover swapped the button out mid-click on pages that capture the pointer.
    default: return `<div class="tip${s.hover ? '' : ' css'}" role="tooltip" id="tip">Publish a link anyone can open · <b>share.peteknowsai.xyz</b></div>` + share();
  }
}

// What the hidden status line says when the state changes, for a screen reader.
const SAID = { sharing: 'Sharing', copied: 'Link copied', shared: 'Shared', error: "Couldn't share", idle: 'Not shared' };

// Mount the button, wire its events, and ask share.py where this doc stands.
function mount(cfg) {
  const host = document.createElement('div');
  host.id = 'ship-share-host';
  const root = host.attachShadow({ mode: 'open' });
  root.innerHTML = `<style>${CSS}</style><div class="share"></div><div class="sr" role="status"></div>`;
  document.documentElement.appendChild(host);
  const box = root.querySelector('.share'), said = root.querySelector('.sr');
  let state = { mode: 'idle' }, last = null; // last: the newest status answer, for the panel

  // Redraw the frame; keep keyboard focus inside when it was inside.
  // Skips identical markup, so a status answer that changes nothing can't swap the button
  // out from under a click.
  let drawn = '';
  const render = () => {
    const html = shareView(state);
    if (html === drawn) return;
    drawn = html;
    const inside = !!root.activeElement;
    box.innerHTML = html;
    if (inside) (root.querySelector('.primary') || root.querySelector('.btn'))?.focus({ preventScroll: true });
    said.textContent = SAID[state.mode] || '';
  };
  const set = (s) => { state = s; render(); };
  const send = (cmd) => new Promise((r) => {
    try { chrome.runtime.sendMessage({ share: { cmd, key: cfg.key, file: cfg.file } }, (res) => r(!chrome.runtime.lastError && res ? res : MISSING)); } catch { r(MISSING); }
  });
  // Only idle and shared take a status answer: never under a panel or mid-publish.
  const status = async () => {
    const r = await send('status');
    if (!r.ok) return;
    last = r;
    if (state.mode === 'idle' || state.mode === 'shared') set(r.shared ? { mode: 'shared', ...r } : { mode: 'idle' });
  };
  const share = async () => {
    set({ mode: 'sharing' });
    const r = await send('publish');
    if (r.ok) last = r;
    set(r.ok ? { mode: 'copied', ...r } : { mode: 'error', error: r.error });
  };
  const close = () => { if (state.mode === 'copied' || state.mode === 'panel') set({ mode: 'shared', ...last }); else if (state.mode === 'error') set({ mode: 'idle' }); };
  const act = {
    share,
    toggle: () => state.mode === 'shared' ? set({ mode: 'panel', ...last }) : close(),
    open: () => window.open(last?.url, '_blank'),
    stop: async () => { const r = await send('stop'); if (r.ok) { last = null; set({ mode: 'idle' }); } else set({ mode: 'error', error: r.error }); },
    copy: async (b) => { const r = await send('copy'); if (!r.ok) return set({ mode: 'error', error: r.error }); const t = b.textContent; b.textContent = 'Copied'; setTimeout(() => { if (b.isConnected) b.textContent = t; }, 1200); },
  };
  box.addEventListener('click', (e) => { const b = e.target.closest('[data-act]'); if (b) act[b.dataset.act](b); });
  document.addEventListener('pointerdown', (e) => e.target !== host && close());
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && state.mode !== 'shared' && state.mode !== 'idle') { close(); root.querySelector('.btn')?.focus(); } });
  document.addEventListener('visibilitychange', () => document.visibilityState === 'visible' && status());

  render();
  // show.sh republishes in the background after opening a redraw, so an early status
  // can predate the upload: ask again twice.
  status(); setTimeout(status, 5000); setTimeout(status, 20000);
}

if (typeof module !== 'undefined') module.exports = { shareView, relTime };
else if (typeof document !== 'undefined' && window.__shipShare && !document.getElementById('ship-share-host')) mount(window.__shipShare);
})();
