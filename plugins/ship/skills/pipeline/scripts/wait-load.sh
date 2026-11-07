#!/bin/bash
# wait-load.sh [<max seconds>]: returns once the 1-minute load average is under the core count,
# the bar contract.md's Red under load sets before a rerun and mac-vm.sh sets before a boot
# (app-look's VM failed to boot twice at load 117 to 146 on 18 cores, and booted at 16).
# Every ship used to write this loop itself. Prints the load as it waits, exit 1 when it is
# still over after <max seconds> (default 1800). Run it as a background Bash call.
# wait-load.sh --selftest
set -euo pipefail

cores=${WAIT_LOAD_CORES:-$(sysctl -n hw.ncpu)}
every=${WAIT_LOAD_EVERY:-30}
load1() {  # the 1-minute figure; WAIT_LOAD_SEQ is a file of figures, one per check, for the test
  if [ -n "${WAIT_LOAD_SEQ:-}" ]; then sed -n "${1}p" "$WAIT_LOAD_SEQ"
  else sysctl -n vm.loadavg | awk '{print $2}'; fi
}

wait_load() {
  local max=${1:-1800} waited=0 n=1 l
  while :; do
    l=$(load1 "$n"); n=$((n + 1))
    if awk -v l="$l" -v c="$cores" 'BEGIN { exit !(l + 0 < c + 0) }'; then
      echo "load $l, under $cores cores"; return 0
    fi
    [ "$waited" -lt "$max" ] || { echo "load still $l on $cores cores after ${max}s" >&2; return 1; }
    echo "waiting: load $l on $cores cores" >&2
    sleep "$every"; waited=$((waited + every))
  done
}

selftest() {
  local t; t=$(mktemp -d); trap 'rm -rf "$t"' RETURN
  printf '146\n117\n16\n' > "$t/seq"
  out=$(WAIT_LOAD_SEQ=$t/seq WAIT_LOAD_CORES=18 WAIT_LOAD_EVERY=0 bash "$0" 60 2>/dev/null) || { echo "wait-load selftest: FAILED (a falling load should pass)"; return 1; }
  [ "$out" = "load 16, under 18 cores" ] || { echo "wait-load selftest: FAILED (said: $out)"; return 1; }
  printf '90\n90\n90\n' > "$t/seq"
  if WAIT_LOAD_SEQ=$t/seq WAIT_LOAD_CORES=18 WAIT_LOAD_EVERY=1 bash "$0" 1 2>/dev/null; then
    echo "wait-load selftest: FAILED (a load that stays high should time out)"; return 1
  fi
  printf '18\n' > "$t/seq"
  if WAIT_LOAD_SEQ=$t/seq WAIT_LOAD_CORES=18 WAIT_LOAD_EVERY=0 bash "$0" 0 2>/dev/null; then
    echo "wait-load selftest: FAILED (a load equal to the cores is not under them)"; return 1
  fi
  echo "wait-load selftest: ok"
}

case "${1:-}" in
  --selftest) selftest ;;
  ''|[0-9]*) wait_load "${1:-1800}" ;;
  *) echo "usage: wait-load.sh [<max seconds>] | --selftest" >&2; exit 2 ;;
esac
