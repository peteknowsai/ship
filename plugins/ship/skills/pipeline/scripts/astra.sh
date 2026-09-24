#!/usr/bin/env bash
# One BUILD task on Astra through `codex exec`, with the three guards bare exec lacks.
#
#   astra.sh run    <worktree> <brief.md> <out-dir> [effort]   a coding task, workspace-write
#   astra.sh review <worktree> <brief.md> <out-dir> [effort]   a read-only pass, fresh context
#   astra.sh fix    <worktree> <brief.md> <out-dir> [effort]   findings into the same thread
#   astra.sh --selftest
#
# <out-dir> gets events.jsonl (liveness), last.md (the final message) and stderr.txt.
# Exit 0: finished and said something. 3: killed by the watchdog (never started, or went
# silent). 4: exited without a final message, which means it DID NOT RUN, never a clean
# bill. Anything else is codex's own code. Slow is not failure; unknown is.
#
# Why each line is here (reference/incidents.md, Dispatch): the brief comes from a file so
# stdin closes at EOF (a held stdin looked like a slow run for an hour, 2026-09-03);
# no `thread.started` inside ASTRA_STARTUP seconds is a run that died at startup; no new
# event for ASTRA_IDLE seconds is a model that stopped; an empty last.md after exit 0 is
# the `exec review` that hit a skill-loading error and wrote nothing. `resume` takes no -C
# and no -s (both refused the whole command, 2026-09-17), so a fix round runs from the
# worktree with the sandbox as a -c key.
set -u
MODEL=${ASTRA_MODEL:-gpt-6-astra}
CODEX=${ASTRA_CODEX:-codex}
STARTUP=${ASTRA_STARTUP:-45}
IDLE=${ASTRA_IDLE:-900}
TICK=${ASTRA_TICK:-5}

mtime() { stat -f %m "$1" 2>/dev/null || stat -c %Y "$1"; }

# The user's MCP servers (a browser, a REPL) are half a second of startup each run and
# tool schemas a coding task should never reach for. Off per run, config untouched.
mcp_off() {
  local config="${CODEX_HOME:-$HOME/.codex}/config.toml"
  [ -f "${config}" ] || return 0
  sed -n 's/^\[mcp_servers\.\([A-Za-z0-9_-]*\)\]$/\1/p' "${config}" | sort -u |
    while read -r name; do printf -- '-c\nmcp_servers.%s.enabled=false\n' "${name}"; done
}

dispatch() {
  local mode=$1 worktree=$2 brief=$3 out=$4 effort=${5:-high}
  [ -d "${worktree}" ] || { echo "astra: no worktree at ${worktree}" >&2; return 2; }
  [ -s "${brief}" ] || { echo "astra: brief ${brief} is missing or empty" >&2; return 2; }
  mkdir -p "${out}"; out=$(cd "${out}" && pwd); worktree=$(cd "${worktree}" && pwd)   # a fix round runs from the worktree
  local events="${out}/events.jsonl" last="${out}/last.md"
  local -a common=(-m "${MODEL}" -c "model_reasoning_effort=${effort}" --json -o "${last}")
  local line; while read -r line; do common+=("${line}"); done < <(mcp_off)
  brief=$(cd "$(dirname "${brief}")" && pwd)/$(basename "${brief}")
  rm -f "${last}"
  local started_at; started_at=$(date +%s)
  case "${mode}" in
    run)    : > "${events}"; "${CODEX}" exec -C "${worktree}" -s workspace-write "${common[@]}" - < "${brief}" >> "${events}" 2> "${out}/stderr.txt" & ;;
    review) : > "${events}"; "${CODEX}" exec -C "${worktree}" -s read-only "${common[@]}" - < "${brief}" >> "${events}" 2> "${out}/stderr.txt" & ;;
    fix)
      local thread; thread=$(sed -n 's/.*"thread_id":"\([^"]*\)".*/\1/p' "${events}" 2>/dev/null | head -1)
      [ -n "${thread}" ] || { echo "astra: no thread_id in ${events}; nothing to resume" >&2; return 2; }
      (cd "${worktree}" && exec "${CODEX}" exec resume "${thread}" "${common[@]}" -c 'sandbox_mode="workspace-write"' - < "${brief}") >> "${events}" 2> "${out}/stderr.txt" & ;;
    *) echo "astra: unknown mode ${mode}" >&2; return 2 ;;
  esac
  local pid=$! now seen_start=0
  [ "${mode}" = fix ] && seen_start=1
  while kill -0 "${pid}" 2>/dev/null; do
    sleep "${TICK}"; now=$(date +%s)
    [ "${seen_start}" = 0 ] && grep -q '"thread.started"' "${events}" 2>/dev/null && seen_start=1
    if [ "${seen_start}" = 0 ] && [ $((now - started_at)) -ge "${STARTUP}" ]; then
      kill "${pid}" 2>/dev/null; echo "astra: no thread.started after ${STARTUP}s; died at startup. See ${out}/stderr.txt" >&2; return 3
    fi
    if [ $((now - $(mtime "${events}"))) -ge "${IDLE}" ]; then
      kill "${pid}" 2>/dev/null; echo "astra: no event for ${IDLE}s; the run went silent. Resume it with: astra.sh fix" >&2; return 3
    fi
  done
  wait "${pid}"; local code=$?
  [ "${code}" = 0 ] || { echo "astra: codex exited ${code}. See ${out}/stderr.txt" >&2; return "${code}"; }
  [ -s "${last}" ] || { echo "astra: exit 0 and no final message. The run DID NOT RUN; retry it." >&2; return 4; }
  echo "astra: done in $(( $(date +%s) - started_at ))s -> ${last}"
}

selftest() {
  local dir; dir=$(mktemp -d); local fails=0
  local self; self=$(cd "$(dirname "$0")" && pwd)/$(basename "$0")
  mkdir -p "${dir}/wt"; echo "do the thing" > "${dir}/brief.md"
  stub() { printf '#!/usr/bin/env bash\n%s\n' "$1" > "${dir}/codex"; chmod +x "${dir}/codex"; }
  expect() { local want=$1 name=$2; shift 2
    ASTRA_CODEX="${dir}/codex" ASTRA_TICK=1 ASTRA_STARTUP=2 ASTRA_IDLE=3 CODEX_HOME="${dir}" "${self}" "$@" >/dev/null 2>&1; local got=$?
    if [ "${got}" = "${want}" ]; then echo "  ok   ${name}"; else echo "  FAIL ${name}: exit ${got}, wanted ${want}"; fails=$((fails+1)); return 1; fi; }
  local write_last='while [ $# -gt 0 ]; do [ "$1" = -o ] && out=$2; shift; done'
  stub "${write_last}; cat >/dev/null; echo '{\"type\":\"thread.started\",\"thread_id\":\"t1\"}'; echo done > \"\$out\""
  expect 0 "a run that finishes"            run "${dir}/wt" "${dir}/brief.md" "${dir}/o1"
  expect 0 "a fix round finds the thread"   fix "${dir}/wt" "${dir}/brief.md" "${dir}/o1"
  (cd "${dir}" && expect 0 "a fix round on relative paths" fix wt brief.md o1) || fails=$((fails+1))   # the subshell's own count is lost
  stub "cat >/dev/null; echo '{\"type\":\"thread.started\",\"thread_id\":\"t1\"}'"
  expect 4 "exit 0 with no final message"   run "${dir}/wt" "${dir}/brief.md" "${dir}/o2"
  stub "cat >/dev/null; sleep 30"
  expect 3 "died at startup"                run "${dir}/wt" "${dir}/brief.md" "${dir}/o3"
  stub "cat >/dev/null; echo '{\"type\":\"thread.started\",\"thread_id\":\"t1\"}'; sleep 30"
  expect 3 "went silent mid-run"            review "${dir}/wt" "${dir}/brief.md" "${dir}/o4"
  stub "cat >/dev/null; exit 7"
  expect 7 "codex's own failure passes through" run "${dir}/wt" "${dir}/brief.md" "${dir}/o5"
  expect 2 "a fix with no thread to resume" fix "${dir}/wt" "${dir}/brief.md" "${dir}/o6"
  : > "${dir}/empty.md"
  expect 2 "an empty brief"                 run "${dir}/wt" "${dir}/empty.md" "${dir}/o7"
  rm -rf "${dir}"; echo "astra self-test: $((9 - fails))/9"; [ "${fails}" = 0 ]
}

case "${1:-}" in
  --selftest) selftest ;;
  run|review|fix) [ $# -ge 4 ] || { sed -n '2,8p' "$0" >&2; exit 2; }; dispatch "$@" ;;
  *) sed -n '2,12p' "$0" >&2; exit 2 ;;
esac
