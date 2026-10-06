---
name: verify
description: >
  Prove the feature just built actually works before anything merges: write a QA script,
  run it yourself on the running app the way Pete would (a browser through chrome-devtools;
  his iPhone or a simulator through agent-device for a native app), fix what fails and run
  it again until it passes. Codex tests only when Pete asks. Use in ship's TEST stage (it's
  invoked there automatically) or standalone when a change is ready and you want proof it
  works: "verify this", "prove it works", "/verify". Never declares a feature working off
  the diff alone — it drives the real app.
user_invocable: true
---

# /verify — prove the feature works, then hand proof to TEST

**You test it yourself, in this session** (Pete, 2026-10-05): write the QA script, run it
on the running app, fix what fails, run it again. The one who sees the bug reads the logs
and makes the fix, so a round costs a rerun, not a hand-off. Split across two sessions it
cost six rounds on one iPhone scroll bug: the tester could see it but not fix it, and the
fixer could fix it but not see it. Objective checks (tsc / lint / unit / e2e) are the
regression sweep (§3). Codex tests only when Pete asks for it: `reference/codex.md`.

**Works means every step of the script passed on the running app**, each with its
evidence: a screenshot, the agent-device diff, a response body. Reading the diff and
concluding "looks right" is exactly the failure this skill exists to prevent.

## 1. Preconditions — the caller owns these

The running app is **already up** — in ship's TEST the target is the branch's preview link
when ship built one (the host, database and sign-in Pete will test), else the worktree's dev
server, booted for you; standalone, boot it first and note the URL. Reuse that stack, never
boot a second. A preview behind the host's login wall (Vercel protection) is reached with its
automation bypass: send the `x-vercel-protection-bypass` value as an extra header on the
page (and `x-vercel-set-bypass-cookie: true` on the first load), never through Pete's
browser.

**The generic seam (don't cross it):** if the feature is behind auth, the **repo** must
provide a test way to reach authed surfaces: its contract's `test-auth:`. `seed <how>` is a
seeded account and its secret. `form <how>` means the app's own sign-in form works with test
credentials (a Clerk test instance: any address, the fixed code 424242), and then signing in
through that form, with a fresh test address per walk, is the path. verify does **not** mint
sessions, set auth cookies, hit a dev-login endpoint, bypass auth, or stand up infra — that's
repo plumbing. If authed surfaces are unreachable and the repo offers no test-auth path, the
result is `unverifiable` naming the wall, and Pete walks it — never fake a pass.

**The seeded account is the QA run's alone while it walks.** Never invite Pete to poke at
the app on the same seeded user mid-run — his concurrent clicks read as bugs. Seed a second
user for his hands-on look, or wait for the result.

**iOS, through agent-device: a native app on Pete's own iPhone ("iPhone PM") or an Xcode
simulator, and mobile web only ever in a simulator.** A web app is tested in the browser,
its mobile layout at phone width (390px) there. When the build is meant for phones (the
spec or storyboard says mobile web), the script may add the simulator's Safari at the
branch URL: a judgment call on what's being built, never a default, and never iPhone PM,
whose Safari is never used (Pete, 2026-10-05). For a native app the phone is the real
thing, so it is the default whenever `agent-device devices` lists it; otherwise a booted
simulator. In a repo whose contract has `ios:`, run it whenever the app can see the change
(its native code, or the server and APIs it calls): it builds the branch's own app, pointed
at the branch's server, installs it, and prints the IOS line. Without `ios:` there is no
device step. Landing removes that branch app from the device again (the pipeline skill's
Land), unless its IOS line says `keep=yes`. One ship on the phone at a time: a second ship
that finds it held tests on a simulator. Never control the Mac's desktop.

## 2. Write the QA script → run it → fix → rerun (≤ 3 fix rounds)

**Write `<out-dir>/qa.md`** (outside the repo) from the spec or plan, else the acceptance
criteria. Its head names what the run uses: URL, AUTH (the test-auth path, with everything
a fresh account needs, an invite code or a PIN), IOS (the line `ios:` printed, or none),
BACKEND (on `backend: per-branch`, the exact deployment, pinned on every CLI call, or seeds
land on one backend and the app reads another), PROTECTION (the bypass value, or none),
STORYBOARD (a GATED ship's frames and `~/.claude/skills/impeccable/reference/craft-floor.md`,
or none). Then numbered steps, each one thing a person does and what they should see:
"4. Scroll up slowly past the first page of history → the message you were reading stays
put". Cover every acceptance criterion, every frame the change built (a visible gap from
its frame is a failure), the edges the spec names, and a clean console. Post one line
before running, `QA: <n> steps on <surface> — <qa.md path>`, so Pete can watch and steer;
what he says mid-run changes the run.

**Run it** the way a person would, with real clicks, taps and keys:
- **Browser: the chrome-devtools MCP** (`mcp__chrome-devtools__*`, loaded with one
  ToolSearch call; headless, a fresh profile, never Pete's Chrome). Click, hover, fill and
  press keys through its tools; `evaluate_script` reads state, never fires events, because a
  script-fired event passes where a real right-click or drag fails. `emulate` covers the
  390px layout and dark mode; `handle_dialog` answers a native prompt. Check the console and
  failed requests as you go. A print flow: headless `window.print()` stalls the browser, so
  judge the printout with print-media emulation first and click Print last.
  No chrome-devtools tools in the session (ToolSearch finds none: its `npx` start failed
  at launch): drive headless Chrome through Playwright (`~/node_modules/playwright`,
  `channel: "chrome"`) with real locator clicks and keys, never events fired from
  `evaluate`, read the console through `page.on("console")`, and say in the result which
  browser ran.
- **iOS: the agent-device CLI** from the shell (`agent-device help manual-qa` and
  `help debugging` are its guides). `agent-device open <bundle> --device "iPhone PM"
  --foreground` (without `--device` it picks a simulator), then press, fill and scroll with
  `--settle` and judge from the diff it prints; `close` when done. What the phone taught
  (cells-app, 2026-10-05):
  - Read the app's own prints with `xcrun devicectl device process launch --console
    --terminate-existing --device <udid> <bundle>`, and write debug traces to stderr: a
    `print()` block-buffers off a terminal, so its lines arrive late or never.
  - Scroll a feed with `agent-device gesture pan <x> <y> <dx> <dy> <ms>` from mid-screen.
    `scroll up` starts at the bottom edge and can land on the composer, and an open keyboard
    swallows it.
  - Seed content from the Mac (the repo's own test helpers or API), never by typing it on
    the phone: `fill` garbles long text.
  - To reach a state a short test account can't (paging, a long list), shrink the constants
    in a debug build and never commit them.
  - The simulator is not the phone: three scroll fixes passed in it and failed on iPhone PM.
    A native change is proven on the phone when it is connected.
- **API, CLI, script:** run the real commands; their output is the evidence.

Screenshots only at the beats that prove a step (start → action → result), as absolute
paths under `<shots-root>/.ship-shots/<slug>/`; the agent-device diff and a page snapshot
are cheaper evidence where they show the result.

**A step fails:** you have the app open, so look before you change code — the console, the
network, the device log, a trace — and fix the cause, then re-run the gates (§3) and rerun
the failed steps plus every step the fix could touch. The same step failing twice means the
last fix was a guess: call the Skill tool with `diagnosing-bugs` and get a loop that goes red
on it (a test, a script, a trace) before the next fix. Three fix rounds without a pass:
stop, and hand the caller what keeps failing with its evidence. A step you can't reach (a
mic, a bot check, a missing device, an auth wall with no test-auth path) makes the result
`unverifiable`, naming the step, even when everything else passed. Never loop forever; never
merge unproven.

**The result** goes to `<out-dir>/result.md`:

```
VERDICT: works | broken | unverifiable
EVIDENCE: ordered list of "<screenshot path or output> — <plain-language caption>"
EXPECTED / OBSERVED: for every step that didn't pass
TASTE: <0-3 short "looked off / couldn't confirm" notes, or "none">
```

## 3. Regression sweep — you run the codified checks; fix red directly

Run it before the first QA run and after every fix round. In ship, BUILD's pre-flight is
the first run, so skip it then unless the tree changed since. Run the repo's `tsc` / lint / unit / existing e2e as a regression sweep — and **run what the
DEPLOY workflow runs, not just the test gate.** If deploy does a build/typecheck the test job
skips (`next build`, `flue build`, an app-level tsc that vitest never touches), run it locally
here: deploy-only failures are the most expensive class because they land *after* merge (a
TS7023 invisible to vitest once sailed through to a red dev deploy). Triage failures
(real-bug vs stale-test); **never weaken an assertion to go green.**

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
`TASTE` notes, and the crystallized spec path (or none). In ship they go on the review card:
the storyboard becomes "Proof it works," the taste notes "Flagged." Pete reviews proof, not
faith.
