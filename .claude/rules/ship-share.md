---
paths:
  - "share/**"
  - "chrome/ship-tabs/share.js"
  - "plugins/ship/skills/pipeline/scripts/share.py"
  - "plugins/ship/skills/pipeline/scripts/share-host.sh"
---

# ship-share — share.peteknowsai.xyz

Pete's Share button on a ship doc publishes it to a public, unlisted link for clients.
Three pieces:

- `chrome/ship-tabs/share.js` draws the button in a shadow root on file:// ship docs and
  asks the native host `com.pete.ship.share` to publish, copy, stop or report status.
- `plugins/ship/skills/pipeline/scripts/share.py` is that host (`share-host.sh` runs it
  on `/usr/bin/python3`, 3.9, with Chrome's bare PATH) and the CLI. It packs the page and
  everything it loads from disk into one file, uploads it with the Keychain item
  `ship-share`, copies the link, and keeps doc-to-link state in
  `~/.config/ship-share/links.json`. `show.sh` calls `share.py republish` on every card it
  opens, so a shared doc follows its redraws; a doc never shared is left alone.
- `share/worker/` is the `ship-share` Worker and R2 bucket on PKAI at
  `share.peteknowsai.xyz`. It keeps every changed upload as a version, serves the newest
  at `/<id>/<name>` and `?v=<n>` for older ones, and draws the footer with the arrows at
  serve time. The apex `peteknowsai.xyz` stays free. Redeploy with `npx wrangler deploy`
  in that dir; the upload key is its `SHARE_TOKEN` secret, the same value as the
  Keychain item. Never echo it.

Checks: `/usr/bin/python3 plugins/ship/skills/pipeline/scripts/share.py --selftest`,
`node share/worker/test.mjs`. The native host manifest is written by
`share.py install <extension-id>` from this main checkout, so it outlives worktrees.
Take a page down by hand with `share.py stop <key>` (keys are in links.json).
