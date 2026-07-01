# ship

A Claude Code plugin: **`/ship`** takes a feature from **idea to merged in one command** — `worktree → discover → plan → build → review` — gating only on the two decisions that are actually yours: **the design direction**, and **"go"**. Everything in between is automatic.

It's opinionated. Built for a hands-off, PM-style workflow: you stay in your lane (product, design, taste, scope); the machine handles the mechanics and only stops at the two gates.

## What it does

- **Two gates, only two.** Design direction (after discovery), then "go" (after planning). Everything else runs without you.
- **Sized to the ask.** Three lanes, ship picks: **express** (quick fix — no spec/plan, straight through to dev), **self-directed** (writes its own spec + plan, builds, reviews, merges — zero stops), **gated** (the two gates, when your taste is in play). Same worktree → merge → dev rails in all three; gates fire only when your answer would change what gets built.
- **You read the meta, never the diff.** Every checkpoint auto-opens a condensed HTML card in your browser — a design spec, a go-card, and a **review card** at merge. Never "go read the PR."
- **Gate notifications.** When a ship parks at a gate, a desktop notification taps you on the shoulder (Ghostty-native, with a macOS fallback) — so you can walk away.
- **Stage-aware status line.** Which ship, what phase (`designing → planning → building → reviewing`), ships-in-flight, your context + weekly budget, effort level. A bold banner when a ship needs you.
- **BUILD routed across models.** Each build task is routed via the bundled `router` skill — split across Opus and GPT-5.5 (codex) per a tunable mix — while the driving model owns the brief, review, gates, and git.
- **Fresh-agent verification.** REVIEW invokes the bundled `verify` skill before the card so the running app is driven and judged before merge.

## What's in the plugin

- `skills/ship` — the pipeline playbook + the go-card / review-card templates + the design record.
- `skills/router` — model delegation for the BUILD stage (bundled; BUILD-only).
- `skills/verify` — fresh read-only verification against the running app before merge.
- `hooks/` — the gate desktop-notification hook.
- `statusline.sh` — the stage-aware status line.
- `.codex-plugin/plugin.json` — the Codex Desktop manifest (see below).

## Requires

Declared as plugin `dependencies` (Claude Code will prompt/handle them): **superpowers**, **ponytail**, **worktrunk** (`wt`). Optional but recommended: **impeccable** (HTML design sprints) and **pix** (image generation) for the discovery stage — without them, discovery degrades to text + CSS, still fine.

## Your standing stack stays personal

`/ship` reads your **standing stack** (your default frameworks — never re-asked) from your own agent instructions, *not* from this plugin. In Claude Code that's usually `~/.claude/CLAUDE.md`; in Codex it's AGENTS.md/global instructions. A repo's own `CLAUDE.md` / `AGENTS.md` overrides it. The plugin is the *process*; your stack is *you*.

## Install

```
/plugin marketplace add peteknowsai/ship
/plugin install ship@ship
```

If you want the bundled status line, point your `statusLine` at it (or let the plugin's `statusLine` field wire it).

## Codex Desktop

Ship also runs under Codex Desktop — `.codex-plugin/plugin.json` is the manifest Codex reads. Same pipeline, same gates; the mechanics swap: Codex owns worktree birth/cleanup (no `wt` against Codex-managed worktrees), artifacts open in the in-app Browser (served over localhost), merges go through the PR path, and — with no status line or FleetView there — every status line carries a `branch <branch> · worktree <path>` breadcrumb. The full swap list lives in the ship skill under **"Running under Codex Desktop"**.
