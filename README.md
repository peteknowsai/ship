# ship

A Claude Code plugin: **`/ship`** takes a feature from **idea to merged in one command** — `worktree → discover → plan → build → review` — gating only on the two decisions that are actually yours: **the design direction**, and **"go"**. Everything in between is automatic.

It's opinionated. Built for a hands-off, PM-style workflow: you stay in your lane (product, design, taste, scope); the machine handles the mechanics and only stops at the two gates.

## What it does

- **Two gates, only two.** Design direction (after discovery), then "go" (after planning). Everything else runs without you.
- **You read the meta, never the diff.** Every checkpoint auto-opens a condensed HTML card in your browser — a design spec, a go-card, and a **review card** at merge. Never "go read the PR."
- **Gate notifications.** When a ship parks at a gate, a desktop notification taps you on the shoulder (Ghostty-native, with a macOS fallback) — so you can walk away.
- **Stage-aware status line.** Which ship, what phase (`designing → planning → building → reviewing`), ships-in-flight, your context + weekly budget, effort level. A bold banner when a ship needs you.
- **BUILD routed across models.** Each build task goes ~50/50 to Opus or GPT-5.5 (codex) via the bundled `router` skill — Opus owns the brief, review, gates, and git.

## What's in the plugin

- `skills/ship` — the pipeline playbook + the go-card / review-card templates + the design record.
- `skills/router` — model delegation for the BUILD stage (bundled; BUILD-only).
- `hooks/` — the gate desktop-notification hook.
- `statusline.sh` — the stage-aware status line.

## Requires

Declared as plugin `dependencies` (Claude Code will prompt/handle them): **superpowers**, **ponytail**, **worktrunk** (`wt`). Optional but recommended: **impeccable** (HTML design sprints) and **pix** (image generation) for the discovery stage — without them, discovery degrades to text + CSS, still fine.

## Your standing stack stays personal

`/ship` reads your **standing stack** (your default frameworks — never re-asked) from your own `~/.claude/CLAUDE.md`, *not* from this plugin. A repo's own `CLAUDE.md` overrides it. The plugin is the *process*; your stack is *you*.

## Install

```
/plugin marketplace add peteknowsai/ship
/plugin install ship@ship
```

If you want the bundled status line, point your `statusLine` at it (or let the plugin's `statusLine` field wire it).
