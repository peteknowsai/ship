#!/bin/bash
# carried.sh <owner/repo>: run from a ship's worktree at LAND, the older open PRs whose
# commits this branch carries, copied (git cherry's "-") or as-is (the same sha on both
# sides), leaving out what main already has. One line per shared commit:
#   #<n> <draft|ready> <branch> <sha> <docs|code> <file count> files: <first five>
# docs means every file is under specs/ or docs/, or Markdown. Exit 1 when there is any,
# 0 when none, 2 when it couldn't check (stderr says why). A newer PR carrying this
# branch's commits built on it and lands after it, so it is named on stderr, never a hit.
# Every ship used to write this check itself; cel-262's `sed s/^/.../` broke on the slash
# in feature/ branch names, and its errors read as hits.
# carried.sh --selftest
set -euo pipefail

docs_only() {  # stdin: one path per line
  local f
  while read -r f; do
    [ -n "$f" ] || continue
    case "$f" in specs/*|docs/*|*.md) ;; *) return 1 ;; esac
  done
}

carried() {  # stdin: "<n> <branch> <isDraft>" per open PR; $1: this branch
  local me=$1 prs mine=0 hits=0 unchecked=0 n branch draft sha copies onmain ours theirs shared files
  prs=$(cat)
  while read -r n branch draft; do
    if [ "$branch" = "$me" ]; then mine=$n; fi
  done <<<"$prs"
  while read -r n branch draft; do
    [ -n "$n" ] || continue
    [ "$branch" = "$me" ] && continue
    if ! git rev-parse -q --verify "origin/$branch^{commit}" >/dev/null; then
      echo "carried: #$n $branch is not on origin (a fork, or deleted), unchecked" >&2
      unchecked=$((unchecked + 1)); continue
    fi
    copies=$(git cherry HEAD "origin/$branch" origin/main) || return 2
    onmain=$(git cherry origin/main "origin/$branch") || return 2
    ours=$(git rev-list --no-merges origin/main..HEAD) || return 2
    theirs=$(git rev-list --no-merges "origin/main..origin/$branch") || return 2
    shared=$(comm -23 \
      <( { awk '$1 == "-" { print $2 }' <<<"$copies"
           comm -12 <(sort <<<"$ours") <(sort <<<"$theirs"); } | sort -u) \
      <(awk '$1 == "-" { print $2 }' <<<"$onmain" | sort -u))
    [ -n "$shared" ] || continue
    if [ "$mine" -gt 0 ] && [ "$n" -gt "$mine" ]; then
      echo "carried: #$n is newer and carries this branch's commits, so it lands after this one" >&2
      continue
    fi
    for sha in $shared; do
      hits=$((hits + 1))
      files=$(git show --name-only --format= "$sha") || return 2
      printf '#%s %s %s %s %s %s files: %s\n' "$n" "$([ "$draft" = true ] && echo draft || echo ready)" \
        "$branch" "${sha:0:9}" "$(docs_only <<<"$files" && echo docs || echo code)" \
        "$(grep -c . <<<"$files" || true)" "$(head -5 <<<"$files" | tr '\n' ' ')"
    done
  done <<<"$prs"
  if [ "$hits" -gt 0 ]; then return 1; fi
  if [ "$unchecked" -gt 0 ]; then return 2; fi
  return 0
}

selftest() {
  local t; t=$(mktemp -d)
  if ( set -e; cd "$t"
    git init -q --bare origin.git; git clone -q origin.git w 2>/dev/null; cd w
    git config user.email t@t; git config user.name t
    c() { echo "$2" > "$1"; git add "$1"; git commit -qm "$1"; }
    git checkout -q -b main; c a base; git push -q origin main
    git checkout -q -b feature/doc; c doc.md d; git push -q origin feature/doc
    git checkout -q -b feature/other main; c o.ts o; git push -q origin feature/other
    git checkout -q -b feature/me main; git cherry-pick -x feature/doc >/dev/null
    git push -q origin feature/me
    rc=0; out=$(printf '1 feature/doc true\n2 feature/other false\n5 feature/me false\n' | carried feature/me) || rc=$?
    [ "$rc" = 1 ] || exit 11                                  # a copy, found by git cherry alone
    [[ "$out" == "#1 draft feature/doc "*" docs 1 files: doc.md "* ]] || exit 12
    [ "$(wc -l <<<"$out")" -eq 1 ] || exit 13                 # not the unrelated PR, not our own
    rc=0; printf '7 feature/doc true\n5 feature/me false\n' | carried feature/me 2>/dev/null || rc=$?
    [ "$rc" = 0 ] || exit 14                                  # a newer PR built on us waits on us
    git checkout -q -b feature/stacked origin/feature/other; c s.ts s; git push -q origin feature/stacked
    rc=0; out=$(printf '2 feature/other false\n6 feature/stacked false\n' | carried feature/stacked) || rc=$?
    [ "$rc" = 1 ] && [[ "$out" == "#2 ready feature/other "*" code 1 files: o.ts "* ]] || exit 15  # as-is
    git checkout -q -b feature/y main; c y.md y; git push -q origin feature/y
    git checkout -q main; git cherry-pick -x feature/y >/dev/null; git push -q origin main
    git checkout -q -b feature/later main; c m.ts m; git push -q origin feature/later; git fetch -q origin
    rc=0; printf '4 feature/y false\n8 feature/later false\n' | carried feature/later || rc=$?
    [ "$rc" = 0 ] || exit 16                                  # a commit main already has is no hit
    rc=0; printf '3 feature/gone false\n8 feature/later false\n' | carried feature/later 2>/dev/null || rc=$?
    [ "$rc" = 2 ] || exit 17                                  # a branch it can't read is unchecked
  ); then
    echo "carried selftest: ok"; rm -rf "$t"
  else
    echo "carried selftest: FAILED (step $?)"; rm -rf "$t"; return 1
  fi
}

case "${1:-}" in
  --selftest) selftest ;;
  */*)
    git fetch -q origin || { echo "carried: git fetch failed (sandbox off?)" >&2; exit 2; }
    git rev-parse -q --verify origin/main >/dev/null || { echo "carried: no origin/main" >&2; exit 2; }
    me=$(git rev-parse --abbrev-ref HEAD)
    [ "$me" != HEAD ] || { echo "carried: detached HEAD; run it on the ship's branch" >&2; exit 2; }
    prs=$(gh pr list -R "$1" --state open --limit 1000 --json number,headRefName,isDraft \
          -q '.[] | "\(.number) \(.headRefName) \(.isDraft)"') || { echo "carried: gh pr list failed" >&2; exit 2; }
    carried "$me" <<<"$prs" ;;
  *) echo "usage: carried.sh <owner/repo> | --selftest" >&2; exit 2 ;;
esac
