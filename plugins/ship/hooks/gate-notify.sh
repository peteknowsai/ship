#!/bin/bash
# /ship gate notification — fires a desktop notification when a ship parks at a gate.
# Registered as a Stop hook (homezero/.claude/settings.json). Self-gates: does nothing
# unless .ship-stage at the git root holds a gate:* marker, so normal turns are silent.

root=$(git rev-parse --show-toplevel 2>/dev/null) || exit 0
stage_file="$root/.ship-stage"
[ -f "$stage_file" ] || exit 0
stage=$(head -1 "$stage_file" 2>/dev/null | tr -d ' \n')

case "$stage" in
  gate:1*) what="GATE 1 — design direction" ;;
  gate:2*) what="GATE 2 — go" ;;
  *) exit 0 ;;
esac

slug=$(git -C "$root" branch --show-current 2>/dev/null); slug="${slug#feature/}"
[ -z "$slug" ] && slug="ship"

# Prefer a Ghostty-native notification (OSC 777 to the controlling terminal). A bare
# `-w /dev/tty` test isn't enough — in a backgrounded session the device exists but the
# write fails ("Device not configured"), so actually attempt the write and fall back to
# a macOS notification on failure. That fallback is exactly the away-from-keyboard case.
if ! { printf '\033]777;notify;/ship;%s → %s\007' "$slug" "$what" > /dev/tty; } 2>/dev/null; then
  osascript -e "display notification \"${slug} → ${what}\" with title \"/ship\"" >/dev/null 2>&1
fi
exit 0
