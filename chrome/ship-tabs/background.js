// Ship tabs: when a tab lands on one of ship's pages, move it into that window's
// "ship docs" or "ship test" group, making the group the first time. A tab already in a
// group stays where it is, so dragging one out by hand sticks.
importScripts('rules.js');

const COLORS = { 'ship docs': 'blue', 'ship test': 'green' };
let queue = Promise.resolve(); // one at a time, so two tabs opening together make one group

async function sort(tabId, href) {
  const title = shipGroup(href);
  if (!title) return;
  const tab = await chrome.tabs.get(tabId).catch(() => null);
  if (!tab || tab.groupId !== chrome.tabGroups.TAB_GROUP_ID_NONE || tab.pinned) return;
  const [group] = await chrome.tabGroups.query({ windowId: tab.windowId, title });
  if (group) {
    await chrome.tabs.group({ groupId: group.id, tabIds: tabId });
  } else {
    const groupId = await chrome.tabs.group({ tabIds: tabId, createProperties: { windowId: tab.windowId } });
    await chrome.tabGroups.update(groupId, { title, color: COLORS[title] });
  }
}

chrome.tabs.onUpdated.addListener((tabId, change, tab) => {
  const href = change.url || (change.status === 'complete' && tab.url);
  if (href) queue = queue.then(() => sort(tabId, href)).catch(() => {});
});
