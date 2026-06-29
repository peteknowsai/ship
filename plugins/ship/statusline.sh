#!/bin/bash
# Mr StatusLine — Claude Code statusline
# Distilled to what Pete acts on: which ship · does it need me · context · week quota.
# Worktree = the ship slug. /ship writes .ship-stage at the git root.

input=$(cat)

# ---- detect jq ----
HAS_JQ=0
command -v jq >/dev/null 2>&1 && HAS_JQ=1

# ---- color helpers ----
use_color=1
[ -n "$NO_COLOR" ] && use_color=0
c() { [ "$use_color" -eq 1 ] && printf '\033[%sm' "$1"; }
rst() { [ "$use_color" -eq 1 ] && printf '\033[0m'; }

dir_color()  { c '38;5;117'; }   # sky blue
branch_c()   { c '38;5;150'; }   # green
ship_c()     { c '38;5;80';  }   # cyan — the ship
phase_c()    { c '38;5;245'; }   # dim gray — the phase word
gate_c()     { c '1;38;5;214'; } # bold amber — needs you
update_c()   { c '38;5;179'; }   # muted gold

# ---- extract data ----
if [ "$HAS_JQ" -eq 1 ]; then
  current_dir=$(echo "$input" | jq -r '.workspace.current_dir // .cwd // "~"' 2>/dev/null | sed "s|^$HOME|~|g")
  cc_version=$(echo "$input" | jq -r '.version // ""' 2>/dev/null)
  effort=$(echo "$input" | jq -r '.effort.level // ""' 2>/dev/null)
  context_pct=$(echo "$input" | jq -r '.context_window.used_percentage // 0' 2>/dev/null)
  context_pct=$(printf "%.0f" "$context_pct" 2>/dev/null)
else
  current_dir="~"; cc_version=""; effort=""; context_pct=0
fi

# ---- git: branch only (the slug / fallback identity) ----
git_branch=""
git_root=""
wt_count=0
repo_name=$(basename "$current_dir")
if git rev-parse --git-dir >/dev/null 2>&1; then
  git_branch=$(git branch --show-current 2>/dev/null || git rev-parse --short HEAD 2>/dev/null)
  git_root=$(git rev-parse --show-toplevel 2>/dev/null)
  wt_list=$(git worktree list 2>/dev/null)
  # ships in flight = linked worktrees (total minus the main checkout)
  wt_count=$(printf '%s\n' "$wt_list" | grep -c .)
  wt_count=$((wt_count - 1)); [ "$wt_count" -lt 0 ] && wt_count=0
  # canonical repo name = basename of the main (first) worktree, so a worktree shows
  # "homezero", not the long redundant "homezero.feature-x"
  main_wt=$(printf '%s\n' "$wt_list" | head -1 | awk '{print $1}')
  [ -n "$main_wt" ] && repo_name=$(basename "$main_wt")
fi

# ---- ship stage (worktree pipeline marker written by /ship) ----
ship_stage=""
[ -n "$git_root" ] && [ -f "$git_root/.ship-stage" ] && \
  ship_stage=$(head -1 "$git_root/.ship-stage" 2>/dev/null | tr -d ' \n')
ship_slug="${git_branch#feature/}"

# ---- weekly Max usage (cached; OAuth token from Keychain) ----
weekly_pct=""
weekly_resets=""
usage_cache="$HOME/.claude/usage-cache.json"
cache_stale=1
if [ -f "$usage_cache" ]; then
  cache_age=$(($(date +%s) - $(stat -f %m "$usage_cache" 2>/dev/null || echo 0)))
  [ "$cache_age" -lt 300 ] && cache_stale=0
fi
if [ "$cache_stale" -eq 1 ] && [ "$HAS_JQ" -eq 1 ]; then
  access_token=$(security find-generic-password -s "Claude Code-credentials" -w 2>/dev/null | jq -r '.claudeAiOauth.accessToken // empty' 2>/dev/null)
  if [ -n "$access_token" ]; then
    fresh_data=$(curl -s --max-time 2 "https://api.anthropic.com/api/oauth/usage" \
      -H "Authorization: Bearer $access_token" \
      -H "anthropic-beta: oauth-2025-04-20" \
      -H "Accept: application/json" 2>/dev/null)
    echo "$fresh_data" | jq -e '.seven_day' >/dev/null 2>&1 && echo "$fresh_data" > "$usage_cache"
  fi
fi
if [ -f "$usage_cache" ] && [ "$HAS_JQ" -eq 1 ]; then
  weekly_val=$(jq -r '.seven_day.utilization // empty' "$usage_cache" 2>/dev/null)
  [ -n "$weekly_val" ] && [ "$weekly_val" != "null" ] && weekly_pct=$(printf "%.0f" "$weekly_val" 2>/dev/null)
  weekly_resets=$(jq -r '.seven_day.resets_at // empty' "$usage_cache" 2>/dev/null)
fi

# ---- update available? (cached 30m; render only when actually behind) ----
update_available=""
vc_cache="$HOME/.claude/version-check.json"
vc_stale=1
if [ -f "$vc_cache" ]; then
  vc_age=$(($(date +%s) - $(stat -f %m "$vc_cache" 2>/dev/null || echo 0)))
  [ "$vc_age" -lt 1800 ] && vc_stale=0
fi
if [ "$vc_stale" -eq 1 ] && [ "$HAS_JQ" -eq 1 ]; then
  latest=$(curl -s --max-time 2 "https://registry.npmjs.org/@anthropic-ai/claude-code/latest" 2>/dev/null | jq -r '.version // empty' 2>/dev/null)
  [ -n "$latest" ] && printf '{"latest":"%s"}' "$latest" > "$vc_cache"
fi
if [ -f "$vc_cache" ] && [ "$HAS_JQ" -eq 1 ] && [ -n "$cc_version" ]; then
  latest=$(jq -r '.latest // empty' "$vc_cache" 2>/dev/null)
  if [ -n "$latest" ] && [ "$latest" != "$cc_version" ]; then
    newest=$(printf '%s\n%s\n' "$cc_version" "$latest" | sort -V | tail -1)
    [ "$newest" = "$latest" ] && update_available="$latest"
  fi
fi

# ---- reset time formatter (only used when week >= 50%) ----
format_reset() {
  local iso_ts="$1"; [ -z "$iso_ts" ] && return
  local stripped=$(echo "$iso_ts" | sed 's/\.[^+Z]*//; s/+.*//; s/Z//')
  local reset_epoch=$(TZ=UTC date -jf "%Y-%m-%dT%H:%M:%S" "$stripped" "+%s" 2>/dev/null)
  [ -z "$reset_epoch" ] && return
  local diff=$(( reset_epoch - $(date +%s) ))
  [ "$diff" -le 0 ] && printf "now" && return
  if [ "$diff" -lt 3600 ]; then
    printf "%dm" $((diff / 60))
  elif [ "$diff" -lt 86400 ]; then
    local h=$((diff / 3600)); local m=$(((diff % 3600) / 60))
    [ "$m" -gt 0 ] && printf "%dh%dm" "$h" "$m" || printf "%dh" "$h"
  else
    local local_ts=$(date -r "$reset_epoch" "+%a %-I:%M%p" 2>/dev/null | tr '[:upper:]' '[:lower:]')
    local day=$(echo "$local_ts" | awk '{print $1}')
    local hour=$(echo "$local_ts" | awk '{print $2}' | sed 's/m$//')
    day="$(echo "${day:0:1}" | tr '[:lower:]' '[:upper:]')${day:1}"
    printf "%s %s" "$day" "$hour"
  fi
}

# ---- value-based colors ----
context_color() {
  if [ "${context_pct:-0}" -ge 80 ]; then c '38;5;203'    # red
  elif [ "${context_pct:-0}" -ge 60 ]; then c '38;5;215'  # orange
  else c '38;5;158'; fi                                    # green
}
weekly_color() {
  if [ "${weekly_pct:-0}" -ge 80 ]; then c '38;5;203'
  elif [ "${weekly_pct:-0}" -ge 50 ]; then c '38;5;215'
  else c '38;5;158'; fi
}

# ============================ render ============================
# Line 1 — identity only: which ship (or repo·branch) + ships-in-flight count.
# Phase moves to line 2 to keep this short.
is_gate=0; phase=""
if [ -n "$ship_stage" ]; then
  case "$ship_stage" in
    gate:1*) printf "$(gate_c)✋ %s — design?$(rst)" "$ship_slug"; is_gate=1 ;;
    gate:2*) printf "$(gate_c)✋ %s — go?$(rst)" "$ship_slug"; is_gate=1 ;;
    discover*) printf "$(ship_c)🚢 %s$(rst)" "$ship_slug"; phase="🔍 designing" ;;
    plan*)     printf "$(ship_c)🚢 %s$(rst)" "$ship_slug"; phase="📐 planning" ;;
    build*)    printf "$(ship_c)🚢 %s$(rst)" "$ship_slug"; phase="🔨 building" ;;
    review*)   printf "$(ship_c)🚢 %s$(rst)" "$ship_slug"; phase="👀 reviewing" ;;
    *)         printf "$(ship_c)🚢 %s$(rst)" "$ship_slug" ;;
  esac
else
  printf "$(dir_color)📁 %s$(rst)" "$repo_name"
  [ -n "$git_branch" ] && printf "  $(branch_c)🌿 %s$(rst)" "$git_branch"
fi
# ships-in-flight count (linked worktrees) — orientation; hidden at a gate
if [ "$is_gate" -eq 0 ] && [ "${wt_count:-0}" -ge 1 ]; then
  printf "  $(c '38;5;108')🌳 %d$(rst)" "$wt_count"
fi
printf "\n"

# Line 2 — phase (when in a ship), then the gauges + effort.
[ -n "$phase" ] && printf "$(phase_c)%s$(rst)  " "$phase"
printf "$(context_color)🧠 %d%%$(rst)" "${context_pct:-0}"
if [ -n "$weekly_pct" ]; then
  printf "  $(weekly_color)📊 %d%%$(rst)" "$weekly_pct"
  if [ "${weekly_pct:-0}" -ge 50 ]; then
    rs=$(format_reset "$weekly_resets")
    [ -n "$rs" ] && printf " $(c '38;5;245')↻ %s$(rst)" "$rs"
  fi
fi
# effort — reasoning tier. The harness exposes no real ultracode bit (it reports as
# xhigh, same as plain extra-high). Pete never uses plain xhigh on Opus, so for him
# xhigh ≡ ultracode — render it as the ultra badge: three rainbow ⚡. Other tiers plain.
# ponytail: xhigh==ultracode is a deliberate convention, not detection — the only honest
# proxy available. If plain xhigh ever gets used, this over-claims; swap the convention then.
if [ "$effort" = "xhigh" ]; then
  printf "  $(c '38;5;196')⚡$(c '38;5;220')⚡$(c '38;5;51')⚡$(rst)$(c '1;38;5;207') ultra$(rst)"
elif [ -n "$effort" ]; then
  printf "  $(c '38;5;147')⚡ %s$(rst)" "$effort"              # light purple
fi
[ -n "$update_available" ] && printf "  $(update_c)⬆ update$(rst)"
printf "\n"
