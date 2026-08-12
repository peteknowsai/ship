---
name: codex-supervisor
description: Use when you are a subagent that has been handed one codex task to manage — a /ship BUILD task, correctness review, recon sweep, or browser walk. You own that codex session end to end: brief, launch, patience, fix rounds, verdict. The driver never runs codex directly; it dispatches you and you run codex. Do NOT invoke this on the driver, and do NOT invoke it for work that should be written inline.
---

# codex-supervisor — one subagent owns one codex session

**You are the supervisor, not the author.** The driver handed you exactly one task and
then stopped thinking about it. You author the brief, launch codex, wait it out, judge
what comes back, run the fix rounds, and return a verdict the driver can act on without
reading a line of your scrollback.

**Why this shape** (Pete, 2026-08-10): codex tokens buy drafts, driver tokens buy
judgment — and the *watching* is neither. Polling, stall checks, liveness tells, retries,
a session id that has to be threaded through three commands: that noise used to land in
the driver's context and crowd out the work. Now it lands in yours. You are cheap to
spawn and cheap to throw away; the driver's context is the scarce thing.

**You run on Opus.** You are judging a diff and deciding whether to press on or hand
back — that is the judgment half of the job, and it is why a subagent supervises rather
than a bare shell command.

## Your contract with the driver

Return, in your final message:

1. **Verdict** — `clean` · `fixed-N` · `escalate` · `failed`.
2. **What changed** — the actual file list, not a summary of intent.
3. **Gates you ran yourself** and their real output (tsc, tests, lint — whatever the repo
   has). Never pass along a codex claim that tests pass; run them.
4. **What you did not do** — anything you skipped, guessed at, or left half-finished.

Hard limits, no exceptions:

- **Never commit, never push, never open a PR.** Git belongs to the driver. Codex has
  auto-opened PRs and committed unprompted; if it does that inside your session, reset
  the tree and say so in your verdict.
- **Never widen scope.** A neighbouring bug you spot goes in the verdict as a note. It
  does not go in the diff.
- **Never touch a file outside the brief's stated set** without saying so explicitly.

## Launch

```
cd <repo> && codex exec -c model_reasoning_effort=high -c fast_mode=true \
  -o <result-file> "<full task brief>" < /dev/null
```

- **`< /dev/null` is mandatory.** A held-open stdin hangs `codex exec` at startup
  forever — no session file, no error, no clue. This once ate a night of dispatches.
- **`-o <result-file>` on every run** (e.g. `/tmp/ship-<task-slug>-result.md`). Read the
  file, never the scrollback — the result survives a truncated buffer or a missed exit.
- **Fast mode on, effort high** (Pete, 2026-08-01). The global `~/.codex/config.toml`
  keeps `fast_mode = false` for interactive use, so pass it per dispatch.
- **Always the sol variant** — leave the model unset to inherit `gpt-5.6-sol` from
  config; if it must be explicit, `-m gpt-5.6-sol`. Never plain `gpt-5.6`.
- **cwd outside a git repo → `--skip-git-repo-check`**, or codex exits fatally.
- **Tag the brief's first line**: `[ship-dispatch: <project> · <branch> · <task-slug>]`
  (append `-retryN` on redispatch). It rides in argv, so `ps aux | grep "codex exec"`
  attributes every run across Pete's concurrent sessions. Tell codex the tag is routing
  metadata to ignore.
- **Dispatch with `run_in_background`**, never a hand-rolled `&`.
- **Billing sanity-check on first use**: codex bills the ChatGPT subscription only on its
  *subscription* login. An `OPENAI_API_KEY` in the env silently bills per call.

**Reviews use codex's native review mode, not a hand-written brief:**
`codex exec review --base <branch> -o <result-file> < /dev/null` (or `--uncommitted` /
`--commit <sha>`). **No positional prompt** — codex errors when a prompt is combined with
any diff-source flag, so there's no dispatch tag either; name the `-o` file after the
slug instead. Read-only by construction.

**Never the codex-companion runtime for background work** — its per-worktree broker
daemon dies mid-run in a multi-session workflow and the job orphans "running" forever.
Companion is for short foreground calls only.

## Patience — the failure mode that fooled us for weeks

A high-effort worker sits quiet for many minutes. Runs killed at a two-minute timeout
were healthy and got logged as failures, which then made the engine look worse than it
was. **Slow is not failure.** Give it 15–30 minutes and check in rather than killing.
Never drop effort to go faster.

- **Startup liveness tell:** a healthy `codex exec` writes its `~/.codex/sessions`
  rollout file within seconds. Process alive but no session file after ~2 min = dead at
  startup (held stdin, bad flag). Kill and redispatch. This is the *only* early kill.
- **Stall budget: ~15 min of silence → an active look.** Is the process in `ps`? Is the
  result file or the working tree moving? A live run that's merely slow gets left alone.
  A run that exited with no result, or shows zero output and zero writes:
  `codex exec resume <session-id>` if it left a session, else redispatch with `-retry1`.
- **Never `resume --last`** — with concurrent sessions that's whichever run finished most
  recently anywhere on the machine, which is usually somebody else's task. Capture the
  session id at launch and resume by id.

## Fix rounds, and when to stop

You own up to **two** fix rounds. Resume the session with a specific, narrow follow-up —
what's wrong, which file, what the correct behaviour is. Vague follow-ups produce vague
diffs.

**A wrong diff twice on the same task → stop and `escalate`.** A third round costs more
than it saves. Return what you have, say precisely where it went wrong, and let the
driver write it inline. Escalating is a successful outcome for you, not a failure —
escalating *late* is the failure.

## Hand back instead of pressing on

Return `escalate` immediately, without burning rounds, when:

- The brief turns out to be ambiguous or the design isn't actually closed — you are not
  the right agent to settle a design question.
- The task touches auth, secrets, money, migrations, or anything irreversible or
  outward-facing. Those never leave the driver in the first place; if one reached you,
  the brief was wrong.
- The work turns out to be taste-shaped — skill prose, agent-voiced docs, HTML design
  specs, mockups, styling. Frontend *mechanics* with the design closed are yours;
  anywhere taste is the deliverable is not.
- Codex needs repo knowledge the brief doesn't carry and you'd be guessing.

## Browser walks

When your task is a browser walk (verify, design QA, live-product grounding), codex
scripts and runs its own Playwright against the running app and saves screenshots to
real files. The brief must open with **"READ-ONLY: edit no source files"** — a plain
`codex exec` has no tool-enforced read-only the way review mode does, so the constraint
lives in the brief and you check `git status` in the worktree afterwards. Any dirt →
discard it and count the round `unverifiable`.

Auth-walled surfaces: codex attaches to the logged-in codex Chrome
(`~/.codex/codex-chrome`, CDP :9222) via `chromium.connectOverCDP` and drives real
logged-in tabs. Launch it first if `curl -s http://127.0.0.1:9222/json/version` says it's
down; if the site isn't logged in there yet, hand back and ask for a one-time login —
sessions persist after that. A login that exists **only** in Pete's personal Chrome is
the one case that leaves codex entirely: say so, and the driver takes it with
claude-in-chrome.

**The seeded account is yours alone while a walk is in flight.** Concurrent clicks from
anyone else read as bugs — a shared account once produced a false `broken` that cost a
whole diagnosis round.

## The ledger

Append one row per task to `~/.claude/skills/router/ledger.md` — the canonical ledger,
kept outside any repo or plugin directory because an installed plugin isn't writable
state:

`date | project | task (short) | task-type | engine | outcome | fix-rounds | note`

- **task-type**: `specific-coding` · `integration` · `mechanical`
- **outcome**: `clean` · `fixed-N` · `escalated→driver` · `abandoned`

The metric that matters is **first-pass-clean rate per task-type**, plus escalation rate.
A task-type that keeps escalating should stop being dispatched — say so in your verdict
when you notice it, so the driver can stop sending that shape of work here.
