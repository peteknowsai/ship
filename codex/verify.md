---
name: verify
description: Prove a shipped feature works by writing a QA script and running it yourself against its real UI, API, or CLI, fixing until it passes. Use during ship's TEST or when asked to prove a change works.
---

# Verify in Codex

The driver tests its own work (Pete, 2026-10-05): it writes a QA script, runs it on the
running app, fixes what fails and runs it again. The one who sees the bug fixes it, so a
round is a rerun, not a hand-off. No subagent tester, no nested coding session.

## Write the QA script

Write `<out-dir>/qa.md`, outside the repo, from the spec or plan, else the acceptance
criteria. Its head names the app URL or native app, the backend deployment, the test
account and the authorized authentication route (with any invite code or PIN). Then
numbered steps, each one thing a person does and what they should see. Cover every
acceptance criterion, the storyboard frames the change built, the edges the spec names,
and a clean console. Reuse the running stack. Freeze upstream (no merges or rebases)
until the run ends; its own fixes are the only edits.

## Run it

Use it the way Pete would: a browser for web UI, with a mobile layout at phone width
(390px) there, and agent-device for iOS. A native app is the branch's own app the
contract's `ios:` installed, on Pete's iPhone ("iPhone PM") when it is connected (pass
`--device "iPhone PM"`; without it agent-device picks a simulator), else a booted
simulator. Mobile web, when what's built is meant for phones, is a simulator's Safari,
never the phone. Never control the Mac's desktop. Real clicks, taps and keys; a script
reads state, never fires events. Shell tools cover API and CLI behavior. On the phone,
scroll a feed with `agent-device gesture pan` from mid-screen, seed long text from the
Mac rather than typing it, and read the app's prints with `xcrun devicectl device process
launch --console`.

An existing authorized session or the repo's test-auth path is usable. Never bypass
auth or manufacture credentials. Unreachable real behavior is `unverifiable`.
Mockups and storyboards never substitute for runtime evidence.

## Fix and rerun

A failing step: look first (console, network, device log, a trace), fix the cause, run
the affected regression and production build checks, then rerun the failed steps and
every step the fix could touch. The same step failing twice gets a loop that goes red on
it before the next fix. Cap at three fix rounds. A remaining failure or an unreachable
core step blocks a success claim and landing.

## Return evidence

- Verdict: `works`, `broken`, or `unverifiable`.
- Ordered evidence: screenshots for meaningful UI states, command output for CLI/API
  flows. Show the trigger and result, not arbitrary screenshots.
- Expected and observed for every step that didn't pass, and any part it could not reach.

Keep useful regression coverage for core journeys using the repo's existing test
setup. Don't add a framework or a permanent test for every manual verification step.
Reuse valid test evidence; repeat only when changes or unresolved failures justify it.
