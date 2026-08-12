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
- **`/ship design <idea>`** — pins GATED and mandates the full design walkthrough in
  DISCOVER. The verb is Pete asserting taste is in play; never downgrade it, however
  mechanical the work looks.
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

The rails are constant: worktree off main → change → prove it → merge via PR → dev
lane — **nothing ever edits main directly, however tiny, and Pete does nothing unless a
gate genuinely needs him.** What scales is the ceremony, and **you size it, not Pete**:

- **EXPRESS — a quick tweak or fix.** Whole diff visible before you start, no money
  path. No spec, no plan, no cards, no stops: worktree → change → repo gates
  (tsc/tests) → self-drive the affected flow → fast PR, merged on green → dev lane →
  `result:` line. A dab of `ponytail` (smallest diff), and `impeccable` for anything
  visual. Pete finds out from the `result:` line, not before.
- **SELF-DIRECTED — real work with no taste question in it.** Write whatever
  machine-facing spec/plan *you* need to build it well, then build, run the full REVIEW
  machinery (codex review + `verify` — a `works` verdict is the merge bar), merge,
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

**Everything is orchestrated from inside Claude Code** (Pete, 2026-08-10). The driver
dispatches only to **harness subagents** — it never runs `codex exec` itself, never
shells out to `claude -p`, and never watches a background process. Some subagents do the
work themselves; others are **codex supervisors**: an Opus subagent that owns one codex
session end to end (brief → launch → patience → fix rounds → verdict) per the
`codex-supervisor` skill. Codex tokens still buy the drafts; the supervisor absorbs the
polling, the stall checks, and the retries that used to crowd the driver's context.
Never Sonnet.

**Two dispatch shapes:**

- **Codex supervisor (Opus → codex)** — the default for closed-brief drafting,
  correctness review, recon sweeps, and browser walks. Anything with real work to
  explore and no open design question.
- **Plain Claude subagent** — when repo context or taste is load-bearing enough that
  handing it to codex would cost more in fix rounds than it saves.

**What delegates, what stays inline** — in order, per build task:

1. **Design still open, real risk, ambiguous?** → the driver closes the judgment first,
   then dispatches the fully-specified remainder. Judgment inseparable from the
   writing → the driver does it inline.
2. **Fully specified and self-contained, with real work to explore?** → **codex
   supervisor**. The default destination for drafting.
3. **Smaller than the dispatch overhead** (brief + supervise + read the verdict)? →
   inline. A rename, a config line, a verbatim write already authored in the brief,
   wiring a triaged review fix. Real multi-file exploration still dispatches.
4. **A supervisor returns `escalate`?** → the driver writes it inline, now, and logs
   why. Don't re-dispatch the same task a third time. **Slow is not failure** — never
   escalate because a run is taking a while; that judgment belongs to the supervisor.
5. **Skill/agent prose and frontend design — never delegated.** SKILL.md files,
   agent-voiced docs, HTML design specs, mockups, styling — anywhere taste is the
   deliverable, the driver authors inline. Frontend *mechanics* with the design closed
   dispatch like any other closed brief.

**The driver owns the envelope**, whoever drafts: it writes the brief the supervisor
carries (exact files, signatures, test cases, constraints — a vague brief burns the
savings in fix rounds), reviews the returned diff and runs the gates before anything is
committed (never trust a "tests pass" claim, from a supervisor or from codex), and owns
git entirely. **One writer per branch at a time** — concurrent writers on one tree
collide; serialize, or give each its own sub-worktree.

**All browser work goes through a supervisor too** — verify walks, design QA,
live-product grounding: codex scripts its own Playwright against the running app and
saves screenshots to disk. Auth-walled surfaces use the logged-in codex Chrome
(`~/.codex/codex-chrome`, CDP :9222). The one exception that never reaches codex: a
login that exists solely in Pete's *personal* Chrome — that's a driver-side
claude-in-chrome walk.

**Never idle while a supervisor runs** — a review or QA pass is 10–25 minutes.
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
   per stage.
2. **Two gates, at most.** GATE 1 = design direction (after DISCOVER) — always a hard
   stop on the GATED lane. GATE 2 = go (after PLAN, via the go-card) — a hard stop
   **only when the card carries a genuine call for Pete**: a PM tradeoff, a money path,
   or something you judge he'd genuinely want to see before build. **A zero-call
   go-card auto-passes** (Pete, 2026-07-28): render it, `open` it, narrate
   "gate 2 auto-passed — nothing needed you," and keep going. Schema or auth alone
   don't force the stop — stop only when you deem it genuinely necessary. Money paths
   always stop. When a gate does fire, it is a **HARD STOP** — present the artifact and
   wait.

**Who Pete is & the stack:** his global instructions carry both (technical-PM tone dial;
the standing stack — flue · Cloudflare · Convex · Clerk · Stripe · Next). Never re-ask
the stack. **The repo's own `CLAUDE.md` / `AGENTS.md` overrides it** where it diverges.
Escalate a library choice only when it's both architectural *and* outside the canon.

## The ship contract — what a repo tells ship

A repo declares how ship runs it in its `CLAUDE.md` / `AGENTS.md`: the **gate commands**
(tests, typecheck, production build), the **deploy lanes** and their scripts, **per-branch
preview provisioning** where a shared backend exists, a **test-auth path** verify may
use, and — for repos that shouldn't ship at all (wikis, civic work) — **`ship: no`**,
which means decline and say why. homezero's AGENTS.md is the model. A repo with no
contract gets best-effort: whatever gates you can find, merge to main, no deploy claim.

## The pipeline — create a todo for each stage

Each stage writes its marker to `.ship-stage` at the git root (the status line + the
FleetView row read it). Written for Claude Code; a **Codex Desktop** driver applies the
swaps in "Running under Codex Desktop" below.

### 0 · Worktree (invisible)  → marker: `discover`

**Prereqs:** a git repo with `main` and ≥1 commit (zero-commit repo: `git add -A &&
git commit -m "init"` first). The PR path needs a GitHub remote; a repo with no remote
falls back to `wt merge` at merge time.

```
wt switch --create feature/<slug> --no-cd --format=json -y
```
then enter the path from the JSON — Claude Code: `EnterWorktree({path})`; Codex:
absolute paths. `--no-cd` is load-bearing. A `.config/wt.toml` auto-provisions
gitignored runtime files. Write `printf 'discover' > <root>/.ship-stage`. Never build
on main.

- **Provision the per-branch backend now** if the repo's ship contract has one — a
  worktree building against a shared backend clobbers it (incidents: Backends). No
  preview lane → build against the repo's dev stack.
- **Cross-repo case:** `EnterWorktree` only takes for the session's primary repo
  (incidents: Worktrees). Against any other repo, work the worktree by **absolute
  path** and **narrate the fork the moment you create it** (`forked feature/<slug> off
  main @ <path>`) — a blind status line must never make it look like nothing forked.
- **Opportunistic tidy:** glance at `git worktree list` and `wt remove <branch> -f`
  any worktree that provably landed (merged PR whose `headRefOid` matches its HEAD,
  clean tree — incidents: Worktrees). Never touch one with uncommitted work.

### 1 · DISCOVER — Pete's taste, up front  → marker: `discover`, then `gate:1`

- Invoke `superpowers:brainstorming`. PM-framed, one question at a time.
- **Recon runs on a supervisor, synthesis stays with the driver.** Codebase
  evidence-gathering dispatches as a read-only codex run (report findings, edit
  nothing).
  The recon brief includes a **reuse audit**: for every core noun the feature
  introduces, grep the whole repo — data layer included — for existing infra before the
  plan treats it as new (incidents: Design).
- **Bug-shaped requests get an empirical root-cause check** — reproduce the failure or
  read the runtime evidence; never spec a fix from a hypothesis (incidents: Design).
- For any visual/UI feature, invoke `impeccable` and follow its Setup (context.mjs —
  the repo's PRODUCT.md/DESIGN.md are the visual authority): a new surface or
  replacement look routes through its `shape`/new-work path; a refinement stays on the
  incumbent world. Use `/pix` for imagery freely — the spec *is* the prototype.
  **Ground the design in the live product**: a supervisor walks the running app /
  deployed URL and reports the real theme/CSS with screenshots; design from those,
  never from in-repo mockups (incidents: Design).
- Produce ONE self-contained HTML spec in the repo's docs home (`specs/` or `docs/`,
  whichever it uses) — e.g. `specs/designs/YYYY-MM-DD-<slug>.html` — covering the
  **whole** feature; it's the scope contract PLAN and BUILD execute in full.
  **The driver authors all design artifacts inline** — taste is the deliverable, never
  dispatched.
- **Spec shape:** `14-research-feature-explainer` body (TL;DR first, collapsible
  depth); a genuine direction choice presents as `02-exploration-visual-designs` — 2–3
  live-rendered directions side-by-side so Pete picks by looking; mockups are live
  (`07`/`08-prototype`); flows are diagrams (`13-flowchart-diagram`).
- Write `gate:1`, fire the gate notification, `open` the spec, end the turn with a
  `needs input:` line ("design direction?"). **HARD STOP — GATE 1.**

### 2 · PLAN — automatic  → marker: `plan`, then `gate:2` (or straight through)

- Write `plan`. Invoke `superpowers:writing-plans` for ONE execution plan covering the
  **entire spec** — never sliced into phases. Run `ponytail` as the *waste* critic, not
  a scope critic — it cuts reinvention and gold-plating, never specced scope. Save the
  markdown plan to the docs home (e.g. `specs/plans/YYYY-MM-DD-<slug>.md`).
- Render the HTML **go-card** from `reference/go-card.html` (contract below) and
  `open` it.
- **Gate or go:** if the card carries a genuine call (PM tradeoff, money path, your
  judgment says he'd want to see it) — write `gate:2`, fire the gate notification, end
  the turn with `needs input:` ("go?"). **HARD STOP.** Otherwise **auto-pass**: narrate
  "gate 2 auto-passed — nothing needed you" and continue to BUILD.

### 3 · BUILD — automatic  → marker: `build:N:M` (N done of M tasks)

- Write `build:0:<M>`; bump N per task. Build **all M tasks** in one session; commit
  each task on the branch as it lands, merge only when the whole plan is built.
- Invoke `superpowers:subagent-driven-development` (the driver drives) and dispatch
  each task per **Engines** above — closed briefs to codex supervisors, sub-overhead
  work inline. The driver owns the brief, the diff review, the gates, and git. One
  writer per branch at a time.
- **Single-writer vs fan-out — pick by the diff, not reflex.** Default one writer.
  Fan out writers (own worktrees, merged back) only for genuinely independent AND
  numerous tasks — a migration, a mechanical sweep. The high-value fan-out is the
  **review**, regardless of build size: don't parallelize 5 small edits; do
  parallelize 5 verifiers.
- `ponytail` posture; `superpowers:verification-before-completion` before claiming any
  task done — actually run it; `superpowers:systematic-debugging` on a red test.
- **UI-writing briefs carry the craft floor** — codex has no impeccable installed and
  a subagent loads its own skills, not the driver's, so the floor never reaches the
  writer unless the brief points it there: every dispatch that writes UI carries
  `~/.claude/skills/impeccable/reference/craft-floor.md` down to the writer, with its
  checks and bans.
- **Before BUILD is done, smoke-walk the whole feature yourself** — boot the app and
  drive the spec's real user paths (the formal `verify` runs in REVIEW; don't invoke it
  twice). Two preconditions that have each cost a red deploy (incidents: Backends): a
  framework with its own production build → **run that build too**; the branch touched
  `convex/` → **re-push the preview** (`npx convex deploy --preview-name <branch> -y`).
  *You* find the breakage, never Pete.
- Raise a hand only for a genuine fork (PM-framed, with a rec).

### 4 · REVIEW / MERGE — automatic  → marker: `review`, then remove the file

- Write `review`. **Sync with main first**: `git fetch origin`; absorb upstream in the
  worktree (rebase, or merge if unsafe), re-run the gates, then dispatch review — and
  re-sync right before the merge if main moved again (incidents: Worktrees).
- **Freeze the tree while a verifier is driving** — no merges, rebases, or edits until
  its verdict lands (incidents: Worktrees). Absorb upstream *before* dispatching a
  round, never during.
- **Correctness review — a supervisor on codex review mode, launched first** so it
  works while the rest of REVIEW proceeds (`codex exec review --base <lane-target>`;
  the supervisor owns the mechanics). Meanwhile the driver runs `ponytail-review` (the
  over-build sweep). The **driver triages every finding** — adversarial reviewers
  over-flag by design — fixes what's real, puts judgment calls on the card. Codex
  unavailable → `/code-review` + `ponytail-review` on the driver. The high-value
  fan-out is here: several verifiers on one diff beats one.
- **Design QA for visual features** — a background supervisor first runs
  impeccable's deterministic detector over the branch's changed UI files
  (`node ~/.claude/skills/impeccable/scripts/detect.mjs --json <files>` — local, no
  network), then walks the built surfaces and judges them against the GATE 1 spec and
  the craft-floor checklist (contrast, depth, spacing, type, motion, states, copy, and
  the bans). Bounded per impeccable's own ceiling: one batched round, one confirm, no
  open-ended polish loops. Driver triages: real gaps fixed before the card, nits land
  on the card for Pete.
- **Put it in front of Pete, running.** For any visual/interactive feature, boot the
  worktree's dev server in the background and `open http://localhost:<port>` so the
  live local app is on his screen. **Never deploy to let him review; never tell him to
  "go look at the live site"** — the worktree's localhost is the review surface.
  (Non-UI change → show the demo/test output instead.)
- **Prove it works — invoke `verify` before the card.** A fresh read-only supervisor
  drives the feature and returns `works | broken | unverifiable` + a
  screenshot storyboard; verify loops-to-fix (cap ~3). **`broken` after the cap, or
  `unverifiable` → do NOT merge**: end the turn with `needs input:` ("review: <feature>
  — couldn't prove it works: <reason>") and hand Pete the verdict + evidence.
- **Render the review card** from `reference/review-card.html` (contract below) to the
  docs home and `open` it, pointed at the running localhost. **Never tell Pete to "go
  read the PR"** — the review comes to him, running and labeled.
- **The merge gate always holds for GATED ships**: present the running app + card, end
  with `needs input:` ("review: <feature> — merge?"), and wait. **Never merge a gated
  UI Pete hasn't seen run** — a standing "go" authorizes the build, not the merge of an
  unseen feature. EXPRESS / SELF-DIRECTED merge autonomously on green gates + `works`.
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
  the run for YOUR commit**, not "latest," and artifact-check the lane; **a red shared
  lane you didn't cause is a shared resource** — check for an existing fix PR, claim
  with a draft PR first.
- **Promotion to production is NOT ship's job.** "Merged" means live on *dev*. Never
  promote to prod / `www`, never offer to (the repo's promote script is Pete's own
  human-gated ritual). Only where merge auto-deploys straight to prod is the merge
  itself the release — treat the review card's "Merge?" accordingly.
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

## The go-card contract (GATE 2 artifact)

Render `reference/go-card.html` filled with the meta only — one screen (a
`16-implementation-plan` boiled down to its decision surface):

- **What gets built** — one line of scope.
- **Ponytail's cut-list** — what was dropped, and why.
- **Pete's 1–3 calls** — each a PM tradeoff *with your recommendation*. Zero calls →
  the gate auto-passes (see Two principles); the card is still rendered for the record.
- **Risk** — one line.
- **Mockup thumbnail** — if visual, from the design spec.
- **Go** — one line.

It is the *only* thing Pete reads before a build starts. Never make him read the plan.

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
- **Merge?** — the PR link is there for the curious, but he shouldn't need it. Merge
  lands on the integration lane — reversible, low-stakes. (Only where merge
  auto-deploys to prod is it the point of no return — say so there.)

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

1. **Status line** — the `gate:N` marker shows `✋ <slug> — design?/go?` in bold amber.
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
