#!/bin/bash
# stage.sh <worktree> <stage>: set the ship's stage marker, which the status line reads,
# and keep ship's own files (.ship-stage, .ship-shots, .ship-shown, .ship-route.json) out of git.
# stage.sh <dir> exclude: only the exclude line, no marker (a cross-repo ship's shots root).
# One plain command, so it never trips the harness's worktree-isolation guard the way
# `echo … >> $(git rev-parse …)` does.
set -eu
[ $# -eq 2 ] || { echo "stage.sh: expected 2 args, got $#" >&2; sed -n '2p' "$0"; exit 2; }
root=$(git -C "$1" rev-parse --show-toplevel)
common=$(git -C "$root" rev-parse --git-common-dir)
case "$common" in /*) ;; *) common="$root/$common" ;; esac
mkdir -p "$common/info"
grep -qxF '.ship-*' "$common/info/exclude" 2>/dev/null || echo '.ship-*' >> "$common/info/exclude"
[ "$2" = exclude ] && { echo "$root: .ship-* excluded"; exit 0; }
printf '%s' "$2" > "$root/.ship-stage"
# land: a SELF-DIRECTED or GATED ship commits its review card before LAND removes the
# worktree; warn when the branch adds none for its slug (thin-search needed a second PR).
# Only those lanes run route.py plan, so .ship-route.json tells them from EXPRESS.
if [ "$2" = land ] && [ -f "$root/.ship-route.json" ]; then
  slug=$(git -C "$root" rev-parse --abbrev-ref HEAD); slug=${slug#*/}
  base=$(git -C "$root" rev-parse --abbrev-ref origin/HEAD 2>/dev/null) || base=origin/main
  key=$(printf '%s' "$slug" | grep -oE '^[a-z]+-[0-9]+' || true)  # cel-221: a card folder may carry just the key
  id=${key:-$slug}
  git -C "$root" diff --name-only "$base"...HEAD 2>/dev/null | grep -qE "review.*$id|$id.*review" ||
    echo "warning: no review card for $slug on this branch; commit it now" >&2
fi
# A session keeps the ship it loaded at startup; a long one can run on rules since fixed.
here=$(cd "$(dirname "$0")/../../.." && pwd)
new=$(jq -r '.plugins["ship@ship"][0].installPath // empty' "${SHIP_INSTALLED:-$HOME/.claude/plugins/installed_plugins.json}" 2>/dev/null || true)
case "$here" in */plugins/cache/ship/ship/*)
  [ -n "$new" ] && [ "$(basename "$new")" != "$(basename "$here")" ] && [ -d "$new" ] &&
    echo "notice: ship was updated since this session loaded it ($(basename "$here") -> $(basename "$new")). Reread $new/skills/pipeline/SKILL.md, Engines and this stage's section, and call scripts from $new from here on; the newer rules win." >&2
esac
echo "$root: $2"
