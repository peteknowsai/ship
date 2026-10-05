---
name: verify
description: >
  Prove the feature just built actually works — Codex uses the running app the way Pete
  would, in a browser and on his iPhone or a simulator, and judges it — before anything
  merges. A change Pete can try goes to him in the Codex app, where he and Codex plan and
  run the test together; the rest gets a headless read-only Codex tester. Use in ship's TEST stage (it's invoked there
  automatically) or standalone when a change is ready and you
  want proof it works: "verify this", "prove it works", "/verify". Never declares a
  feature working off the diff alone — it drives the real app.
user_invocable: true
---

# /verify — prove the feature works, then hand proof to TEST

You are the **orchestrator + fixer**. Verification splits by who's best at it:

- **The subjective question — "does the feature do what was intended?"** → a fresh
  **read-only Codex tester** (Astra on high) uses the running app the way Pete would, in a
  browser and on iOS, and judges it. It didn't write the code and comes from another model
  family (independence), and app-driving is verbose (context-isolation). It reports; it
  never fixes. A change Pete can try is handed to him in the Codex app (§2, the hand-off);
  anything else runs headless through `astra.sh test`, and its `works` lands the branch
  without Pete.
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

**iOS is the native app only, on Pete's own iPhone ("iPhone PM") or an Xcode simulator,
through agent-device.** Never the mobile web in the phone's Safari: the browser covers web
pages (Pete, 2026-10-05). The phone is the real thing, so it is the default whenever
`agent-device devices` lists it; otherwise a booted simulator. In a repo whose contract
has `ios:`, the driver runs it before the tester starts whenever the app can see the
change (its native code, or the server and APIs it calls): it builds the branch's own app,
pointed at the branch's server, installs it, and prints the IOS line the brief carries.
Without `ios:`, the brief says `IOS: none`. The tester never builds or installs: a
missing app or one talking to another server comes back `unverifiable`, and the driver
runs `ios:` and retests. Landing removes that branch app from the device again (the
pipeline skill's Land). One tester on the phone at a time: a second ship that finds
it busy tests on a simulator. The headless tester never controls the Mac's desktop; in a
hand-off Pete is watching, and Codex may use the app's computer use when the plan says so.

## 2. Verify the feature (delegate) → fix → re-verify (loop ≤ 3)

Brief from the plan/spec file if one exists (point the tester at it), else inline the
acceptance criteria. Write the brief to `<out-dir>/brief.md`, outside the repo.

**Which tester.** A change Pete can try, a page, a screen or the iPhone app, goes to him
in the Codex app: the hand-off (Pete, 2026-10-05). Anything with nothing to click, a
backend, an API, a script, gets the headless tester and lands without him. Same brief
either way, except that a hand-off brief swaps the tools sentence for "use the Codex app's
browser, computer use, and agent-device for iOS", and shots are optional: Pete watched,
so the thread link is the proof.

**The hand-off.** From the pipeline skill's directory:

```bash
scripts/codex-handoff.py start <worktree> <out-dir>/brief.md <out-dir>
```

It starts a Codex thread in the worktree (Astra on high, read-only, approvals on request)
whose first turn turns the brief into a numbered test plan, opens the thread in Pete's
Codex app (`codex://threads/<id>`), queues ship's go so Codex starts testing at once,
and prints the link and the plan. Pete watches and steers there; nobody has to say go
(Pete, 2026-10-05). The first turn runs before the app has the thread, with no network,
so it only plans: the pre-flight already proved the app is up. Then, in the background:

```bash
scripts/codex-handoff.py wait <out-dir>
```

It returns when a turn ends on a `VERDICT:` line, prints the verdict, and writes the
report to `<out-dir>/last.md`. Pete sets the pace, so re-arm it when its background
timeout ends; exit 2 means the thread is gone, so start a new one. **broken**: fix,
re-gate, push, write what changed and what to retest to `<out-dir>/retest.md`, run
`codex-handoff.py retest <out-dir> <out-dir>/retest.md`, and `wait` again. The same
thread keeps the context Pete built with it, which a fresh run would lose. `retest`
queues the note with `codex queue` and opens the thread: the Codex app runs it there as
soon as it has the thread loaded, so the fix round needs nothing from Pete but his eyes.
Post one line saying what was fixed and that Codex is retesting. If `start` fails (the Codex app
missing, Codex signed out), run the headless tester and say so.

**Local sites never prompt.** The Codex app's browser asks per site, and a site is host plus
port, so every worktree's port would ask again. `~/.codex/browser/config.toml` allows them all
once: `[origins] allowed = ["localhost", "localhost:*", "*.localhost", "*.localhost:*",
"127.0.0.1", "127.0.0.1:*"]` (entries are `*` globs on `host:port`). If the thread still
can't open the app, look for a `denied` entry in `~/.codex/browser/sessions/<thread>.toml`:
a thread's own decline beats that allow, and `start` clears the ones its first turn leaves.

**The headless tester.** From the pipeline skill's directory, in the background:

```bash
scripts/astra.sh test <worktree> <out-dir>/brief.md <out-dir>
```

`test` runs `codex exec` read-only with two MCP servers on and pre-approved: the
chrome-devtools browser, headless, and agent-device (iOS). The browser may write only in
the worktree and the out-dir, so the Codex tester's shots path is `<out-dir>/shots`, and
the driver copies what the card shows into `<shots-root>/.ship-shots/<slug>/`. The
verdict is `<out-dir>/last.md`. Every
round is a **fresh run** in a new out-dir: a tester that saw the bug is no longer
independent of the fix. Exit 3 or 4 means the run didn't happen; retry
once. Codex down or signed out (the same exit repeating, `refresh_token_invalidated` in
`stderr.txt`): fall back to a fresh Opus subagent driving the chrome-devtools MCP
(`mcp__chrome-devtools__*`, loaded with one ToolSearch call; never the claude-in-chrome
tools) with the same brief, and any iOS step in it is `unverifiable`.
The sandbox stops the tester writing to the tree, and the driver still checks `git
status` after the run (any dirt → discard it, count the round as `unverifiable`):

```
READ-ONLY: you may not edit, create, or delete any source file — screenshots go under
<absolute shots path>/ only, always as absolute paths (the browser tool can write
nowhere else, and it resolves relative paths somewhere it can't write).
You are the tester, standing in for the user. Independently confirm THIS feature works
by using the running app (the stack is already up at <URL> — reuse it, never boot your
own): in a browser through the chrome-devtools MCP, and on iOS through the agent-device
MCP when the IOS line names a device. Never control the Mac's desktop. Report what you
find; never fix anything, and never write outside the shots path.
Most new features have no automated spec — verify it agentically.
Drive it the way a person would: click, hover, fill and press keys through the browser
tools, and press, fill and scroll through agent-device. evaluate_script is for reading
state, never for firing events, because a script-fired event passes where a real
right-click or drag fails. Walk the surface you
were given, signed in the way the AUTH line says. A step you could not reach (a mic, a
bot check, a missing device) makes the verdict `unverifiable`, naming the step, even
when everything else worked.

FEATURE (what a user should now be able to do + the observable success state):
  <intent / acceptance criteria>            (or: see plan/spec file <path>)
HOW TO EXERCISE IT:
  <route + steps / API call / CLI>
STORYBOARD (a GATED ship's locked design, else 'none'):
  <storyboard path#frame-ids>, and ~/.claude/skills/impeccable/reference/craft-floor.md.
  The built screens should match their frames; a visible gap is a finding.
IOS (when the change reaches a phone, else 'none'):
  The IOS line the contract's `ios:` printed: the device ("iPhone PM" or the booted
  simulator) and the branch app's bundle id. Only that native app, never Safari. Start
  with agent-device `open <bundle> --foreground`; close the session when done.
AUTH (if behind login):
  <the repo's test-auth path: a seeded account, or `form` with its test credentials and
  everything a fresh account needs to get in, an invite code or a PIN, or 'none'>. Use ONLY that path. Do NOT mint sessions, set auth cookies, or hit a dev-login
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
console for errors along the way. A print flow: headless `window.print()` stalls the
browser tool, so judge the printout with print-media emulation first and click Print last.
Screenshot the MEANINGFUL BEATS (start → action → success), not a random dump. Judge
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

Run it before the first round and after every fix round. In ship, BUILD's pre-flight is
the first run, so skip it then unless the tree changed since. Run the repo's `tsc` / lint / unit / existing e2e as a regression sweep — and **run what the
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
`TASTE` notes, and the crystallized spec path (or none). In ship, a headless pass lays
these straight into the review card: the storyboard becomes "Proof it works," the taste
notes become "Verifier flagged." Pete reviews proof, not faith. A hand-off needs no card:
he watched it, and the thread link is the record.
