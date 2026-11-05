#!/usr/bin/env bash
# Checks the statusline: ship detection (the marker, the cross-repo pointer),
# the worktree line, and the quota gauges. Seeds every cache so nothing hits the network.
# bash plugins/ship/statusline-test.sh
set -u
SL=$(cd "$(dirname "$0")" && pwd)/statusline.sh
T=$(mktemp -d); export HOME="$T/home"; mkdir -p "$HOME/.claude/ship-active"
trap 'rm -rf "$T"' EXIT
touch "$HOME/.claude/version-check.json"
g() { git -C "$1" -c user.name=t -c user.email=t@t "${@:2}"; }
git init -q -b main "$T/launch"; g "$T/launch" commit -q --allow-empty -m i
git init -q -b main "$T/target"; g "$T/target" commit -q --allow-empty -m i
g "$T/target" worktree add -q -b feature/thing "$T/target.thing"
fails=0
line1() { printf '{"session_id":"%s"}' "$1" | (cd "$2" && NO_COLOR=1 bash "$SL") | head -2 | tr '\n' ' '; }
expect() { local name=$1 want=$2 got=$3
  case "$got" in *"$want"*) echo "  ok   $name" ;; *) echo "  FAIL $name: got '$got', wanted '$want'"; fails=$((fails+1)) ;; esac; }
refuse() { local name=$1 bad=$2 got=$3
  case "$got" in *"$bad"*) echo "  FAIL $name: got '$got', must not contain '$bad'"; fails=$((fails+1)) ;; *) echo "  ok   $name" ;; esac; }

# ---- ship stages ----
echo 'review' > "$T/target.thing/.ship-stage"
expect "review has its own stage"  "build · review · test" "$(line1 s0 "$T/target.thing")"
echo 'gate:1' > "$T/target.thing/.ship-stage"
expect "storyboard gate"           "thing — storyboard?" "$(line1 s0 "$T/target.thing")"
echo 'test' > "$T/target.thing/.ship-stage"
expect "ship at work on test"      "thing — testing" "$(line1 s0 "$T/target.thing")"
echo 'gate:test' > "$T/target.thing/.ship-stage"
expect "parked for Pete's test"    "thing — try it, then merge main?" "$(line1 s0 "$T/target.thing")"
echo 'gate:input' > "$T/target.thing/.ship-stage"
expect "a needs-input stop"        "thing — needs you" "$(line1 s0 "$T/target.thing")"
echo 'land' > "$T/target.thing/.ship-stage"
expect "ship landing lights land"  "test · land" "$(line1 s0 "$T/target.thing")"
echo 'build:2:5' > "$T/target.thing/.ship-stage"
expect "ships in flight counted"   "🚢 1" "$(line1 s0 "$T/target")"
refuse "nobody waiting, no hand"   "wait on you" "$(line1 s0 "$T/target")"
g "$T/target" worktree add -q -b feature/w1 "$T/target.w1"; g "$T/target" worktree add -q -b feature/w2 "$T/target.w2"
echo 'gate:input' > "$T/target.w1/.ship-stage"; touch -t "$(date -v-1d +%Y%m%d%H%M)" "$T/target.w1/.ship-stage"
echo 'gate:2' > "$T/target.w2/.ship-stage"; touch -t "$(date -v-19d +%Y%m%d%H%M)" "$T/target.w2/.ship-stage"
expect "ships waiting on Pete"     "🚢 3  ✋ 2 wait on you · oldest 19d" "$(line1 s0 "$T/target")"
echo 'gate:2' > "$T/target.w1/.ship-stage"; rm "$T/target.w2/.ship-stage"
expect "a fresh wait reads in hours" "✋ 1 wait on you · oldest 0h" "$(line1 s0 "$T/target")"
rm "$T/target.w1/.ship-stage"
echo "$T/target.thing" > "$HOME/.claude/ship-active/s1"
expect "cross-repo pointer"        "🚢 thing" "$(line1 s1 "$T/launch")"
rm "$T/target.thing/.ship-stage"
expect "pointer after teardown"    "📁 launch" "$(line1 s1 "$T/launch")"
[ -f "$HOME/.claude/ship-active/s1" ] && { echo "  FAIL stale pointer not removed"; fails=$((fails+1)); } || echo "  ok   stale pointer removed"

# ---- worktree line ----
expect "main checkout on main"     "📁 target  main" "$(line1 s0 "$T/target")"
expect "linked worktree marked"    "🌳 target ⎇ thing" "$(line1 s0 "$T/target.thing")"
g "$T/target" worktree add -q --detach "$T/target.det"
expect "detached shows its sha"    "🌳 target ⎇ @" "$(line1 s0 "$T/target.det")"
g "$T/launch" checkout -q -b feature/oops
expect "main checkout off main"    "📁 launch  ⚠ feature/oops" "$(line1 s0 "$T/launch")"

# ---- quota gauges ----
iso() { date -u -r $(( $(date +%s) + $1 )) +%Y-%m-%dT%H:%M:%S.000000+00:00; }
quota() { # O F reset_s
  cat > "$HOME/.claude/usage-cache.json" <<J
{"seven_day":{"utilization":$1,"resets_at":"$(iso $3)"},"limits":[{"kind":"weekly_all","percent":$1},
 {"kind":"weekly_scoped","percent":$2,"resets_at":"$(iso $3)","scope":{"model":{"display_name":"Fable"}}}]}
J
}
line2() { printf '{"model":{"display_name":"Opus 5.5"},"effort":{"level":"%s"}}' "${1:-high}" | (cd "$T" && NO_COLOR=1 bash "$SL") | tail -1; }
quota 1 1 435600
expect "O and F, one reset"        "O 1% · F 1% ↻5d" "$(line2)"
refuse "no Codex gauge"            "│" "$(line2)"
expect "effort after model"        "🤖 Opus 5.5  ⚡high  🧠" "$(line2)"
expect "xhigh reads as xhigh"  "⚡xhigh" "$(line2 xhigh)"
quota 40 81 70000
expect "hotter bucket's reset"     "F 81% ↻19h" "$(line2)"
refuse "fresh cache carries no ?"  "?" "$(line2)"
touch -t 202001010000 "$HOME/.claude/usage-cache.json"
expect "stale cache gets a ?"      "↻19h?" "$(line2)"

ctx() { printf '{"model":{"display_name":"Opus 5.5"},"context_window":{"used_percentage":35,"total_input_tokens":350000,"context_window_size":1000000}}' | (cd "$T" && NO_COLOR=1 bash "$SL") | tail -1; }
expect "no compact setting: share of the window" "🧠 35%" "$(ctx)"
echo '{"autoCompactWindow":400000}' > "$HOME/.claude/settings.json"
expect "a 400k compact point: share of it"     "🧠 87%" "$(ctx)"
echo '{"autoCompactWindow":"auto"}' > "$HOME/.claude/settings.json"
expect "auto falls back to the window"         "🧠 35%" "$(ctx)"
rm "$HOME/.claude/settings.json"

echo "statusline test: $fails failed"; [ "$fails" = 0 ]
