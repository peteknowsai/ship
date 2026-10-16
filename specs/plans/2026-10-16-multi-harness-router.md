# Multi-harness BUILD router — execution plan

Pete's design, settled in chat on 2026-10-16 (decision log: "Each model runs in the harness built for it",
"Ship scores BUILD difficulty … with SubQ Snap"). Machine-facing; Pete reads the result, not this.

## What changes

BUILD stops being Fable-or-Opus. `route.py plan` ranks the routable tasks by difficulty (SubQ, Jev fallback,
unchanged) and cuts them into three tiers by rank, then picks an engine inside each tier:

| Tier (by rank among routable tasks) | Engines | Pick inside the tier |
|---|---|---|
| hard: top third (always holds the hardest task) | `opus`, `fable` | fixed: the hardest 3/4 of the tier to Opus, the rest to Fable |
| middle: middle third | `astra`, `wonder` | dealt in proportion to each pool's spare rate |
| easy: bottom third | `sol`, `spark` | dealt in proportion to each pool's spare rate |

**Spare rate** (Pete's "use what would otherwise go unused"): budget left per day until the pool resets,
`(100 - used) / max(days_to_reset, 0.25)`. A pool with lots left that resets soon gets the most work; a pool
nearly spent or a week from reset gets little. (A pace projection was tried in review and read any pool used at
a steady pace as empty with half its budget left, so it is out.)

Engines, harnesses, pools:

| engine | model | harness | how the driver runs it | pool |
|---|---|---|---|---|
| `opus` | Opus 5.5 | Claude Code subagent | Agent tool, `model: "opus"` | `anthropic` (weekly_all + 5h session) |
| `fable` | Fable 5.1 | Claude Code subagent | Agent tool, `model: "fable"` | `fable` (weekly_scoped, drains ~2x, counted double) |
| `astra` | gpt-6-astra | Codex | `astra.sh build <wt> <brief> <out> gpt-6-astra` | `openai` |
| `sol` | gpt-6.1-sol | Codex | `astra.sh build <wt> <brief> <out> gpt-6.1-sol` | `openai` |
| `wonder` | muse-wonder-full-1.0 | Muse Code | `muse.py build <wt> <brief> <out> muse-wonder-full-1.0` | `muse` |
| `spark` | muse-spark-1.3 | Muse Code | `muse.py build <wt> <brief> <out> muse-spark-1.3` | `muse` |

Rules, applied before dealing:
- **Confidential repos never reach Muse** (Contributor mode trains on what it sees). A repo is confidential when
  its path, or its main checkout's path (`dirname` of `git -C <path> rev-parse --path-format=absolute
  --git-common-dir`: every ship runs in `~/Projects/.worktrees/<repo>/<branch>`, outside the listed folder), sits
  under a prefix listed in `~/.config/ship/confidential-paths` (one absolute path per line, `#`
  comments, `~` expanded). That file is local to Pete's Mac and never committed: the ship repo is public and
  must not name client repos. Confidential: `wonder` and `spark` leave the candidate lists, so middle is all
  `astra` and easy all `sol`.
- **Opus cap:** no `opus` build while the `anthropic` pool's weekly_all is at or above 70%, or its 5h session at or
  above 85%; those hard tasks go to `fable`. If `fable`'s pool is at or above 95%, its hard tasks go to `opus`
  (the cap still wins: both blocked → `fable` and stderr says so).
- **An empty pool** (used ≥ 95%, or `limit_reached`, or the Muse 5h window ≥ 95%) leaves its engines out of
  the middle and easy tiers; a tier with no engine left escalates its tasks one tier up (easy → middle → hard).
  The hard tier never empties: only the Opus cap and Fable-empty rules apply there.
- **Unknown quota** (a cache missing, or older than 30 minutes, matching the status line's own staleness rule)
  counts as 50% used with 3.5 days to reset, and is named in the JSON's `quota_notes`, never an error: the router
  never blocks a build. Ties in dealing go to the first engine in `ENGINES[tier]`.

Runtime escalation (driver, documented in SKILL.md): a builder that fails (nonzero wrapper exit, a quota error,
or two wrong diffs) re-runs one tier up on the engine `route.py quota` shows with the most spare, skipping the
pool that just failed; hard escalates fable → opus.

## Tasks

Order: Task 1 first (Tasks 3 and 4 import quota.py). Task 2 shares no file and runs beside Task 1. Tasks 3 and 4
start once Task 1 is merged into the branch. Task 5 is the driver's, after 1-4.

### Task 1: quota.py — read and project the four pools

**Files:** create `plugins/ship/skills/pipeline/scripts/quota.py`.

Reads three caches and projects how much of each pool would go unused at its reset at the current pace.

- Sources (all JSON; a missing or unparseable file is "unknown", never a crash):
  - `~/.claude/usage-cache.json` (written by the status line). `limits[]` entries `{kind, percent, resets_at}`
    with kinds `session` (5h), `weekly_all`, `weekly_scoped` (its `scope.model.display_name` is `Fable`);
    `resets_at` is ISO 8601 with offset. Fallback fields: `.five_hour.utilization/.resets_at`,
    `.seven_day.utilization/.resets_at`.
  - `~/.claude/codex-usage-cache.json` (status line): `.rate_limit.primary_window.used_percent`,
    `.rate_limit.primary_window.reset_at` (epoch seconds), `.rate_limit.primary_window.reset_after_seconds`,
    `.rate_limit.primary_window.limit_window_seconds` (604800 = weekly), and `.rate_limit.limit_reached`. Copy
    the real nesting into the self-test fixture.
  - `~/.claude/muse-usage-cache.json` (written by muse.py, Task 3): the `usage/changed` params verbatim,
    `{"observedAtMs", "tier", "window": {"usedPercent", "resetsAtMs", "windowDurationMins"}, "weekly":
    {"usedPercent", "resetsAtMs"}}`. Staleness for Muse is by `resetsAtMs`, not file age (it only refreshes when a
    Muse build runs). A window or week whose
    `resetsAtMs` has passed counts as 0% used with the next reset one window later.
  - Overridable for tests: env `SHIP_QUOTA_ANTHROPIC`, `SHIP_QUOTA_CODEX`, `SHIP_QUOTA_MUSE` (paths), and
    `SHIP_QUOTA_NOW` (epoch seconds).
- Spare rate for one weekly window: `rate = (100 - used) / max(days_to_reset, 0.25)`, floored at 0.
- Pool numbers (`pools()` returns a dict keyed by pool):
  - `anthropic`: `used` = weekly_all percent, `session` = session percent, `rate` from weekly_all,
    `opus_blocked` = weekly_all ≥ 70 or session ≥ 85.
  - `fable`: from weekly_scoped; `rate` is halved (Fable drains about twice as fast, Pete 2026-10-16);
    `empty` = used ≥ 95.
  - `openai`: from primary_window; `empty` = `limit_reached` or used ≥ 95.
  - `muse`: `rate` from weekly; `empty` = weekly ≥ 95 or the 5h window ≥ 95 (a window or week whose
    `resetsAtMs` has passed reads 0% used).
  - each pool carries `used`, `rate`, `empty`, `resets_at` (ISO), `known` (bool), `note` (why unknown, if so).
- `confidential(path)` lives here (one reader for route.py and muse.py): true when `path` or its main checkout
  (see the rule above) is under a listed prefix; the list path is overridable by `SHIP_CONFIDENTIAL_PATHS`.
- CLI: `quota.py` prints the pools as JSON; `quota.py --table` prints one line per pool
  (`pool used% unused% resets`); `quota.py --selftest`.
- Self-test (no network, temp files via the env overrides), each asserting a number: 10% used with 6 days to
  reset → rate 15.0; 40% used with 5.42 days → ~11.1 and not empty; 50% with 1 day → 50; 0.1 days to reset uses
  the 0.25 floor; Fable halved; Opus blocked at weekly 70 and at session 85; an expired Muse window reads 0%;
  Muse window at 96% → empty; a missing cache → known false, used 50; a cache file older than 30 min → unknown;
  `limit_reached` → empty; `confidential` true for a temp git worktree whose main checkout sits under a listed
  prefix and false for one that doesn't.

### Task 2: astra.sh build mode — Codex builds again, sandbox off

**Files:** modify `plugins/ship/skills/pipeline/scripts/astra.sh`.

- New mode `astra.sh build <worktree> <brief.md> <out-dir> <model> [effort]`; `<model>` is required
  (`gpt-6-astra` or `gpt-6.1-sol`; any other string is passed through). Effort defaults to `high`.
- `dispatch()` today hardcodes `-s read-only` and takes `[effort]` as `$5`; parameterize the sandbox and the
  arg positions (build: model `$5`, effort `$6`; `case` needs `build) [ $# -ge 5 ]`).
- Runs `codex exec -C <worktree> -s danger-full-access` (Codex's sandbox blocked vitest writes, Xcode and
  typecheck and made the driver rerun tests on most Codex tasks in October; Pete approved sandbox-off builds
  2026-10-16) with the same isolation as `review`: `--ignore-user-config`, `-c features.apps=false`, and a home of
  its own under `<out-dir>/home` holding only a link to the real `auth.json` (so no MCP server, connector, plugin
  or skill reaches the builder). The model's shell must still see the real home, or `npm test`, `xcodebuild`
  (DerivedData, keychains), Playwright's browser cache and package stores break: pass
  `-c shell_environment_policy.inherit="all"` and `-c shell_environment_policy.set.HOME="<real HOME>"`
  (`--ignore-user-config` drops Pete's own policy block, so both are needed). Same watchdog, same exit codes, same
  `events.jsonl` / `last.md` / `stderr.txt`.
- Update the header comment: Codex builds again (2026-10-16), and why the sandbox is off.
- The old retired-mode check (`run`) stays refused; `build` without a model exits 2.
- Self-test additions (raise the count): a build run finishes; its args carry `-s danger-full-access`,
  `-m gpt-6.1-sol` when asked, `--ignore-user-config`, `features.apps=false`, `HOME=<out>/home`, the auth link,
  and `shell_environment_policy.set.HOME=` the real home; `build` with no model exits 2. Rename the retired-mode
  case so it no longer says "build modes".

### Task 3: muse.py — Muse Code builds through `muse serve`, and records plan usage

**Files:** create `plugins/ship/skills/pipeline/scripts/muse.py`.

`muse exec` never reports plan usage; `muse serve` (JSON-RPC 2.0, one JSON object per line on stdio) sends a
`usage/changed` notification after each turn. A working probe is at
`/Users/pete/.claude/jobs/33c787a1/tmp/muse-usage-probe.py` (read it: initialize → `initialized` notification →
`session/start` → `turn/start`). Full wire schema: run `muse schema generate-ts --out <dir> --experimental` and
read `msp.d.ts` (`SessionStartParams`, `TurnStartParams`, `TurnCompletedParams`, `TurnError`, `QuotaDetail`,
`ItemCompletedParams`, `SubscriptionUsage`). `commandId` must be a UUIDv7 (the probe has a helper).

- `muse.py build <worktree> <brief.md> <out-dir> <model>`:
  - Refuses (exit 2) when `quota.confidential(<worktree>)` is true (import it; one reader).
  - Starts `muse serve --contributor-mode on --disable-sandbox --trust-workspace --disable-request-user-input
    --model <model>` with cwd `<worktree>`, under an isolated home so Pete's personal skills (`~/.agents/skills`)
    never load and never reach Meta: `HOME=<out-dir>/home`, with `<out-dir>/home/.config/muse/auth.json` and
    `settings.json` symlinked to the real `~/.config/muse/` files. (`serve` has no
    `--no-foreign-personal-context` flag; the isolated home does the same job: 23 skills load isolated vs 123
    with the real home, per review's probe.) Keep `PATH`. Set `MUSE_NO_AUTO_UPDATE=1` so the launcher doesn't
    swap binaries mid-build, and pass `--no-session-log`. The binary is found relative to the launcher, so the
    isolated home doesn't break the lookup. Two things Task 6 must confirm on a real turn and fix here if they
    fail: the model's shell sees the real `HOME` (else tests run in the empty home), and `auth.json` is still a
    symlink afterwards (Muse writes auth atomically; if it turns into a copy, point `XDG_CONFIG_HOME` at the real
    `~/.config` instead of linking files).
  - `session/start` with `workspaceRoot` = worktree, `modelId` = model, `approvalMode: "allowAll"`; the result's
    session id is `result.session.sessionId`.
  - `turn/start` with `input: [{"type": "text", "text": <brief file contents>}]`, `reasoningEffort: "high"`.
  - Writes every frame to `<out-dir>/events.jsonl`. The final message is the text of the last `item/completed`
    whose `item.kind == "agentMessage"`, its text in `item.text`, written to `<out-dir>/last.md`.
  - Ends on `turn/completed`: `terminal == "completed"` and a non-empty last.md → exit 0; `failed` with
    `error.quota` → write the quota detail to the usage cache as exhausted (`window.usedPercent: 100`,
    `resetsAtMs` from the detail), print it, exit 5; other failure → exit 1 with the error on stderr; completed
    with no message → exit 4 (it DID NOT RUN, as astra.sh says).
  - Every `usage/changed` (and a final `usage/read` after the turn) rewrites `~/.claude/muse-usage-cache.json`
    (path overridable by `SHIP_QUOTA_MUSE`) with the params plus `observedAtMs`.
  - Watchdog like astra.sh: no `turn/started` within `MUSE_STARTUP` (default 60) seconds → kill, exit 3; no frame
    for `MUSE_IDLE` (default 900) seconds → kill, exit 3. Always kill the serve process on exit.
- `muse.py usage` prints the cached usage (no prompt spent); `usage/read` answers `{}` before any observation,
  so a missing `usage` member is "nothing observed", not an error.
- `muse.py --selftest` with a stub server: `MUSE_BIN` points at a temp Python script that speaks the protocol
  (answers initialize, session/start, turn/start, then emits turn/started, an agentMessage item/completed,
  usage/changed, turn/completed). Cases: a completed build writes last.md and the usage cache; a quota failure
  exits 5 and marks the cache exhausted; completed with no message exits 4; a silent server is killed with
  exit 3; a confidential worktree exits 2 before starting the server; the serve argv carries the four flags and
  HOME points at the isolated home with the auth link.

### Task 4: route.py — tiers, pools, and the picks

**Files:** modify `plugins/ship/skills/pipeline/scripts/route.py`.

- Replace `LADDER` with `TIERS = [('easy', 1/3), ('middle', 1/3), ('hard', 1/3)]` cut by the same running-share
  `assign()` (hardest task always in `hard`), and `ENGINES = {'easy': ['sol', 'spark'], 'middle': ['astra',
  'wonder'], 'hard': ['opus', 'fable']}`, `POOL = {'opus': 'anthropic', 'fable': 'fable', 'astra': 'openai',
  'sol': 'openai', 'wonder': 'muse', 'spark': 'muse'}`. Keep the history comment above it, adding 2026-10-16.
- `pick(tiers, pools, confidential)` → engine per task, implementing every rule in "What changes" above:
  hard = hardest 3/4 (rounded up) to opus, the rest fable, then the Opus cap and Fable-empty overrides; middle
  and easy dealt across their candidates in proportion to each pool's `unused` (largest-remainder, interleaved
  by rank so both engines see easy and hard ends of the tier); a candidate whose pool is empty drops out; a tier
  with no candidates escalates.
- `plan()` loads `quota.pools()` and `quota.confidential(repo root of the plan file)`; the JSON gains `tier` and
  `pool` per task and a top-level `quota` (the pools) and `quota_notes`. The stderr table shows engine, tier,
  score, title, then one line per pool. Router-down fallback (no scores): every task is `fable` as before, tier
  `unknown`.
- `log`: fill `pool` from `POOL[engine]` when absent (any engine not in the map logs no pool).
- `report`: add a by-pool block (rows, first-pass rate, mean fix rounds), deriving the pool at report time with
  `row.get('pool') or POOL.get(row['engine'])` so the 1000+ rows logged before this ship count.
- New subcommand `route.py quota` = `quota.py --table` (so the driver has one tool).
- Self-test: keep every existing check that still applies (rewrite the ladder ones for tiers); add: nine tasks
  split 3/3/3 by rank; Opus takes `ceil(0.75 * n)` of a hard tier of n, capped at n-1 when n ≥ 2 so Fable
  always gets one (n=1: opus; n=3: 2 opus + 1 fable; n=4: 3 + 1), Opus on the hardest; middle with openai unused
  60 and muse 20 deals 3 tasks 2 astra / 1 wonder; confidential drops wonder/spark; Opus cap moves hard to fable; muse empty sends
  middle all to astra; both easy pools empty escalates easy to middle; unknown quota counts 50 and is noted;
  `log engine=sol` fills `pool=openai`; two unknown pools at 50/50 dealing 3 tasks gives the extra to the first
  engine in `ENGINES[tier]`; the hard tier never escalates even with both Anthropic pools full (all `fable`,
  noted).

### Task 5: SKILL.md, CLAUDE.md, and the docs (inline)

**Files:** `plugins/ship/skills/pipeline/SKILL.md` (Engines; BUILD, including the "Two wrong diffs … one rung
up the ladder" bullet, which becomes the tier escalation; "moves the cuts"), `CLAUDE.md` (selftest list),
`plugins/ship/skills/pipeline/reference/incidents.md` (Dispatch: one line on Codex's sandbox and why it's off for
builds now).

- Engines: replace the Fable/Opus table and "Codex builds nothing" with the tier table, the engine/harness/pool
  table, the rules, the runtime escalation, `route.py quota`, and the ledger's `pool`. Codex now runs in three
  places (build, Sol's review, testing on request). Muse runs only through `muse.py`, never a hand-typed
  `muse exec`. Say confidential repos are listed in a local file, without naming any.
- BUILD: a non-Claude engine runs as a background Bash call of its wrapper with the same brief file the Agent
  tool would get; the driver reads `<out>/last.md` (STATUS, TESTS, CONCERNS), reviews the diff, runs the gates.
  Every builder works in its own lane worktree when lanes fan out, exactly like a subagent. Seconds for the
  ledger come from the wrapper's "done in Ns" line.
- CLAUDE.md: add `quota.py --selftest` and `muse.py --selftest` to the selftest list.

### Task 6: live checks (driver)

- `quota.py --table` on the real caches: four pools; Muse reads unknown until the first `muse.py build` writes
  its cache.
- One real tiny task through each new engine, in a throwaway worktree of the ship repo (e.g. "add a one-line
  comment to README"): `astra.sh build … gpt-6-astra`, `astra.sh build … gpt-6.1-sol`, `muse.py build …
  muse-wonder-full-1.0`, `muse.py build … muse-spark-1.3`. Each must edit only the named file, not commit, end
  with STATUS/TESTS/CONCERNS, and (Muse) refresh the usage cache. The briefs ask each builder to run `echo
  $HOME` and one real test command (`python3 plugins/ship/skills/pipeline/scripts/route.py --selftest`) and
  report both: the shell must see `/Users/pete`. After the Muse runs, `<out>/home/.config/muse/auth.json` must
  still be a symlink. Remove the throwaway worktree after.
- `route.py plan` on a real cells-app plan: tiers, pools, picks printed; then the same with a temp
  confidential-paths file covering it: no wonder/spark.
- `~/.config/ship/confidential-paths` exists with Pete's client prefix (not committed).

### Task 7: Pete's global CLAUDE.md, memory (driver)

- Draft the "Who writes code" change in `~/.claude/CLAUDE.md` and show Pete the diff before saving (Pete's call).
- Update the engine-ladder memory and the decision log.
