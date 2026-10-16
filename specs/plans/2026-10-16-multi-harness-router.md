# Multi-harness BUILD router — execution plan

Pete's design, settled in chat on 2026-10-16 (decision log: "Each model runs in the harness built for it",
"Ship scores BUILD difficulty … with SubQ Snap"). Machine-facing; Pete reads the result, not this.

## What changes

BUILD stops being Fable-or-Opus. `route.py plan` ranks the routable tasks by difficulty (SubQ, Jev fallback,
unchanged) and cuts them into three tiers by rank, then picks an engine inside each tier:

| Tier (by rank among routable tasks) | Engines | Pick inside the tier |
|---|---|---|
| hard: top third (always holds the hardest task) | `opus`, `fable` | fixed: the hardest 3/4 of the tier to Opus, the rest to Fable |
| middle: middle third | `astra`, `wonder` | dealt in proportion to each pool's projected unused quota |
| easy: bottom third | `sol`, `spark` | dealt in proportion to each pool's projected unused quota |

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
  its path sits under a prefix listed in `~/.config/ship/confidential-paths` (one absolute path per line, `#`
  comments, `~` expanded). That file is local to Pete's Mac and never committed: the ship repo is public and
  must not name client repos. Confidential: `wonder` and `spark` leave the candidate lists, so middle is all
  `astra` and easy all `sol`.
- **Opus cap:** no `opus` build while the `anthropic` pool's weekly_all is at or above 70%, or its 5h session at or
  above 85%; those hard tasks go to `fable`. If `fable`'s pool is at or above 95%, its hard tasks go to `opus`
  (the cap still wins: both blocked → `fable` and stderr says so).
- **An empty pool** (projected unused ≤ 0, or used ≥ 95%) leaves its engines out of the tier; a tier with no
  engine left escalates its tasks one tier up (easy → middle → hard).
- **Unknown quota** (a cache missing or older than its window) counts as 50% spare for that pool and is named
  in the JSON's `quota_notes`, never an error: the router never blocks a build.

Runtime escalation (driver, documented in SKILL.md): a builder that fails (nonzero wrapper exit, a quota error,
or two wrong diffs) re-runs one tier up on the engine `route.py quota` shows with the most spare, skipping the
pool that just failed; hard escalates fable → opus.

## Tasks

### Task 1: quota.py — read and project the four pools

**Files:** create `plugins/ship/skills/pipeline/scripts/quota.py`.

Reads three caches and projects how much of each pool would go unused at its reset at the current pace.

- Sources (all JSON; a missing or unparseable file is "unknown", never a crash):
  - `~/.claude/usage-cache.json` (written by the status line). `limits[]` entries `{kind, percent, resets_at}`
    with kinds `session` (5h), `weekly_all`, `weekly_scoped` (its `scope.model.display_name` is `Fable`);
    `resets_at` is ISO 8601 with offset. Fallback fields: `.five_hour.utilization/.resets_at`,
    `.seven_day.utilization/.resets_at`.
  - `~/.claude/codex-usage-cache.json` (status line): `.rate_limit.primary_window.used_percent`,
    `.reset_at` (epoch seconds), `.limit_window_seconds` (604800 = weekly); `.rate_limit.limit_reached`.
  - `~/.claude/muse-usage-cache.json` (written by muse.py, Task 3): `{"window": {"usedPercent", "resetsAtMs",
    "windowDurationMins"}, "weekly": {"usedPercent", "resetsAtMs"}, "observedAtMs"}`. A window or week whose
    `resetsAtMs` has passed counts as 0% used with the next reset one window later.
  - Overridable for tests: env `SHIP_QUOTA_ANTHROPIC`, `SHIP_QUOTA_CODEX`, `SHIP_QUOTA_MUSE` (paths), and
    `SHIP_QUOTA_NOW` (epoch seconds).
- Projection for one window: `elapsed = window_len - seconds_to_reset` (clamped ≥ 1h so a fresh window doesn't
  extrapolate wildly), `projected_end = used + used / elapsed * seconds_to_reset`, `unused = max(0, 100 -
  projected_end)`. Weekly windows are 7 days; Anthropic session is 5h; Muse window uses `windowDurationMins`.
- Pool numbers (`pools()` returns a dict keyed by pool):
  - `anthropic`: `used` = weekly_all percent, `session` = session percent, `unused` = projected weekly unused,
    `opus_blocked` = weekly_all ≥ 70 or session ≥ 85.
  - `fable`: from weekly_scoped; `unused` is halved (Fable drains about twice as fast, Pete 2026-10-16).
  - `openai`: from primary_window; `limit_reached` → `unused` 0.
  - `muse`: `unused` = the smaller of projected weekly unused and `100 - window used` (the 5h window is the
    tighter limit day to day).
  - each pool carries `resets_at` (ISO), `known` (bool), `note` (why unknown, if so).
- CLI: `quota.py` prints the pools as JSON; `quota.py --table` prints one line per pool
  (`pool used% unused% resets`); `quota.py --selftest`.
- Self-test (no network, temp files via the env overrides): a fresh week at 10% used, a week half gone at 50%
  (projects ~100, unused ~0), Fable halved, Opus blocked at 70 and at session 85, an expired Muse window reads
  0%, a missing cache reads unknown at 50, `limit_reached` reads 0.

### Task 2: astra.sh build mode — Codex builds again, sandbox off

**Files:** modify `plugins/ship/skills/pipeline/scripts/astra.sh`.

- New mode `astra.sh build <worktree> <brief.md> <out-dir> <model> [effort]`; `<model>` is required
  (`gpt-6-astra` or `gpt-6.1-sol`; any other string is passed through). Effort defaults to `high`.
- Runs `codex exec -C <worktree> -s danger-full-access` (Codex's sandbox blocked vitest writes, Xcode and
  typecheck and made the driver rerun tests on most Codex tasks in October; Pete approved sandbox-off builds
  2026-10-16) with the same isolation as `review`: `--ignore-user-config`, `-c features.apps=false`, and a home of
  its own under `<out-dir>/home` holding only a link to the real `auth.json` (so no MCP server, connector, plugin
  or skill reaches the builder). Same watchdog, same exit codes, same `events.jsonl` / `last.md` / `stderr.txt`.
- Update the header comment: Codex builds again (2026-10-16), and why the sandbox is off.
- The old retired-mode check (`run`) stays refused; `build` without a model exits 2.
- Self-test additions (raise the count): a build run finishes; its args carry `-s danger-full-access`,
  `-m gpt-6.1-sol` when asked, `--ignore-user-config`, `features.apps=false`, `HOME=<out>/home`, the auth link;
  `build` with no model exits 2.

### Task 3: muse.py — Muse Code builds through `muse serve`, and records plan usage

**Files:** create `plugins/ship/skills/pipeline/scripts/muse.py`.

`muse exec` never reports plan usage; `muse serve` (JSON-RPC 2.0, one JSON object per line on stdio) sends a
`usage/changed` notification after each turn. A working probe is at
`/Users/pete/.claude/jobs/33c787a1/tmp/muse-usage-probe.py` (read it: initialize → `initialized` notification →
`session/start` → `turn/start`). Full wire schema: run `muse schema generate-ts --out <dir> --experimental` and
read `msp.d.ts` (`SessionStartParams`, `TurnStartParams`, `TurnCompletedParams`, `TurnError`, `QuotaDetail`,
`ItemCompletedParams`, `SubscriptionUsage`). `commandId` must be a UUIDv7 (the probe has a helper).

- `muse.py build <worktree> <brief.md> <out-dir> <model>`:
  - Refuses (exit 2) when `<worktree>` is under a prefix in `~/.config/ship/confidential-paths` (same reader as
    route.py; put the reader in quota.py as `confidential(path)` and import it, or duplicate the five lines).
  - Starts `muse serve --contributor-mode on --disable-sandbox --trust-workspace --disable-request-user-input
    --model <model>` with cwd `<worktree>`, under an isolated home so Pete's personal skills (`~/.agents/skills`)
    never load and never reach Meta: `HOME=<out-dir>/home`, with `<out-dir>/home/.config/muse/auth.json` and
    `settings.json` symlinked to the real `~/.config/muse/` files. (`serve` has no
    `--no-foreign-personal-context` flag; the isolated home does the same job.) Keep `PATH`.
  - `session/start` with `workspaceRoot` = worktree, `modelId` = model, `approvalMode: "allowAll"`.
  - `turn/start` with `input: [{"type": "text", "text": <brief file contents>}]`, `reasoningEffort: "high"`.
  - Writes every frame to `<out-dir>/events.jsonl`. The final message is the text of the last `item/completed`
    whose `item.kind == "agentMessage"` (find its text field in the schema), written to `<out-dir>/last.md`.
  - Ends on `turn/completed`: `terminal == "completed"` and a non-empty last.md → exit 0; `failed` with
    `error.quota` → write the quota detail to the usage cache as exhausted (`window.usedPercent: 100`,
    `resetsAtMs` from the detail), print it, exit 5; other failure → exit 1 with the error on stderr; completed
    with no message → exit 4 (it DID NOT RUN, as astra.sh says).
  - Every `usage/changed` (and a final `usage/read` after the turn) rewrites `~/.claude/muse-usage-cache.json`
    (path overridable by `SHIP_QUOTA_MUSE`) with the params plus `observedAtMs`.
  - Watchdog like astra.sh: no `turn/started` within `MUSE_STARTUP` (default 60) seconds → kill, exit 3; no frame
    for `MUSE_IDLE` (default 900) seconds → kill, exit 3. Always kill the serve process on exit.
- `muse.py usage` prints the cached usage (no prompt spent).
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
- `report`: add a by-pool block (rows, first-pass rate, mean fix rounds).
- New subcommand `route.py quota` = `quota.py --table` (so the driver has one tool).
- Self-test: keep every existing check that still applies (rewrite the ladder ones for tiers); add: nine tasks
  split 3/3/3 by rank; Opus takes `ceil(0.75 * n)` of a hard tier of n, capped at n-1 when n ≥ 2 so Fable
  always gets one (n=1: opus; n=3: 2 opus + 1 fable; n=4: 3 + 1), Opus on the hardest; middle with openai unused
  60 and muse 20 deals 3 tasks 2 astra / 1 wonder; confidential drops wonder/spark; Opus cap moves hard to fable; muse empty sends
  middle all to astra; both easy pools empty escalates easy to middle; unknown quota counts 50 and is noted;
  `log engine=sol` fills `pool=openai`.

### Task 5: SKILL.md, CLAUDE.md, and the docs (inline)

**Files:** `plugins/ship/skills/pipeline/SKILL.md` (Engines, BUILD), `CLAUDE.md` (selftest list),
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

- `quota.py --table` on the real caches: four pools, Muse known (the probe already wrote usage? if not, the
  first muse.py run will).
- One real tiny task through each new engine, in a throwaway worktree of the ship repo (e.g. "add a one-line
  comment to README"): `astra.sh build … gpt-6-astra`, `astra.sh build … gpt-6.1-sol`, `muse.py build …
  muse-wonder-full-1.0`, `muse.py build … muse-spark-1.3`. Each must edit only the named file, not commit, end
  with STATUS/TESTS/CONCERNS, and (Muse) refresh the usage cache. Remove the throwaway worktree after.
- `route.py plan` on a real cells-app plan: tiers, pools, picks printed; then the same with a temp
  confidential-paths file covering it: no wonder/spark.
- `~/.config/ship/confidential-paths` exists with Pete's client prefix (not committed).

### Task 7: Pete's global CLAUDE.md, memory (driver)

- Draft the "Who writes code" change in `~/.claude/CLAUDE.md` and show Pete the diff before saving (Pete's call).
- Update the engine-ladder memory and the decision log.
