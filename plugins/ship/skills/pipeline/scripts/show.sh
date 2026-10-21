#!/bin/bash
# show.sh <worktree> <slug> <kind> <file|url> [done]: put a ship page in Pete's Chrome
# without bringing Chrome forward or taking his tab. The #ship=<repo>/<slug>/<kind> tag
# tells the ship-tabs extension to file it in the docs or test group, title it, close the tab it
# replaces (same slug and kind), and on `done` close the ship's other tabs too.
# Kinds: storyboard, plan, review, test (the worktree's localhost), preview.
# Each kind's last URL lands in <top>/.ship-shown/<kind> for the gate buttons.
# show.sh --selftest: checks the recording against a fake `open`.
set -eu
if [ "${1:-}" = --selftest ]; then
  t=$(mktemp -d); trap 'rm -rf "$t"' EXIT
  git init -q "$t/repo" && mkdir -p "$t/repo/sub" "$t/bin" && touch "$t/repo/sub/sb.html"
  printf '#!/bin/sh\necho "$@" >> "%s/opened"\n' "$t" > "$t/bin/open" && chmod +x "$t/bin/open"
  PATH="$t/bin:$PATH" "$0" "$t/repo/sub" demo storyboard "$t/repo/sub/sb.html" done >/dev/null
  shown=$(cat "$t/repo/.ship-shown/storyboard")
  case "$shown" in file://*sb.html#ship=repo/demo/storyboard) ;; *) echo "FAIL recorded: $shown"; exit 1 ;; esac
  grep -q -- '-g -a Google Chrome .*&done$' "$t/opened" || { echo "FAIL open: $(cat "$t/opened")"; exit 1; }
  echo "show.sh selftest ok"; exit 0
fi
[ $# -ge 4 ] || { sed -n '2,8p' "$0"; exit 2; }
common=$(git -C "$1" rev-parse --path-format=absolute --git-common-dir)
repo=$(basename "$(dirname "$common")")
url=$4
[ -e "$url" ] && url=$(python3 -c 'import pathlib,sys; print(pathlib.Path(sys.argv[1]).resolve().as_uri())' "$url")
case "$url" in *'#'*) sep='&' ;; *) sep='#' ;; esac
url="$url${sep}ship=$repo/$2/$3"
# The gate buttons (hooks/register.ts) bring this page forward on Pete's press: keep the
# last one per kind at the worktree's top, without `done`, which would close his other tabs.
top=$(git -C "$1" rev-parse --show-toplevel)
mkdir -p "$top/.ship-shown" && printf '%s\n' "$url" > "$top/.ship-shown/$3"
url="$url${5:+&$5}"
open -g -a "Google Chrome" "$url"
# A doc Pete has shared from its Share button follows its redraws: republish it in the
# background (share.py does nothing for a doc never shared, and never fails this script).
# Only card kinds: the extension keys any other doc by its path, not repo/slug/kind.
case "$3" in storyboard|plan|review)
  [ -f "$4" ] && { /usr/bin/python3 "$(dirname "$0")/share.py" republish "$repo/$2/$3" "$4" >/dev/null 2>&1 & } ;;
esac
echo "$url"
