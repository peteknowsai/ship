---
name: ship
description: Ship product changes with express, self-directed, or gated workflows. Supports /ship express, /ship design, and /ship next. Use for implementation requests, not questions or pure research.
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
- `/ship next`: read the board's Next column, enrich thin cards using repo context,
  and report ship-now, needs-design, and too-thin groups. Ship whole cards sequentially,
  each in its own worktree. Present one combined design review for needs-design cards.
  Leave too-thin cards with the specific missing question. No board means explain that
  this verb cannot run. A failed card does not block unrelated cards.

Self-directed work needs only the execution notes required to coordinate it. No
storyboard, plan card, or review card unless it helps a real decision. Scope stays
exactly what Pete requested. Never turn a complete approved feature into a partial ship.

## Establish the repo and worktree

Read the repo's AGENTS.md and CLAUDE.md. Honor `ship: no`, gate commands, preview
backend, test-auth route, deployment lane, release ritual, `land:`, and any
`design of record: transplant <path>` contract. Inspect current git state first.

Reuse a feature worktree. For a Codex-managed worktree, create a feature branch if
detached. Never nest or remove Worktrunk worktrees inside an app-managed worktree.
Starting on main: create a worktree with `wt switch --create`, otherwise use
`git worktree add`. Keep the primary checkout on main and use absolute paths.
Follow an explicit repo base-branch override, otherwise branch from main.

Provision only the preview resources the repo requires. Keep its backend, URL, and
test account isolated from other runs. Record the branch and worktree at start,
input gates, and completion. Before writing `.ship-stage`, ensure it is ignored
with `git check-ignore`; if needed add it to the shared git info/exclude resolved
through `git rev-parse --git-path info/exclude`. Update it at stage transitions.

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

- Use collaboration subagents with `model: "gpt-6-astra"`, `fork_turns: "none"`, and
  a self-contained brief. Let the configured reasoning effort apply unless the task
  or user needs an explicit setting. Do not lower it merely to chase speed.
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
Do not merge on a mockup, a worker's claim, or tests that miss the requested behavior.

Fix real findings. Re-run affected checks and use a fresh verifier if behavior changed.
Cap repeated verification at three rounds, then report the specific blocker. Preserve
all unrelated edits. Never blindly reset or discard a dirty worktree.

For gated visual work, `reference/review-card.html` can collect the delivered behavior
and observed evidence. Fill `LANDING_STATUS` with the verified landing result or
  the specific unapproved action. It is a report, not another approval gate. Otherwise report
results in the conversation. Do not write a card just because a template exists.

## Land and clean up

Honor `land:` when present, including a local-only repo. Otherwise use a GitHub PR,
wait for required checks, and squash-merge on green within existing authorization.
Re-sync and recheck if the landing target moved. Never commit directly to main.
Only pause for a genuinely unapproved choice, money action, or production release.
Do not re-ask for permission already granted. No remote and no landing contract means
report the missing integration route rather than inventing a remote or release command.

Verify landing before removing a worktree created by this run. Leave pre-existing and
Codex-managed worktrees to their owner. Never archive the user's task for cleanup.
Stop run-owned servers, remove the stage marker, and release run-owned previews when
safe. Never delete another run's resources. Deploy only through the repo's authorized
lane and watch the exact commit's deployment to completion before claiming it is live.

Update existing board cards when authorized. Keep unrelated suggestions as notes until
Pete asks to file them. Read existing decision history when helpful, but never write
persistent memory without an explicit request. Do not turn a run into skill surgery.

End with what shipped, the evidence, and any limitation. Include branch and worktree.
