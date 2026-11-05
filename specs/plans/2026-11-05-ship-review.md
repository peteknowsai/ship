# ship review: execution plan

Source of truth: the locked storyboard `specs/designs/2026-11-05-ship-review.html`
(round 1, every pick taken, 2026-11-05). Decisions logged: 501947aa (stops, money, LAND),
d68bffa3 (QA cases at PLAN), 571c13c7 (skill budget, recall, route.py log, verify split,
deletions). This plan is machine-facing; Pete reads the plan card.

One PR (#307, `feature/ship-review`) carries Tasks 1-8. Task 9 is a cells-app PR of its
own. Task 10 runs after the merge. Every task ends on its own commit, gates green.

Gates for this repo (all of them, `$JOB/tmp/gates.sh` runs the set):
`route.py --selftest`, `decisions.py --selftest`, `muse.py --selftest`,
`branch-db.py --selftest`, `icon-check.py --selftest`, `what-changed.sh --selftest`,
`show.sh --selftest`, `mac-vm.sh --selftest`, `bash plugins/ship/hooks/ship-recap.sh --selftest`,
`bash plugins/ship/statusline-test.sh`, `node chrome/ship-tabs/test.mjs`,
`node share/worker/test.mjs`, `/usr/bin/python3 .../share.py --selftest`,
`claude plugin test plugins/ship`.

## QA cases (fixed at PLAN; TEST walks these, may add, never drops one)

1. Every gate above green on the branch head, run in full.
2. Rule audit: every rule in the old `pipeline/SKILL.md` (main's 1,540 lines) and old
   `verify/SKILL.md` (461 lines) is either in the new skill, in a named reference file
   behind a pointer whose wording says when to read it, or listed as deliberately dropped
   with the locked pick that dropped it. No rule silently gone. A fresh Opus subagent
   produces the table; the driver checks every DROPPED row against the board.
3. Fact check: every script, path, flag, subcommand and file the new skill text, the
   references and CLAUDE.md name exists on the branch and behaves as described
   (`--help` or the code). Zero dangling names, including deleted files (astra.sh,
   codex-handoff.py, quota.py, board/, reference/codex.md, Fable window).
4. `grep -rniE 'astra|codex|fable|sol\b|spark|quota\.py|shipboard|board\.cells'` over
   `plugins/ README.md CLAUDE.md .claude-plugin/` returns only intended mentions
   (the Codex-is-off line, `F` in the status line's quota, git-history pointers).
5. Line budget: `pipeline/SKILL.md` under 1,000 lines (target about 900);
   `verify/SKILL.md` about 4,000 words; checks-template.md is one-line-per-lesson shaped.
6. statusline: a fixture with two worktrees whose `.ship-stage` is `gate:*` (mtimes 1d and
   19d ago) and one at `build:2:5` renders `✋ 2 wait on you · oldest 19d`; with none
   waiting the chunk is absent. Covered in statusline-test.sh.
7. route.py: `log` without `seconds=` fills it from commit times (anchor at `plan`, then
   each `log`); `gate -- <cmd>` records each run, and `log` without `gates_first_pass=` /
   `fix_rounds=` fills them from those records; `readers` exits 1 naming the missing
   reader until both wonder and opus `stage=branch` rows exist for the ship, 0 after, and
   0 when the wonder row's note starts `out`. All in `--selftest`.
8. decisions.py: `supersede <id> <id> ... --file` writes one new decision and retires every
   named id (no duplicates); `stale` lists active calls naming a retired engine; both in
   `--selftest`. Run `stale` on the real ship and cells-app logs: ship shows none after
   Task 9, cells-app shows none after its supersede.
9. Plugin loads: a fresh `claude -p`-free check, `claude plugin test plugins/ship` green,
   and the deployed cache dir's SKILL.md parses (frontmatter intact, description present).
10. Templates: go-card.html renders storyboard first, the empty-calls rule is one rule;
    review-card.html has a "Where it is" slot. Open each headless at 1280 and 390 wide,
    no console errors, no horizontal scroll.

### Task 1: Delete the dead code

Delete outright (git history keeps it):
- `plugins/ship/skills/pipeline/scripts/astra.sh`, `codex-handoff.py`
- `codex/` (ship.md, verify.md), `scripts/build-codex.py`, `scripts/test-codex.py`
  (then `scripts/` if empty), `plugins/ship/.codex-plugin/`
- `plugins/ship/skills/verify/reference/codex.md`
- `board/` (shipboard.mjs, plist, worker/)
- `plugins/ship/skills/pipeline/design/` (both old HTML docs)

Trim:
- `muse.py`: the `build` mode, `usage` subcommand, usage cache writer, any quota leftovers;
  `review` and `--selftest` keep working.
- `statusline.sh`: the Codex quota fetch and render (`C ...`), `gate:codex`, the Codex
  `stage:` parse; `statusline-test.sh` loses the matching cases. `~/.config/ship/no-codex`
  stops mattering (listed for Pete in Task 10, not deleted).
- `hooks/ship-recap.sh`: the `[fable]` tag and the "report is gone" warning, plus tests.
- `hooks/gate-notify.sh`: `gate:codex` case, stale comments.
- `hooks/register.ts` + `register.test.ts`: the Codex `stage:` key parse and the gate:codex case.
- `plugins/ship/plugin.json` and `.claude-plugin/marketplace.json` descriptions: say what
  ship does now (Opus builds, Wonder and Opus read, ship tests itself).
- `README.md`: the Codex section.
- Every shell self-test that hardcodes `/tmp` for mktemp uses `mktemp -d` under `$TMPDIR`.

Check callers before each delete (`grep -rn` over plugins, CLAUDE.md, README, chrome,
menubar, share, and `~/Projects/claude-home/claude/skills`, `~/.claude/commands`).

### Task 2: route.py owns the build log

- Remove: the Fable window (`FABLE_UNTIL`, the every-other-task split and its test), the
  `quota` and `reader` subcommands, the pool table and POOL map, the difficulty band and
  score, the `routed` fill (always `driver`). Move the Jev `decide()` code to
  decisions.py if decisions.py is its only caller, with its test.
- `plan` records HEAD's commit time as the timing anchor in `.ship-route.json`.
- New `gate -- <cmd...>`: runs the command (output passes through, exit code returned)
  and appends `{ts, ok}` to `.ship-gates` at the worktree top (excluded like other
  `.ship-*` files).
- `log`: when `seconds=` is absent, it is HEAD's commit time minus the anchor; when
  `gates_first_pass=` / `fix_rounds=` are absent, they come from `.ship-gates` runs after
  the anchor (first run's ok; count of red runs). Then the anchor moves to HEAD's time.
  A value given on the command line wins. With no anchor and no value, the field is left
  out, never guessed.
- New `readers repo= ship=`: exit 0 when the ledger holds `review=wonder stage=branch` and
  `review=opus stage=branch` rows for the ship (a wonder row whose `note` starts `out`
  counts, for Muse being down), else exit 1 printing what's missing.
- `--selftest` covers all of the above in a temp git repo.

### Task 3: decisions.py retires many and flags stale calls

- `supersede <id> [<id> ...] --file <json>`: one new decision, every named id retired by
  it, in one write. Prefix ids accepted as today; an id that matches nothing or two
  decisions refuses before writing.
- `stale`: active calls whose text names a retired engine or tool (Astra, Sol, Spark,
  Codex, Fable building, quota.py, SubQ, shipboard). `relevant` and `recent` mark such
  a call `[stale]` so a ship never acts on one.
- `--selftest` covers both.

### Task 4: status line counts the ships waiting on Pete

- `statusline.sh` line 1 gains `✋ N wait on you · oldest Nd` after `🚢 N`: N counts
  worktrees whose live `.ship-stage` starts `gate:`; the age is the oldest such file's
  mtime, in days (hours under one day). Absent when N is 0.
- `statusline-test.sh` gets the fixture from QA case 6.

### Task 5: verify split

- `verify/SKILL.md` keeps the web path (about 4,000 words). Move out, each behind a
  pointer naming when to read it:
  - `reference/ios.md` (contract has `ios:`): iPhone and simulator preconditions and walk;
    settles the locked phone (simulator unless the change needs the phone itself) and
    Safari; names the `ios:` owner.
  - `reference/mac.md` (contract has `mac:`): Mac VM preconditions and walk.
  - `reference/browser.md`: protected previews, print, terminal UI.
- Settle in the move: qa.md says "protected" and never holds the bypass secret; define
  `<out-dir>` and `<shots-root>` once; repo-specific sign-in tricks go to that repo's
  checks file.
- QA cases come from the plan's `## QA cases` section (PLAN writes them); verify walks
  them as written, may add, never drops one.
- `reference/checks-template.md`: one line per lesson, a new lesson replaces the old
  one on the same subject, a noise table (known console noise to ignore), the cap.
- §5 write-back: prune the file to its cap when over it.
- `reference/codex.md` is gone (Task 1); drop its pointer.

### Task 6: pipeline references

- New `reference/contract.md`: every contract key in full (gates, scoped runs, sandbox,
  backend, stack, ios, mac, worker, land, deploy, smoke), moved from SKILL.md's contract
  section. Define `worker:`.
- New `reference/plan-review-brief.md`: the plan reader's checklist (from PLAN).
- New `reference/branch-review-brief.md`: both branch readers' brief (from REVIEW), with
  the HEAD sha rule and "assume the writer was wrong at every seam".
- `rare-cases.md`: add backends other than a copied database, native app repos and the
  locked phone pointer, the integration lane and long-running workers; drop "Running
  under Codex Desktop".
- `incidents.md`: cut the Codex, Astra and Sol dispatch history (keep the generic
  delegation lessons); add the commands the worktree guard misreads.
- `go-card.html`: storyboard first, then the work list; one rule for no calls (shown,
  not waited on; the "Your call" card says so in one line).
- `review-card.html`: add the "Where it is" slot (preview/live links); fix the
  "verifier" wording; FLAGGED says what Pete can say.

### Task 7: rewrite pipeline/SKILL.md (about 900 lines)

Order and budgets (storyboard A2): What ship is 25 · Verbs and sizing 60 · Talking to
Pete, ship's own parts only 20 · Working rules (guard, sandbox, tmp, background waits) 35
· Engines and reviewers 50 · Repo contract, one line per key 45 · 0 Fork 80 · 1 DISCOVER 85
· 2 PLAN 55 · 3 BUILD 95 · 4 REVIEW 55 · 5 TEST 85 · 6 LAND 105 · 7 RETRO 45 · Every stop 25.

Must carry:
- The fourteen B1 answers: Codex off in one line; no plan card on self-directed ships,
  the review card stays; one stop list; plan card storyboard first, no calls → shown;
  review card "where it is"; smoke reruns once on a network error only; full gates before
  QA when the tree changed after pulling main; REVIEW its own stage; read-only checks
  (duplicate card, landed fix, free disk) before the fork, fork right after; dev server
  up before Wonder's read starts; qa.md says "protected"; LAND step 0 in the worktree,
  then main; `worker:` defined (contract.md); locked phone → simulator unless the change
  needs the phone.
- Every stop (C2) in one table: storyboard round, plan card with a call, Pete's login,
  money path (any repo, `land: auto` included), one-way door, "you said you'd try it",
  QA couldn't prove a step.
- LAND (D2): gates green in the worktree → mergeable and `gh pr checks` green → squash
  merge → then `wt remove` → watch the deploy; a failed build keeps the old one live and
  fixes forward; live but broken (404s, smoke red) reverts first, then fixes.
- PLAN writes the QA cases (E3). TEST walks them, may add, never drops.
- Engines: Opus 5.5 writes; Wonder and Opus read the plan (Wonder) and branch (both);
  `route.py readers` before LAND on self-directed and gated ships; ledger rows filled by
  route.py (seconds and first pass from commits and `route.py gate`). No Fable window.
- Decision recall (`decisions.py relevant`) on design ships only; never act on a
  `[stale]` call.
- A pointer per moved block, worded by the case that sends the agent there.
- Everything in the incidents-first rule: a one-run lesson goes to incidents.md.

### Task 8: repo docs and memory

- `CLAUDE.md`: the line budget rule under House rules (pipeline skill under 1,000 lines;
  a retro finding goes to `reference/incidents.md` first, a second run hitting it earns a
  skill line); drop the shipboard section and the astra.sh / codex-handoff.py mentions;
  name the new route.py and decisions.py checks.
- Memories: engine-ladder (Fable window closed, report given on the board as G2, Opus
  only), ship-tests-itself (QA cases fixed at PLAN, E3).

### Task 9: cells-app (own PR)

- Trim `~/Projects/cells-app/.claude/skills/checks/SKILL.md` (595 lines) to about 150 in
  the new one-line-per-lesson shape, keeping every live lesson; lands through cells-app's
  own contract.
- `decisions.py supersede` in cells-app's log: c1c2b0ec, fbc0c618, 19cece12, 78683828,
  ae5d50f3 and the SubQ line in 5dea5e0e, with one current engines call.

## After the merge (runs at LAND, not a build task)

- Deploy to the plugin cache (every `ship@ship` entry).
- Shipboard teardown on PKAI, each checked before removal: the `board.cells.md` Worker,
  its R2 bucket `shipboard`, its DNS record.
- List the leftover files for Pete without deleting: `~/.config/ship/opus-weekly-cap`,
  `~/.config/ship/no-codex`, `~/.claude/codex-usage-cache.json`, the old cache dirs.
