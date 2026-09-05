---
name: verify
description: Independently verify a shipped feature by exercising its real UI, API, or CLI. Use during ship review or when asked to prove a change works.
---

# Verify in Codex

Use a fresh read-only Astra subagent through collaboration, with
`model: "gpt-6-astra"` and `fork_turns: "none"`. Give it a self-contained brief.
The driver owns fixes and regression checks. No supervisor or nested coding session.

## Prepare the brief

Provide the intended behavior, acceptance criteria, exact app URL or native app,
backend deployment, test account, and authorized authentication route. Reuse the
running stack. Isolate accounts when reviews run in parallel. Freeze source and
backend state until the verdict returns. Record git status before and after.

Start the brief with "READ-ONLY: do not edit, create, or delete source files."
Temporary checks and screenshots go under a per-run temporary directory. Tell the
verifier to use available browser or native app tools for UI, or shell tools for API
and CLI behavior. For skill changes, exercise realistic workflow decisions instead
of inventing a browser UI. Do not require `/browse`, `pane`, or Claude-specific tools.

An existing authorized session or the repo's test-auth path is usable. Never bypass
auth or manufacture credentials. Unreachable real behavior is `unverifiable`.
Mockups and storyboards never substitute for runtime evidence.

## Return evidence

The verifier reports:

- Verdict: `works`, `broken`, or `unverifiable`.
- Expected behavior and what it actually observed.
- Ordered evidence, including screenshots for meaningful UI states or command output
  for CLI/API flows. Show the trigger and result, not arbitrary screenshots.
- Actionable failures and any parts it could not verify.

Send the result to the driver and finish with the same verdict. No special `-o` file
convention is required. Source edits by a verifier invalidate the round; report and
preserve them for the driver to inspect. Never discard unrelated work.

## Fix and recheck

The driver fixes failures, runs affected regression and production build checks,
and requests a fresh verifier when behavior changes. Cap at three rounds. A remaining
failure or unverifiable core flow blocks a success claim and landing.

Keep useful regression coverage for core journeys using the repo's existing test
setup. Don't add a framework or a permanent test for every manual verification step.
Reuse valid test evidence; repeat only when changes or unresolved failures justify it.
