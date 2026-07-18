---
name: router
description: Use ONLY when executing the build tasks of an implementation plan (the BUILD stage of /ship) — dispatching each task to GPT-5.6 sol via claudex (sol in the Claude Code harness; codex exec is the fallback) per Pete's current dial (see "Target mix" — currently 0/100, Opus is out of the BUILD rotation entirely; drafting is all sol, sub-overhead work inline on the driver). Do NOT invoke for planning, design, review, merge, or normal work — that all stays on the driver (the harness model). Never route to Sonnet.
---

# router — split BUILD-stage coding across Opus and GPT-5.6 sol

**Scope: the BUILD stage only.** Discover, plan, design, merge, and every normal
task stay on **the driver** — the harness model running the session (Fable) — as
usual; do not invoke router for them. Router fires *only* when the driver is
dispatching the concrete build tasks of an already-written implementation plan.
Outside build, there is no routing decision. (Ship's other codex offloads —
adversarial review in REVIEW, mechanical recon in DISCOVER — are wired directly
in the ship skill, not through router. The constant everywhere: **design,
planning, and the final say stay with Fable**; codex is inference muscle.)

Two engines:

- **GPT-5.6 sol** — via **`claudex -p … --effort xhigh` in the background** (Pete's
  call, 2026-07-16: sol drafts in the *Claude Code harness* through claudex —
  loopback CLIProxyAPI backed by Codex OAuth — because sol performs better in this
  harness than in Codex, and a claudex worker inherits Pete's CLAUDE.md, skills, and
  MCP natively; see the quick-reference). Billing rides the ChatGPT subscription
  through the proxy, and the wrapper unsets every Anthropic credential — a claudex
  worker *cannot* bill Anthropic API credits, so the "never `claude -p` for agent
  work" billing rule is satisfied by construction. **`codex exec` is the drafting
  fallback** when the proxy path is down (same model, same subscription; see the
  fallback block — there, **Fast mode stays OFF**, Pete 2026-07-13: Fast burned
  credits ~2.5× for ~1.5× speed). Off-Max entirely; xhigh stays the effort floor —
  save credits on the *tier*, never on thinking.
- **Opus** *(dormant at the current 0/100 dial — kept for when Pete swings it
  back)* — an Opus subagent: `Agent(model: opus)` in Claude Code; under Codex
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

**Auth caveat:** on first use each session, sanity-check the path with
`claudex-proxy status`. **A stopped proxy is NOT a fallback case** — the claudex
wrapper auto-starts it on every invocation (no launchd service exists, so after
a reboot "stopped" is the normal resting state; `claudex-proxy start` also works
by hand). Fall back to `codex exec` only when the path actually *fails*: the
start errors, the Codex OAuth credential is missing/expired, or `gpt-5.6-sol`
is absent from the proxy's `/v1/models`. On the fallback, the savings only hold
if `codex` uses its *subscription* login, not an API key (an `OPENAI_API_KEY`
in the env would silently bill per-call).

## Prime directive: success over the mix

The dial is a **target, not a quota.** You (the driver) decide each assignment —
optimize for the work getting done *well*, and **self-adjust freely** as the ledger
shows what works. If a task wants a different engine than the split suggests, follow
the task and log why. Pete: *"use your judgment and make sure you get the job done,
that's what's important."*

## The two engines

| Engine | Invoke | Best at |
|--------|--------|---------|
| **GPT-5.6 sol** | `claudex -p "<brief>" --effort xhigh --dangerously-skip-permissions` (cwd = repo worktree, background; fallback: `codex exec`, see quick-reference) | Fully-specified, self-contained coding with real work to explore: figure out signatures, write tests against real types, work through a well-briefed problem. "Here's exactly what to build" → it builds it well |
| **Opus** *(dormant at 0/100)* | `Agent(model: opus)` | Judgment and integration: design still open mid-task, cross-file integration, real risk, irreversible surfaces, ambiguity a brief can't close — at the current dial that work is the driver's, not Opus's |

**You (the driver) dial thinking per task — and default to MORE thinking, not
less.** sol workers: `xhigh` unless you have a reason to drop (credits are real but
thinking is the cheap part — the expensive mistake is a shallow wrong draft; spend
it). Opus subagents: `high` floor, `xhigh` for the gnarly ones; go lower only for
genuinely mechanical work. **Slow is fine — the answer to an engine taking a while
is a longer timeout, not less thinking or a different engine** (see the patience
note).

## Target mix  ← Pete's dial — edit here when he retunes it

**Current dial (2026-07-11): Opus 0 / GPT-5.6 sol 100 — Opus 4.8 is out of the
BUILD rotation entirely (Pete's call).** All drafting goes to GPT-5.6 sol; there
is no per-task engine choice, only dispatch-vs-inline (heuristic #4). A task that
would have wanted Opus-grade judgment doesn't get a different engine — it gets
a **tighter brief**: the driver closes the open design question itself, then
dispatches the fully-specified remainder; if the judgment can't be separated
from the writing, the driver does that task inline. **Fable has the final say
at any mix** — the driver owns design, planning, briefs, triage, and merge; the
dial only moves who drafts the code.

**Harness (2026-07-16, Pete's call): sol drafts through claudex** — the Claude
Code harness on the loopback proxy path — not through `codex exec`. Same model,
same ChatGPT-subscription billing; `codex exec` remains only as the drafting
fallback when the proxy path is down. Browser work (below) is unchanged — still
`codex exec` + Playwright.

**Browser work is codex's too (Pete, 2026-07-11):** verify walks, design QA,
and live-product grounding dispatch as background `codex exec` — codex scripts
its own Playwright and saves screenshots to disk. Auth-walled surfaces: codex
attaches to the dedicated logged-in **codex Chrome**
(`~/.codex/codex-chrome`, CDP :9222) via `connectOverCDP`. Opus's only
remaining pipeline job is claude-in-chrome against Pete's *personal* Chrome,
for logins that exist nowhere else.

## The assignment heuristic

For each build task, ask in order:

1. **Design still open, real risk, irreversible, ambiguous mid-flight?** → the
   **driver closes the judgment first** (decide the design, pick the shape,
   settle the ambiguity), then dispatches the now-fully-specified task to sol.
   Judgment inseparable from the writing → the driver does the task inline.
2. **Fully specified and self-contained, with real work to explore** — exact
   files, signatures, test cases, no open design questions? → **GPT-5.6 sol
   (claudex, xhigh).** At the current dial this is the default destination for
   everything.
3. *(dormant at 0/100)* When the dial has two engines, solid well-specified
   coding that fits either balances the split.
4. **Smaller than the dispatch overhead?** → the **driver writes it inline**.
   A dispatch costs ~5–10 min of fixed overhead (brief, launch, poll, read
   result) — a verbatim write already authored in the brief, a rename, a config
   line, wiring a triaged review fix all finish faster on the driver than the
   overhead alone (Pete's amendment to conserve-Fable, 2026-07-06). Anything
   with real exploration or multi-file work still dispatches.
5. **The sol worker produced a *wrong* diff twice on a task?** → escalate to
   **the driver** — Fable rewrites the task inline (at 0/100 there is no Opus
   bench; a third sol round costs more than it saves), log `escalated→driver`.
   **Slow is not failure** — never escalate (or kill a run) because a worker is
   taking a while.
6. **Agent-skill / craft prose AND frontend design — never routed.** SKILL.md
   files, reference/verb docs, agent-voiced distillations are **driver-authored**
   (Fable), not sent to codex or Opus (Pete's dial, 2026-07-02) — the voice and
   judgment *are* the deliverable. Same for **frontend design** (Pete's call,
   2026-07-18, reversing 2026-07-16): HTML design specs, mockups, visual/UI
   work, styling — anywhere taste is the deliverable — Fable authors inline.
   Frontend *mechanics* with the design already closed (wiring a spec'd
   component, plumbing per an approved design) route to sol like any other
   closed-brief task.

### Patience note (hard-won — read before dispatching sol)

A sol worker — claudex or codex — can sit quiet for many minutes at xhigh — past
runs were killed at a 2-minute timeout before a single file was written, and those
got mislogged as failures. They weren't; they were impatience. **We have time:
dispatch in the background and give it a generous window — think 15–30 minutes,
not 2 — checking in on it rather than killing it.** Don't drop effort to make it
faster; xhigh + patience is the deal. The one true exception: **work smaller than
the dispatch overhead** — that's not a dispatch task at any speed, the driver
writes it inline (heuristic #4).

### Tag and track every dispatch

Pete runs concurrent sessions dispatching workers at once — untagged and
untracked, a hung run sits unnoticed until someone wonders why a task never
landed (it has happened). So:

- **Tag:** the first line of every brief is
  `[ship-dispatch: <project> · <branch> · <task-slug>]` (append `-retryN` on
  redispatch). The brief rides in argv (`claudex -p "<brief>"` and
  `codex exec "<brief>"` alike), so the tag shows in `ps aux | grep -E
  'claudex|codex exec'` — any session, and Pete, can attribute every run at a
  glance. Tell the worker in the brief that the tag line is routing metadata to
  ignore.
- **Track:** dispatch with the harness's `run_in_background` (it notifies on
  exit) and check in at intervals. **Startup liveness tells:** a healthy claudex
  run creates its session transcript under `~/.claude/projects/` within seconds
  (and `claudex-proxy logs` shows traffic); a healthy `codex exec` creates its
  `~/.codex/sessions` rollout file within seconds. Process alive with neither
  after ~2 min = dead at startup (stdin held open, bad flag, proxy down), kill
  and redispatch — this is distinct from "slow is fine", which applies only
  after the session exists. **Every dispatch carries a stall budget: ~15 minutes
  of silence → an active look** (is the process in `ps`? has the result file or
  the run's working tree moved?) — never more passive waiting. Patience
  (15–30 min) is for **live** runs — the process exists and its output or the
  working tree is moving; a live run that's just slow gets left alone. A run
  that exited without a result, or a stall-budget check finding zero output and
  zero file writes, is not a patience case: kill the process chain, resume the
  specific session if it left one (claudex: `claudex -p --resume <session-id>
  "<follow-up>"`; codex: `codex exec resume <session-id>`), else redispatch
  with `-retry1`, and log the row honestly (`abandoned` or `fixed-N`, note
  "hung"). The stall budget converts "stuck forever" into "lost 15 minutes."

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

**Claudex (GPT-5.6 sol in the Claude Code harness) — the default drafting dispatch:**
```
cd <worktree> && claudex -p "<full task brief>" --effort xhigh \
  --dangerously-skip-permissions > <result-file> 2> <result-file>.err
```
launched in the background — in Claude Code the Bash tool's `run_in_background`
(it notifies on exit). Never a hand-rolled `&`.
- The wrapper auto-starts the loopback proxy, pins `--model gpt-5.6-sol`, routes
  via `ANTHROPIC_BASE_URL` to CLIProxyAPI (Codex OAuth = ChatGPT subscription),
  and **unsets `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` / `CLAUDE_CODE_OAUTH_TOKEN`**
  — a claudex worker cannot bill Anthropic credits or an OpenAI API key.
- **`> <result-file>` on every dispatch** (e.g. `/tmp/ship-<task-slug>-result.md`)
  — `-p` prints the final message to stdout; capture it so the result survives a
  truncated shell buffer. Read the file, not the scrollback. **Keep stderr in
  its own `.err` file, never `2>&1`** — the wrapper writes proxy-health and
  connector warnings to stderr, and merged into stdout they sit ahead of the
  result and break `--output-format json` parsing (the session id extraction).
- **`--dangerously-skip-permissions` is the worker's autonomy envelope** — legal
  because the worker runs in ship's isolated worktree and the driver reviews the
  diff and re-runs the gates afterward (the same trust shape `codex exec`
  full-auto had). Never hand it a shared checkout.
- First line of the brief is the `[ship-dispatch: …]` tag (see "Tag and track").
- The worker inherits Pete's global CLAUDE.md, the repo's CLAUDE.md, and the
  installed skills — brief it like a teammate on these rails, not like codex
  (no need to restate house rules the harness already loads).
- Fix rounds: capture the session id (`--output-format json` emits it) and
  resume that specific session: `claudex -p --resume <session-id> "<follow-up>"`.
  Never resume "the last session" — concurrent dispatches make that a lottery.
- Edits the working tree directly → obey "one writer per branch."
- **Fallback:** claudex missing, the proxy *fails to auto-start* (a merely
  stopped proxy is not failure — the wrapper starts it), or `gpt-5.6-sol`
  absent from the proxy's `/v1/models` → dispatch that task via `codex exec`
  below and log `fallback→codex` in the ledger note. Never stall a build on
  proxy repair.
- **Failure and fallback are never silent (Pete's call, 2026-07-16).** The
  ledger note is the record, not the alert: the moment a dispatch falls back
  to codex or a claudex run dies (proxy failure, auth expiry, hung worker),
  say so in the turn's narration as it happens (`⚠ claudex down — <reason>,
  task dispatched via codex exec`) AND carry it in the run's closing
  `result:` line (`· fallback→codex ×N: <reason>` / `· claudex failed:
  <reason>`). Pete finds out the proxy path broke from the session line, on
  the turn it broke — never by discovering it in the ledger later.

**Codex fallback (GPT-5.6 sol via `codex exec`) — drafting fallback only; still
the standing engine for review mode and browser work (wired in the ship skill):**
```
cd <repo> && codex exec -c model_reasoning_effort=xhigh -o <result-file> "<full task brief>" < /dev/null
```
launched in the background — in Claude Code the Bash tool's `run_in_background`
(it notifies on exit); under Codex Desktop a long-lived shell session you poll.
Never a hand-rolled `&`.
- **`-o <result-file>` on every dispatch** (e.g. `/tmp/ship-<task-slug>-result.md`) —
  it writes the agent's final message to a file, so the result survives even if
  the shell buffer is truncated or the watcher misses the exit. Read the file,
  not the scrollback.
- **`< /dev/null` is mandatory.** When stdin isn't a TTY, `codex exec` blocks
  reading stdin to EOF *before doing anything* — a held-open pipe hangs the run
  at startup forever, with no session file and no error (this ate a night of
  dispatches once and got misblamed on fast mode/xhigh).
- **cwd outside a git repo → add `--skip-git-repo-check`**, or codex exits
  fatally at startup ("Not inside a trusted directory").
- **Always the sol variant.** GPT-5.6 in this pipeline means `gpt-5.6-sol`,
  never plain `gpt-5.6` or another variant (Pete's call, 2026-07-11). If a
  dispatch ever needs the model set explicitly, it's `-m gpt-5.6-sol`.
- Leave the model unset so the run inherits `~/.codex/config.toml` (gpt-5.6-sol,
  standard tier — Fast mode is OFF to conserve credits; don't override either).
- First line of the brief is the `[ship-dispatch: …]` tag (see "Tag and track
  every dispatch") so the run is attributable in `ps`.
- Fix rounds: resume the *specific* session — capture the session id codex
  prints, then `codex exec resume <session-id> "<follow-up>"`. **Never
  `resume --last`** — with concurrent sessions dispatching codex, "--last" is
  whichever run finished most recently anywhere on the machine, not your task.
- Edits the working tree directly → obey "one writer per branch."
- **Reviews use codex's native review mode, not a hand-rolled brief:**
  `codex exec review --base <branch> -o <result-file> < /dev/null`
  (or `--uncommitted` / `--commit <sha>`). **No positional prompt** — codex
  errors ("cannot be used with [PROMPT]") when a prompt is combined with any
  diff-source flag; review mode applies its own rubric. No prompt also means
  no ship-dispatch tag — name the `-o` result file after the feature slug so
  the run is attributable in `ps`. Review mode is read-only by
  construction and computes the diff itself — "edit nothing" enforced by the
  tool, not by prompt convention.
- **Do NOT use the codex-companion runtime (`codex` plugin's
  `codex-companion.mjs task/status/result`) for background work.** Its jobs
  depend on a per-worktree broker daemon that the plugin's SessionEnd hook
  tears down — in Pete's multi-session, restart-heavy workflow the broker dies
  mid-run and the job sits "running" forever, orphaned (it killed a 25-minute
  review). Companion is acceptable only for short *foreground* calls you'll
  outlive; `codex exec` is the path for everything dispatched. Never go through
  the `codex:codex-rescue` subagent either (Sonnet forwarder; Sonnet is
  retired).

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

- **engine**: `claudex` · `codex` (fallback) · `opus`
- **task-type**: `specific-coding` · `integration` · `mechanical`
- **outcome**: `clean` (passed review + gates first pass) · `fixed-N` (N
  review→fix cycles) · `escalated→driver` (the sol worker couldn't; the driver
  rewrote inline) · `abandoned`
- Headline metric: **first-pass-clean rate per engine and per task-type**, plus
  **escalation rate.**

**How to tune the split:** every so often (or when Pete asks), read the ledger:
- an engine cleaning a task-type first-pass → send it *more* of that type.
- a task-type that keeps getting `escalated→driver` → keep that type on the
  driver and say so when reporting the mix.
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
