#!/bin/bash
# what-changed.sh <old-copy> <new-copy>: the skill files that differ between two installed ship
# copies and, under each Markdown one, the sections its changed lines sit in, so a session told
# ship was updated rereads those instead of diffing by hand (ttowns-civic-feed, 2026-11-04).
# Each heading carries its line in the new copy, so the Read tool opens the section there;
# a computed `sed -n "${a},${b}p"` is refused by the worktree guard (cel-280).
# Under each heading of a SKILL.md come the new copy's changed lines themselves, so the rule is
# in front of the session whether or not it rereads: cel-272 was told twice that Working rules
# had changed, never opened them, and started the Monitor the new lines ruled out. A reference
# file keeps its headings alone, since it is read when its case comes up.
# what-changed.sh --selftest
set -u
per_section=8  # changed lines shown under one heading; the rest are counted
in_all=60      # and under every heading together: both callers run at every stage change

# Markdown headings, outside code fences: a skill's bash blocks are full of `# comment` lines.
heads() { awk '/^(```|~~~)/ { f = !f; next } !f && /^#+ / { print }' "$1"; }

sections() {  # the heading over each line of $2 that differs from $1, once each, in file order;
              # with $3 set, $2's changed lines under it and a mark where lines were only removed;
              # then any heading $1 had that $2 lost, so a deleted section is named, not its neighbour
  diff -U0 "$1" "$2" |
    # + 0: read as text, a hunk from line 2 to line 10 ends before it starts and was dropped whole
    awk '/^@@/ { split($3, r, ","); n = substr(r[1], 2) + 0; c = (2 in r) ? r[2] + 0 : 1
                 if (c == 0) print (n < 1 ? 1 : n), 0; for (i = n; i < n + c; i++) print i, 1 }' |
    awk -v cap="$per_section" -v lines="${3:-0}" '
         function more(  d) { d = k - cap; k = 0
           if (d > 0) print "      | (" d " more changed line" (d == 1 ? "" : "s") " in this section)" }
         NR == FNR { at[$1] = 1; if ($2) show[$1] = 1; else gone[$1] = 1; next }
         /^(```|~~~)/ { f = !f }
         !f && /^#+ / { more(); h = substr($0, 1, 72); hn = FNR; told = 0 }
         FNR in at { if (!seen[hn]++) print "    " (hn ? h " (line " hn ")" : "(before the first heading)")
                     if (lines && FNR in gone && !told++) print "      | (lines removed here)"
                     if (lines && FNR in show && $0 !~ /^[ \t\r]*$/ && ++k <= cap) print "      | " $0 }
         END { more() }' - "$2"
  awk 'NR == FNR { have[$0] = 1; next } !have[$0] { print "    gone: " substr($0, 1, 72) }' \
    <(heads "$2") <(heads "$1")
}

changes() {  # the listing, with no more than $in_all changed lines in it
  listing "$1" "$2" | awk -v max="$in_all" '
    /^      \| \(lines removed here\)$/ { print; next }
    /^      \| \([0-9]+ more changed lines? in this section\)$/ {  # a count, not a line: past the
      if (n >= max) cut += substr($2, 2); else print; next }        # limit it joins the closing count
    /^      \| / && ++n > max { cut++; next }
    { print }
    END { if (n) print "  (a | line is one changed line, often mid-sentence: open its section for the whole rule)"
          if (cut) print "  (" cut " more changed line" (cut == 1 ? "" : "s") " left out: open the sections named above)" }'
}

listing() {
  diff -rq "$1/skills" "$2/skills" 2>/dev/null | while IFS= read -r line; do
    case "$line" in
      Files\ *)
        a=${line#Files }; a=${a%% and *}; b=${line#* and }; b=${b% differ}
        echo "  ${b#"$2"/skills/}"
        case "$b" in */SKILL.md) sections "$a" "$b" 1 ;; *.md) sections "$a" "$b" ;; esac ;;
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
  ok 'a changed SKILL.md is listed with only the section that changed, and its changed lines' \
     '[ "$(under pipeline/SKILL.md)" = "$(printf "    ### 5 · LAND (line 7)\n      | merge first\n      | then smoke")" ]'
  ok 'an identical file is not listed' '! printf "%s" "$out" | grep -q "verify/SKILL.md"'
  ok 'a new and a removed file are named as such' \
     'printf "%s" "$out" | grep -qx "  new: pipeline/added.sh" && printf "%s" "$out" | grep -qx "  gone: pipeline/gone.md"'
  ok 'a line above every heading and a new heading both show, each once' \
     '[ "$(under verify/notes.md)" = "$(printf "    (before the first heading)\n    ## B (line 5)")" ]'
  ok 'a deletion inside a section names it, a fenced # line is no heading, a deleted section is gone' \
     '[ "$(under verify/edits.md)" = "$(printf "    ## Keep (line 1)\n    ## Notes (line 7)\n    ## Notes (line 9)\n    gone: ## Old")" ]'
  ok 'deleting line 1 names what now starts the file' '[ "$(under verify/top.md)" = "    ## S (line 1)" ]'
  ok 'two identical copies print nothing' '[ -z "$(changes "$t/a" "$t/a")" ]'
  mkdir -p "$t/c/skills/pipeline" "$t/d/skills/pipeline" "$t/c/skills/verify" "$t/d/skills/verify"
  printf '## One\nkeep\n## Two\nkeep\n' > "$t/c/skills/pipeline/SKILL.md"
  { printf '## One\n'; for i in 1 2 3 4 5 6 7 8 9; do echo "new $i"; done; printf '\nkeep\n## Two\nkeep\nnew 10\n'; } > "$t/d/skills/pipeline/SKILL.md"
  printf '## A\nx\n## B\ny\nz\n## C\nw\n' > "$t/c/skills/verify/SKILL.md"
  printf '## A\nx\n## B\ny\n## C\nw\nc1\nc2\nc3\nc4\n' > "$t/d/skills/verify/SKILL.md"
  per_section=3; out=$(changes "$t/c" "$t/d"); per_section=8
  ok 'a hunk from line 2 to line 11 shows (read as text, 2 comes after 11), capped, blank lines aside' \
     '[ "$(under pipeline/SKILL.md)" = "$(printf "    ## One (line 1)\n      | new 1\n      | new 2\n      | new 3\n      | (6 more changed lines in this section)\n    ## Two (line 13)\n      | new 10")" ]'
  ok 'a section that only lost lines says so, and a file'"'"'s last section counts what it leaves out' \
     '[ "$(under verify/SKILL.md)" = "$(printf "    ## B (line 3)\n      | (lines removed here)\n    ## C (line 5)\n      | c1\n      | c2\n      | c3\n      | (1 more changed line in this section)")" ]'
  ok 'a listing with lines in it says what a | line is' \
     'printf "%s\n" "$out" | tail -1 | grep -q "^  (a | line is one changed line"'
  per_section=3; in_all=3; out=$(changes "$t/c" "$t/d"); per_section=8; in_all=60
  ok 'past the limit for the whole listing the headings and the removed mark still show, and every line left out is counted' \
     '[ "$out" = "$(printf "  pipeline/SKILL.md\n    ## One (line 1)\n      | new 1\n      | new 2\n      | new 3\n    ## Two (line 13)\n  verify/SKILL.md\n    ## B (line 3)\n      | (lines removed here)\n    ## C (line 5)\n  (a | line is one changed line, often mid-sentence: open its section for the whole rule)\n  (11 more changed lines left out: open the sections named above)")" ]'
  [ $fail = 0 ] && echo "what-changed self-test: 0 failed" || { echo "what-changed self-test: failed"; exit 1; }
  exit 0
fi

[ $# -eq 2 ] && [ -d "$1/skills" ] && [ -d "$2/skills" ] || { awk 'NR > 1 { if (!/^#/) exit; print }' "$0" >&2; exit 2; }
changes "$1" "$2"
