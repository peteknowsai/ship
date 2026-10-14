#!/bin/bash
# show.sh <worktree> <slug> <kind> <file|url> [done]: put a ship page in Pete's Chrome
# without bringing Chrome forward or taking his tab. The #ship=<repo>/<slug>/<kind> tag
# tells the ship-tabs extension to file it in the docs or test group, title it, close the tab it
# replaces (same slug and kind), and on `done` close the ship's other tabs too.
# Kinds: storyboard, plan, review, test (the worktree's localhost), preview.
set -eu
[ $# -ge 4 ] || { sed -n '2,6p' "$0"; exit 2; }
common=$(git -C "$1" rev-parse --path-format=absolute --git-common-dir)
repo=$(basename "$(dirname "$common")")
url=$4
[ -e "$url" ] && url=$(python3 -c 'import pathlib,sys; print(pathlib.Path(sys.argv[1]).resolve().as_uri())' "$url")
case "$url" in *'#'*) sep='&' ;; *) sep='#' ;; esac
url="$url${sep}ship=$repo/$2/$3${5:+&$5}"
open -g -a "Google Chrome" "$url"
# A doc Pete has shared from its Share button follows its redraws: republish it in the
# background (share.py does nothing for a doc never shared, and never fails this script).
# Only card kinds: the extension keys any other doc by its path, not repo/slug/kind.
case "$3" in storyboard|plan|review)
  [ -f "$4" ] && { /usr/bin/python3 "$(dirname "$0")/share.py" republish "$repo/$2/$3" "$4" >/dev/null 2>&1 & } ;;
esac
echo "$url"
