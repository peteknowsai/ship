# ship review: execution plan

Source of truth: the locked storyboard `specs/designs/2026-11-05-ship-review.html`
(round 1, every pick taken, 2026-11-05). Decisions logged: 501947aa (stops, money, LAND),
d68bffa3 (QA cases at PLAN), 571c13c7 (skill budget, recall, route.py log, verify split,
deletions). This plan is machine-facing; Pete reads the plan card. Revised after Wonder's
plan read (19 real, 3 nits, 1 false) and the cel-315-walk-notes retro.

One PR (#307, `feature/ship-review`) carries Tasks 1-8. Task 9 is a cells-app PR of its
own. The after-merge list runs at LAND. Every task: commit, then `route.py log`.

Gates for this repo (`$JOB/tmp/gates.sh` runs the set, sandbox off):
`route.py --selftest`, `decisions.py --selftest`, `muse.py --selftest`,
`branch-db.py --selftest`, `icon-check.py --selftest`, `what-changed.sh --selftest`,
`show.sh --selftest`, `mac-vm.sh --selftest`, `bash plugins/ship/hooks/ship-recap.sh --selftest`,
`bash plugins/ship/statusline-test.sh`, `node chrome/ship-tabs/test.mjs`,
`node share/worker/test.mjs`, `/usr/bin/python3 .../share.py --selftest`,
`claude plugin test plugins/ship`.

## QA cases (fixed at PLAN; TEST walks these, may add, never drops one)

1. Every gate above green on the branch head, run in full.
2. Rule audit: every rule in main's `pipeline/SKILL.md` (1,540 lines), `verify/SKILL.md`
   (461), `rare-cases.md`, `incidents.md`, `go-card.html`, `review-card.html` and
   `storyboard.html` is either kept (in the new skill, or in a named file behind a pointer
   whose wording names the case that sends the agent there), or listed as dropped with the
   locked pick that dropped it. A fresh Opus subagent produces the table; the driver checks
   every DROPPED row against the board and spot-checks ten KEPT rows by following the pointer.
3. Fact check: every script, path, flag, subcommand and file the new skill text, the
   references and CLAUDE.md name exists on the branch and behaves as described (`--help`
   or the code). Zero dangling names, deleted files included (astra.sh, codex-handoff.py,
   quota.py, board/, reference/codex.md, `muse.py build`, `route.py reader`).
4. `grep -rniE '\bastra\b|codex|fable|\bsol\b|\bspark\b|quota\.py|shipboard|board\.cells'`
   over `plugins/ README.md CLAUDE.md .claude-plugin/` returns only intended mentions
   (the Codex-is-off line, the status line's `F` quota, git-history pointers, decisions.py's
   RETIRED table).
5. Line budget: `pipeline/SKILL.md` under 1,000 lines (target about 900); `verify/SKILL.md`
   about 4,000 words; checks-template.md is one-line-per-lesson shaped.
6. statusline: two worktrees whose `.ship-stage` is `gate:*` (mtimes 1 and 19 days ago, one
   of them `gate:input`) and one at `build:2:5` render `✋ 2 wait on you · oldest 19d`; none
   waiting, the chunk is absent; `gate:input` renders its own line-1 text. In
   statusline-test.sh.
7. route.py `--selftest`: `log` fills `seconds` from the wall clock since `plan` or the last
   task row (review and recall rows don't move it); `gate <cmd>` records each run and `log`
   fills `gates_first_pass` / `fix_rounds` from runs since the last task row; a value passed
   wins; `readers` exits 1 naming the missing reader until both `review=wonder stage=branch`
   and `review=opus stage=branch` rows exist, 0 after, and 0 with a wonder row whose note
   starts `out:`; `report` still reads old rows that carry pool and score.
8. decisions.py `--selftest`: `supersede <id> <id> ... --file` writes one decide event and
   one supersede event per id, every id vanishes from `recent`, and an id matching nothing
   refuses before any write; `stale` lists a pre-retirement call that gives a retired
   engine a ship job, not a later "Codex is off" call, not a product call naming the same
   model (cells-app's Codex login, its Muse Spark picker). Then on the real logs: ship's
   `stale` shows none now; cells-app's shows none after Task 9.
9. Plugin loads: `claude plugin test plugins/ship` green, and the branch's two SKILL.md
   files keep their frontmatter (name, description) intact.
10. Templates: fill go-card.html and review-card.html with fixture values (every `{{...}}`
    replaced, a local storyboard and image), then open each headless at 1280 and 390 wide:
    storyboard first on the plan card, one no-calls rule, a "Where it is" slot on the
    review card, no console errors, no horizontal scroll.
11. One gate run with the Bash sandbox on, to confirm the self-tests that should pass there
    still do (the ones that bind ports are expected red and named).

## Task 1: Delete the dead code

Delete outright (git history keeps it):
- `plugins/ship/skills/pipeline/scripts/astra.sh`, `codex-handoff.py`
- `codex/` (ship.md, verify.md), `scripts/build-codex.py`, `scripts/test-codex.py`
  (then `scripts/`), `plugins/ship/.codex-plugin/`
- `plugins/ship/skills/verify/reference/codex.md`
- `board/` (shipboard.mjs, plist, worker/)
- `plugins/ship/skills/pipeline/design/` (both old HTML docs)

Trim:
- `muse.py`: drop the `build` and `usage` CLI entries and the usage cache (save_usage,
  mark_exhausted, read/write_cache: nothing outside muse.py reads it since quota.py went).
  Keep the internal builder `review()` runs, its `seconds` file (route.py `out=` reads it),
  exit 5 with the reset time printed. Rework the self-test to drive `review`.
- `statusline.sh`: the Codex quota fetch and render (`C ...`), `gate:codex`, the Codex
  multi-line `stage:` parse; `statusline-test.sh` loses those cases.
- `hooks/register.ts`: the Codex `stage:` parse in `parseStage`; its test case.
- `hooks/ship-recap.sh`: the `[fable]` tag and the "report is gone" warning, plus tests.
- `hooks/gate-notify.sh`: the `gate:codex` case, stale comments.
- `stage.sh`: the "watched Codex hand-off" words in the LAND warning.
- `plugins/ship/plugin.json`, `.claude-plugin/marketplace.json`: descriptions say what ship
  does now (Opus builds, Wonder and Opus read, ship tests itself).
- `README.md`: the Codex section.
Dropped from the board's ride-alongs: "mktemp under $TMPDIR" (no self-test hardcodes /tmp;
bare `mktemp -d` already honors `$TMPDIR`).

Check callers before each delete (`grep -rn` over plugins, CLAUDE.md, README, chrome,
menubar, share, `~/Projects/claude-home/claude/skills`, `~/.claude/commands`).

## Task 2: route.py owns the build log

- Remove: the Fable window (`FABLE_UNTIL`, the every-other-task split, its test), the
  `reader` subcommand, the `routed` fill, the POOL map and difficulty band (report groups
  by engine only; old rows' pool and score fields are ignored, not an error). Move the Jev
  `decide()` code to decisions.py, its only caller, with its test.
- `plan` saves the tasks to `.ship-route.json` with `anchor` = now (wall clock); a
  re-`plan` keeps an existing anchor.
- New `gate <cmd> [args]`: runs the command (output passes through, its exit code
  returned) and appends `{ts, ok, cmd}` to `.ship-gates` beside the marker. One call per
  check: the scoped gate script is one command, so a red run is one fix round.
- `log`, task rows only: `seconds` = now − anchor; `gates_first_pass` = the first gate run
  after the anchor passed; `fix_rounds` = red runs after it. A value on the command line
  wins; no anchor or no runs leaves the field out. Then anchor = now. Review and recall
  rows never touch the anchor.
- New `readers repo= ship=`: exit 0 when the ledger holds `review=wonder stage=branch` and
  `review=opus stage=branch` rows for the ship (a wonder row with `note=out:<exit>` counts:
  Muse was down and an Opus reader took its place), else exit 1 naming what's missing.
- `--selftest` covers all of it in a temp git repo.

## Task 3: decisions.py retires many and flags stale calls

- `supersede <id> [<id> ...] --file <json>`: every id resolves first (each to exactly one
  active decision, else refuse with nothing written); then one decide event (its
  `supersedes` is the id, or the list of ids) and one `kind: supersede` event per id, which
  is what `active()` reads.
- `stale`: active calls made before an engine or tool was retired that give it a ship job:
  a clause of the decision text (not the rationale) holding both a retired name (word
  boundaries: Codex, Astra, Sol, Sonnet, Fable, SubQ, quota, shipboard; not Spark, a live
  cells-app product model) and a job
  word (build, review, QA, test, fix, task, dispatch, pace, ...), dated before that name's
  retirement. `relevant` and `recent` mark such a call `[stale: ...; the skill's text wins]`.
- `--selftest` covers both, including a later "Codex is off" call and a product call.

## Task 4: status line counts the ships waiting on Pete

- Every stop in the C2 list writes a `gate:` marker: storyboard `gate:1`, plan card with a
  call `gate:2`, merge-main stops `gate:test`, and the `needs input:` stops (Pete's login,
  QA couldn't prove a step) a new `gate:input`. statusline.sh renders `gate:input` as
  `✋ <slug> — needs you`; register.ts shows no buttons for it; gate-notify fires for it.
- Line 1 gains `✋ N wait on you · oldest Nd` after `🚢 N`: N counts worktrees whose live
  `.ship-stage` starts `gate:`; the age is the oldest such file's mtime, in days (hours
  under one day). Absent when N is 0.
- statusline-test.sh gets QA case 6's fixture.

## Task 5: verify split

- `verify/SKILL.md` keeps the web path (about 4,000 words). Move out, each behind a
  pointer naming when to read it:
  - `reference/ios.md`, read when the contract has `ios:` or the spec or storyboard says
    mobile web: iPhone and simulator preconditions and walks, simulator Safari for mobile
    web; settles the locked phone (simulator unless the change needs the phone itself);
    names who owns `ios:`.
  - `reference/mac.md` (contract has `mac:`): Mac VM preconditions and walk.
  - `reference/browser.md`: protected previews, print, a terminal UI.
- Settle in the move: qa.md says "protected" and never holds the bypass secret; define
  `<out-dir>` and `<shots-root>` once, the shots root being the session's launch
  directory (the primary checkout when the session entered a worktree), since the
  chrome-devtools MCP refuses files outside it (cel-315 retro); repo-specific sign-in
  tricks go to that repo's checks file.
- QA cases: on a ship with a plan they come from its `## QA cases` (PLAN wrote them) and
  verify walks them as written, may add, never drops one; on EXPRESS or standalone
  `/verify`, verify writes qa.md's cases itself, as today.
- `reference/checks-template.md`: one line per lesson; a new lesson replaces the old one
  on the same subject; a noise table (console noise to ignore); the cap.
- §5 write-back prunes the file to its cap when over it.

## Task 6: pipeline references

- New `reference/contract.md`: every contract key in full, moved from SKILL.md: `gates:`
  (scoped runs, sandbox, load rule), `dev:`, `preview:`, `test-auth:`, `backend:`,
  `stack:`, `ios:`, `mac:`, `worker:` (defined: a long-running process main runs, which LAND
  restarts after the merge), `deploy:`, `smoke:`, `live:`, `land:`, `release:`, `board:`,
  `ship: no`. The `land: auto` clause says money paths still wait for "merge main" (Q4).
  The load rule gains: a second red on load waits for the 1-minute load to fall under the
  core count before the next run, never skipping a test (cel-315 retro).
- New `reference/plan-review-brief.md` (plan reader's checklist) and
  `reference/branch-review-brief.md` (both branch readers' brief, the HEAD sha rule,
  "assume the writer was wrong at every seam").
- Card contracts move into their templates as a comment block at the top: the storyboard
  contract into `storyboard.html`, the plan card's into `go-card.html`, the review card's
  into `review-card.html`; the skill keeps one line per card with the pointer.
- `rare-cases.md`: add backends other than a copied database, native app repos and the
  locked-phone pointer, the integration lane, long-running workers; update Landing
  variants to the new LAND order (merge without `--delete-branch`, `wt remove`, then
  delete the remote branch); drop "Running under Codex Desktop".
- `incidents.md`: cut the Codex, Astra and Sol dispatch history (keep the generic
  delegation lessons); add the commands the worktree guard misreads.
- `go-card.html`: storyboard first, then the work list; one no-calls rule (the card is
  shown, not waited on, and "Your call" says so in one line).
- `review-card.html`: add the "Where it is" slot (preview and live links); fix the
  "verifier" wording; FLAGGED says what Pete can say.

## Task 7: rewrite pipeline/SKILL.md (about 900 lines)

Order and budgets (storyboard A2): What ship is 25 · Verbs and sizing 60 · Talking to
Pete, ship's own parts only 20 · Working rules (guard, sandbox, tmp, background waits) 35
· Engines and readers 50 · Repo contract, one line per key 45 · 0 Fork 80 · 1 DISCOVER 85
· 2 PLAN 55 · 3 BUILD 95 · 4 REVIEW 55 · 5 TEST 85 · 6 LAND 105 · 7 RETRO 45 · Every stop 25.
Follow-ups go in RETRO, gate signals in Every stop, FleetView in Talking to Pete.

Must carry:
- The fourteen B1 answers: Codex off in one line; no plan card on self-directed ships,
  the review card stays; one stop list; plan card storyboard first, no calls → shown;
  review card "where it is"; smoke reruns once on a network error only; full gates before
  QA when the tree changed after pulling main; REVIEW its own stage; read-only checks
  (duplicate card, landed fix, free disk) before the fork, fork right after; dev server
  up before Wonder's read starts; qa.md says "protected"; LAND step 0 in the worktree,
  then main; `worker:` defined (contract.md); locked phone → simulator unless the change
  needs the phone.
- Every stop (C2) in one table with its marker: storyboard round `gate:1`, plan card with
  a call `gate:2`, Pete's login `gate:input`, money path (any repo, `land: auto`
  included) `gate:test`, one-way door `gate:test`, "you said you'd try it" `gate:test`, QA
  couldn't prove a step `gate:input`.
- LAND (D2): gates green in the worktree, `route.py readers` (self-directed and gated) →
  mergeable, and `gh pr checks`: no checks reported means the local gates stand, pending
  waits (`gh pr checks --watch`), red is fixed in the worktree → `gh pr merge <n> --squash`
  without `--delete-branch` → `wt remove <branch> -f` → `git push origin --delete <branch>`
  → watch the deploy: a failed build keeps the old one live and fixes forward; live but
  broken (404s, smoke red) reverts first, then fixes.
- PLAN writes `## QA cases` into the plan (E3); TEST walks them, may add, never drops.
  EXPRESS has no plan: verify writes the cases at TEST.
- Engines: Opus 5.5 writes; Wonder reads the plan; Wonder and Opus read the branch. Tally
  commands carry `stage=plan|branch`; Muse out is `review=wonder stage=branch note=out:<exit>`
  plus the Opus stand-in's own row. BUILD: commit, then `route.py log`; every gate check
  runs as `route.py gate bash <gates script>`, one call per check; seconds and first pass
  come from route.py, never typed. No Fable window.
- Decision recall (`decisions.py relevant`) on design ships only; a `[stale]` call loses to
  the skill's text.
- A pointer per moved block, worded by the case that sends the agent there.
- The incidents-first rule: a one-run lesson goes to incidents.md.

## Task 8: repo docs and memory

- `CLAUDE.md`: the line budget under House rules (pipeline skill under 1,000 lines; a
  retro finding goes to `reference/incidents.md` first, and a second run hitting it earns
  a skill line); drop the shipboard section and the astra.sh / codex-handoff.py mentions;
  name `route.py gate` / `readers` and `decisions.py stale` among the checks.
- Memories: engine-ladder (Fable window closed, G2 report given, Opus only),
  ship-tests-itself (QA cases fixed at PLAN, E3).

## Task 9: cells-app (own PR)

- Trim `~/Projects/cells-app/.claude/skills/checks/SKILL.md` (595 lines) to about 150 in
  the one-line-per-lesson shape, keeping every live lesson; lands through cells-app's own
  contract.
- In cells-app's decision log, three supersedes, each replacement one clean call:
  c1c2b0ec, 19cece12, 78683828, ae5d50f3 (Fable and Astra building, reviewing, testing)
  by the current engines call; fbc0c618 by its connectors content without the build
  clause; 5dea5e0e by its content with Snap on TypeSafe's Jev (cells-app #390, 2026-11-03)
  in place of SubQ. Read each first. Then `stale` shows none.

## Retro findings folded in mid-build

- cel-298 (Task 6, 7): the review card's commit is the one that carries LAND step 0's
  smoke line; stage.sh's land warning says to commit the card with step 0's smoke, before
  the merge, so its warning on entry is the reminder, not an alarm.
- cel-298 (Task 6): every template h1 gets line-height 1.3 or more (impeccable's
  tight-leading floor), so a card never trips its Stop hook: review-card 1.05, go-card 1.1.
- screendrop-worker/loom-parity 1 (Task 7): every `gh` call names its repo, `-R
  <owner/repo>`, once as a working rule; gh resolves a fork's PR against `upstream`
  otherwise. The PR_URL line included.
- screendrop 2 (Task 6, 7): `deploy:` is the repo's own command that puts merged main live
  where the host doesn't build main (a Worker with no Workers Builds). LAND runs it from the
  main checkout after the merge, then watches `live:`; that is the repo's command, not a
  hand deploy. A repo that deploys by hand with no line gets one in this PR.
- screendrop 3 (Task 7): LAND step 0 checks each env name the diff newly reads exists, by
  name, where landing deploys (`wrangler secret list`, `vercel env ls production`, `npx
  convex env list --prod`); a missing one parks with `needs input:` naming it, since a
  production setting is Pete's. Names only, never values.
- screendrop 4 (Task 7): REVIEW's triage goes to `<job tmp>/triage-<slug>.md` before the
  first fix, one line per finding (reader, what, real/false/nit, fixed or declined and why);
  the ledger counts and the PR body's Reviewed line and declined list come from it.
- screendrop 5: not a change. The locked stop table already says "land anyway", or the same
  intent in other words, lands an unproven ship with the unwalked steps in `result:`.
- cel-323 1 (folded after Task 8): stage.sh's land reminder fired on every landing, since
  EXPRESS has no card and the carded lanes commit theirs later in LAND step 1. The check
  moves to `route.py readers`, which only SELF-DIRECTED and GATED run, after the card's
  commit, and refuses a branch that adds none.
- cel-323 3 (Task 9): cells-app's `stack:` line marks yonder and yeoman `:unreleased`, as
  their pack.json files do. Not a stack-check change: Vercel shows a production deployment
  for both, so a "no production yet" hint would never fire.

## After the merge (runs at LAND, not a build task)

- Deploy to the plugin cache (every `ship@ship` entry); then check the deployed SKILL.md
  files' frontmatter.
- Shipboard teardown on PKAI, each looked at before removal: the `board.cells.md` Worker,
  the R2 bucket `shipboard`, the DNS record. The launchd agent `md.cells.shipboard` is not
  installed (`launchctl list`, ~/Library/LaunchAgents checked 2026-11-05); recheck first.
- List the leftover files for Pete without deleting: `~/.config/ship/opus-weekly-cap`,
  `~/.config/ship/no-codex`, `~/.claude/codex-usage-cache.json`,
  `~/.claude/muse-usage-cache.json`, the old cache dirs.
