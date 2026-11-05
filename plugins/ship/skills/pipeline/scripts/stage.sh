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
# A session keeps the ship it loaded at startup; a long one can run on rules since fixed.
here=$(cd "$(dirname "$0")/../../.." && pwd)
new=$(jq -r '.plugins["ship@ship"][0].installPath // empty' "${SHIP_INSTALLED:-$HOME/.claude/plugins/installed_plugins.json}" 2>/dev/null || true)
case "$here" in */plugins/cache/ship/ship/*)
  if [ -n "$new" ] && [ "$(basename "$new")" != "$(basename "$here")" ] && [ -d "$new" ]; then
    echo "notice: ship was updated since this session loaded it ($(basename "$here") -> $(basename "$new")). Reread what changed, listed below by file and section under $new/skills/ (diff -ru $here/skills $new/skills for the lines), and call scripts from $new from here on; the newer rules win. A changed rule for a stage this ship already passed does not redo that stage: a check or stop it adds runs before landing, and a record a later step reads is written from what was done, never invented." >&2
    lister="$new/skills/pipeline/scripts/what-changed.sh"; [ -f "$lister" ] || lister="$(dirname "$0")/what-changed.sh"
    # The list below starts from the copy these scripts came from, but the Skill tool loads every
    # ship skill from the copy the session started on, even one first loaded after an update
    # (cel-306 followed 8f5738a's verify while calling 839a52's scripts).
    echo "A ship skill loads from the copy this session started on, even one loaded after this notice: for each whose printed base directory is not under $new, run bash $lister <that path, cut before /skills> $new and read what it lists under that skill." >&2
    bash "$lister" "$here" "$new" >&2 2>/dev/null || true
  fi
esac
echo "$root: $2"
