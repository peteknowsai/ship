# Router delegation ledger

Two engines now: **Opus / GPT-5.5**, ~50/50, BUILD-stage only (see the `router`
skill). Append a row after every delegated *build* task; keep the summary current.
The metric that matters: **first-pass-clean rate per engine and per task-type**,
plus **escalation rate**.

Row format: `date | project | task | task-type | engine | outcome | fix-rounds | note`
- task-type: specific-coding · integration · mechanical (plan/review rows from
  history stay below for context, but router no longer routes those — Opus only)
- outcome: clean · fixed-N · escalated→opus · abandoned

## Rolling summary

| Engine | Build tasks | First-pass clean | Escalated | Notes |
|--------|-------------|------------------|-----------|-------|
| Opus | many | high | — | the default; owns brief/review/gates/git |
| GPT-5.5 (codex) | ~6 | ~4/6 clean | 2 (latency/slowness, not capability) | clean on real-exploration coding (ask.ts: 78 tests; M1: 15 tests); escalated/abandoned on verbatim writes where it was just slow |

Target: **Opus 50 / GPT-5.5 50**, BUILD-stage only. Mix is a hypothesis —
self-adjust for success.

**Standing learnings**
- **codex is slow on deterministic/verbatim writes** — for a file whose exact
  content is already in the brief, Opus-inline beats codex by minutes. Reserve
  GPT-5.5 for tasks where it genuinely *explores* (signatures, tests, a real
  self-contained problem). `xhigh` has timed out before writing a single file —
  give verbatim-heavy tasks a longer timeout or lower effort, or just keep on Opus.
- codex has **overstepped git** (auto-opened a PR, committed unprompted). Git
  stays on Opus; brief codex to write files only.
- **One writer per branch** is real — a concurrent Opus-subagent + codex run
  caused a git collision. Serialize or isolate.

## Log

| date | project | task | task-type | tier | outcome | fix-rounds | note |
|------|---------|------|-----------|------|---------|-----------|------|
| 2026-06-25 | homezero brain-native | Phase B — port store/parcels to native SQL + Vectorize | specific-coding/integration | Opus | fixed-1 | 1 | multi-file + a staff-interim scope gap to judge → Opus warranted |
| 2026-06-25 | homezero brain-native | Phase C — R2→DO ingest beat + exporter + counts | specific-coding | Opus | clean | 0 | novel Flue extend/schedule idioms → Opus warranted |
| 2026-06-25 | homezero brain-native | Phase D — DO-RPC read methods + MARKET_STORE flag | integration | Opus | clean | 0 | cross-agent stub + flag wiring → Opus warranted |
| 2026-06-25 | homezero brain-native | Phase A removal — delete superseded session-clear machinery | mechanical | Opus | clean | 0 | **down-tier candidate**: pure deletion, fully specified → should've been GPT-5.5/Gemini |
| 2026-06-25 | homezero brain-native | 4× diff reviews (B, B-delta, D, +Phase-A diff) | review | Opus | n/a | — | reviews stay Opus |
2026-06-28 | zero/extension | flair.ts Found Terminal tokens + verdictView + coverage fact/highlight | integration | opus | clean | 0 | tests updated, 64→ green
2026-06-28 | zero/extension | popup re-skin (dark/mono, HomeZero wordmark) | specific-coding | opus | clean | 0 | bundled fonts in index.html
2026-06-28 | zero/extension | zillow.content.ts restyle pill/toast/panel + under-card strip/glow/reading | integration | opus | clean | 0 | DOM-fragile; needs live Zillow validation
2026-06-28 | zero/extension | utils/ask.ts + tests/ask.test.ts (8-kind ask model, parse+serialize) | specific-coding | gpt-5.5 | clean | 0 | 78 tests; re-verified tsc+test by opus; high quality

2026-06-28 | homezero | team Task4 TeamPanel.tsx + panel CSS | specific-coding | gpt5.5(codex,xhigh) | clean | 0 | exact-spec match; tsc fail was a missing `convex codegen` step I owned, codex correctly stopped+reported
2026-06-28 | homezero | team Task6 /team page + team.css | specific-coding | gpt5.5(codex,xhigh) | abandoned | 0 | 2min timeout at xhigh before writing any file; completed on Opus (content was fully authored in brief). Lesson: give codex a longer timeout OR lower effort for verbatim-file tasks
2026-06-28 | zero/extension | recon: current homezero /api/card+coverage+convex+auth+board-ask reality (5 Explore agents) | review | opus(workflow) | clean | 0 | grounded the spec in real code
2026-06-28 | zero/homezero | extension advisor-ask contract spec (HTML) | plan | opus | clean | 0 | spec is a brief → stays Opus
2026-06-28 | zero/homezero | adversarial verify: answer-string formats + spec audit (2 Explore agents) | review | opus(workflow) | clean | 0 | nailed canonical strings, 1 nit fixed (stage always-string)
2026-06-28 | Zero/homezero | M1 setName mutation + TDD tests | specific-coding | codex/gpt-5.5 | clean | 0 | exact code+tests in brief; 15 tests pass; matched brief verbatim
2026-06-28 | Zero/homezero | M2 settings shell + Account + settings.css | integration | opus-subagent | pending | - | aesthetic keystone; CSS lift from mockup
2026-06-28 | zero/homezero | recon: shipped contract reality from PR#99 diff | review | opus | clean | 0 | confirmed answer-string/fact/highlights match spec
2026-06-28 | zero/extension | ask.ts rewrite → real boardCardAsk + canonical string + tests | specific-coding | gpt-5.5 | clean | 0 | codex auto-opened PR#9 (overstepped git); re-verified by opus
2026-06-28 | zero/extension | Phase 2 wiring: flair highlights, background answer/highlights routes, content-script live 8-control panel + glow | integration | opus | clean | 0 | adversarial review: 0 bugs; added debounce
2026-06-28 | Zero/homezero | M2 settings shell + Account + CSS (UPDATE) | integration | opus-subagent | clean | 0 | aesthetic CSS lift from mockup; tsc clean; gave clean class vocab for downstream
2026-06-28 | Zero/homezero | M3 Connections (WhatsApp relocate) | specific-coding | codex/gpt-5.5 | escalated→opus | - | codex too slow (buffered, ~mins for a deterministic file write); killed 3x incl. a concurrent-git collision. Opus wrote it inline in seconds.
2026-06-28 | Zero/homezero | M4 Billing read+stubs | specific-coding | opus-inline | clean | 0 | needed Clerk type spelunking (useSubscription/usePlans shapes) → judgment; reused signup billingPlanCards
2026-06-28 | Zero/homezero | M5 Notifications+Privacy panes | specific-coding | opus-inline | clean | 0 | lint caught inline-component-in-render, fixed
2026-06-28 | Zero/homezero | M6 AppShell cleanup + entry points | integration | opus-inline | clean | 0 | deletion/refactor w/ breakage risk; dead-import culling; correct for Opus
2026-06-28 | Zero/homezero | M7 verify + PR | review/ops | opus-inline | clean | 0 | tsc+lint+build+289 tests green; PR #100

## Note (2026-06-28 run): codex/gpt-5.5 first-pass-clean on the ONE task it finished (M1) but its
## wall-clock latency on `codex exec` (buffered output, minutes for a fully-specified write) made it
## slower than Opus writing the same file inline. For deterministic writes where the exact content is
## already known, Opus-inline beat codex on time. Reserve codex for tasks where it actually explores.
2026-06-28 | Zero/extension | dock + /api/asks open-ask queue (content script) | integration | opus | clean | 0 | crash-sensitive content-script DOM + shape-critical asks parser + tightly-coupled main() closures → kept Opus end-to-end; backend GET /api/asks built by homezero team (PR #99). asks-feed parser was a codex-shaped task but foundational/shape-critical (codex missed the near-identical ask.ts shape earlier), so Opus owned it.
