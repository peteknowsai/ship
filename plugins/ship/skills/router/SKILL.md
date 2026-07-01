---
name: router
description: Use ONLY when executing the build tasks of an implementation plan (the BUILD stage of /ship) — deciding, per task, whether the work goes to GPT-5.5 (codex, the default) or Opus. Two engines, ~95% GPT-5.5 / ~5% Opus, self-tuning via a ledger. Do NOT invoke for planning, design, review, merge, or normal work — that all stays on the driver (the harness model). Never route to Sonnet.
---

# router — send BUILD-stage coding to GPT-5.5 first, Opus sparingly

**Scope: the BUILD stage only.** Discover, plan, design, review, merge, and every
normal task stay on **the driver** — the harness model running the session (Fable) —
as usual; do not invoke router for them. Router fires *only* when the driver is
dispatching the concrete build tasks of an already-written implementation plan.
Outside build, there is no routing decision.

Two engines:

- **GPT-5.5** — via `codex exec "<brief>"` (cwd = repo), **default effort `xhigh`,
  Fast mode on** (`service_tier = "fast"` + `[features] fast_mode = true` in
  `~/.codex/config.toml` — global, every `codex exec` inherits it; ~1.5× faster for
  2.5× the credit burn, and Pete has chosen to spend it — never turn it off to save
  codex credits). On Pete's Codex plan: effectively **unlimited and off-Max
  entirely**. This is the default engine for build tasks.
- **Opus** — an Opus subagent (`Agent(model: opus)`). On Claude Max, where the
  **weekly Opus credits are the scarce resource** — spend them only where the task
  genuinely needs Opus-grade judgment.

**Never route to Sonnet** — Sonnet 5 is retired from this pipeline entirely (Pete's
call). If a task feels "Sonnet-shaped" (solid, well-specified coding), that's a
GPT-5.5 task now.

The constraint is the **Opus credit pool**: codex costs nothing against it, Opus
drains it. So the routing job: hand GPT-5.5 everything it can do well — which is
most of a well-briefed build — and **keep Opus for the minority of tasks where
judgment, cross-file integration, or risk truly demand it.**

**Auth caveat:** the codex savings only hold if `codex` uses its *subscription*
login, not an API key (an `OPENAI_API_KEY` in the env would silently bill
per-call). On first use each session, sanity-check codex is logged into Pete's plan.

## Prime directive: success over the mix

The 95/5 is a **floor on codex usage, not a straitjacket.** You (the driver)
decide each assignment — optimize for the work getting done *well* and for Opus
credits surviving the week, and **self-adjust freely** as the ledger shows what
works. If a task wants a different engine than the split suggests, follow the task
and log why. Pete: *"use your judgment and make sure you get the job done, that's
what's important."*

## The two engines

| Engine | Invoke | Best at |
|--------|--------|---------|
| **GPT-5.5** | `codex exec "<brief>"` (cwd = repo), `-c model_reasoning_effort=xhigh`, Fast mode on by default | **The default for build tasks — nearly all of them.** Well-briefed coding of every stripe: implement a component, write tests against known types, careful refactors, self-contained problems with real exploration. Unlimited, off-Max — when in doubt and the brief is solid, send it here |
| **Opus** | `Agent(model: opus)` | The rare exception (~5% — a task or two per plan, often zero): design still open mid-task, gnarly cross-file integration, real risk, irreversible surfaces, ambiguity a brief can't close — the tasks where a wrong diff is expensive |

Dial **codex thinking per task**: `xhigh` is the default (usage is unlimited — spend
it), and **slow is fine — the answer to codex taking a while is a longer timeout,
not less thinking or a different engine** (see the latency note). Opus subagents get
effort matched to the task's difficulty.

## Target mix

Across the build tasks of one plan: **GPT-5.5 ~95 / Opus ~5.**

Assign by **fit first**, but the prior is strong: codex is the default for
*everything*, and each Opus assignment is an exception you justify in the ledger —
expect a task or two per plan at most, often zero. When torn, lean **GPT-5.5 with a
tighter brief** — a better brief is cheaper than an Opus credit. Never hand a genuine
judgment task to codex just to protect the number — log the drift and why.

## The assignment heuristic

For each build task, ask in order:

1. **Can a tight brief close every open question?** If you can write exact files,
   signatures, test cases, and constraints → **GPT-5.5 (codex, xhigh).** This
   should be ~95% of tasks — nearly every build task from a good plan is briefable.
2. **Judgment can't be briefed away** — design still open, gnarly cross-file
   integration, real risk, irreversible, ambiguous mid-flight? → **Opus.**
3. **Tiny verbatim write, content already authored in the brief?** → the **driver
   writes it inline** — faster than spinning up any subagent or waiting on codex.
4. **codex produced a *wrong* diff twice on a task?** → escalate to **Opus**, log
   `escalated→opus`. A third fix round costs more than the credit. **Slow is not
   failure** — never escalate (or kill a run) because codex is taking a while.

### Patience note (hard-won — read before sending to codex)

`codex exec` buffers output and can sit silent for many minutes at xhigh — past
runs were killed at a 2-minute timeout before codex had written a single file, and
those got mislogged as failures. They weren't; they were impatience. **We have
time: run codex in the background (`run_in_background`) with a generous window —
think 15–30 minutes, not 2 — and check in on it rather than killing it.** Don't
drop effort to make it faster; xhigh + patience is the deal. The one true
exception: a **tiny verbatim write whose exact content is already in the brief** —
that's not a codex task at any speed, the driver writes it inline (heuristic #3).

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

**Codex (GPT-5.5):**
```
cd <repo> && codex exec -c model_reasoning_effort=xhigh "<full task brief>"
```
- Non-interactive, edits files autonomously. `codex exec resume --last` to
  continue. If it needs write access beyond its sandbox, pass the appropriate
  `-c sandbox_*` / approval config.
- Fast mode rides along from `~/.codex/config.toml` (`service_tier = "fast"`,
  `[features] fast_mode = true`) — don't override it, and if codex ever errors with
  `Unsupported service_tier`, flag it to Pete instead of silently downgrading.
- Launch long tasks in the background with a 15–30 min window — never kill a run
  for slowness alone (see the patience note).
- Runs in the repo cwd and edits the working tree directly → obey "one writer per
  branch."

**Opus:**
```
Agent(model: opus, prompt: "<full task brief>")
```

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
- Report realized mix vs the 95/5 target and per-engine hit-rates when
  summarizing a plan's execution.

The mix is a floor on codex; the ledger is the evidence; refine over time.

## When NOT to delegate (keep on the driver or Opus)

- Anything touching auth, secrets, money, migrations, or irreversible / outward-
  facing actions → Opus (or the driver directly).
- Anything where the spec is still fuzzy (clarify/plan first — that's not a build
  task yet).
- Tiny verbatim writes where the content is *already authored* in the brief
  (driver-inline is faster than spinning up any subagent).
- The final review of a branch, and all of git → the driver, always.
