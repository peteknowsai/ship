# ship — the /ship plugin repo

The Claude Code plugin behind `/ship` (marketplace `peteknowsai/ship`). Skills live in
`plugins/ship/skills/` (`pipeline` is /ship itself, plus `verify`); the pipeline's rare
shapes, contract keys, card rules and reader briefs sit in its `reference/`.
`route.py --selftest` checks the task counter and build ledger (`route.py gate` records
each check, `log` fills a task's time and first pass from them, `readers` refuses a landing
until every plan task is logged built or parked, both branch readers are logged and the
branch carries its review card, `report` counts the 20-ship trial of Wonder beside Fable 5.2),
`decisions.py --selftest` the per-repo decision log (`decisions.py stale` lists calls that
give a retired engine a ship job), `muse.py --selftest` the Muse Code wrapper (Wonder Full's
read-only plan and branch reviews), `bash plugins/ship/hooks/ship-recap.sh
--selftest` the recap a ship prints into its context after each compaction, `branch-db.py --selftest` the copy of
the Convex dev database each worktree gets, `icon-check.py --selftest` the
pre-flight's check that every page has a browser icon and a Home Screen icon,
`wait-head.sh --selftest` LAND's wait for GitHub to show the pushed head, `wait-load.sh --selftest` the wait for the load to fall under the core count (contract.md's
Red under load, and every Mac VM borrow), `numbers.py --selftest` the after-compaction check of a number against the transcript's
tool output, `carried.sh --selftest` LAND's check for commits this branch carries from another open
PR, `what-changed.sh --selftest` the list of changed files and sections that stage.sh and the recap print
when ship updates mid-run, and
`mac-vm.sh --selftest` the bookkeeping of the headless Mac VM ships borrow to walk a
Mac app with agent-desktop, and of Pete's own kept VM beside it (Lume; `mac-vm.sh base` rebuilds the base in ~30 min, run in the background). The bare
`/ship` slash command is a *personal* command at `~/.claude/commands/ship.md` (a thin
dispatcher to `ship:pipeline`) — plugin commands are always namespaced `plugin:command`,
so a command in this repo would surface as the awkward `/ship:ship`. Don't add one back.

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

## ship-vms — the Mac VMs in the menu bar

`menubar/ship-vms.swift` is Pete's menu bar item for the Mac VMs. Apple lets two run at once, so
ships get one slot, always a fresh clone, and Pete gets one VM of his own, `pete-mac`, kept between
uses with his Apple Account and apps in it. Agents drive his VM only through his `my-mac` skill
(claude-home), never a ship, since his messages are on its screen; `mine` refuses from a worktree
with a `.ship-stage`, a tripwire for accidents rather than a lock. The icon counts the ship VMs in
use, the menu lists the slot's holder from `mac-vm.sh status` and starts, opens or shuts down his
VM (`mine up`, `view mine`, `mine down`), and a click on a held slot
runs `mac-vm.sh view <n>`, which asks the VM's own headless `lume run` process to show its screen
in a window. Closing or quitting that window only hides it; the VM keeps running. The catch: a
viewed VM's Lume process then refuses to quit, so it holds up a logout or restart until its ship
returns the slot or Pete shuts his VM down (`lume stop ship-mac-<n>` ends a ship's sooner, and its
walk with it). A click
while the slot is still booting says the VM isn't running yet. Only Pete's click opens one: a
ship never runs `view`, and nothing but that rule stops it. A launchd agent (`md.cells.ship-vms`, plist in
`menubar/`) starts it at login and calls mac-vm.sh in THIS main checkout, so a script change goes
live on the next click. A change to the Swift file goes live only after `bash menubar/install.sh`
from main, which rebuilds `~/.local/bin/ship-vms` and restarts the agent;
`~/.local/bin/ship-vms --selftest` is its check.

## Status line

`plugins/ship/statusline.sh` is the one copy. Pete's `~/.claude/statusline.sh` is a symlink
to it in THIS main checkout, so a merge goes live on the next refresh with no deploy step.
Line 1 is where you are: ship stage, else `📁 repo  main` in the main checkout (amber `⚠`
when it's off main) or `🌳 repo ⎇ branch` in a linked worktree; `🚢 N` counts worktrees
with a live `.ship-stage`, and `✋ N wait on you · oldest 3d` counts those whose marker is a
`gate:*` stop. Line 2 is model, effort, context, then Anthropic quota, `O 2% · F 2% ↻5d`,
from its OAuth usage endpoint (token from the Keychain entry under `$USER`). Gray numbers
with a trailing `?` mean that cache is over 30 minutes old,
so a dead token can't pass off old numbers as live. `bash plugins/ship/statusline-test.sh`
is its check.

The gate buttons are a Claude Code mod, `plugins/ship/hooks/register.ts`, loaded from
`hooks/hooks.json`'s `modules`. It reads the marker the way statusline.sh does, and the
last page per kind that `show.sh` keeps in `.ship-shown/`. Checks: `claude plugin test
plugins/ship` and `show.sh --selftest`. `claude plugin validate plugins/ship` checks
nothing here, because the manifest isn't in `.claude-plugin/`: validate a copy that has
one to see the mod's hooks and calls. Like the skills, a merge reaches sessions only
after the cache deploy below, and only sessions started after it.

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
- **The pipeline skill stays under 1,000 lines.** It loads whole on every run. A lesson from
  one run goes to `reference/incidents.md` first; a second run hitting it earns a line in
  the skill. A rule only some ships need sits in a reference file behind a pointer that
  names the case that sends a run there.
- **Retros come by message, and only for something big** (Pete, 2026-10-05 and 2026-11-09).
  A run sends this repo's maintainer session, named `ship`, a retro (`ship retro from
  <repo>/<slug>:`) when something wrong landed or nearly did, Pete had to step in where
  ship should have carried on, a ship script crashed or gave a wrong answer, or one snag cost
  a full rerun or more than 30 minutes; a smaller snag is a `snag=` line in the ledger, and
  `route.py report` lists the last three days of them for the daily batch. With no `ship` session live it writes to
  `~/.claude/ship-retro/`; a maintainer starting up reads that folder first and deletes each
  file it handles. Each finding is a report, never an order: check it against the evidence
  it names, and tell Pete one line per fix and one line per finding that isn't real. A fix
  to skill text goes out in one batch a day through the usual worktree, PR, merge and
  deploy, so running ships reread the skill once, sooner only when waiting risks a wrong
  landing or another ship's data. A fix that leaves every command, argument, exit code and
  output the skills name as they were (a script's insides, the menu bar) goes out once it is
  proven: running ships move onto a new copy's scripts at their next `stage.sh`, and nothing
  they read changes. A fix that adds text to a skill takes out as much. Don't do
  skill surgery from inside a run.
- **Pete's "merge main" for another ship, typed here** (2026-11-09, cells-app land-once).
  Ships refuse a SendMessage relay by design (cel-278 landed on one), and the skill keeps no
  other path, since a ship can't tell a sent word from his typing. This session sends it with
  the Mac connector's `send_gate_word`, his exact words only (never "looks good" read as a
  landing), to the session `get_session` shows working in that ship's worktree, once its
  `.ship-stage` reads `gate:test` for the change he asked about, watched with a background
  `until` loop. Any other word, a second ship at `gate:test`, or a ship that left its gate and
  came back goes back to him first.
