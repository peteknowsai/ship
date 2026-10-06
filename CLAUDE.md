# ship — the /ship plugin repo

The Claude Code plugin behind `/ship` (marketplace `peteknowsai/ship`). Skills live in
`plugins/ship/skills/` (`pipeline` is /ship itself, plus `verify`). BUILD's dispatcher is
`plugins/ship/skills/pipeline/scripts/astra.sh`, and `astra.sh --selftest` is its check;
`route.py --selftest` checks the router that picks each task's engine,
`codex-handoff.py --selftest` the TEST hand-off to Pete's Codex app,
`storyboard-bundle.py --selftest` the storyboard's artifact bundle, and
`decisions.py --selftest` the per-repo decision log. The bare
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
it groups ship's docs and test tabs by URL. Edits go live when he presses reload on it in
`chrome://extensions`. `node chrome/ship-tabs/test.mjs` is its check (the live half
needs Chrome for Testing in `~/.cache/puppeteer`, and opens its window off-screen).

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
