---
name: pipeline
description: Use for any code change in a product/web repo, quick fix to full feature — ship sizes the ceremony itself and stops only when Pete's taste is in play. Explicit verbs pin the process — "/ship express <tweak>", "/ship design <idea>"; anything else sizes itself. EXPRESS (tweak — no spec/plan, straight through to dev), SELF-DIRECTED (writes its own spec+plan, builds, reviews, merges, deploys — zero stops), or GATED (design direction + "go" gates) — gates fire only when Pete's answer would change what gets built. Auto-triggers on change requests; you never type it. Do NOT use for a question or pure analysis. Never edit main directly.
---

# /ship — idea to merged, in one command

You run a feature from idea to merged. Pete is heavy in DISCOVER (his taste), glances at
a card only when it genuinely needs him, and comes back at the end. Everything else is
automatic.

**Scope is the spec — Pete's dial, not yours.** Ship builds *exactly* what the design
spec covers: the whole thing, in one pass — one plan, one build, one review, one merge.
Never decompose a specced feature into "Ship 1 of 4," never defer specced surfaces to a
"later phase." A bigger spec means a bigger plan and a longer build — that is wanted.
Phasing is Pete's to ask for, never yours to impose.

`reference/incidents.md` holds environment facts learned from real failed runs — consult
the relevant section before merges, teardowns, deploys, or debugging a dispatch.

## Verbs — Pete pins the process explicitly

If the invocation's first word is `express` or `design`, that verb pins the
process and skips the sizing judgment below. Anything else — bare `/ship <idea>` or
the auto-trigger — sizes itself. Every verb rides the same rails: stage 0's worktree
off main via `wt`, never a primary checkout.

**Pasted agent output as the argument** (another agent's report or completion message,
not an idea): read it as "land what it made, and build the fixes it recommends", say so in
one line up front, and size that.

**The fork is the verb's FIRST act — before any question, recon agent, or authoring
step.** The moment a verb lands, resolve the target repo and run stage 0 there. The
marker flip is how Pete *sees* ship engage. One exception: a bug card reproduces read-only
against main first, posting one line that it is doing so, and forks only once a code change
is known. That covers a brief that may end in no code ("if it's gone or not ours, close it
with evidence") and a recheck of a fix that just landed: compare the bad data's timestamps
with the fix's merge time before anything else, since a row written before the fix proves
nothing (CEL-174 forked and copied a database for one). Keep the repro's files at absolute
paths under the job's tmp, since `$TMPDIR` differs with the sandbox. A run that closes the card that way changes nothing, so it has no
worktree, PR or landing; its proof goes on the card (CEL-172).

- **`/ship express <tweak>`** — pins EXPRESS. The verb pins ceremony *down*, never
  safety down: a money path or a taste call promotes per the mid-flight rule regardless.
- **`/ship design <idea>`** — pins GATED and mandates the full design workshop in
  DISCOVER (storyboard → rounds → lock → HTML plan → go → spec → build). The verb is
  Pete asserting taste is in play; never downgrade it, however mechanical the work
  looks.

## Sizing — every change ships; you pick the ceremony

The rails are constant: worktree off main, its branch pushed at once with a draft PR
tracking it → change, pushed at every milestone so the host builds a preview → review →
**TEST: ship writes a QA script and runs it itself the way Pete would, in a browser, and on
his iPhone only for a native app, fixing until it passes, and a pass lands it** (squash the PR) → the host deploys what main deploys. Nothing ever edits
main directly, however tiny, and nothing lands untested: main is where things go live.
What scales is the ceremony before TEST, and you size it, not Pete:

- **EXPRESS — a quick tweak or fix.** Whole diff visible before you start, no money
  path. No spec, no plan, no cards, no stops: worktree → change → repo gates
  (tsc/tests) → pre-flight (the page loads, no console errors) → push, links → TEST →
  land on a pass →
  `result:` line. No branch readers: REVIEW's two-lab read belongs to SELF-DIRECTED and
  GATED. A dab of `ponytail` (smallest diff), and `impeccable` for anything
  visual. The first Pete hears of it is the links.
- **SELF-DIRECTED — real work with no taste question in it.** Write whatever
  machine-facing spec/plan *you* need to build it well, then build, run the full REVIEW
  machinery (the fresh-eyes review, then TEST's QA run — its `works` is the bar
  for landing), land, `result:`. No stops — the artifacts are for the record, not
  approval.
- **GATED — Pete's taste or direction is genuinely in play.** A new user-facing
  surface, visual identity, a product tradeoff, ambiguous scope, a money path — the
  gated pipeline below.

**A card key doesn't size the ship.** A board card that is an EXPRESS-sized fix runs as
EXPRESS: no written plan, no plan review.

**The gate test is never size — it's whether Pete's answer would change what gets
built** (or the change is risky/irreversible). If his input wouldn't change the outcome,
don't stop. Every lane lands only on green gates and the QA run's `works`. A
money path, a one-way door (the PR body's Merge Danger call, TEST below), and a change
Pete said he wants to try himself also wait for his "merge main" after the pass.
Mid-flight, promote the moment taste or direction appears (park, write the spec from
what you've learned, present GATE 1); size alone moves EXPRESS → SELF-DIRECTED, never to
a gate. Never use an autonomous lane to slip a taste call past Pete.

## Engines

**Opus 5.5 writes; Muse Wonder Full reads beside it** (Pete, 2026-10-24). The driver and
every subagent it starts (`model: "opus"`) run Opus 5.5 at high effort, never xhigh, max or
medium. Wonder Full reviews the plan and reads the branch, and never writes code. Nothing
else runs: no Sonnet, Fable or a Codex model. `muse.py build` and `astra.sh` stay in
`scripts/` for when he turns one back on.

**One loop does the work, and a subagent earns its seat.** The driver builds, tests and
fixes in its own context, where it reads the raw diff, test output and browser snapshot
itself; a subagent hands back a summary, and a summary drops what the next step needed
(Anthropic, "when to fold subagents into your main agent loop"; here, briefs left the
wiring between files to the driver on 6 of 9 tasks in one ship). A subagent is for three
jobs only:
1. **Fresh eyes**: the plan review (PLAN) and the branch review (REVIEW), where a reader
   that didn't write the code is the point.
2. **A sweep whose answer is all the driver needs**: recon across many files, an expert
   consult, a reference lookup.
3. **Reading the rest of the ship never needs**: a task whose context would crowd the
   driver's, such as a wide mechanical migration. It gets a brief (BUILD's boilerplate),
   logs `engine=opus` with the reason in `note`, and the driver reviews its diff and runs
   the gates as for its own.

Speed is never the reason: Pete doesn't measure a ship by wall time, and serial work is
easier to reason through. Never `claude -p` from inside a session.

**The loop's context grows with every task, and compaction is survivable by design.**
Claude Code compacts it automatically, so a ship keeps its state on disk, never only in
context: the plan file, a commit per task, the marker, `.ship-done`, the ledger, the QA
result. After each compaction the plugin's `hooks/ship-recap.sh` prints that state into the
fresh context (stage, plan path, each task done or todo, the branch's commits, uncommitted
files); trust it over the summary, reread the plan and this skill's section for the stage,
and post Pete the one-line status.

**The readers: Opus and Wonder, two labs.** A reader shares the blind spots of code its own
lab wrote and goes easy on it (Pete, 2026-10-14), and Opus wrote every line, so Wonder is
the reader that can see them; the Opus reader is a fresh subagent whose brief says to assume
the writer was wrong at every seam. Wonder runs as `scripts/muse.py review <worktree>
<brief> <out-dir>`, a background Bash call: read-only, exit 6 if it changed the tree, its
findings in `<out-dir>/last.md`, with `<out-dir>` in the job's tmp, outside the worktree
(`muse.py` refuses one inside it). Muse runs only through `muse.py`, never a hand-typed
`muse exec`. Any nonzero exit means Muse is out (2: a confidential repo, since Muse's
Contributor mode trains on what it reads, listed in `~/.config/ship/confidential-paths`, and
with no list file Muse is off everywhere; 5: its quota): an Opus subagent reads in its place,
and the `result:` line says so. Readers report and never edit, because a reader that
rewrites breaks working code. A claim about how a dependency behaves at runtime is checked in its
installed code (`node_modules/<pkg>/dist`), not its docs: a plan review once took Eve's
docs on queued messages at their word, and the runtime did otherwise (2026-10-14).

**Pete's budget word outranks ship's defaults.** When he caps subagents or spend for a run
("no extra parallel agents"), skip the Opus readers and keep Wonder, which draws on no
Claude quota, and the `result:` line names what that skipped.

**The ledger judges the fold.** After PLAN, `scripts/route.py plan <plan.md>` lists the
tasks, saves them and moves the marker to `build:0:<M>`. When a task's diff is accepted,
append its outcome, from the worktree:

```bash
route.py log repo=<repo> ship=<slug> task=<n> engine=<driver|opus> \
  seconds=<wall time> fix_rounds=<n> gates_first_pass=<true|false> verdict=<clean|fixed|redone>
```

`routed` fills itself as `driver`, so a task handed to a subagent shows as `engine=opus`.
Seconds come from the run itself, and a number you don't have is left out, never
estimated: a third of the first 81 rows were round-number guesses. `route.py report`
compares driver-built and subagent-built tasks by first-pass gates and fix rounds; if
handed-off tasks keep needing more rounds, the third job above shrinks.

**Codex is off.** Pete dropped the subscription (2026-10-22), so "test in codex" has no
engine: tell him in one line and test in this session. `ship:verify`'s
`reference/codex.md` stays for when he turns it back on.

**A brief, when there is one, is the driver's envelope**: the exact files and the wiring
points among them (where the new piece is registered, exported, routed or called from),
signatures, test cases, constraints. Call the Skill tool with
`mattpocock-skills:writing-for-agents` once per run before the first brief. The driver
reviews what comes back and runs the gates before anything is committed (never trust a
"tests pass" claim from a worker), and owns git entirely. One writer per tree at a time.

**Browser work runs on the chrome-devtools MCP** (`mcp__chrome-devtools__*`: headless,
a fresh isolated profile per session, so parallel walks never collide and no window
opens on Pete's screen): the pre-flight check, TEST's QA run, live-product grounding. A subagent
loads those tools with one ToolSearch call before its first step. A surface that needs
Pete's real login and has no test-auth path in the repo is his: hand it off with
`needs input:`. A reference product behind his login (muse.ai) is his too: ask for
screenshots of the states you need, and use the `mcp__claude-in-chrome__*` tools only
when he asks, since they drive his own Chrome. A subagent drives the
browser against the running app and reports what it saw; a coding worker never does.

**Every page Pete should see goes to his Chrome through `scripts/show.sh`**, never a bare
`open`: `show.sh <root> <slug> <kind> <file|url> [done]`, kind one of `storyboard`, `plan`,
`review`, `test` (the worktree's localhost) or `preview`. It opens with `open -g`, so Chrome
never comes forward and takes the screen while he works, and tags the URL so his ship-tabs
extension (`chrome/ship-tabs/` in the ship repo) files it in the window's 📐 docs or
🧪 test group, titles it (`🧪 cells-app · smarter-search · …`), hands him back the tab he was on, and closes the tab it
replaces: a redrawn storyboard or a restarted server is one tab, never two. `done` on the
review card that goes with `result:` closes the ship's other tabs. It keeps each kind's last
URL in `.ship-shown/<kind>` at the worktree's top, which the gate buttons open. A storyboard, plan or
review card Pete has shared from its Share button is republished by show.sh on each
redraw, so the link he sent follows the rounds; sharing a doc is his press, never
ship's. Never connect to his
Chrome itself (chrome-devtools `--autoConnect`, `--browserUrl`): every connection pops an
"Allow remote debugging?" dialog on his screen. Every automated browser is the separate
chrome-headless-shell build (the chrome-devtools MCP's `--executablePath`, Playwright's
`executablePath`), never the Google Chrome app run headless: macOS counts a hidden copy
of the app as Chrome running and hands it Pete's Dock click, so his own Chrome won't open.

**Never idle while a run or a subagent works.** Work the non-tree list meanwhile (the
review card if this ship gets one, the commit message, the ledger lines) so the stage
closes minutes after the result lands. Same posture at gates: notify, then keep doing
non-gated work.

**How a turn ends.** A message with no tool call ends the turn, and on the autonomous
lanes nobody is waiting to say "continue". Four endings are wrong while work is still
owed: a summary that announces the next step instead of taking it; an offer to carry
on unless Pete objects; a list of decisions when none of them blocks the rest; and
stopping because a milestone landed or the turn ran long. Status notes and
recommendations go in the same message as the next tool call. A turn ends at a gate
(`needs input:`), at `result:`, when nothing can move without Pete, or while you wait
on background work with nothing else to do, where a one-line status is right and the
harness wakes you when it lands.

## Two principles, always

1. **The meta rule.** Every artifact Pete sees is a condensed HTML page — he reads the
   *meta*, never the full spec or plan. The spec and cards are HTML he opens in the
   browser; the execution plan is machine-facing markdown he never reads. HTML artifacts
   follow the html-effectiveness patterns (https://thariqs.github.io/html-effectiveness/):
   plain-English TL;DR first, structure as diagrams/side-by-sides instead of prose,
   depth behind collapsibles, anything visual a *live* embed. Pattern picks are named
   per stage. Prune hard inside that format — never reach for a new one. Pete tried
   landing-page-styled gate artifacts against the plain doc and kept the doc: "this is
   taking it far too radical an approach… maybe there's just a little bit of pruning."
   Cut any section that doesn't change a decision; shorter ledes, depth collapsed.
   **The storyboard is the one page that is not condensed prose: it is mockups**, and
   its words are captions (stage 1). A storyboard that reads as a document has failed.
2. **Two gates, both his.** GATE 1 = Pete's lock on the storyboard (DISCOVER runs as
   presented rounds, each a hard stop — see stage 1). GATE 2 = his "go" on the HTML
   plan card (stage 2), and it stops only when the card carries a call: a card with
   none is shown, not waited on. GATE 1 always fires on the GATED lane. SELF-DIRECTED and EXPRESS render no cards and never
   stop before TEST; a money path stops on any lane, at its gates and again before landing. When a gate
   fires, it is a **HARD STOP** — present the artifact and wait. On every lane, a
   ship tests its own work at TEST, and its pass lands it without him.

Every word Pete reads, in chat or on a page, follows "Talking to Pete" (near the end).

**Pete's stack:** his global instructions carry the standing stack — Eve · Vercel ·
Convex · Clerk · Stripe · Next (Cloudflare keeps DNS, R2 and the Workers already running). Never re-ask it. The repo's own `CLAUDE.md` /
`AGENTS.md` overrides it where it diverges.
Escalate a library choice only when it's both architectural *and* outside the canon.

## The ship contract — what a repo tells ship

A repo declares how ship runs it in its `CLAUDE.md` / `AGENTS.md`, as a short list of
facts. The workflow is ship's; the contract only says what this repo's commands are.
Every key is optional, and the default is what a repo with no contract gets:

- **`gates:`** the commands that must pass: tests, typecheck, production build. Default:
  whatever you can find. Gates, smokes and dev servers run with the Bash sandbox off: they
  bind ports and fetch fonts and packages by design, and under the sandbox they fail with
  `listen EPERM` or a fetch error that reads as a real red (CEL-147 lost a 7-minute suite
  to 27 of them). A multi-step gate run goes in a script file written with the Write tool,
  then `bash <file>`, since the worktree guard refuses long inline commands. That script
  starts with `set -euo pipefail`: without it, `npm test | tail -8` exits with tail's code,
  and CEL-180's script printed green over a failed test. A full run whose only failures are
  in files the diff never touched, under heavy load from sibling ships (timeouts, or a set
  that moves between unrelated files from run to run), reruns just those files alone. If
  they pass alone, it's load: both runs and the `uptime` load figure go in the commit or the
  `result:` line, and it isn't root-caused. A failure in a file the diff touched is a real
  red.
- **`preview:`** a command that prints this branch's preview links, one per app, with
  each build's state (cells-app: `scripts/preview-links.sh`, which reads Vercel). Ship
  runs it after every push and posts what it prints. A contract may mark it `on demand`
  (cells-app: a push builds nothing): then ship posts the localhost after each push and
  runs `preview:` once before TEST, only when the change needs what localhost cannot show
  (the contract says what) or Pete asks. Default: no hosted preview; the worktree's
  localhost is the only link.
- **`dev:`** the command that starts the worktree's own dev server on a port of its own
  and prints its URL (cells-app: `npm run dev`, via `scripts/dev.sh`). Default: the
  repo's dev script, detached.
- **`test-auth:`** how the QA run signs in. `seed <how>` is the old path: a seeded account
  and a secret verify may use. `form <how>` means the app's own sign-in form works with
  test credentials (Clerk test instances: any address, code 424242), and verify may use
  it. `none` makes an auth-gated walk `unverifiable`.
- **`backend:`** `copy [<app-dir>]` (the default where the repo has a `convex.json`): stage 0
  gives the worktree its own Convex dev deployment, a copy of dev's functions, settings,
  data and stored files, with `scripts/branch-db.py` (app-dir: the folder holding
  `convex.json`, default the root; cells-app names the pack it runs). The worktree tests and
  breaks its copy, and landing puts it back on the shared database. `shared-dev` (the
  default otherwise): previews and localhost use the app's dev database, ship never
  rewrites an env file, and it says so on the card, or in the `result:` line, when a
  branch changes a schema. `per-branch`: ship provisions a database preview per branch at
  stage 0 and deprovisions it at teardown (incidents: Backends).
- **`stack:`** how to run `scripts/stack-check.sh` (in this skill's directory) for the
  repo: the host team and the app projects, plus where each app's Convex dev deployment
  and prod deploy key are. It checks that dev and prod never cross: git link and
  production branch (`--production-branch <branch>` where it is not main), protection, the Convex deploy key on Production only, every dev
  Convex setting present on prod, Clerk `pk_live` on Production and `pk_test` elsewhere.
  Ship runs it before TEST and before landing; a ✗ is ship's to fix, never Pete's.
- **`live:`** what landing on main deploys, and how to watch it. cells-app: "main is
  production; each touched pack's Vercel production build pushes its Convex functions,
  then the app." Default: nothing, and ship claims no deploy.
- **`release:`** for a repo whose main is a parking lot: the word that puts main on
  production and the command it runs (cells-app: "release" runs `npm run release`). Ship
  runs it only on that word, never as part of landing, and watches what `live:` names.
  Without it, landing is the release wherever main deploys.
- **`smoke:`** the repo's automated end-to-end smoke, in two halves. `branch <cmd>` runs
  against the worktree's own server once, in BUILD's pre-flight, and again only if the tree
  changed before landing (LAND's step 0); never per milestone push or per task, because a
  smoke can cost real model calls (cells-app's: about 12 bot turns, about 13 cents). `main <cmd>`
  runs once per landing, after the deploy watch, against what landing put live, or main's
  own server where main deploys nothing (cells-app: `local-pack.sh --restart` smokes main on
  localhost). It is the one check that sees ships together: each branch was tested alone,
  and two that land an hour apart are never walked side by side. Default: none, and LAND's
  one load of each live URL is the whole check. A smoke red whose failing step is a network error
  to a third party (a connect timeout, a DNS failure) gets one rerun, said in the `result:`
  line; any other red is real.
- **`board:`** where the repo's tickets live, how to file one, and what each column means
  (cells-app's names them and says which a ship may file into). Default: none, and
  follow-ups stay in the `result:` message.
- **`ios:`** for a native iOS app, the command that builds the branch's own app, pointed
  at the branch's server, installs it on a device by name ("iPhone PM" or a simulator),
  and prints its IOS line (device, udid, bundle id). Default: none. A web app is tested in
  the browser, its mobile layout at phone width (390px) there; when what's being built is
  meant for phones (the spec or storyboard says mobile web), the QA script may add Safari in a
  booted simulator. That is a judgment call on the build, and never iPhone PM, which is
  for native apps (Pete, 2026-10-05).
- **`land:`** how a branch reaches main. `pr` (the default) squash-merges
  the tracker PR. `direct` pushes `HEAD:main` after a rebase and opens no PR. `auto`, for a repo whose main
  deploys nothing, lands on the QA run's `works` and never waits for Pete, money paths
  included. Any other value is
  a command ship runs from the worktree in place of the merge (a mirror remote, a
  local-only main, a promote hook that builds on push); the command is the repo's, and
  ship never invents one.
- **`ship: no`** — for repos that shouldn't ship at all (wikis, civic work): decline and
  say why.

Rare repo shapes have their own rules in `reference/rare-cases.md`: read the section
before stage 0 when the contract declares `design of record: transplant`, a release
ritual, or a `land:` other than `pr`, when the ship targets another repo than the
session's, and before changing how ship runs under Codex Desktop.

## Decision memory — settled calls survive the session

`scripts/decisions.py` in this skill's directory keeps one decision log per repo. Run
it from inside the target repo.

- **DISCOVER start, and PLAN start on SELF-DIRECTED:** run
  `decisions.py relevant "<the idea in one sentence>"`. It returns the six decisions
  that bear on the idea, whatever their age (the decision model scores every active one; if none
  answers it prints the newest instead and says so). Treat them as settled calls with
  their rationale. Don't re-ask Pete a settled question; reversing one is allowed, but
  say so explicitly.
- **When a gate (or Pete mid-run) resolves a durable call** — design direction, scope
  cut, architecture or tool choice — log it:
  `decisions.py log '{"decision":"…","rationale":"…","source":"user"}'`, or `log --file <json>`
  from inside a worktree, where the guard refuses quoted JSON. A reversal is
  `decisions.py supersede <id> '<json>'`, with the id `recent` prints. Turn-level edits
  and phrasing tweaks are never logged — a noisy store is worse than none.

## The pipeline — create a todo for each stage

Each stage writes its marker with `scripts/stage.sh <worktree> <stage>` (the status
line and the FleetView row read `.ship-stage`). Call this skill's scripts (`stage.sh`,
`route.py`, `decisions.py`) by absolute path, the base directory the harness printed when
this skill loaded plus `/scripts/`, typed out in full, never through a shell variable,
which the worktree guard refuses. A script or brief file goes in the job's tmp through
the Write tool, since the Bash sandbox can't write there, or under `$TMPDIR` from Bash, and
either one runs by its path typed out in full, never `python3 "$TMPDIR/x.py"`, which the
guard refuses like any computed path;
and every stage flip posts Pete one
line: the goal, the stage, what's next. Post it again after a compaction or a side job.
Five runs had him asking "where are we?" mid-flight.

**What runs with the Bash sandbox off.** Anything that writes outside the worktree or binds
a port: the fork (`wt switch --create`, `stage.sh` on a new worktree), the ledger (`route.py
log`), `muse.py`, anything that talks to GitHub (`gh`, `git
push`, `git fetch`: the sandbox's proxy fails their TLS check), any git command that rewrites
the tree (`rebase`, `merge`, `checkout`, `reset`: the sandbox denies writes under `.claude/`,
and CEL-213's rebase stopped halfway there, leaving the tree split between main and the
branch), gates, smokes and dev servers. Everything else
stays in the sandbox.

**`$TMPDIR` changes with the sandbox.** A sandboxed Bash call sees `/tmp/claude-<uid>`, one
with the sandbox off sees `/var/folders/…/T`, so a file one writes is missing to the
other. Anything that crosses (a log, a script, a brief) gets an absolute path under the
job's tmp or the worktree, or rides the background call's own output file.

**Env files without sourcing.** The guard refuses `set -a && . ./.env.local`; give the tool
the file instead (`tsx --env-file=.env.local`, `node --env-file=.env.local`).

**Shell inside a worktree session.** The harness refuses a command it can't tell stays
in the worktree: `$(git …)` substitutions, `cd <dir> && git …`, loops or heredocs that
name git, and read-only commands it misparses (a path segment named `source`, a zsh
`echo ==`, a `for` loop over `sed`, a heredoc that only writes files, a docker `--format '{{…}}'`
string, a `python3 -` heredoc whose text says "git", a `$VAR` argument even to a binary that isn't git). Read and search
with the Read and Grep tools when the session has them, which it never checks; else use
`git -C <path>`, one plain command per call, and put anything multi-step in a script
file under the job's tmp directory. Any file edit the Edit and Write tools can't make
goes the same way: Write the script to the job's tmp, then `bash <path>` or `python3
<path>`. Never an inline heredoc, `sed -i` chain or loop first, not even once: one run
hit the guard eight times reaching for them. A command on the main checkout (`cd <main> && git`,
`git -C <main>`) is refused while the session is in the worktree: run it from a script, or
after `ExitWorktree` at LAND. Two runs lost 40 commands to split-and-retry, and two more
lost about ten each (2026-10-05). Written for Claude Code; a Codex driver runs `codex/ship.md` instead (see
`reference/rare-cases.md`, Running under Codex Desktop).

### 0 · Worktree (invisible)  → marker: `discover`

**Prereqs:** a git repo with a base branch and ≥1 commit (zero-commit repo: `git add
-A && git commit -m "init"` first). The PR path needs a GitHub remote; a repo with no
remote falls back to `wt merge` at merge time.

**Resolve the base branch first — never assume `main`:** `git symbolic-ref
refs/remotes/origin/HEAD` (strip `refs/remotes/origin/`), else `origin/main`, else
`origin/master`, else local `main`. Every `main` in this pipeline means that detected
base branch.

**Waiting on other ships to land** (a docs ship written from main once its siblings are
  in): run the wait as a background Bash call, which wakes the session when it exits:
  `until [ -z "$(gh pr list --state open --search '<keys>' --json number -q '.[].number')" ];
  do sleep 300; done` in a script file. Give it no deadline; if it does stop (a usage pause,
  a restart), start it again rather than landing early.

**Never stack on a branch that hasn't landed.** Asked to build on top of another
ship's branch, branch off main anyway, cherry-pick only the commits you need from it,
and open the tracker PR against main. Its own rebase later finds those commits already
there. A PR based on the other branch strands at landing whenever that branch
hasn't landed first (incidents: Worktrees).

**A card key in the idea (`CEL-103`) means look before forking:** `git branch -a --list
'*<key>*'` and `gh pr list --state open --search <key>`. A hit whose worktree has no live
session (none in ListAgents, its `.ship-stage` not moving) is a stalled ship: resume it in
that worktree at its stage, PR and all. A fresh fork beside it once rebuilt CEL-103 while
its first run sat at `build:6:7` with PR #200 open. A hit with a live session is another
ship's: tell Pete in one line and stop.

Check free disk first (`df -h ~`): under 10 GB, tell Pete in one line before forking.
A fork copies the repo's ignored files, and a full disk once failed `stage.sh` and
`decisions.py` with ENOSPC in the middle of a LAND.

```
git fetch origin
wt switch --create feature/<slug> --base origin/<base> --no-cd --format=json -y
```
(`origin/<base>`, the base branch resolved above, because a stale local copy has cost a
rebase and reinstall), with the Bash sandbox off: it writes under `~/Projects/.worktrees`,
which the sandbox refuses after the branch already exists. A fork that half-ran ("Branch
already exists", no worktree) finishes with `wt switch feature/<slug> --no-cd -y`, without
`--create`. Then enter
the path from the JSON. A second ship in the same session calls
`ExitWorktree({action:"keep"})` before `EnterWorktree` on the new path. A session launched
inside a worktree can't: `EnterWorktree` refuses a second wt-made worktree, and its sandbox
only covers the launch tree, so its next ship starts a fresh session from the main checkout
(CEL-128, 2026-10-17); if the cwd isn't
inside the repo at all (a teardown by absolute path leaves it in `~` or a removed folder),
`cd <main checkout>` first, since `EnterWorktree` refuses from there. In the session's primary repo, `EnterWorktree({path})`
is required: the status line and FleetView read the session's cwd,
so a run that keeps working by absolute path while parked on main is invisible to Pete
even though `.ship-stage` is being written faithfully in the worktree (he has had to ask
mid-BUILD whether a run forked at all). Absolute-path driving is the *cross-repo*
fallback only, where `EnterWorktree` can't take. Self-heal: notice mid-pipeline that
the session cwd isn't the worktree → `EnterWorktree({path})` right then; it works fine
after the fact. `--no-cd` is load-bearing. A `.config/wt.toml` auto-provisions
gitignored runtime files. With none, provision the worktree yourself before the first
gate: the repo's frozen-lockfile install, a real one and never a link (this tree runs the
dev server and the production build, and Turbopack refuses a linked `node_modules`), and
a copy of the main checkout's gitignored env files (`.env.local`). Without them the first
test run dies on module-not-found, which reads as a real red. A provisioned install is the
main checkout's, which can be older than the origin/main the worktree forked from: when the
worktree's lockfile differs from the main checkout's (`cmp <worktree>/package-lock.json
<main-checkout>/package-lock.json`, or the repo's own lockfile), run the frozen-lockfile
install before the first gate (eca-finder's copied `node_modules` lacked main's new
`@amplitude/*` packages and failed typecheck five times). Run `scripts/stage.sh <root> discover`: it writes the marker
and adds `.ship-*` to the repo's `info/exclude`, since `git add -A` sweeps the marker
into commits otherwise (incidents: Worktrees). Never build on main.

- **Push the branch at once** (`git push -u origin feature/<slug>`), and open the
  **tracker PR** as a draft with the first commit (`gh pr create --draft --base main
  --fill`; GitHub refuses a PR with no commits). Every commit message and PR body is a file
  written with the Write tool, then `git commit -F <file>` and `gh pr create --body-file
  <file>`, one command per call: the worktree guard refuses a heredoc and a chained
  commit, push and PR. Its body is the one-line why and the
  preview links, refreshed as they change. It is GitHub's record of what is in flight and,
  once squashed, of what shipped; it is never a review step. `land: direct` opens none.
  A branch that should carry a card key (`cel-52-…`) gets it at the fork. Renaming one
  later closes its tracker PR (GitHub did, 2026-10-14): open a new PR on the new name and
  close the old one on purpose, then re-read the dev origin (`dev:`, e.g. `scripts/dev.sh
  --print-origin`), since a repo that derives its port and host from the branch moves both.
- **Backend:** `copy` → right after the fork, start `branch-db.py up <worktree> [<app-dir>]`
  in the background, once per app the branch runs, and let it finish before the first
  convex command or dev server: until it does, the worktree's `.env.local` is main's and
  points at shared dev. It takes about 1.5 minutes and prints the copy's name; that name is
  the BACKEND a verify brief pins. From then on the worktree's `convex dev`, and the Convex
  plugin's Stop hook, push to the copy, which is what they should do. The Convex MCP tools
  don't follow it: they resolve the shared dev deployment. Read and write the copy with the
  CLI from the app-dir (`npx convex data <table>`, `npx convex run`), never the MCP, or a
  test write lands on shared dev. The hook fires only
  when a turn ends, so any edit under `convex/` in REVIEW or TEST goes to the copy with `npx
  convex dev --once` before the next QA step: a triage fix that skipped it failed CEL-103's
  QA on the old function. Stripe and Clerk
  webhooks still go to shared dev, so a webhook flow is tested there or said to be untested.
  The copy expires 7 days after it was made, which is the cleanup; a branch older than
  that restores its env files from main (`wt step copy-ignored` where the repo uses it) and
  runs `up` again. `up` refuses when a deploy key sits in the app's env files, since the CLI
  then ignores `--deployment`, and repoints the worktree only once the copy is whole. `shared-dev` → build against
  the app's dev database and touch no env file. Another live worktree whose branch changes
  `convex/` turns that database into a fight: the Convex plugin's Stop hook pushes each
  tree's whole `convex/` at every turn end, so each push drops the functions the other
  added (a catalog ship's survived only because the other branch's data failed
  validation). Check at the fork, and again right before any push to shared dev, since a
  sibling can start touching Convex in between (`git worktree list`, then `git diff
  --name-only origin/main...HEAD -- <paths>` in each live one). The paths are every folder
  the repo's Convex code lives in, not just `convex/`: the ones the contract names (cells-app:
  `convex/`, `convex-core/`, `packs/*/convex/`), else each `convex.json`'s `functions` folder.
  On `backend: copy`, `branch-db.py diff <worktree> [<app-dir>]` lists the functions a push
  from this branch would drop from shared dev, and exits 1 when there are any. When one does, tell its session and
  plan one merged push up front: from a throwaway `git worktree add --detach` holding both
  branches' `convex/`, until the first lands; then merge main and push alone. A repo that
  keeps hitting this belongs on `backend: copy`. `per-branch` → provision the branch's database preview now; a worktree
  building against a shared backend it changes clobbers it (incidents: Backends). Rewrite
  the worktree's env file to the preview before the first backend command and confirm the
  first deploy's host is the preview: the inherited `.env.local` carries the shared key,
  and the `--preview-name` flag does not override it (incidents: Backends). From here on
  the preview's *name* comes from that file, never from the branch.
- **Cross-repo case** (the target repo's `git rev-parse --git-common-dir` differs from
  the launch repo's): `reference/rare-cases.md` first.
- **A new ship always forks a new worktree.** A session that just landed one and gets
  the next never runs `git switch -c` inside the old tree: the old worktree then
  outlives its merge under another branch's name, and cells names its instance after
  the branch, so the first instance is orphaned.
- **Recon may contradict the fork — then re-fork.** In a multi-repo workspace the target
  repo is itself a recon finding (incidents: Worktrees). Exit, `wt remove` the empty
  worktree, fork in the right repo, narrate the move. Fork-first stays; being wrong
  about the repo is cheap, being invisible is not.
- **Opportunistic tidy:** glance at `git worktree list` and `wt remove <branch> -f`
  any worktree that provably landed (a merged PR whose `headRefOid` matches its HEAD, or,
  with no PR, a HEAD inside `origin/main` by `git merge-base --is-ancestor`; clean tree —
  incidents: Worktrees). Never touch one with uncommitted work, one a live session holds
  (wt's 💬), or one under two hours old: a worktree or lane born a minute ago sits inside
  main or its parent exactly like a landed one, and a sweep took a lane mid-task.

### 1 · DISCOVER — Pete's taste, up front  → marker: `discover`, then `gate:1`

- **Resurface decision memory first** (see Decision memory) — settled calls constrain
  the grilling; don't re-litigate them inside it.
- **Grill on the storyboard, never in chat.** Call the Skill tool with
  `mattpocock-skills:grilling` for how to ask: each round asks every question that's open
  now, numbered Q1, Q2…, each with your recommended answer and worded so "yes" takes it,
  and recon answers the facts. The questions live under the frames, each naming the
  frames it's about; the chat carries only the `needs input:` line (Pete, 2026-10-16: "I
  like my storyboards"). Nothing is asked before round 1: where an answer would change
  what to draw, draw your recommendation and ask under it.
- **Recon runs on a subagent, synthesis stays with the driver.** Codebase
  evidence-gathering dispatches as a read-only Opus subagent (report findings, edit
  nothing).
  The recon brief includes a reuse audit: for every core noun the feature
  introduces, grep the whole repo — data layer included — for existing infra before the
  plan treats it as new (incidents: Design). When the design lands on an *existing*
  surface, it also classifies that surface's liveness — current design system?
  reachable from primary nav? touched by recent commits? — because a deprecated page
  serves happily (incidents: Design). The spec names the chosen surface explicitly.
  It also lists the ships already in flight in this repo (`git worktree list` and each
  tree's `.ship-stage`) whose surfaces overlap this one; ask those sessions what they are
  changing (ListAgents, SendMessage) before round 1, because a parallel ship can redefine
  what the storyboard is about to show. Any count it reports comes from an API total
  (`gh api search/issues` `total_count`), never from the length of a `--limit` list: a
  capped list put 18 merges on a storyboard that should have said 62.
- **Bug-shaped requests get an empirical root-cause check** — reproduce the failure or
  read the runtime evidence; never spec a fix from a hypothesis (incidents: Design). When
  the measurement contradicts the card's own call, the measurement wins: fix what it
  shows, and say so in the PR and on the card. CEL-74's card said to stub a slow step;
  no run was slow, and the fault was a port collision.
- **Consult the installed domain experts before you spec.** Recon tells you what the
  repo does; an expert tells you what the *stack* will do to you. Where the change
  lands in a domain some installed agent knows better than you, ask it — as harness
  subagents (the Agent tool, `subagent_type`), fired in parallel while recon runs, one
  round, before the storyboard is drawn. Not a coding subagent; not a second recon pass.
  - **Read the session's own roster** — the available agent types and skills are listed
    in-session — and match against the surface the change actually touches:
    `convex/` → the Convex expert (and its authz auditor when the change moves
    ownership or exposes records), a Claude Code capability (hooks, MCP, subagents,
    SDK) → the claude-code guide, DNS / WAF / the edge → `cloudflare`, an always-on
    agent → `flue`. Never a hardcoded list — rosters differ per machine and repo.
    Nothing matches → consult nobody; a manufactured consult is worse than none.
  - **Ask what changes the design, not what does the work.** "What's the canonical
    pattern for this here", "what will bite us at scale", "what does this choice make
    impossible later", "is there a component that already does this". A consult whose
    answer couldn't move a line of the spec was a wasted turn.
  - **You keep the pen.** Answers are evidence, weighed like recon — the driver writes
    the spec, and Pete's settled calls (decision memory) and the repo's `CLAUDE.md`
    outrank any agent's opinion. When a consult changes a decision, name it in the
    spec's TL;DR so the reason survives the run.
- For any visual/UI feature, invoke `impeccable` and follow its Setup (`<skill
  dir>/scripts/impeccable context`; the repo's PRODUCT.md/DESIGN.md are the visual
  authority): a new surface or replacement look routes through its `shape`/new-work
  path; a refinement stays on the incumbent world. Before new-work, merge `"buildPath":
  "code"` into the repo's gitignored `.impeccable/config.local.json`: ship builds in code,
  and the storyboard is the one approval Pete sees, never impeccable's decision page or
  image comps (impeccable 4.5, 2026-10-05). Imagery inside a frame is drawn in code (SVG,
  CSS, a gradient or a labeled placeholder): `/image-gen` runs on Codex, which Pete has
  dropped for now (2026-10-22).
  **Ground the design in the live product**: a subagent walks the running app /
  deployed URL over the chrome-devtools MCP and reports the real theme/CSS with screenshots;
  design from those, never from in-repo mockups (incidents: Design).
- **DISCOVER is a storyboard, not a document.** The first thing he
  sees is the app: an HTML page that is mostly mockups of the screens the feature
  touches, the way a designer opens a session by putting comps on the table. He reads
  it like a storyboard, reacts, and you redraw. Nothing in DISCOVER is a spec; the
  spec is written after his go (stage 2).
  1. **Round 1 — the storyboard.** One file per ship,
     `specs/designs/YYYY-MM-DD-<slug>.html` in the docs home, from
     `reference/storyboard.html` (contract below). It is an artboard board, laid out the
     way a design tool lays out a page: every screen and state is its own artboard at its
     real device size, side by side in story order, all at one zoom. **It tells the whole
     flow, not the screen that changes**: it starts where the person comes from, runs
     through every step of the new part and ends where they land, existing screens drawn
     as they are and marked unchanged. **Every frame has a code** (A1, A2… per row, below)
     so Pete can answer "A3 too busy" and you know the frame. Draw more, smaller
     frames: every state the feature passes through (empty, typing, loading, results,
     error, done, the phone) gets its own artboard, rather than a few tall screens stacked
     down a long page. Each artboard is live HTML in the product's own stylesheet and
     tokens, so a hover, an open menu or a tab inside it works, but artboards are never
     wired to each other: no "try it" prototype at the top, no click-through between
     frames (Pete, 2026-10-12: "move away from the full interactive app"). Where a direction
     is genuinely open, draw it as two or three artboards of the same screen in an options
     row (`02-exploration-visual-designs`), never as prose options. The words on the page
     are captions, one line under each frame saying what is new in it, and the round's
     questions under the board. Recon, consults and the reuse audit go in one collapsed
     block at the foot, for the record; they never sit above a frame. No TL;DR essay,
     no section per research finding, no fait accompli. `stage.sh <root> gate:1`, commit,
     fire the gate notification, `show.sh <root> <slug> storyboard <file>`, end the turn with `needs input:`
     ("storyboard round 1 — reactions?"). **HARD STOP** — every round is one. It is a
     local HTML file in his browser, never a Claude artifact (Pete, 2026-10-08).
  2. **Rounds.** Pete reacts, by code where he can; "yes" takes every pick on the page.
     Redraw the frames in place, in the same file, and bump the
     round in its `<title>` and `data-round` — minutes per round, not a
     re-spec. A frame he killed is deleted, never greyed out, and its code is never
     reused: A3 means the same frame in round 5 as in round 1. A new frame takes its row's
     next number. Answered questions leave the page; new ones continue the Q numbers. Re-`show.sh` (it replaces the old tab), end the turn
     with `needs input:` again. Push back where taste warrants it: a designer with no
     opinions is a renderer. Loop until he locks it ("this is it", "lock it", "yes").
  3. **Lock = GATE 1.** Commit the storyboard as it stands: it is the design of
     record from here on. Every frame left in it ships; nothing not in it does. Log
     the direction to decision memory, then straight into PLAN.
  Pen (the Pencil app) is no longer the default. When Pete asks to take a frame into
  pen, put it there, let him iterate, and harvest the result back into the frame
  before the lock; the storyboard stays the single design of record either way. When the design of record lives
  on another branch, copy the frames this ship builds into its own branch at PLAN and point
  every brief at that copy: a design session on the other branch trimmed CEL-146's frames
  before its QA ran.
- **Commit every gate artifact to the branch before you fire the gate** (storyboard,
  plan card). A parked ship with uncommitted work looks disposable to another
  session's cleanup sweep, and one nearly lost its spec that way (incidents: Worktrees).
- **The driver draws the frames and writes the captions inline** (taste is the
  deliverable, never dispatched). A subagent may build a heavy asset a frame calls for
  (an animated film) to the driver's frame and caption, never the frames themselves.
- A trivial visual change where several frames would be noise may collapse the
  storyboard to one frame + one confirm — never to zero showings on the GATED lane.
  A non-visual GATED ship (pure product tradeoff, no UI) has no storyboard; it gates
  on a one-screen board in the `14-research-feature-explainer` shape: TL;DR first,
  the one question that matters, depth collapsed.

### 2 · PLAN — the plan Pete says go on  → marker: `plan`, then `gate:2` when it stops

- `stage.sh <root> plan`. Run `ponytail` as the *waste* critic, not a scope critic — it cuts
  reinvention and gold-plating, never a frame Pete locked.
- **A task that hooks into a dependency's runtime** (a framework's workflow or sandbox, a
  bundler's transform, the shape a model must answer in) is followed in the plan by a
  driver live check: run the real thing once in the worktree. CEL-80's check after its
  Task 8 found two bugs no unit test or build could. Lanes carry no `.env.local`, so live
  checks are always the driver's, never a lane's.
- **Consult a domain expert again only for a question the plan raises and the
  storyboard didn't settle** — schema shape, index or migration order, an API's real
  constraint, an auth boundary. Same rules as DISCOVER's consult: harness subagent, a
  question not a task, the driver decides. On SELF-DIRECTED — which skips DISCOVER's
  storyboard — this is the lane's only consult, so a stack question that would change
  the plan gets asked here or nowhere.
- **Render the plan card** from `reference/go-card.html` (contract below): the locked
  storyboard in one glance, then what gets built as a punch list in plain English
  (one line per piece of work, in build order), the cut list, his calls with your
  recommendation, the risk line, and "go". Commit it, `show.sh … plan` it.
- **Calls on the card are plain language, and only the ones that change what he gets.**
  Each says what he'd see either way. A technical choice where you have a clear pick is
  yours: take it and log it. Never offer to phase the work.
- **GATE 2 is his go when the card carries a call** (Two principles). `stage.sh <root>
  gate:2`, fire the gate notification, end the turn with `needs input:` ("go?"). **HARD
  STOP.** A card with no call is not a stop: `show.sh … plan` it, post one line ("plan card: no
  calls, building"), write no `gate:2` marker, and go straight on as if he had said go. SELF-DIRECTED renders no
  card and stops for nobody.
- **His go → spec it out.** Only now does the machine-facing writing happen: invoke
  `superpowers:writing-plans` for ONE execution plan covering the entire
  storyboard — never sliced into phases — saved to the docs home
  (`specs/plans/YYYY-MM-DD-<slug>.md`). It carries everything a frame can't: copy as
  data, routes, behaviour, states, a11y, test cases, and for each UI task the frame it
  must match (`<storyboard>.html#A3`, its code, never a prose description of the frame).
  Pete never reads it. A change he asks for after go is an express round, not a
  re-plan. Each task names its files, the signatures it adds or changes, and its
  test cases — brief-grade, so the BUILD brief is a paste plus deviations. Every
  4-minute first-pass-clean dispatch in the ledger had this; every 25-minute one
  left the worker to find the shape itself.
- **A task that computes from rows another code path writes gets one end-to-end test
  through the real writer** — not just unit tests over hand-built rows, which pass while
  the production writers produce garbage (incidents: Design).
- **Every task is a `### Task N: <name>` heading**, which `route.py plan` counts.
- **Wonder reviews the plan before BUILD, on every lane that has one** (Engines: the
  readers; an Opus subagent when Muse is out). Write the brief to a file. It reads the storyboard or spec, the
  execution plan and the repo's ship contract, edits nothing, and returns findings as task, problem, fix: a
  frame or requirement the spec names that no task covers (it maps each one to its task
  and lists the orphans: one plan built a spec's intro and none of the screens its frames
  asked for, and Pete caught it mid-build), a missing task, a wrong file, a test that cannot fail, an order that breaks, a seam two tasks each assume the other owns, a concurrency fix whose guard checks only
  which write is newer and not whose it is (CEL-152's newest-wins rule passed plan review;
  both branch readers caught it), a
  screen that waits on someone else with no way back to it (trace how the user returns
  once the other side acts; one plan's payoff screen was unreachable without re-walking
  the intro), and a
  step that copies a secret from somewhere it can't be read back (a Vercel sensitive
  variable pulls as a placeholder): that step becomes a planned rotation on both sides,
  and the card says it signs everyone out once. For every third-party API the plan
  calls, it checks paging, resuming from a saved cursor after a pause, what a deleted or
  cancelled item looks like, and items the API expands (recurring events): one plan
  review passed four such bugs that only branch review caught (muse-7-notifier,
  2026-10-14). A task that reads what another part of the app produces, a loop's brief or
  a tool's payload, quotes a real sample of it, never the storyboard's mock: one plan
  parsed a "Price" heading from a mock when the live brief says "Budget", and only QA
  caught it (market-loops, 2026-10-15). The driver triages and edits the plan, and logs the reader's tally: `route.py log
  repo=<repo> ship=<slug> review=wonder stage=plan real=<n> false=<n> out=<out-dir>` (`review=opus
  seconds=<n>` when Opus read in its place). Nothing goes back to Pete unless it changes what
  gets built. Then `route.py plan` (Engines). No task starts before the review lands,
  unless the plan names it a spike: two runs built early and
  rewrote what the review then flagged.

### 3 · BUILD — automatic  → marker: `build:N:M` (N done of M tasks)

- `route.py plan` already moved the marker to `build:0:<M>`, and each `route.py log`
  counts one task done. A run that skipped `route.py plan` writes `build:0:<M>` itself before the
  first task, and still logs each task it built: `route.py log` needs no saved route,
  so a ship promoted mid-flight logs its tasks as `engine=driver`; a status line still on `plan` mid-BUILD is the tell. Build all M tasks in one session; commit
  each task on the branch as it lands, land only when the whole plan is built.
- **Push at every milestone, and hand Pete the links.** After a task
  is committed, push the branch. When the repo has a per-push `preview:`, run it once the
  builds settle, never blocking the next dispatch on them, and post one line per app with
  what changed and what to try; with an on-demand one, post the localhost. Pete works solo and tests mid-flight, so the links always show
  the worktree's latest. A build that failed is yours to fix before you post.
- **The driver builds every task itself, in plan order** (Engines), test first where the
  task names its tests, and commits each one as its gates go green. A task handed to a
  subagent is the exception Engines names, and says why in the ledger's `note`.
- **Check the plan's files against work in flight, before the first task.** `gh pr
  list --state open --json number,headRefName,files` and `git log origin/main --since=1.day
  --name-only`: a plan file another PR or a fresh main commit also touches gets read first.
  If it already makes the same change, drop the task and absorb it once it lands; if it is
  mid-flight, ask its session (ListAgents, SendMessage). showing-followups rebuilt "each
  branch gets its own Simulator" while cells-app #206 had it in review, and the rebase
  conflicted.
- **A task's check is the diff and the gates, nothing else.** Read the diff, run
  tsc/tests/lint, commit. Nobody drives the app or CLI per task: the pre-flight is once
  at the end of BUILD, and the QA run is TEST's. A reviewer hand-driving
  the product per task cost 20 minutes a task and found nothing the gates missed.
- **Standing brief boilerplate** (each line from a burned run, incidents: Dispatch):
  one task per brief, with the plan's complete code pasted in, the exact test commands
  and the files it may touch; "do it, do not propose", because a worker given an open ask
  stops and proposes; test files whose assertions the planned change invalidates are always in
  scope, allowlist or not; the final message is STATUS, TESTS, CONCERNS, and a longer
  report goes in a file inside the worktree; the worker never commits and never
  runs `git reset/checkout/stash`. A
  repo whose rules load by path (`.claude/rules/`, a `scripts/rules-for.py`) gets those
  rule files named in every brief, because a subagent only sees them if told. A subagent
  never gets a copy of the env files: the Convex plugin's Stop hook pushes the tree's
  uncommitted `convex/` to whatever deployment its `.env.local` names, so one copied in
  ships a half-edit to the copy the driver is testing, or on `shared-dev` to everyone. A Convex
  repo's briefs say `convex codegen` prints "Uploading functions" while it analyzes and
  deploys nothing, so no worker stops to worry about it.
- **Never add scope to a running worker by message.** New findings wait for its report
  and go out as the next fix round, and the report is checked against every message
  it was sent. Two workers finished before reading items sent mid-run, and both cost a
  redo.
- **A cut after go is said out loud.** Any plan item dropped, narrowed or swapped after
  Pete's go, including a model or tool that differs from the reference, goes in the
  next message and the `result:` line. One run dropped a settings dropdown Pete had
  asked for and he found out by asking "this is all done?".
- **A fix round goes back to the same worker** with the findings as the brief, so the
  context is already paid for: `SendMessage` to the same subagent. Two wrong diffs on one
  task and the driver takes it back and writes it, and the ledger records `verdict=redone`.
- **A quiet run never blocks the build.** The harness wakes the driver when a subagent
  returns, so silence is not a signal to chase. If a subagent's work is visibly in the tree and no report has
  landed, self-serve: review the diff and run the gates yourself. Dead air on the
  *reporting* path has stalled a real ship twice in one run; the work was already done
  both times.
- `ponytail` posture; `superpowers:verification-before-completion` before claiming any
  task done — actually run it; `superpowers:systematic-debugging` on a red test. A test
  that fails three or more times across full runs is a bug, not a flake: root-cause it
  (shared temp files or ids between parallel suites are the usual cause), never retry it
  green. Three workers once called a real race flaky and buried it under a longer timeout.
  A timeout goes up only for a test that is slow by design: it passes every time alone, its
  time is its own work (frames, a big fixture) rather than a wait on something shared, and
  the commit says the numbers ("~1 s alone, past 5 s under the full suite"). One that
  won't reproduce across a few full runs ends as "no repro", with what was tried and any
  real fault found nearby, never as a guessed fix.
- **UI-writing briefs carry the storyboard frame and the craft floor** — every
  dispatch that writes UI names the frame to match
  (`specs/designs/<storyboard>.html#A3`, its code; the worker reads the frame's markup
  and CSS, which is why a frame beats a PNG), and — since a subagent does not get the
  impeccable hook — tells it to read
  `~/.claude/skills/impeccable/reference/craft-floor.md` and honor its checks and bans,
  plus the three model defaults the storyboard contract bans.
- **Before BUILD is done, a light pre-flight, so the QA run never opens a broken
  page.** Run the gates and, for a framework with its own production build, that build;
  compare the key names in the worktree's env files with the main checkout's (and
  `.env.example`): a key main gained after the fork is missing here, and an agent that
  can't start reads as a product bug and costs a QA round. Then boot the app, confirm the
  server on its port is this worktree's: `scripts/listener.sh <port>` waits for the
  listener and prints its pid and the checkout it serves, walking up the parent processes
  when a Next server's own cwd reads `/`: brief-and-home's
  hashed port was already held by another checkout's server, its own died on EADDRINUSE
  in a log nobody read, and the first smoke walked the wrong app). Another checkout's
  listener is never stopped, before or during a run: start this worktree's server on a
  free port (the contract's `dev:` says how; `PORT=<n>` by default) and read the port back
  from the repo's dev command for every link, smoke, test and app build after (CEL-120
  stopped CEL-118's server on a shared 3144, thinking it its own). Then load each surface
  the feature touches once in the chrome-devtools browser: it renders, its first step works, the console is clean. Then the contract's
  `smoke: branch`, once. Not a walk-through:
  that is TEST's QA run. A feature that makes model calls also counts the canned or
  fallback lines in the dev log after those loads: a nonzero count is a defect (a
  timeout shorter than the model's real turn, a length cap every answer fails), never noise.
  A change with UI also runs impeccable's detector on the UI files it touched,
  `~/.claude/skills/impeccable/scripts/impeccable detect --no-advisory <files>` (exit
  0 clean, 2 findings on stderr, 1 a file it couldn't read): fix each finding, or waive a
  deliberate one in place with its `impeccable-disable-line <rule> -- <why>` comment.
  It is free and mechanical, so the QA run never spends a round on a craft-floor miss.
  Every web surface the feature touches also runs `scripts/icon-check.py <url>...` (same
  exit codes): it needs a browser icon and a 180px PNG Home Screen icon, since Pete opens
  apps by name from his phone and the launcher shows their icons (Pete, 2026-10-14). When one is
  missing, make it before landing in the app's own colors: the mark through impeccable as an
  SVG, and the PNG rendered from it by chrome-headless-shell (`--headless --screenshot=<png>
  --window-size=180,180 --default-background-color=00000000 file://<svg>`) (Next: `app/icon.svg` and `app/apple-icon.png`).
  Also, on `backend: per-branch`,
  the branch touched `convex/` → re-push the preview (`npx convex deploy --preview-name <name-from-
  .env.local> -y`, from the worktree root — the branch name and the shell's leftover cwd
  have each sent a deploy to the wrong place). *You* find the breakage, never Pete.
- Raise a hand only for a genuine fork (PM-framed, with a rec).

### 4 · TEST — ship reviews it, then uses it as Pete would  → marker: `review`, then `test`

Three phases after the plan, as Pete sees them: BUILD, TEST, LAND. TEST's first half is
ship reviewing its own work (gates, a cold correctness read); its second half is ship
using the running thing the way Pete would, from a QA script it writes and runs in this
session, in a browser, and on his iPhone only when the repo has a native app (Pete,
2026-10-05: the one who sees the bug fixes it, so a round is a rerun, not a hand-off).
Its pass lands the branch; after it, nothing waits for Pete unless the lane is a money
path, he asked to try it himself, or the run could not prove it. Codex tests only when
he asks.


- `stage.sh <root> review`. Sync with main first: `git fetch origin`; absorb upstream in the
  worktree (rebase, or merge if unsafe), rerun the repo's install when the absorb changed
  a lockfile or the workspace list (main's new packages otherwise fail typecheck), re-gate
  by **overlap** (on `backend: copy`, when the
  absorb brought Convex changes, push them to the copy with `npx convex dev --once` in
  each app-dir: nothing else does, and muse-core-loops' QA hit a function main had added
  that its copy lacked), then dispatch review — and
  re-sync right before landing if main moved again (incidents: Worktrees). On
  `backend: per-branch`, if the absorbed commits touched `convex/`, re-deploy the preview before any further
  verification — function skew is invisible to tsc, vitest and the production build,
  and has hard-crashed a page after a green rebase (incidents: Backends).
- **Re-gate by overlap after an absorb.** Before absorbing, compare what main brought with
  what the branch changed: `comm -12 <(git diff --name-only HEAD...origin/main | sort)
  <(git diff --name-only origin/main...HEAD | sort)`. Full gates when that prints a file, or
  main brought a lockfile, the workspace list, a schema or anything under `convex/`.
  Otherwise the typecheck alone: main's commits passed their own gates and touch nothing
  this branch does, and the typecheck catches an API they changed under it. A repo's
  contract that says to run the gates after every rebase still wins.
- **Freeze upstream while the QA run walks** — no merges or rebases until its result
  lands (incidents: Worktrees). Absorb upstream *before* a run, never during; the run's
  own fixes are the only edits.
- **Correctness review: a fresh Opus subagent (`model: "opus"`), launched first** so
  it works while the rest of REVIEW proceeds. Its brief lists the plan's tasks and says to clear each
  one task by task, then read the whole branch for the rest. The branch was drafted one
  task at a time; the reviewer reads it whole (`git diff <lane-target>...HEAD`) in a
  clean context, with the spec, and hunts the seams between tasks as hard as the tasks
  themselves — a writer and its reader drifting apart, a helper two tasks each
  invented, a test that only passes on hand-built rows. Its brief says: before calling a
  field unwritten or a function uncalled, grep the whole repo, packages, extensions and
  scripts included, not only the directories the diff touched (a HIGH that would have
  parked secrets-report missed the writer in a browser extension). It touches nothing, runs no test that binds a port or starts a server, and returns
  findings as file:line, the failure scenario, and a severity.
  **Wonder reads the same branch at the same time**: write that brief to a file and run
  `scripts/muse.py review <worktree> <brief> <out-dir>` in the background. Neither reader
  sees the other's findings. Muse out: Opus reads alone; say so in the `result:` line, never
  wait on it.
  The driver triages every finding from both
  — adversarial reviewers over-flag by design, and a finding both reached on their own is
  the strongest lead, never proof — checks each against the code, fixes what's real, puts judgment calls
  on the card or in the `result:` line. Then one ledger row per reader: `route.py log
  repo=<repo> ship=<slug> review=opus real=<n> false=<n> only=<n> seconds=<n>` and the same
  with `review=wonder` (`out=<out-dir>` in place of `seconds`), where `only` counts the real
  findings the other reader missed.
- **Design against the storyboard is the QA run's to judge**: the script carries a step
  per frame the change built and the craft floor
  (`~/.claude/skills/impeccable/reference/craft-floor.md`), and a gap is a failure like
  any other.
- **Keep it running, for the QA run and for Pete.** Two surfaces: the branch's **preview
  links** (the contract's `preview:`, the real host, database and sign-in), and the
  worktree's **localhost** (the contract's `dev:` command, else the dev script). Pete may
  look whenever he likes; it never holds the ship. Boot the dev server detached, from the worktree root by absolute path (`cd <worktree> &&`
  first: the shell keeps the last `cd`, and one into `packs/homebody` started `npm run dev`
  in the wrong folder), never through a bounded pipe (`nohup <dev>
  > dev.log 2>&1 &`, then curl-probe — a `| head -50` has SIGPIPE'd a server mid-verify)
  and `show.sh <root> <slug> test <url>` the URL it printed (`preview` for a preview link). A feature behind an auth gate needs its test-auth path
  working on both, or it 403s and reads as broken (incidents: Backends). Never run a
  production deploy to let him review, and never tell him to "go look at the live site".
  (Non-UI change → show the demo/test output instead.)
- **Screenshots go in `<shots-root>/.ship-shots/<slug>/`, always as an absolute path**,
  because the chrome-devtools MCP writes only inside the session's workspace roots and
  resolves a relative path against the launch directory, which stops being a root once
  the session enters a worktree. `<shots-root>` is the worktree the session entered;
  on a cross-repo ship, where the session never entered one, it is the session's launch
  directory. The driver writes that absolute path into every brief that screenshots.
  `.ship-shots` is never committed (~6MB of PNGs broke a push). In the worktree,
  `stage.sh`'s `.ship-*` exclude already covers it; a cross-repo `<shots-root>` gets the same
  line with `scripts/stage.sh <shots-root> exclude`, which writes no marker. Copy anything the
  presented card references somewhere durable before teardown, or the card 404s its
  own proof (incidents: Worktrees), then delete `<shots-root>/.ship-shots/<slug>/`,
  which on a cross-repo ship is not inside the worktree teardown removes.
- **Before the QA run, check the wiring.** Run the contract's `stack:` (a ✗ is yours to
  fix first), and look at what landing will change in the backend: a change that
  **removes or renames** a backend function or table lands in two passes, first the app
  stops using it and then it goes, because landing ships the backend before the app and
  a failed app build would leave the old app calling what is gone. The same goes for any
  persisted schema an older process still writes, a local database file included: a
  column change that an old process's positional insert breaks is a one-way door, so it
  lands additive first or says so in Merge Danger.
- **TEST — ship runs its QA script, and a pass lands it.** With green gates and the
  review triaged, push, `stage.sh <root> test`, and **the driver runs the QA itself**: call
  the Skill tool with `ship:verify` (the full name: bare `verify` resolves to another skill
  and is refused), with the worktree's absolute path, the URL, the BACKEND, test-auth, IOS
  and STORYBOARD lines, the spec or plan, and the repo's checks skill
  (`.claude/skills/checks/SKILL.md`, or "none yet: write it"). The one who sees the bug fixes
  it, with the snapshot and console in front of it, then reruns the gates and commits. It
  writes the QA script, runs
  it on the chrome-devtools browser and, when the native app can see the
  change, on agent-device (`ios:` builds and installs the branch's app first; the phone is
  the default and a simulator stands in when it isn't connected, another ship holds it, or
  it answers "Locked". A locked phone parks the ship (`needs input:` "unlock iPhone PM")
  only when the change needs what a simulator can't show: push, location or other system
  prompts, the camera, real scrolling and touch feel. Otherwise walk the simulator and say
  so on the card;
  a mobile-web build may add a simulator's Safari, never the phone), fixes what fails and
  reruns, up to three fix rounds on any one failing step (a new bug each round is progress, and the `result:` line gives the count). No desktop control of the Mac. It walks the surface Pete
  would open, signed in the way he would be, with real clicks, taps and keys, never events
  dispatched from a script (a right-click menu bug got past synthetic events twice). When
  getting past sign-in on the repo's test-auth path took a trick (Clerk's bot check, say),
  write it into the contract's `test-auth:` so the next run doesn't rediscover it. It
  uses the branch's preview link when there is one (a per-push `preview:`, or an
  on-demand one ship built), else the localhost.
  **Pete asks for Codex** ("test in codex"): verify's `reference/codex.md` hands it to his
  Codex app or the headless tester instead; write `gate:codex` while his Codex app has it.
  - **`works`: write the PR body, then land** (LAND), unless the lane waits for Pete
    (below). No stop, no cue. Call the Skill tool with `mattpocock-skills:pr` and rewrite the tracker PR's
    body in its shape: Summary (the smallest visual that shows the change), Evidence
    (before/after: the QA result and its shots, the test that went green), Merge Danger
    (door and blast radius). The door is ship's call on every ship: **two-way** (a revert
    undoes it) lands now; **one-way** (it deletes or migrates data, moves money, sends
    something to people, or a revert can't undo it) waits for Pete's "merge main" like a
    money path.
  - **`broken` after three fix rounds on one step, or `unverifiable`: park.** End the turn with
    `needs input:` ("test: <feature> — couldn't prove it works: <reason>") and hand Pete
    the result and evidence. A step the run couldn't reach (a mic, a bot check, a device
    it couldn't open) makes the result partial, and partial is `unverifiable`, never a
    footnote on a landing. Three ships went to Pete with a known gap and he found it in
    minutes ("this should have been tested before you sent it").
- **Render the review card** (SELF-DIRECTED and GATED; an EXPRESS ship has none, and its
  `result:` line carries the proof shots' paths) from `reference/review-card.html` (contract below) to the
  docs home as soon as the result is in, and commit it on the branch, with the proof
  shots it shows copied beside it, before LAND's step 0: LAND removes the worktree. A
  Codex hand-off Pete watched gets none; its record is the `result:` line, the PR body,
  and the thread link. `LANDING_STATUS` says "Tested · landing on main", or what it waits
  on. `show.sh … review <file> done` the landed base's copy with the `result:` (main's, or
  for another base `git show origin/<base>:<path>` into the job's tmp, shots too) (closing the ship's other tabs),
  or `show.sh … review` the worktree's with the park. It is the
  record of what landed and the proof, not a gate.
- **What still waits for Pete's "merge main" after a pass**: a money path, a one-way
  door, and a change he said he wants to try himself. `stage.sh <root> gate:test`, post the links (and the
  card), and end the turn:
  `needs input: test <slug> — <what to try> · say "merge main"`, then the branch ·
  worktree tail. His word means take this worktree all the way, PR merge, deploy,
  cleanup (LAND). The same intent in other words counts ("push to main", "merge it",
  "ship it"); "looks good" does not land. A ship parked on `unverifiable` writes
  `gate:test` too, and the same word lands it once he has walked the gap himself.
- **While parked, keep the dev server up**; a change he asks for goes back through
  BUILD's push-and-links loop and the QA run, and lands on its pass unless the lane
  still waits for him.
- Changes Pete asks for while parked go through `superpowers:receiving-code-review` —
  verify the ask against the code, do the work, loop the changed flow back through the
  QA run. A change he asks for after landing is a new EXPRESS ship.
### 5 · LAND — on the QA pass, or Pete's "merge main"  → marker: `land`, then removed

Mechanics only: nothing is reviewed here. Merge, watch it go live, tidy up.

- **Land — `land: pr` (the default), from the MAIN CHECKOUT, teardown first** (incidents: Worktrees — both orderings that deviate have stranded ships):
  0. Pre-flight *from the worktree*: delete any test data the run kept for itself (cells-app:
     a `--keep` smoke person, `npm run prune -- --people --finish <id>`) while the worktree's
     server still answers, since the cleanup needs it and Clerk's test instance caps at 100
     people; then `stage.sh <root> land`, then `git fetch origin`; if main moved, absorb +
     re-gate by overlap (REVIEW) + push; and if the tree changed since its last full sweep
     (TEST's fix rounds run scoped), run the full gates and `smoke: branch` once here either way (`git restore next-env.d.ts` first: `next dev` rewrites it and the
     rebase refuses the dirty file), with the worktree's dev server stopped and any simulator shut first,
     since a loaded box turns a full suite's slow tests into timeouts that read as real red; run `stack:` once more; bring the `pr`-shaped body from TEST up to date with what actually
     shipped (the squash commit takes it); `gh pr ready <#>`; confirm `gh pr view <#> --json mergeable`
     says `MERGEABLE`.
  1. Return to the main checkout (`ExitWorktree({action:"keep"})`). If it answers that no
     EnterWorktree session is active, run 2–4 by absolute path against the main checkout
     instead (`wt -C <main> remove …`, `gh pr merge <#> -R <owner/repo> …`, `git -C <main>
     pull --ff-only`), then `cd <main checkout>` so the next ship's `EnterWorktree` can
     take.
  2. `wt remove feature/<slug> -f` — frees the branch for `--delete-branch`.
  3. `gh pr merge <#> --squash --delete-branch` — from the main checkout.
  4. `git pull --ff-only` (+ `git branch -D feature/<slug>` if a local branch
     lingers: a squash merge rewrites the commits, so `wt remove` and git both call the
     branch unmerged and keep it, and only `-D` takes it). Dirty main checkout (another session's work) → skip the local ff
     and run any deploy from a throwaway worktree pinned to `origin/main`.
  - A worktree ship didn't create, a session launched inside its worktree, a repo with
    no GitHub remote, or `land:` other than `pr`: `reference/rare-cases.md`, Landing variants.
  - Then `rm -f .ship-stage .ship-route.json` and `rm -f ~/.claude/ship-active/$CLAUDE_CODE_SESSION_ID`,
    **stop the review dev server**, remove the branch app `ios:` installed, by the udid and
    bundle on its IOS line (`xcrun devicectl device uninstall app --device <udid>
    <bundle>`, or `xcrun simctl uninstall <udid> <bundle>`; only that bundle, never the
    real app; a phone that isn't connected gets one line saying so), unless the line says
    `keep=yes`: a test app every branch installs over keeps the permissions Pete granted it,
    and removing it brings the prompts back; delete the build cache the line names (`dd=`,
    Xcode's DerivedData, 2 GB a branch: landed branches' copies once filled the disk), deprovision the per-branch
    backend stage 0 spun up, if any (skip it for previews and `copy`, which expire). Verify with
    `git worktree list` — zero ship-created worktrees must remain; a leftover means
    teardown failed (usually a merge run inside the worktree) — recover before
    declaring done.
- **Watch what landing deploys (the contract's `live:`).** A diff that touches nothing
  `live:` builds deploys nothing: skip the deploy and say so in the `result:` line, since a
  deploy run for it would ship main's other unreleased commits (eca-finder, 2026-10-24). Where main is production and
  the host builds it (cells-app: each touched pack's Vercel production build, Convex
  first), watch every such build to READY or ERROR, then load each live URL once (`curl -sS -o
  /dev/null -w '%{http_code}'`, and the page's text): READY with a 404 or the host's "not
  found" page is a failed deploy, not a live one (one app served NOT_FOUND on every
  route from a READY build, 2026-10-05). Report it with the live URLs; ship
  never runs a production deploy or pushes a production database by hand. Where the
  contract names a separate integration lane instead, push merged main to it — its
  dev-deploy step runs from the main checkout (shared-plane writer; incidents: Backends)
  — and hand back the lane's URL. Never make Pete run a deploy. Watch
  rules (each from a real incident — incidents: Backends): every wait has a deadline
  and a never-started check, so a watch that sees no deployment for the SHA within
  about 3 minutes says so and looks at the host's ignore step (a 25-minute wait was on
  a build Vercel never started), and nothing waits on a build the lane never makes;
  watch the deploy to conclusion (red = unfinished work, fix-forward on a new express branch); then
  run the contract's `smoke: main` once, no reruns, and treat its red the same way, telling Pete in one
  line what broke and which ships landed since the last green; watch
  the run for YOUR commit — `gh run list --commit <full sha>` (get it with
  `git -C <root> rev-parse <sha>` in its own call), full SHA only, a short one matches nothing and the watch times out silently — and
  artifact-check the lane; a red shared
  lane you didn't cause is a shared resource — check for an existing fix PR, claim
  with a draft PR first.
- **A long-running local process that serves main's code (a launchd job, a queue
  runner) picks up the change only when it restarts.** QA can't drive it before the merge,
  so TEST proves that path at data level (verify: API, CLI, script). A change no person
  can trigger (a race, a background worker, a third party mid-call) is verified at data
  level, every case on the branch's backend, plus a browser check of any screen that reads
  the result, and that is `works`, not partial. When that screen can only be reached by
  seeding model output, a render test of the real component with the result's real shape
  counts as the screen check. A change to a prompt is proven by replay: run the
  same saved model inputs through main's prompt and the branch's, a few times each, and
  quote both results (CEL-170: main showed the bug in 1 of 2, the branch in 0 of 2). After the merge,
  restart it once it is idle, never with a job in flight, which the restart would fail, and
  say so in `result:` rather than "nothing deploys". The contract's `worker:` line names
  the restart command and the idle check; a repo with such a process and no line gets one
  in this PR.
- **A separate promotion is NOT ship's job.** Where a repo promotes from an integration
  lane to production by its own script, that is Pete's human-gated ritual: never run it,
  never offer to, unless the contract's `release:` names it: then Pete's release word runs
  it. Where main is production, landing is the release and ship watches it through.
- Run RETRO, then end with a `result:` line: what shipped, one sentence, with the live
  links (or the lane's) — plus `· retro sent` when it was. Then the follow-ups
  (below), or nothing when there are none. Only a landing earns `result:`; a ship parked at TEST ends its turns
  with `needs input:`.

### 6 · RETRO — how this run used ship, sent to the maintainer  → no marker

The *running* agent never edits the skill: you're shipping a feature, and the fix belongs
to the maintainer, the session named `ship` in this plugin's repo, which fixes it now
(Pete, 2026-10-05; no GitHub issues). Look back at this run, from the transcript, not
memory, at how you used ship, through mattpocock's `retro` lens turned on ship itself:
- **steering**: a ship rule that was unclear, contradicted another, didn't change what
  you did, or that you broke and why; and every time Pete had to correct the pipeline or
  step in where ship should have carried on;
- **automated checks**: a mistake one of ship's scripts (`stage.sh`, `codex-handoff.py`,
  `route.py`, the pre-flight) could have caught, or a check that misfired;
- **information access**: something ship never handed you or the QA run (a URL, a
  log, a credential path, a device state) that cost a round;
- **navigation**: a rule you had to hunt for, or found too late;
- **tool economy**: a step ship made expensive (a slow wait, a rerun, a long poll) that a
  script or a narrower command would replace.

Then `ListAgents` and `SendMessage` the peer named `ship` (never this session itself):
`ship retro from <repo>/<slug>:` and each finding as one line with what happened, the
gap, and the fix you'd make, the evidence (a file:line, a turn, a QA step)
named so the maintainer can check it. A clean run sends `ship retro from <repo>/<slug>:
clean`. Fire and forget: never wait on a reply. No `ship` session live: write the same
text to `~/.claude/ship-retro/<date>-<repo>-<slug>.md`, which the maintainer reads when
it starts. Never invent a lesson; a finding needs its evidence.

**The repo gets a retro too.** Look back at the run for what the repo's own environment
should have caught (the lens of mattpocock's `retro`):
- **a mistake a check could have caught** (a lint rule, a type, a test, a pre-commit or
  CI job; a repo with no guardrail at all is a finding in itself). A mechanical rule gets
  a check, never a line in a standards doc;
- **information the run lacked** (a dev server log nobody tailed, a dashboard it couldn't
  read, a crash that surfaced as "Connecting…");
- **navigation**: a file or dependency the run took long to find, which a pointer in the
  repo's `CLAUDE.md` or docs home would have saved;
- **an expensive tool call** that a script or a narrower command would replace.

Each real one is a follow-up (below), with what to add and where: the run has landed,
so a guardrail or pointer is its own small ship, never a commit slipped onto main. A gap the repo already knows about (the same finding in
an earlier run's list) is not news; say nothing.

Don't gate `result:` on any of this.

## The storyboard contract (GATE 1 artifact)

Render `reference/storyboard.html`, an artboard board: the page is the frames, laid out.

- **Flows** — one row per story, artboards left to right in the order a person meets
  them, arrows drawn by the template. Together the rows tell the whole flow: the screen
  the person comes from, every step of the new part, the screen they land on. A screen
  that doesn't change is drawn as it is, with `data-same`, so its code goes grey. Every
  state gets its own artboard, named for the
  state ("Typing a zip", "No results"); a phone and a desktop of one screen sit in the
  same board at true relative size (`data-w`/`data-h` are the device's: 390×844,
  1280×800). The board opens zoomed to fit, and clicking an artboard's name shows it
  alone at full size.
- **Artboards** — live HTML at ship size in the product's own stylesheet: a repo that
  ships one links it by relative path from the docs home (cells: the three grok sheets
  under `web/public/`); anything else inlines the tokens it uses. Each is authored as a
  `<template>` and mounted into its own iframe, so the product's sheet styles the frame
  and nothing else, `:root` tokens resolve, and a hover, an open menu or a tab works
  where the feature has one. Never wired together, and never a "try it" app above the
  board (Pete, 2026-10-08 and 2026-10-12).
- **Codes** — every artboard's `data-mount` is its code: the row's letter (A, B, C… in
  page order, an options row included) and its place in the row (A1, A2…). The template
  draws the code as the frame's tag and its anchor (`#A3`), so the plan and briefs cite
  the same name Pete uses. Codes are kept for good: a killed frame's code is never
  reused, and a frame added mid-row takes the row's next number, not its position. These
  are the board's labels around the frames, never inside one: the craft floor's ban on
  numbered section labels is about the product's own screens.
- **Options** — a direction in play is an options row of sibling artboards with codes of
  their own (D1 / D2 / D3), no arrows.
- **Where the product's sheet doesn't decide, the model's own defaults are out**: a
  cream or off-white page, an italic accent word in a headline, pill-shaped buttons.
  The craft floor already bans numbered section labels and monospace as costume.
- **Captions** — one line under each artboard: what is new in it.
- **The questions** — the round's grilling (DISCOVER): every question open now, Q1,
  Q2…, each naming its frames and carrying the pick you'd make, worded so "yes" takes
  it. The ones a designer would bring, never a recommendation dressed as a question.
  They live on the page; chat never repeats them.
- **For the record** — one collapsed block at the foot: recon, consults, reuse audit,
  surface liveness. Never above a frame.

No TL;DR, no research sections, no scope contract, no plan: the page is the artboards.

## The plan card contract (GATE 2 artifact)

Render `reference/go-card.html` filled with the meta only — one screen (a
`16-implementation-plan` boiled down to what he says go on):

- **The storyboard** — the locked page embedded scaled-down in one glance, linked.
- **What gets built** — the punch list: one plain-English line per piece of work, in
  build order, five to twelve lines. Not files, not tasks numbered for a machine.
- **Ponytail's cut-list** — what was dropped, and why.
- **Pete's 1–3 calls** — each a PM tradeoff *with your recommendation*. Zero calls is
  fine, and then the card does not stop.
- **Risk** — one line.
- **Go** — one line.

It is the *only* thing Pete reads before a build starts, and his go is needed only
when it asks him something. The execution plan is written
after his go and he never reads it.

## The review card (every SELF-DIRECTED and GATED pass and park, but a watched Codex hand-off)

Render `reference/review-card.html` filled with the meta only — PM-framed, one screen; a
`17-pr-writeup` for a PM, never a file tour. Pete reviews *this*, not the diff:

- **What you got** — plain-English bullets of what now works.
- **Proof it works** — the QA run's captioned screenshot storyboard (start →
  action → success, browser and phone) with the `works` verdict on top. (Non-visual →
  demo/test output.)
- **Already checked for you** — gates green, the QA script walked end-to-end, any committed e2e spec (name it); what was NOT touched (schema / money /
  public surfaces).
- **Flagged** — taste notes, if any. Reports, not work: one Pete wants changed becomes
  a follow-up.
- **Only you can confirm** — the 1–2 things that need his eye, on the preview links or
  the open localhost.
- **What we should do next** — the follow-ups (below). Most rounds have none: omit the
  section entirely; never pad it.
- **Where it is** — the live links landing deployed (the contract's `live:`), or the
  preview links and localhost when the ship parked. The verdict line (`LANDING_STATUS`)
  says which: "Landed on main" with the live URL, or what it waits on. The tracker PR
  link is there for the record, but he shouldn't need it.

## Follow-ups — what we should do next

A run throws off work that isn't this round's job: an idea outside the spec, a guardrail
or pointer from the repo's retro, a taste note, a bug it saw in passing. Keep a running
list of the ones worth doing (no scratch file; you're one continuous run). A follow-up is
OUTSIDE the spec's scope, never a specced surface you chose not to build; this is not a
loophole around the scope law. Never invent one, and never gate the merge on this.

Sort each one, and give it one plain line on why it's worth doing (Talking to Pete):
- **Quick ship**: the whole change is visible, there's no taste call, and it fits one
  sitting, the size of EXPRESS. Pete says "ship <n>" and it runs as an EXPRESS ship.
- **Ticket**, placed by what it needs, in the column the repo's `board:` gives that meaning
  (cells-app: Ready, Backlog, Icebox):
  - **ready to build**: an agent can build, prove and land it alone, the cause or the shape
    already known, no taste call. On cells-app it goes in Ready, which `/groom` starts from;
  - **needs Pete**: his OK, a design call, a product question, a money path. On cells-app,
    Backlog, with the ask written on it;
  - **someday**: a nice-to-have. On cells-app, Icebox.

  Never a column that means work in flight (cells-app's Building): that is a live session's.

  Pete says "file them" (or names which) and each lands in its column with the why
  written on it and a link back to this PR. A repo with no `board:` gets the list only.

They go on the review card under "What we should do next", and when there is no card,
under the `result:` line as a numbered list. Ship fixes found in its own RETRO go to the
maintainer, never on this list.

## Gate signals — how a parked ship reaches Pete

At a gate, four things fire so Pete notices whether he's watching or away:

1. **Status line** — the `gate:N` marker shows `✋ <slug> — storyboard?/go?` in bold amber.
   TEST's `test` marker is not a gate: it shows `🧪 <slug> — testing`. A Codex
   hand-off Pete asked for writes `gate:codex`: `✋ <slug> — test it with Codex`. A ship that parks for
   Pete writes `gate:test`: `✋ <slug> — try it, then merge main?`.
2. **FleetView bucket** — the turn ends with a `needs input:` line → the row jumps to
   *awaiting input*.
3. **Desktop notification** — the gate Stop-hook fires a Ghostty notification
   (`<slug> → GATE N`, `<slug> → test it with Codex`, or `<slug> → try it, then merge main?`). Gates are rare, so this
   is never noisy.
4. **Gate buttons** — the mod in `hooks/register.ts` draws buttons above the prompt that a
   bare digit presses: `1` raises the page show.sh last opened for the gate, `2` sends
   "lock it" or "go" as Pete's words. It reads `.ship-stage` and `.ship-shown/`, so
   `stage.sh` and `show.sh` are all a run calls; a run writes no button text of its own.

## Talking to Pete — every word he reads

Pete runs several ships at once and reads each message cold, coming back from other work
with this run forgotten. He is sharp; he is also tired of switching. Write for that
(Pete, 2026-10-19). This covers everything he reads: stage updates, `needs input:` and
`result:` lines, storyboard captions and questions, the plan and review cards, and the
PR body's first lines. Messages between sessions (retros, peer replies) are exempt.

- **Open with what this is**: the repo and the feature in his words, with its card key
  ("cells-app, the flaky-tests fix (CEL-74):"), before anything else.
- **Lead with what it means for him**: what now works, or the one call he has to make.
  What the agents did comes after, if at all.
- **Ship's own words stay inside ship.** Say the plain thing instead of: driver (the main
  session), lane, tier, pool, marker, gate, absorb, BACKEND, ledger, route, sweep,
  pre-flight, fan-out, brief. A word the run coined (a function name, a made-up label)
  appears only if Pete used it first, or with a few words saying what it is.
- **The week test.** Before posting, reread it as Pete a week from now with the run
  forgotten. Every noun must still make sense; cut or explain the ones that don't, then
  cut again.
- **A call he has to make** recaps the decision in one line and gives ship's pick, so "yes"
  is a complete answer.
- **Who did it:** "we" for shared work and when unsure, "I" for what the agent did on its
  own, "you" for what is his to do.

The `needs input:` and `result:` prefixes and the branch · worktree tail stay as they are
(FleetView reads them); the words between them follow this section.

## FleetView narration contract

The dashboard reflects the session — make it a ship board:

- **Name** the session `ship:<slug>` at spawn (Pete types it, or dockmaster passes
  `--name`). A running session can't rename itself reliably.
- **Status lines ride with the next tool call** (`🔨 build 4/5 · <slug>`,
  `📐 planning · <slug>`): status-of-work, not an echo of the last tool call. A bare
  status line ends a turn only while you wait on background work (Engines: how a
  turn ends).
- **At a gate, and when TEST parks for Pete, the closing line starts `needs input:`** →
  *awaiting input*.
  At landing, it starts `result:` → *completed*. Mid-work narration keeps it in *working*.
- **End `needs input:` and `result:` lines with `branch <branch> · worktree <path>`**
  (`detached@<short-sha>` until a branch exists) — Pete must always know which checkout
  he's looking at; it's what catches the cross-repo case.

## What this skill deliberately does NOT do — including two standing skill overrides

**This pipeline overrides the superpowers defaults on its autonomous lanes** (a
deliberate ruling, not an oversight): grilling runs only in DISCOVER (GATED / `design`),
EXPRESS and SELF-DIRECTED skip it, and `superpowers:brainstorming` never runs, since its
one-question turns, sizing and visual companion repeat ship's own; and there is no strict TDD by
default — tests are a build deliverable, the pre-merge gate is the backstop, and
test-first (`superpowers:test-driven-development`) is reserved for money paths.

Also not ship's job: arbitrary phasing (the scope law); `executing-plans`
(checkpoint-heavy — the opposite of hands-off); manual git worktree management (`wt`
owns birth-to-death in Claude Code; Codex Desktop owns its own); landing without the
QA run's pass or Pete's "merge main" (except `land: auto`); running a production deploy or pushing a production
database by hand (the host's build does it); a separate promotion script, which is Pete's
human-gated ritual, never ship's to run, gate, or offer.
