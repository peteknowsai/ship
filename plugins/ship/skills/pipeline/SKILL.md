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
marker flip is how Pete *sees* ship engage.

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
  `result:` line. A dab of `ponytail` (smallest diff), and `impeccable` for anything
  visual. The first Pete hears of it is the links.
- **SELF-DIRECTED — real work with no taste question in it.** Write whatever
  machine-facing spec/plan *you* need to build it well, then build, run the full REVIEW
  machinery (the fresh-eyes review, then TEST's QA run — its `works` is the bar
  for landing), land, `result:`. No stops — the artifacts are for the record, not
  approval.
- **GATED — Pete's taste or direction is genuinely in play.** A new user-facing
  surface, visual identity, a product tradeoff, ambiguous scope, a money path — the
  gated pipeline below.

**The gate test is never size — it's whether Pete's answer would change what gets
built** (or the change is risky/irreversible). If his input wouldn't change the outcome,
don't stop. Every lane lands only on green gates and the QA run's `works`. A
money path, a one-way door (the PR body's Merge Danger call, TEST below), and a change
Pete said he wants to try himself also wait for his "merge main" after the pass.
Mid-flight, promote the moment taste or direction appears (park, write the spec from
what you've learned, present GATE 1); size alone moves EXPRESS → SELF-DIRECTED, never to
a gate. Never use an autonomous lane to slip a taste call past Pete.

## Engines

**Opus 5.5 drives every stage.** It owns design, briefs, triage, gates, git, and the
final say. Every model runs at high effort: the driver, every subagent, and every
codex run. Never xhigh or max, and never medium to save time.

**Fable 5.1 is the second opinion in two places**: the plan review at the end of PLAN
and REVIEW's correctness pass. It also builds a band of BUILD tasks.

**BUILD routes by difficulty.** Once the execution plan is written and reviewed, run
`scripts/route.py plan <plan.md>` from this skill's directory. It asks Jev, TypeSafe's
classifier, to score every task's difficulty in one request (well under a second, a
fraction of a cent) and ranks the routable tasks:

| Rank among the plan's routable tasks | Engine | How it runs |
|---|---|---|
| easier half (`fable`) | Fable 5.1 | harness subagent, `model: "fable"`, in the background |
| harder half (`opus`) | Opus 5.5 | harness subagent, `model: "opus"`, in the background |

The split is an experiment (Pete, 2026-10-05), and the ledger decides what stays.
`route.py` holds it in `LADDER`. Codex builds nothing: its sandbox made the driver
rerun the tests on most of its tasks. It tests only when Pete asks (TEST).

A task headed `(driver)` or `(inline)` is never ranked; the driver writes it. An all-inline
plan still runs `route.py plan`, which ranks nothing and sets the marker, and each task
still logs with `engine=driver`, which counts it done. When the
JSON's `fallback` is set, Jev was unreachable and every task went to Fable: say so in
the `result:` line and carry on, because the router never blocks a build. The driver may
override one pick for a concrete reason, such as a file an Opus lane already holds, and
logs the override in the ledger's `note`.

**Every engine gets the same brief and the same rules** (the standing boilerplate in
BUILD): the named files only, never commit, never `git reset/checkout/stash`, end with
STATUS, TESTS, CONCERNS. A harness subagent gets the worktree's absolute path and works
only there.

**The ledger judges the split.** When the driver accepts a task's diff, it appends the
outcome:

```bash
route.py log repo=<repo> ship=<slug> task=<n> engine=<engine> \
  seconds=<wall time> fix_rounds=<n> gates_first_pass=<true|false> verdict=<clean|fixed|redone>
```

Run it from the worktree: it fills the task's score and the engine the router picked
from the saved route, so an override shows as `engine` differing from `routed`. Seconds
come from the run itself (the task notification's duration), and a number you don't have is left out, never estimated: a
third of the first 81 rows were round-number guesses.

`route.py report` prints the table by engine and difficulty band. Pete reads it after
the first build on this ladder and moves the cuts.

**Codex runs only when Pete asks it to test** ("test in codex"), through `ship:verify`'s
`reference/codex.md`: `scripts/codex-handoff.py` for a hand-off to his Codex app,
`scripts/astra.sh test` headless. Never a hand-typed `codex exec`.

**The driver writes inline anything under one file and ~50 lines**: config, glue
between two tasks, a test tweak, a small fix from triage. Mark those tasks `(inline)`
in the plan so the router skips them. Skill and agent prose and design taste never
route either. Recon, expert consults and review fan-outs go
to Opus 5.5 harness subagents (the Agent tool), with the chrome-devtools MCP for
anything in a browser. Never `claude -p` from inside a session. Nothing runs
on Sonnet.

**The driver owns the envelope**, whoever drafts: it writes the brief (exact files,
signatures, test cases, constraints; a vague brief burns the savings in fix rounds;
call the Skill tool with `writing-for-agents` once per run before the first brief),
reviews the returned diff and runs the gates before anything is committed (never trust
a "tests pass" claim from a worker), and owns git entirely. One writer per tree at a
time: serialize, or give each lane its own sub-worktree.

**Browser work runs on the chrome-devtools MCP** (`mcp__chrome-devtools__*`: headless,
a fresh isolated profile per session, so parallel walks never collide and no window
opens on Pete's screen): the pre-flight check, TEST's QA run, live-product grounding. A subagent
loads those tools with one ToolSearch call before its first step. A surface that needs
Pete's real login and has no test-auth path in the repo is his: hand it off with
`needs input:`. A reference product behind his login (muse.ai) is his too: ask for
screenshots of the states you need, and use the `mcp__claude-in-chrome__*` tools only
when he asks, since they drive his own Chrome. A subagent drives the
browser against the running app and reports what it saw; a coding worker never does.

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

**Pete's stack:** his global instructions carry the standing stack — Eve · Vercel ·
Convex · Clerk · Stripe · Next (Cloudflare keeps DNS, R2 and the Workers already running). Never re-ask it. The repo's own `CLAUDE.md` /
`AGENTS.md` overrides it where it diverges.
Escalate a library choice only when it's both architectural *and* outside the canon.

## The ship contract — what a repo tells ship

A repo declares how ship runs it in its `CLAUDE.md` / `AGENTS.md`, as a short list of
facts. The workflow is ship's; the contract only says what this repo's commands are.
Every key is optional, and the default is what a repo with no contract gets:

- **`gates:`** the commands that must pass: tests, typecheck, production build. Default:
  whatever you can find.
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
- **`backend:`** `shared-dev` (the default): previews and localhost use the app's dev
  database, ship never rewrites an env file, and it says so on the card, or in the `result:` line, when a
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
  that bear on the idea, whatever their age (Jev scores every active one; if Jev is
  down it prints the newest instead and says so). Treat them as settled calls with
  their rationale. Don't re-ask Pete a settled question; reversing one is allowed, but
  say so explicitly.
- **When a gate (or Pete mid-run) resolves a durable call** — design direction, scope
  cut, architecture or tool choice — log it:
  `decisions.py log '{"decision":"…","rationale":"…","source":"user"}'`. A reversal is
  `decisions.py supersede <id> '<json>'`, with the id `recent` prints. Turn-level edits
  and phrasing tweaks are never logged — a noisy store is worse than none.

## The pipeline — create a todo for each stage

Each stage writes its marker with `scripts/stage.sh <worktree> <stage>` (the status
line and the FleetView row read `.ship-stage`), and every stage flip posts Pete one
line: the goal, the stage, what's next. Post it again after a compaction or a side job.
Five runs had him asking "where are we?" mid-flight.

**Shell inside a worktree session.** The harness refuses a command it can't tell stays
in the worktree: `$(git …)` substitutions, `cd <dir> && git …`, loops or heredocs that
name git, and read-only commands it misparses (a path segment named `source`, a zsh
`echo ==`, a `for` loop over `sed`, a heredoc that only writes files). Read and search
with the Read and Grep tools when the session has them, which it never checks; else use
`git -C <path>`, one plain command per call, and put anything multi-step in a script
file under the job's tmp directory. A command on the main checkout (`cd <main> && git`,
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

**Never stack on a branch that hasn't landed.** Asked to build on top of another
ship's branch, branch off main anyway, cherry-pick only the commits you need from it,
and open the tracker PR against main. Its own rebase later finds those commits already
there. A PR based on the other branch strands at landing whenever that branch
hasn't landed first (incidents: Worktrees).

```
git fetch origin
wt switch --create feature/<slug> --base origin/<base> --no-cd --format=json -y
```
(`origin/<base>`, the base branch resolved above, because a stale local copy has cost a
rebase and reinstall), then enter
the path from the JSON. A second ship in the same session calls
`ExitWorktree({action:"keep"})` before `EnterWorktree` on the new path. In the session's primary repo, `EnterWorktree({path})`
is required: the status line and FleetView read the session's cwd,
so a run that keeps working by absolute path while parked on main is invisible to Pete
even though `.ship-stage` is being written faithfully in the worktree (he has had to ask
mid-BUILD whether a run forked at all). Absolute-path driving is the *cross-repo*
fallback only, where `EnterWorktree` can't take. Self-heal: notice mid-pipeline that
the session cwd isn't the worktree → `EnterWorktree({path})` right then; it works fine
after the fact. `--no-cd` is load-bearing. A `.config/wt.toml` auto-provisions
gitignored runtime files. Run `scripts/stage.sh <root> discover`: it writes the marker
and adds `.ship-*` to the repo's `info/exclude`, since `git add -A` sweeps the marker
into commits otherwise (incidents: Worktrees). Never build on main.

- **Push the branch at once** (`git push -u origin feature/<slug>`), and open the
  **tracker PR** as a draft with the first commit (`gh pr create --draft --base main
  --fill`; GitHub refuses a PR with no commits). Its body is the one-line why and the
  preview links, refreshed as they change. It is GitHub's record of what is in flight and,
  once squashed, of what shipped; it is never a review step. `land: direct` opens none.
- **Backend:** `shared-dev` (the default) → build against the app's dev database and touch
  no env file. `per-branch` → provision the branch's database preview now; a worktree
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
  incidents: Worktrees). Never touch one with uncommitted work.

### 1 · DISCOVER — Pete's taste, up front  → marker: `discover`, then `gate:1`

- **Resurface decision memory first** (see Decision memory) — settled calls constrain
  the brainstorm; don't re-litigate them inside it.
- Invoke `superpowers:brainstorming`. PM-framed, one question at a time.
- **Recon runs on a subagent, synthesis stays with the driver.** Codebase
  evidence-gathering dispatches as a read-only Opus subagent (report findings, edit
  nothing).
  The recon brief includes a reuse audit: for every core noun the feature
  introduces, grep the whole repo — data layer included — for existing infra before the
  plan treats it as new (incidents: Design). When the design lands on an *existing*
  surface, it also classifies that surface's liveness — current design system?
  reachable from primary nav? touched by recent commits? — because a deprecated page
  serves happily (incidents: Design). The spec names the chosen surface explicitly.
- **Bug-shaped requests get an empirical root-cause check** — reproduce the failure or
  read the runtime evidence; never spec a fix from a hypothesis (incidents: Design).
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
  image comps (impeccable 4.5, 2026-10-05). Use `/image-gen` freely for imagery inside a frame.
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
     `reference/storyboard.html` (contract below). Each frame is a live HTML mockup of
     one screen or state at the size it ships — the window, not a cropped component:
     the sidebar, the titlebar, the new thing in place — drawn in the product's own
     stylesheet and tokens, and working: the storyboard is a little web app Pete can
     click through, not a set of pictures. Where a direction
     is genuinely open, draw it as two or three frames of the same screen side by side
     (`02-exploration-visual-designs`), never as prose options. The words on the page
     are captions: one line under each frame saying what is new in it, and the two or
     three questions a designer would actually bring ("went denser on B, unsure about
     the nav, which tone?"). Recon, consults and the reuse audit go in one collapsed
     block at the foot, for the record; they never sit above a frame. No TL;DR essay,
     no section per research finding, no fait accompli. `stage.sh <root> gate:1`, commit,
     fire the gate notification, `open` the storyboard, end the turn with `needs input:`
     ("storyboard round 1 — reactions?"). **HARD STOP** — every round is one. It is a
     local HTML file in his browser, never a Claude artifact (Pete, 2026-10-08).
  2. **Rounds.** Pete reacts; redraw the frames in place — minutes per round, not a
     re-spec. A frame he killed is deleted, never greyed out. Re-`open`, end the turn
     with `needs input:` again. Push back where taste warrants it: a designer with no
     opinions is a renderer. Loop until he locks it ("this is it", "lock it", "yes").
  3. **Lock = GATE 1.** Commit the storyboard as it stands: it is the design of
     record from here on. Every frame left in it ships; nothing not in it does. Log
     the direction to decision memory, then straight into PLAN.
  Pen (the Pencil app) is no longer the default. When Pete asks to take a frame into
  pen, put it there, let him iterate, and harvest the result back into the frame
  before the lock; the storyboard stays the single design of record either way.
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
- **Consult a domain expert again only for a question the plan raises and the
  storyboard didn't settle** — schema shape, index or migration order, an API's real
  constraint, an auth boundary. Same rules as DISCOVER's consult: harness subagent, a
  question not a task, the driver decides. On SELF-DIRECTED — which skips DISCOVER's
  storyboard — this is the lane's only consult, so a stack question that would change
  the plan gets asked here or nowhere.
- **Render the plan card** from `reference/go-card.html` (contract below): the locked
  storyboard in one glance, then what gets built as a punch list in plain English
  (one line per piece of work, in build order), the cut list, his calls with your
  recommendation, the risk line, and "go". Commit it, `open` it.
- **Calls on the card are plain language, and only the ones that change what he gets.**
  Each says what he'd see either way. A technical choice where you have a clear pick is
  yours: take it and log it. Never offer to phase the work.
- **GATE 2 is his go when the card carries a call** (Two principles). `stage.sh <root>
  gate:2`, fire the gate notification, end the turn with `needs input:` ("go?"). **HARD
  STOP.** A card with no call is not a stop: `open` it, post one line ("plan card: no
  calls, building"), write no `gate:2` marker, and go straight on as if he had said go. SELF-DIRECTED renders no
  card and stops for nobody.
- **His go → spec it out.** Only now does the machine-facing writing happen: invoke
  `superpowers:writing-plans` for ONE execution plan covering the entire
  storyboard — never sliced into phases — saved to the docs home
  (`specs/plans/YYYY-MM-DD-<slug>.md`). It carries everything a frame can't: copy as
  data, routes, behaviour, states, a11y, test cases, and for each UI task the frame it
  must match (`<storyboard>.html#<frame-id>`, never a prose description of the frame).
  Pete never reads it. A change he asks for after go is an express round, not a
  re-plan. Each task names its files, the signatures it adds or changes, and its
  test cases — brief-grade, so the BUILD brief is a paste plus deviations. Every
  4-minute first-pass-clean dispatch in the ledger had this; every 25-minute one
  left the worker to find the shape itself.
- **A task that computes from rows another code path writes gets one end-to-end test
  through the real writer** — not just unit tests over hand-built rows, which pass while
  the production writers produce garbage (incidents: Design).
- **Headings are the router's input.** Every task is a `### Task N: <name>` heading, and
  a task the driver writes itself says `(inline)` or `(driver)` in its heading.
- **Fable reviews the plan before BUILD, on every lane that has one.** A fresh
  subagent (`model: "fable"`) reads the storyboard or spec, the execution plan and the
  repo's ship contract, edits nothing, and returns findings as task, problem, fix: a
  missing task, a wrong file, a test that cannot fail, an order that breaks, an
  `(inline)` task that is not small, a seam two tasks each assume the other owns. The
  driver triages and edits the plan. Nothing goes back to Pete unless it changes what
  gets built. Then `route.py plan` (Engines). No task starts before the review lands,
  `(inline)` ones included, unless the plan names it a spike: two runs built early and
  rewrote what the review then flagged.

### 3 · BUILD — automatic  → marker: `build:N:M` (N done of M tasks)

- `route.py plan` already moved the marker to `build:0:<M>`, and each `route.py log`
  counts one task done, so `(inline)` and `(driver)` tasks log too, with
  `engine=driver`. A run that skipped the router writes `build:0:<M>` itself before the
  first dispatch; a status line still on `plan` mid-BUILD is the tell. Build all M tasks in one session; commit
  each task on the branch as it lands, land only when the whole plan is built.
- **Push at every milestone, and hand Pete the links.** After a task (or a lane's merge)
  is committed, push the branch. When the repo has a per-push `preview:`, run it once the
  builds settle, never blocking the next dispatch on them, and post one line per app with
  what changed and what to try; with an on-demand one, post the localhost. Pete works solo and tests mid-flight, so the links always show
  the worktree's latest. A build that failed is yours to fix before you post.
- Invoke `superpowers:subagent-driven-development` (the driver drives) and send each
  task to the engine `route.py plan` picked (Engines), in the background; `(inline)`
  and `(driver)` tasks the driver writes itself. The driver owns the brief, the diff
  review, the gates, the ledger line, and git. One writer per tree at a time, which
  is why fan-out means sub-worktrees, below.
- **Fan out by file overlap, before the first dispatch.** The plan names each task's
  files. Group tasks that share a file; every group is a lane. Each lane past the
  first gets its own sub-worktree off the branch (`git worktree add <dir> -b
  <branch>-<lane> <branch>`) and its own worker, all launched together; a lane's
  tasks run in plan order inside it, each on its routed engine. The driver merges lanes back in plan order and
  runs the gates once after each merge, then removes that lane: `git -C <worktree>
  worktree remove <lane dir>` and `git -C <worktree> branch -D <branch>-<lane>`, as two
  calls. If the harness refuses, leave it; `wt-sweep` removes a lane whose changes are
  all in its parent. Serial is only for tasks that share files.
  Three disjoint tasks run serially cost the sum of their times; fanned out, the
  slowest one's.
- **A lane worktree has no installs, and a borrowed one must be excluded before the
  first commit.** A fresh `git worktree add` carries no `node_modules` (or `.venv`,
  `vendor`, `.build`). Either run the repo's frozen-lockfile install in the lane, or
  symlink the main worktree's installs in. If you symlink, write each link's path to
  the `info/exclude` that `stage.sh` already wrote `.ship-*` to (its path is `git -C
  <root> rev-parse --git-common-dir` plus `/info/exclude`, run as its own call): a `.gitignore` line like `node_modules/` ignores a directory and not a link, so
  `git add -A` commits it and the merge swaps the real install for a link to itself
  (incidents: Worktrees). Commit lanes with the links excluded, and after the last lane
  merges confirm the main worktree's install is still a directory before trusting a red
  gate.
- **A task's check is the diff and the gates, nothing else.** Read the diff, run
  tsc/tests/lint, commit. Nobody drives the app or CLI per task: the pre-flight is once
  at the end of BUILD, and the QA run is TEST's. A reviewer hand-driving
  the product per task cost 20 minutes a task and found nothing the gates missed.
- **Standing brief boilerplate** (each line from a burned run, incidents: Dispatch):
  one task per brief, with the plan's complete code pasted in, the exact test commands
  and the files it may touch; "do it, do not propose", because Astra stops and
  proposes on an open ask; test files whose assertions the planned change invalidates are always in
  scope, allowlist or not; the final message is STATUS, TESTS, CONCERNS, and a longer
  report goes in a file inside the worktree; the worker never commits and never
  runs `git reset/checkout/stash`. A
  repo whose rules load by path (`.claude/rules/`, a `scripts/rules-for.py`) gets those
  rule files named in every brief, because a subagent only sees them if told.
- **Never add scope to a running worker by message.** New findings wait for its report
  and go out as the next fix round, and the report is checked against every message
  it was sent. Two workers finished before reading items sent mid-run, and both cost a
  redo.
- **A cut after go is said out loud.** Any plan item dropped, narrowed or swapped after
  Pete's go, including a model or tool that differs from the reference, goes in the
  next message and the `result:` line. One run dropped a settings dropdown Pete had
  asked for and he found out by asking "this is all done?".
- **A fix round goes back to the same worker** with the findings as the brief, so the
  context is already paid for: `SendMessage` to the same subagent. A fresh run for the same task starts cold and re-reads
  the tree. Two wrong diffs on one task move it one rung up the ladder, and the ledger
  records `verdict=redone`.
- **A quiet run never blocks the build.** The harness wakes the driver when a subagent
  returns, so silence is not a signal to chase. If a lane's work is visibly in the tree and no report has
  landed, self-serve: review the diff and run the gates yourself. Dead air on the
  *reporting* path has stalled a real ship twice in one run; the work was already done
  both times.
- **Small edits don't fan out.** A lane whose tasks are all sub-threshold is the
  driver's, inline, while the dispatched lanes run. Review fans out regardless of
  build size: several verifiers on one diff beats one.
- `ponytail` posture; `superpowers:verification-before-completion` before claiming any
  task done — actually run it; `superpowers:systematic-debugging` on a red test.
- **UI-writing briefs carry the storyboard frame and the craft floor** — every
  dispatch that writes UI names the frame to match
  (`specs/designs/<storyboard>.html#<frame-id>`; the worker reads the frame's markup
  and CSS, which is why a frame beats a PNG), and — since a subagent does not get the
  impeccable hook — tells it to read
  `~/.claude/skills/impeccable/reference/craft-floor.md` and honor its checks and bans,
  plus the three model defaults the storyboard contract bans.
- **Before BUILD is done, a light pre-flight, so the QA run never opens a broken
  page.** Run the gates and, for a framework with its own production build, that build;
  boot the app and load each surface the feature touches once in the chrome-devtools
  browser: it renders, its first step works, the console is clean. Not a walk-through:
  that is TEST's QA run.
  A change with UI also runs impeccable's detector on the UI files it touched,
  `~/.claude/skills/impeccable/scripts/impeccable detect --no-advisory <files>` (exit
  0 clean, 2 findings on stderr, 1 a file it couldn't read): fix each finding, or waive a
  deliberate one in place with its `impeccable-disable-line <rule> -- <why>` comment.
  It is free and mechanical, so the QA run never spends a round on a craft-floor miss.
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
  worktree (rebase, or merge if unsafe), re-run the gates, then dispatch review — and
  re-sync right before landing if main moved again (incidents: Worktrees). On
  `backend: per-branch`, if the absorbed commits touched `convex/`, re-deploy the preview before any further
  verification — function skew is invisible to tsc, vitest and the production build,
  and has hard-crashed a page after a green rebase (incidents: Backends).
- **Freeze upstream while the QA run walks** — no merges or rebases until its result
  lands (incidents: Worktrees). Absorb upstream *before* a run, never during; the run's
  own fixes are the only edits.
- **Correctness review: a fresh Fable subagent (`model: "fable"`), launched first** so
  it works while the rest of REVIEW proceeds. When Fable built some tasks, it still
  reviews: it reads the whole branch cold, which no single task's writer did. The branch was drafted one
  task at a time; the reviewer reads it whole (`git diff <lane-target>...HEAD`) in a
  clean context, with the spec, and hunts the seams between tasks as hard as the tasks
  themselves — a writer and its reader drifting apart, a helper two tasks each
  invented, a test that only passes on hand-built rows. Its brief says: before calling a
  field unwritten or a function uncalled, grep the whole repo, packages, extensions and
  scripts included, not only the directories the diff touched (a HIGH that would have
  parked secrets-report missed the writer in a browser extension). It touches nothing and returns
  findings as file:line, the failure scenario, and a severity. The driver triages every finding
  — adversarial reviewers over-flag by design — fixes what's real, puts judgment calls
  on the card or in the `result:` line. The high-value fan-out is here: several verifiers on one diff beats one.
- **Design against the storyboard is the QA run's to judge**: the script carries a step
  per frame the change built and the craft floor
  (`~/.claude/skills/impeccable/reference/craft-floor.md`), and a gap is a failure like
  any other.
- **Keep it running, for the QA run and for Pete.** Two surfaces: the branch's **preview
  links** (the contract's `preview:`, the real host, database and sign-in), and the
  worktree's **localhost** (the contract's `dev:` command, else the dev script). Pete may
  look whenever he likes; it never holds the ship. Boot the dev server detached, never through a bounded pipe (`nohup <dev>
  > dev.log 2>&1 &`, then curl-probe — a `| head -50` has SIGPIPE'd a server mid-verify)
  and `open` the URL it printed. A feature behind an auth gate needs its test-auth path
  working on both, or it 403s and reads as broken (incidents: Backends). Never run a
  production deploy to let him review, and never tell him to "go look at the live site".
  (Non-UI change → show the demo/test output instead.)
- **Screenshots go in `<shots-root>/.ship-shots/<slug>/`, always as an absolute path**,
  because the chrome-devtools MCP writes only inside the session's workspace roots and
  resolves a relative path against the launch directory, which stops being a root once
  the session enters a worktree. `<shots-root>` is the worktree the session entered;
  on a cross-repo ship, where the session never entered one, it is the session's launch
  directory. The driver writes that absolute path into every brief that screenshots.
  Exclude `.ship-shots` in `<shots-root>`'s repo `info/exclude` the way `.ship-stage`
  is, since it is never committed (~6MB of PNGs broke a push). Copy anything the
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
  review triaged, push, `stage.sh <root> test`, and invoke `ship:verify` (the full name:
  bare `verify` resolves to another skill and is refused). It writes the QA script, runs
  it in this session on the chrome-devtools browser and, when the native app can see the
  change, on agent-device (`ios:` builds and installs the branch's app first; the phone is
  the default and a simulator stands in when it isn't connected or another ship holds it;
  a mobile-web build may add a simulator's Safari, never the phone), fixes what fails and
  reruns, up to three fix rounds. No desktop control of the Mac. It walks the surface Pete
  would open, signed in the way he would be, with real clicks, taps and keys, never events
  dispatched from a script (a right-click menu bug got past synthetic events twice). When
  getting past sign-in on the repo's test-auth path took a trick (Clerk's bot check, say),
  write it into the contract's `test-auth:` so the next run doesn't rediscover it. It
  uses the branch's preview link when there is one (a per-push `preview:`, or an
  on-demand one ship built), else the localhost.
  **Pete asks for Codex** ("test in codex"): verify's `reference/codex.md` hands it to his
  Codex app or the headless tester instead; write `gate:codex` while his Codex app has it.
  - **`works`: write the PR body, then land** (LAND), unless the lane waits for Pete
    (below). No stop, no cue. Call the Skill tool with `pr` and rewrite the tracker PR's
    body in its shape: Summary (the smallest visual that shows the change), Evidence
    (before/after: the QA result and its shots, the test that went green), Merge Danger
    (door and blast radius). The door is ship's call on every ship: **two-way** (a revert
    undoes it) lands now; **one-way** (it deletes or migrates data, moves money, sends
    something to people, or a revert can't undo it) waits for Pete's "merge main" like a
    money path.
  - **`broken` after three fix rounds, or `unverifiable`: park.** End the turn with
    `needs input:` ("test: <feature> — couldn't prove it works: <reason>") and hand Pete
    the result and evidence. A step the run couldn't reach (a mic, a bot check, a device
    it couldn't open) makes the result partial, and partial is `unverifiable`, never a
    footnote on a landing. Three ships went to Pete with a known gap and he found it in
    minutes ("this should have been tested before you sent it").
- **Render the review card** from `reference/review-card.html` (contract below) to the
  docs home as soon as the result is in, and commit it on the branch, with the proof
  shots it shows copied beside it, before LAND's step 0: LAND removes the worktree. A
  Codex hand-off Pete watched gets none; its record is the `result:` line, the PR body,
  and the thread link. `LANDING_STATUS` says "Tested · landing on main", or what it waits
  on. `open` main's copy with the `result:`, or the worktree's with the park. It is the
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
### 5 · LAND — on the QA pass, or Pete's "merge main"  → marker removed

Mechanics only: nothing is reviewed here. Merge, watch it go live, tidy up.

- **Land — `land: pr` (the default), from the MAIN CHECKOUT, teardown first** (incidents: Worktrees — both orderings that deviate have stranded ships):
  0. Pre-flight *from the worktree*: `git fetch origin`; if main moved, absorb +
     re-gate + push; run `stack:` once more; bring the `pr`-shaped body from TEST up to date with what actually
     shipped (the squash commit takes it); `gh pr ready <#>`; confirm `gh pr view <#> --json mergeable`
     says `MERGEABLE`.
  1. Return to the main checkout (`ExitWorktree({action:"keep"})`).
  2. `wt remove feature/<slug> -f` — frees the branch for `--delete-branch`.
  3. `gh pr merge <#> --squash --delete-branch` — from the main checkout.
  4. `git pull --ff-only` (+ `git branch -D feature/<slug>` if a local branch
     lingers). Dirty main checkout (another session's work) → skip the local ff
     and run any deploy from a throwaway worktree pinned to `origin/main`.
  - A worktree ship didn't create, a session launched inside its worktree, a repo with
    no GitHub remote, or `land:` other than `pr`: `reference/rare-cases.md`, Landing variants.
  - Then `rm -f .ship-stage .ship-route.json` and `rm -f ~/.claude/ship-active/$CLAUDE_CODE_SESSION_ID`,
    **stop the review dev server**, remove the branch app `ios:` installed, by the udid and
    bundle on its IOS line (`xcrun devicectl device uninstall app --device <udid>
    <bundle>`, or `xcrun simctl uninstall <udid> <bundle>`; only that bundle, never the
    real app; a phone that isn't connected gets one line saying so), unless the line says
    `keep=yes`: a test app every branch installs over keeps the permissions Pete granted it,
    and removing it brings the prompts back, deprovision the per-branch
    backend stage 0 spun up, if any (or skip if previews auto-expire). Verify with
    `git worktree list` — zero ship-created worktrees must remain; a leftover means
    teardown failed (usually a merge run inside the worktree) — recover before
    declaring done.
- **Watch what landing deploys (the contract's `live:`).** Where main is production and
  the host builds it (cells-app: each touched pack's Vercel production build, Convex
  first), watch every such build to READY or ERROR, then load each live URL once (`curl -sS -o
  /dev/null -w '%{http_code}'`, and the page's text): READY with a 404 or the host's "not
  found" page is a failed deploy, not a live one (eca-finder served NOT_FOUND on every
  route from a READY build, 2026-10-05). Report it with the live URLs; ship
  never runs a production deploy or pushes a production database by hand. Where the
  contract names a separate integration lane instead, push merged main to it — its
  dev-deploy step runs from the main checkout (shared-plane writer; incidents: Backends)
  — and hand back the lane's URL. Never make Pete run a deploy. Watch
  rules (each from a real incident — incidents: Backends): every wait has a deadline
  and a never-started check, so a watch that sees no deployment for the SHA within
  about 3 minutes says so and looks at the host's ignore step (a 25-minute wait was on
  a build Vercel never started), and nothing waits on a build the lane never makes;
  watch the deploy to conclusion (red = unfinished work, fix-forward on a new express branch); watch
  the run for YOUR commit — `gh run list --commit <full sha>` (get it with
  `git -C <root> rev-parse <sha>` in its own call), full SHA only, a short one matches nothing and the watch times out silently — and
  artifact-check the lane; a red shared
  lane you didn't cause is a shared resource — check for an existing fix PR, claim
  with a draft PR first.
- **A separate promotion is NOT ship's job.** Where a repo promotes from an integration
  lane to production by its own script, that is Pete's human-gated ritual: never run it,
  never offer to, unless the contract's `release:` names it: then Pete's release word runs
  it. Where main is production, landing is the release and ship watches it through.
- Run RETRO, then end with a `result:` line: what shipped, one sentence, with the live
  links (or the lane's) — plus `· retro sent` and/or `· K backlog candidates`
  when applicable. Only a landing earns `result:`; a ship parked at TEST ends its turns
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

Each real one is a backlog candidate (below), listed under the `result:` line with what
to add and where: the run has landed, so a guardrail or pointer is its own small ship,
never a commit slipped onto main. A gap the repo already knows about (the same finding in
an earlier run's list) is not news; say nothing.

Don't gate `result:` on any of this.

## The storyboard contract (GATE 1 artifact)

Render `reference/storyboard.html` — a page that is the app, not a page about it:

- **Frames** — one per screen or state, live HTML at ship size, in the product's own
  stylesheet: a repo that ships one links it by relative path from the docs home
  (cells: the three grok sheets under `web/public/`); anything else inlines the tokens
  it uses. Each frame is authored as a `<template>` and mounted into its own iframe by
  the page's script, so the product's sheet styles the frame and nothing else, `:root`
  tokens resolve, and a hover, an open menu or a tab works where the feature has one,
  so Pete can poke it. Directions in play are sibling frames of the same screen. Frames
  are screens, not a wired-up app: no click-through demo between them (Pete,
  2026-10-08).
- **Where the product's sheet doesn't decide, the model's own defaults are out**: a
  cream or off-white page, an italic accent word in a headline, pill-shaped buttons.
  The craft floor already bans numbered section labels and monospace as costume.
- **Captions** — one line per frame: what is new in it.
- **The questions** — two or three, the ones a designer would bring, each with the
  pick you'd make. Never a recommendation dressed as a question.
- **For the record** — one collapsed block at the foot: recon, consults, reuse audit,
  surface liveness. Never above a frame.

No TL;DR, no research sections, no scope contract, no plan: the page is the mockups.

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

## The review card (every pass and park but a watched Codex hand-off)

Render `reference/review-card.html` filled with the meta only — PM-framed, one screen; a
`17-pr-writeup` for a PM, never a file tour. Pete reviews *this*, not the diff:

- **What you got** — plain-English bullets of what now works.
- **Proof it works** — the QA run's captioned screenshot storyboard (start →
  action → success, browser and phone) with the `works` verdict on top. (Non-visual →
  demo/test output.)
- **Already checked for you** — gates green, the QA script walked end-to-end, any committed e2e spec (name it); what was NOT touched (schema / money /
  public surfaces).
- **Flagged** — taste notes, if any. Reports, not work — Pete
  decides: fix now / backlog / ignore.
- **Only you can confirm** — the 1–2 things that need his eye, on the preview links or
  the open localhost.
- **Also worth building — didn't make this round** — the run's backlog candidates (see
  below). Most rounds have none — omit the section entirely; never pad it.
- **Where it is** — the live links landing deployed (the contract's `live:`), or the
  preview links and localhost when the ship parked. The verdict line (`LANDING_STATUS`)
  says which: "Landed on main" with the live URL, or what it waits on. The tracker PR
  link is there for the record, but he shouldn't need it.

## Backlog candidates — collect deferrals for the card

A run throws off build-worthy ideas that aren't this round's job. Keep a running list
(no scratch file — you're one continuous run) of the ones you'd *actually build*, each
with a one-line why-deferred. A candidate is a thing OUTSIDE the spec's scope —
never a specced surface you chose not to build; this is not a loophole around the scope
law. Surface them on the review card when there is one, else under the `result:` line,
which names the count. Don't invent a tracker. Never gate the merge on this.

## Gate signals — how a parked ship reaches Pete

At a gate, three things fire so Pete notices whether he's watching or away:

1. **Status line** — the `gate:N` marker shows `✋ <slug> — storyboard?/go?` in bold amber.
   TEST's `test` marker is not a gate: it shows `🧪 <slug> — testing`. A Codex
   hand-off Pete asked for writes `gate:codex`: `✋ <slug> — test it with Codex`. A ship that parks for
   Pete writes `gate:test`: `✋ <slug> — try it, then merge main?`.
2. **FleetView bucket** — the turn ends with a `needs input:` line → the row jumps to
   *awaiting input*.
3. **Desktop notification** — the gate Stop-hook fires a Ghostty notification
   (`<slug> → GATE N`, `<slug> → test it with Codex`, or `<slug> → try it, then merge main?`). Gates are rare, so this
   is never noisy.

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
deliberate ruling, not an oversight): `superpowers:brainstorming` runs only in DISCOVER
(GATED / `design`) — EXPRESS and SELF-DIRECTED skip it; and there is no strict TDD by
default — tests are a build deliverable, the pre-merge gate is the backstop, and
test-first (`superpowers:test-driven-development`) is reserved for money paths.

Also not ship's job: arbitrary phasing (the scope law); `executing-plans`
(checkpoint-heavy — the opposite of hands-off); manual git worktree management (`wt`
owns birth-to-death in Claude Code; Codex Desktop owns its own); landing without the
QA run's pass or Pete's "merge main" (except `land: auto`); running a production deploy or pushing a production
database by hand (the host's build does it); a separate promotion script, which is Pete's
human-gated ritual, never ship's to run, gate, or offer.
