---
name: pipeline
description: Use for any code change in a product/web repo, quick fix to full feature — ship sizes the ceremony itself and stops only when Pete's taste is in play. Explicit verbs pin the process — "/ship express <tweak>", "/ship design <idea>", "/ship next" (ship the board's Next column as a batch); anything else sizes itself. EXPRESS (tweak — no spec/plan, straight through to dev), SELF-DIRECTED (writes its own spec+plan, builds, reviews, merges, deploys — zero stops), or GATED (design direction + "go" gates) — gates fire only when Pete's answer would change what gets built. Auto-triggers on change requests; you never type it. Do NOT use for a question or pure analysis. Never edit main directly.
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

## Verbs — Pete pins the process explicitly

If the invocation's first word is `express`, `design`, or `next`, that verb
**pins the process and skips the sizing judgment below**. Anything else — bare
`/ship <idea>` or the auto-trigger — sizes the lane exactly as today. Verbs are
overrides, not a menu. Every verb rides the same rails as every lane: **stage 0's
worktree off main via `wt`, never a primary checkout**.

**The fork is the verb's FIRST act — before any question, recon agent, or authoring
step.** The moment a verb lands, resolve the target repo, then immediately run
stage 0 there: `wt switch --create`, enter the worktree, write `.ship-stage`. That
marker flip is how Pete *sees* ship engage — a verb that spawns recon or asks
questions while still parked on main looks like nothing happened, and that's a bug,
not a sequencing choice. One exception: `/ship next`'s board sweep is read-only —
each *queued ship* forks as its own first act instead.

- **`/ship express <tweak>`** — pins EXPRESS. The verb pins ceremony *down*, never
  safety down: if the change turns out to touch schema/auth/money or a taste call,
  promote per the mid-flight rule regardless of the pin.
- **`/ship design <idea>`** — pins GATED and mandates the full design walkthrough in
  DISCOVER: clarifying questions one at a time, 2–3 approaches with a recommendation,
  the HTML spec with a live mockup, GATE 1 — then the normal pipeline through to dev.
  The verb is Pete asserting taste is in play; never downgrade it to SELF-DIRECTED
  however mechanical the work looks.
- **`/ship next`** — ship the board's **Next column** as one batch (board-backed repos
  only; no board → say so and stop). Moving a card to Next is Pete's "build this"
  signal; this verb is how the column gets worked:
  1. **Sweep + enrich.** Pull every Next card. Bring each up to the backlog skill's
     standard anatomy (What / Why / Done when) from card context + the repo before
     judging it — a thin ticket enriched now is a ship that doesn't stall later.
  2. **Triage** each card, Fable's judgment: **ship-now** (intent clear, no taste
     call — the spec is inferable), **needs-design** (Pete's taste or direction
     genuinely in play — same test as the GATED lane), or **too-thin** (can't design
     it without Pete). Narrate the three lists before firing anything.
  3. **Fire ship-now as a sequential queue** — one ship at a time, each a normal lane
     run with its own worktree, full pipeline, own card flow (In Progress → … →
     For Review). **Never a parallel swarm**: merges serialize onto main, one preview
     backend at a time, and a failed ship parks that card (comment why) and moves to
     the next — one bad ticket never stalls the queue.
  4. **Bulk GATE 1 for needs-design: ONE design doc, one sitting.** A single HTML —
     a section per ticket: proposed direction, mockup where visual, and the one
     question that matters. Publish to the specs host, comment the link on each
     ticket, present it once. **Pete's section-by-section approval is the only human
     gate in the batch** — approved sections run straight through (plan machine-facing,
     no per-ticket go-card; the For Review column + dev lane are the net) and join the
     queue. Sections he redirects get revised and re-presented; nothing builds on a guess.
  5. **Too-thin cards** stay in Next: comment the one clarifying question on each and
     name them in narration. They ship on a later `/ship next`, once answered.
  End with a batch `result:` line: `shipped N · awaiting design answers M · too thin K`.

## Sizing — every change ships; you pick the ceremony, and gates exist only for Pete's taste

The rails are constant: worktree off main → change → prove it → merge → dev lane —
**nothing ever edits main directly, however tiny, and Pete does nothing unless a
gate genuinely needs him.** What scales is the ceremony, and **you size it, not
Pete** — he asks for what he wants; you figure out what that takes. Three lanes:

- **EXPRESS — a quick tweak or fix.** Whole diff visible before you start, no
  schema/auth/money. No spec, no plan, no cards, no stops: worktree → change → repo
  gates (tsc/tests) → self-drive the affected flow → `wt merge` → dev lane →
  `result:` line. Bring a dab of `ponytail` (smallest diff that works) and, for
  anything visual, a dab of `impeccable` (the tweak should look intentional, not
  patched). Pete finds out it's done from the `result:` line, not before.
- **SELF-DIRECTED — real work that doesn't need Pete's eye.** Too big to freehand,
  but no product-direction or taste question in it: write whatever spec/plan *you*
  need to build it well (machine-facing, in the docs home, `ponytail` as waste
  critic; `impeccable` posture for any visual surface) — then build, run the REVIEW
  machinery (codex adversarial review + `verify` — a `works` verdict is the merge bar), merge,
  deploy to dev, `result:` line. **Zero stops — the artifacts are for the record,
  not for approval.**
- **GATED — Pete's taste or direction is genuinely in play.** A new user-facing
  surface, visual identity, a product tradeoff, ambiguous scope, schema/auth/money —
  the two-gate pipeline below, unchanged.

**The gate test is never size — it's whether Pete's answer would change what gets
built** (or the change is risky/irreversible). If his input wouldn't change the
outcome, don't stop; if it would, gate — that's the whole reason gates exist.
**Autonomous lanes merge only on green gates + a `works` verdict** — anything less
parks and asks instead of merging broken work. Mid-flight, promote the moment taste
or direction appears (park, write the spec from what you've learned, present
GATE 1); size alone just moves EXPRESS → SELF-DIRECTED, never to a gate. Never use
an autonomous lane to slip a taste call past Pete.

**The engine ladder (conserve Fable):** the driver — Fable — is the scarcest
inference in the pipeline; spend it only on what needs its judgment (design,
planning, briefs, triage, gates, git — the final say). **Browser-driving is
always an Opus subagent** (`Agent(model: opus)`): verify, impeccable critique,
live-product grounding — never drive Playwright/Chrome from the driver. Heavy
non-judgment inference (correctness review, mechanical recon, drafting code)
goes to GPT-5.6 sol per the router. Sonnet never. **One amendment (Pete's call,
2026-07-06): a dispatch has ~5–10 min of fixed overhead (brief, launch, poll,
read result) — work smaller than that overhead, the driver does inline.** A
rename, a config line, wiring a triaged review fix: dispatching it costs more
wall-clock than doing it. Real features still go to codex; browser-driving is
Opus with no size exception.

**Never idle while a dispatch runs.** Waiting is the pipeline's biggest time
sink — a codex review or Opus QA pass is 10–25 minutes, and a driver that just
watches it wastes the whole window. While anything is dispatched, work the
standing non-tree list (none of it violates one-writer-per-branch: the
dispatch owns the working tree, these don't touch it): draft the review card,
write the Linear punch-list update and closing comment, publish the spec, prep
the commit message, groom remaining `/ship next` cards. The goal: when a
dispatch lands, everything around it is already done — the stage closes in
minutes. Same posture at gates: notify, then keep doing non-gated work while
Pete decides.

**Two principles, always:**

1. **The meta rule.** Every artifact Pete sees is a condensed HTML page — he reads the
   *meta*, never the full spec or plan. The spec (design) and the go-card are HTML he
   opens in the browser. The execution plan is machine-facing markdown he never reads.
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
his global instructions (`~/.claude/CLAUDE.md` in Claude Code, AGENTS.md / global
Codex instructions in Codex): flue · Cloudflare · Convex · Clerk · Stripe · Next.
**The repo's own `CLAUDE.md` / `AGENTS.md` overrides it** when that repo diverges
(a non-web repo declares its own stack). Escalate a library choice only when it's both
architectural *and* outside the repo's canon.

## The pipeline — create a todo for each stage

Each stage writes its marker to `.ship-stage` at the git root (the status line + the
FleetView row read it). The marker format is below each stage.

The pipeline below is written for Claude Code (the primary harness). When the driver
is a **Codex Desktop** session, the same pipeline runs with different mechanics —
see **"Running under Codex Desktop"** near the end; its swaps override the
worktree/browser/merge specifics below.

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
then enter/use the path from the JSON. Claude Code: `EnterWorktree({path})`. Codex:
set subsequent tool working directories to that path (or use absolute paths). `--no-cd`
is load-bearing. If the repo has a `.config/wt.toml`, it auto-provisions the worktree (gitignored runtime
files — node_modules, .env, .dev.vars — via reflink). Write the first marker:
`printf 'discover' > <root>/.ship-stage`. Never build on main.

**Isolate the branch's backend if the repo has a preview lane.** A worktree that builds against
a *shared* backend (one Convex/DB deployment serving every branch) corrupts it — pushing this
branch's schema reconciles the shared plane to *this* branch and drops indexes other branches
added (the clobbering bug). So if the repo provisions a **per-branch backend**, do it now and
point the worktree at it, so BUILD and REVIEW never touch a shared plane (homezero:
`scripts/new-preview.sh <branch>` — spins up an isolated Convex preview seeded with real
content, prints the deploy key + backend URL to export into the worktree; see its `## Deploy
lanes` in AGENTS.md). No preview lane → just build against whatever dev stack the repo gives you.

**Cross-repo case — narrate the fork or it looks like nothing happened.** `EnterWorktree`
only adopts worktrees of the **session's primary repo**. When ship runs against a *different*
repo (iterating on the ship plugin itself, or any repo that isn't this session's primary),
`EnterWorktree` silently won't take, the session cwd never moves, and the status line stays
pinned to the primary repo — `.ship-stage` is written in the feature repo the status line
isn't watching, so the worktree + stage are **real but invisible**. In that case: work the
worktree by **absolute path**, and **state the forked branch + worktree path in your narration
the moment you create it** (`forked feature/<slug> off main @ <path>`) — a blind status line
must never make it look like nothing forked. Pete watches for the worktree from the get-go; if
the breadcrumb can't show it, your words must.

**Opportunistic tidy (anti-accumulation):** glance at `git worktree list` first and
`wt remove <branch> -f` any worktree whose branch is already merged and its remote shows
`[gone]` (a finished ship that wasn't torn down). Only ever touch merged+gone worktrees —
never one with unmerged work. This + stage 4's teardown means ship worktrees never pile up.

### 1 · DISCOVER — Pete's taste, up front  → marker: `discover`, then `gate:1`

- Invoke `superpowers:brainstorming`. PM-framed, one question at a time.
- **Mechanical recon runs on GPT-5.6 sol, synthesis stays with the driver.** When
  grounding needs codebase evidence-gathering (what's the current state of X,
  where does Y live, summarize this subsystem), dispatch a background
  `codex exec … < /dev/null` **briefed read-only** (report findings, edit
  nothing — see the router skill's quick-reference) instead of burning
  Max-quota agents on reading. The driver — Fable — does the actual design and
  every judgment call from that evidence; recon is the only part that leaves.
- **The recon brief includes a reuse audit:** for every core noun the feature
  introduces (a table, module, event type, helper), grep the WHOLE repo — data
  layer included, not just the subsystem in focus — for existing infra of that
  name before the plan treats it as new. Extend-it beats build-it (a plan once
  specced a fresh `events` table the repo already had; three tasks got
  rewritten mid-build).
- **Bug-shaped requests ("X isn't working") get an empirical root-cause check
  before the spec commits to a cause:** reproduce the failure or read the
  actual runtime evidence (logs, live session transcripts, dependency health)
  and write the *observed* cause with its evidence — never spec a fix from a
  hypothesis. (A hypothesized cause once produced a fix that would have made
  an agent fabricate data; the real cause was a 500ing dependency.)
- For any visual/UI feature, also run `impeccable` — the HTML design sprint (use `/pix`
  for imagery freely). The spec *is* the prototype.
- **Ground the design in the *live* product, not stale artifacts.** Before designing any
  visual feature, look at what's actually shipped — boot the app (its dev script) or open
  the deployed URL and *see* the current surface and its real theme/CSS. **An Opus
  subagent does the driving** (browser tools are always Opus, never the driver): it
  walks the relevant surfaces, saves screenshots, and reports the real theme/CSS;
  the driver Reads the key screenshots and designs from them. In-repo mockups
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
  turn with a `needs input:` line** naming the ship + "go?". **HARD STOP — GATE 2.**
  (No effort/ultracode nudge — BUILD's writers are mostly codex now; run at whatever
  effort the session already has.)

### 3 · BUILD — automatic  → marker: `build:N:M` (N done of M tasks)

- Write `build:0:<M>` to `.ship-stage`; bump N as each task completes. Build **all M
  tasks** in one session — a big plan means a long build, and that is the job; don't stop
  partway or hand back a half-built feature. Commit each task on the branch as it lands
  (durable, resumable progress), but don't merge until the whole plan is built.
- Invoke `superpowers:subagent-driven-development`, driven by the harness model (the driver).
- Invoke `router` to dispatch each build task — currently all drafting goes to
  GPT-5.6 **sol** (codex, xhigh, Fast mode; always the sol variant, never plain
  gpt-5.6) — Sonnet never, and the router skill owns the engine dial (Pete's —
  read it there, don't restate it here). The driver owns the brief, the diff
  review, the gates, and git. One writer per branch at a time.
- **Single-writer vs fan-out — pick by the diff, not by reflex** (matters most under
  ultracode, where "always orchestrate" tempts you to parallelize the build). The default is
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
  not just unit tests. Two smoke-walk preconditions that have each cost a red deploy: **if the
  change touches a framework with its own production build** (`flue build`, `next build`,
  wrangler/vite bundling), **run that build too** — tsc+vitest green ≠ deployable; and **if the
  branch touched `convex/`, re-push it to the per-branch preview first**
  (`npx convex deploy --preview-name <branch> -y`) — the preview holds stage-0 code and drifts
  behind every Convex commit. *You* find the breakage, never Pete. Fix what breaks (loop with
  `systematic-debugging`); only leave BUILD once the live flow actually works. The review card's
  end-to-end promise ("it runs" — backed by REVIEW's verify pass) must stay true.
- Raise a hand only for a genuine fork (PM-framed, with a rec). Pete can jump in from
  FleetView anytime.

### 4 · REVIEW / MERGE — automatic  → marker: `review`, then remove the file

- Write `review` to `.ship-stage`.
- **First: sync with main.** `git fetch origin`; if `origin/main` has commits the
  branch lacks, absorb it *in the worktree* (rebase, or merge when rebase is
  unsafe), re-run the repo gates, and only then dispatch the review — on
  multi-session days main moves under every long ship, and a review against a
  stale fork reviews apparent reversions of other ships' work (it has wasted
  full review runs). Repeat right before the merge if main moved again during
  REVIEW.
- **Freeze the tree while a verifier is driving.** A live verify round holds a
  read lock on the worktree: no merges, rebases, or edits until its verdict
  lands — a mid-round `git merge` once left conflict markers in a hot-reloading
  file, broke the dev server under the verifier, and wasted the whole Opus
  round. Absorb upstream *before* dispatching the next round, never during.
- **Correctness review runs on GPT-5.6 sol — codex's native review mode, launched
  first so it works while the rest of REVIEW proceeds.** From the worktree,
  background dispatch (router quick-reference rules apply — `< /dev/null`,
  `-o` result file):
  `codex exec review --base <lane-target-branch> -o <result-file> < /dev/null`
  **No focus prompt** — codex rejects `[PROMPT]` alongside `--base` (or any
  diff-source flag); review mode picks the diff and applies its own bug-hunt
  rubric. Name the result file after the feature slug so the run is
  attributable in `ps`. The over-build sweep (reinvented stdlib, speculative
  abstraction, unneeded deps) is the driver's: run `ponytail-review` while
  codex works. Review mode is
  read-only by construction and computes the diff itself. Review inference is
  heavy and codex is the unlimited plan — spend GPT-5.6 sol here, save Opus/Max
  for judgment. Read the result file before the card; the **driver triages
  every finding** — adversarial reviewers over-flag by design, so verify each
  claimed bug against the code (receiving-code-review posture), fix what's
  real, put judgment calls on the card. codex unavailable → fall back to
  `/code-review` + `ponytail-review` on the driver.
- **Design QA for visual features — an Opus subagent runs `impeccable` in critique
  mode** (`Agent(model: opus)` — it drives the running worktree app with browser
  tools, and browser-driving is always Opus, never the driver) with the GATE 1
  spec as the bar. DISCOVER used impeccable to set the design bar; nobody but this
  pass checks the *built* feature clears it (verify's taste notes are a smoke
  test, not a design review). The driver triages its findings: real gaps get
  fixed before the card, nits land on the card as "Verifier flagged / suggested"
  for Pete to judge.
- **Put it in front of Pete, running — every time.** For any visual/interactive feature
  (the default on this web stack), **boot the worktree's own dev server yourself** (its dev
  script — e.g. `next dev` — in the background) and `open http://localhost:<port>` (usually
  `:3000`) so the *live local app* is on his screen the instant he's asked to review. He
  walks through it on the worktree. **Never deploy to let him review, and never tell him to
  "go look at the live site"** — deploy is downstream of merge; the worktree's localhost is
  the review surface. (Non-UI change — CLI/library — show the demo/test output instead.)
- **Prove it actually works — invoke `verify` before the card.** With the app running,
  invoke the `verify` skill against the worktree's localhost. A fresh read-only **Opus**
  sub-agent drives the feature, screenshots the beats, and returns `works | broken | unverifiable` +
  taste notes; verify loops-to-fix (cap ~3). **`broken` after the cap, or `unverifiable`, →
  do NOT proceed to merge: end the turn with a `needs input:` line ("review: <feature> —
  couldn't prove it works: <reason>") and hand Pete the verdict + evidence.** Only a `works`
  verdict (with its screenshot storyboard + any taste notes) flows into the card below; if verify
  crystallized an e2e spec for a core journey, name that path in "Already checked for you".
- **Render a review card** from `reference/review-card.html` (contract below), write it to
  the repo's docs home (e.g. `specs/plans/review-<slug>.html`), and `open` it. Point it at
  the running localhost ("walk through it — it's already open"). **Never tell Pete to "go
  read the PR"** — the review comes to him, running and labeled.
- **The merge gate always holds for GATED ships.** Present the running app + the
  review card, end with a `needs input:` line ("review: <feature> — merge?"), and **wait.
  Never merge a gated UI Pete hasn't seen run** — a standing "go" authorizes the build, not
  the merge of an unseen feature. (EXPRESS / SELF-DIRECTED ships merge autonomously — their
  bar is green gates + verify's `works`, per Sizing — and a tiny, non-visual, watched change
  may `wt merge` directly.)
- **When Pete asks for changes at the card, apply `superpowers:receiving-code-review`** —
  verify the ask against the code before implementing (his feedback is product-true but
  may be technically underspecified), do the work, then loop the changed flow back
  through `verify` before re-presenting. Never blind-implement and re-card.
- On "merge", land it and **let worktrunk own teardown — a leftover worktree is a bug**:
  - **Tiny & watched →** `wt merge` (runs the repo's `wt.toml` pre-merge gate, squashes,
    ff's main, removes the worktree — worktrunk merges *from* the worktree safely), then
    `ExitWorktree({action:"keep"})` in Claude Code, or point subsequent Codex tool calls at
    the main checkout (wt already deleted the dir).
  - **Substantial (PR path) → the merge must run from the MAIN CHECKOUT, never from inside the
    worktree.** `gh pr merge` checks out the base branch locally after merging; run from inside
    the worktree it dies with `fatal: 'main' is already used by worktree …` — the PR merges on
    GitHub but the local step fails, so teardown never runs and Pete is stranded in an orphan
    worktree (this has bitten real runs). So **tear down FIRST, then merge — after a merge
    pre-flight**, because tearing down a worktree whose PR then conflicts strands the ship
    with no worktree and no merge (that recovery is all manual):
    0. Pre-flight *from the worktree*: `git fetch origin` — if main moved, absorb + re-gate
       (the REVIEW sync step) and push; then confirm `gh pr view <#> --json mergeable` says
       `MERGEABLE`. Never tear down a worktree whose PR can't merge.
    1. Return to the main checkout: Claude Code `ExitWorktree({action:"keep"})`; Codex sets
       subsequent tool calls to the main checkout path.
    2. `wt remove feature/<slug> -f` — remove the local worktree now (frees the branch so
       `--delete-branch` can delete it; you're about to merge it anyway).
    3. `gh pr merge <#> --squash --delete-branch` — now from the main checkout: merges + deletes
       the *remote* branch, no checkout conflict.
    4. `git pull --ff-only` so local main matches (+ `git branch -D feature/<slug>` if the squash
       left an "unmerged" local branch behind). Nothing left on disk. **If the main checkout is
       dirty with another session's uncommitted work** (`git status --porcelain`), skip the local
       ff — leave their work untouched — and run any deploy step from a throwaway worktree pinned
       to `origin/main`, never from the dirty checkout (deploying it would ship their unfinished
       work and miss your merge).
  - **Session living in a pre-existing worktree ship didn't create** (e.g. Zero's sibling-worktree
    convention): don't tear down what isn't yours — the session and its dev server live there.
    Instead: `gh pr merge <#> --squash -R <owner/repo>` *without* `--delete-branch`,
    `git push origin --delete <branch>` to drop the remote branch, ff the main checkout, and
    leave the worktree + local branch in place (Pete's, not ship's). The zero-worktrees
    assertion below scopes to worktrees ship itself created.
  - Then `rm .ship-stage`, **stop the review dev server you booted** (its worktree is being
    removed), and **deprovision the per-branch preview backend if Stage 0 spun one up** — close
    the resource you opened, or skip if the repo's previews auto-expire (don't leave orphaned
    backends piling up). **Verify with `git worktree list` — zero ship worktrees must remain. A
    leftover worktree means the teardown failed (usually the merge ran inside the worktree) —
    recover it before you declare done.**
- **Ship deploys to the integration lane, never to production.** After the merge, push merged
  main to the repo's shared *dev/integration* lane if it has one — run its dev-deploy step **from
  the main checkout** (homezero: `scripts/deploy-dev.sh`, the single serialized writer for the
  shared dev plane; never run it from a worktree — that's the clobbering bug again), then hand
  back that lane's URL (homezero: `dev.homezero.md`). If the repo just auto-deploys on merge via
  CI, say so and hand back the URL once it's up; if it has no deploy step, confirm merged. Never
  make Pete run a deploy himself. Three deploy-watch rules, each from a real incident:
  - **Watch the deploy to conclusion — a red deploy is unfinished work**, on every lane
    including EXPRESS and batch runs (a batch once merged 18 green PRs over a dev lane that
    had been red for an hour). Red → diagnose, fix-forward on a new express branch,
    re-verify. Batch fleets: one watcher for the final merge wave is enough.
  - **Watch the run for YOUR commit** — `gh run list --commit <sha>` — not "the latest run":
    a following merge's push can cancel yours via workflow concurrency, and the superseding
    run's green reads as yours while dev is actually mid-deploy. Cheap artifact check before
    handing back the URL: fetch the lane's HTML shell and confirm a marker the diff introduced.
  - **A red *shared*-lane deploy you didn't cause is a shared resource** — before authoring a
    fix, check for an existing fix PR (`gh pr list --search`) and open a **draft PR first as
    the claim**; two sessions once raced identical fixes and one ship was thrown away.
- **Promotion to production is NOT ship's job — shipping ends at the integration lane.** On the
  three-lane model this assumes (a separate prod promote), "merged" means live on *dev*, not live
  for users — so never deploy or promote to prod / `www`, never add a promote gate or offer to
  promote (homezero: `scripts/promote-to-prod.sh` is a separate, human-gated ritual Pete runs on
  his own cadence — deliberately outside the pipeline). (Only where merge auto-deploys straight to
  prod is a merge itself the user-facing release — the review-card "Merge?" line covers that case.)
  Hand back the dev URL and stop there.
- Run the RETRO below, then **end with a `result:` line**: what shipped, one sentence — and if
  RETRO filed a note, name it (`… · ship-retro #N filed`). If the run left backlog candidates on
  the review card, name the count too (`… · 2 backlog candidates`) so Pete knows to approve them.

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
- **Also worth building — didn't make this round** — the run's *backlog candidates*: build-worthy
  things you deliberately left out of this round (see the collection rule below). Each one: what
  it is, one line on *why* it was deferred, and a proposed board destination (Backlog default;
  Icebox for the clearly-speculative). **Most rounds have none** — omit the card entirely when
  the list is empty; never pad it. This is **non-blocking**: the card lists them and the
  `result:` line names the count — nothing stops for them.
- **Merge?** — the PR link is there for the curious, but he shouldn't need it. Merge lands the
  feature on the **integration lane** (dev where the repo has one, else just main) — not on
  users, so it's a reversible, low-stakes yes once he's seen it run. (Only where merge
  auto-deploys straight to prod is it the point of no return — treat it that way there.)

### The board is the run's record (board-backed repos)

Where the repo has a backlog-board skill (homezero → the `linear` skill, which holds all the
mutations and recipes), the ticket mirrors the run — Pete follows a ship from his phone by
opening the card. **The board is a mirror, never a gate**: an API hiccup gets one line of
narration and the pipeline rolls on; no stage ever waits on Linear.

- **Run start** — move the matching card to In Progress. A GATED ship with no card gets one
  created (title = the feature, description = Pete's ask in his words). EXPRESS runs skip the
  board entirely unless a card already exists for the work.
- **GATE 1, design approved** — publish the spec HTML to the repo's public specs host
  (homezero: `specs.homezero.md` — the linear skill's R2 recipe, ~2s, **never the dev
  deploy**), then comment on the issue: 3-line design summary + the spec link. **Ticket links
  are always public URLs** — never localhost, never a file path.
- **PLAN** — mirror the plan's punch list into the issue description as markdown checkboxes;
  check items off as build tasks land. The ticket is the punch list; the HTML is the depth.
- **Merge** — move the card to **For Review** and make **the ticket itself the review ask** —
  Pete does his final pass from the ticket on his phone, no HTML required. Append a
  `## For your review` section to the description: the dev-lane URL to test at, then
  **checkboxes for exactly what needs his eye** (the "only you can confirm" items + any
  verifier flags — the same content the review card carries), and a 1–2 line *what shipped*.
  Close with a comment carrying the `result:` line + verify verdict. Publish + link the
  review-card HTML **only when there's more than the ticket can hold** (a screenshot
  storyboard, before/afters) — depth behind a link, never the primary surface. Never move to
  Done — **Done is Pete's drag**: he tests on dev, ticks the boxes, and moves the card
  himself; ship's pipeline ends at For Review on the board just as it ends at the dev lane
  in the repo. (GATED ships still present the review card at the merge gate as always — this
  is about what lands on the ticket after the merge.)
- **Bigger than this round** — when the design reveals real phases beyond this ship, create a
  board **project**: this round's issue goes in it, the later phases are filed as issues in the
  same project, and the spec link lives on the project description. Next round picks up inside
  the project instead of re-discovering the shape.

### Backlog candidates — collect deferrals, surface them, file on approval

A ship run keeps throwing off *build-worthy ideas that aren't this round's job* — a surface you
scoped out in DISCOVER ("not this round"), an over-build the `ponytail` review said to cut but
that's a real feature later, an adjacent thing the verifier or the build turned up. Today they
evaporate. Don't let them.

- **Collect as you go — no scratch file, you're one continuous run.** As the driver you see every
  deferral source (DISCOVER scope cuts, the ponytail/verifier reports, ideas noticed mid-build).
  Keep a running list of the ones you'd *actually build*, each with a one-line *why-deferred*.
  Same bar as RETRO: **most runs defer nothing worth keeping** — a genuine candidate, not every
  passing thought. **A candidate is a thing OUTSIDE this spec's scope** — an adjacent feature, a
  nice-to-have the work exposed. It is *never* a specced surface you chose not to build: the scope
  law holds (build the whole spec, never slice it into "Ship 1 of N"), and this section is not a
  loophole around it. New ideas the run surfaced, yes; specced work deferred, never.
- **Surface in the review card** — the "Also worth building" card (above), one `.cand` per item
  with a proposed destination: **Backlog** by default ("things we intend to build"), **Icebox**
  only for the clearly-speculative. Empty list → omit the card.
- **File on approval — non-blocking.** The `result:` line names the count ("· 2 backlog
  candidates"). When Pete says *file them* (or names which), file each through the repo's backlog
  board and reply with the links — only where the repo *has* one: a configured backlog skill
  (homezero → the `linear` skill, HOM board; `stateId` Backlog default, Icebox for speculative;
  description = the idea + "deferred from ship run on `<feature>`"). Candidates that are
  **phases of one larger design** go into that design's board *project* (see the board-record
  section) instead of loose backlog cards. **No board for this repo → the card and the
  `result:` line are the record; don't invent a tracker.** Never gate the merge or the
  `result:` line on this — approval is always async.

## Running under Codex Desktop

Same pipeline, same gates, same artifacts — these mechanical swaps apply **only when
the driver is a Codex Desktop session** (they override the Claude Code specifics above):

- **Worktrees: Codex owns birth and cleanup — never run `wt` against a Codex-managed
  worktree** (no `wt switch --create`, no `wt merge`, no `wt remove`, no nesting a wt
  worktree inside one). Preferred start: the thread already in **Worktree mode** off
  `main` — Codex creates the worktree (usually detached HEAD) under
  `$CODEX_HOME/worktrees`. Sanity-check where you are (`git rev-parse --show-toplevel`,
  `git branch --show-current`); if detached, make the branch real before the first
  commit: `git switch -c feature/<slug>`. If the thread is **Local on `main`**, do NOT
  edit — stop with `needs input: click Fork into new worktree for this ship`. (**Fork
  into local** is only for when Pete explicitly wants the work in his foreground
  checkout.)
- **Artifacts open in Codex's in-app Browser**, not via macOS `open`: serve the
  artifact's directory on localhost and navigate the in-app Browser there (raw
  `file://` URLs are unreliable in Codex); a running app's localhost URL opens
  directly. Fall back to `open`/Chrome only if the in-app Browser is unavailable or
  Pete asks.
- **Merge is the PR path only**: push the branch, open the PR, merge via Codex's Git
  UI or `gh pr merge <#> --squash --delete-branch` — never from inside the branch's
  own worktree. Then `rm .ship-stage`, stop the review dev server, deprovision the
  preview backend — but **leave worktree cleanup to Codex** (archive the thread).
- **No status line, no FleetView** — narration carries the load alone. Every status /
  `needs input:` / `result:` line ends with the `branch <branch> · worktree <path>`
  breadcrumb (see the narration contract), and `hooks/gate-notify.sh` isn't auto-wired
  — run it manually at gates if it's present.

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
- **End `needs input:` and `result:` lines with `branch <branch> · worktree <path>`**
  (`detached@<short-sha>` until a branch exists). Pete must always know which checkout
  he's looking at — this is what catches the cross-repo case where no status line is
  watching, and under Codex Desktop it's the only location signal there is.

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
- **Go** — one line: BUILD starts the moment Pete says go.

It is the *only* thing Pete reads before a build starts. Never make him read the plan.

## What this skill deliberately does NOT do

No arbitrary phasing — ship plans and builds the whole spec in one pass, never slicing a
specced feature into "Ship 1 of N" and stopping (phasing is Pete's to request, not ship's
to impose). No `executing-plans` (checkpoint-heavy — the opposite of hands-off). No strict
TDD by default (tests are a build deliverable; the pre-merge test gate is the backstop;
reserve test-first — `superpowers:test-driven-development` — for money/auth paths). No manual git worktree management — `wt` owns the
worktree birth-to-death in Claude Code, Codex Desktop owns its own managed worktrees
(never `wt` inside one). No promoting to production — ship ends at the integration lane (dev);
promotion to prod / `www` is a separate, human-gated ritual Pete runs, never ship's to deploy,
gate, or offer.
