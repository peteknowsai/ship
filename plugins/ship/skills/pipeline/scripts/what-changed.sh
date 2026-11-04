#!/bin/bash
# what-changed.sh <old-copy> <new-copy>: the skill files that differ between two installed ship
# copies and, under each Markdown one, the sections its changed lines sit in, so a session told
# ship was updated rereads those instead of diffing by hand (ttowns-civic-feed, 2026-11-04).
# what-changed.sh --selftest
set -u

sections() {  # the heading over each line of $2 that differs from $1, once each, in file order
  diff -U0 "$1" "$2" |
    awk '/^@@/ { split($3, r, ","); n = substr(r[1], 2); c = (2 in r) ? r[2] : 1
                 if (c == 0) print n; for (i = n; i < n + c; i++) print i }' |
    awk 'NR == FNR { at[$1] = 1; next }
         /^#+ / { h = substr($0, 1, 72) }
         FNR in at && !seen[h]++ { print "    " (h == "" ? "(before the first heading)" : h) }' - "$2"
}

changes() {
  diff -rq "$1/skills" "$2/skills" 2>/dev/null | while IFS= read -r line; do
    case "$line" in
      Files\ *)
        a=${line#Files }; a=${a%% and *}; b=${line#* and }; b=${b% differ}
        echo "  ${b#"$2"/skills/}"
        case "$b" in *.md) sections "$a" "$b" ;; esac ;;
      Only\ in\ *)
        dir=${line#Only in }; dir=${dir%%: *}; path="$dir/${line#*: }"
        case "$path" in "$2"/*) echo "  new: ${path#"$2"/skills/}" ;; *) echo "  gone: ${path#"$1"/skills/}" ;; esac ;;
    esac
  done
}

if [ "${1:-}" = --selftest ]; then
  t=$(mktemp -d); trap 'rm -rf "$t"' EXIT; fail=0
  ok() { if eval "$2"; then echo "  ok   $1"; else echo "  FAIL $1"; fail=1; fi; }
  mkdir -p "$t/a/skills/pipeline" "$t/b/skills/pipeline" "$t/a/skills/verify" "$t/b/skills/verify"
  printf '# ship\nintro\n## Engines\nopus\n### 4 · TEST\nwalk it\n### 5 · LAND\nmerge\nwatch\n' > "$t/a/skills/pipeline/SKILL.md"
  printf '# ship\nintro\n## Engines\nopus\n### 4 · TEST\nwalk it\n### 5 · LAND\nmerge first\nwatch\nthen smoke\n' > "$t/b/skills/pipeline/SKILL.md"
  printf 'same\n' | tee "$t/a/skills/verify/SKILL.md" > "$t/b/skills/verify/SKILL.md"
  printf 'old\n' > "$t/a/skills/pipeline/gone.md"; printf 'x\n' > "$t/b/skills/pipeline/added.sh"
  printf '# t\none\n## A\ntwo\n' > "$t/a/skills/verify/notes.md"
  printf 'zero\n# t\none\n## A\n## B\nthree\n' > "$t/b/skills/verify/notes.md"
  out=$(changes "$t/a" "$t/b")
  ok 'a changed SKILL.md is listed with only the section that changed' \
     '[ "$(printf "%s\n" "$out" | awk "/^  pipeline\/SKILL.md\$/ { on = 1; next } on && /^    / { print; next } { on = 0 }")" = "    ### 5 · LAND" ]'
  ok 'an identical file is not listed' '! printf "%s" "$out" | grep -q "verify/SKILL.md"'
  ok 'a new and a removed file are named as such' \
     'printf "%s" "$out" | grep -qx "  new: pipeline/added.sh" && printf "%s" "$out" | grep -qx "  gone: pipeline/gone.md"'
  ok 'a line above every heading and a new heading both show, each once' \
     '[ "$(printf "%s\n" "$out" | sed -n "/verify\/notes.md/,\$p" | tail -n +2)" = "$(printf "    (before the first heading)\n    ## B")" ]'
  ok 'two identical copies print nothing' '[ -z "$(changes "$t/a" "$t/a")" ]'
  [ $fail = 0 ] && echo "what-changed self-test: 0 failed" || { echo "what-changed self-test: failed"; exit 1; }
  exit 0
fi

[ $# -eq 2 ] && [ -d "$1/skills" ] && [ -d "$2/skills" ] || { sed -n '2,5p' "$0" >&2; exit 2; }
changes "$1" "$2"
