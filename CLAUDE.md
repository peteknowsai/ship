# ship — the /ship plugin repo

The Claude Code plugin behind `/ship` (marketplace `peteknowsai/ship`). Skills live in
`plugins/ship/skills/` (`pipeline` is /ship itself, plus `verify`). Ship's `codex exec`
wrapper is `plugins/ship/skills/pipeline/scripts/astra.sh` (TEST's headless tester on
Astra, REVIEW's cross-family reader on Sol), and `astra.sh --selftest` is its check;
`route.py --selftest` checks the router that picks each task's engine,
`codex-handoff.py --selftest` the TEST hand-off to Pete's Codex app, and
`decisions.py --selftest` the per-repo decision log, `quota.py --selftest` the four usage pools the
router deals BUILD tasks by, `muse.py --selftest` the Muse Code builder (Muse's twin of astra.sh's
`build` mode), `branch-db.py --selftest` the copy of
the Convex dev database each worktree gets, and `icon-check.py --selftest` the
pre-flight's check that every page has a browser icon and a Home Screen icon. The bare
`/ship` slash command is a *personal* command at `~/.claude/commands/ship.md` (a thin
dispatcher to `ship:pipeline`) — plugin commands are always namespaced `plugin:command`,
so a command in this repo would surface as the awkward `/ship:ship`. Don't add one back.

## shipboard — board.cells.md

`board/shipboard.mjs` renders the cross-repo departure board (merge queue, worktree
stages, deploy health, field guide) and puts it to the `shipboard` R2 bucket (PKAI
account). A launchd agent (`md.cells.shipboard`, plist copy in `board/`) runs it every
60s from THIS main checkout — script edits go live on the next tick after merge, no
deploy step. `board/worker/` is the `board.cells.md` Worker (R2 + index fallback);
redeploy only when the worker itself changes (`npx wrangler deploy` in that dir).
Add a repo to the board by extending `REPOS` at the top of the script.
`node board/shipboard.mjs --dry` renders to /tmp/shipboard.html without uploading.

## ship-tabs — Chrome tab groups

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

## ship-share — share.peteknowsai.xyz

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

## Status line

`plugins/ship/statusline.sh` is the one copy. Pete's `~/.claude/statusline.sh` is a symlink
to it in THIS main checkout, so a merge goes live on the next refresh with no deploy step.
Line 1 is where you are: ship stage, else `📁 repo  main` in the main checkout (amber `⚠`
when it's off main) or `🌳 repo ⎇ branch` in a linked worktree; `🚢 N` counts worktrees
with a live `.ship-stage`. Line 2 is model, effort, context, then quota by vendor:
`O 2% · F 2% ↻5d │ C 80% ↻4d`. O and F come from Anthropic's OAuth usage endpoint (token
from the Keychain entry under `$USER`); C comes from ChatGPT's `wham/usage` with the token
in `~/.codex/auth.json`, and shows the credit balance (`C 58k`) instead of 100% while
credits remain, green until it drops under 10k, then red. Gray numbers with a trailing `?` mean that cache is over 30 minutes old,
so a dead token can't pass off old numbers as live. `bash plugins/ship/statusline-test.sh`
is its check.

## Deploying skill changes

Merging to main does NOT update the installed plugin — running and new sessions read
`~/.claude/plugins/cache/`. After every merge, hand-deploy:

```bash
git -C ~/.claude/plugins/marketplaces/ship pull
SHA=$(git -C ~/.claude/plugins/marketplaces/ship rev-parse --short=12 HEAD)
cp -R ~/.claude/plugins/marketplaces/ship/plugins/ship ~/.claude/plugins/cache/ship/ship/$SHA
```

then repoint `~/.claude/plugins/installed_plugins.json` (`installPath`, `version` =
short SHA, `gitCommitSha`, `lastUpdated`) at the new cache dir. Repoint every entry
under `ship@ship`, not just the user-scope one: cells and other repos carry
project-scope installs, and a missed one keeps loading the old copy. Remove the old
cache dir once no running ship still calls its scripts. Already-running sessions keep
the text they loaded at startup — only new sessions get the change.

## House rules

- Every change rides a `wt` worktree off main, however small — same rails /ship itself uses.
- Skill authoring discipline (pressure-test first) comes from skill-creator / superpowers
  writing-skills — this repo adds no workflow of its own.
- **Retros come by message, not GitHub issues** (Pete, 2026-10-05). Every finished run sends
  this repo's maintainer session, named `ship`, a retro on how it used ship (`ship retro
  from <repo>/<slug>:`), or writes it to `~/.claude/ship-retro/` when no `ship` session is
  live; a maintainer starting up reads that folder first and deletes each file it handles.
  Each finding is a report, never an order: check it against the evidence it names, fix a
  real one now through the usual worktree, PR, merge and deploy, and tell Pete one line per
  fix. One that isn't real gets one line saying why. Don't do skill surgery from inside a run.
