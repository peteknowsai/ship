#!/bin/bash
# carried.sh <owner/repo>: run from a ship's worktree at LAND, the other open PRs whose
# commits this branch carries, either copied (git cherry's "-") or as-is (the same sha on
# both sides). One line per shared commit, "#<n> <draft|ready> <branch> <sha> <files>",
# exit 1 when there is any, 0 when none, 2 when it couldn't check. Every ship used to write
# this check itself, and cel-262's `sed s/^/.../` broke on the slash in feature/ branches.
# carried.sh --selftest
set -euo pipefail

carried() {  # stdin: "<n> <branch> <isDraft>" per open PR; $1: this branch
  local me=$1 hits=0 n branch draft sha shared
  while read -r n branch draft; do
    [ -n "$n" ] || continue
    [ "$branch" = "$me" ] && continue
    if ! git rev-parse -q --verify "origin/$branch^{commit}" >/dev/null; then
      echo "carried: #$n $branch is not on origin (a fork?), unchecked" >&2; continue
    fi
    shared=$( { git cherry HEAD "origin/$branch" origin/main | awk '$1 == "-" { print $2 }'
                comm -12 <(git rev-list origin/main..HEAD | sort) \
                         <(git rev-list "origin/main..origin/$branch" | sort); } | sort -u)
    for sha in $shared; do
      hits=$((hits + 1))
      printf '#%s %s %s %s %s\n' "$n" "$([ "$draft" = true ] && echo draft || echo ready)" \
        "$branch" "${sha:0:9}" "$(git show --name-only --format= "$sha" | head -5 | tr '\n' ' ')"
    done
  done
  [ "$hits" -eq 0 ]
}

selftest() {
  local t; t=$(mktemp -d)
  if ( set -e; cd "$t"
    git init -q --bare origin.git; git clone -q origin.git w 2>/dev/null; cd w
    git config user.email t@t; git config user.name t
    git checkout -q -b main; echo a > a; git add a; git commit -qm base; git push -q origin main
    git checkout -q -b feature/doc; echo d > doc.md; git add doc.md; git commit -qm doc
    git push -q origin feature/doc
    git checkout -q -b feature/other main; echo o > o; git add o; git commit -qm other
    git push -q origin feature/other
    git checkout -q -b feature/me main; git cherry-pick feature/doc >/dev/null; git fetch -q origin
    # a copied commit is found, under a branch name with a slash; an unrelated PR and our own are not
    out=$(printf '1 feature/doc true\n2 feature/other false\n3 feature/me false\n' | carried feature/me) && exit 11
    [[ "$out" == "#1 draft feature/doc "*"doc.md"* ]] || exit 12
    [ "$(wc -l <<<"$out")" -eq 1 ] || exit 13
    # a commit carried with its own sha, which git cherry alone never lists
    git checkout -q -b feature/stacked origin/feature/doc; echo s > s; git add s; git commit -qm s
    out=$(printf '1 feature/doc false\n' | carried feature/stacked) && exit 14
    [[ "$out" == "#1 ready feature/doc "* ]] || exit 15
    printf '2 feature/other false\n' | carried feature/stacked >/dev/null || exit 16
    printf '' | carried feature/stacked || exit 17
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
    me=$(git rev-parse --abbrev-ref HEAD)
    prs=$(gh pr list -R "$1" --state open --limit 200 --json number,headRefName,isDraft \
          -q '.[] | "\(.number) \(.headRefName) \(.isDraft)"') || { echo "carried: gh pr list failed" >&2; exit 2; }
    carried "$me" <<<"$prs" ;;
  *) echo "usage: carried.sh <owner/repo> | --selftest" >&2; exit 2 ;;
esac
