// Ship tabs: every page ship opens (pipeline/scripts/show.sh tags it) lands in the window's
// docs or test group, titled with what it is, without taking the tab Pete is on. A redo replaces the
// tab it supersedes, and a ship's `done` page closes the rest of that ship's tabs.
importScripts('rules.js');

let queue = Promise.resolve(); // one at a time, so tabs opening together make one group
const run = (fn) => { queue = queue.then(fn).catch(() => {}); };
const load = async () => ({ byKey: {}, byTab: {}, active: {}, ...(await chrome.storage.session.get(['byKey', 'byTab', 'active'])) });

async function sort(tabId, href) {
  const tag = shipTag(href);
  const s = await load();
  if (!tag || tag.inferred || s.byTab[tabId] === tag.key) return; // an untagged doc is the sweep's
  const tab = await chrome.tabs.get(tabId).catch(() => null);
  if (!tab) return;

  const olds = [];
  for (const [key, id] of Object.entries(s.byKey)) {
    if (id === tabId || !(key === tag.key || (tag.done && key.startsWith(`${tag.repo}/${tag.slug}/`)))) continue;
    const old = await chrome.tabs.get(id).catch(() => null);
    if (old) olds.push(old);
    delete s.byKey[key]; delete s.byTab[id];
  }
  const replacedActive = olds.some((o) => o.active);
  s.byKey[tag.key] = tabId; s.byTab[tabId] = tag.key;

  // Opening made it the active tab; hand Pete back the one he was on, unless he was
  // looking at the page this one replaces.
  if (tab.active && !replacedActive) {
    const [before, now] = s.active[tab.windowId] || [];
    const back = now === tabId ? before : now;
    if (back) await chrome.tabs.update(back, { active: true }).catch(() => {});
  }
  await chrome.storage.session.set(s);

  await join(tabId, tab.windowId, groupOf(tag));
  // Close what it replaces only now, so a group never empties out and comes back elsewhere.
  await chrome.tabs.remove(olds.map((o) => o.id)).catch(() => {});
  await label(tabId, tag);
  await offerShare(tabId, tag, href);
}

// A ship doc on disk gets the Share button (rules.js shareable): the page learns its key
// and file, then share.js draws the button in a shadow root. Not on the sweep: the button
// lives until the page reloads, and a reload fires `complete`, so one helper spawn per load.
async function offerShare(tabId, tag, href) {
  if (!shareable(tag, href)) return;
  await chrome.scripting.executeScript({ target: { tabId }, args: [{ key: tag.key, file: decodeURIComponent(new URL(href).pathname) }], func: (s) => { window.__shipShare = s; } }).catch(() => {});
  await chrome.scripting.executeScript({ target: { tabId }, files: ['share.js'] }).catch(() => {});
}

// The button's line to share.py: one native host spawn per request, its answer handed
// back to the page. No host installed → one human sentence, not a dead button.
chrome.runtime.onMessage.addListener((msg, sender, reply) => {
  if (!msg.share) return;
  chrome.runtime.sendNativeMessage('com.pete.ship.share', msg.share).then(reply, () => reply({ ok: false, error: "The share helper isn't installed. Run share.py install." }));
  return true;
});

// Every few minutes, at startup and after each ship page opens: group what's loose, close
// older copies of a page, age out a gone worktree's docs (rules.js, sweepPlan).
async function sweep() {
  const titles = new Map((await chrome.tabGroups.query({})).map((g) => [g.id, g.title]));
  const tabs = (await chrome.tabs.query({})).map((t) => ({ ...t, groupTitle: titles.get(t.groupId) }));
  const plan = sweepPlan(tabs, Date.now());
  for (const g of plan.group) await join(g.id, g.windowId, g.group).catch(() => {});
  for (const l of plan.label) await label(l.id, l.tag);
  for (const id of plan.activate) await chrome.tabs.update(id, { active: true }).catch(() => {});
  if (plan.close.length) await chrome.tabs.remove(plan.close).catch(() => {});
}

// Joining puts the tab at the group's end, so the newest page is always the last one.
async function join(tabId, windowId, { title, color }) {
  const [group] = await chrome.tabGroups.query({ windowId, title });
  if (group) return chrome.tabs.group({ groupId: group.id, tabIds: tabId });
  const groupId = await chrome.tabs.group({ tabIds: tabId, createProperties: { windowId } });
  await chrome.tabGroups.update(groupId, { title, color });
}

// Prefix the page's title ("🧪 smarter-search · …") and keep it there when the app retitles.
// A local file needs the extension's "Allow access to file URLs" switch on.
function label(tabId, tag) {
  return chrome.scripting.executeScript({ target: { tabId }, args: [tabLabel(tag)], func: (p) => {
    // An older label ("🎨 smarter-search · storyboard r1", a template's or an earlier
    // version's) gives way to the new one, never stacks under it.
    const fix = () => { if (!document.title.startsWith(p)) document.title = p + document.title.replace(/^(🎨|📋|✅|🧪|🌐|📸|📄|•) [^·]*· /u, ''); };
    fix();
    if (!window.__shipLabel) {
      window.__shipLabel = true;
      new MutationObserver(fix).observe(document.head || document.documentElement, { subtree: true, childList: true, characterData: true });
    }
  } }).catch(() => {});
}

chrome.alarms.get('sweep').then((a) => a || chrome.alarms.create('sweep', { periodInMinutes: 5 })); // re-creating resets the clock
chrome.alarms.onAlarm.addListener(() => run(sweep));
// Docs already open when the extension loads or reloads get their button now, not at
// their next page load.
async function offerAll() {
  for (const t of await chrome.tabs.query({})) await offerShare(t.id, shipTag(t.url || ''), t.url || '');
}
chrome.runtime.onStartup.addListener(() => run(async () => { await sweep(); await offerAll(); }));
chrome.runtime.onInstalled.addListener(() => run(async () => { await sweep(); await offerAll(); }));

chrome.tabs.onCreated.addListener((tab) => {
  if (tab.pendingUrl || tab.url) run(() => sort(tab.id, tab.pendingUrl || tab.url));
});
chrome.tabs.onUpdated.addListener((tabId, change, tab) => {
  if (change.url) { run(() => sort(tabId, change.url)); run(sweep); }
  if (change.status === 'complete') run(async () => {
    const { byTab = {} } = await chrome.storage.session.get('byTab');
    const tag = byTab[tabId] ? shipTag(`x:#ship=${byTab[tabId]}`) : shipTag(tab.url || '');
    if (!tag) return;
    await label(tabId, tag); // a full page load drops the prefix and the button; put them back
    await offerShare(tabId, tag, tab.url || '');
  });
});
chrome.tabs.onActivated.addListener(({ tabId, windowId }) => run(async () => {
  const { active = {} } = await chrome.storage.session.get('active');
  active[windowId] = [(active[windowId] || [])[1], tabId];
  await chrome.storage.session.set({ active });
}));
chrome.tabs.onRemoved.addListener((tabId) => run(async () => {
  const s = await load();
  if (!s.byTab[tabId]) return;
  delete s.byKey[s.byTab[tabId]]; delete s.byTab[tabId];
  await chrome.storage.session.set(s);
}));
