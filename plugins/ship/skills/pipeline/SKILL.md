---
name: pipeline
description: Use for any code change in a product/web repo, quick fix to full feature. Ship sizes the ceremony itself and stops only when Pete's taste or a risky merge is in play. Explicit verbs pin the process, "/ship express <tweak>" and "/ship design <idea>"; anything else sizes itself. EXPRESS (a tweak, no spec or plan, straight to a tested merge), SELF-DIRECTED (writes its own plan, builds, reviews, tests and merges with no stops), or GATED (a storyboard and a plan card Pete answers), and a gate fires only when Pete's answer would change what gets built. Auto-triggers on change requests; you never type it. Do NOT use for a question or pure analysis. Never edit main directly.
---

# /ship — idea to merged, in one command

You run a feature from idea to merged. Pete is heavy in DISCOVER (his taste), glances at a
card only when it needs him, and comes back at the end. Everything else is automatic: ship
builds, reviews and tests its own work, and its QA pass lands it.

**Scope is the spec, Pete's dial, not yours.** Ship builds exactly what the design spec
covers, the whole thing in one pass: one plan, one build, one review, one merge. Never
decompose a specced feature into "Ship 1 of 4", never defer specced surfaces to a "later
phase". A bigger spec means a bigger plan and a longer build, and that is wanted. Phasing is
Pete's to ask for, never yours to impose.

**Every artifact Pete sees is a condensed HTML page** in the html-effectiveness patterns
(https://thariqs.github.io/html-effectiveness/): plain-English lead first, structure as
diagrams and side-by-sides, depth behind collapsibles, anything visual a live embed. Prune
hard inside that format and never reach for a new one: Pete tried landing-page cards and kept
the plain doc ("maybe there's just a little bit of pruning"). The storyboard is the one page
that is mockups, not prose. The execution plan is machine-facing markdown he never reads.

**Pete's stack** is in his global instructions (Eve · Vercel · Convex · Clerk · Stripe ·
Next; Cloudflare keeps DNS, R2 and its Workers): never re-ask it. The repo's own `CLAUDE.md`
/ `AGENTS.md` overrides it. Escalate a library choice only when it is architectural *and*
outside the canon.

`reference/incidents.md` holds environment facts from real failed runs: read its section
before merges, teardowns, deploys, a dev-server restart, a background push, a host's first
push, a storyboard opened in Safari, or debugging a dispatch or a refused command.

**Not ship's job:** phasing (the scope law); superpowers' `brainstorming`, on any lane
(ship's DISCOVER replaces it), and `executing-plans`; strict TDD outside money paths, where
`superpowers:test-driven-development` runs; grilling outside DISCOVER; manual worktree
management (`wt` owns birth to death); a production deploy or database push by hand; a
promotion script that is Pete's ritual.

## Verbs and sizing

The first word pins the process: `express` or `design`. Anything else, a bare `/ship <idea>`
or the auto-trigger, sizes itself. Every verb rides the same rails.

- **`/ship express <tweak>`** pins EXPRESS. It pins ceremony down, never safety: a money
  path or a taste call promotes per the mid-flight rule regardless.
- **`/ship design <idea>`** pins GATED and the full design workshop (storyboard, rounds,
  lock, plan card, go, plan, build). Pete is saying taste is in play; never downgrade it,
  however mechanical the work looks.
- **A claude.ai/share link** is Pete's own conversation: read it at once, headless, since
  WebFetch gets only the footer of a page that renders client-side. The chrome-devtools MCP
  (navigate, wait for "You said", take the text) or `chrome-headless-shell --headless
  --virtual-time-budget=15000 --dump-dom <url>` renders the whole chat.
- **Pasted agent output** (another agent's report, not an idea) means "land what it made, and
  build the fixes it recommends": say so in one line up front, and size that.

**The fork comes first.** The moment a verb lands, resolve the target repo, run stage 0's
read-only checks (seconds), and fork. The marker flip is how Pete sees ship engage; nothing
is asked and no recon starts before it. One exception: a bug card reproduces read-only
against main first, posting one line that it is doing so, and forks only once a code change
is known. That covers a brief that may end in no code ("if it's gone or not ours, close it
with evidence") and a recheck of a fix that just landed: compare the bad data's timestamps
with the fix's merge time first, since a row written before the fix proves nothing (CEL-174
forked and copied a database for one). A card whose dated repros on main predate every change
to the cause files (`git log origin/main --since=<repro date> -- <files>` prints nothing) is
reproduced already: recheck it by code, and repro live only when that code moved (cel-283). Keep the repro's files at absolute paths under the
job's tmp. A run that closes the card that way has no worktree, PR or landing; its proof goes
on the card (CEL-172).

**The rails never change:** a worktree off main, its branch pushed at once with a draft PR
tracking it, pushed at every milestone, then review, then TEST, where ship writes a QA script
and runs it itself the way Pete would and its pass lands it. Nothing edits main directly and
nothing lands untested. What scales is the ceremony before TEST, and you size it:

- **EXPRESS: a quick tweak or fix.** The whole diff is visible before you start and there is
  no money path. No spec, no plan, no cards, no stops: worktree, change, gates, pre-flight,
  push and links, TEST, land on a pass, `result:`. No branch readers, except one Wonder read
  (`muse.py review`) before TEST when the diff is text a model reads (a prompt, a tool
  description) or acts on the machine (kills processes, deletes files, force-pushes):
  CEL-181 and CEL-134 shipped one-reader bugs there. A text transform or row filter still
  gets REVIEW's corpus run. A change to a function many callers share is SELF-DIRECTED,
  however small. A dab of `ponytail` (smallest diff), `impeccable` for anything visual. A
  diff of only docs skips the gates, pre-flight and app walk: TEST is verify's docs fact
  check. A diff of only tests, evals or test scripts is proven by its own green run, with
  nothing loosened that the PR doesn't name (CEL-231, CEL-256). The first Pete hears of an
  EXPRESS ship is its links.
- **SELF-DIRECTED: real work with no taste question in it.** Write the machine-facing plan
  you need, then build, run REVIEW's two readers and TEST, land, `result:`. No stops before
  TEST and no plan card; the review card is the record.
- **GATED: Pete's taste or direction is in play.** A new user-facing surface, visual
  identity, a product tradeoff, ambiguous scope, a money path.

**A card key doesn't size the ship**: an EXPRESS-sized board card runs as EXPRESS. **The
gate test is never size**: it is whether Pete's answer would change what gets built, or the
change is risky or irreversible (Every stop). Mid-flight, promote the moment taste or
direction appears: park, write the spec from what you've learned, show the storyboard. Size
alone moves EXPRESS to SELF-DIRECTED, never to a gate. Never use an autonomous lane to slip
a taste call past Pete.

## Talking to Pete

His global instructions set the voice. Ship adds these, for everything he reads: stage
updates, `needs input:` and `result:` lines, storyboard captions and questions, the cards and
the PR body's first lines. Messages between sessions are exempt.

- **Open with what this is**: the repo and the feature in his words, with its card key
  ("cells-app, the flaky-tests fix (CEL-74):").
- **Ship's own words stay inside ship**: driver, lane, tier, marker, gate, absorb, BACKEND,
  ledger, route, sweep, pre-flight, fan-out, brief. A word the run coined appears only if
  Pete used it first, or with a few words saying what it is.
- **A call he has to make** recaps the decision in one line and gives ship's pick, so "yes"
  is a complete answer.
- **Every stage flip posts one line**: the goal, the stage, what's next. Again after a
  compaction or a side job; five runs had him asking "where are we?".
- **FleetView reads the session.** Pete names it `ship:<slug>` at spawn. Status lines ride
  with the next tool call (`🔨 build 4/5 · <slug>`) and say where the work stands, never
  the last command run. A turn that stops for him ends with a
  `needs input:` line (the row goes to awaiting input); a landing ends with `result:`
  (completed). Both end with `branch <branch> · worktree <path>` (`detached@<short-sha>`
  before a branch exists), which catches the cross-repo case. Keep those prefixes and the
  tail exactly; the words between follow this section.

## Working rules

- **Call this skill's scripts by absolute path**, the base directory the harness printed when
  it loaded plus `/scripts/`, typed out in full, never through a shell variable.
- **The worktree guard** refuses any command it can't prove stays in the worktree, and
  misreads some that do (incidents: The worktree guard). Read and search with the Read and
  Grep tools; one plain git command per call; anything multi-step, any heredoc, loop or
  computed path is a script file written with the Write tool into the job's tmp (or the
  worktree as `.ship-<name>.mts` when it imports the repo's packages), run by its full path.
  A command on the main checkout waits until LAND has left the worktree, never a script that
  hides it from the guard.
  Commit messages and PR bodies are files too: `git commit -F`, `gh pr create --body-file`.
- **Sandbox off** for anything that writes outside the worktree, the job's tmp included (the
  sandbox denies writes under `~/.claude/jobs`; the Write tool can), or binds a port: the fork,
  `stage.sh` on a new worktree, `route.py log`, `muse.py`, `decisions.py` writes, anything
  that talks to GitHub (`gh`, `git push`, `git fetch`: the sandbox's proxy fails their TLS),
  any git command that rewrites the tree or makes a branch (the sandbox denies writes under
  `.claude/` and to `.git/config`, and CEL-213's rebase stopped halfway), a script that writes
  under `.claude/` (the Edit and Write tools can; cel-285's merge of the checks skill could
  not), gates, smokes, dev
  servers, `tsx`, and anything that reaches a local server, since a sandboxed `curl` at
  localhost reads as a dead server. Everything else stays in the sandbox.
- **`$TMPDIR` changes with the sandbox** (`/tmp/claude-<uid>` inside, `/var/folders/…/T`
  outside), so anything that crosses gets an absolute path under the job's tmp.
- **Env files are given to the tool** (`tsx --env-file=.env.local`), never sourced.
- **Every `gh` call names its repo**, `-R <owner/repo>`: in a fork with an `upstream` remote
  gh resolves against upstream and finds no PR (screendrop-worker, 2026-11-05).
- **Calls sent together all run**, even when the first fails, so a call that needs another's
  result goes in the next message (a wait beside a failed step ran out its whole timeout).
- **A background or Monitor command reports nothing until its pipe flushes**: `grep
  --line-buffered`, never a bare `| grep` or `| cut`. A wait needs no loop: `gh pr checks <#>
  -R <o/r> --watch`.
- **Never idle while a run or a subagent works.** Work the non-tree list meanwhile (the card,
  the commit message, the ledger lines), and at a gate notify, then keep doing non-gated work.
- **How a turn ends.** On the autonomous lanes nobody says "continue". A summary that
  announces the next step, an offer to carry on, a list of decisions none of which blocks the
  rest, and a stop because a milestone landed are all wrong while work is owed. Status goes
  in the same message as the next tool call. A turn ends at a stop (`needs input:`), at
  `result:`, when nothing can move without Pete, or while you wait on background work with
  nothing else to do.
- **Pete's budget word outranks ship's defaults.** When he caps subagents or spend for a run,
  skip the Opus readers, keep Wonder (no Claude quota), log each skip (`review=opus
  stage=<plan|branch> note=skipped:budget`), and say what that skipped in `result:`.
- **Log every durable call**, on any lane, that a stop or Pete mid-run settles (direction,
  scope cut, architecture or tool choice): `decisions.py log --file <json>`
  (`{"decision","rationale","source":"user"}`); a reversal is `decisions.py supersede <id>
  [<id>...] --file <json>` with ids from `recent`. Never turn-level edits.

## Engines and readers

**Opus 5.5 writes; Muse Wonder Full reads beside it** (Pete, 2026-10-24). The driver and every
subagent it starts (`model: "opus"`) run Opus 5.5 at high effort. Wonder reads the plan and
the branch and never writes. Nothing else runs. Codex is off (Pete, 2026-10-22): "test in
codex" gets one line saying so, and this session tests.

**One loop does the work.** The driver builds, tests and fixes in its own context, where it
reads the raw diff, test output and browser snapshot; a subagent hands back a summary, and a
summary drops what the next step needed (briefs left the wiring between files to the driver
on 6 of 9 tasks in one ship). A subagent earns its seat for three jobs only:
1. **Fresh eyes**: the plan review and the branch review, where not having written it is the
   point.
2. **A sweep whose answer is all the driver needs**: recon, an expert consult, a lookup.
3. **Reading the rest of the ship never needs**: a wide mechanical migration that would crowd
   the driver. It gets a brief, logs `engine=opus` with the reason in `note`, and the driver
   reviews its diff and runs the gates as for its own.

Speed is never the reason: Pete doesn't measure a ship by wall time. Never `claude -p` from
inside a session. **A brief** is the driver's envelope: the exact files and the wiring among
them, signatures, test cases, constraints; call the Skill tool with
`mattpocock-skills:writing-for-agents` once per run before the first. The driver reviews what
comes back and runs the gates before anything is committed, and owns git. One writer per tree.

**Compaction is survivable by design.** A ship keeps its state on disk: the plan, a commit
per task, the marker, `.ship-done`, the ledger, and in the job's tmp the triage file and the
QA result. After each compaction `hooks/ship-recap.sh` prints the stage, the plan, each task
done or todo, the branch's commits and uncommitted files: trust it over the summary, reread
the plan, this skill's section for the stage and any triage or QA file the stage wrote, and
post Pete the one line.

**The readers: Opus and Wonder, two labs.** A reader shares the blind spots of code its own
lab wrote and goes easy on it (Pete, 2026-10-14). The Opus reader is a fresh subagent whose
brief says to assume the writer was wrong at every seam. Wonder runs as `scripts/muse.py
review <worktree> <brief> <out-dir>`, a background Bash call: read-only, findings in
`<out-dir>/last.md`, `<out-dir>` in the job's tmp (muse.py refuses one inside the worktree).
Any nonzero exit means Muse is out (5: its quota, with the reset; 2: a usage error, so read
stderr; 6: the tree changed under it), and so does exit 0 with `last.md` missing or empty,
which is never a clean read (incidents: Dispatch): a fresh Opus subagent takes Wonder's brief, its row
is `review=opus … note=for:wonder` so the ledger never credits Wonder with it, and `result:`
says so. Nothing writes in the worktree while Muse reads, the gates, a build, a
commit and a dev server's start included: `next build` and `next dev` rewrite the tracked
`next-env.d.ts` (find-three-more, CEL-233), so a server TEST needs is up before the read
starts. Gitignored files don't count. Muse runs only through `muse.py`, never a hand-typed
`muse exec`. Readers report and never edit. A claim about how a
dependency behaves at runtime is checked in its installed code (`node_modules/<pkg>/dist`),
not its docs (Eve's queued messages, 2026-10-14).

**The ledger** (`~/.claude/ship-ledger.jsonl`) is kept by `scripts/route.py`, from the
worktree:
- `route.py plan <plan.md>` after PLAN: saves the tasks, starts the clock, marker to
  `build:0:<M>`.
- `route.py gate <cmd>` runs each check and records whether it passed, one call per check.
- `route.py log repo=<r> ship=<slug> task=<n> engine=<driver|opus> verdict=<clean|fixed|redone>`
  after each task's commit: it fills `seconds`, `gates_first_pass` and `fix_rounds` from the
  clock and the gate runs, and counts the task done. Never type a number you don't have.
- `review=<wonder|opus> stage=<plan|branch> real= false= only= nits=` per reader, timed by
  `out=<out-dir>` on Wonder's row (route.py reads muse.py's `seconds` file there) and by
  `seconds=` from the subagent's reported duration on Opus's; and `recall=<shown> used=<n>`
  on design ships. `route.py readers repo= ship=` exits 1 until both branch readers are
  logged since the branch began and the branch adds its review card. `route.py report`
  compares engines and readers; if
  handed-off tasks keep needing more fix rounds, job 3 above shrinks.

**Browser work runs on the chrome-devtools MCP** (headless, a fresh profile per session): the
pre-flight, the QA run, grounding in the live product. A subagent loads those tools with one
ToolSearch call. A reference product behind Pete's login (muse.ai) is his: ask for
screenshots, and use the `mcp__claude-in-chrome__*` tools only when he asks, since they drive
his own Chrome. A coding worker never drives the browser. Every automated browser is the
chrome-headless-shell build, never the Google Chrome app run headless, which takes his Dock
click; never connect to his Chrome (each connection pops "Allow remote debugging?").

**Every page Pete should see goes through `scripts/show.sh <root> <slug> <kind> <file|url>
[done]`**, kind `storyboard`, `plan`, `review`, `test` (localhost) or `preview`, never a bare
`open`. It opens with `open -g` so Chrome never takes his screen, tags the URL so his
ship-tabs extension files and titles it and closes the tab it replaces, keeps each kind's last
URL in `.ship-shown/<kind>` for the gate buttons, and republishes a doc he shared from its
Share button (sharing is his press, never ship's). `done` on the landed review card closes
the ship's other tabs.

## The repo's contract

A repo tells ship its commands in its `CLAUDE.md` / `AGENTS.md`. Every key is optional; each
is in full in `reference/contract.md`, read the first time a stage uses it.

- `gates:` the commands that must pass. Full at BUILD's pre-flight, after an absorb that
  changed the tree, and at LAND step 1 when the tree changed since the last full run; scoped
  (typecheck plus the runner's changed tests) for each task and fix round; always through
  `route.py gate`, sandbox off.
- `dev:` starts the worktree's own server on its own port and prints its URL.
- `preview:` prints the branch's preview links after each push, or `on demand`.
- `test-auth:` how the QA run signs in: `seed`, `form` or `none`.
- `backend:` `copy` (Convex default), `shared-dev` or `per-branch`.
- `stack:` runs `scripts/stack-check.sh`, before TEST and before landing.
- `ios:` / `mac:` build and install the branch's native app and print its IOS or MAC line.
- `worker:` a long-running process main runs: its restart and idle check.
- `deploy:` the repo's command that puts main live where the host doesn't build main.
- `smoke:` `branch <cmd>` at the pre-flight and LAND, `main <cmd>` once per landing.
- `live:` what landing deploys and how to watch it.
- `land:` `pr` (default), `direct`, `auto`, or the repo's own command.
- `release:` the word and command that put a parking-lot main on production.
- `board:` where tickets go and what each column means.
- `ship: no` declines, saying why.

`reference/rare-cases.md` holds the rare shapes: read its section before stage 0 when the
ship targets another repo than the session's, the contract declares a `land:` other than
`pr`, a backend other than `copy`, `ios:`/`mac:`, `worker:`, an integration lane, a release
ritual or `design of record: transplant`, or the PR's base is a branch another session owns.

## The pipeline

Each stage writes its marker with `scripts/stage.sh <worktree> <stage>`; the status line
and FleetView read `.ship-stage`.

### 0 · Fork  → marker: `discover`

**Read-only checks first, seconds each.**
- **Prereqs**: a git repo with a base branch and a commit (a zero-commit repo: `git add -A
  && git commit -m init` first). No GitHub remote falls back to `wt merge` at LAND.
- **The base branch**: `git symbolic-ref refs/remotes/origin/HEAD`, else `origin/main`,
  else `origin/master`, else local `main`. Every `main` below means that branch.
- **A card key in the idea (`CEL-103`)**: `git branch -a --list '*<key>*'` and `gh pr list
  -R <o/r> --state open --search <key>`. A hit with no live session (none in ListAgents, its
  `.ship-stage` not moving) is a stalled ship: resume it there, PR and all (a fresh fork once
  rebuilt CEL-103 beside its first run). A hit with a live session is another ship's: tell
  Pete in one line and stop. Then `git log origin/<base> --since=7.days --format='%h %s' --
  <files the card names>`: a merged PR that meets the card's done-when lines closes the card
  instead (CEL-241 rebuilt one).
- **Free disk**: `df -h ~` under 10 GB is one line to Pete before forking (a full disk failed
  `stage.sh` mid-LAND).

**Fork**, sandbox off, from a fresh fetch so a stale local main costs nothing:
```
git fetch origin
wt switch --create feature/<slug> --base origin/<base> --no-cd --format=json -y
```
A fork that half-ran ("Branch already exists", no worktree) finishes with `wt switch
feature/<slug> --no-cd -y`. Then `EnterWorktree({path})` on the JSON's path: the status line
and FleetView read the session's cwd, so a run working by absolute path from main is
invisible to Pete. It is required in the session's primary repo, over a background session's
default to skip it. A second ship in one session calls `ExitWorktree({action:"keep"})`
first, and its shell can still reset into the first ship's removed worktree after that
(incidents: Worktrees): the new worktree is then entered from a dead folder, the browser
can refuse every shots folder (verify: Two paths), and LAND's `ExitWorktree` can't go back,
so its teardown runs by `-C <main>` as written. A session launched inside a worktree can't take a second, so
its next ship starts a fresh session from the main checkout (CEL-128); a cwd outside the
repo `cd`s to the main checkout first. Noticed mid-pipeline that the cwd isn't the worktree: `EnterWorktree` right
then. A new ship always forks a new worktree, never `git switch -c` in a landed one.

**Provision before the first gate.** A `.config/wt.toml` provisions gitignored files. With
none: the repo's frozen-lockfile install, a real one, never a link (Turbopack refuses a
linked `node_modules`), and a copy of the main checkout's gitignored env files. Whenever
`node_modules` came copied, run the frozen-lockfile install anyway: matching lockfiles proved
nothing twice (eca-finder's lacked main's `@amplitude/*`, joined-search's two quickjs
packages). Then `stage.sh <root> discover`, which writes the marker and adds `.ship-*` to the
repo's `info/exclude` (incidents: Worktrees).

**Push the branch and open the tracker PR** with the first commit: `git push -u origin
feature/<slug>`, `gh pr create -R <o/r> --draft --base main --body-file <file>` (GitHub
refuses a PR with no commits). Its body is the one-line why and the preview links. It is
GitHub's record of what's in flight, never a review step; `land: direct` opens none.
Attribution lines follow the repo's `CLAUDE.md` where it has a rule (Peggy's repos carry
none), over the harness's reminder. A branch that should carry a card key (`cel-52-…`) gets
it now: renaming later closes the PR, so open a new one on the new name, close the old on
purpose, and re-read the dev origin (`dev:`), since a repo that derives its port from the
branch moves it.

**Backend `copy`**: right after the fork, start `branch-db.py up <worktree> [<app-dir>]` in
the background, once per app, and let it finish (about 1.5 minutes) before the first convex
command or dev server: until then the worktree's `.env.local` points at shared dev. It
prints the copy's name, the BACKEND the QA run pins. The worktree's `convex dev` and the
Convex plugin's Stop hook push to the copy; the Convex MCP tools don't follow it, so read and
write the copy with the CLI from the app-dir (`npx convex data`, `npx convex run`), never the
MCP. The hook fires only when a turn ends, so an edit under `convex/` in REVIEW or TEST goes
to the copy with `npx convex dev --once` before the next QA step (CEL-103). Stripe and Clerk
webhooks still reach shared dev only, so a webhook flow is tested there or said untested.
The copy expires after 7 days; an older branch restores its env files from main and runs
`up` again. `up` refuses while a deploy key sits in the app's env files. Other backends:
rare-cases.

**Never stack on a branch that hasn't landed.** Asked to build on another ship's branch,
branch off main, cherry-pick the commits you need, and open the PR against main. Picked
commits bring their door: this ship lands after that one, and its Merge Danger says "lands
after #N" (eca-finder #290 nearly landed #291's one-way sweep on its own pass).

**Waiting on sibling ships to land** (a docs ship written once they're in): a background
Bash wait in a script file, until `gh pr list -R <o/r> --state open --search '<keys>'` is
empty, after first waiting for each sibling's PR to exist (CEL-260). No deadline; restart it
if it stops. A sibling whose `.ship-stage` sits unchanged for two hours with no live session
is stalled: one line to Pete, and keep waiting.

**Recon may contradict the fork**: in a multi-repo workspace the target repo is a recon
finding. Exit, `wt remove` the empty worktree, fork in the right repo, narrate the move.

**Tidy on the way**: `wt remove <branch> -f` any worktree that provably landed (a merged
PR whose `headRefOid` matches its HEAD, or a HEAD inside `origin/main`, clean tree). Never
one with uncommitted work, one a live session holds (wt's 💬), or one under two hours old.

### 1 · DISCOVER — Pete's taste, up front  → marker: `discover`, then `gate:1`

- **Recall first, on design ships**: `decisions.py relevant "<the idea in one sentence>"
  --ship <slug>` (from inside the repo) prints up to six decisions that bear on it and
  records them as shown. They are settled calls: don't re-ask Pete one, and say so out loud
  when reversing one. When one changes what the ship does, `decisions.py used <slug> <id>
  "<what it changed>"` right then: the repo's log keeps it through a compaction, a resume and
  teardown, and a count from memory is a guess (company-pack). A call marked `[stale]`
  gives a retired engine a ship job, and this skill's text wins over it.
- **Grill on the storyboard, never in chat.** Call the Skill tool with
  `mattpocock-skills:grilling` for how to ask: each round asks every question open now,
  numbered Q1, Q2…, each with your pick worded so "yes" takes it, and recon answers the facts.
  Nothing is asked before round 1: where an answer would change what to draw, draw your pick
  and ask under it.
- **Recon is a read-only Opus subagent; synthesis stays with the driver.** Its brief: a reuse
  audit (grep the whole repo, data layer included, for every core noun the feature
  introduces); the liveness of any existing surface the design lands on (current design
  system? reachable from primary nav? touched recently?), since a deprecated page serves
  happily; the ships in flight whose surfaces overlap (`git worktree list` and each
  `.ship-stage`), whose sessions you ask (ListAgents, SendMessage) before round 1; and every
  count from an API total (`gh api search/issues` `total_count`), never a `--limit` list's
  length. The spec names the chosen surface (incidents: Design).
- **A bug-shaped request gets an empirical root-cause check**: reproduce it or read the
  runtime evidence, never spec from a hypothesis. When the measurement contradicts the card,
  the measurement wins, and the PR and card say so (CEL-74).
- **Consult the installed domain experts** before drawing, as harness subagents in parallel
  with recon, one round: match the session's own roster of agents and skills against what the
  change touches (`convex/` → the Convex expert and its authz auditor, a Claude Code
  capability → the claude-code guide, DNS or the edge → `cloudflare`). Nothing matches,
  consult nobody. Ask what changes the design ("what will bite us at scale", "is there a
  component for this"), weigh answers like recon, and name a consult that changed a decision
  in the plan. Pete's settled calls and the repo's `CLAUDE.md` outrank any agent.
- **A visual feature runs `impeccable`** and its Setup (`<skill dir>/scripts/impeccable
  context`; the repo's PRODUCT.md / DESIGN.md are the visual authority): a new surface takes
  its shape path, a refinement stays on the incumbent world. Before new work, merge
  `"buildPath": "code"` into the repo's gitignored `.impeccable/config.local.json`: the
  storyboard is the one approval Pete sees, never impeccable's decision page. Imagery inside
  a frame is drawn in code. **Ground it in the live product**: a subagent walks the running
  app over chrome-devtools and reports the real theme and CSS with screenshots, never in-repo
  mockups.
- **The storyboard is round 1**, `specs/designs/YYYY-MM-DD-<slug>.html` in the docs home,
  from `reference/storyboard.html`, whose comment holds its rules. It is an artboard board:
  every screen and state its own live-HTML artboard at true device size, in the product's own
  stylesheet, side by side in story order, each with a code (A1, A2…) Pete answers by. It
  tells the whole flow, from where the person comes from to where they land. An open
  direction is an options row, never prose. The words are captions and the round's questions;
  recon goes in one collapsed block at the foot. The driver draws every frame and caption; a
  subagent may build a heavy asset a frame calls for. Commit it, `stage.sh <root> gate:1`,
  `show.sh <root> <slug> storyboard <file>`, and end the turn with `needs input:`
  ("storyboard round 1: reactions?"). Every round is a hard stop.
- **Rounds**: Pete reacts by code; "yes" takes every pick on the page. Redraw in place in the
  same file, bump the round in its `<title>` and `data-round`, delete a killed frame and never
  reuse its code, drop answered questions and continue the numbers, re-`show.sh`, and stop
  again. Push back where taste warrants it. Asked to show it on his phone: rare-cases, which
  never serves the repo root.
- **Lock = gate 1** ("lock it", "this is it", "yes"): commit the storyboard as it stands.
  Every frame in it ships and nothing else does. Log the direction (Working rules), then PLAN.
- **Smaller shapes.** A trivial visual change may collapse to one frame and one confirm,
  never zero on GATED. A non-visual GATED ship gates on a one-screen board: the lead, the one
  question that matters, depth collapsed. When Pete asks to take a frame into pen (Pencil),
  harvest the result back before the lock. A design of record on another branch is copied
  into this branch at PLAN, and every brief points at the copy (CEL-146's frames were
  trimmed under it).

### 2 · PLAN  → marker: `plan`, then `gate:2` when the card has a call

- `stage.sh <root> plan`. `ponytail` is the waste critic: it cuts reinvention and gold
  plating, never a frame Pete locked.
- **GATED renders the plan card** from `reference/go-card.html`, whose comment holds its
  rules: the locked storyboard first, then the work list, the cut list, his calls, risk, go.
  Calls are plain language and only ones that change what he gets. Commit it, `show.sh … plan`
  it. **With a call** it is gate 2: `stage.sh <root> gate:2`, `needs input:` ("go?"), a hard
  stop; after his "go", `stage.sh <root> plan` again. **With none** it is shown, not waited
  on: one line ("plan card: no calls, building"), no marker, straight on. SELF-DIRECTED and
  EXPRESS render no card.
- **Anything Pete must create himself** (an OAuth app, an account, a key) is a call on the
  card, or on a cardless lane a stop now (`stage.sh <root> gate:input`, `needs input:`),
  never a surprise at TEST (cc-bridge's GitHub app swapped for Cloudflare Access once asked).
- **Then the execution plan**: call `superpowers:writing-plans` for ONE plan covering the
  whole storyboard or spec, saved as `specs/plans/YYYY-MM-DD-<slug>.md` in the docs home. It
  carries what a frame can't: copy as data, routes, behaviour, states, a11y, and for each UI
  task its frame (`<storyboard>.html#A3`). Each task is a `### Task N: <name>` heading, which
  `route.py plan` counts, and names its files, the signatures it adds, and its test cases,
  brief-grade. A change Pete asks for after go is an express round, not a re-plan.
- **The plan writes its `## QA cases`**: numbered steps TEST walks, each one thing a person
  does and what they should see, covering every frame, requirement and edge the spec names,
  and each a case that fails on main's code, a race fix's at every ordering it claims, the same
  instant among them (verify: Pick cases that can fail). TEST walks them as written, may add, never drops
  one. Writing them before the code keeps them about what was asked, not what got built.
- **A task that hooks into a dependency's runtime** (a framework's workflow, a bundler's
  transform, the shape a model must answer in) is followed by a driver live check of the real
  thing (CEL-80's found two bugs no test could). **A task that computes from rows another
  path writes** gets one end-to-end test through the real writer (incidents: Design).
- **Consult an expert again** only for a question the plan raises that the storyboard didn't
  settle (schema shape, migration order, an auth boundary). On SELF-DIRECTED this is the
  lane's only consult.
- **Wonder reads the plan before BUILD** (an Opus subagent when Muse is out), from
  `reference/plan-review-brief.md` written to a file. The driver triages: fix the plan where
  real, decline nits and anything the spec doesn't ask for, and log `route.py log repo= ship=
  review=wonder stage=plan real= false= nits= out=<out-dir>`. Nothing goes back to Pete unless it
  changes what gets built. Then `route.py plan`. No task starts before the review lands,
  unless the plan names it a spike.

### 3 · BUILD  → marker: `build:N:M` (N done of M)

- **The driver builds every task itself, in plan order**, test first where the task names its
  tests. Per task: read the diff, run the gates scoped through `route.py gate` (one call per
  check, so a red is one fix round), commit, then `route.py log`. Build all M tasks in one
  session; land only when the whole plan is built. A run that skipped `route.py plan` writes
  `build:0:<M>` itself.
- **Push at every milestone and hand Pete the links.** After a commit, push. With a per-push
  `preview:`, run it once the builds settle, never blocking the next task, and post one line
  per app with what changed and what to try, the tracker PR's body carrying the newest; on
  demand, post the localhost. A failed build is
  yours to fix before you post.
- **Before the first task, check the plan's files against work in flight**: `gh pr list -R
  <o/r> --state open --json number,headRefName,files` and `git log origin/main --since=1.day
  --name-only`. A task another PR already makes is dropped and absorbed once it lands; one
  mid-flight is asked about (showing-followups rebuilt what cells-app #206 had in review).
- **A task's check is the diff and the gates.** Nobody drives the app per task: the
  pre-flight is once at the end, the QA run is TEST's. One exception: code something else
  starts (an MCP server, a worker, a job) that finds a file by a relative name gets one run
  from a temp working directory (fast-readers' worker loaded tsx by bare name).
- **A script that writes data keeps a record and an undo** before REVIEW. When REVIEW or TEST
  tightens the rule those writes followed, recheck every one (5 of 19 catalog links were
  wrong). A rule's first run over existing rows is a dry run: the list of what it would
  change, sorted by reason, read before any write.
- **A subagent's task** (Engines, job 3) gets the standing boilerplate, each line from a
  burned run (incidents: Dispatch): one task per brief with the plan's code pasted in, the
  exact test commands and the files it may touch; "do it, do not propose"; test files whose
  assertions the change invalidates are in scope; the final message is STATUS, TESTS,
  CONCERNS, a longer report in a file in the worktree; it never commits and never runs `git
  reset/checkout/stash`. A repo whose rules load by path (`.claude/rules/`) gets those files
  named. A subagent never gets a copy of the env files (the Convex Stop hook would push its
  half-edit). A Convex repo's briefs say `convex codegen` prints "Uploading functions" and
  deploys nothing. Never add scope by message mid-run: findings wait for its report and go
  back to the same worker (SendMessage) as the next round. Two wrong diffs and the driver
  writes it, `verdict=redone`. Its report is checked against every message it was sent, each
  fix item done. Silence is not a signal: if its work is in the tree and no report has
  landed, review the diff and run the gates yourself.
- **A UI task matches its frame** (`specs/designs/<storyboard>.html#A3`, markup and CSS), and
  a subagent writing UI is told to read `~/.claude/skills/impeccable/reference/craft-floor.md`
  and the storyboard's three banned model defaults, since it doesn't get impeccable's hook.
- **A cut after go is said out loud**: any planned item dropped, narrowed or swapped, a model
  or tool that differs from the reference included, goes in the next message and `result:`.
- **Discipline**: `ponytail`; `superpowers:verification-before-completion` before calling a
  task done; `superpowers:systematic-debugging` on a red. A test failing three or more times
  across full runs is a bug, never a flake: root-cause it (shared temp files or ids between
  parallel suites, usually). A timeout goes up only for a test slow by design (passes alone
  every time, its time its own work), and the commit gives the numbers. One that won't
  reproduce ends as "no repro" with what was tried, never a guessed fix.
- **The pre-flight closes BUILD, so the QA run never opens a broken page:**
  1. Full gates and, for a framework with its own production build, that build (dev server
     stopped first: contract.md). On `backend: per-branch`, the preview re-push rare-cases
     names.
  2. The key names in the worktree's env files against the main checkout's and
     `.env.example`: a key main gained after the fork is missing here.
  3. A native repo builds its app once now (rare-cases: Native app repos).
  4. Boot the app on this worktree's own port (`dev:`), and `scripts/listener.sh <port>`
     confirms the listener is this worktree's: it prints the pid, `cwd` and node `bin`
     checkout, and `bin` wins (Eve's chdir pointed a server at main, CEL-119). Another
     checkout's listener is never stopped: take a free port (CEL-120 stopped a sibling's).
  5. Load each surface the feature touches once in chrome-devtools: it renders, its first
     step works, the console is clean. Then `smoke: branch` once. Not a walk-through.
  6. A feature that makes model calls counts the canned or fallback lines in the dev log: a
     nonzero count is a defect. A check that falls back quietly is proven answering twice: one
     case where it should fire, and one direct call printing the raw reply. A 401 or a
     missing key means localhost can't run that flow: walk it on a preview, and write that
     into the repo's checks skill.
  7. UI files: `~/.claude/skills/impeccable/scripts/impeccable detect --no-advisory <files>`
     (0 clean, 2 findings, 1 unreadable): fix each, or waive a deliberate one in place with
     `impeccable-disable-line <rule> -- <why>`. Every web surface:
     `scripts/icon-check.py <url>...`: it needs a browser icon and a 180px PNG Home Screen
     icon, since Pete opens apps from his phone (Pete, 2026-10-14). A missing one is made
     before landing in the app's own colors, the mark through impeccable as SVG and the PNG
     rendered by `chrome-headless-shell --headless --screenshot=<png> --window-size=180,180
     --default-background-color=00000000 file://<svg>` (Next: `app/icon.svg`,
     `app/apple-icon.png`).
  You find the breakage, never Pete.
- **A genuine fork mid-BUILD** (his answer would change what gets built) is a stop:
  `stage.sh <root> gate:input`, `needs input:` PM-framed with a pick, and keep building what
  it doesn't hold. Taste or direction promotes instead (Verbs and sizing).

### 4 · REVIEW — two readers, then triage  → marker: `review`

SELF-DIRECTED and GATED. EXPRESS runs only the sync with main below, then TEST, with its one
Wonder read where Sizing says.

- `stage.sh <root> review`. **Sync with main**: `git fetch origin`, absorb in the worktree
  in a call of its own (rebase, or merge if unsafe) and see it clean; rerun the repo's install
  when the absorb changed a lockfile or the workspace list; on `copy`, push absorbed Convex
  changes to the copy with `npx convex dev --once` in each app-dir (muse-core-loops hit a
  function its copy lacked); on `per-branch`, rare-cases' re-deploy. **When the absorb
  changed the tree, the full gates run now, before either reader starts**, since a gate that
  builds rewrites tracked files under Muse's read. An absorb that touched the repo's
  `CLAUDE.md` / `AGENTS.md` can change the contract: reread it. Review against a stale fork
  reviews other ships' work as reversions.
- **Start TEST's dev server now** (TEST: Keep it running), before either reader starts.
- **Both readers read the branch at once, from `reference/branch-review-brief.md`** filled
  and written to a file first, so a reader that dies is respawned from it: the Opus subagent
  (`model: "opus"`), launched first, and Wonder (`muse.py review`, background). Both briefs
  name the HEAD sha; neither sees the other's findings; no fix is committed until both are
  back (card-quality-rank committed Wonder's fixes mid-read, and Opus reported its top
  finding as already fixed). Muse out: the stand-in reads Wonder's brief.
- **Triage every finding from both.** Adversarial readers over-flag by design, and one both
  reached alone is the strongest lead, never proof. Check each against the code. A review
  makes the branch correct, not bigger (Pete, 2026-11-01): decline a nit (style, naming, a
  comment that isn't wrong) and anything the spec doesn't ask for, unless it's security,
  money or data loss. Judgment calls go on the card or in `result:`.
- **`git status` before the first fix**: dirt means a reader edited the tree, which nothing
  stops a subagent doing; its edits are thrown away, never committed (incidents: Dispatch).
- **Write the triage to `<job tmp>/triage-<slug>.md` before the first fix**: one line per
  finding, its reader, what it says, real, false or nit, and fixed or declined with why. It
  outlives a compaction, and the ledger rows and the PR's Reviewed line come from it
  (screendrop-worker rebuilt one from the transcript). Then one row per reader: `route.py log
  repo= ship= review=opus stage=branch real= false= only= nits= seconds=` and the same for
  `review=wonder` with `out=<out-dir>` in place of `seconds=`, where `only` counts real
  findings the other missed. Muse out: `review=wonder stage=branch note=out:<exit>`, plus the
  stand-in's own `review=opus … note=for:wonder` row.
- **Fix what's real**, each fix run against the cases the issue or spec names before it's
  committed (two readers' fixes added up to a guard that undid eca-finder's loose deck), with
  the gates scoped through `route.py gate`. A fix that rebuilds the rule a finding was
  about, a rule a later read still finds new cases in, or a read still out when TEST
  starts: incidents, Design & review.
- **A text transform or a row filter runs over the real corpus, on every lane.** A change to
  anything that rewrites text (a name cleaner, a parser, a formatter) runs over all the dev
  data it will see, and the driver reads the before-and-after diff (eca-finder's cleaner
  passed review and tests, then mangled four of 9,373 names). A filter's diff is what its
  consumer returns before and after, and a loosened one also meets made-up inputs it must
  still refuse.

### 5 · TEST — ship uses it as Pete would  → marker: `test`

- **Push**, so the preview QA walks carries REVIEW's absorb and fixes (with a per-push
  `preview:`, wait for its build), then `stage.sh <root> test`. **Freeze upstream while the QA
  run walks**: absorb before a run, never during; the run's own fixes are the only edits.
- **Keep it running, for the QA run and for Pete.** Two surfaces: the branch's preview links
  (`preview:`) and the worktree's localhost (`dev:`). Boot the dev server detached from the
  worktree root by absolute path (`cd <worktree> &&` first: one in `packs/homebody` started
  the wrong app), output to a file, never through a bounded pipe (`| head -50` SIGPIPE'd a
  server mid-walk); wait with `scripts/listener.sh <port>`, load the URL once with the sandbox
  off, then `show.sh <root> <slug> test <url>` (`preview` for a preview link). An auth-gated
  feature needs its test-auth path working on both (incidents: Backends). Never run a
  production deploy for him to look, never send him to the live site.
- **Check the wiring first.** Run `stack:` (a ✗ is yours). A change that removes or renames a
  backend function or table lands in two passes, first the app stops using it, then it goes,
  since landing ships the backend before the app. Any persisted schema an older process still
  writes (a local database file included) changes additively first, or Merge Danger calls it
  one-way.
- **The QA run: call the Skill tool with `ship:verify`**, the full name (bare `verify` is
  another skill and is refused), an API-only change included. It loads from the copy this
  session started on, whatever was installed since (cel-306 followed 8f5738a's verify while
  calling 839a52's scripts): when its printed base directory is not under the `installPath`
  that `~/.claude/plugins/installed_plugins.json` names for `ship@ship`, run
  `<installPath>/skills/pipeline/scripts/what-changed.sh <the base directory cut before
  /skills> <installPath>` and read
  what it lists under `verify/`, which wins; nothing listed there means verify is unchanged.
  Hand it the worktree's path,
  the URL, the BACKEND, test-auth, IOS and STORYBOARD lines, the plan's `## QA cases` (or on
  EXPRESS the change's intent), and the repo's checks skill (`.claude/skills/checks/SKILL.md`,
  or "none yet: write it"), and the `<out-dir>` and launch directory verify names at its top;
  it writes qa.md,
  walks the surface Pete would open the way he would, with real clicks and keys, fixes what
  fails, reruns, up to three fix rounds on one step (a new bug each round is progress, and
  `result:` gives the count), and writes back what it learned. A
  protected preview, a print or copy flow and a terminal UI are its `reference/browser.md`; a
  phone, simulator or mobile web its `reference/ios.md`, where a locked phone falls back to a
  simulator unless the change needs the phone itself; a Mac app its `reference/mac.md`, in a
  borrowed VM, never desktop control of Pete's Mac.
- **Design against the storyboard is the QA run's to judge**: a step per frame the change
  built and the craft floor, and a gap is a failure.
- **What no person can walk is proven at data level**: a race, a background worker, a third
  party mid-call; records that cost money or that test-auth can't seed; a walk the brief
  forbids. The product's own functions over real records on the branch's backend, then a
  browser check of each screen that reads the result, is `works`, not partial, and the card
  says which steps went that way. A screen reachable only by seeding model output passes on a
  render test of the real component with the result's real shape. A prompt change is proven
  by replay: the same saved inputs through main's prompt and the branch's, a few times each,
  both quoted (CEL-170); an empty reply or a fallback is a failed run.
- **`works`: write the PR body, then land.** Call the Skill tool with `mattpocock-skills:pr`
  and rewrite the tracker PR in its shape: Summary, Evidence (the QA result and its shots, the
  test that went green), Merge Danger, and a last line per reader, `Reviewed: Wonder Full <n>
  fixed, <n> declined, <n> wrong · Opus …`, with each declined finding and why in a collapsed
  list, all from the triage file. Every number anywhere comes from recorded output, rechecked
  before posting and after a compaction. An image on the branch links by commit
  (`blob/<sha>/<path>?raw=true`). The door is ship's call: **two-way** (a revert undoes it)
  lands now; **one-way** (it deletes or migrates data, sends something to people, or a revert
  can't undo it) waits for "merge main", as do a money path and a change he said he'd try
  first: `stage.sh <root> gate:test`, the card, `needs input:`. On `land: auto` only a money
  path waits.
- **`broken` after three rounds on one step, or `unverifiable`: park.** `stage.sh <root>
  gate:input`, hand Pete the result and evidence, and end with `needs input:` ("test:
  <feature>: couldn't prove <step>: <reason>"). Partial is `unverifiable`, never a footnote
  on a landing: three ships went to Pete with a known gap and he found it in minutes.
- **The review card**, SELF-DIRECTED and GATED, on a pass or a park: `reference/
  review-card.html`, whose comment says where it goes, what each slot holds, and that it is
  committed before the merge with the shots it shows. `LANDING_STATUS` says "Tested · landing
  on main" or what it waits on. EXPRESS has none; its `result:` names the proof shots.
- **Screenshots** live in verify's `<shots-root>/.ship-shots/<slug>/` (its `SHOTS:`), never
  committed; any brief that screenshots or hands the browser a file (an `evaluate_script`
  `sourcePath`, a sign-in script; recon's walk of the live product included) gets that
  absolute path written in, or before verify has run, verify's probe (Two paths), since the
  browser reads and writes only inside its workspace roots.
  Copy what the card shows beside the card before teardown, then delete that folder after
  landing, unless the ship is EXPRESS, whose `result:` names them (moved to the main
  checkout's `.ship-shots/<slug>/` before teardown when the shots root was the worktree). A shots root in
  another repo gets the exclude with `scripts/stage.sh <shots-root> exclude`.
- **While parked**, keep the dev server up. A change Pete asks for goes through
  `superpowers:receiving-code-review` (verify the ask against the code), BUILD's push and
  links, and the QA run, and lands on its pass unless a stop still holds. A change he asks for
  after landing is a new EXPRESS ship.

### 6 · LAND — on the QA pass, or Pete's word  → marker: `land`, then removed

Mechanics only: nothing is reviewed here. The checks and the merge run in the worktree, so a
refusal leaves a tree to fix in; the main checkout comes after. A `land:` other than `pr`, a
repo's own land script, a session launched inside its worktree, a worktree ship didn't make,
or no GitHub remote: `reference/rare-cases.md`, Landing variants.

1. **In the worktree, make it landable.**
   - Release what the run started from inside it: a QA-run directory's own teardown, its
     containers, a simulator it cloned, a borrowed VM slot. Delete test data the run kept,
     the way the checks skill says, while the server still answers: `scripts/listener.sh
     <port> 1` naming this worktree, then one request. A reboot or a stop during a park takes
     it (company-pack's Mac rebooted mid-park), so start it again on the app the walk used
     first (Clerk's test instance caps at 100 people; cells-app: each walk person by `DELETE
     /api/account` as them, the checks skill's recipe, since `npm run prune -- --people
     --finish` waits on every other landing's lock: cel-297 stalled behind #442's).
   - `stage.sh <root> land`, `git fetch origin`; if main moved, absorb it in a call of its own
     and see it merged clean before any gate (CEL-140 gated a half-merged tree). An absorb
     whose files (`git diff --name-only HEAD...origin/main` after the fetch and before the
     absorb, one plain call, right for a merge or a rebase) overlap what the QA run walked or measured reruns those steps on the merged
     tree (the server restarted on it, or a preview's new build); an overlap of only tests,
     or imports that still name the same code, keeps the pass, and the PR says so.
   - The full gates once, if the tree changed since their last full run, with the dev server
     stopped and any simulator shut. `smoke: branch` once, if the diff since its last result
     touches what the app carries (anything but docs, tests, the review card and its shots,
     or the repo's own skip rule), with the server back up on the app the smoke drives and
     its links and keys copied back from the main checkout where a QA of another app left its
     own (ttowns-civic-feed's Blob 403s); a new smoke of code the last one never saw is not a
     rerun.
   - **Every env name the diff newly reads exists where landing deploys**, by name: `wrangler
     secret list`, `vercel env ls production`, `npx convex env list --prod`. Names only,
     never values. A missing one parks (`stage.sh <root> gate:input`, `needs input:` naming
     it): a production setting is Pete's (screendrop-worker's OWNER_SUB, 2026-11-05).
   - On a design ship, from the worktree, `route.py log repo= ship= <what decisions.py tally
     <slug> prints>`: `used` counts decisions that changed what the ship did (a question not
     asked, a choice made their way, a reversal said out loud). Tally's exit 1 means no recall
     ran, so no row; route.py refuses a second one, as a return to step 1 would log.
   - Commit the smoke's result line with the review card and its shots (`git restore
     next-env.d.ts` first), and bring the PR body up to date with what shipped (the squash
     takes it). `stack:` once more. For each other open PR, `git cherry HEAD origin/<branch>
     origin/main` (a script file) prints `-` for its commits this branch carries: a hit lands
     after that PR.
   - Stop the worktree's dev server with the repo's stop command, from the worktree; then
     `listener.sh <port> 1` must find nothing (one still there stops by its process group).
   - `route.py readers repo=<r> ship=<slug>` exits 0 (SELF-DIRECTED and GATED): both branch
     readers logged and the review card committed. Push.
2. **GitHub agrees.** `gh pr ready <#> -R <o/r>`; `gh pr view <#> -R <o/r> --json mergeable`
   says `MERGEABLE`; `gh pr checks <#> -R <o/r>`: no checks reported means the local gates
   stand, pending waits (`--watch`), red is fixed in the worktree and back to step 1. These
   and the merge spend GitHub's GraphQL budget, which sibling ships exhaust while `gh api
   rate_limit` still shows budget: the REST forms are in incidents: GitHub.
3. **Merge**: `gh pr merge <#> -R <o/r> --squash`, from the worktree, without
   `--delete-branch`, so nothing local runs and a refusal leaves the tree.
4. **Leave the worktree**: `ExitWorktree({action:"keep"})`. Every command after names the
   main checkout (`git -C <main>`, `wt -C <main>`): the shell can still sit in the worktree
   or a removed folder (CEL-233, CEL-217). `wt -C <main> remove feature/<slug> -f`, then
   `rm -rf <worktree>` once `git worktree list` no longer shows it (the harness's
   `.claude/.cc-writes` keeps the folder alive); if the harness refuses because it is the
   session's own folder, leave it to `wt-sweep`. If `ExitWorktree` answers that no session is
   active, `cd <main checkout>` after this step, so the next ship's `EnterWorktree` takes.
5. **Tidy the branch and main**: `git -C <main> push origin --delete feature/<slug>` (a
   "remote ref does not exist" means the repo already deleted it); `git -C <main> pull
   --ff-only`, and `git -C <main> branch -D feature/<slug>` if it lingers (a squash rewrites
   the commits, so git calls it unmerged). A dirty main checkout holds another session's
   work: skip the pull. When the guard still refuses git against main, leave the pull to the
   next session there and say so in `result:`. Then `rm -f <worktree>/.ship-stage
   <worktree>/.ship-route.json ~/.claude/ship-active/$CLAUDE_CODE_SESSION_ID` where they
   remain, deprovision a per-branch backend, remove a native branch app (rare-cases), and
   check `git worktree list`: zero ship-made worktrees remain, or teardown failed and is
   recovered before `result:`.
6. **Watch the deploy.** `deploy:` runs now, once, from the main checkout once step 5 pulled
   it, else from a throwaway worktree pinned to `origin/main` (`git -C <main> worktree add
   --detach <job tmp>/deploy origin/main` after a fetch, removed after), never from a main
   that missed the merge; when neither can run, `result:` says the deploy is still owed.
   Then what `live:`
   names, to READY or ERROR, and each live URL loaded once (`curl -sS -o /dev/null -w
   '%{http_code}'` and the page's text): READY with a 404 or the host's "not found" page is a
   failed deploy. Watch rules (incidents: Backends):
   - Wait on a Vercel build with `vercel inspect <url> --wait --timeout <t>`; find a merge's
     build with `vercel ls -m githubCommitSha=<full sha>`, into a file in the job's tmp, never
     `| head`. A CLI `--prod` deploy where git also builds main starts a second production
     build that ends up live: watch it too. Take Convex MCP selectors from the main checkout.
     A GitHub Actions deploy: watch the run for your commit, `gh run list -R <o/r> --commit
     <full sha>` (`git -C <main> rev-parse <sha>` in its own call; a short sha matches
     nothing and the watch times out silently).
   - Every wait has a deadline and a never-started check: no deployment for the sha within
     about 3 minutes means look at the host's ignore step. A diff `live:` doesn't build
     deploys nothing: say so, and never run a deploy for it, which would ship main's other
     unreleased commits.
   - **A failed build** leaves the old one live: fix forward on a new EXPRESS branch.
     **Live but broken** (a 404, a red `smoke: main`): revert first, a `revert/<slug>`
     worktree off main with `git revert <squash sha>`, its gates, the live load and a squash
     merge; then fix forward on a new ship. Tell Pete in one line what broke and which ships
     landed since the last green.
   - `smoke: main` once, after the watch (one rerun on a third party's network error); none after a land
     script that ran it. Restart a `worker:` once idle (rare-cases). Ship never runs a
     production deploy or pushes a production database by hand, and never makes Pete run
     one; an integration lane or a promotion is rare-cases.
7. **Close out.** On a design ship, the retro carries step 1's recall count. `show.sh …
   review <file> done` the landed card.
   Run RETRO, then end with `result:`: what shipped, one sentence, the live links, `· retro
   sent` when it was, then the follow-ups. Only a landing earns `result:`.

### 7 · RETRO — what the run teaches  → no marker

**Ship gets a retro.** The running agent never edits this skill; the fix belongs to the
maintainer, the session named `ship` in this plugin's repo (Pete, 2026-10-05). Look back
from the transcript, not memory, at how you used ship: a rule that was unclear, contradicted
another, changed nothing or that you broke, and every time Pete stepped in where ship should
have carried on (steering); a mistake one of ship's scripts could have caught, or a check
that misfired; something ship never handed you or the QA run that cost a round; a rule found
too late; a step a script or narrower command would make cheaper. `ListAgents`, then
`SendMessage` the peer named `ship` (never yourself): `ship retro from <repo>/<slug>:` and
each finding as one line with what happened, the gap, the fix you'd make and its evidence (a
file:line, a turn, a QA step). A clean run sends `…: clean`. Fire and forget. No `ship`
session live: write the same text to `~/.claude/ship-retro/<date>-<repo>-<slug>.md`. Never
invent a lesson. The maintainer files a one-run lesson in `reference/incidents.md`; a second
run hitting it earns a line here.

**The repo gets a retro too**: a mistake one of its checks could have caught (a lint rule, a
type, a test, a CI job; a mechanical rule gets a check, never a standards line), information
the run lacked (a log nobody tailed), a file it took long to find that a pointer in its
`CLAUDE.md` would have saved, an expensive call a script would replace. A repo with no
tests, lint or CI at all is one. Each real one is a follow-up. A gap an earlier run already listed is not news.

**Follow-ups** are work outside the spec's scope the run threw off, never a specced surface
left unbuilt. Keep a running list, never invent one, never gate the merge on it. Each gets
one plain line on why it's worth doing, and a kind:
- **Quick ship**: the whole change visible, no taste call, one sitting. Pete says "ship <n>"
  and it runs as EXPRESS.
- **Ticket**, in the column the repo's `board:` gives its need (cells-app: Ready for an agent
  to build alone, Backlog with the ask written on it for Pete's OK or a design call, Icebox
  for someday), never a column for work in flight. Pete says "file them" (or names which) and
  each lands with its why and a link to this PR, and any measurement it rests on pasted or at
  a durable path.

They go on the review card under "What we should do next", or under `result:` as a numbered
list. Ship fixes found in its own retro go to the maintainer, never this list. Don't gate
`result:` on any of it.

## Every stop

A stop is a hard stop: show the page, write the marker, end the turn with `needs input:`,
and keep doing work the stop doesn't hold. Nothing else stops a ship. Once Pete answers,
write the stage back (`stage.sh <root> plan`, `test`, `land`; mid-BUILD `build:<n>:<m>`, n
the tasks in `.ship-done`), since a stop's marker counts as waiting on him until it moves.

| Stop | Marker | Pete sees | He says |
|---|---|---|---|
| Storyboard round (GATED) | `gate:1` | ✋ storyboard? and the page | reactions, or "lock it" |
| Plan card with a call | `gate:2` | ✋ go? and the card | "go", or the call |
| A step only his login can do, a thing only he can create, or a genuine fork mid-BUILD | `gate:input` | the exact step, or the fork and ship's pick | "done", or the pick |
| Money path, any repo, `land: auto` included | `gate:test` | ✋ try it, then merge main? | "merge main" |
| One-way door (not on `land: auto`) | `gate:test` | ✋ try it, then merge main? | "merge main" |
| A change he said he'd try or see first, a copy change included (not on `land: auto`) | `gate:test` | ✋ try it, then merge main? | "merge main" |
| QA couldn't prove a step, a missing production setting | `gate:input` | the step and why | do it, or "land anyway" |

"Merge main" takes the worktree all the way: merge, deploy, teardown. The same intent in
other words counts ("ship it", "just merge"); "looks good" does not land. "Land anyway" on an
unproven ship, or "merge main" there, lands it with the unwalked steps named in `result:`. A locked phone stops
nothing: the simulator walks it unless the change needs the phone itself.

**How a stop reaches him**: the status line shows the marker in amber (`✋ <slug> — needs
you` for `gate:input`) and counts the ships waiting and the oldest wait; the `needs input:`
line moves the FleetView row to awaiting input; the gate hook fires a desktop notification;
and the mod in `hooks/register.ts` draws buttons a bare digit presses (`1` raises the page
`show.sh` last opened for the stop, `2` sends "lock it" or "go"), read from `.ship-stage` and
`.ship-shown/`, so a run writes no button text.
