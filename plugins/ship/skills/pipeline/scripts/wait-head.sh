#!/bin/bash
# wait-head.sh <owner/repo> <pr> [<max seconds>]: run from the worktree after a push; returns
# once GitHub's head for the PR is this worktree's HEAD. Right after a push it can still show
# the old head, and a check or land script reading it then gets a stale answer (#492 lost a
# queue turn to a 0 s "conflicts with main"). Reads over REST, which sibling ships exhaust
# last (incidents: GitHub). Exit 1 still stale after <max seconds> (default 120), 2 when it
# can't ask. Every ship used to write this loop itself. wait-head.sh --selftest
set -euo pipefail

every=${WAIT_HEAD_EVERY:-5}
self=$(cd "$(dirname "$0")" && pwd)/$(basename "$0")

wait_head() {
  local repo=$1 pr=$2 max=${3:-120} want got waited=0
  want=$(git rev-parse HEAD) || exit 2
  while :; do
    got=$(gh api "repos/$repo/pulls/$pr" -q .head.sha 2>/dev/null) || { echo "wait-head: gh api failed for $repo#$pr (sandbox off?)" >&2; exit 2; }
    [ "$got" = "$want" ] && { echo "GitHub's head for #$pr is ${want:0:9}"; return 0; }
    [ "$waited" -lt "$max" ] || { echo "GitHub still shows ${got:0:9} for #$pr after ${max}s, not ${want:0:9}" >&2; return 1; }
    sleep "$every"; waited=$((waited + every))
  done
}

selftest() {
  local t; t=$(mktemp -d); trap 'rm -rf "$t"' RETURN
  git init -q "$t/w" && git -C "$t/w" -c user.email=t@t -c user.name=t commit -q --allow-empty -m a
  local head; head=$(git -C "$t/w" rev-parse HEAD)
  mkdir "$t/bin"
  # A fake gh: the head only for `api repos/o/r/pulls/7 -q .head.sha`, stale for the first
  # $STALE asks, and failing past 10 so a loop that never ends fails rather than hangs.
  printf '#!/bin/sh\nn=$(cat %s/n 2>/dev/null || echo 0); n=$((n + 1)); echo $n > %s/n\n[ $n -le 10 ] || exit 3\n[ "$*" = "api repos/o/r/pulls/7 -q .head.sha" ] || exit 1\n[ $n -le "$STALE" ] && echo 0000000000 || echo %s\n' "$t" "$t" "$head" > "$t/bin/gh"
  chmod +x "$t/bin/gh"
  run() { (cd "$t/w" && PATH="$t/bin:$PATH" WAIT_HEAD_EVERY=1 bash "$self" "$@"); }
  out=$(STALE=2 run o/r 7 5 2>&1) || { echo "wait-head selftest: FAILED (a head that catches up should pass: $out)"; return 1; }
  [ "$(cat "$t/n")" = 3 ] || { echo "wait-head selftest: FAILED (asked $(cat "$t/n") times, want 3)"; return 1; }
  echo 0 > "$t/n"; rc=0; STALE=99 run o/r 7 2 >/dev/null 2>&1 || rc=$?
  [ "$rc" = 1 ] && [ "$(cat "$t/n")" = 3 ] || { echo "wait-head selftest: FAILED (a stale head should exit 1 after 3 asks in 2 s, got $rc after $(cat "$t/n"))"; return 1; }
  echo 0 > "$t/n"
  rc=0; STALE=0 run o/r 8 10 >/dev/null 2>&1 || rc=$?
  [ "$rc" = 2 ] || { echo "wait-head selftest: FAILED (a failed ask should exit 2, got $rc)"; return 1; }
  echo "wait-head selftest: ok"
}

case "${1:-}" in
  --selftest) selftest ;;
  */*) [[ "${2:-}" =~ ^[0-9]+$ && "${3:-120}" =~ ^[0-9]+$ ]] || { echo "usage: wait-head.sh <owner/repo> <pr> [<max seconds>]" >&2; exit 2; }
       wait_head "$@" ;;
  *) echo "usage: wait-head.sh <owner/repo> <pr> [<max seconds>] | --selftest" >&2; exit 2 ;;
esac
