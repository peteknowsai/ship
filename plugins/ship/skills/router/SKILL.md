---
name: router
description: Use ONLY when executing the build tasks of an implementation plan (the BUILD stage of /ship) — deciding, per task, whether the work goes to Opus or GPT-5.5 (codex). Two engines split per Pete's current dial (see "Target mix" — currently ~20/80 Opus/GPT-5.5), self-tuning via a ledger. Do NOT invoke for planning, design, review, merge, or normal work — that all stays on the driver (the harness model). Never route to Sonnet.
---

# router — split BUILD-stage coding across Opus and GPT-5.5

**Scope: the BUILD stage only.** Discover, plan, design, merge, and every normal
task stay on **the driver** — the harness model running the session (Fable) — as
usual; do not invoke router for them. Router fires *only* when the driver is
dispatching the concrete build tasks of an already-written implementation plan.
Outside build, there is no routing decision. (Ship's other codex offloads —
adversarial review in REVIEW, mechanical recon in DISCOVER — are wired directly
in the ship skill, not through router. The constant everywhere: **design,
planning, and the final say stay with Fable**; codex is inference muscle.)

Two engines:

- **GPT-5.5** — via the **codex-companion runtime** (OpenAI's `codex` plugin for
  Claude Code; see the quick-reference), **default effort `xhigh`, Fast mode on**
  (`service_tier = "fast"` + `[features] fast_mode = true` in `~/.codex/config.toml`
  — global, every codex run inherits it; ~1.5× faster for 2.5× the credit burn, and
  Pete has chosen to spend it — never turn it off to save codex credits). On Pete's
  Codex plan: effectively **unlimited and off-Max entirely**.
- **Opus** — an Opus subagent: `Agent(model: opus)` in Claude Code; under Codex
  Desktop, an Opus-capable subagent tool if the harness exposes one (search the
  available tools first) — if none, keep the task on the driver and log
  `driver-no-opus`. On Claude Max, drawing on the weekly Opus quota.

**Never route to Sonnet** — Sonnet 5 is retired from this pipeline entirely (Pete's
call), whatever the current mix.

**The mix is Pete's dial, not a constant.** He retunes it as quota reality changes
(it has swung from 50/50 to 95/5 codex and back inside a week). The current dial
lives in **"Target mix"** below — when Pete says "go X/Y," that section (and this
description) is the only thing to edit. The heuristics, discipline, and patience
rules below hold at any mix.

**Auth caveat:** the codex savings only hold if `codex` uses its *subscription*
login, not an API key (an `OPENAI_API_KEY` in the env would silently bill
per-call). On first use each session, sanity-check codex is logged into Pete's plan.

## Prime directive: success over the mix

The dial is a **target, not a quota.** You (the driver) decide each assignment —
optimize for the work getting done *well*, and **self-adjust freely** as the ledger
shows what works. If a task wants a different engine than the split suggests, follow
the task and log why. Pete: *"use your judgment and make sure you get the job done,
that's what's important."*

## The two engines

| Engine | Invoke | Best at |
|--------|--------|---------|
| **GPT-5.5** | companion runtime: `task --background --write --effort xhigh "<brief>"` (cwd = repo), Fast mode on by default | Fully-specified, self-contained coding with real work to explore: figure out signatures, write tests against real types, work through a well-briefed problem. "Here's exactly what to build" → it builds it well |
| **Opus** | `Agent(model: opus)` | Judgment and integration: design still open mid-task, cross-file integration, real risk, irreversible surfaces, ambiguity a brief can't close — plus solid well-specified coding when the split calls for it |

**You (the driver) dial thinking per task — and default to MORE thinking, not
less.** codex: `xhigh` unless you have a reason to drop (usage is unlimited — spend
it). Opus subagents: `high` floor, `xhigh` for the gnarly ones; go lower only for
genuinely mechanical work. **Slow is fine — the answer to an engine taking a while
is a longer timeout, not less thinking or a different engine** (see the patience
note).

## Target mix  ← Pete's dial — edit here when he retunes it

**Current dial (2026-07-02): Opus ~20 / GPT-5.5 ~80** — Opus/Max quota is very
tight; reserve Opus for tasks that genuinely need its judgment and send everything
else to codex. **Fable has the final say at any mix** — the driver owns design,
planning, briefs, triage, and merge; the dial only moves who drafts the code.

Assign by **fit first**, then glance at the running split and rebalance only the
borderline tasks. Never hand a judgment task to codex just to hit the number — log
the drift and why. When a task fits both engines equally, alternate toward
whichever side of the split is behind.

## The assignment heuristic

For each build task, ask in order:

1. **Needs Opus-grade judgment** — design still open, cross-file integration,
   real risk, irreversible, ambiguous mid-flight? → **Opus.**
2. **Fully specified and self-contained, with real work to explore** — exact
   files, signatures, test cases, no open design questions? → **GPT-5.5 (codex,
   xhigh).**
3. **Solid, well-specified coding that fits either?** → balance the split (see
   the dial above).
4. **Tiny verbatim write, content already authored in the brief?** → the **driver
   writes it inline** — faster than spinning up any subagent or waiting on codex.
5. **codex produced a *wrong* diff twice on a task?** → escalate to **Opus**, log
   `escalated→opus`. A third fix round costs more than it saves. **Slow is not
   failure** — never escalate (or kill a run) because codex is taking a while.

### Patience note (hard-won — read before sending to codex)

codex can sit quiet for many minutes at xhigh — past runs were killed at a
2-minute timeout before codex had written a single file, and those got mislogged
as failures. They weren't; they were impatience. **We have time: dispatch with
`task --background` and give it a generous window — think 15–30 minutes, not 2 —
checking `status` rather than killing it.** Don't drop effort to make it faster;
xhigh + patience is the deal. The one true exception: a **tiny verbatim write
whose exact content is already in the brief** — that's not a codex task at any
speed, the driver writes it inline (heuristic #4).

### Tag and track every codex dispatch

Pete runs concurrent sessions dispatching codex at once — untagged and
untracked, a hung run sits unnoticed until someone wonders why a task never
landed (it has happened). So:

- **Tag:** the first line of every codex brief is
  `[ship-dispatch: <project> · <branch> · <task-slug>]` (append `-retryN` on
  redispatch). The companion runtime shows it as the job's summary in `status`,
  so any session, and Pete, can attribute every run at a glance. Tell codex in
  the brief that the tag line is routing metadata to ignore.
- **Track:** dispatch with `task --background`, note the returned job id, and
  check `status <job-id>` at each check-in. Patience (15–30 min) is for
  **live** runs — `status` says `running` and the phase/working tree is moving.
  A job that reports `failed`, or a window that elapses with no progress, is
  not a patience case: `cancel` it if needed, redispatch with `-retry1`, and
  log the row honestly (`abandoned` or `fixed-N`, note "hung").

## The discipline (non-negotiable, both engines)

Whoever drafts the code, **the driver owns the envelope**:

1. **The driver writes the brief** — exact files, signatures, test cases,
   constraints. A vague brief to codex wastes the savings in fix rounds.
2. **The driver reviews the diff** and **runs the gates** (tsc / tests / build)
   before anything is committed. Never trust a "tests pass" claim — re-run them.
   This holds for Opus-subagent output too.
3. **The driver owns git** — commits, merges, branch hygiene. (Codex has
   auto-opened PRs / committed unprompted before — rein it in; git stays with
   the driver.)
4. **One writer per branch at a time.** Never run two writers — an Opus subagent
   and/or a codex task — against the same working tree concurrently; they collide
   (it has caused git collisions). Serialize them, or give each its own
   sub-worktree.

The split is about *who drafts the code*, not about skipping review. Quality bar
is identical across both engines.

## CLI / invoke quick-reference

**Codex (GPT-5.5) — the companion runtime** (OpenAI's `codex` plugin for Claude
Code, installed as `codex@openai-codex`):
```
COMPANION=$(ls -d ~/.claude/plugins/cache/openai-codex/codex/*/scripts/codex-companion.mjs | tail -1)
cd <repo> && node "$COMPANION" task --background --write --effort xhigh "<full task brief>"
```
- **The driver calls the script directly** — do NOT go through the
  `codex:codex-rescue` subagent (it's a Sonnet-powered forwarder that adds a hop
  and nothing else; Sonnet is retired here).
- `task --background` returns a **job id** immediately. Poll
  `node "$COMPANION" status <job-id>` and fetch `node "$COMPANION" result <job-id>`
  when it completes; `cancel <job-id>` kills a dead run. **Jobs are
  workspace-scoped — run status/result/cancel from the same cwd as the dispatch.**
- `--write` is required for build tasks (edits files); leave `--model` unset so
  the run inherits `~/.codex/config.toml` (gpt-5.5 + Fast mode — don't override,
  and if codex errors with `Unsupported service_tier`, flag it to Pete instead of
  silently downgrading).
- The runtime drives `codex app-server` over JSON-RPC — the old `codex exec`
  stdin-hang and `--skip-git-repo-check` startup traps don't apply through it.
- First line of the brief is the `[ship-dispatch: …]` tag (see "Tag and track
  every codex dispatch") — it becomes the job summary in `status`.
- `task --resume-last` continues the previous codex thread in this workspace
  (fix rounds on the same task).
- Edits the working tree directly → obey "one writer per branch."
- **Fallback** (plugin missing): `cd <repo> && codex exec -c
  model_reasoning_effort=xhigh "<brief>" < /dev/null` — the `< /dev/null` is
  mandatory (`codex exec` blocks reading a non-TTY stdin to EOF before doing
  anything; a held-open pipe hangs it at startup forever with no session and no
  error), and a cwd outside a git repo also needs `--skip-git-repo-check` or it
  dies at startup.

**Opus:**
```
Agent(model: opus, prompt: "<full task brief>")   // Claude Code
```
- Codex Desktop: use an Opus-capable subagent tool if one is exposed; otherwise keep
  the task on the driver and log the engine as `driver-no-opus` in the ledger.

## The metric — the ledger

Maintain `~/.claude/skills/router/ledger.md` — the **single canonical ledger**,
outside any repo or plugin directory (create it there if missing; never write a
ledger into the plugin's own directory — an installed plugin isn't writable state).
**After every delegated build task**, append a row and keep the rolling summary
current.

Row: `date | project | task (short) | task-type | engine | outcome | fix-rounds | note`

- **engine**: `codex` · `opus`
- **task-type**: `specific-coding` · `integration` · `mechanical`
- **outcome**: `clean` (passed review + gates first pass) · `fixed-N` (N
  review→fix cycles) · `escalated→opus` (codex couldn't, reassigned up) ·
  `abandoned`
- Headline metric: **first-pass-clean rate per engine and per task-type**, plus
  **escalation rate.**

**How to tune the split:** every so often (or when Pete asks), read the ledger:
- codex cleaning a task-type first-pass → send it *more* of that type.
- codex keeps getting `escalated→opus` on a type → keep that type on Opus and
  say so when reporting the mix.
- Report realized mix vs the current dial and per-engine hit-rates when
  summarizing a plan's execution.

The mix is Pete's dial; the ledger is the evidence; refine over time.

## When NOT to delegate (keep on the driver or Opus)

- Anything touching auth, secrets, money, migrations, or irreversible / outward-
  facing actions → Opus (or the driver directly).
- Anything where the spec is still fuzzy (clarify/plan first — that's not a build
  task yet).
- Tiny verbatim writes where the content is *already authored* in the brief
  (driver-inline is faster than spinning up any subagent).
- The final review of a branch, and all of git → the driver, always.
