#!/usr/bin/env bash
# Checks the statusline's ship detection: both marker formats, and the cross-repo pointer.
# bash plugins/ship/statusline-test.sh
set -u
SL=$(cd "$(dirname "$0")" && pwd)/statusline.sh
T=$(mktemp -d); export HOME="$T/home"; mkdir -p "$HOME/.claude/ship-active"
trap 'rm -rf "$T"' EXIT
g() { git -C "$1" -c user.name=t -c user.email=t@t "${@:2}"; }
git init -q "$T/launch"; g "$T/launch" commit -q --allow-empty -m i
git init -q "$T/target"; g "$T/target" commit -q --allow-empty -m i
g "$T/target" worktree add -q -b codex/thing "$T/target.thing"
fails=0
line1() { printf '{"session_id":"%s"}' "$1" | (cd "$2" && NO_COLOR=1 bash "$SL") | head -2 | tr '\n' ' '; }
expect() { local name=$1 want=$2 got=$3
  case "$got" in *"$want"*) echo "  ok   $name" ;; *) echo "  FAIL $name: got '$got', wanted '$want'"; fails=$((fails+1)) ;; esac; }

printf 'REVIEW\nbranch: x\n' > "$T/target.thing/.ship-stage"
expect "codex bare word on line 1" "build · test" "$(line1 s0 "$T/target.thing")"
printf 'stage: gate:1\nbranch: x\n' > "$T/target.thing/.ship-stage"
expect "codex stage key"           "thing — storyboard?" "$(line1 s0 "$T/target.thing")"
echo 'test' > "$T/target.thing/.ship-stage"
expect "parked for Pete's test"    "thing — test it, then merge main?" "$(line1 s0 "$T/target.thing")"
echo 'build:2:5' > "$T/target.thing/.ship-stage"
echo "$T/target.thing" > "$HOME/.claude/ship-active/s1"
expect "cross-repo pointer"        "🚢 thing" "$(line1 s1 "$T/launch")"
rm "$T/target.thing/.ship-stage"
expect "pointer after teardown"    "📁 launch" "$(line1 s1 "$T/launch")"
[ -f "$HOME/.claude/ship-active/s1" ] && { echo "  FAIL stale pointer not removed"; fails=$((fails+1)); } || echo "  ok   stale pointer removed"
echo "statusline test: $fails failed"; [ "$fails" = 0 ]
