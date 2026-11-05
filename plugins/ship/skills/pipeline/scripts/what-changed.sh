#!/bin/bash
# what-changed.sh <old-copy> <new-copy>: the skill files that differ between two installed ship
# copies and, under each Markdown one, the sections its changed lines sit in, so a session told
# ship was updated rereads those instead of diffing by hand (ttowns-civic-feed, 2026-11-04).
# Each heading carries its line in the new copy, so the Read tool opens the section there;
# a computed `sed -n "${a},${b}p"` is refused by the worktree guard (cel-280).
# what-changed.sh --selftest
set -u

# Markdown headings, outside code fences: a skill's bash blocks are full of `# comment` lines.
heads() { awk '/^(```|~~~)/ { f = !f; next } !f && /^#+ / { print }' "$1"; }

sections() {  # the heading over each line of $2 that differs from $1, once each, in file order,
              # then any heading $1 had that $2 lost, so a deleted section is named, not its neighbour
  diff -U0 "$1" "$2" |
    awk '/^@@/ { split($3, r, ","); n = substr(r[1], 2); c = (2 in r) ? r[2] : 1
                 if (c == 0) print (n < 1 ? 1 : n); for (i = n; i < n + c; i++) print i }' |
    awk 'NR == FNR { at[$1] = 1; next }
         /^(```|~~~)/ { f = !f }
         !f && /^#+ / { h = substr($0, 1, 72); hn = FNR }
         FNR in at && !seen[hn]++ { print "    " (hn ? h " (line " hn ")" : "(before the first heading)") }' - "$2"
  awk 'NR == FNR { have[$0] = 1; next } !have[$0] { print "    gone: " substr($0, 1, 72) }' \
    <(heads "$2") <(heads "$1")
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
      *) echo "  $line" ;;  # a file turned directory or link: rare, so diff's own words
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
  printf '## Keep\na\nb\n```bash\n# a comment, not a heading\n```\nc\n## Notes\nx\n## Old\ngone soon\n## Notes\ny\n' > "$t/a/skills/verify/edits.md"
  printf '## Keep\na\n```bash\n# a comment, not a heading\n```\nc2\n## Notes\nx2\n## Notes\ny2\n' > "$t/b/skills/verify/edits.md"
  printf 'first\n## S\nrest\n' > "$t/a/skills/verify/top.md"; printf '## S\nrest\n' > "$t/b/skills/verify/top.md"
  out=$(changes "$t/a" "$t/b")
  under() { printf "%s\n" "$out" | awk -v f="  $1" '$0 == f { on = 1; next } on && /^    / { print; next } { on = 0 }'; }
  ok 'a changed SKILL.md is listed with only the section that changed' \
     '[ "$(under pipeline/SKILL.md)" = "    ### 5 · LAND (line 7)" ]'
  ok 'an identical file is not listed' '! printf "%s" "$out" | grep -q "verify/SKILL.md"'
  ok 'a new and a removed file are named as such' \
     'printf "%s" "$out" | grep -qx "  new: pipeline/added.sh" && printf "%s" "$out" | grep -qx "  gone: pipeline/gone.md"'
  ok 'a line above every heading and a new heading both show, each once' \
     '[ "$(under verify/notes.md)" = "$(printf "    (before the first heading)\n    ## B (line 5)")" ]'
  ok 'a deletion inside a section names it, a fenced # line is no heading, a deleted section is gone' \
     '[ "$(under verify/edits.md)" = "$(printf "    ## Keep (line 1)\n    ## Notes (line 7)\n    ## Notes (line 9)\n    gone: ## Old")" ]'
  ok 'deleting line 1 names what now starts the file' '[ "$(under verify/top.md)" = "    ## S (line 1)" ]'
  ok 'two identical copies print nothing' '[ -z "$(changes "$t/a" "$t/a")" ]'
  [ $fail = 0 ] && echo "what-changed self-test: 0 failed" || { echo "what-changed self-test: failed"; exit 1; }
  exit 0
fi

[ $# -eq 2 ] && [ -d "$1/skills" ] && [ -d "$2/skills" ] || { sed -n '2,7p' "$0" >&2; exit 2; }
changes "$1" "$2"
