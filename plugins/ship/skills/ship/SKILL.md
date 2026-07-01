---
name: ship
description: Use for any feature or multi-step change in a product/web repo — takes it from idea to merged through one Codex Desktop pipeline (worktree → discover → plan → build → review), gating only on design direction and "go". Auto-triggers on feature-shaped requests; you never type it. Do NOT use for a typo fix, a one-line change, or a question — those just get done. Never edit main directly.
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
   sees in Codex's in-app Browser. The execution plan is machine-facing markdown he never reads.
   HTML artifacts follow the **html-effectiveness patterns**
   (https://thariqs.github.io/html-effectiveness/): the thesis is that flows, options,
   and relationships are *spatial* information markdown flattens — so lead with a
   plain-English TL;DR, render structure as diagrams/side-by-sides instead of prose,
   put depth behind collapsibles, and make anything visual a *live* embed, not a
   description. Per-artifact pattern picks are named in each stage below.
2. **Two gates, only two.** GATE 1 = design direction (after DISCOVER). GATE 2 = go
   (after PLAN, via the go-card). Nothing else stops for him. Both gates are **HARD
   STOPS** — present the artifact and wait; never auto-advance past them.

**Who Pete is:** a technical PM, not an engineer. Translate technical calls to plain
product terms, give a recommendation, let him decide. His lane = product, design,
taste, scope. Your lane = mechanics — handle them, summarize in one line. The
**standing stack is never re-asked** — it's Pete's default product/web stack, declared in
his global Codex instructions / `~/.codex/AGENTS.md` (flue · Cloudflare · Convex · Clerk ·
Stripe · Next). **The repo's own `AGENTS.md` overrides it** when that repo diverges
(a non-web repo declares its own stack). Escalate a library choice only when it's both
architectural *and* outside the repo's canon.

**Codex prerequisites:** `superpowers`, `impeccable`, `ponytail`, and `router` must
be available. `worktrunk`/`wt` is optional: use it only when Pete explicitly wants
Worktrunk hooks/pathing/merge behavior for this run.

## The pipeline — create a todo for each stage

Each stage writes its marker to `.ship-stage` at the git root. The marker format is
below each stage.

## Codex screen + location contract

Pete must always know which checkout he is looking at.

- Include `branch <branch> · worktree <path>` in every normal status line, every
  `needs input:` line, and the final `result:` line.
- If Git is detached, label it `detached@<short-sha>` until a branch exists.
- Codex app owns worktree birth/cleanup by default. Do not create nested `wt`
  worktrees inside a Codex-managed worktree.
- Use the visible Codex app labels:
  - Project menu **Create permanent worktree** = long-lived reusable worktree project;
    not the default for a ship.
  - Chat menu **Fork into new worktree** = normal recovery path when the current
    thread is Local/main but the ship needs isolation.
  - Chat menu **Fork into local** = bring work back to Local only when Pete wants the
    foreground checkout.
- Prefer Codex's in-app Browser for every spec, go-card, review-card, and local app.
  For generated HTML files, serve the artifact directory on `localhost` and navigate the
  in-app Browser there. Raw `file://` URLs are not reliable in Codex.
- If the app already runs at `localhost`, open that URL directly in the in-app Browser.
- Fall back to macOS `open` or Chrome only when the in-app Browser is unavailable or Pete
  explicitly asks for it.

### 0 · Worktree sanity (invisible)

**Preferred start:** the thread is in Codex **Worktree** mode, based on `main`.
Codex creates a lightweight managed worktree, usually detached HEAD, under
`$CODEX_HOME/worktrees`.

Run:

```
git rev-parse --show-toplevel
git branch --show-current
git rev-parse --short HEAD
```

If this thread is already in a Codex-managed worktree or permanent worktree, proceed.
If it is in Local on `main`, do not edit files there: use **Fork into new worktree**
when available; otherwise stop with `needs input: click Fork into new worktree for
this ship`.

If Git is detached, make a real feature branch in the active Codex worktree before the
first commit:

```
git switch -c feature/<slug>
```

If the worktree already has a non-`main` branch, keep it. Write the first marker:
`printf 'discover' > <root>/.ship-stage`. Report `branch <branch|detached@sha> ·
worktree <path>`.

**Isolate the branch's backend if the repo has a preview lane.** A worktree that builds against
a *shared* backend (one Convex/DB deployment serving every branch) corrupts it — pushing this
branch's schema reconciles the shared plane to *this* branch and drops indexes other branches
added (the clobbering bug). So if the repo provisions a **per-branch backend**, do it now and
point the worktree at it, so BUILD and REVIEW never touch a shared plane (homezero:
`scripts/new-preview.sh <branch>` — spins up an isolated Convex preview seeded with real
content, prints the deploy key + backend URL to export into the worktree; see its `## Deploy
lanes` in AGENTS.md). No preview lane → just build against whatever dev stack the repo gives you.

**Cross-repo case — narrate the fork or it looks like nothing happened.** When ship runs
against a repo that is not the session's primary checkout, the Codex app may keep the visible
thread label pinned to the primary repo. In that case: work by absolute path, and state the
forked branch + worktree path in your narration the moment you create it
(`forked feature/<slug> off main @ <path>`). Pete watches for the worktree from the get-go;
if the app breadcrumb can't show it, your words must.

### 1 · DISCOVER — Pete's taste, up front  → marker: `discover`, then `gate:1`

- Invoke `superpowers:brainstorming`. PM-framed, one question at a time.
- For any visual/UI feature, also run `impeccable` — the HTML design sprint (use `/pix`
  for imagery freely). The spec *is* the prototype.
- **Ground the design in the *live* product, not stale artifacts.** Before designing any
  visual feature, look at what's actually shipped — boot the app (its dev script) or open
  the deployed URL and *see* the current surface and its real theme/CSS. In-repo mockups
  (`design/`, old specs) drift and read as current when they're not; the running app is the
  design source of truth. (A run once designed against a repo's old cream mockups while the
  live product had moved to a dark terminal UI — caught only at GATE 1, the whole spec redone.)
- Produce ONE self-contained HTML spec in the repo's docs home (`specs/` or `docs/`,
  whichever it uses) — e.g. `specs/designs/YYYY-MM-DD-<slug>.html`. Design the **whole**
  feature here — every surface and behavior Pete wants in scope — because this spec is the
  scope contract PLAN and BUILD execute in full. A big feature is a big spec; don't trim
  it to a slice.
- **Shape the spec on the html-effectiveness patterns** — it's an explainer Pete decides
  from, not a document he studies: `14-research-feature-explainer` is the body (TL;DR
  first, collapsible depth, no wall of prose); when GATE 1 is a genuine *direction*
  choice, present it as `02-exploration-visual-designs` — 2–3 **live-rendered**
  directions side-by-side with one-line tradeoffs, so Pete picks by looking, not
  reading; embedded mockups are live/interactive (`07`/`08-prototype`) — the spec *is*
  the prototype; any flow or pipeline is a diagram (`13-flowchart-diagram`), never a
  paragraph pretending to be one.
- Write `gate:1` to `.ship-stage`, fire the gate notification (see "Gate signals"),
  open the spec in the in-app Browser, and **end the turn with a `needs input:` line**
  naming the ship + "design direction?" + `branch <branch> · worktree <path>`.
  **HARD STOP — GATE 1.** Wait for approval.

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
  below). Write `gate:2`, fire the gate notification, open the go-card in the in-app
  Browser, and **end the turn with a `needs input:` line** naming the ship + "go?" +
  `branch <branch> · worktree <path>`. **HARD STOP — GATE 2.** Codex effort is
  configured outside the skill; do not invent an effort-gate ritual.

### 3 · BUILD — automatic  → marker: `build:N:M` (N done of M tasks)

- Write `build:0:<M>` to `.ship-stage`; bump N as each task completes. Build **all M
  tasks** in one session — a big plan means a long build, and that is the job; don't stop
  partway or hand back a half-built feature. Commit each task on the active feature branch
  as it lands (durable, resumable progress), but don't merge until the whole plan is built.
- Invoke `superpowers:subagent-driven-development` when the plan has independent build
  tasks.
- Invoke `router` to decide which tasks stay in the current Codex session versus another
  available engine. This session owns the brief, diff review, verification gates, and git.
  One writer per branch at a time.
- **Single-writer vs fan-out — pick by the diff, not by reflex**. The default is
  one writer on the branch: right for a small, interdependent, or design-coherent feature,
  where parallel writers just race on the shared checkout for no gain. Fan out writers (each
  in its own worktree, merged back) ONLY when tasks are genuinely independent *and* numerous
  enough that isolation + merge beats serialized commits — a large migration, a broad
  mechanical sweep. The high-value place to fan out is the **review**, regardless of build
  size: independent reviewers per dimension + adversarial verification (see REVIEW). Don't
  parallelize 5 small edits; do parallelize 5 verifiers.
- Apply `ponytail` posture (shortest diff, reuse, no reinvention).
- Run `superpowers:verification-before-completion` before claiming any task done — actually run it.
- On a red test, `superpowers:systematic-debugging`.
- **Before BUILD is done, walk the whole feature end-to-end yourself** — a quick *self-driven*
  smoke-walk (the formal fresh-agent `verify` skill runs in REVIEW, not here — don't invoke it
  twice): boot the app and drive its *real* user paths (the spec's happy path + key edge cases),
  not just unit tests. *You* find the breakage, never Pete. Fix what breaks (loop with
  `systematic-debugging`); only leave BUILD once the live flow actually works. The review card's
  end-to-end promise ("it runs" — backed by REVIEW's verify pass) must stay true.
- Raise a hand only for a genuine fork (PM-framed, with a rec). Pete can jump in from
  the thread anytime.

### 4 · REVIEW / MERGE — automatic  → marker: `review`, then remove the file

- Write `review` to `.ship-stage`.
- Run a correctness code review (`/code-review` where available) + `ponytail-review`
  (over-build) — one pass.
- **Design QA for visual features — invoke `impeccable` in critique mode** against the
  running worktree app, with the GATE 1 spec as the bar. DISCOVER used impeccable to set
  the design bar; nobody but this pass checks the *built* feature clears it (verify's
  taste notes are a smoke test, not a design review). Findings are triaged like
  ponytail-review's: real gaps get fixed before the card, nits land on the card as
  "Verifier flagged / suggested" for Pete to judge.
- **Put it in front of Pete, running — every time.** For any visual/interactive feature
  (the default on this web stack), **boot the worktree's own dev server yourself** (its dev
  script — e.g. `next dev` — in the background) and open `http://localhost:<port>` (usually
  `:3000`) in the in-app Browser so the *live local app* is on his screen the instant he's
  asked to review. He walks through it on the worktree. **Never deploy to let him review,
  and never tell him to "go look at the live site"** — deploy is downstream of merge; the
  worktree's localhost is the review surface. (Non-UI change — CLI/library — show the
  demo/test output instead.)
- **Prove it actually works — invoke `verify` before the card.** With the app running,
  invoke the `verify` skill against the worktree's localhost. A fresh read-only sub-agent
  drives the feature, screenshots the beats, and returns `works | broken | unverifiable` +
  taste notes; verify loops-to-fix (cap ~3). **`broken` after the cap, or `unverifiable`, →
  do NOT proceed to merge: end the turn with a `needs input:` line ("review: <feature> —
  couldn't prove it works: <reason>") and hand Pete the verdict + evidence.** Only a `works`
  verdict (with its screenshot storyboard + any taste notes) flows into the card below; if verify
  crystallized an e2e spec for a core journey, name that path in "Already checked for you".
- **Render a review card** from `reference/review-card.html` (contract below), write it to
  the repo's docs home (e.g. `specs/plans/review-<slug>.html`), and open it in the in-app
  Browser. Point it at the running localhost ("walk through it — it's already open").
  **Never tell Pete to "go read the PR"** — the review comes to him, running and labeled.
- **The merge gate always holds for visual/substantial work.** Present the running app + the
  review card, end with a `needs input:` line ("review: <feature> — merge?") that includes
  `branch <branch> · worktree <path>`, and **wait. Never merge a UI Pete hasn't seen run**
  — a standing "go" authorizes the build, not the merge of an unseen feature.
- **When Pete asks for changes at the card, apply `superpowers:receiving-code-review`** —
  verify the ask against the code before implementing (his feedback is product-true but
  may be technically underspecified), do the work, then loop the changed flow back
  through `verify` before re-presenting. Never blind-implement and re-card.
- On "merge", land it through the Codex-app/PR path:
  1. Push the feature branch and open a PR if one does not already exist.
  2. Merge with Codex's Git UI or `gh pr merge <#> --squash --delete-branch` from a main
     checkout. If local `main` is checked out elsewhere, do not run `gh pr merge` inside the
     Codex-managed branch worktree; it can merge remotely and then fail locally on checkout.
  3. Stop the review dev server, remove `.ship-stage`, and deprovision the per-branch preview
     backend if Stage 0 spun one up. Leave Codex-managed worktree cleanup to Codex/archive.
     Do not run `wt remove` for Codex-managed worktrees.
  4. If Pete needs the work in Local, use **Fork into local** instead of checking out the same
     branch in two places.
- **Ship deploys to the integration lane, never to production.** After the merge, push merged
  main to the repo's shared *dev/integration* lane if it has one — run its dev-deploy step **from
  the main checkout** (homezero: `scripts/deploy-dev.sh`, the single serialized writer for the
  shared dev plane; never run it from a worktree — that's the clobbering bug again), then hand
  back that lane's URL (homezero: `dev.homezero.md`). If the repo just auto-deploys on merge via
  CI, say so and hand back the URL once it's up; if it has no deploy step, confirm merged. Never
  make Pete run a deploy himself.
- **Promotion to production is NOT ship's job — shipping ends at the integration lane.** On the
  three-lane model this assumes (a separate prod promote), "merged" means live on *dev*, not live
  for users — so never deploy or promote to prod / `www`, never add a promote gate or offer to
  promote (homezero: `scripts/promote-to-prod.sh` is a separate, human-gated ritual Pete runs on
  his own cadence — deliberately outside the pipeline). (Only where merge auto-deploys straight to
  prod is a merge itself the user-facing release — the review-card "Merge?" line covers that case.)
  Hand back the dev URL and stop there.
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
It's a `17-pr-writeup` for a PM: what changed and why with visual before/after evidence,
never a file tour. Pete reviews *this*, not the diff:

- **What you got** — plain-English bullets of what now works (what it *does*, not a file list).
- **Proof it works** — the verifier's captioned screenshot **storyboard** (start → action →
  success) with the `works` verdict on top. This replaces a static mockup: it's evidence the
  running feature does what was intended, organized for a glance. It's also still **running for
  him at localhost** (you booted it). (Non-visual change — show the demo/test output instead.)
- **Already checked for you** — gates/tests green, **the flow driven end-to-end by a fresh
  agent (it runs)**, plus any **e2e spec verify committed** for a core journey (name it — that
  path is a standing test now); what was NOT touched (schema / money / public surfaces). Set his
  risk expectation.
- **Verifier flagged / suggested** — the verifier's taste notes ("looked off / couldn't
  confirm"), if any. These are *reports, not work* — Pete decides: fix now / backlog / ignore.
- **Only you can confirm** — the 1–2 things that need his eye; walk through them on the open
  localhost.
- **Merge?** — the PR link is there for the curious, but he shouldn't need it. Merge lands the
  feature on the **integration lane** (dev where the repo has one, else just main) — not on
  users, so it's a reversible, low-stakes yes once he's seen it run. (Only where merge
  auto-deploys straight to prod is it the point of no return — treat it that way there.)

## Gate signals — how a parked ship reaches Pete

When you hit a gate, three things fire so Pete notices whether he's watching or away:

1. **Marker** — write `gate:N` to `.ship-stage` so the thread, scripts, and humans can
   see the parked state.
2. **Thread line** — end the turn with `needs input:` plus `branch <branch> · worktree
   <path>`. At merge, end with `result:` plus the same label.
3. **Desktop notification** — if the copied plugin has `hooks/gate-notify.sh`, run it
   manually after writing the marker. Codex does not wire that script automatically.

## Codex narration contract

The app reflects the latest useful status. Make it a ship board:

- **End every turn with a clean one-line status** (`build 4/5 · <slug>`,
  `planning · <slug>`), ending with `branch <branch> · worktree <path>`. Give
  status-of-work, not an echo of the last tool call.
- **At a gate, the closing line starts `needs input:`**.
- **At merge, it starts `result:`**.

## The go-card contract (GATE 2 artifact)

Render `reference/go-card.html` filled with the meta only — one screen, nothing more
(the template is a `16-implementation-plan` boiled down to its decision surface —
scope, calls, risk — everything else stays in the machine-facing plan):

- **What gets built** — one line of scope.
- **Ponytail's cut-list** — what was dropped, and why.
- **Pete's 1–3 calls** — each a PM tradeoff *with your recommendation*. (Often zero —
  then say "nothing needs you" and it's a pure confirm.)
- **Risk** — one line.
- **Mockup thumbnail** — if the feature is visual, pulled from the design spec.
- **Go** — one line: BUILD starts after Pete says go.

It is the *only* thing Pete reads before a build starts. Never make him read the plan.

## What this skill deliberately does NOT do

No arbitrary phasing — ship plans and builds the whole spec in one pass, never slicing a
specced feature into "Ship 1 of N" and stopping (phasing is Pete's to request, not ship's
to impose). No `executing-plans` (checkpoint-heavy — the opposite of hands-off). No strict
TDD by default (tests are a build deliverable; the pre-merge test gate is the backstop;
reserve test-first — `superpowers:test-driven-development` — for money/auth paths). No default
Worktrunk birth/death inside Codex — Codex owns managed worktrees unless Pete explicitly chooses
`wt`. No promoting to production — ship ends at the integration lane (dev); promotion to prod /
`www` is a separate, human-gated ritual Pete runs, never ship's to deploy, gate, or offer.
