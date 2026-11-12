---
paths:
  - "plugins/ship/statusline.sh"
  - "plugins/ship/statusline-test.sh"
  - "plugins/ship/hooks/**"
  - "plugins/ship/plugin.json"
  - "plugins/ship/skills/pipeline/scripts/stage.sh"
  - "plugins/ship/skills/pipeline/scripts/route.py"
  - "plugins/ship/skills/pipeline/scripts/show.sh"
---

# Status line

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
after the cache deploy in CLAUDE.md, and only sessions started after it.
