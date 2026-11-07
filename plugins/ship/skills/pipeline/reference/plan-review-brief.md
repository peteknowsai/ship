# Plan review brief

The brief PLAN hands Wonder, or the Opus subagent reading in its place. Copy it into a file
in the job's tmp, fill the brackets, and add any check this plan's shape calls for.

---

You are reviewing an execution plan before any code is written. Read only; change nothing.

Repo: [repo], worktree [absolute path] at HEAD [sha] (branch [branch]).

Read, in this order:
1. [The storyboard Pete locked, `specs/designs/<file>.html`: every frame inside
   `<template data-frame>` and every question under the rows. On SELF-DIRECTED: the spec.]
2. [The execution plan, `specs/plans/<file>.md`.]
3. The repo's ship contract (its `CLAUDE.md` / `AGENTS.md`) and the code the plan changes.

Find, with file:line evidence for each:
- **A frame or requirement no task covers.** Map each frame and requirement to its task and
  list the orphans: one plan built a spec's intro and none of the screens its frames asked
  for, and Pete caught it mid-build.
- **A missing task, a wrong file, a test that cannot fail, an order that breaks** (a task
  that depends on one after it), and a seam two tasks each assume the other owns.
- **A concurrency fix whose guard checks only which write is newer and not whose it is**
  (CEL-152's newest-wins rule passed plan review; both branch readers caught it).
- **A screen that waits on someone else with no way back to it.** Trace how the user
  returns once the other side acts: one plan's payoff screen was unreachable without
  re-walking the intro.
- **A new floating surface** (a popover, a hover card, a menu that stays open while the
  person works) **that an app-wide check counts as a modal or overlay**: get-the-apps' card
  took `role="dialog"`, ModalLayer's `overlayIsOpen` went true, and ⌘B and every shortcut
  not marked to work over a modal stopped. Both branch readers caught it; the plan read didn't.
- **A step that copies a secret from somewhere it can't be read back** (a Vercel sensitive
  variable pulls as a placeholder): it becomes a planned rotation on both sides, and the
  card says it signs everyone out once.
- **Every third-party API the plan calls**: paging, resuming from a saved cursor after a
  pause, what a deleted or cancelled item looks like, and items the API expands (recurring
  events). One plan review passed four such bugs that only branch review caught
  (muse-7-notifier, 2026-10-14).
- **A task that reads what another part of the app produces** (a loop's brief, a tool's
  payload) quotes a real sample of it, never the storyboard's mock: one plan parsed a
  "Price" heading from a mock when the live brief says "Budget" (market-loops, 2026-10-15).
- **A claim about how a dependency behaves at runtime**, checked in its installed code
  (`node_modules/<pkg>/dist`), not its docs: a review once took Eve's docs on queued
  messages at their word, and the runtime did otherwise (2026-10-14).
- **The plan's `## QA cases`**: a case that can't catch the failure it's meant to, a
  failure no case catches, or a walk on an app the contract doesn't check (cells-app checks
  on Homebody), where that app's own tests stand in (incidents: Design). A case whose screen
  shows only when a model chooses it is two: the choice as a rate over fresh runs on main
  and the branch, with the rate the plan expects named up front and 0 on the branch a fail,
  and the screen reached by seeding through the real write path the model would use
  (feed-imagery's writer picked no card in 6 runs, main's in 0 of 148).

Skip style, wording and taste. Number each finding, give it a severity (blocker,
should-fix, nit), the evidence, and the smallest fix as task, problem, fix.
