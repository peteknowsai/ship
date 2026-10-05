# Rare cases — read the section that applies before stage 0

SKILL.md covers the common ship: one repo, a PR to main, the repo's own design. These
rules apply only when the contract or the target says so, and they override SKILL.md
where they differ.

## Cross-repo ship (the target repo is not the session's)

- `EnterWorktree` only takes for the session's primary repo
  (incidents: Worktrees). If the target repo's `git rev-parse --git-common-dir` differs
  from the launch repo's, never call it: work the worktree by absolute path, point
  the status line at it with `mkdir -p ~/.claude/ship-active && echo <path> >
  ~/.claude/ship-active/$CLAUDE_CODE_SESSION_ID`, and narrate the fork the moment you
  create it (`forked feature/<slug> off main @ <path>`).
- Screenshots: `<shots-root>` is the session's launch directory, which teardown does
  not remove, so delete `<shots-root>/.ship-shots/<slug>/` yourself after landing.

## Landing variants

- Session living in a worktree ship didn't create (Zero's sibling convention):
  don't tear down what isn't yours — merge with `-R <owner/repo>` sans
  `--delete-branch`, `git push origin --delete <branch>`, leave the worktree.
- Session *launched* inside its worktree, not entered through `EnterWorktree`: it
  can't leave. `ExitWorktree` does nothing, and once the directory is gone the harness
  refuses every shell command, in subagents too. Run step 0, merge from the worktree
  (`gh pr merge <#> --squash --delete-branch` merges on GitHub and only fails its local
  checkout of main), do everything else that needs a shell, skip SKILL.md LAND's `rm .ship-stage`
  step, and finish with `stage.sh <root> landed`. The SessionEnd hook removes a landed
  worktree when the session closes, and `wt-sweep` (every 10 minutes) catches any the
  hook missed. Never `wt remove` the folder the session is standing in.
- No GitHub remote → `wt merge` (squashes, ff's main, removes the worktree) is the
  fallback.
- **`land: direct`** replaces SKILL.md LAND's steps 0–4: from the worktree, `git fetch origin && git
  rebase origin/main`, re-gate, `git push origin HEAD:main`, confirm main moved, then
  teardown and `git push origin --delete <branch>`.
- **A `land: <command>`** replaces SKILL.md LAND's steps 0–4 the same way: sync with main, re-gate, run
  the contract's command from the worktree, confirm main moved (`git log -1 main`),
  then teardown from the main checkout as above. No PR is merged; a mirror remote is
  pushed only if the contract says so.

## Release ritual (VERSION + CHANGELOG)

A repo that publishes releases may also declare a release ritual: it keeps a
`VERSION` file and a `CHANGELOG.md`, and its contract says to bump them at ship time.
Then the branch's last commit before merge bumps VERSION scale-aware (patch = fix or
small addition, minor = new capability, major = breaking) and adds ONE user-facing
CHANGELOG entry — what the user can now do, never branch narrative (no mid-branch
version numbers, no review play-by-play). No declaration → no bump, no entry; app
repos skip this entirely.

## `design of record: transplant <path>`

The repo's chrome is a byte-level transplant of another product's renderer, and `<path>`
is that product's bundle. Surfaces the reference owns are lifted, never designed,
measured or minimised: the contract names which hooks are the reference's and which are
the repo's own (cells: `sand-`/`ui-` are Grok's, `cells-` are ours), and ship applies its
design machinery only to the repo's own. The repo's parity check joins the gates.

- **DISCOVER.** A surface the reference owns gets no impeccable shaping and no design
  workshop. Its design is the reference bundle; its storyboard frame is the lifted
  markup, with the i18n id, the chunk and the class strings named in the caption. A
  ship that touches nothing of the repo's own still storyboards, so Pete sees where the
  lifted thing sits in the app, and locks on that.
- **PLAN.** Ponytail's ladder stops above the reference. A wrapper, a class, a token or
  an element the reference's markup carries is never waste, however empty it looks (the
  padding lives in it); "shortest working diff" applies to the repo's own code only.
- **BUILD.** A brief that touches a reference surface carries the reference path, the
  component to lift (grep the bundle for the id, take the class strings and the tree
  between), the rule lift it, never re-measure it, and the repo's parity check as a gate
  the worker runs before reporting. No craft floor and no comp for those surfaces; the
  comp is the bundle.
- **TEST.** For a reference surface, design is judged against the reference product
  beside ours (the repo's own tree audit and its screenshots), never a frame, and a
  visible difference is a finding whatever the checks say. That goes in the tester's
  brief in place of the storyboard line.

## Running under Codex Desktop

A Codex driver does not run SKILL.md. It runs the packaged Codex skill, built from
`codex/ship.md` by `scripts/build-codex.py`, which owns every Codex difference: Astra
drives and builds, no Anthropic model and no `route.py` run, a fresh Astra context
reviews the plan and the branch, effort is high throughout, and Codex's own worktree,
browser and landing rules apply. Change Codex behavior there, never here.
