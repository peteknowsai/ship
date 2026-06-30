---
name: ship
description: Use for any feature or multi-step change in a product/web repo — takes it from idea to merged through one pipeline (worktree → discover → plan → build → review), gating only on design direction and "go". Auto-triggers on feature-shaped requests; you never type it. Do NOT use for a typo fix, a one-line change, or a question — those just get done. Never edit main directly.
---

# /ship — idea to merged, in one command

You run a feature from idea to merged. Pete is heavy in DISCOVER (his taste), glances
at one card mid-way (go), and comes back at the end. Everything between and after the
two gates is automatic.

**Scope is the spec — Pete's dial, not yours.** Ship builds *exactly* what the design
spec covers: the whole thing, in one pass — one plan, one build, one review, one merge.
If Pete wants less he specs less; if he specs a big feature you plan and build the
*entire* feature and do not slice it down. Never decompose a specced feature into
"Ship 1 of 4" and stop, never defer specced surfaces to a "later phase," never let the
plan shrink the destination. A bigger spec means a bigger plan and a longer build — that
is wanted, not a problem to manage away. Phasing is Pete's to ask for, never yours to
impose. The models can hold a big plan; trust that.

**Two principles, always:**

1. **The meta rule.** Every artifact Pete sees is a condensed HTML page — he reads the
   *meta*, never the full spec or plan. The spec (design) and the go-card are HTML he
   opens in the browser. The execution plan is machine-facing markdown he never reads.
2. **Two gates, only two.** GATE 1 = design direction (after DISCOVER). GATE 2 = go
   (after PLAN, via the go-card). Nothing else stops for him. Both gates are **HARD
   STOPS** — present the artifact and wait; never auto-advance past them.

**Who Pete is:** a technical PM, not an engineer. Translate technical calls to plain
product terms, give a recommendation, let him decide. His lane = product, design,
taste, scope. Your lane = mechanics — handle them, summarize in one line. The
**standing stack is never re-asked** — it's Pete's default product/web stack, declared in
his global `~/.claude/CLAUDE.md` (flue · Cloudflare · Convex · Clerk · Stripe · Next).
**The repo's own `CLAUDE.md` overrides it** when that repo diverges (a non-web repo
declares its own stack). Escalate a library choice only when it's both architectural
*and* outside the repo's canon.

## The pipeline — create a todo for each stage

Each stage writes its marker to `.ship-stage` at the git root (the status line + the
FleetView row read it). The marker format is below each stage.

### 0 · Worktree (invisible)

**Prereqs:** a git repo with a `main` branch and at least one commit (the PR-merge path
also needs a GitHub remote; `wt merge` to local main works without one). If the repo is
empty (no commits / no `main`), make the first commit before branching — `git add -A &&
git commit -m "init"` — then continue. These are generic git setup, not ship's job to
invent, but stage 0 fails on a zero-commit repo, so handle it here.

Create an isolated worktree off main and enter it (the worktrunk `wt-switch-create` flow):

```
wt switch --create feature/<slug> --no-cd --format=json -y
```
then `EnterWorktree({path})` with the path from the JSON. `--no-cd` is load-bearing.
If the repo has a `.config/wt.toml`, it auto-provisions the worktree (gitignored runtime
files — node_modules, .env, .dev.vars — via reflink). Write the first marker:
`printf 'discover' > <root>/.ship-stage`. Never build on main.

**Opportunistic tidy (anti-accumulation):** glance at `git worktree list` first and
`wt remove <branch> -f` any worktree whose branch is already merged and its remote shows
`[gone]` (a finished ship that wasn't torn down). Only ever touch merged+gone worktrees —
never one with unmerged work. This + stage 4's teardown means ship worktrees never pile up.

### 1 · DISCOVER — Pete's taste, up front  → marker: `discover`, then `gate:1`

- Invoke `superpowers:brainstorming`. PM-framed, one question at a time.
- For any visual/UI feature, also run `impeccable` — the HTML design sprint (use `/pix`
  for imagery freely). The spec *is* the prototype.
- Produce ONE self-contained HTML spec in the repo's docs home (`specs/` or `docs/`,
  whichever it uses) — e.g. `specs/designs/YYYY-MM-DD-<slug>.html`. Design the **whole**
  feature here — every surface and behavior Pete wants in scope — because this spec is the
  scope contract PLAN and BUILD execute in full. A big feature is a big spec; don't trim
  it to a slice.
- Write `gate:1` to `.ship-stage`, fire the gate notification (see "Gate signals"),
  `open` the spec, and **end the turn with a `needs input:` line** naming the ship +
  "design direction?". **HARD STOP — GATE 1.** Wait for approval.

### 2 · PLAN — automatic  → marker: `plan`, then `gate:2`

- Write `plan` to `.ship-stage`.
- Invoke `superpowers:writing-plans` to produce ONE execution plan covering the **entire
  spec** — every task to build the whole feature, however many that is. Do **not** slice
  the feature into sequential ships/phases or defer specced surfaces; one plan, built in
  one pass. Run `ponytail` as the *waste* critic, not a scope critic — it cuts
  reinvention, over-abstraction, unneeded deps, and gold-plating, but never amputates
  specced scope (the spec is the floor). Save its cut-list of dropped *waste* and the
  markdown execution plan to the repo's docs home (e.g. `specs/plans/YYYY-MM-DD-<slug>.md`).
- Render the HTML **go-card** from `reference/go-card.html` — the meta only (contract
  below). Write `gate:2`, fire the gate notification, `open` the go-card, and **end the
  turn with a `needs input:` line** naming the ship + "go? (flip `/effort ultracode`
  first)". **HARD STOP — GATE 2.** Ultracode can't be auto-set mid-session (it's
  session-only, settable only via the interactive `/effort` picker), so GATE 2 — the
  last stop before BUILD — is where Pete flips it. Nudge, never assume he did.

### 3 · BUILD — automatic  → marker: `build:N:M` (N done of M tasks)

- Write `build:0:<M>` to `.ship-stage`; bump N as each task completes. Build **all M
  tasks** in one session — a big plan means a long build, and that is the job; don't stop
  partway or hand back a half-built feature. Commit each task on the branch as it lands
  (durable, resumable progress), but don't merge until the whole plan is built.
- Invoke `superpowers:subagent-driven-development`, driven by Opus.
- Invoke `router` to split each build task ~50/50 Opus ↔ GPT-5.5 (codex). Opus owns the
  brief, the diff review, the gates, and git. One writer per branch at a time.
- Apply `ponytail` posture (shortest diff, reuse, no reinvention).
- Run `superpowers:verify-before-done` before claiming any task done — actually run it.
- On a red test, `superpowers:systematic-debugging`.
- **Before BUILD is done, walk the whole feature end-to-end yourself** — invoke `verify`:
  boot the app and drive its *real* user paths (the spec's happy path + key edge cases),
  not just unit tests. *You* find the breakage, never Pete. Fix what breaks (loop with
  `systematic-debugging`); only leave BUILD once the live flow actually works. The review
  card's "walked it end-to-end" line is a promise — keep it true.
- Raise a hand only for a genuine fork (PM-framed, with a rec). Pete can jump in from
  FleetView anytime.

### 4 · REVIEW / MERGE — automatic  → marker: `review`, then remove the file

- Write `review` to `.ship-stage`.
- Run `/code-review` (correctness) + `ponytail-review` (over-build) — one pass.
- **Put it in front of Pete, running — every time.** For any visual/interactive feature
  (the default on this web stack), **boot the worktree's own dev server yourself** (its dev
  script — e.g. `next dev` — in the background) and `open http://localhost:<port>` (usually
  `:3000`) so the *live local app* is on his screen the instant he's asked to review. He
  walks through it on the worktree. **Never deploy to let him review, and never tell him to
  "go look at the live site"** — deploy is downstream of merge; the worktree's localhost is
  the review surface. (Non-UI change — CLI/library — show the demo/test output instead.)
- **Render a review card** from `reference/review-card.html` (contract below), write it to
  the repo's docs home (e.g. `specs/plans/review-<slug>.html`), and `open` it. Point it at
  the running localhost ("walk through it — it's already open"). **Never tell Pete to "go
  read the PR"** — the review comes to him, running and labeled.
- **The merge gate always holds for visual/substantial work.** Present the running app + the
  review card, end with a `needs input:` line ("review: <feature> — merge?"), and **wait.
  Never merge a UI Pete hasn't seen run** — a standing "go" authorizes the build, not the
  merge of an unseen feature. (Only a tiny, non-visual, watched change may `wt merge`
  directly.)
- On "merge", land it and **let worktrunk own teardown — a leftover worktree is a bug**:
  - **Tiny & watched →** `wt merge` (runs the repo's `wt.toml` pre-merge gate, squashes,
    ff's main, removes the worktree), then `ExitWorktree({action:"keep"})` to point the
    session back at the main checkout (wt already deleted the dir).
  - **Substantial (PR path) →** `gh pr merge --squash --delete-branch` — this deletes only
    the *remote* branch, so clean up locally so nothing piles up: `ExitWorktree({action:"keep"})`,
    then `wt remove feature/<slug> -f` to tear down the *local* worktree + branch, then
    `git -C <main-checkout> pull --ff-only` so local main matches. Nothing left on disk.
  - Then `rm .ship-stage` and **stop the review dev server you booted** (its worktree is being
    removed). Verify with `wt list` / `git worktree list` — zero ship worktrees should remain.
- If the repo auto-deploys on merge to main (CI), say so and hand back the live URL once it's
  up; otherwise just confirm merged. Never make Pete run a deploy himself.
- Run the RETRO below, then **end with a `result:` line**: what shipped, one sentence — and if
  RETRO filed a note, name it (`… · ship-retro #N filed`).

### 5 · RETRO — autonomous; only if the run taught us something  → no marker

Ship improves itself from its own runs — but the *running* agent never edits the skill. You're
shipping someone's feature, not doing skill surgery, and one run is too narrow a view to write a
*general* fix. So do a fast autonomous retro and **drop a note for the ship maintainer** — no
gate, no PR, no waiting on Pete.

If this run surfaced a real gap — Pete corrected the pipeline, a stage misfired, a step was
missing — file it as a GitHub issue on the skill's own repo (for this skill, `peteknowsai/ship`),
labeled `ship-retro`:

```
gh issue create -R peteknowsai/ship --label ship-retro --title "retro: <one-line gap>" \
  --body "<what happened · the gap · a suggested fix (which stage, roughly what to change) · the repo/feature it came from>"
```

Include the **suggested fix** so the maintainer has a concrete starting point — but you do NOT
open a PR or touch the skill. The ship-maintainer agent monitors the `ship-retro` label, batches
notes across runs into one *general* skill change, and reviews that PR with Pete.

- **Most runs teach nothing — skip silently.** Never invent a lesson; a clean run files no note.
  One real note beats five padded ones.
- Don't gate `result:` on this — file the note (or don't) and finish the run.

## The review card (REVIEW artifact)

Render `reference/review-card.html` filled with the meta only — PM-framed, one screen.
Pete reviews *this*, not the diff:

- **What you got** — plain-English bullets of what now works (what it *does*, not a file list).
- **What it looks like** — it's already **running for him at localhost** (you booted it); a
  screenshot/mockup goes here for the record.
- **Already checked for you** — gates/tests green, **the flow walked end-to-end (it runs)**;
  what was NOT touched (schema / money / public surfaces). Set his risk expectation.
- **Only you can confirm** — the 1–2 things that need his eye; walk through them on the open
  localhost.
- **Merge?** — the PR link is there for the curious, but he shouldn't need it. Merge is the
  point of no return (it deploys, if the repo auto-deploys) — only after he's seen it run.

## Gate signals — how a parked ship reaches Pete

When you hit a gate, three things fire so Pete notices whether he's watching or away:

1. **Status line** — the `gate:N` marker makes the line show `✋ <slug> — design?/go?` in
   bold amber. His in-session and in-dashboard glance.
2. **FleetView bucket** — end the turn with a line starting `needs input:` → the
   dashboard row jumps to the **awaiting input** group. (See the narration contract.)
3. **Desktop notification** — the gate Stop-hook fires a Ghostty notification
   (`<slug> → GATE N`) so an away-from-keyboard Pete gets a tap on the shoulder. Gates
   are rare, so this is never noisy.

## FleetView narration contract

The dashboard can't be styled, but it reflects the session. Make it a ship board:

- **Name** the session `ship:<slug>` at spawn (Pete types it, or v2 dockmaster passes
  `--name`). A running session can't rename itself reliably.
- **End every turn with a clean one-line status** (`🔨 build 4/5 · <slug>`,
  `📐 planning · <slug>`). The Haiku summarizer mirrors your latest line into the row —
  give it status-of-work, not an echo of the last tool call.
- **At a gate, the closing line starts `needs input:`** → row moves to *awaiting input*.
  **At merge, it starts `result:`** → row moves to *completed*. Mid-work narration keeps
  it in *working*.

## The go-card contract (GATE 2 artifact)

Render `reference/go-card.html` filled with the meta only — one screen, nothing more:

- **What gets built** — one line of scope.
- **Ponytail's cut-list** — what was dropped, and why.
- **Pete's 1–3 calls** — each a PM tradeoff *with your recommendation*. (Often zero —
  then say "nothing needs you" and it's a pure confirm.)
- **Risk** — one line.
- **Mockup thumbnail** — if the feature is visual, pulled from the design spec.
- **Flip to ultracode** — one line: BUILD runs at full power on ultracode; flip
  `/effort ultracode` before saying go (it can't be auto-set mid-session). The rainbow
  `⚡⚡⚡ ultra` badge in the status line confirms it took.

It is the *only* thing Pete reads before a build starts. Never make him read the plan.

## What this skill deliberately does NOT do

No arbitrary phasing — ship plans and builds the whole spec in one pass, never slicing a
specced feature into "Ship 1 of N" and stopping (phasing is Pete's to request, not ship's
to impose). No `executing-plans` (checkpoint-heavy — the opposite of hands-off). No strict
TDD by default (tests are a build deliverable; the pre-merge test gate is the backstop;
reserve test-first for money/auth). No manual git worktree management — `wt` owns the
worktree birth-to-death.
