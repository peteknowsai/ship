---
paths:
  - "chrome/ship-tabs/**"
  - "plugins/ship/skills/pipeline/scripts/show.sh"
---

# ship-tabs — Chrome tab groups

`chrome/ship-tabs/` is an unpacked Chrome extension Pete loads from this main checkout;
it files every tab ship opens through `pipeline/scripts/show.sh` (tagged
`#ship=<repo>/<slug>/<kind>`) into one of two groups per window, 📐 docs or 🧪 test, labels
it with its kind, app and ship, and closes the tab it
replaces; a five-minute sweep (`sweepPlan` in `rules.js`) also files untagged ship docs by
their path, closes older copies of a page and ages out a worktree's pages after three days.
Edits go live when he presses reload on it in `chrome://extensions`.
`node chrome/ship-tabs/test.mjs` is its check. Its `--live` half launches Chrome for
Testing with `open -g`; run it only when Pete is away from the screen, since he has had
test windows fight him for focus. Never connect to his own Chrome over CDP: each
connection pops an "Allow remote debugging?" dialog. It also draws the Share button on
every ship doc (`share.js`, below); that needs its `nativeMessaging` permission.
Its host permissions cover localhost, `*.vercel.app` previews and `https://*.mac.cells.md`,
where apps live on Pete's tailnet (`homebody/` on his phone); a tab on a host it can't
script still groups but goes unlabeled.
