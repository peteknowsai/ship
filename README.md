# ship

A Claude Code plugin: **`/ship`** takes a feature from **idea to merged in one command** — `worktree → discover → plan → build → review` — gating only on the two decisions that are actually yours: **locking the storyboard**, and **"go"** on the plan. Everything in between is automatic.

It's opinionated. Built for a hands-off, PM-style workflow: you stay in your lane (product, design, taste, scope); the machine handles the mechanics and only stops at the two gates.

## What it does

- **Two gates, only two.** Lock the storyboard (after discovery), then "go" on the plan (after planning). Everything else runs without you.
- **Sized to the ask.** Three lanes, ship picks: **express** (quick fix — no spec/plan, straight through to dev), **self-directed** (writes its own spec + plan, builds, reviews, merges — zero stops), **gated** (the two gates, when your taste is in play). Same worktree → merge → dev rails in all three; gates fire only when your answer would change what gets built.
- **You read the meta, never the diff.** Every checkpoint puts an HTML page in a background Chrome tab, never taking the screen — a **storyboard** (an artboard board of every screen and state, live mockups, not a document), a one-screen **plan card**, and a **review card** at merge or when a ship parks. Never "go read the PR."
- **Gate notifications.** When a ship parks at a gate, a desktop notification taps you on the shoulder (Ghostty-native, with a macOS fallback) — so you can walk away.
- **Stage-aware status line.** Which ship, what phase (`designing → planning → building → reviewing`), ships-in-flight, your context + weekly budget, effort level. A bold banner when a ship needs you.
- **Opus 5.5 drives; each build task goes to the engine its difficulty earns.** `scripts/route.py` asks Jev, TypeSafe's classifier, to score every task in the plan and ranks them: the easier half goes to a Fable 5.1 subagent and the harder half to Opus 5.5. That split is an experiment the ledger will judge. Fable also reviews the plan before BUILD and the whole branch in REVIEW, and GPT-6.1 Sol reads the branch beside it, the one check from outside Claude's family; the ledger tallies which reader's findings were real. The driver owns the brief, the diff review, the gates, and git, and logs every task's outcome to a ledger (`route.py report`) so the split can be tuned on data.
- **Ship tests it as Pete would, and a pass lands it.** TEST invokes the bundled `verify` skill: the session writes a QA script and runs it itself, in a browser through chrome-devtools and on iOS through agent-device (Pete's iPhone, or an Xcode simulator), fixes what fails and reruns, and its `works` lands the branch without waiting on Pete. Codex tests only when Pete asks (`verify/reference/codex.md`: a hand-off to his Codex app through `scripts/codex-handoff.py`, or the headless `astra.sh test`). Money paths, and changes Pete asked to try himself, still wait for his "merge main".

## What's in the plugin

- `skills/ship` — the pipeline playbook + the storyboard / plan-card / review-card templates + the design record.
- `skills/verify` — fresh read-only verification against the running app before merge.
- `hooks/` — the gate desktop-notification hook.
- `statusline.sh` — the stage-aware status line, with Anthropic and Codex quota.
- `.codex-plugin/plugin.json` — the Codex Desktop manifest (see below).

## Requires

Declared as plugin `dependencies` (Claude Code will prompt/handle them): **superpowers**, **ponytail**, **worktrunk** (`wt`), and **mattpocock-skills** (`pr` for the PR body and its merge-danger call, `diagnosing-bugs` for a finding that comes back, `writing-for-agents` for briefs; install it from Matt's own marketplace, `claude plugin marketplace add mattpocock/skills`, since the official one lags). Optional but recommended: **impeccable** (the craft floor, and its detector in BUILD's pre-flight) and the **image-gen** skill (imagery inside a frame) for the discovery stage — without them, the storyboard is drawn from the product's stylesheet alone, still fine.

## Your standing stack stays personal

`/ship` reads your **standing stack** (your default frameworks — never re-asked) from your own agent instructions, *not* from this plugin. In Claude Code that's usually `~/.claude/CLAUDE.md`; in Codex it's AGENTS.md/global instructions. A repo's own `CLAUDE.md` / `AGENTS.md` overrides it. The plugin is the *process*; your stack is *you*.

## Install

```
/plugin marketplace add peteknowsai/ship
/plugin install ship@ship
```

If you want the bundled status line, point your `statusLine` at it (or let the plugin's `statusLine` field wire it).

## Tab groups in Chrome

`chrome/ship-tabs/` is a small Chrome extension that keeps ship's pages tidy. Ship opens
every page through `pipeline/scripts/show.sh`, which uses `open -g` (Chrome never comes
forward) and tags the URL `#ship=<repo>/<slug>/<kind>`. Each window gets at most two
groups, whatever the app: blue **📐 docs** (storyboards, plan and review cards, shots, any
doc) and green **🧪 test** (the running apps, localhost and previews). A page joins at the
group's end, so the last tab in docs is the newest thing ship showed you. Each tab is
titled with its kind, app and ship, then the page's own title
(`🎨 cells-app · smarter-search · storyboard r2`, `🧪 cells-app · smarter-search · Find a class`).
The extension
hands you back the tab you were on and closes the tab a new one replaces, so a redrawn
storyboard or a restarted dev server is one tab, never two. When a ship lands, its review
card closes the rest of that ship's tabs.

A sweep runs at startup and every five minutes. It reads ship docs that arrived untagged
(an older session's plain `open`, a click in Finder) from their paths: `designs/` is a
storyboard, `plans/go-card-*` a plan card, `plans/review-*` a review card, anything else
in a `specs/` or `docs/` home a doc of that repo. It files loose ones into docs or test
(tabs still in an earlier version's per-app groups included), labels them, closes older copies of the same page so only the newest stays, and closes a
worktree's pages nobody has looked at in three days. Your own tabs, and ship tabs you
dragged into a group of your choosing, are never moved.

Pete's `~/.claude/hooks/quiet-open.sh` (a PreToolUse hook on Bash) catches any session's
plain `open <page>` and makes it `open -g -a "Google Chrome"`, tagging a localhost URL with
the checkout's repo and branch, so even sessions that predate show.sh never pull Chrome
to the front.

Install once: `chrome://extensions`, turn on Developer mode, **Load unpacked**, pick
`chrome/ship-tabs` in this repo's main checkout, and turn on **Allow access to file URLs**
in its Details: Chrome lets it label local docs only with that on. After a change, press its reload button. `node chrome/ship-tabs/test.mjs`
checks the tag rules; `--live` also runs the real grouping in Chrome for Testing, launched
in the background.

## Codex Desktop

The Codex package uses `codex/ship.md` and `codex/verify.md`. It keeps the shared
express and design processes, but uses Astra subagents directly. It has no
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
