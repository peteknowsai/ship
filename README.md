# ship

A Claude Code plugin: **`/ship`** takes a feature from **idea to merged in one command** — `worktree → discover → plan → build → review` — gating only on the two decisions that are actually yours: **locking the storyboard**, and **"go"** on the plan. Everything in between is automatic.

It's opinionated. Built for a hands-off, PM-style workflow: you stay in your lane (product, design, taste, scope); the machine handles the mechanics and only stops at the two gates.

## What it does

- **Two gates, only two.** Lock the storyboard (after discovery), then "go" on the plan (after planning). Everything else runs without you.
- **Sized to the ask.** Three lanes, ship picks: **express** (quick fix — no spec/plan, straight through to dev), **self-directed** (writes its own spec + plan, builds, reviews, merges — zero stops), **gated** (the two gates, when your taste is in play). Same worktree → merge → dev rails in all three; gates fire only when your answer would change what gets built.
- **You read the meta, never the diff.** Every checkpoint auto-opens an HTML page in your browser — a **storyboard** (live mockups of the app, not a document), a one-screen **plan card**, and a **review card** at merge. Never "go read the PR."
- **Gate notifications.** When a ship parks at a gate, a desktop notification taps you on the shoulder (Ghostty-native, with a macOS fallback) — so you can walk away.
- **Stage-aware status line.** Which ship, what phase (`designing → planning → building → reviewing`), ships-in-flight, your context + weekly budget, effort level. A bold banner when a ship needs you.
- **BUILD supervised, not shelled out.** Each closed-brief build task goes to an Opus subagent that owns one codex session end to end — brief, launch, patience, fix rounds, verdict — while the driver owns the plan, the diff review, the gates, and git. Orchestration stays inside Claude Code; codex still does the drafting.
- **Fresh-agent verification.** REVIEW invokes the bundled `verify` skill before the card so the running app is driven and judged before merge.

## What's in the plugin

- `skills/ship` — the pipeline playbook + the storyboard / plan-card / review-card templates + the design record.
- `skills/verify` — fresh read-only verification against the running app before merge.
- `hooks/` — the gate desktop-notification hook.
- `statusline.sh` — the stage-aware status line.
- `.codex-plugin/plugin.json` — the Codex Desktop manifest (see below).

## Requires

Declared as plugin `dependencies` (Claude Code will prompt/handle them): **superpowers**, **ponytail**, **worktrunk** (`wt`). Optional but recommended: **impeccable** (the craft floor) and the **image-gen** skill (imagery inside a frame) for the discovery stage — without them, the storyboard is drawn from the product's stylesheet alone, still fine.

## Your standing stack stays personal

`/ship` reads your **standing stack** (your default frameworks — never re-asked) from your own agent instructions, *not* from this plugin. In Claude Code that's usually `~/.claude/CLAUDE.md`; in Codex it's AGENTS.md/global instructions. A repo's own `CLAUDE.md` / `AGENTS.md` overrides it. The plugin is the *process*; your stack is *you*.

## Install

```
/plugin marketplace add peteknowsai/ship
/plugin install ship@ship
```

If you want the bundled status line, point your `statusLine` at it (or let the plugin's `statusLine` field wire it).

## Codex Desktop

The Codex package uses `codex/ship.md` and `codex/verify.md`. It keeps the shared
express, design, and next processes, but uses Astra subagents directly. It has no
supervisors or app-server dispatcher. Small changes stay with the driver; independent
build tasks and final reviews can run in parallel.

Build a portable package into a new directory:

```sh
python3 scripts/test-codex.py
python3 scripts/build-codex.py /tmp/ship-codex
```

The builder copies the current storyboard, plan-card, and review-card templates from
`plugins/ship`, adds the Codex instructions and manifest, and records the source commit
in `SOURCE.json`. Install the result as the personal marketplace's ship package.
Before replacing an existing local package or installed cache, back it up. Preserve
its registered manifest version for an in-place refresh. New tasks rediscover the
skills; an active task must explicitly reread them.

When the Claude pipeline changes, review the matching native process in `codex/`
and rerun the behavioral cases in [the sync notes](specs/2026-09-05-codex-ship.html).
The bundle shares templates, not Claude tool instructions. Do not copy supervisors
or Claude-only tools into the Codex package.
