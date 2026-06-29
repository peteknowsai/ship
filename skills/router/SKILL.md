---
name: router
description: Use ONLY when executing the build tasks of an implementation plan (the BUILD stage of /ship) — deciding, per task, whether the work goes to Opus or to GPT-5.5 (codex). Two engines, ~50/50, self-tuning via a ledger. Do NOT invoke for planning, design, review, merge, or normal work — that all stays Opus.
---

# router — split BUILD-stage coding across Opus / GPT-5.5

**Scope: the BUILD stage only.** Discover, plan, design, review, merge, and every
normal task stay on **Opus**, as usual — do not invoke router for them. Router
fires *only* when an Opus driver is dispatching the concrete build tasks of an
already-written implementation plan. Outside build, there is no routing decision.

Two engines, both **flat-rate** (no API metering):

- **Opus** — this harness, or an Opus subagent (`Agent(model: opus)`). On Claude Max.
- **GPT-5.5** — via `codex exec "<brief>"` (cwd = repo). On Pete's Codex plan.

The only metered constraint is the **Max quota**, and Opus draws on it. Codex is
off-Max entirely. So the routing job: hand GPT-5.5 the work it can do well, keep
Opus for the work that needs it, and **save Max without losing quality.**

**Auth caveat:** the savings only hold if `codex` uses its *subscription* login,
not an API key (an `OPENAI_API_KEY` in the env would silently bill per-call). On
first use each session, sanity-check codex is logged into Pete's plan.

## Prime directive: success over the mix

The 50/50 is a **starting hypothesis, not a quota.** You (the Opus driver) decide
each assignment — optimize for the work getting done *well* and for Max savings,
and **self-adjust freely** as the ledger shows what works. If a task wants the
other engine than the split suggests, follow the task and log why. Pete: *"you be
the thing that decides how things get delegated… self-adjust as needed, success
is what matters."*

## The two engines

| Engine | Invoke | Best at |
|--------|--------|---------|
| **Opus** | you directly, or `Agent(model: opus)` | Decisions, decomposition, cross-file integration, ambiguity, real risk, anything irreversible — and the build tasks where the spec is still a little open |
| **GPT-5.5** | `codex exec "<brief>"` (cwd = repo) | Fully-specified, self-contained coding: exact files, signatures, test cases, no open design questions. "Here's exactly what to build" → it builds it well — *when it actually has something to explore* (see latency note) |

Dial **thinking per task**: Opus effort to the task's difficulty; codex with
`-c model_reasoning_effort=<low|medium|high|xhigh>` to match (high/xhigh for the
gnarly ones, lower for simpler — but mind the latency note).

## Target mix (starting hypothesis, tuned by the ledger)

Across the build tasks of one plan, aim for roughly **Opus 50 / GPT-5.5 50.**

Assign by **fit first**, then glance at the running split and rebalance only the
borderline tasks. Never hand a judgment task to GPT-5.5 just to hit the number —
log the drift and why.

## The assignment heuristic

For each build task, ask in order:

1. **Needs Opus-grade judgment** — design still open, cross-file integration,
   real risk, irreversible, ambiguous? → **Opus.**
2. **Fully specified and self-contained** — exact files, signatures, test cases,
   no open design questions — *and there's real work for it to do* (not just a
   verbatim file write)? → **GPT-5.5 (codex).**
3. **Unsure, or borderline 2↔1?** → **up-tier to Opus.** A wrong diff costs more
   (review + fix + re-dispatch) than just using Opus. Down-tier only when confident.

### Latency note (hard-won — read before sending to codex)

`codex exec` buffers output and is **slow on deterministic writes**: for a fully-
specified file whose exact content is already known, Opus writing it inline beats
codex on wall-clock by minutes. **Reserve GPT-5.5 for tasks where it genuinely
*explores*** — figures out signatures, writes tests against real types, works
through a self-contained problem. For "type out this file I already wrote in the
brief," keep it on Opus-inline. If you do send a verbatim-heavy task to codex,
give it a longer timeout or lower the effort — `xhigh` has timed out before
writing a single file.

## The discipline (non-negotiable, both engines)

Whoever writes the code, **Opus owns the envelope**:

1. **Opus writes the brief** — exact files, signatures, test cases, constraints.
   A vague brief to GPT-5.5 wastes the savings in fix rounds.
2. **Opus reviews the diff** and **runs the gates** (tsc / tests / build) before
   anything is committed. Never trust a "tests pass" claim — re-run them.
3. **Opus owns git** — commits, merges, branch hygiene. (Codex has auto-opened
   PRs / committed unprompted before — rein it in; git stays on Opus.)
4. **One writer per branch at a time.** Never run an Opus subagent and a codex
   task against the same working tree concurrently — they collide (it has caused
   git collisions). Serialize them, or give each its own sub-worktree.

The 50/50 is about *who drafts the code*, not about skipping review. Quality bar
is identical across both engines.

## CLI quick-reference

**Codex (GPT-5.5):**
```
cd <repo> && codex exec "<full task brief>"
```
- Non-interactive, edits files autonomously. `-c model_reasoning_effort=<level>`
  to dial thinking. `codex exec resume --last` to continue. If it needs write
  access beyond its sandbox, pass the appropriate `-c sandbox_*` / approval config.
- Runs in the repo cwd and edits the working tree directly → obey "one writer per
  branch."

## The metric — the ledger

Maintain `~/.claude/skills/router/ledger.md`. **After every delegated build
task**, append a row and keep the rolling summary current.

Row: `date | project | task (short) | task-type | engine | outcome | fix-rounds | note`

- **task-type**: `specific-coding` · `integration` · `mechanical` · (review/plan
  rows may appear from history but those stay Opus — router doesn't route them)
- **outcome**: `clean` (passed review + gates first pass) · `fixed-N` (N
  review→fix cycles) · `escalated→opus` (codex couldn't, reassigned up) · `abandoned`
- Headline metric: **first-pass-clean rate per engine and per task-type**, plus
  **escalation rate.**

**How to tune the split:** every so often (or when Pete asks), read the ledger:
- GPT-5.5 cleaning a task-type first-pass → send it *more* of that type.
- GPT-5.5 keeps getting `escalated→opus` on a type → stop sending that type there.
- Report realized mix vs the 50/50 target and per-engine hit-rates when
  summarizing a plan's execution.

The mix is a hypothesis; the ledger is the evidence; refine over time.

## When NOT to delegate to GPT-5.5 (keep on Opus)

- Anything touching auth, secrets, money, migrations, or irreversible / outward-
  facing actions.
- Anything where the spec is still fuzzy (clarify/plan first — that's not a build
  task yet).
- Verbatim file writes where the content is already authored (Opus-inline is faster).
- The final review of a branch, and all of git.
