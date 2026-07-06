# ship — the /ship plugin repo

The Claude Code plugin behind `/ship` (marketplace `peteknowsai/ship`). Skills live in
`plugins/ship/skills/` (`pipeline` is /ship itself, plus `router` and `verify`). The bare
`/ship` slash command is a *personal* command at `~/.claude/commands/ship.md` (a thin
dispatcher to `ship:pipeline`) — plugin commands are always namespaced `plugin:command`,
so a command in this repo would surface as the awkward `/ship:ship`. Don't add one back.

## Deploying skill changes

Merging to main does NOT update the installed plugin — running and new sessions read
`~/.claude/plugins/cache/`. After every merge, hand-deploy:

```bash
git -C ~/.claude/plugins/marketplaces/ship pull
SHA=$(git -C ~/.claude/plugins/marketplaces/ship rev-parse --short=12 HEAD)
cp -R ~/.claude/plugins/marketplaces/ship/plugins/ship ~/.claude/plugins/cache/ship/ship/$SHA
```

then repoint `~/.claude/plugins/installed_plugins.json` (`installPath`, `version` =
short SHA, `gitCommitSha`, `lastUpdated`) at the new cache dir, and remove the old
cache dir. Already-running sessions keep the text they loaded at startup — only new
sessions get the change.

## House rules

- Every change rides a `wt` worktree off main, however small — same rails /ship itself uses.
- Skill authoring discipline (pressure-test first) comes from skill-creator / superpowers
  writing-skills — this repo adds no workflow of its own.
- `ship-retro`-labeled GitHub issues are the self-improvement inbox; the maintainer batches
  them into skill PRs. Don't do skill surgery from inside a run.
