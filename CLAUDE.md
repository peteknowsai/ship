# ship — the /ship plugin repo

The Claude Code plugin behind `/ship` (marketplace `peteknowsai/ship`). Skills live in
`plugins/ship/skills/` (`pipeline` is /ship itself, plus `verify`); the pipeline's rare
shapes, contract keys, card rules and reader briefs sit in its `reference/`. The bare
`/ship` slash command is a *personal* command at `~/.claude/commands/ship.md` (a thin
dispatcher to `ship:pipeline`) — plugin commands are always namespaced `plugin:command`,
so a command in this repo would surface as the awkward `/ship:ship`. Don't add one back.

## Checks

Most scripts under `plugins/ship/skills/pipeline/scripts/` and `plugins/ship/hooks/` carry a
`--selftest`; run it for each one a change touches (`share.py` on `/usr/bin/python3`). Look
for it in the header first: a script without one takes the flag as an ordinary argument
(`share-host.sh` then waits on stdin, `gate-notify.sh` can send a notification). The rest:
`node chrome/ship-tabs/test.mjs`,
`node share/worker/test.mjs`, `bash plugins/ship/statusline-test.sh`,
`claude plugin test plugins/ship` and `~/.local/bin/ship-vms --selftest`.

## Side systems

Four systems ride along with the plugin, each with notes in `.claude/rules/`. A rule loads by
itself only for a file inside the session's own working directory. The maintainer session
sits in main and edits worktrees by path, so none loads for it: Read the system's rule
before the first edit to one of its files. Pete's Mac runs all four from this main checkout,
so a worktree edit is live only once it merges and main pulls, plus the step its line names.

- **ship-tabs**, `.claude/rules/ship-tabs.md`: the Chrome extension in `chrome/ship-tabs/`
  that files the tabs `show.sh` opens into groups. Live once Pete presses reload on it in
  `chrome://extensions`. Never connect to his own Chrome over CDP, and run `test.mjs --live`
  only when he is away from the screen.
- **ship-share**, `.claude/rules/ship-share.md`: his Share button (`share.js`, live with the
  extension's reload), `share.py` (the native host, live on the pull) and the Worker in
  `share/worker/` behind share.peteknowsai.xyz (live after `npx wrangler deploy` in that
  dir). Run `share.py install` only from this main checkout: it writes the host's path from
  where it runs, and one written from a worktree dies with it. Never echo the upload key.
- **ship-vms**, `.claude/rules/ship-vms.md`: the menu bar item in `menubar/` and
  `mac-vm.sh`. A script change is live on the next click, a Swift change only after `bash
  menubar/install.sh` from main. Never run `mac-vm.sh view`; Pete's own VM, `pete-mac`, is
  driven only through his `my-mac` skill.
- **Status line and gate buttons**, `.claude/rules/status-line.md`:
  `plugins/ship/statusline.sh`, and the mod in `plugins/ship/hooks/` that draws the gate
  buttons. Both read the stage marker `stage.sh` and `route.py` write. The status line is
  live on the next refresh, through the `~/.claude/statusline.sh` symlink; the gate buttons,
  like the skills, only after the cache deploy below, in sessions started after it.
  `claude plugin validate plugins/ship` checks nothing here.

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
  landing or another ship's data. A fix that makes a script do what the skill text already
  says, with its commands, arguments and the files it keeps unchanged, goes out once it is
  proven, since a running ship picks it up with no rule to reread; a fix that also changes
  skill text waits for the batch whole. A fix that adds text to a skill takes out as much.
  Don't do skill surgery from inside a run.
- **Pete's "merge main" for another ship, typed here** (2026-11-09, cells-app land-once).
  Ships refuse a SendMessage relay by design (cel-278 landed on one), and the skill keeps no
  other path, since a ship can't tell a sent word from his typing. Only the maintainer session
  named `ship`, in this main checkout, sends it, never a ship run on this repo. It notes the
  head of that ship's branch when he says the word, then sends his exact words (never "looks
  good" read as a landing) with the Mac connector's `send_gate_word` to the session
  `get_session` shows in that ship's worktree, once its `.ship-stage` reads `gate:test` on that
  same head, watched with a background `until` loop. A moved head, a second ship at
  `gate:test`, or any other word goes back to him first.
