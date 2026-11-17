#!/bin/bash
# wait-load.sh [--settled] [<max seconds>]: returns once the 1-minute load average is under the
# core count, the bar contract.md's Red under load sets before a rerun and mac-vm.sh sets before a
# boot (app-look's VM failed to boot twice at load 117 to 146 on 18 cores, and booted at 16).
# --settled also wants the 5-minute average under one and a half times the cores, the bar before
# a landing script's gates: a suite started the moment the 1-minute figure dips pushes the load
# back up (cel-500's landing went red at a 5-minute 31 and 42 on 18 cores, and green at 26).
# Every ship used to write this loop itself. Prints the load as it waits, exit 1 when it is
# still over after <max seconds> (default 1800). Run it as a background Bash call.
# wait-load.sh --selftest
set -euo pipefail

cores=${WAIT_LOAD_CORES:-$(sysctl -n hw.ncpu 2>/dev/null || true)}
every=${WAIT_LOAD_EVERY:-30}
loads() {  # the 1- and 5-minute figures; WAIT_LOAD_SEQ is a file of them, a line per check, for the test
  if [ -n "${WAIT_LOAD_SEQ:-}" ]; then sed -n "${1}p" "$WAIT_LOAD_SEQ"
  else sysctl -n vm.loadavg 2>/dev/null | awk '{print $2, $3}'; fi
}
read_fail() { echo "wait-load: couldn't read the load (the sandbox blocks sysctl: run it with the sandbox off)" >&2; exit 2; }

wait_load() {
  local max=${1:-1800} waited=0 n=1 out l f num='^[0-9]+(\.[0-9]+)?$' five=
  while :; do
    out=$(loads "$n") || read_fail; n=$((n + 1))
    read -r l f _ <<<"$out"
    [[ "$l" =~ $num ]] || read_fail
    if [ "$settled" = 1 ]; then [[ "$f" =~ $num ]] || read_fail; five=", 5-minute $f"; fi
    if awk -v l="$l" -v f="${f:-0}" -v c="$cores" -v s="$settled" \
        'BEGIN { exit !(l + 0 < c + 0 && (!s || f + 0 < c * 1.5)) }'; then
      if [ "$settled" = 1 ]; then echo "load $l$five, settled on $cores cores"
      else echo "load $l, under $cores cores"; fi
      return 0
    fi
    [ "$waited" -lt "$max" ] || { echo "load still $l$five on $cores cores after ${max}s" >&2; return 1; }
    echo "waiting: load $l$five on $cores cores" >&2
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
  printf '\n' > "$t/seq"; rc=0
  WAIT_LOAD_SEQ=$t/seq WAIT_LOAD_CORES=18 WAIT_LOAD_EVERY=0 bash "$0" 5 2>/dev/null || rc=$?
  [ "$rc" = 2 ] || { echo "wait-load selftest: FAILED (an empty reading must not pass, rc $rc)"; return 1; }
  rc=0; bash "$0" 5x 2>/dev/null || rc=$?
  [ "$rc" = 2 ] || { echo "wait-load selftest: FAILED (a bad argument must be refused, rc $rc)"; return 1; }
  # --settled: cel-500's three starts, red at a 5-minute 42 and 31, green at 26
  printf '17.98 42.44 47.78\n17.73 30.68 45.13\n15.53 26.48 37.95\n' > "$t/seq"
  out=$(WAIT_LOAD_SEQ=$t/seq WAIT_LOAD_CORES=18 WAIT_LOAD_EVERY=0 bash "$0" --settled 60 2>/dev/null) || { echo "wait-load selftest: FAILED (--settled should pass once both figures fall)"; return 1; }
  [ "$out" = "load 15.53, 5-minute 26.48, settled on 18 cores" ] || { echo "wait-load selftest: FAILED (--settled said: $out)"; return 1; }
  out=$(WAIT_LOAD_SEQ=$t/seq WAIT_LOAD_CORES=18 WAIT_LOAD_EVERY=0 bash "$0" 60 2>/dev/null) || { echo "wait-load selftest: FAILED (without --settled the 5-minute figure must not count)"; return 1; }
  [ "$out" = "load 17.98, under 18 cores" ] || { echo "wait-load selftest: FAILED (without --settled said: $out)"; return 1; }
  printf '10 27\n' > "$t/seq"
  if WAIT_LOAD_SEQ=$t/seq WAIT_LOAD_CORES=18 WAIT_LOAD_EVERY=0 bash "$0" --settled 0 2>/dev/null; then
    echo "wait-load selftest: FAILED (a 5-minute load at one and a half times the cores is not under it)"; return 1
  fi
  printf '10\n' > "$t/seq"; rc=0
  WAIT_LOAD_SEQ=$t/seq WAIT_LOAD_CORES=18 WAIT_LOAD_EVERY=0 bash "$0" --settled 5 2>/dev/null || rc=$?
  [ "$rc" = 2 ] || { echo "wait-load selftest: FAILED (--settled with no 5-minute reading must not pass, rc $rc)"; return 1; }
  echo "wait-load selftest: ok"
}

settled=0
if [ "${1:-}" = --settled ]; then settled=1; shift; fi
case "${1:-}" in
  --selftest) selftest ;;
  *[!0-9]*) echo "usage: wait-load.sh [--settled] [<max seconds>] | --selftest" >&2; exit 2 ;;
  *) [[ "$cores" =~ ^[0-9]+$ ]] || read_fail; wait_load "${1:-1800}" ;;
esac
