#!/usr/bin/env bash
# TEST's headless tester: Astra through `codex exec`, with the three guards bare exec lacks.
#
#   astra.sh test   <worktree> <brief.md> <out-dir> [effort]   read-only, drives the app
#                                                             in a browser and on iOS
#   astra.sh --selftest
#
# Codex left BUILD on 2026-10-01, and the run/review/fix modes went with it (2026-10-05).
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
# the `exec review` that hit a skill-loading error and wrote nothing.
set -u
MODEL=${ASTRA_MODEL:-gpt-6-astra}
CODEX=${ASTRA_CODEX:-codex}
STARTUP=${ASTRA_STARTUP:-45}
IDLE=${ASTRA_IDLE:-900}
TICK=${ASTRA_TICK:-5}

mtime() { stat -f %m "$1" 2>/dev/null || stat -c %Y "$1"; }

# The user's MCP servers are half a second of startup each and tools a tester should
# never reach for, so all but TESTER_MCP go off per run, config untouched. Those two are
# pre-approved: under exec's approval policy "never", an unapproved MCP call is refused,
# not asked (2026-10-01).
TESTER_MCP="chrome-devtools agent-device"
# chrome-devtools writes files only inside its MCP roots, and exec negotiates none, so the
# server falls back to the OS temp dir and refuses the worktree and the out-dir (retro #129).
# The tester relaunches it headless, as the Claude side runs it, with those two as roots.
tester_browser() { # <worktree> <out-dir>
  printf -- '-c\nmcp_servers.chrome-devtools.args=["chrome-devtools-mcp@latest","--isolated=true","--headless=true","--workspace=%s","--workspace=%s"]\n' "$1" "$2"
}
mcp_off() { # [servers to keep]
  local config="${CODEX_HOME:-$HOME/.codex}/config.toml"
  [ -f "${config}" ] || return 0
  sed -n 's/^\[mcp_servers\.\([A-Za-z0-9_-]*\)\]$/\1/p' "${config}" | sort -u |
    while read -r name; do
      case " ${1:-} " in
        *" ${name} "*) printf -- '-c\nmcp_servers.%s.default_tools_approval_mode="approve"\n' "${name}" ;;
        *) printf -- '-c\nmcp_servers.%s.enabled=false\n' "${name}" ;;
      esac
    done
}

dispatch() {
  local worktree=$2 brief=$3 out=$4 effort=${5:-high}
  [ -d "${worktree}" ] || { echo "astra: no worktree at ${worktree}" >&2; return 2; }
  [ -s "${brief}" ] || { echo "astra: brief ${brief} is missing or empty" >&2; return 2; }
  mkdir -p "${out}"; out=$(cd "${out}" && pwd); worktree=$(cd "${worktree}" && pwd)
  local events="${out}/events.jsonl" last="${out}/last.md"
  local -a common=(-m "${MODEL}" -c "model_reasoning_effort=${effort}" --json -o "${last}")
  local line; while read -r line; do common+=("${line}"); done < <(mcp_off "${TESTER_MCP}")
  while read -r line; do common+=("${line}"); done < <(tester_browser "${worktree}" "${out}")
  brief=$(cd "$(dirname "${brief}")" && pwd)/$(basename "${brief}")
  rm -f "${last}"
  local started_at; started_at=$(date +%s)
  : > "${events}"; "${CODEX}" exec -C "${worktree}" -s read-only "${common[@]}" - < "${brief}" >> "${events}" 2> "${out}/stderr.txt" &
  local pid=$! now seen_start=0
  while kill -0 "${pid}" 2>/dev/null; do
    sleep "${TICK}"; now=$(date +%s)
    [ "${seen_start}" = 0 ] && grep -q '"thread.started"' "${events}" 2>/dev/null && seen_start=1
    if [ "${seen_start}" = 0 ] && [ $((now - started_at)) -ge "${STARTUP}" ]; then
      kill "${pid}" 2>/dev/null; echo "astra: no thread.started after ${STARTUP}s; died at startup. See ${out}/stderr.txt" >&2; return 3
    fi
    if [ $((now - $(mtime "${events}"))) -ge "${IDLE}" ]; then
      kill "${pid}" 2>/dev/null; echo "astra: no event for ${IDLE}s; the run went silent; run a fresh tester" >&2; return 3
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
  expect 0 "a run that finishes"            test "${dir}/wt" "${dir}/brief.md" "${dir}/o1"
  (cd "${dir}" && expect 0 "a run on relative paths" test wt brief.md o1) || fails=$((fails+1))   # the subshell's own count is lost
  stub "cat >/dev/null; echo '{\"type\":\"thread.started\",\"thread_id\":\"t1\"}'"
  expect 4 "exit 0 with no final message"   test "${dir}/wt" "${dir}/brief.md" "${dir}/o2"
  stub "cat >/dev/null; sleep 30"
  expect 3 "died at startup"                test "${dir}/wt" "${dir}/brief.md" "${dir}/o3"
  stub "cat >/dev/null; echo '{\"type\":\"thread.started\",\"thread_id\":\"t1\"}'; sleep 30"
  expect 3 "went silent mid-run"            test "${dir}/wt" "${dir}/brief.md" "${dir}/o4"
  stub "cat >/dev/null; exit 7"
  expect 7 "codex's own failure passes through" test "${dir}/wt" "${dir}/brief.md" "${dir}/o5"
  expect 2 "the retired build modes are refused" run "${dir}/wt" "${dir}/brief.md" "${dir}/o6"
  : > "${dir}/empty.md"
  expect 2 "an empty brief"                 test "${dir}/wt" "${dir}/empty.md" "${dir}/o7"
  printf '[mcp_servers.agent-device]\n[mcp_servers.node_repl]\n' > "${dir}/config.toml"
  stub "echo \"\$*\" > ${dir}/args; ${write_last}; cat >/dev/null; echo '{\"type\":\"thread.started\",\"thread_id\":\"t1\"}'; echo done > \"\$out\""
  expect 0 "a test run finishes"            test "${dir}/wt" "${dir}/brief.md" "${dir}/o8"
  if grep -q -- '-s read-only' "${dir}/args" && grep -q 'agent-device.default_tools_approval_mode="approve"' "${dir}/args" &&
     grep -q 'node_repl.enabled=false' "${dir}/args" && ! grep -q 'agent-device.enabled=false' "${dir}/args" &&
     grep -q -- "--headless=true\",\"--workspace=${dir}/wt\",\"--workspace=${dir}/o8\"" "${dir}/args"; then
    echo "  ok   a test run is read-only, only the tester's servers on and pre-approved, its browser headless and rooted in the worktree and out-dir"
  else echo "  FAIL a test run's flags: $(cat "${dir}/args")"; fails=$((fails+1)); fi
  rm -rf "${dir}"; echo "astra self-test: $((10 - fails))/10"; [ "${fails}" = 0 ]
}

case "${1:-}" in
  --selftest) selftest ;;
  test) [ $# -ge 4 ] || { sed -n '2,8p' "$0" >&2; exit 2; }; dispatch "$@" ;;
  *) sed -n '2,8p' "$0" >&2; exit 2 ;;
esac
