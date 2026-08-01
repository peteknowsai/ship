---
name: router
description: Use ONLY when executing the build tasks of an implementation plan (the BUILD stage of /ship) — dispatching each coding task to GPT-5.6 sol via background codex exec. Fable always drives (every stage, including BUILD) and dispenses the coding tasks; sub-overhead work stays inline on the driver. Do NOT invoke for planning, design, review, merge, or normal work — that all stays on the driver. Never route to Sonnet.
---

# router — the driver dispenses BUILD coding to GPT-5.6 sol

**Scope: the BUILD stage only.** Discover, plan, design, merge, and every normal task
stay on the driver; router fires only when dispatching the concrete build tasks of an
already-written implementation plan. (Ship's other codex offloads — review mode in
REVIEW, recon in DISCOVER, verify's browser walks — are wired directly in the ship
skill; the invoke rules below apply to them all the same.)

**The dial (Pete, 2026-07-28): Fable always drives — every stage, including BUILD — and
dispenses the coding tasks to codex.** Driver tokens buy judgment (design, briefs,
triage, gates, git, the final say); codex tokens buy drafts — codex does markedly better
work under a well-authored brief, and brief-writing is what the driver excels at.
**Never route to Sonnet** — retired from this pipeline entirely. The dial is a target,
not a quota: *"use your judgment and make sure you get the job done, that's what's
important."* If a task wants different handling, follow the task and log why.

**Billing:** codex bills the ChatGPT subscription — the savings hold only on its
*subscription* login; an `OPENAI_API_KEY` in the env silently bills per-call
(sanity-check on first use). **Fast mode is ON for ship dispatches** (Pete, 2026-08-01,
reversing the 07-13 cost ruling — the ~2.5× credit burn for ~1.5× speed is accepted):
add `-c fast_mode=true` to every dispatch; the global `~/.codex/config.toml` keeps
`fast_mode = false` for interactive use. **xhigh is still the effort floor** — never
save on thinking.
For Anthropic-model offloads, never shell out to `claude -p` from inside a session —
use harness subagents (the Agent tool): same models, same Max billing, native tracking.
`claude -p` belongs in scripts/cron, not inside a run.

## The assignment heuristic

For each build task, in order:

1. **Design still open, real risk, ambiguous?** → the driver closes the judgment first
   (decide the design, settle the ambiguity), then dispatches the fully-specified
   remainder. Judgment inseparable from the writing → the driver does the task inline.
2. **Fully specified and self-contained, with real work to explore?** → **GPT-5.6 sol**
   (`codex exec`, xhigh). The default destination for drafting.
3. **Smaller than the dispatch overhead (~5–10 min: brief, launch, poll, read)?** → the
   driver writes it inline. A rename, a config line, a verbatim write already authored
   in the brief, wiring a triaged review fix — all finish faster than the overhead.
   Real multi-file exploration still dispatches.
4. **A wrong diff twice on the same task?** → escalate: the driver rewrites inline; log
   `escalated→driver`. A third codex round costs more than it saves. **Slow is not
   failure** — never escalate because a worker is taking a while.
5. **Skill/agent prose and frontend design — never routed.** SKILL.md files, agent-
   voiced docs, HTML design specs, mockups, styling — anywhere taste is the
   deliverable — the driver authors inline. Frontend *mechanics* with the design closed
   route like any other closed-brief task.

**Browser work is codex's, always** — verify walks, design QA, live-product grounding:
codex scripts its own Playwright, saves screenshots to disk. Auth-walled: the logged-in
codex Chrome (`~/.codex/codex-chrome`, CDP :9222) via `connectOverCDP`. Never drive
the browser from the driver.

## Patience & liveness

An xhigh worker can sit quiet for many minutes — runs killed at a 2-minute timeout were
healthy and got mislogged as failures. **Dispatch in the background with a generous
window (15–30 min), checking in rather than killing.** Don't drop effort to go faster.

- **Startup liveness tell:** a healthy `codex exec` creates its `~/.codex/sessions`
  rollout file within seconds. Process alive with no session file after ~2 min = dead
  at startup (held stdin, bad flag) — kill and redispatch. Distinct from "slow is
  fine," which applies only after the session exists.
- **Stall budget: ~15 min of silence → an active look** (process in `ps`? result file
  or working tree moving?). A live run that's just slow gets left alone. A run that
  exited without a result, or shows zero output and zero writes: kill the chain,
  `codex exec resume <session-id>` if it left a session, else redispatch `-retry1`,
  and log the row honestly.

## Tag and track every dispatch

Pete runs concurrent sessions; untagged hung runs sit unnoticed.

- **Tag:** first line of every brief is
  `[ship-dispatch: <project> · <branch> · <task-slug>]` (append `-retryN` on
  redispatch) — it rides in argv, so `ps aux | grep "codex exec"` attributes every run.
  Tell the worker the tag is routing metadata to ignore.
- **Track:** dispatch with the harness's `run_in_background` (notifies on exit) —
  never a hand-rolled `&`.

## The discipline (non-negotiable)

Whoever drafts, **the driver owns the envelope**:

1. **The driver writes the brief** — exact files, signatures, test cases, constraints.
   A vague brief wastes the savings in fix rounds.
2. **The driver reviews the diff and runs the gates** before anything is committed —
   never trust a "tests pass" claim.
3. **The driver owns git** — codex has auto-opened PRs and committed unprompted; rein
   it in.
4. **One writer per branch at a time** — concurrent writers on one working tree
   collide. Serialize, or give each its own sub-worktree.

## CLI quick-reference

```
cd <repo> && codex exec -c model_reasoning_effort=xhigh -c fast_mode=true -o <result-file> "<full task brief>" < /dev/null
```

- **`-o <result-file>` on every dispatch** (e.g. `/tmp/ship-<task-slug>-result.md`) —
  the result survives a truncated buffer or missed exit. Read the file, not scrollback.
- **`< /dev/null` is mandatory** — a held-open stdin hangs `codex exec` at startup
  forever, no session file, no error.
- **cwd outside a git repo → `--skip-git-repo-check`**, or codex exits fatally.
- **Always the sol variant** — `gpt-5.6-sol`, never plain `gpt-5.6`. Leave the model
  unset to inherit `~/.codex/config.toml` (sol, standard tier); if it must be explicit,
  `-m gpt-5.6-sol`.
- Fix rounds: capture the session id and `codex exec resume <session-id>
  "<follow-up>"`. **Never `resume --last`** — with concurrent sessions it's whichever
  run finished most recently anywhere on the machine.
- **Reviews use codex's native review mode, not a hand-rolled brief:**
  `codex exec review --base <branch> -o <result-file> < /dev/null` (or
  `--uncommitted` / `--commit <sha>`). **No positional prompt** — codex errors when a
  prompt is combined with any diff-source flag. No prompt means no dispatch tag — name
  the `-o` file after the slug instead. Read-only by construction.
- **Never the codex-companion runtime for background work** — its per-worktree broker
  daemon dies mid-run in a multi-session workflow and the job orphans "running"
  forever. Companion only for short foreground calls; `codex exec` for everything
  dispatched. Never the `codex:codex-rescue` subagent (Sonnet forwarder; retired).

## The ledger

Maintain `~/.claude/skills/router/ledger.md` — the single canonical ledger, outside any
repo or plugin directory (an installed plugin isn't writable state). **After every
delegated build task**, append a row:

`date | project | task (short) | task-type | engine | outcome | fix-rounds | note`

- **task-type**: `specific-coding` · `integration` · `mechanical`
- **outcome**: `clean` · `fixed-N` · `escalated→driver` · `abandoned`
- Headline metric: **first-pass-clean rate per task-type**, plus escalation rate. A
  task-type that keeps escalating stays on the driver — say so when reporting a plan's
  execution.

## When NOT to delegate (driver-inline, always)

- Auth, secrets, money, migrations, irreversible or outward-facing actions.
- A still-fuzzy spec (clarify/plan first — that's not a build task yet).
- Tiny verbatim writes already authored in the brief.
- The final review of a branch, and all of git.
