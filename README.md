# ship

`ship` is a Codex Desktop plugin for taking a feature from idea to reviewed PR:
`worktree -> discover -> plan -> build -> review`. It gates only on the two calls Pete
actually needs to make: design direction, then "go".

It is opinionated: Pete reviews compact HTML artifacts in the Codex in-app Browser, not
raw plans or diffs. Codex handles the mechanics.

## What It Does

- **Two gates.** Design direction after discovery, then "go" after planning.
- **HTML decision cards.** A design spec, go-card, and review card open in the browser.
- **Codex-managed worktrees.** Ship assumes Codex Desktop owns worktree birth and cleanup.
- **BUILD routing.** The bundled `router` skill defaults build drafting to codex and uses
  Opus-capable subagents only for rare judgment-heavy tasks.
- **Fresh verification.** REVIEW invokes the bundled `verify` skill before the card so the
  running app is driven and judged before merge.

## What's In The Plugin

- `skills/ship` — the pipeline playbook plus go-card/review-card templates.
- `skills/router` — BUILD-stage task routing.
- `skills/verify` — fresh read-only verification against the running app before merge.
- `hooks/gate-notify.sh` — optional manual gate notification helper.
- `.codex-plugin/plugin.json` — the Codex Desktop manifest.

Legacy Claude plugin files may still exist in this repo, but Codex reads
`.codex-plugin/plugin.json`.

## Requires

`superpowers`, `ponytail`, and `impeccable` should be available in Codex. `router` and
`verify` are bundled here. `worktrunk` is optional and should only be used when Pete
explicitly wants Worktrunk behavior for a run.

## Standing Stack

`ship` reads Pete's standing stack from Codex global instructions / `~/.codex/AGENTS.md`.
A repo's own `AGENTS.md` overrides it. The plugin is the process; the stack is Pete's.
