# Gate buttons — execution plan

**Goal:** when a ship parks at a gate, the band above Claude Code's prompt shows buttons Pete
presses with a bare digit (or a click) instead of noticing the status line and typing.
Approved by Pete in chat, 2026-10-21: digits plus click, no letters, never a merge button.

**Architecture:** a mod (Claude Code function hooks) inside the existing ship plugin.
`plugins/ship/hooks/hooks.json` gains `"modules": ["./register.ts"]` beside its Stop settings
hook. The module polls the session's ship worktree for `.ship-stage` every 2 s (and on
`turn.complete`), keeps the current gate in a module variable, and draws the `AbovePrompt`
band only while a gate is up and no turn is running. `show.sh` records the last URL it opened
per kind so "show" can bring that exact tab forward.

| Marker | `1` | `2` |
|---|---|---|
| `gate:1*` | show storyboard (`.ship-shown/storyboard`) | lock it (submits `lock it`) |
| `gate:2*` | show plan card (`.ship-shown/plan`) | go (submits `go`) |
| `gate:test*` | open the app (newest of `.ship-shown/preview`, `.ship-shown/test`) | none |
| anything else, `gate:codex*` included | band empty | |

"show" runs `open -a "Google Chrome" <url>` without `-g`: Pete's own press, so Chrome coming
forward is wanted. The URL carries show.sh's `#ship=` tag, so ship-tabs swaps the tab in place.
A missing `.ship-shown/<kind>` toasts "no <kind> opened yet" and opens nothing.
"lock it"/"go" call `$.prompt.submit({ text, asUser: true })`, not awaited.

**Finding the worktree** (same order as statusline.sh): `~/.claude/ship-active/<session id>`
names a worktree (first line) holding `.ship-stage` → that; else walk up from the session cwd
to the first directory holding `.ship-stage`. Stage parsing matches statusline.sh: a
`stage:` key line wins, else the first line; spaces stripped, lowercased.

### Task 1: show.sh records the last URL per kind (inline)

File: `plugins/ship/skills/pipeline/scripts/show.sh`. After the URL is tagged and before
`open -g`, write it to `<worktree>/.ship-shown/<kind>` (`mkdir -p`, one line). `.ship-*` is
already in the repo's info/exclude via stage.sh, so it never commits. Check: run show.sh's
recording line against a temp dir by hand (no open) — covered by Task 2's live check.

### Task 2: the mod and its test (driver)

Files: `plugins/ship/hooks/register.ts` (new), `plugins/ship/hooks/hooks.json`,
`plugins/ship/hooks/register.test.ts` (new).

- `session.start`: `refresh($)`, then `$.clock.every(2000, () => refresh($))`.
- `turn.complete`: `refresh($)` after `next(e)`.
- `refresh`: compute `{ kind, slug, root }` or null; when it differs from the stored one,
  store it and `$.ui.invalidate('ui.render')`. Errors (unreadable file) read as no gate.
- `ui.render` `{ component: 'AbovePrompt' }`: `next(e)` when no gate, `hasSurvey` or
  `isWorking`; else a row: amber `✋ <slug>` text, then the buttons (`plain: true`,
  `hotkey: '1'`/`'2'`, keys `ship-show`/`ship-answer`). Slug = branch-less folder name is not
  reliable, so read it from `git -C <root> branch --show-current` once per gate change, minus
  a `feature/`-style prefix; fall back to the folder name.
- Tests (`claude plugin test plugins/ship`), with fs/env/session/process/clock calls answered
  by test hooks: gate:1 draws both buttons on terminal and desktop; pressing `ship-answer`
  submits `lock it` as the user; pressing `ship-show` runs `open -a Google Chrome <recorded url>`;
  gate:test draws only `ship-show`; `gate:codex` and no marker draw nothing; `isWorking`
  draws nothing.
- Gates: `claude plugin validate plugins/ship`, `claude plugin test plugins/ship`,
  `bash plugins/ship/statusline-test.sh`.
- Live check (driver): `claude --plugin-dir plugins/ship` style run is interactive, so
  instead load-test through `claude plugin test` plus a manual marker flip in a scratch
  worktree, and confirm show.sh writes `.ship-shown/<kind>`.

### Task 3: docs (inline)

`README.md`: a short "Gate buttons" section (what shows at each gate, digits work from an
empty prompt, click works, merge stays typed). Root `CLAUDE.md`: one line under Status line
pointing at the mod and its test command. Pipeline SKILL.md "Gate signals": add a 4th signal,
the band buttons.
