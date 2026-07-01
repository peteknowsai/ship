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
  regression sweep; pass/fail can't be rubber-stamped, and you need the error to fix it.

**You never declare the feature works yourself — only a fresh verifier can.** Reading the
diff and concluding "looks right" is exactly the failure this skill exists to prevent.

## 1. Preconditions — the caller owns these

The running app is **already up** — in ship's REVIEW the worktree's dev server is booted for
you; standalone, boot it first and note the URL. The verifier **reuses** that stack, never
boots its own.

**The generic seam (don't cross it):** if the feature is behind auth, the **repo** must
provide a local/test way to reach authed surfaces. verify does **not** mint sessions, bypass
auth, or stand up infra — that's repo plumbing, and baking it in here would couple this skill
to one app. If authed surfaces are unreachable and the repo offers no test-auth path, return
`unverifiable` with that reason — never fake a pass.

## 2. Verify the feature (delegate) → fix → re-verify (loop ≤ 3)

Brief from the plan/spec file if one exists (point the verifier at it), else inline the
acceptance criteria. Spawn a fresh **read-only** verifier sub-agent:

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

Drive the REAL flow with Playwright — walk the exact steps a user would, like clicking through
it. Screenshot the MEANINGFUL BEATS (start → action → success), not a random dump. Judge
observed vs expected. Return ONLY:

VERDICT: works | broken | unverifiable
EVIDENCE: ordered list of "<screenshot path> — <plain-language caption>"   (the storyboard)
EXPECTED: <criteria>
OBSERVED: <what actually happened>
TASTE: <0-3 short "looked off / couldn't confirm" notes, or "none">
```

- **broken** → fix the implementation, then spawn a **fresh** verifier (never reuse the one
  that saw the bug — it's no longer independent of the fix). Cap at ~3 rounds.
- **still broken after the cap**, or **unverifiable** → stop and hand the verdict + evidence
  up to the caller for Pete. Never loop forever; never merge unproven.

## 3. Regression sweep — you run the codified checks; fix red directly

Run the repo's `tsc` / lint / unit / existing e2e as a regression sweep. Triage failures
(real-bug vs stale-test); **never weaken an assertion to go green.** If a fix changes feature
behavior, re-verify (§2).

## 4. Crystallize — core journeys only

If the feature is a genuine **core journey** — auth, money, a primary product flow, NOT every
small feature — write the Playwright drive you just ran out as a committed `.spec.ts` in the
repo's e2e location, folded into the feature's own diff. Stable selectors (role/label/text;
add a small `data-testid` only when there's no good handle — never a brittle CSS path). Most
features: skip this — drive, prove, report, done. The standing suite stays thin: core flows,
not a spec per micro-feature. **Running** the committed spec in the gate is the **repo's** job
(the seam) — verify writes it, the repo wires it.

## 5. Hand back proof

Return to the caller: `VERDICT`, `EVIDENCE` (the ordered screenshot + caption storyboard),
`TASTE` notes, and the crystallized spec path (or none). In ship, REVIEW lays these straight
into the review card — the storyboard becomes "Proof it works," the taste notes become
"Verifier flagged." Pete reviews proof, not faith.
