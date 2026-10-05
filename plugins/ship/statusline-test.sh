#!/usr/bin/env bash
# Checks the statusline: ship detection (both marker formats, the cross-repo pointer),
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
g "$T/target" worktree add -q -b codex/thing "$T/target.thing"
fails=0
line1() { printf '{"session_id":"%s"}' "$1" | (cd "$2" && NO_COLOR=1 bash "$SL") | head -2 | tr '\n' ' '; }
expect() { local name=$1 want=$2 got=$3
  case "$got" in *"$want"*) echo "  ok   $name" ;; *) echo "  FAIL $name: got '$got', wanted '$want'"; fails=$((fails+1)) ;; esac; }
refuse() { local name=$1 bad=$2 got=$3
  case "$got" in *"$bad"*) echo "  FAIL $name: got '$got', must not contain '$bad'"; fails=$((fails+1)) ;; *) echo "  ok   $name" ;; esac; }

# ---- ship stages ----
printf 'REVIEW\nbranch: x\n' > "$T/target.thing/.ship-stage"
expect "codex bare word on line 1" "build · test" "$(line1 s0 "$T/target.thing")"
printf 'stage: gate:1\nbranch: x\n' > "$T/target.thing/.ship-stage"
expect "codex stage key"           "thing — storyboard?" "$(line1 s0 "$T/target.thing")"
echo 'test' > "$T/target.thing/.ship-stage"
expect "codex at work on test"     "thing — codex testing" "$(line1 s0 "$T/target.thing")"
echo 'gate:test' > "$T/target.thing/.ship-stage"
expect "parked for Pete's test"    "thing — try it, then merge main?" "$(line1 s0 "$T/target.thing")"
echo 'build:2:5' > "$T/target.thing/.ship-stage"
expect "ships in flight counted"   "🚢 1" "$(line1 s0 "$T/target")"
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
quota() { # O F codex% anthropic_reset_s codex_reset_s [credits]
  cat > "$HOME/.claude/usage-cache.json" <<J
{"seven_day":{"utilization":$1,"resets_at":"$(iso $4)"},"limits":[{"kind":"weekly_all","percent":$1},
 {"kind":"weekly_scoped","percent":$2,"resets_at":"$(iso $4)","scope":{"model":{"display_name":"Fable"}}}]}
J
  cat > "$HOME/.claude/codex-usage-cache.json" <<J
{"rate_limit":{"limit_reached":false,"primary_window":{"used_percent":$3,"reset_at":$(( $(date +%s) + $5 ))}},
 "credits":{"has_credits":true,"balance":"${6:-58468.40}"}}
J
}
line2() { printf '{"model":{"display_name":"Opus 5.5"},"effort":{"level":"%s"}}' "${1:-high}" | (cd "$T" && NO_COLOR=1 bash "$SL") | tail -1; }
quota 1 1 12 435600 522000
expect "both vendors, own resets"  "O 1% · F 1% ↻5d │ C 12% ↻6d" "$(line2)"
expect "effort after model"        "🤖 Opus 5.5  ⚡high  🧠" "$(line2)"
expect "xhigh is the ultra badge"  "⚡⚡⚡ultra" "$(line2 xhigh)"
quota 40 81 12 70000 522000
expect "hotter bucket's reset"     "F 81% ↻19h" "$(line2)"
quota 1 1 99 435600 361862
expect "under 100%: percent only"  "C 99% ↻4d" "$(line2)"
quota 1 1 100 435600 361862
expect "spent with credits: balance" "C 58k ↻4d" "$(line2)"
quota 1 1 100 435600 361862 0.00
expect "spent, no credits: 100%"   "C 100% ↻4d" "$(line2)"
line2c() { printf '{"model":{"display_name":"Opus 5.5"}}' | (cd "$T" && bash "$SL") | tail -1; }
green=$'\e[38;5;158m'; red=$'\e[38;5;203m'
quota 1 1 100 435600 361862
expect "healthy balance is green"  "${green}C 58k" "$(line2c)"
quota 1 1 100 435600 361862 9500
expect "balance under 10k is red"  "${red}C 9k" "$(line2c)"
quota 1 1 100 435600 361862 0.00
refuse "fresh caches carry no ?"   "?" "$(line2)"
touch -t 202001010000 "$HOME/.claude/usage-cache.json" "$HOME/.claude/codex-usage-cache.json"
expect "stale caches get a ?"      "↻5d? │ C 100% ↻4d?" "$(line2)"

echo "statusline test: $fails failed"; [ "$fails" = 0 ]
