---
name: router
description: Use ONLY when executing the build tasks of an implementation plan (the BUILD stage of /ship) — deciding, per task, whether the work goes to Opus, Sonnet 5 (xhigh), or GPT-5.5 (codex). Three engines, ~40 Opus / 40 GPT-5.5 / 20 Sonnet, self-tuning via a ledger. Do NOT invoke for planning, design, review, merge, or normal work — that all stays Opus.
---

# router — split BUILD-stage coding across Opus / Sonnet 5 / GPT-5.5

**Scope: the BUILD stage only.** Discover, plan, design, review, merge, and every
normal task stay on **Opus**, as usual — do not invoke router for them. Router
fires *only* when an Opus driver is dispatching the concrete build tasks of an
already-written implementation plan. Outside build, there is no routing decision.

Three engines:

- **Opus** — this harness, or an Opus subagent (`Agent(model: opus)`). On Claude Max.
- **Sonnet 5 (xhigh)** — a Sonnet subagent at extra-high effort (`Agent(model: sonnet)`).
  Also on Claude Max, but a **fraction of Opus's quota draw** — near-Opus on
  well-specified coding. The way to stay on Anthropic quality while saving Max.
- **GPT-5.5** — via `codex exec "<brief>"` (cwd = repo). On Pete's Codex plan,
  **off-Max entirely** — the only engine that doesn't touch the quota at all.

The metered constraint is the **Max quota**: Opus draws on it heavily, Sonnet
lightly, codex not at all. So the routing job: hand GPT-5.5 the self-contained work
it can explore well (free), use Sonnet for solid coding that wants Anthropic
quality without Opus's quota cost, and **keep Opus for the work that needs it —
saving Max without losing quality.**

**Auth caveat:** the codex savings only hold if `codex` uses its *subscription*
login, not an API key (an `OPENAI_API_KEY` in the env would silently bill
per-call). On first use each session, sanity-check codex is logged into Pete's plan.

## Prime directive: success over the mix

The 40/40/20 is a **starting hypothesis, not a quota.** You (the Opus driver)
decide each assignment — optimize for the work getting done *well* and for Max
savings, and **self-adjust freely** as the ledger shows what works. If a task
wants a different engine than the split suggests, follow the task and log why.
Pete: *"use your judgment and make sure you get the job done, that's what's
important"* — and *"you be the thing that decides how things get delegated…
self-adjust as needed, success is what matters."*

## The three engines

| Engine | Invoke | Best at |
|--------|--------|---------|
| **Opus** | you directly, or `Agent(model: opus)` | Decisions, decomposition, cross-file integration, ambiguity, real risk, anything irreversible — and the build tasks where the spec is still a little open |
| **Sonnet 5 (xhigh)** | `Agent(model: sonnet)` at xhigh effort | Solid, well-specified coding that wants Anthropic quality but **no Opus-grade judgment** — implement a clear component, write tests against known types, careful mechanical refactors, **and the deterministic/verbatim writes codex is too slow for**. Near-Opus on coding at a fraction of the Max draw — the default way to stretch Opus quota |
| **GPT-5.5** | `codex exec "<brief>"` (cwd = repo) | Fully-specified, self-contained coding: exact files, signatures, test cases, no open design questions. "Here's exactly what to build" → it builds it well — *when it actually has something to explore* (see latency note). The only fully off-Max engine |

Dial **thinking per task**: Opus effort to the task's difficulty; Sonnet at
**xhigh** (the coding sweet spot — don't drop it lower for build work); codex with
`-c model_reasoning_effort=<low|medium|high|xhigh>` to match (high/xhigh for the
gnarly ones, lower for simpler — but mind the latency note).

## Target mix (starting hypothesis, tuned by the ledger)

Across the build tasks of one plan, aim for roughly **Opus 40 / GPT-5.5 40 /
Sonnet 5 20.**

Assign by **fit first**, then glance at the running split and rebalance only the
borderline tasks. Never hand a judgment task to a lower tier just to hit the number
— log the drift and why. When torn between **Opus and Sonnet** for solid,
well-specified coding, lean **Sonnet** — that's the bucket that used to default to
Opus, and moving it down is how the quota saving actually happens.

## The assignment heuristic

For each build task, ask in order:

1. **Needs Opus-grade judgment** — design still open, cross-file integration,
   real risk, irreversible, ambiguous? → **Opus.**
2. **Fully specified and self-contained, with real work to explore** — exact
   files, signatures, test cases, no open design questions, *and there's genuine
   exploration for it to do* (not just a verbatim file write)? → **GPT-5.5
   (codex)** — it's free, off-Max, and good at this.
3. **Solid, well-specified coding that wants Anthropic reliability** — a clear
   component, tests against known types, a careful refactor — *or* a
   deterministic/verbatim-heavy write where codex's latency hurts? → **Sonnet 5
   (xhigh).** This is the bucket that used to default to Opus; move it to Sonnet
   to save the quota while staying on Anthropic quality.
4. **Unsure, or borderline?** → **up-tier** (codex→Sonnet, Sonnet→Opus). A wrong
   diff costs more (review + fix + re-dispatch) than the quota you'd save.
   Down-tier only when confident.

### Latency note (hard-won — read before sending to codex)

`codex exec` buffers output and is **slow on deterministic writes**: for a fully-
specified file whose exact content is already known, an Anthropic engine writing it
beats codex on wall-clock by minutes. **Reserve GPT-5.5 for tasks where it
genuinely *explores*** — figures out signatures, writes tests against real types,
works through a self-contained problem. For "type out this file I already
specified," send it to **Sonnet 5 (xhigh)**, not codex — same off-the-critical-path
saving without the buffered-write latency, and it keeps Opus quota free. (Opus-inline
only when the verbatim content is *already authored* in the brief and tiny.) If you
do send a verbatim-heavy task to codex anyway, give it a longer timeout or lower the
effort — `xhigh` has timed out before writing a single file.

## The discipline (non-negotiable, all engines)

Whoever writes the code, **Opus owns the envelope**:

1. **Opus writes the brief** — exact files, signatures, test cases, constraints.
   A vague brief to Sonnet or GPT-5.5 wastes the savings in fix rounds.
2. **Opus reviews the diff** and **runs the gates** (tsc / tests / build) before
   anything is committed. Never trust a "tests pass" claim — re-run them. This
   holds for Sonnet output too: subagent review is not a substitute for Opus
   re-running the gates.
3. **Opus owns git** — commits, merges, branch hygiene. (Codex has auto-opened
   PRs / committed unprompted before — rein it in; git stays on Opus.)
4. **One writer per branch at a time.** Never run two writers — an Opus subagent,
   a Sonnet subagent, and/or a codex task — against the same working tree
   concurrently; they collide (it has caused git collisions). Serialize them, or
   give each its own sub-worktree.

The split is about *who drafts the code*, not about skipping review. Quality bar
is identical across all three engines.

## CLI / invoke quick-reference

**Sonnet 5 (xhigh):**
```
Agent(model: sonnet, prompt: "<full task brief>")   // effort: xhigh
```
- Native Anthropic subagent — no sandbox/auth fragility, no codex git-collision
  risk. Still obey "one writer per branch."

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

- **engine**: `opus` · `sonnet` · `codex`
- **task-type**: `specific-coding` · `integration` · `mechanical` · (review/plan
  rows may appear from history but those stay Opus — router doesn't route them)
- **outcome**: `clean` (passed review + gates first pass) · `fixed-N` (N
  review→fix cycles) · `escalated→<engine>` (lower tier couldn't, reassigned up) ·
  `abandoned`
- Headline metric: **first-pass-clean rate per engine and per task-type**, plus
  **escalation rate.**

**How to tune the split:** every so often (or when Pete asks), read the ledger:
- An engine cleaning a task-type first-pass → send it *more* of that type.
- codex keeps getting `escalated` on a type → try **Sonnet** for it before falling
  all the way back to Opus.
- Sonnet keeps getting `escalated→opus` on a type → keep that type on Opus.
- Report realized mix vs the 40/40/20 target and per-engine hit-rates when
  summarizing a plan's execution.

The mix is a hypothesis; the ledger is the evidence; refine over time.

## When NOT to delegate below Opus (keep on Opus)

- Anything touching auth, secrets, money, migrations, or irreversible / outward-
  facing actions.
- Anything where the spec is still fuzzy (clarify/plan first — that's not a build
  task yet).
- Tiny verbatim writes where the content is *already authored* in the brief
  (Opus-inline is faster than spinning up any subagent).
- The final review of a branch, and all of git.
