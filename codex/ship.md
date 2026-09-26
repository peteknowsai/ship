---
name: ship
description: Ship product changes with express, self-directed, or gated workflows. Supports /ship express and /ship design. Use for implementation requests, not questions or pure research.
---

# Ship in Codex

Build the requested scope, verify it, and land it. The driver owns design, integration,
git, and reporting. Use Astra subagents directly. No supervisors, app-server dispatch,
nested coding sessions, or user-visible tasks for internal work.

## Choose the process

- `/ship express <change>`: a small fix, no spec or cards. Worktree, edit, relevant
  checks, exercise changed behavior, land. Keep it with the driver unless the actual
  work needs another agent. A new taste, money, or irreversible decision can still gate.
- `/ship design <idea>`: show a live HTML storyboard, revise it with Pete, and wait
  for design lock. Then show an HTML plan card and wait for go. Write the execution
  plan after go, then build the whole approved scope. Never downgrade this explicit verb.
- Bare `/ship <change>` or an implementation request: choose express for a small
  change. Otherwise work self-directed unless a new design or unresolved scope needs
  Pete's judgment. Do not invent gates for mechanics already authorized.

Self-directed work needs only the execution notes required to coordinate it. No
storyboard, plan card, or review card unless it helps a real decision. Scope stays
exactly what Pete requested. Never turn a complete approved feature into a partial ship.

## Establish the repo and worktree

Read the repo's AGENTS.md and CLAUDE.md. Honor `ship: no`, `gates:`, `preview:`, `dev:`,
`test-auth:`, `backend:`, `stack:`, `live:`, `land:`, `release:`, the release ritual, and any
`design of record: transplant <path>` contract. Inspect current git state first.

The phases after the plan are BUILD, TEST and LAND. TEST is ship proving its own work
(gates, a cold correctness review, `ship:verify`) and then Pete trying it on the preview
links; LAND is mechanics on his word "merge main". Nothing lands without that word unless
the contract says `land: auto`.

A new ship gets a new worktree. Reuse only the one this ship started in, never a
worktree whose branch already landed. For a Codex-managed worktree, create a feature branch if
detached. Never nest or remove Worktrunk worktrees inside an app-managed worktree.
Starting on main: create a worktree with `wt switch --create`, otherwise use
`git worktree add`. Keep the primary checkout on main and use absolute paths.
Follow an explicit repo base-branch override, otherwise branch from main. Fetch
first and branch from the remote's copy (`origin/<base>`), since a stale local base has
cost a rebase and reinstall.

Push the branch at once and open a draft tracker PR with the first commit (`land:
direct` opens none); it records work in flight and is never a review step. Push again at
every milestone and post the output of the contract's `preview:` command, one link per
app, so Pete can test mid-flight. When `preview:` is on demand, post the localhost
instead and build a preview once before TEST only when the contract or Pete calls for it.
A `release:` word runs its command only when Pete says it, never as part of landing. With `backend: shared-dev` (the default), use the app's
dev database and edit no env file; provision a per-branch backend only for `backend:
per-branch`. Keep test accounts isolated from other runs. Record the branch and worktree at start,
input gates, and completion. Before writing `.ship-stage`, ensure it is ignored
with `git check-ignore`; if needed add it to the shared git info/exclude resolved
through `git rev-parse --git-path info/exclude`. Update it at stage transitions with
one line, the bare stage word the status line reads: `discover`, `gate:1`, `plan`,
`gate:2`, `build:N:M`, `review`, or `test`.

## Design when needed

Read only the code and prior decisions needed to understand the feature. Reuse
existing components and installed dependencies. Delegate recon only for a concrete
question that can run alongside useful driver work, never as a mandatory tour.
For a reference-transplant contract, inspect and reuse the actual reference markup
and behavior. Do not redesign reference-owned surfaces.

For `/ship design` or a visual gated change:

1. Use `reference/storyboard.html` for live app frames in the product's styling.
   Show screens and interaction states with short captions. Put supporting research
   behind a disclosure. Ask only questions whose answers change the design.
2. Open the storyboard and wait for reactions. Revise until Pete locks the direction.
   Commit each gate artifact before presenting it. Mark `gate:1` at design lock requests.
3. Use `reference/go-card.html` to show the locked design, what gets built, unresolved
   choices with recommendations, and material risk. Mark `gate:2` and wait for go.
4. After go, write machine-facing execution notes with acceptance criteria, reusable
   components, file ownership, relevant gates, and exact storyboard frame references.

A nonvisual taste or scope decision can be resolved in concise prose without a mockup.
Use the existing docs home. Open HTML through Codex's file panel or serve it locally
in the in-app browser. Never require FleetView, Ghostty, or Claude-only browser tools.
Read installed impeccable guidance when designing UI. Do not expand approved scope.

## Build with Astra

Make small, coherent edits directly. Delegate only when context isolation, independent
judgment, or parallel execution saves work. Don't pay for an agent just to relay a task.

Any lane with execution notes gets them reviewed first: a fresh Astra subagent reads
them against the request or the locked design and reports a missing task, a wrong
file, a test that cannot fail, or an order that breaks. Fix what's real, then build.

- Use collaboration subagents with `model: "gpt-6-astra"`, `fork_turns: "none"`, and
  a self-contained brief. Reasoning effort is high for every worker and for the
  driver. No Anthropic models run in this workflow.
- Each worker owns named files and acceptance criteria. Tell workers they are not
  alone, must preserve others' edits, and must not commit, push, or open PRs.
- Parallelize tasks whose file ownership and dependencies do not overlap. Keep
  dependent edits sequential. Workers report changed files, checks run, and gaps.
- Keep one execution plan, only when needed. Update it instead of creating duplicate
  specs, task trackers, or progress documents. Never reduce approved scope for speed.
- Add tests for meaningful changed behavior and update the canonical docs. Prefer
  existing checks. Do not add tests that only repeat implementation wording.
- Run checks once at the right level. Worker checks cover their change; final checks
  cover the integrated result. Repeat only after edits, upstream changes, or failures
  that could invalidate the evidence. Include production build checks when applicable.

Mark build progress in `.ship-stage`. Report useful findings, not agent chatter.

## Review and prove

Sync with the landing target before final review. If upstream changes a preview
backend, refresh it before verification. Freeze source and test state during review.

Express changes: run relevant checks and exercise the affected behavior directly.
For larger work, launch a fresh Astra correctness reviewer and invoke `ship:verify`
for an independent Astra runtime verifier. They can run concurrently against the same
frozen build with isolated accounts. The driver runs final repository gates in parallel
only if those checks do not mutate the verifier's data, build, or backend.

The reviewer checks the whole branch against the approved scope, especially interfaces
between workers. It reports actionable findings with file, line, and failure scenario.
The verifier drives actual behavior and returns `works`, `broken`, or `unverifiable`.
Do not go to TEST on a mockup, a worker's claim, or tests that miss the requested
behavior. The verifier walks the preview link when one was built, else the worktree's dev
server.

The walk covers the surface Pete will open, signed in as he will be, with real clicks
rather than script-dispatched events. A path it could not reach (a mic, a bot check)
makes the verdict partial, and partial is `unverifiable`: stop and tell Pete, never cue
TEST with the gap as a footnote. Any plan item cut or swapped after his go is named in
the next message. Every wait has a deadline and a never-started check. Only a landing
ends with `result:`.

Fix real findings. Re-run affected checks and use a fresh verifier if behavior changed.
Cap repeated verification at three rounds, then report the specific blocker. Preserve
all unrelated edits. Never blindly reset or discard a dirty worktree.

Then park for Pete: push, write `test` to `.ship-stage`, post the links and what to try,
and end with `needs input: test <slug> — say "merge main"`. A change he asks for goes
back through build, push, links and verify, and parks again.

For gated visual work, `reference/review-card.html` can collect the delivered behavior
and observed evidence. Fill `LANDING_STATUS` with the verified landing result or
  the specific unapproved action. It is a report, not another approval gate. Otherwise report
results in the conversation. Do not write a card just because a template exists.

## Land and clean up

Land only on Pete's "merge main" (or on green with `land: auto`). `land: pr`, the
default: update the tracker PR's body to what shipped, mark it ready, and squash-merge it.
`land: direct`: rebase on main, re-gate, push `HEAD:main`, delete the remote branch.
Any other `land:` value is the repo's command, including a local-only repo. Re-sync and
recheck if the landing target moved. Never commit directly to main.
Do not re-ask for permission already granted. No remote and no landing contract means
report the missing integration route rather than inventing a remote or release command.

Verify landing before removing a worktree created by this run. Leave pre-existing and
Codex-managed worktrees to their owner. Never archive the user's task for cleanup.
Stop run-owned servers, remove the stage marker, and release run-owned previews when
safe. Never delete another run's resources. Never run a production deploy or push a
production database by hand: where the contract's `live:` says main is production, the
host's build does it, and you watch the exact commit's builds to completion and report the
live links before claiming it is live.

Keep unrelated suggestions as notes on the review card until
Pete asks to file them. Read existing decision history when helpful, but never write
persistent memory without an explicit request. Do not turn a run into skill surgery.

End with what shipped, the evidence, and any limitation. Include branch and worktree.
