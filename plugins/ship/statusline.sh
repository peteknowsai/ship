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

# the stage breadcrumb — design · plan · build · test · land, active stage lit amber.
# Shown for the whole ship (and at gates), next to the brain on line 2,
# so which stage we're in always reads — not just a single dim word.
stage_bar() {
  active="$1"; out=""
  for s in design plan build test land; do
    [ -n "$out" ] && out="$out$(c '38;5;239') · $(rst)"
    if [ "$s" = "$active" ]; then out="$out$(c '1;38;5;215')$s$(rst)"
    else out="$out$(c '38;5;242')$s$(rst)"; fi
  done
  printf '%s' "$out"
}

# ---- extract data ----
if [ "$HAS_JQ" -eq 1 ]; then
  current_dir=$(echo "$input" | jq -r '.workspace.current_dir // .cwd // "~"' 2>/dev/null | sed "s|^$HOME|~|g")
  cc_version=$(echo "$input" | jq -r '.version // ""' 2>/dev/null)
  effort=$(echo "$input" | jq -r '.effort.level // ""' 2>/dev/null)
  model_name=$(echo "$input" | jq -r '.model.display_name // .model.id // ""' 2>/dev/null)
  context_pct=$(echo "$input" | jq -r '.context_window.used_percentage // 0' 2>/dev/null)
  context_pct=$(printf "%.0f" "$context_pct" 2>/dev/null)
else
  current_dir="~"; cc_version=""; effort=""; context_pct=0; model_name=""
fi

# The context-window size never changes mid-session, so "(1M context)" is a constant
# taking up room. Drop any trailing parenthetical: "Opus 5 (1M context)" -> "Opus 5".
model_name=$(printf '%s' "$model_name" | sed 's/ *([^)]*)//g')

# A ship aimed at another repo can't move the session's cwd (EnterWorktree refuses a
# foreign worktree), so /ship leaves the worktree's path under this session's id.
# Follow it while that worktree still carries a stage marker; teardown ends it.
if [ "$HAS_JQ" -eq 1 ]; then
  ship_ptr="$HOME/.claude/ship-active/$(echo "$input" | jq -r '.session_id // "none"' 2>/dev/null)"
  if [ -f "$ship_ptr" ]; then
    ship_wt=$(head -1 "$ship_ptr")
    if [ -f "$ship_wt/.ship-stage" ]; then cd "$ship_wt" 2>/dev/null; else rm -f "$ship_ptr"; fi
  fi
fi

# ---- git: where am I (main checkout or linked worktree) and on what ----
git_branch=""
git_root=""
is_linked=0
ships_count=0
repo_name=$(basename "$current_dir")
if git rev-parse --git-dir >/dev/null 2>&1; then
  # --show-current prints nothing (and succeeds) on a detached HEAD, so fall back by hand
  git_branch=$(git branch --show-current 2>/dev/null)
  [ -n "$git_branch" ] || git_branch="@$(git rev-parse --short HEAD 2>/dev/null)"
  git_root=$(git rev-parse --show-toplevel 2>/dev/null)
  # a linked worktree has its own git dir inside the main checkout's common dir
  { read -r gd; read -r gcd; } < <(git rev-parse --path-format=absolute --git-dir --git-common-dir 2>/dev/null)
  [ -n "$gd" ] && [ "$gd" != "$gcd" ] && is_linked=1
  wt_list=$(git worktree list 2>/dev/null)
  # ships in flight = linked worktrees carrying a live .ship-stage (landed ones are done)
  while read -r wt; do
    [ -f "$wt/.ship-stage" ] && ! grep -q landed "$wt/.ship-stage" 2>/dev/null && ships_count=$((ships_count + 1))
  done < <(printf '%s\n' "$wt_list" | tail -n +2 | awk '{print $1}')
  # canonical repo name = basename of the main (first) worktree, so a worktree shows
  # "homezero", not the long redundant "homezero.feature-x"
  main_wt=$(printf '%s\n' "$wt_list" | head -1 | awk '{print $1}')
  [ -n "$main_wt" ] && repo_name=$(basename "$main_wt")
fi

# ---- ship stage (worktree pipeline marker written by /ship) ----
# Claude Code writes the bare stage word; Codex writes "key: value" lines with a
# "stage:" key (or a bare word on line 1). Take the stage key when present.
ship_stage=""
if [ -n "$git_root" ] && [ -f "$git_root/.ship-stage" ]; then
  ship_stage=$(sed -n 's/^stage:[[:space:]]*//p' "$git_root/.ship-stage" | head -1)
  [ -n "$ship_stage" ] || ship_stage=$(head -1 "$git_root/.ship-stage")
  ship_stage=$(printf '%s' "$ship_stage" | tr -d ' \n' | tr '[:upper:]' '[:lower:]')
fi
ship_slug="${git_branch#*/}"

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
  access_token=$(security find-generic-password -s "Claude Code-credentials" -a "$USER" -w 2>/dev/null | jq -r '.claudeAiOauth.accessToken // empty' 2>/dev/null)
  if [ -n "$access_token" ]; then
    fresh_data=$(curl -s --max-time 2 "https://api.anthropic.com/api/oauth/usage" \
      -H "Authorization: Bearer $access_token" \
      -H "anthropic-beta: oauth-2025-04-20" \
      -H "Accept: application/json" 2>/dev/null)
    echo "$fresh_data" | jq -e '.seven_day' >/dev/null 2>&1 && echo "$fresh_data" > "$usage_cache"
  fi
fi
scoped_pct=""
scoped_label=""
if [ -f "$usage_cache" ] && [ "$HAS_JQ" -eq 1 ]; then
  weekly_val=$(jq -r '(.limits[]? | select(.kind == "weekly_all") | .percent) // .seven_day.utilization // empty' "$usage_cache" 2>/dev/null)
  [ -n "$weekly_val" ] && [ "$weekly_val" != "null" ] && weekly_pct=$(printf "%.0f" "$weekly_val" 2>/dev/null)
  weekly_resets=$(jq -r '.seven_day.resets_at // empty' "$usage_cache" 2>/dev/null)
  # model-scoped weekly bucket (e.g. Fable) — label comes from the API, not hardcoded
  scoped_pct=$(jq -r '(.limits[]? | select(.kind == "weekly_scoped") | .percent) // empty' "$usage_cache" 2>/dev/null)
  scoped_resets=$(jq -r '(.limits[]? | select(.kind == "weekly_scoped") | .resets_at) // empty' "$usage_cache" 2>/dev/null)
  scoped_label=$(jq -r '(.limits[]? | select(.kind == "weekly_scoped") | .scope.model.display_name) // empty' "$usage_cache" 2>/dev/null | tr '[:upper:]' '[:lower:]')
fi

# ---- Codex weekly (cached; token from ~/.codex/auth.json) ----
codex_pct=""; codex_reset_epoch=""
codex_cache="$HOME/.claude/codex-usage-cache.json"
codex_stale=1
if [ -f "$codex_cache" ]; then
  codex_age=$(($(date +%s) - $(stat -f %m "$codex_cache" 2>/dev/null || echo 0)))
  [ "$codex_age" -lt 300 ] && codex_stale=0
fi
if [ "$codex_stale" -eq 1 ] && [ "$HAS_JQ" -eq 1 ] && [ -f "$HOME/.codex/auth.json" ]; then
  codex_tok=$(jq -r '.tokens.access_token // empty' "$HOME/.codex/auth.json" 2>/dev/null)
  codex_acct=$(jq -r '.tokens.account_id // empty' "$HOME/.codex/auth.json" 2>/dev/null)
  if [ -n "$codex_tok" ]; then
    fresh_codex=$(curl -s --max-time 2 "https://chatgpt.com/backend-api/wham/usage" \
      -H "Authorization: Bearer $codex_tok" -H "chatgpt-account-id: $codex_acct" \
      -H "Accept: application/json" 2>/dev/null)
    echo "$fresh_codex" | jq -e '.rate_limit.primary_window' >/dev/null 2>&1 && echo "$fresh_codex" > "$codex_cache"
  fi
fi
if [ -f "$codex_cache" ] && [ "$HAS_JQ" -eq 1 ]; then
  codex_pct=$(jq -r '.rate_limit.primary_window.used_percent // empty' "$codex_cache" 2>/dev/null)
  codex_reset_epoch=$(jq -r '.rate_limit.primary_window.reset_at // empty' "$codex_cache" 2>/dev/null)
  codex_locked=$(jq -r '.rate_limit.limit_reached // false' "$codex_cache" 2>/dev/null)
  # credits = the overage bank that keeps Codex running once the weekly locks
  codex_credits=$(jq -r 'if .credits.has_credits then (.credits.balance | tonumber | floor) else empty end' "$codex_cache" 2>/dev/null)
fi

# ---- stale? a fetch that keeps failing leaves the last good cache behind; flag it ----
stale_after=1800
is_stale() { [ -f "$1" ] && [ $(( $(date +%s) - $(stat -f %m "$1" 2>/dev/null || echo 0) )) -gt "$stale_after" ]; }
anthro_stale=0; is_stale "$usage_cache" && anthro_stale=1
codex_stale=0;  is_stale "$codex_cache" && codex_stale=1

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

# ---- reset time formatter: relative, compact ("45m", "19h", "1d19h", "4d") ----
format_reset() {
  local iso_ts="$1"; [ -z "$iso_ts" ] && return
  local stripped=$(echo "$iso_ts" | sed 's/\.[^+Z]*//; s/+.*//; s/Z//')
  format_reset_epoch "$(TZ=UTC date -jf "%Y-%m-%dT%H:%M:%S" "$stripped" "+%s" 2>/dev/null)"
}
format_reset_epoch() {
  local reset_epoch="$1"; [ -z "$reset_epoch" ] && return
  local diff=$(( reset_epoch - $(date +%s) ))
  [ "$diff" -le 0 ] && printf "now" && return
  local d=$((diff / 86400)) h=$(((diff % 86400) / 3600))
  if [ "$diff" -lt 3600 ]; then printf "%dm" $((diff / 60))
  elif [ "$d" -eq 0 ]; then printf "%dh" "$h"
  elif [ "$d" -eq 1 ] && [ "$h" -gt 0 ]; then printf "1d%dh" "$h"   # under 2d the hours matter
  else printf "%dd" "$d"; fi
}

# ---- value-based colors ----
context_color() {
  if [ "${context_pct:-0}" -ge 80 ]; then c '38;5;203'    # red
  elif [ "${context_pct:-0}" -ge 60 ]; then c '38;5;215'  # orange
  else c '38;5;158'; fi                                    # green
}
weekly_color() {
  [ "$anthro_stale" = 1 ] && { c '38;5;245'; return; }   # stale: gray, not traffic-light
  if [ "${weekly_pct:-0}" -ge 80 ]; then c '38;5;203'
  elif [ "${weekly_pct:-0}" -ge 50 ]; then c '38;5;215'
  else c '38;5;158'; fi
}
# the balance is its own gauge: green while it's healthy, red under 10k
credits_color() {
  [ "$codex_stale" = 1 ] && { c '38;5;245'; return; }
  if [ "${codex_credits:-0}" -lt 10000 ]; then c '38;5;203'; else c '38;5;158'; fi
}
codex_color() {
  [ "$codex_stale" = 1 ] && { c '38;5;245'; return; }   # stale: gray, not traffic-light
  if [ "${codex_pct:-0}" -ge 80 ]; then c '38;5;203'
  elif [ "${codex_pct:-0}" -ge 50 ]; then c '38;5;215'
  else c '38;5;158'; fi
}
scoped_color() {
  [ "$anthro_stale" = 1 ] && { c '38;5;245'; return; }   # stale: gray, not traffic-light
  if [ "${scoped_pct:-0}" -ge 80 ]; then c '38;5;203'
  elif [ "${scoped_pct:-0}" -ge 50 ]; then c '38;5;215'
  else c '38;5;158'; fi
}

# ============================ render ============================
# Line 1 — identity only: which ship (or repo·branch) + ships-in-flight count.
# Phase moves to line 2 to keep this short.
is_gate=0; phase=""
if [ -n "$ship_stage" ]; then
  case "$ship_stage" in
    gate:1*) printf "$(gate_c)✋ %s — storyboard?$(rst)" "$ship_slug"; is_gate=1; phase="$(stage_bar design)" ;;
    gate:2*) printf "$(gate_c)✋ %s — go?$(rst)" "$ship_slug"; is_gate=1; phase="$(stage_bar plan)" ;;
    gate:codex*) printf "$(gate_c)✋ %s — test it with Codex$(rst)" "$ship_slug"; is_gate=1; phase="$(stage_bar test)" ;;
    gate:test*) printf "$(gate_c)✋ %s — try it, then merge main?$(rst)" "$ship_slug"; is_gate=1; phase="$(stage_bar test)" ;;
    test*)   printf "$(ship_c)🧪 %s — codex testing$(rst)" "$ship_slug"; phase="$(stage_bar test)" ;;
    discover*) printf "$(ship_c)🚢 %s$(rst)" "$ship_slug"; phase="$(stage_bar design)" ;;
    plan*)     printf "$(ship_c)🚢 %s$(rst)" "$ship_slug"; phase="$(stage_bar plan)" ;;
    build*)    printf "$(ship_c)🚢 %s$(rst)" "$ship_slug"; phase="$(stage_bar build)" ;;
    landed*) printf "$(ship_c)✅ %s — landed; goes when this session ends$(rst)" "$ship_slug"; phase="$(stage_bar land)" ;;
    review*)   printf "$(ship_c)🚢 %s$(rst)" "$ship_slug"; phase="$(stage_bar test)" ;;
    *)         printf "$(ship_c)🚢 %s$(rst)" "$ship_slug" ;;
  esac
elif [ "$is_linked" -eq 1 ]; then
  # in a worktree: tree icon, branch without its feature/ fix/ prefix
  printf "$(c '38;5;108')🌳 %s$(rst) $(branch_c)⎇ %s$(rst)" "$repo_name" "${git_branch#*/}"
else
  printf "$(dir_color)📁 %s$(rst)" "$repo_name"
  if [ -n "$git_root" ]; then
    # the main checkout stays on main; anything else is a mistake worth seeing
    case "$git_branch" in
      main|master) printf "  $(phase_c)%s$(rst)" "$git_branch" ;;
      *) printf "  $(gate_c)⚠ %s$(rst)" "$git_branch" ;;
    esac
  fi
fi
# ships in flight — orientation; hidden at a gate
if [ "$is_gate" -eq 0 ] && [ "$ships_count" -ge 1 ]; then
  printf "  $(c '38;5;80')🚢 %d$(rst)" "$ships_count"
fi
printf "\n"

# Line 2 — phase (when in a ship), then the gauges + effort.
[ -n "$phase" ] && printf "$(phase_c)%s$(rst)  " "$phase"
[ -n "$model_name" ] && printf "$(c '38;5;183')🤖 %s$(rst)" "$model_name"
# effort — reasoning tier. The harness exposes no real ultracode bit (it reports as
# xhigh, same as plain extra-high). Pete never uses plain xhigh on Opus, so for him
# xhigh ≡ ultracode — render it as the ultra badge: three rainbow ⚡. Other tiers plain.
# ponytail: xhigh==ultracode is a deliberate convention, not detection — the only honest
# proxy available. If plain xhigh ever gets used, this over-claims; swap the convention then.
if [ "$effort" = "xhigh" ]; then
  printf "  $(c '38;5;196')⚡$(c '38;5;220')⚡$(c '38;5;51')⚡$(rst)$(c '1;38;5;207')ultra$(rst)"
elif [ -n "$effort" ]; then
  printf "  $(c '38;5;147')⚡%s$(rst)" "$effort"              # light purple
fi
[ -n "$model_name$effort" ] && printf "  "
printf "$(context_color)🧠 %d%%$(rst)" "${context_pct:-0}"
# Quota, grouped by vendor:  O 72% · F 53% ↻2d │ C 80% ↻4d  (or C 58k once spent)
# O = weekly_all (every model, Fable included; Pete reads it as Opus). F = weekly_scoped,
# Fable alone, the tighter cap. Both drain on Fable tokens; the higher one locks first.
# Each vendor always shows its own reset right after its group: the clocks differ
# (a Codex reset restarts its 7-day timer, an Anthropic reset only refills the percent).
# Codex at 100% with credits left shows the balance instead of the percent ("C 58k").
# A trailing "?" and gray numbers mean that vendor's cache is over 30 minutes old.
dim_sep() { printf " $(c '38;5;245')%s$(rst) " "$1"; }
if [ -n "$weekly_pct" ]; then
  printf "  $(weekly_color)O %d%%$(rst)" "$weekly_pct"
  hot_reset="$weekly_resets"
  if [ -n "$scoped_pct" ] && [ -n "$scoped_label" ]; then
    scoped_initial=$(printf '%s' "${scoped_label:0:1}" | tr '[:lower:]' '[:upper:]')
    dim_sep "·"; printf "$(scoped_color)%s %d%%$(rst)" "$scoped_initial" "$scoped_pct"
    [ "$scoped_pct" -gt "$weekly_pct" ] && [ -n "$scoped_resets" ] && hot_reset="$scoped_resets"
  fi
  rs=$(format_reset "$hot_reset")
  [ -n "$rs" ] && printf " $(c '38;5;245')↻%s$(rst)" "$rs"
  [ "$anthro_stale" = 1 ] && printf "$(c '38;5;245')?$(rst)"
fi
if [ -n "$codex_pct" ]; then
  [ -n "$weekly_pct" ] && dim_sep "│" || printf "  "
  if [ "${codex_pct%.*}" -ge 100 ] && [ "${codex_credits:-0}" -gt 0 ]; then
    # sub is spent but credits are covering it: the balance is the number that matters now
    if [ "$codex_credits" -ge 1000 ]; then cr="$((codex_credits / 1000))k"; else cr="$codex_credits"; fi
    printf "$(credits_color)C %s$(rst)" "$cr"
  else
    printf "$(codex_color)C %d%%$(rst)" "$codex_pct"
  fi
  rs=$(format_reset_epoch "$codex_reset_epoch")
  [ -n "$rs" ] && printf " $(c '38;5;245')↻%s$(rst)" "$rs"
  [ "$codex_stale" = 1 ] && printf "$(c '38;5;245')?$(rst)"
fi
[ -n "$update_available" ] && printf "  $(update_c)⬆ update$(rst)"
printf "\n"
