---
name: ship
description: Use for any feature or multi-step change in a product/web repo — takes it from idea to merged through one pipeline (worktree → discover → plan → build → review), gating only on design direction and "go". Auto-triggers on feature-shaped requests; you never type it. Do NOT use for a typo fix, a one-line change, or a question — those just get done. Never edit main directly.
---

# /ship — idea to merged, in one command

You run a feature from idea to merged. Pete is heavy in DISCOVER (his taste), glances
at one card mid-way (go), and comes back at the end. Everything between and after the
two gates is automatic.

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

### 1 · DISCOVER — Pete's taste, up front  → marker: `discover`, then `gate:1`

- Invoke `superpowers:brainstorming`. PM-framed, one question at a time.
- For any visual/UI feature, also run `impeccable` — the HTML design sprint (use `/pix`
  for imagery freely). The spec *is* the prototype.
- Produce ONE self-contained HTML spec in the repo's docs home (`specs/` or `docs/`,
  whichever it uses) — e.g. `specs/designs/YYYY-MM-DD-<slug>.html`.
- Write `gate:1` to `.ship-stage`, fire the gate notification (see "Gate signals"),
  `open` the spec, and **end the turn with a `needs input:` line** naming the ship +
  "design direction?". **HARD STOP — GATE 1.** Wait for approval.

### 2 · PLAN — automatic  → marker: `plan`, then `gate:2`

- Write `plan` to `.ship-stage`.
- Invoke `superpowers:writing-plans`. Run `ponytail` as the scope critic — produce a
  cut-list. Save the markdown execution plan to the repo's docs home (e.g.
  `specs/plans/YYYY-MM-DD-<slug>.md`).
- Render the HTML **go-card** from `reference/go-card.html` — the meta only (contract
  below). Write `gate:2`, fire the gate notification, `open` the go-card, and **end the
  turn with a `needs input:` line** naming the ship + "go?". **HARD STOP — GATE 2.**

### 3 · BUILD — automatic  → marker: `build:N:M` (N done of M tasks)

- Write `build:0:<M>` to `.ship-stage`; bump N as each task completes.
- Invoke `superpowers:subagent-driven-development`, driven by Opus.
- Invoke `router` to split each build task ~50/50 Opus ↔ GPT-5.5 (codex). Opus owns the
  brief, the diff review, the gates, and git. One writer per branch at a time.
- Apply `ponytail` posture (shortest diff, reuse, no reinvention).
- Run `superpowers:verify-before-done` before claiming any task done — actually run it.
- On a red test, `superpowers:systematic-debugging`.
- Raise a hand only for a genuine fork (PM-framed, with a rec). Pete can jump in from
  FleetView anytime.

### 4 · REVIEW / MERGE — automatic  → marker: `review`, then remove the file

- Write `review` to `.ship-stage`.
- Run `/code-review` (correctness) + `ponytail-review` (over-build) — one pass.
- **Render a review card** from `reference/review-card.html` (contract below), write it to
  the repo's docs home (e.g. `specs/plans/review-<slug>.html`), and `open` it. **Never tell
  Pete to "go read the PR"** — the review comes to him, labeled, in plain terms. He glances
  and answers in Claude Code.
- **Tiny & watched → merge directly** (`wt merge`). **Substantial → open the PR *and* the
  review card, then end with a `needs input:` line ("review: <feature> — merge?").** Wait.
- On "merge": `wt merge` (or squash-merge the PR with `--delete-branch`) — runs the
  pre-merge test gate (whatever the repo's `wt.toml` defines), lands spec + plan + code,
  deletes the branch, removes the worktree. Then `rm .ship-stage`.
- End with a `result:` line: what shipped, one sentence.

## The review card (REVIEW artifact)

Render `reference/review-card.html` filled with the meta only — PM-framed, one screen.
Pete reviews *this*, not the diff:

- **What you got** — plain-English bullets of what now works (what it *does*, not a file list).
- **What it looks like** — a screenshot/mockup, for any user-facing or visual change.
- **Already checked for you** — gates/tests green; what was NOT touched (schema / money /
  public surfaces). Set his risk expectation.
- **Only you can confirm** — the 1–2 things that need his eye (a visual, a behavior).
- **Merge?** — the PR link is there for the curious, but he shouldn't need it.

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

It is the *only* thing Pete reads before a build starts. Never make him read the plan.

## What this skill deliberately does NOT do

No `executing-plans` (checkpoint-heavy — the opposite of hands-off). No strict TDD by
default (tests are a build deliverable; the pre-merge test gate is the backstop;
reserve test-first for money/auth). No manual git worktree management — `wt` owns the
worktree birth-to-death.
