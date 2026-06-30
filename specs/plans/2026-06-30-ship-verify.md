# ship `verify` Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an independent verifier to ship's REVIEW stage that drives the just-built feature on the running app via Playwright, proves it works with captioned screenshots, loops-to-fix, and lays the proof into the review card before the merge gate.

**Architecture:** A new self-contained `verify` skill (REVIEW invokes it, like it already invokes `/code-review`). The skill spawns a fresh read-only verifier sub-agent that drives the running app through the feature's acceptance criteria, screenshots the beats, and returns `works|broken` + taste notes. The driver fixes broken runs and re-spawns a fresh verifier (cap ~3, then escalates to Pete). For genuine core journeys it crystallizes the exploration into a committed Playwright `.spec.ts`. The review-card template gains a proof storyboard + a "verifier flagged" block.

**Tech Stack:** Claude Code skill (markdown) · Playwright (live drive + committed `.spec.ts`) · the existing ship HTML card templates.

## Global Constraints

- All three deliverables live **inside the ship plugin** (`peteknowsai/ship`); no homezero changes in this plan.
- **Generic seam — verify never implements auth/stack-up.** It assumes the *caller* (ship REVIEW) has already booted the running app and that the *repo* provides a way to reach authed surfaces. verify does **not** mint sessions, bypass auth, or boot infra. This single boundary is non-negotiable — it's what keeps the skill repo-agnostic.
- The driver (ship/Opus) **never declares the feature works itself** — only a *fresh* verifier sub-agent that didn't write the code can return `works`.
- Fix loop is capped at **~3 rounds**; still broken → **escalate to Pete** with the verdict, never silent-merge.
- Crystallized specs are **core journeys only** — not a spec per feature. Keep the standing suite thin.
- This is a **skill/markdown + HTML** feature: there is no `pytest`. Each task ends with a concrete **acceptance check** (grep for the required contract, or a browser smoke-render), not a unit test. That is the honest analogue of the test cycle here.
- Match existing file conventions: skill frontmatter shape mirrors `plugins/ship/skills/router/SKILL.md`; card markup/classes mirror the existing `review-card.html`.

---

## File Structure

- **Create** `plugins/ship/skills/verify/SKILL.md` — the verifier skill (the whole new capability).
- **Modify** `plugins/ship/skills/ship/SKILL.md` — Stage 4 REVIEW invokes `verify`; the "review card" contract section documents the new blocks.
- **Modify** `plugins/ship/skills/ship/reference/review-card.html` — proof storyboard replaces the single thumb; add a "verifier flagged / suggested" block.

Order matters: Task 1 creates the skill (defines the contract REVIEW depends on), Task 2 wires REVIEW to it + updates the card contract, Task 3 makes the card template carry the proof. Each is independently reviewable.

---

### Task 1: Author the `verify` skill

**Files:**
- Create: `plugins/ship/skills/verify/SKILL.md`

**Interfaces:**
- Produces (the contract REVIEW consumes in Task 2): the skill, when invoked, returns to its caller — `verdict` (`works`|`broken`|`unverifiable`), `evidence` (ordered list of `{path, caption}` screenshot beats), `taste_notes` (short list of "looked off / couldn't confirm" items), and `spec_committed` (path of a crystallized `.spec.ts`, or none).

- [ ] **Step 1: Write the skill frontmatter + role**

Create `plugins/ship/skills/verify/SKILL.md` starting with:

```markdown
---
name: verify
description: >
  Prove the feature just built actually works — a fresh read-only verifier sub-agent
  drives the running app and judges it — before anything merges. Use in ship's REVIEW
  stage (it's invoked there automatically) or standalone when a change is ready and you
  want proof it works: "verify this", "prove it works", "/verify". Never declares a
  feature working off the diff alone — it drives the real app.
user_invocable: true
---

# /verify — prove the feature works, then hand proof to REVIEW

You are the **orchestrator + fixer**. Verification splits by who's best at it:

- **The subjective question — "does the feature do what was intended?"** → a fresh
  **read-only verifier sub-agent** drives the running app and judges it. It didn't write
  the code (independence) and app-driving is verbose (context-isolation) — both pay off.
- **Objective codified checks** (tsc / lint / unit / existing e2e) → **you** run them as a
  regression sweep; pass/fail can't be rubber-stamped and you need the error to fix it.

**You never declare the feature works yourself — only a fresh verifier can.**
```

- [ ] **Step 2: Write the "preconditions + stack" section (the generic seam)**

Append:

```markdown
## 1. Preconditions (the caller owns these)
The running app is **already up** — REVIEW booted the worktree's dev server; standalone,
boot it first. The verifier **reuses** that stack, never boots its own. If the feature is
behind auth, the **repo** must provide a local/test way to reach authed surfaces — verify
does NOT mint sessions or bypass auth itself. If authed surfaces are unreachable and the
repo offers no test-auth path, return `unverifiable` with that reason (don't fake it).
```

- [ ] **Step 3: Write the verifier sub-agent prompt (live drive via Playwright)**

Append:

````markdown
## 2. Verify the feature (delegate) → fix → re-verify (loop ≤ 3)
Brief from the plan/spec file if one exists (point the verifier at it), else inline the
acceptance criteria. Spawn a fresh **read-only** verifier:

```
You are a read-only verifier. Do NOT edit code. Independently confirm THIS feature works by
driving the running app with Playwright (the stack is already up at <URL>). Most new features
have no automated spec — verify it agentically.

FEATURE (what a user should now be able to do + the observable success state):
  <intent / acceptance criteria>            (or: see plan/spec file <path>)
HOW TO EXERCISE IT:
  <route + steps / API call / CLI>
AUTH (if behind login):
  reach authed surfaces via the repo's local/test-auth path; if none exists, say so and stop.

Drive the REAL flow with Playwright — walk the exact steps a user would, like clicking
through it. Screenshot the MEANINGFUL BEATS (start → action → success), not a random dump.
Judge observed vs expected. Return ONLY:

VERDICT: works | broken | unverifiable
EVIDENCE: ordered list of "<screenshot path> — <plain-language caption>"  (the storyboard)
EXPECTED: <criteria>
OBSERVED: <what actually happened>
TASTE: <0-3 short "looked off / couldn't confirm" notes, or "none">
```

- **broken** → fix the implementation, then spawn a **fresh** verifier (never reuse the one
  that saw the bug). Cap at ~3 rounds.
- **still broken after the cap** → stop and hand the verdict + evidence up to the caller for
  Pete. Never loop forever, never merge unproven.
````

- [ ] **Step 4: Write the regression sweep + crystallize sections**

Append:

````markdown
## 3. Regression sweep — you run the codified checks; fix red directly
Run the repo's `tsc` / lint / unit / existing e2e. Triage failures (real-bug vs stale-test);
**never weaken an assertion to go green.** If a fix changes feature behavior, re-verify (§2).

## 4. Crystallize — core journeys only
If the feature is a genuine **core journey** (auth, money, a primary product flow — NOT every
small feature), write the Playwright drive you just ran out as a committed `.spec.ts` in the
repo's e2e location, folded into the feature's own diff. Stable selectors (role/label/text;
add a small `data-testid` only when there's no good handle). Most features: skip this — drive,
prove, report, done. Running the committed spec in the gate is the **repo's** job (the seam).

## 5. Hand back proof
Return to the caller: VERDICT, EVIDENCE (the ordered screenshot+caption storyboard), TASTE
notes, and the crystallized spec path (or none). REVIEW lays these into the review card.
````

- [ ] **Step 5: Acceptance check — the contract is all present**

Run:
```bash
cd plugins/ship/skills/verify
grep -q 'name: verify' SKILL.md \
 && grep -q 'read-only verifier' SKILL.md \
 && grep -q 'VERDICT: works | broken | unverifiable' SKILL.md \
 && grep -q 'Cap at ~3 rounds\|loop ≤ 3' SKILL.md \
 && grep -q 'does NOT mint sessions' SKILL.md \
 && grep -q 'core journey' SKILL.md \
 && echo "VERIFY-SKILL CONTRACT OK" || echo "MISSING CONTRACT"
```
Expected: `VERIFY-SKILL CONTRACT OK`

- [ ] **Step 6: Commit**

```bash
git add plugins/ship/skills/verify/SKILL.md
git commit -m "ship: add verify skill — fresh agent proves the feature on the running app"
```

---

### Task 2: Wire `verify` into REVIEW + update the card contract

**Files:**
- Modify: `plugins/ship/skills/ship/SKILL.md` (Stage 4 REVIEW, ~lines 175-201; card contract, ~lines 203-216)

**Interfaces:**
- Consumes (from Task 1): the verify skill's returned `verdict` / `evidence` / `taste_notes` / `spec_committed`.
- Produces (Task 3 consumes): the card now carries a storyboard (evidence) + a flagged block (taste_notes).

- [ ] **Step 1: Insert the verify invocation into REVIEW, before the card**

In `plugins/ship/skills/ship/SKILL.md`, in Stage 4 (`### 4 · REVIEW / MERGE`), immediately after the `/code-review` + `ponytail-review` bullet and before the "Render a review card" bullet, add:

```markdown
- **Prove it actually works — invoke `verify` before the card.** After the static reviews,
  invoke the `verify` skill against the running worktree app (you already booted it). A fresh
  read-only sub-agent drives the feature, screenshots the beats, and returns
  `works | broken | unverifiable` + taste notes; verify loops-to-fix (cap ~3). **`broken` after
  the cap, or `unverifiable`, → do NOT proceed to merge: end the turn with a `needs input:` line
  ("review: <feature> — couldn't prove it works: <reason>") and hand Pete the verdict + evidence.**
  Only carry a `works` verdict (+ its storyboard) into the card.
```

- [ ] **Step 2: Update the "review card" contract to document the proof blocks**

In the `## The review card (REVIEW artifact)` section, replace the **What it looks like** bullet and add a flagged bullet so it reads:

```markdown
- **Proof it works** — the verifier's captioned screenshot **storyboard** (start → action →
  success) with the `works` verdict on top. This replaces a static mockup: it's evidence the
  running feature does what was intended, organized for a glance. (Non-visual change — show the
  demo/test output instead.)
- **Already checked for you** — gates/tests green, **the flow driven end-to-end by a fresh
  agent (it runs)**; what was NOT touched (schema / money / public surfaces).
- **Verifier flagged / suggested** — the verifier's taste notes ("looked off / couldn't
  confirm"), if any. These are *reports, not work* — Pete decides: fix now / backlog / ignore.
- **Only you can confirm** — the 1–2 things that need his eye; walk them on the open localhost.
```

- [ ] **Step 3: Acceptance check — REVIEW invokes verify before the card, escalation documented**

Run:
```bash
cd plugins/ship/skills/ship
awk '/^### 4 · REVIEW/,/^### 5 · RETRO/' SKILL.md | grep -q 'invoke the `verify` skill\|invoke `verify`' \
 && awk '/^### 4 · REVIEW/,/^### 5 · RETRO/' SKILL.md | grep -q "couldn't prove it works" \
 && grep -q 'Proof it works' SKILL.md \
 && grep -q 'Verifier flagged' SKILL.md \
 && echo "REVIEW-WIRING OK" || echo "WIRING INCOMPLETE"
```
Expected: `REVIEW-WIRING OK`. Also eyeball: the verify bullet sits **after** static review and **before** the "Render a review card" bullet.

- [ ] **Step 4: Commit**

```bash
git add plugins/ship/skills/ship/SKILL.md
git commit -m "ship: REVIEW invokes verify before the card; card contract gains proof + flagged blocks"
```

---

### Task 3: Extend the review-card template with the proof storyboard

**Files:**
- Modify: `plugins/ship/skills/ship/reference/review-card.html`

**Interfaces:**
- Consumes: the verifier evidence (`{path, caption}` beats) + taste notes, rendered by REVIEW.

- [ ] **Step 1: Replace the single-thumb "What it looks like" card with a storyboard**

In `review-card.html`, replace the VISUAL card (the `<div class="card">` containing
`<h2>What it looks like</h2>` and the single `<img class="thumb">`) with a proof storyboard:
verdict pill + a repeatable captioned beat. Use the existing CSS vars/classes where they fit;
add minimal storyboard CSS in the `<style>` block. Mark it include-only like the current VISUAL
card. Concretely:

```html
  <!-- PROOF: the verifier's storyboard. Include for any user-facing feature; for a non-visual
       change, swap the beats for demo/test output. Repeat the .beat block per screenshot. -->
  <div class="card">
    <h2>Proof it works <span class="pill-ok">{{VERDICT}}</span></h2>
    <div class="storyboard">
      <figure class="beat">
        <img src="{{SHOT_1_SRC}}" alt="{{SHOT_1_CAP}}">
        <figcaption>{{SHOT_1_CAP}}</figcaption>
      </figure>
      <!-- repeat <figure class="beat"> per beat: start → action → success -->
    </div>
  </div>
```

Add to the `<style>` block:
```css
  .pill-ok{font:600 12px/1 ui-monospace,monospace;background:#1f7a3d;color:#eafff0;
           border-radius:6px;padding:3px 8px;vertical-align:2px;margin-left:6px}
  .storyboard{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}
  .beat{margin:0}
  .beat img{width:100%;aspect-ratio:16/10;object-fit:cover;border:1px solid var(--line,#2a3340);
            border-radius:8px;display:block}
  .beat figcaption{font:12px/1.4 ui-monospace,monospace;color:#9aa7b4;margin-top:6px}
```

- [ ] **Step 2: Add the "Verifier flagged / suggested" card**

Immediately after the "Already checked for you" card, add an include-only block:

```html
  <!-- FLAGGED: include only if the verifier returned taste notes, else delete this card -->
  <div class="card">
    <h2>Verifier flagged / suggested</h2>
    <ul>{{FLAGGED_ITEMS}}</ul>
    <p class="sub">Reports, not work — say fix now / backlog / ignore.</p>
  </div>
```

- [ ] **Step 3: Acceptance check — smoke-render the card**

Run:
```bash
cd plugins/ship/skills/ship/reference
grep -q 'storyboard' review-card.html \
 && grep -q '{{VERDICT}}' review-card.html \
 && grep -q 'Verifier flagged' review-card.html \
 && echo "CARD MARKUP OK" || echo "CARD MARKUP MISSING"
open review-card.html   # eyeball: storyboard row + flagged card render; existing blocks intact
```
Expected: `CARD MARKUP OK`, and the opened card shows the storyboard row + flagged card without breaking the existing layout. (Template placeholders showing literally is expected — REVIEW fills them at render time.)

- [ ] **Step 4: Commit**

```bash
git add plugins/ship/skills/ship/reference/review-card.html
git commit -m "ship: review card carries the verifier proof storyboard + flagged block"
```

---

## Self-Review

**Spec coverage** (against `specs/2026-06-30-ship-verify-design.html`):
- New `verify` skill → Task 1. ✓
- REVIEW invokes verify before the card → Task 2 Step 1. ✓
- Review-card proof storyboard + flagged blocks → Task 3 + Task 2 Step 2 (contract). ✓
- Fresh read-only verifier, works|broken, cap-3 → escalate → Task 1 Steps 1,3 + Task 2 Step 1. ✓
- Playwright live-drive + crystallize core journeys → Task 1 Steps 3,4. ✓
- Screenshots organized as captioned storyboard for PM review → Task 1 Step 3 + Task 3 Step 1. ✓
- Generic seam (repo provides runnable-past-auth app; verify implements no auth bypass) → Global Constraints + Task 1 Step 2. ✓
- Out-of-scope kept out (no homezero auth hook, no crabbox, no loops, no video-hosting) → nothing in this plan touches them. ✓

**Placeholder scan:** no "TBD/TODO/handle edge cases" — every step shows the exact markdown/HTML/commands. The `{{...}}` in the HTML are intentional render-time template slots (the existing card already uses them), not plan placeholders.

**Type/name consistency:** the verifier return fields (`verdict`/`evidence`/`taste_notes`/`spec_committed`) defined in Task 1's Interfaces are the same names REVIEW consumes in Task 2 and the card renders in Task 3. `VERDICT` / storyboard "beats" / "flagged" terminology is consistent across all three tasks.
