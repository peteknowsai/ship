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
to one app. If authed surfaces are unreachable and the repo offers no test-auth path, the
blessed alternative before `unverifiable`: **attach to the codex Chrome** — a dedicated
logged-in Chrome instance (profile `~/.codex/chrome-profile`, launch with
`~/.codex/codex-chrome` if `curl -s http://127.0.0.1:9222/json/version` says it's down);
the verifier's Playwright attaches with
`chromium.connectOverCDP("http://127.0.0.1:9222")` and drives real logged-in tabs. Pete
logs into each site there once; sessions persist. If the needed login exists only in
Pete's *personal* Chrome, the last resort is a Claude subagent (`Agent(model: opus)`,
claude-in-chrome tools). Note in the verdict which route was used. Otherwise return
`unverifiable` with the reason — never fake a pass.

**The seeded account is the verifier's alone while a walk is in flight.** Never invite Pete
to poke at the app on the same seeded user mid-round — his concurrent clicks read as bugs
(a shared account once produced a false `broken` that cost a diagnosis round). Seed a second
user for his hands-on look, or wait for the verdict. This applies to the codex Chrome too
(its logins are shared state) and doubly to claude-in-chrome, which is his real profile;
Playwright's own isolated browser is immune by construction.

## 2. Verify the feature (delegate) → fix → re-verify (loop ≤ 3)

Brief from the plan/spec file if one exists (point the verifier at it), else inline the
acceptance criteria. The verifier is a fresh **background codex dispatch** — GPT-5.6 sol
is the pipeline's browser engine (Pete's call, 2026-07-11): from the worktree,
`codex exec -o <result-file> "<brief below>" < /dev/null` (router dispatch rules apply —
background, stall budget, read the result file, not scrollback). codex scripts and runs
its own Playwright against the running app and saves screenshots to real files. The
brief must open with "READ-ONLY: edit no source files" — codex review-mode's
tool-enforced read-only doesn't apply to a plain exec, so the brief carries the
constraint, and the driver eyeballs `git status` in the worktree after the run
(any dirt → discard it, count the round as `unverifiable`):

```
READ-ONLY: you may not edit, create, or delete any source file — throwaway Playwright
scripts and screenshots go under /tmp/verify-<slug>/ only. Independently confirm THIS
feature works by driving the running app with Playwright (the stack is already up at
<URL> — reuse it, never boot your own). Most new features have no automated spec —
verify it agentically.

FEATURE (what a user should now be able to do + the observable success state):
  <intent / acceptance criteria>            (or: see plan/spec file <path>)
HOW TO EXERCISE IT:
  <route + steps / API call / CLI>
AUTH (if behind login):
  <the repo's local/test-auth path, or 'none'>. Use ONLY that path. Do NOT mint sessions, set
  auth cookies, log in through the real login UI, or hit a dev-login endpoint yourself. If it's
  'none' or the path fails, return `unverifiable` and stop — never improvise a way past auth.

Drive the REAL flow with Playwright — walk the exact steps a user would, like clicking through
it. Screenshot the MEANINGFUL BEATS (start → action → success), not a random dump. Judge
observed vs expected. Return ONLY:

VERDICT: works | broken | unverifiable
EVIDENCE: ordered list of "<screenshot path> — <plain-language caption>"   (the storyboard)
EXPECTED: <criteria>
OBSERVED: <what actually happened>
TASTE: <0-3 short "looked off / couldn't confirm" notes, or "none">

This report is your FINAL MESSAGE — it lands in the -o result file the caller reads;
finishing without it is an incomplete run.
```

**Auth-walled surface (the AUTH line forces it):** point the same codex verifier at the
**codex Chrome** instead of a fresh browser — add to the brief: "attach with
`chromium.connectOverCDP('http://127.0.0.1:9222')` and drive a new tab there; it is
logged in." (Launch `~/.codex/codex-chrome` first if :9222 is down; if the site isn't
logged in there yet, park with a `needs input:` asking Pete to log in once — sessions
persist after that.) **Last resort only** — the login exists solely in Pete's personal
Chrome: a Claude subagent (`Agent(model: opus)`, unnamed one-shot, claude-in-chrome
tools). Its screenshot reality: MCP screenshots render inline-only and the download
fallback works ONCE per tab — save the one file early, use DOM measurements as
storyboard substitutes for the rest (acceptable evidence). Note in the verdict which
route was used.

- **broken** → fix the implementation, then spawn a **fresh** verifier (never reuse the one
  that saw the bug — it's no longer independent of the fix). Cap at ~3 rounds.
- **still broken after the cap**, or **unverifiable** → stop and hand the verdict + evidence
  up to the caller for Pete. Never loop forever; never merge unproven.

## 3. Regression sweep — you run the codified checks; fix red directly

Run the repo's `tsc` / lint / unit / existing e2e as a regression sweep — and **run what the
DEPLOY workflow runs, not just the test gate.** If deploy does a build/typecheck the test job
skips (`next build`, `flue build`, an app-level tsc that vitest never touches), run it locally
here: deploy-only failures are the most expensive class because they land *after* merge (a
TS7023 invisible to vitest once sailed through to a red dev deploy). Triage failures
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
