# Rare cases — read the section that applies when its case comes up

SKILL.md covers the common ship: one repo, a PR to main, the repo's own design, a copied
Convex database or none. These rules apply only when the contract or the target says so,
and they override SKILL.md where they differ.

## Cross-repo ship (the target repo is not the session's)

- `EnterWorktree` only takes for the session's primary repo
  (incidents: Worktrees). If the target repo's `git rev-parse --git-common-dir` differs
  from the launch repo's, never call it: work the worktree by absolute path, point
  the status line at it with `mkdir -p ~/.claude/ship-active && echo <path> >
  ~/.claude/ship-active/$CLAUDE_CODE_SESSION_ID`, and narrate the fork the moment you
  create it (`forked feature/<slug> off main @ <path>`).
- Screenshots: `<shots-root>` is the session's launch directory, which teardown does
  not remove, so delete `<shots-root>/.ship-shots/<slug>/` yourself after landing, unless the ship is
  EXPRESS, whose `result:` line names them.

## Landing variants

SKILL.md's LAND runs its step 1 checks and the merge in the worktree, then leaves
for the main checkout to remove the worktree, delete the remote branch and pull. These
replace parts of it.

- **A worktree ship didn't create** (Zero's sibling convention): don't tear down what
  isn't yours. Merge as written, `git push origin --delete <branch>`, and leave the
  worktree and its branch.
- **A session *launched* inside its worktree**, not entered through `EnterWorktree`: it
  can't leave. `ExitWorktree` does nothing, and once the directory is gone the harness
  refuses every shell command, in subagents too. Run LAND's worktree steps and the merge as
  written, then `git push origin --delete <branch>` from the worktree, skip the main
  checkout's steps and the marker's removal except `deploy:`, which runs from a throwaway
  worktree pinned to `origin/main` (`git worktree add --detach <job tmp>/deploy origin/main`
  after a fetch, removed after), and finish with `stage.sh <root> landed`. The
  SessionEnd hook removes a landed worktree when the session closes, and `wt-sweep` (every
  10 minutes) catches any the hook missed. Never `wt remove` the folder the session is
  standing in. Main's pull waits for the next session in the main checkout; say so in the
  `result:` line.
- **No GitHub remote** → `wt merge` (squashes, ff's main, removes the worktree) is the
  fallback.
- **A repo whose own land script merges the PR itself** (cells-app's `scripts/land-pr.sh`,
  which merges main into the pushed PR head, collapses it to one commit from the PR title
  and the branch's commit messages, gates that tree by the paths the PR changes,
  squash-merges and smokes main):
  - LAND step 1 runs as written, absorb, `smoke: branch`, `stack:`, the Never-stack
    check and the push included, except its full-suite runs (the tree-changed one and the
    one after an absorb): the script's gates stand in for those, so the suite never runs twice
    (cel-268-email-approvals). Still run in step 1 what the script doesn't pick for
    this diff: cells-app's land-pr runs no `mac:test`, so a `mac/` change runs it there. It
    runs the network gates (`network:typecheck`, `network:test`) only when the PR's own
    diff has a `convex/`, `convex-core/` or `packs/*/convex/` path, which misses a `lib/`
    file convex-core imports (#398 landed `network:typecheck` red that way, and its test
    runs under `network:test`). So step 1 runs both when the branch changes code
    with no such path, or an absorb brought one, and never on a diff of only what never
    ships.
  - Push everything first (it lands the PR's pushed head), put the final evidence in a
    commit message rather than only the PR body (its commit never reads the body), and stop
    the worktree's dev server and any simulator before it runs, since its suite is
    load-sensitive too.
  - Run it from the worktree in place of LAND's checks and merge, then tear down as
    written (`wt remove`, the remote branch if the script left it, `git branch -D`, the
    marker).
  - When it prints its smoke line (cells-app: `main: <sha> serving, smoke ...`), LAND's own
    `smoke: main` is skipped: one paid smoke per landing. A diff of only what never ships
    gets no main smoke from it; say so in the `result:` line rather than claim one.
- **`land: auto`** lands as `pr` does, on the QA run's `works`: a one-way door or a try-it
  change doesn't wait, a money path still waits for "merge main" (contract.md).
- **`land: direct`** replaces LAND's checks and merge: from the worktree, `git fetch origin
  && git rebase origin/main`, re-gate and smoke as LAND step 1 says, `git push origin
  HEAD:main`, confirm main moved, then teardown and `git push origin --delete <branch>`.
- **A `land: <command>`** replaces them the same way: sync with main, re-gate and smoke as
  LAND step 1 says, run the contract's command from the worktree, confirm main moved
  (`git log -1 main`), then teardown from the main checkout as written. No PR is merged; a
  mirror remote is pushed only if the contract says so.

## The PR's base is a branch another session owns

When the base is an integration branch a live session is building on (`.ship-stage` in
its worktree, or it said so), land into it the way a teammate would:
- A schema change the base's dev watcher would reject (rows QA writes with new fields
  fail its next schema push): cherry-pick the additive schema commit onto their branch
  first, with their say, before QA writes any rows.
- Message that session before the squash merge, and have it pull before its watcher
  pushes again.
- The review card lands on the base, not main (`reference/review-card.html`'s comment: the
  landed base's copy).

## Showing a storyboard on Pete's phone

Only when he asks: serve the docs home's designs folder (and the stylesheet folder its
frames link) on a LAN port, through a folder of symlinks to just those, never the repo
root, which would serve `.env.local`. Stop the server at the lock.

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

## Backends other than a copied database

**`shared-dev`.** Build against the app's dev database and touch no env file. Another live
worktree whose branch changes `convex/` turns that database into a fight: the Convex
plugin's Stop hook pushes each tree's whole `convex/` at every turn end, so each push drops
the functions the other added (a catalog ship's survived only because the other branch's
data failed validation). Check at the fork, and again right before any push to shared dev,
since a sibling can start touching Convex in between (`git worktree list`, then `git diff
--name-only origin/main...HEAD -- <paths>` in each live one). The paths are every folder the
repo's Convex code lives in, not just `convex/`: the ones the contract names (cells-app:
`convex/`, `convex-core/`, `packs/*/convex/`), else each `convex.json`'s `functions` folder.
On `backend: copy`, `branch-db.py diff <worktree> [<app-dir>]` lists the functions a push
from this branch would drop from shared dev, and exits 1 when there are any. When one does,
tell its session and plan one merged push up front: from a throwaway `git worktree add
--detach` holding both branches' `convex/`, until the first lands; then merge main and push
alone. A repo that keeps hitting this belongs on `backend: copy`.

**`per-branch`.** Provision the branch's database preview at stage 0; a worktree building
against a shared backend it changes clobbers it (incidents: Backends).
- Rewrite the worktree's env file to the preview before the first backend command and
  confirm the first deploy's host is the preview: the inherited `.env.local` carries the
  shared key, and the `--preview-name` flag does not override it (incidents: Backends).
  From here on the preview's *name* comes from that file, never from the branch.
- BUILD's pre-flight: when the branch touched `convex/`, re-push the preview (`npx convex
  deploy --preview-name <name-from-.env.local> -y`, from the worktree root: the branch name
  and the shell's leftover cwd have each sent a deploy to the wrong place).
- REVIEW: when the absorbed commits touched `convex/`, re-deploy the preview before any
  further verification. Function skew is invisible to tsc, vitest and the production build,
  and has hard-crashed a page after a green rebase (incidents: Backends).
- LAND: deprovision it at teardown.

## Native app repos (`ios:`, `mac:`)

- **BUILD's pre-flight builds the branch's app once, before REVIEW.** Upstream churn alone
  can break a native build harness between PLAN and TEST (peggy-qa's bundle id moved into
  an xcconfig and its build patch refused every build), and that is BUILD's to fix, not
  TEST's.
- **TEST** runs it through verify: `reference/ios.md` for the phone, simulators, mobile-web
  Safari and a locked phone (a simulator walks it unless the change needs the phone
  itself); `reference/mac.md` for the borrowed Mac VM.
- **LAND step 1** deletes a simulator the run cloned and returns a borrowed VM slot,
  from the worktree, since removing the worktree first orphans them.
- **LAND's teardown** removes the branch app `ios:` installed, by the udid and bundle on its
  IOS line (`xcrun devicectl device uninstall app --device <udid> <bundle>`, or `xcrun
  simctl uninstall <udid> <bundle>`; only that bundle, never the real app; a phone that
  isn't connected gets one line saying so), unless the line says `keep=yes`: a test app
  every branch installs over keeps the permissions Pete granted it, and removing it brings
  the prompts back. It deletes the build cache the line names (`dd=`, Xcode's DerivedData,
  2 GB a branch: landed branches' copies once filled the disk).

## An integration lane

Where the contract names a separate integration lane instead of main deploying, landing
pushes merged main to it. Its dev-deploy step runs from the main checkout (shared-plane
writer; incidents: Backends); hand back the lane's URL, and never make Pete run a deploy.
Watch the run for YOUR commit, `gh run list -R <owner/repo> --commit <full sha>` (get it
with `git -C <root> rev-parse <sha>` in its own call; a short one matches nothing and the
watch times out silently), and artifact-check the lane. A red shared lane you didn't cause
is a shared resource: check for an existing fix PR, and claim it with a draft PR first.

A promotion from that lane to production by the repo's own script is Pete's human-gated
ritual, never ship's to run, gate or offer, unless the contract's `release:` names it: then
Pete's release word runs it.

## Long-running workers (`worker:`)

A long-running local process that serves main's code (a launchd job, a queue runner) picks
up the change only when it restarts, so QA can't drive it before the merge: TEST proves that
path at data level (verify: API, CLI, script). After the merge, restart it once it is idle,
never with a job in flight, which the restart would fail, and say so in `result:` rather
than "nothing deploys". The contract's `worker:` line names the restart command and the
idle check; a repo with such a process and no line gets one in this PR. A launchd restart
waits out the old job's teardown (incidents: Backends).
