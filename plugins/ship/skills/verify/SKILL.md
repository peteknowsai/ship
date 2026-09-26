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

The running app is **already up** — in ship's TEST the target is the branch's preview link
when ship built one (the host, database and sign-in Pete will test), else the worktree's dev server, booted for you; standalone, boot it first and note the URL.
The verifier **reuses** that stack, never boots its own. A preview behind the host's login
wall (Vercel protection) is reached with its automation bypass: the caller passes the
`x-vercel-protection-bypass` value, and the verifier sets it as an extra header on its
page (and `x-vercel-set-bypass-cookie: true` on the first load), never through Pete's
browser.

**The generic seam (don't cross it):** if the feature is behind auth, the **repo** must
provide a test way to reach authed surfaces: its contract's `test-auth:`. `seed <how>` is a
seeded account and its secret. `form <how>` means the app's own sign-in form works with test
credentials (a Clerk test instance: any address, the fixed code 424242), and then signing in
through that form, with a fresh test address per walk, is the path. verify does **not** mint
sessions, bypass auth, or stand up infra — that's repo plumbing, and baking it in here would
couple this skill to one app. If authed surfaces are unreachable and the repo offers no test-auth path,
return `unverifiable` naming the wall, and Pete walks it — never fake a pass.

**The seeded account is the verifier's alone while a walk is in flight.** Never invite Pete
to poke at the app on the same seeded user mid-round — his concurrent clicks read as bugs
(a shared account once produced a false `broken` that cost a diagnosis round). Seed a second
user for his hands-on look, or wait for the verdict. The chrome-devtools browser is
headless with a fresh profile per session, so it never fights Pete for a tab — but two
concurrent walks on one seeded account still collide on the backend.

## 2. Verify the feature (delegate) → fix → re-verify (loop ≤ 3)

Brief from the plan/spec file if one exists (point the verifier at it), else inline the
acceptance criteria. The verifier is a **fresh subagent** — fresh so it judges the
feature rather than its own work. It drives the running app through the
**chrome-devtools MCP** (`mcp__chrome-devtools__*`, loaded with one ToolSearch call;
never the claude-in-chrome tools) and captures screenshots as it goes. The brief must open with "READ-ONLY: edit no source
files" — nothing enforces that at the tool layer, so the brief carries the constraint,
and the driver eyeballs `git status` in the worktree after the run
(any dirt → discard it, count the round as `unverifiable`):

```
READ-ONLY: you may not edit, create, or delete any source file — screenshots go under
<absolute shots path>/ only, always as absolute paths (the browser tool can write
nowhere else, and it resolves relative paths somewhere it can't write).
Independently confirm THIS feature works by driving the running app in the browser (the
stack is already up at <URL> — reuse it, never boot your own). First load the browser
tools in one call: ToolSearch "select:mcp__chrome-devtools__new_page,
mcp__chrome-devtools__navigate_page,mcp__chrome-devtools__take_snapshot,
mcp__chrome-devtools__click,mcp__chrome-devtools__fill,mcp__chrome-devtools__take_screenshot,
mcp__chrome-devtools__list_console_messages,mcp__chrome-devtools__evaluate_script".
Most new features have no automated spec — verify it agentically.
Drive it the way a person would: click, hover, fill and press keys through the browser
tools. evaluate_script is for reading state, never for firing events, because a
script-fired event passes where a real right-click or drag fails. Walk the surface you
were given, signed in the way the AUTH line says. A step you could not reach (a mic, a
bot check, a missing device) makes the verdict `unverifiable`, naming the step, even
when everything else worked.

FEATURE (what a user should now be able to do + the observable success state):
  <intent / acceptance criteria>            (or: see plan/spec file <path>)
HOW TO EXERCISE IT:
  <route + steps / API call / CLI>
AUTH (if behind login):
  <the repo's test-auth path: a seeded account, or `form` with its test credentials, or
  'none'>. Use ONLY that path. Do NOT mint sessions, set auth cookies, or hit a dev-login
  endpoint yourself, and use the real login UI only when the path is `form`. If it's 'none' or
  the path fails, return `unverifiable` and stop — never improvise a way past auth.
PROTECTION (a preview behind the host's login wall):
  <the bypass value, or 'none'>. Send it as the `x-vercel-protection-bypass` header on
  every request of your page; never sign in to the host yourself.
BACKEND (repos with `backend: per-branch`):
  <the exact deployment the app is serving>. Pin it on EVERY CLI call
  (--preview-name/--deployment). Unpinned calls resolve to a different deployment than the
  app reads, so your seeds land on one backend and the browser on another — that split-brain
  reports as a broken feature and burns the whole round.

Drive the REAL flow — walk the exact steps a user would, clicking through it. Check the
console for errors along the way. Screenshot the MEANINGFUL BEATS (start → action → success), not a random dump. Judge
observed vs expected. Return ONLY:

VERDICT: works | broken | unverifiable
EVIDENCE: ordered list of "<screenshot path> — <plain-language caption>"   (the storyboard)
EXPECTED: <criteria>
OBSERVED: <what actually happened>
TASTE: <0-3 short "looked off / couldn't confirm" notes, or "none">

This report is your FINAL MESSAGE — it is what the caller reads;
finishing without it is an incomplete run.
```

**Auth-walled surface with no test-auth path (the AUTH line says so):** the verifier
walks everything short of the wall, and the verdict is `unverifiable` naming the
wall. Park with a `needs input:` so Pete walks that part himself.

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
small feature — write the drive you just walked as a committed Playwright `.spec.ts` in the
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
