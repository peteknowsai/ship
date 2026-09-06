---
name: pipeline
description: Use for any code change in a product/web repo, quick fix to full feature — ship sizes the ceremony itself and stops only when Pete's taste is in play. Explicit verbs pin the process — "/ship express <tweak>", "/ship design <idea>", "/ship next" (ship the board's Next column as a batch); anything else sizes itself. EXPRESS (tweak — no spec/plan, straight through to dev), SELF-DIRECTED (writes its own spec+plan, builds, reviews, merges, deploys — zero stops), or GATED (design direction + "go" gates) — gates fire only when Pete's answer would change what gets built. Auto-triggers on change requests; you never type it. Do NOT use for a question or pure analysis. Never edit main directly.
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

If the invocation's first word is `express`, `design`, or `next`, that verb **pins the
process and skips the sizing judgment below**. Anything else — bare `/ship <idea>` or
the auto-trigger — sizes itself. Every verb rides the same rails: **stage 0's worktree
off main via `wt`, never a primary checkout**.

**The fork is the verb's FIRST act — before any question, recon agent, or authoring
step.** The moment a verb lands, resolve the target repo and run stage 0 there. The
marker flip is how Pete *sees* ship engage. One exception: `/ship next`'s board sweep is
read-only — each *queued ship* forks as its own first act instead.

- **`/ship express <tweak>`** — pins EXPRESS. The verb pins ceremony *down*, never
  safety down: a money path or a taste call promotes per the mid-flight rule regardless.
- **`/ship design <idea>`** — pins GATED and mandates the full design workshop in
  DISCOVER (storyboard → rounds → lock → HTML plan → go → spec → build). The verb is
  Pete asserting taste is in play; never downgrade it, however mechanical the work
  looks.
- **`/ship next`** — ship the board's **Next column** as one batch (board-backed repos
  only; no board → say so and stop):
  1. **Sweep + enrich.** Pull every Next card; bring each up to standard anatomy
     (What / Why / Done when) from card context + the repo before judging it.
  2. **Triage** into **ship-now** (spec inferable, no taste call), **needs-design**
     (Pete's taste genuinely in play — same test as the GATED lane), or **too-thin**
     (can't design it without Pete). Narrate the three lists before firing anything.
  3. **Fire ship-now as a sequential queue** — one ship at a time, each a normal lane
     run with its own worktree and card flow. **Never a parallel swarm**: merges
     serialize onto main, one preview backend at a time; a failed ship parks its card
     (comment why) and the queue moves on.
  4. **Bulk GATE 1 for needs-design: ONE design doc, one sitting** — a single HTML,
     a section per ticket (direction, mockup where visual, the one question that
     matters). Publish, link on each ticket, present once. Approved sections run
     straight through; redirected ones get revised. Nothing builds on a guess.
  5. **Too-thin cards** stay in Next with one clarifying question commented.
  End with a batch `result:` line: `shipped N · awaiting design answers M · too thin K`.

## Sizing — every change ships; you pick the ceremony

The rails are constant: worktree off main → change → prove it → merge via PR (or the
contract's `land:` command) → dev
lane — **nothing ever edits main directly, however tiny, and Pete does nothing unless a
gate genuinely needs him.** What scales is the ceremony, and **you size it, not Pete**:

- **EXPRESS — a quick tweak or fix.** Whole diff visible before you start, no money
  path. No spec, no plan, no cards, no stops: worktree → change → repo gates
  (tsc/tests) → self-drive the affected flow → fast PR, merged on green → dev lane →
  `result:` line. A dab of `ponytail` (smallest diff), and `impeccable` for anything
  visual. Pete finds out from the `result:` line, not before.
- **SELF-DIRECTED — real work with no taste question in it.** Write whatever
  machine-facing spec/plan *you* need to build it well, then build, run the full REVIEW
  machinery (the fresh-eyes review + `verify` — a `works` verdict is the merge bar), merge,
  deploy to dev, `result:`. **Zero stops — the artifacts are for the record, not
  approval.**
- **GATED — Pete's taste or direction is genuinely in play.** A new user-facing
  surface, visual identity, a product tradeoff, ambiguous scope, a money path — the
  gated pipeline below.

**The gate test is never size — it's whether Pete's answer would change what gets
built** (or the change is risky/irreversible). If his input wouldn't change the outcome,
don't stop. **Autonomous lanes merge only on green gates + a `works` verdict.**
Mid-flight, promote the moment taste or direction appears (park, write the spec from
what you've learned, present GATE 1); size alone moves EXPRESS → SELF-DIRECTED, never to
a gate. Never use an autonomous lane to slip a taste call past Pete.

## Engines

**Fable always drives — every stage, including BUILD** (Pete, 2026-07-28). The driver
owns design, briefs, triage, gates, git, and the final say, and **dispenses the plan's
coding tasks to Opus subagents** — the Agent tool, `model: "opus"`, one per task.

**Coding drafts run on plain harness subagents; codex is not a ship engine** (Pete,
2026-09-06, retiring the supervised `codex app-server` dispatch that ran from
2026-08-12 and the `codex-supervisor` skill with it). A subagent returns its result to
the driver and wakes it on completion, so the entire watching layer the supervisor
existed for — an app-server process, a JSONL stream, a `status.json`, stall budgets,
park lines, a session id threaded through three commands, a retry after a run dies at
startup — has nothing left to watch. Two engines meant two sets of failure modes and a
subagent whose whole job was telling them apart. One engine means the harness owns
liveness and the driver owns judgment, which is the split that was wanted all along.

**The driver writes inline anything under one file and ~50 lines** — config, glue
between two tasks, a test tweak, a small fix from triage. Spawning costs a brief and a
context, so a task that would take the driver five minutes never routes (Pete,
2026-09-03: builds were bogged down; the driver does some of it itself). Skill/agent
prose and design taste never route either. **Everything that is not the driver's
judgment routes the same way** — coding drafts, recon, expert consults, verify walks,
design QA, review fan-outs — with the `/browse` skill for anything in a browser. Never
`claude -p` from inside a session. **Opus for anything that writes code or returns a
verdict. Never Sonnet.**

**The driver owns the envelope**, whoever drafts: it writes the brief the subagent
carries (exact files, signatures, test cases, constraints — a vague brief burns the
savings in fix rounds), reviews the returned diff and runs the gates before anything is
committed (never trust a "tests pass" claim from a subagent), and owns git entirely.
**One writer per branch at a time** — concurrent writers on one tree collide;
serialize, or give each its own sub-worktree.

**Browser work splits by wall** (Pete's standing rule): plain headless QA and
unauthenticated browsing — verify walks, design QA, live-product grounding — run on
**`/browse`**; **auth-walled or bot-walled surfaces run on `pane`** (open a tab as your
agent name, raise a handoff when a human is genuinely needed). Never the
`mcp__claude-in-chrome__*` tools. A subagent drives the browser against the running app
and reports what it saw; a coding subagent never drives one.

**Never idle while a subagent runs** — a draft, review, or QA pass is minutes, not
seconds.
Work the standing non-tree list meanwhile (draft the review card, the board update, the
commit message, groom `/ship next` cards) so the stage closes minutes after the result
lands. Same posture at gates: notify, then keep doing non-gated work.

## Two principles, always

1. **The meta rule.** Every artifact Pete sees is a condensed HTML page — he reads the
   *meta*, never the full spec or plan. The spec and cards are HTML he opens in the
   browser; the execution plan is machine-facing markdown he never reads. HTML artifacts
   follow the **html-effectiveness patterns** (https://thariqs.github.io/html-effectiveness/):
   plain-English TL;DR first, structure as diagrams/side-by-sides instead of prose,
   depth behind collapsibles, anything visual a *live* embed. Pattern picks are named
   per stage. **Prune hard inside that format — never reach for a new one.** Pete tried
   landing-page-styled gate artifacts against the plain doc and kept the doc: "this is
   taking it far too radical an approach… maybe there's just a little bit of pruning."
   Cut any section that doesn't change a decision; shorter ledes, depth collapsed.
   **The storyboard is the one page that is not condensed prose: it is mockups**, and
   its words are captions (stage 1). A storyboard that reads as a document has failed
   (Pete, 2026-09-03: "more of a document and less like working with a designer").
2. **Two gates, both his.** GATE 1 = Pete's lock on the storyboard (DISCOVER runs as
   presented rounds, each a hard stop — see stage 1). GATE 2 = his "go" on the HTML
   plan card (stage 2). **Both always fire on the GATED lane** (Pete, 2026-09-03:
   storyboard, lock, plan, go, spec, build). This supersedes the 2026-07-28 rule that a
   zero-call go-card auto-passes: a storyboard he iterated earns a plan he reads, and
   the plan is one screen. SELF-DIRECTED and EXPRESS render no cards and stop for
   nobody; a money path stops on any lane. When a gate fires, it is a **HARD STOP** —
   present the artifact and wait.

**Pete's stack:** his global instructions carry the standing stack — flue · Cloudflare ·
Convex · Clerk · Stripe · Next. Never re-ask it. **The repo's own `CLAUDE.md` /
`AGENTS.md` overrides it** where it diverges.
Escalate a library choice only when it's both architectural *and* outside the canon.

## The ship contract — what a repo tells ship

A repo declares how ship runs it in its `CLAUDE.md` / `AGENTS.md`: the **gate commands**
(tests, typecheck, production build), the **deploy lanes** and their scripts, **per-branch
preview provisioning** where a shared backend exists, a **test-auth path** verify may
use, and — for repos that shouldn't ship at all (wikis, civic work) — **`ship: no`**,
which means decline and say why. homezero's AGENTS.md is the model. A repo with no
contract gets best-effort: whatever gates you can find, merge to main, no deploy claim.

Two more keys, each from a repo that could not run ship without it (cells, 2026-09-03):

- **`land: <command>`** — how a finished branch reaches main when the PR path is wrong
  for the repo (a mirror remote, a local-only main, a promote hook that builds on push).
  Ship runs that command from the worktree in place of the PR merge (stage 4 says
  where), then tears down as usual. The command is the repo's; ship never invents one.
- **`design of record: transplant <path>`** — the repo's chrome is a byte-level transplant
  of another product's renderer, and `<path>` is that product's bundle. Under it,
  surfaces the reference owns are **lifted, never designed, measured or minimised**: the
  contract names which hooks are the reference's and which are the repo's own (cells:
  `sand-`/`ui-` are Grok's, `cells-` are ours), and ship applies its design machinery
  only to the repo's own. The clauses marked *transplant* in DISCOVER, PLAN, BUILD and
  REVIEW below say what changes; the repo's parity check joins the gates. Without the
  key, nothing below changes.

A repo that publishes releases may also declare a **release ritual**: it keeps a
`VERSION` file and a `CHANGELOG.md`, and its contract says to bump them at ship time.
Then the branch's last commit before merge bumps VERSION scale-aware (patch = fix or
small addition, minor = new capability, major = breaking) and adds ONE user-facing
CHANGELOG entry — what the user can now do, never branch narrative (no mid-branch
version numbers, no review play-by-play). No declaration → no bump, no entry; app
repos skip this entirely.

## Decision memory — settled calls survive the session

Where gstack is installed (`~/.claude/skills/gstack/bin/gstack-decision-search` on
disk), the pipeline reuses its per-project decision store — never hand-roll one:

- **DISCOVER start:** run `gstack-decision-search --recent 5` and treat what it lists
  as settled calls with their rationale. Don't re-ask Pete a settled question;
  reversing one is allowed, but say so explicitly.
- **When a gate (or Pete mid-run) resolves a DURABLE call** — design direction, scope
  cut, architecture or tool choice, or a reversal — log it:
  `gstack-decision-log '{"decision":"…","rationale":"…","scope":"repo","source":"user","confidence":8}'`
  (`--supersede <id>` for a reversal). Turn-level edits and phrasing tweaks are never
  logged — a noisy store is worse than none.

No gstack on the machine → skip silently; the pipeline runs unchanged.

## The pipeline — create a todo for each stage

Each stage writes its marker to `.ship-stage` at the git root (the status line + the
FleetView row read it). Written for Claude Code; a **Codex Desktop** driver applies the
swaps in "Running under Codex Desktop" below.

### 0 · Worktree (invisible)  → marker: `discover`

**Prereqs:** a git repo with a base branch and ≥1 commit (zero-commit repo: `git add
-A && git commit -m "init"` first). The PR path needs a GitHub remote; a repo with no
remote falls back to `wt merge` at merge time.

**Resolve the base branch first — never assume `main`:** `git symbolic-ref
refs/remotes/origin/HEAD` (strip `refs/remotes/origin/`), else `origin/main`, else
`origin/master`, else local `main`. Every `main` in this pipeline means that detected
base branch.

```
wt switch --create feature/<slug> --no-cd --format=json -y
```
then enter the path from the JSON. **In the session's primary repo, `EnterWorktree({path})`
is MANDATORY, not a suggestion** — the status line and FleetView read the session's cwd,
so a run that keeps working by absolute path while parked on main is invisible to Pete
even though `.ship-stage` is being written faithfully in the worktree (he has had to ask
mid-BUILD whether a run forked at all). Absolute-path driving is the *cross-repo*
fallback only, where `EnterWorktree` can't take. **Self-heal:** notice mid-pipeline that
the session cwd isn't the worktree → `EnterWorktree({path})` right then; it works fine
after the fact. Codex Desktop: absolute paths throughout. `--no-cd` is load-bearing. A `.config/wt.toml` auto-provisions
gitignored runtime files. Write `printf 'discover' > <root>/.ship-stage`, then
**`echo .ship-stage >> $(git rev-parse --git-common-dir)/info/exclude`** — `git add -A`
sweeps the marker into commits otherwise (incidents: Worktrees). Never build on main.

- **Provision the per-branch backend now** if the repo's ship contract has one — a
  worktree building against a shared backend clobbers it (incidents: Backends). No
  preview lane → build against the repo's dev stack. **Rewrite the worktree's env file
  to the preview before the first backend command** and confirm the first deploy's host
  is the preview: the inherited `.env.local` carries the shared key, and the
  `--preview-name` flag does not override it (incidents: Backends). From here on the
  preview's *name* comes from that file, never from the branch.
- **Cross-repo case:** `EnterWorktree` only takes for the session's primary repo
  (incidents: Worktrees). Against any other repo, work the worktree by **absolute
  path** and **narrate the fork the moment you create it** (`forked feature/<slug> off
  main @ <path>`) — a blind status line must never make it look like nothing forked.
- **Recon may contradict the fork — then re-fork.** In a multi-repo workspace the target
  repo is itself a recon finding (incidents: Worktrees). Exit, `wt remove` the empty
  worktree, fork in the right repo, narrate the move. Fork-first stays; being wrong
  about the repo is cheap, being invisible is not.
- **Opportunistic tidy:** glance at `git worktree list` and `wt remove <branch> -f`
  any worktree that provably landed (merged PR whose `headRefOid` matches its HEAD,
  clean tree — incidents: Worktrees). Never touch one with uncommitted work.

### 1 · DISCOVER — Pete's taste, up front  → marker: `discover`, then `gate:1`

- **Resurface decision memory first** (see Decision memory) — settled calls constrain
  the brainstorm; don't re-litigate them inside it.
- Invoke `superpowers:brainstorming`. PM-framed, one question at a time.
- **Recon runs on a subagent, synthesis stays with the driver.** Codebase
  evidence-gathering dispatches as a read-only Opus subagent (report findings, edit
  nothing).
  The recon brief includes a **reuse audit**: for every core noun the feature
  introduces, grep the whole repo — data layer included — for existing infra before the
  plan treats it as new (incidents: Design). When the design lands on an *existing*
  surface, it also **classifies that surface's liveness** — current design system?
  reachable from primary nav? touched by recent commits? — because a deprecated page
  serves happily (incidents: Design). The spec names the chosen surface explicitly.
- **Bug-shaped requests get an empirical root-cause check** — reproduce the failure or
  read the runtime evidence; never spec a fix from a hypothesis (incidents: Design).
- **Consult the installed domain experts before you spec.** Recon tells you what the
  repo does; an expert tells you what the *stack* will do to you. Where the change
  lands in a domain some installed agent knows better than you, ask it — as harness
  subagents (the Agent tool, `subagent_type`), fired in parallel while recon runs, one
  round, before the board is drawn. Not a coding subagent; not a second recon pass.
  - **Read the session's own roster** — the available agent types and skills are listed
    in-session — and **match against the surface the change actually touches**:
    `convex/` → the Convex expert (and its authz auditor when the change moves
    ownership or exposes records), a Claude Code capability (hooks, MCP, subagents,
    SDK) → the claude-code guide, DNS / WAF / the edge → `cloudflare`, an always-on
    agent → `flue`. **Never a hardcoded list** — rosters differ per machine and repo.
    Nothing matches → consult nobody; a manufactured consult is worse than none.
  - **Ask what changes the design, not what does the work.** "What's the canonical
    pattern for this here", "what will bite us at scale", "what does this choice make
    impossible later", "is there a component that already does this". A consult whose
    answer couldn't move a line of the spec was a wasted turn.
  - **You keep the pen.** Answers are evidence, weighed like recon — the driver writes
    the spec, and Pete's settled calls (decision memory) and the repo's `CLAUDE.md`
    outrank any agent's opinion. When a consult changes a decision, name it in the
    spec's TL;DR so the reason survives the run.
- For any visual/UI feature, invoke `impeccable` and follow its Setup (context.mjs —
  the repo's PRODUCT.md/DESIGN.md are the visual authority): a new surface or
  replacement look routes through its `shape`/new-work path; a refinement stays on the
  incumbent world. Use `/image-gen` freely for imagery inside a frame.
  *Transplant:* a surface the reference owns gets none of this. Its design is the
  reference bundle; its frame in the storyboard is the lifted markup (the i18n id, the
  chunk and the class strings named in the caption), and the workshop below runs only
  for the repo's own surfaces. A ship that touches nothing of the repo's own still
  storyboards — Pete sees where the lifted thing sits in the app — and locks on that.
  **Ground the design in the live product**: a subagent walks the running app /
  deployed URL over `/browse` and reports the real theme/CSS with screenshots;
  design from those, never from in-repo mockups (incidents: Design).
- **DISCOVER is a storyboard, not a document** (Pete, 2026-09-03). The first thing he
  sees is the app: an HTML page that is mostly mockups of the screens the feature
  touches, the way a designer opens a session by putting comps on the table. He reads
  it like a storyboard, reacts, and you redraw. Nothing in DISCOVER is a spec; the
  spec is written after his go (stage 2).
  1. **Round 1 — the storyboard.** One file per ship,
     `specs/designs/YYYY-MM-DD-<slug>.html` in the docs home, from
     `reference/storyboard.html` (contract below). Each frame is a live HTML mockup of
     one screen or state at the size it ships — the window, not a cropped component:
     the sidebar, the titlebar, the new thing in place — drawn in the product's own
     stylesheet and tokens. A transplant frame is the lifted markup. Where a direction
     is genuinely open, draw it as two or three frames of the same screen side by side
     (`02-exploration-visual-designs`), never as prose options. The words on the page
     are captions: one line under each frame saying what is new in it, and the two or
     three questions a designer would actually bring ("went denser on B, unsure about
     the nav, which tone?"). Recon, consults and the reuse audit go in one collapsed
     block at the foot, for the record; they never sit above a frame. No TL;DR essay,
     no section per research finding, no fait accompli. Write `gate:1`, commit, fire
     the gate notification, `open` the storyboard, end the turn with `needs input:`
     ("storyboard round 1 — reactions?"). **HARD STOP** — every round is one.
  2. **Rounds.** Pete reacts; redraw the frames in place — minutes per round, not a
     re-spec. A frame he killed is deleted, never greyed out. Re-`open`, end the turn
     with `needs input:` again. Push back where taste warrants it: a designer with no
     opinions is a renderer. Loop until he locks it ("this is it", "lock it", "yes").
  3. **Lock = GATE 1.** Commit the storyboard as it stands: **it is the design of
     record from here on.** Every frame left in it ships; nothing not in it does. Log
     the direction to decision memory, then straight into PLAN.
  Pen (the Pencil app) is no longer the default. When Pete asks to take a frame into
  pen, put it there, let him iterate, and harvest the result back into the frame
  before the lock; the storyboard stays the single design of record either way.
- **Commit every gate artifact to the branch before you fire the gate** (storyboard,
  plan card). A parked ship with uncommitted work looks disposable to another
  session's cleanup sweep, and one nearly lost its spec that way (incidents: Worktrees).
- **The driver draws the frames and writes the captions inline** (taste is the
  deliverable, never dispatched). A subagent never draws a storyboard.
- A trivial visual change where several frames would be noise may collapse the
  storyboard to one frame + one confirm — never to zero showings on the GATED lane.
  A non-visual GATED ship (pure product tradeoff, no UI) has no storyboard; it gates
  on a one-screen board in the `14-research-feature-explainer` shape: TL;DR first,
  the one question that matters, depth collapsed.

### 2 · PLAN — the plan Pete says go on  → marker: `plan`, then `gate:2`

- Write `plan`. Run `ponytail` as the *waste* critic, not a scope critic — it cuts
  reinvention and gold-plating, never a frame Pete locked. *Transplant:* ponytail's
  ladder stops above the reference. A wrapper, a class, a token or an element the
  reference's markup carries is never waste, however empty it looks (the padding
  lives in it); "shortest working diff" applies to the repo's own code only.
- **Consult a domain expert again only for a question the plan raises and the
  storyboard didn't settle** — schema shape, index or migration order, an API's real
  constraint, an auth boundary. Same rules as DISCOVER's consult: harness subagent, a
  question not a task, the driver decides. **On SELF-DIRECTED — which skips DISCOVER's
  storyboard — this is the lane's only consult**, so a stack question that would change
  the plan gets asked here or nowhere.
- **Render the plan card** from `reference/go-card.html` (contract below): the locked
  storyboard in one glance, then what gets built as a punch list in plain English
  (one line per piece of work, in build order), the cut list, his calls with your
  recommendation, the risk line, and "go". Commit it, `open` it.
- **GATE 2 is his go, always, on the GATED lane** (Two principles). Write `gate:2`,
  fire the gate notification, end the turn with `needs input:` ("go?"). **HARD STOP.**
  SELF-DIRECTED renders no card and stops for nobody.
- **His go → spec it out.** Only now does the machine-facing writing happen: invoke
  `superpowers:writing-plans` for ONE execution plan covering the **entire
  storyboard** — never sliced into phases — saved to the docs home
  (`specs/plans/YYYY-MM-DD-<slug>.md`). It carries everything a frame can't: copy as
  data, routes, behaviour, states, a11y, test cases, and for each UI task the frame it
  must match (`<storyboard>.html#<frame-id>`, never a prose description of the frame).
  Pete never reads it. A change he asks for after go is an express round, not a
  re-plan. **Each task names its files, the signatures it adds or changes, and its
  test cases** — brief-grade, so the BUILD brief is a paste plus deviations. Every
  4-minute first-pass-clean dispatch in the ledger had this; every 25-minute one
  left the worker to find the shape itself.
- **A task that computes from rows another code path writes gets one end-to-end test
  through the real writer** — not just unit tests over hand-built rows, which pass while
  the production writers produce garbage (incidents: Design).

### 3 · BUILD — automatic  → marker: `build:N:M` (N done of M tasks)

- Write `build:0:<M>`; bump N per task. Build **all M tasks** in one session; commit
  each task on the branch as it lands, merge only when the whole plan is built.
- Invoke `superpowers:subagent-driven-development` (the driver drives) and dispatch
  each drafting task to its own Opus subagent (the Agent tool, `model: "opus"`);
  sub-threshold work inline (Engines). The driver owns the brief, the diff review, the gates, and git. One
  writer per **tree** at a time — which is why fan-out means sub-worktrees, below.
- **Fan out by file overlap, before the first dispatch.** The plan names each task's
  files. Group tasks that share a file; every group is a lane. Each lane past the
  first gets its own sub-worktree off the branch (`git worktree add <dir> -b
  <branch>-<lane> <branch>`) and its own subagent, all launched together; a lane's
  tasks run in plan order inside it. The driver merges lanes back in plan order and
  runs the gates once after each merge. Serial is only for tasks that share files.
  A run that serialized three disjoint tasks spent 90 minutes on two of nine
  (2026-09-03); the same three run in the time of the slowest one.
- **A task's check is the diff and the gates, nothing else.** Read the diff, run
  tsc/tests/lint, commit. Nobody drives the app or CLI per task — the smoke-walk is
  once at the end of BUILD and `verify` runs once in REVIEW. A reviewer hand-driving
  the product per task cost 20 minutes a task and found nothing the gates missed.
- **Standing brief boilerplate** (each line from a burned run — incidents: Dispatch):
  test files whose assertions the planned change invalidates are **always in scope**,
  allowlist or not; the worker reports its result and **never commits**; the worker
  never runs `git reset/checkout/stash`.
- **A quiet subagent never blocks the build.** The harness wakes the driver when one
  finishes, so silence is not itself a signal to chase. If a lane's work is visibly in
  the tree and no report has landed, self-serve — review the diff and run the gates
  yourself rather than pinging. Dead air on the *reporting* path has stalled a real
  ship twice in one run; the work was already done both times.
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
  `~/.claude/skills/impeccable/reference/craft-floor.md` and honor its checks and bans.
  *Transplant:* a brief that touches a reference surface carries the reference path,
  the component to lift (grep the bundle for the id, take the class strings and the
  tree between), the rule **lift it, never re-measure it**, and the repo's parity check
  as a gate the worker runs before reporting. No craft floor and no comp for those
  surfaces; the comp is the bundle.
- **Before BUILD is done, smoke-walk the whole feature yourself** — boot the app and
  drive the spec's real user paths (the formal `verify` runs in REVIEW; don't invoke it
  twice). Two preconditions that have each cost a red deploy (incidents: Backends): a
  framework with its own production build → **run that build too**; the branch touched
  `convex/` → **re-push the preview** (`npx convex deploy --preview-name <name-from-
  .env.local> -y`, from the worktree root — the branch name and the shell's leftover cwd
  have each sent a deploy to the wrong place). *You* find the breakage, never Pete.
- Raise a hand only for a genuine fork (PM-framed, with a rec).

### 4 · REVIEW / MERGE — automatic  → marker: `review`, then remove the file

- Write `review`. **Sync with main first**: `git fetch origin`; absorb upstream in the
  worktree (rebase, or merge if unsafe), re-run the gates, then dispatch review — and
  re-sync right before the merge if main moved again (incidents: Worktrees). **If the
  absorbed commits touched `convex/`, re-deploy the preview before any further
  verification** — function skew is invisible to tsc, vitest and the production build,
  and has hard-crashed a page after a green rebase (incidents: Backends).
- **Freeze the tree while a verifier is driving** — no merges, rebases, or edits until
  its verdict lands (incidents: Worktrees). Absorb upstream *before* dispatching a
  round, never during.
- **Correctness review — a fresh harness subagent on the driver's model, launched
  first** so it works while the rest of REVIEW proceeds. The branch was drafted one
  task at a time; the reviewer reads it whole (`git diff <lane-target>...HEAD`) in a
  clean context, with the spec, and hunts the seams between tasks as hard as the tasks
  themselves — a writer and its reader drifting apart, a helper two tasks each
  invented, a test that only passes on hand-built rows. It touches nothing and returns
  findings as file:line, the failure scenario, and a severity. Meanwhile the driver
  runs `ponytail-review` (the over-build sweep). The **driver triages every finding**
  — adversarial reviewers over-flag by design — fixes what's real, puts judgment calls
  on the card. The high-value fan-out is here: several verifiers on one diff beats one.
- **Design QA for visual features** — a background supervisor first runs
  impeccable's deterministic detector over the branch's changed UI files
  (`node ~/.claude/skills/impeccable/scripts/detect.mjs --json <files>` — local, no
  network), then walks the built surfaces and judges them **side-by-side against the
  storyboard** (screenshot each built surface next to its frame rendered at the same
  size — impeccable's approved-comp critique: hero and sections as their own crops,
  never one full-page thumbnail) plus the craft-floor checklist (contrast, depth,
  spacing, type, motion, states, copy, and the bans). The review card shows the
  frame-vs-built pairs — Pete reviews the storyboard he locked against the thing that
  got built. Bounded per impeccable's own ceiling: one batched round, one confirm, no
  open-ended polish loops. **Report only — the driver owns every fix**; check
  `git status` the moment the round lands, because nothing enforces read-only at the
  tool layer (incidents: Dispatch). Driver triages: real gaps fixed before the card,
  nits land on the card for Pete. *Transplant:* for a reference surface the pair is
  the reference product beside ours (the repo's own tree audit and its screenshots),
  never a frame, and a visible difference is a finding whatever the checks say.
- **Put it in front of Pete, running.** For any visual/interactive feature, boot the
  worktree's dev server **detached, never through a bounded pipe** (`nohup npm run dev >
  dev.log 2>&1 &`, then curl-probe — a `| head -50` has SIGPIPE'd a server mid-verify)
  and `open http://localhost:<port>` so the live local app is on his screen. A feature
  behind an auth gate needs its secret in the worktree env, or localhost 403s and reads
  as broken (incidents: Backends). **Never deploy to let him review; never tell him to
  "go look at the live site"** — the worktree's localhost is the review surface.
  (Non-UI change → show the demo/test output instead.)
- **Screenshots live outside the repo** — the job tmp dir, never committed (~6MB of PNGs
  broke a push); copy anything the presented card references somewhere durable before
  teardown, or the card 404s its own proof (incidents: Worktrees).
- **Prove it works — invoke `verify` before the card.** A fresh read-only supervisor
  drives the feature and returns `works | broken | unverifiable` + a
  screenshot storyboard; verify loops-to-fix (cap ~3). **`broken` after the cap, or
  `unverifiable` → do NOT merge**: end the turn with `needs input:` ("review: <feature>
  — couldn't prove it works: <reason>") and hand Pete the verdict + evidence.
- **Render the review card** from `reference/review-card.html` (contract below) to the
  docs home and `open` it, pointed at the running localhost. **Never tell Pete to "go
  read the PR"** — the review comes to him, running and labeled.
- **The merge is NOT a gate — every lane merges itself** (Pete, 2026-08-16, resolving
  the collision with his standing "don't hand me mechanics" rule). A GATED ship whose
  design he approved at GATE 1, with green gates and a `works` verdict, merges without
  stopping: put the running app and the card in front of him **as a report, in the same
  turn as the merge** — he approved the build; landing it on a reversible dev lane is
  mechanics, not a decision. Changes he wants after the fact ride an express round.
  **Two things still hard-stop:** a **money path**, and a repo where **merge
  auto-deploys to production** (there the merge is the release). Neither is "it's a big
  feature" — size never gates.
- Changes Pete asks for at the card go through `superpowers:receiving-code-review` —
  verify the ask against the code, do the work, loop the changed flow back through
  `verify` before re-presenting.
- **Merge — the PR path, from the MAIN CHECKOUT, teardown first** (incidents:
  Worktrees — both orderings that deviate have stranded ships):
  0. Pre-flight *from the worktree*: `git fetch origin`; if main moved, absorb +
     re-gate + push; confirm `gh pr view <#> --json mergeable` says `MERGEABLE`.
  1. Return to the main checkout (`ExitWorktree({action:"keep"})`; Codex: absolute
     paths).
  2. `wt remove feature/<slug> -f` — frees the branch for `--delete-branch`.
  3. `gh pr merge <#> --squash --delete-branch` — from the main checkout.
  4. `git pull --ff-only` (+ `git branch -D feature/<slug>` if a local branch
     lingers). **Dirty main checkout** (another session's work) → skip the local ff
     and run any deploy from a throwaway worktree pinned to `origin/main`.
  - Session living in a worktree ship didn't create (Zero's sibling convention):
    don't tear down what isn't yours — merge with `-R <owner/repo>` sans
    `--delete-branch`, `git push origin --delete <branch>`, leave the worktree.
  - No GitHub remote → `wt merge` (squashes, ff's main, removes the worktree) is the
    fallback.
  - **A `land:` key in the contract replaces steps 0–4**: sync with main, re-gate, run
    the contract's command from the worktree, confirm main moved (`git log -1 main`),
    then teardown from the main checkout as above. No PR is opened and none is merged;
    a mirror remote is pushed only if the contract says so.
  - Then `rm .ship-stage`, **stop the review dev server**, **deprovision the preview
    backend** stage 0 spun up (or skip if previews auto-expire). Verify with
    `git worktree list` — zero ship-created worktrees must remain; a leftover means
    teardown failed (usually a merge run inside the worktree) — recover before
    declaring done.
- **Deploy to the integration lane, never production.** Push merged main to the repo's
  dev lane per its ship contract — its dev-deploy step runs **from the main checkout**
  (shared-plane writer; incidents: Backends) — and hand back the lane's URL. CI
  auto-deploy → say so and hand the URL once up. Never make Pete run a deploy. Watch
  rules (each from a real incident — incidents: Backends): **watch the deploy to
  conclusion** (red = unfinished work, fix-forward on a new express branch); **watch
  the run for YOUR commit** — `gh run list --commit $(git rev-parse <sha>)`, full SHA
  only, a short one matches nothing and the watch times out silently — and
  artifact-check the lane; **a red shared
  lane you didn't cause is a shared resource** — check for an existing fix PR, claim
  with a draft PR first.
- **Promotion to production is NOT ship's job.** "Merged" means live on *dev*. Never
  promote to prod / `www`, never offer to (the repo's promote script is Pete's own
  human-gated ritual). Only where merge auto-deploys straight to prod is the merge
  itself the release — there, and only there, the merge asks first.
- Run RETRO, then **end with a `result:` line**: what shipped, one sentence — plus
  `· ship-retro #N filed` and/or `· K backlog candidates` when applicable.

### 5 · RETRO — autonomous; only if the run taught something  → no marker

The *running* agent never edits the skill — you're shipping a feature, not doing skill
surgery, and one run is too narrow for a general fix. If this run surfaced a real gap
(Pete corrected the pipeline, a stage misfired), file it for the maintainer:

```
gh issue create -R peteknowsai/ship --label ship-retro --title "retro: <one-line gap>" \
  --body "<what happened · the gap · a suggested fix · the repo/feature it came from>"
```

**Most runs teach nothing — skip silently.** Never invent a lesson. Don't gate
`result:` on this.

## The storyboard contract (GATE 1 artifact)

Render `reference/storyboard.html` — a page that is the app, not a page about it:

- **Frames** — one per screen or state, live HTML at ship size, in the product's own
  stylesheet: a repo that ships one links it by relative path from the docs home
  (cells: the three grok sheets under `web/public/`); anything else inlines the tokens
  it uses. Each frame is authored as a `<template>` and mounted into its own iframe by
  the page's script, so the product's sheet styles the frame and nothing else, `:root`
  tokens resolve, and a hover, an open menu or a tab works where the feature has one,
  so Pete can poke it. Directions in play are sibling frames of the same screen.
- **Captions** — one line per frame: what is new in it. A transplant frame's caption
  names the reference component it lifts.
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
  fine; the card still stops for his go.
- **Risk** — one line.
- **Go** — one line.

It is the *only* thing Pete reads before a build starts. The execution plan is written
after his go and he never reads it.

## The review card (REVIEW artifact)

Render `reference/review-card.html` filled with the meta only — PM-framed, one screen; a
`17-pr-writeup` for a PM, never a file tour. Pete reviews *this*, not the diff:

- **What you got** — plain-English bullets of what now works.
- **Proof it works** — the verifier's captioned screenshot storyboard (start → action →
  success) with the `works` verdict on top; the app is also still running for him at
  localhost. (Non-visual → demo/test output.)
- **Already checked for you** — gates green, the flow driven end-to-end by a fresh
  agent, any committed e2e spec (name it); what was NOT touched (schema / money /
  public surfaces).
- **Verifier flagged / suggested** — taste notes, if any. Reports, not work — Pete
  decides: fix now / backlog / ignore.
- **Only you can confirm** — the 1–2 things that need his eye, on the open localhost.
- **Also worth building — didn't make this round** — the run's backlog candidates (see
  below). Most rounds have none — omit the section entirely; never pad it.
- **Merged** — stated, not asked: it's on the dev lane with the URL, reversible. The PR
  link is there for the curious, but he shouldn't need it. (A money path, or a repo
  where merge auto-deploys to prod, is the exception that still asks — say why.)

## The board is the run's record (board-backed repos)

Where the repo has a backlog-board skill (e.g. homezero → the `linear` skill, which
holds the mutations and recipes), the ticket mirrors the run. **The board is a mirror,
never a gate** — an API hiccup gets one line of narration and the pipeline rolls on.

- **Run start** — card to In Progress (GATED ships with no card get one created).
  EXPRESS skips the board unless a card already exists.
- **GATE 1 approved** — publish the spec HTML to the repo's public specs host (never
  the dev deploy), comment the 3-line summary + link. **Ticket links are always public
  URLs** — never localhost or file paths.
- **PLAN** — mirror the punch list into the description as checkboxes; tick as tasks
  land.
- **Merge** — card to **For Review**; the ticket becomes the review ask: a
  `## For your review` section with the dev-lane URL, checkboxes for what needs his
  eye, and a 1–2 line what-shipped; close with a comment carrying the `result:` line +
  verdict. Link the review-card HTML only when the ticket can't hold the depth.
  **Never move to Done — Done is Pete's drag.**
- **Bigger than this round** — real phases beyond this ship become a board *project*:
  this issue joins it, later phases are filed inside it, the spec link lives on the
  project.

## Backlog candidates — collect deferrals, file on approval

A run throws off build-worthy ideas that aren't this round's job. Keep a running list
(no scratch file — you're one continuous run) of the ones you'd *actually build*, each
with a one-line why-deferred. **A candidate is a thing OUTSIDE the spec's scope** —
never a specced surface you chose not to build; this is not a loophole around the scope
law. Surface them on the review card; the `result:` line names the count. When Pete
says *file them*, file through the repo's board skill and reply with links (Backlog
default, Icebox for the speculative; phases of one design go into its board project).
No board → the card is the record; don't invent a tracker. Never gate the merge on
this — approval is always async.

## Running under Codex Desktop

Same pipeline, gates, and artifacts — these swaps apply only when the driver is a Codex
Desktop session:

- **Worktrees: Codex owns birth and cleanup — never run `wt` against a Codex-managed
  worktree.** Preferred start: the thread already in Worktree mode off `main`. Sanity-
  check location (`git rev-parse --show-toplevel`); if detached HEAD, `git switch -c
  feature/<slug>` before the first commit. Thread is Local on `main` → do NOT edit;
  stop with `needs input: click Fork into new worktree for this ship`.
- **Artifacts open in Codex's in-app Browser** — serve the artifact's directory on
  localhost and navigate there (`file://` is unreliable); a running app's URL opens
  directly.
- **Merge is the PR path only**, never from inside the branch's worktree; then
  `rm .ship-stage`, stop the dev server, deprovision the preview — but **leave worktree
  cleanup to Codex** (archive the thread).
- **No status line, no FleetView** — narration carries the load alone; every status /
  `needs input:` / `result:` line ends with the breadcrumb, and `hooks/gate-notify.sh`
  runs manually at gates if present.

## Gate signals — how a parked ship reaches Pete

At a gate, three things fire so Pete notices whether he's watching or away:

1. **Status line** — the `gate:N` marker shows `✋ <slug> — storyboard?/go?` in bold amber.
2. **FleetView bucket** — the turn ends with a `needs input:` line → the row jumps to
   *awaiting input*.
3. **Desktop notification** — the gate Stop-hook fires a Ghostty notification
   (`<slug> → GATE N`). Gates are rare, so this is never noisy.

## FleetView narration contract

The dashboard reflects the session — make it a ship board:

- **Name** the session `ship:<slug>` at spawn (Pete types it, or dockmaster passes
  `--name`). A running session can't rename itself reliably.
- **End every turn with a clean one-line status** (`🔨 build 4/5 · <slug>`,
  `📐 planning · <slug>`) — status-of-work, not an echo of the last tool call.
- **At a gate, the closing line starts `needs input:`** → *awaiting input*. **At merge,
  it starts `result:`** → *completed*. Mid-work narration keeps it in *working*.
- **End `needs input:` and `result:` lines with `branch <branch> · worktree <path>`**
  (`detached@<short-sha>` until a branch exists) — Pete must always know which checkout
  he's looking at; it's what catches the cross-repo case, and under Codex Desktop it's
  the only location signal there is.

## What this skill deliberately does NOT do — including two standing skill overrides

**This pipeline overrides the superpowers defaults on its autonomous lanes** (a
deliberate ruling, not an oversight): `superpowers:brainstorming` runs only in DISCOVER
(GATED / `design`) — EXPRESS and SELF-DIRECTED skip it; and there is **no strict TDD by
default** — tests are a build deliverable, the pre-merge gate is the backstop, and
test-first (`superpowers:test-driven-development`) is reserved for money paths.

Also not ship's job: arbitrary phasing (the scope law); `executing-plans`
(checkpoint-heavy — the opposite of hands-off); manual git worktree management (`wt`
owns birth-to-death in Claude Code; Codex Desktop owns its own); promoting to
production (ship ends at the integration lane — promotion is Pete's separate,
human-gated ritual, never ship's to run, gate, or offer).
