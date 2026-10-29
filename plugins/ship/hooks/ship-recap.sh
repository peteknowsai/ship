#!/bin/bash
# /ship recap after a compaction. Registered as a SessionStart hook with matcher "compact":
# whatever it prints lands in the fresh context, so a squeezed session rereads the ship's
# state from disk (marker, saved task list, done tasks, branch commits) instead of trusting
# the summary. Silent outside a ship. `ship-recap.sh --selftest` is its check.

recap() {
  local input sid ptr root stage branch route done_file base
  input=$(cat)
  sid=$(printf '%s' "$input" | jq -r '.session_id // empty' 2>/dev/null)
  ptr="$HOME/.claude/ship-active/${sid:-none}"
  if [ -n "$sid" ] && [ -s "$ptr" ]; then root=$(head -1 "$ptr")
  else
    local cwd; cwd=$(printf '%s' "$input" | jq -r '.cwd // empty' 2>/dev/null)
    root=$(git -C "${cwd:-.}" rev-parse --show-toplevel 2>/dev/null) || return 0
  fi
  [ -f "$root/.ship-stage" ] || return 0
  stage=$(head -1 "$root/.ship-stage" | tr -d ' \n')
  branch=$(git -C "$root" branch --show-current 2>/dev/null)
  route="$root/.ship-route.json"; done_file="$root/.ship-done"
  echo "/ship recap after compaction, read from disk (trust it over the summary):"
  echo "- worktree $root, branch ${branch:-?}, stage $stage"
  local tasks=""
  if [ -f "$route" ]; then
    tasks=$(jq -r --rawfile done <( [ -f "$done_file" ] && cat "$done_file" || true ) '
      ($done | split("\n") | map(select(length > 0))) as $d
      | "- plan " + (.plan // "path not saved") + ", "
        + ([.tasks[] | select(((.label // (.n|tostring)) as $l | $d | index($l)) or ((.n|tostring) as $n | $d | index($n)))] | length | tostring)
        + " of " + (.tasks | length | tostring) + " tasks logged",
        (.tasks[] | "  " + (if (((.label // (.n|tostring)) as $l | $d | index($l)) or ((.n|tostring) as $n | $d | index($n))) then "done " else "todo " end) + .title + (if .engine == "fable" then " [fable]" else "" end))
    ' "$route" 2>/dev/null)
    printf '%s\n' "$tasks"
  fi
  # A fable task's report dies with the old context, so its files may be built and unchecked.
  grep -q '^  todo .*\[fable\]$' <<<"$tasks" &&
    echo "- a todo [fable] task may already be built by a subagent whose report is gone: treat its files as unchecked, compile and run its tests before you accept them (CEL-140)"
  base=$(git -C "$root" merge-base HEAD origin/main 2>/dev/null || git -C "$root" merge-base HEAD main 2>/dev/null)
  if [ -n "$base" ]; then
    echo "- commits on the branch:"
    git -C "$root" log --oneline "$base"..HEAD | head -20 | sed 's/^/  /'
  fi
  local dirty; dirty=$(git -C "$root" status --short 2>/dev/null | grep -v ' \.ship-' | head -10)
  # Build tools rewrite these on their own; say so, or a resumed driver treats them as work.
  [ -n "$dirty" ] && { echo "- uncommitted:"; printf '%s\n' "$dirty" |
    sed -E 's/^/  /; s/(Package\.resolved|next-env\.d\.ts)$/& (build noise: restore it)/'; }
  echo "Before the next step: reread the plan and the pipeline skill's section for this stage, then post Pete the one-line status."
}

selftest() {
  local tmp fails=0 out
  tmp=$(mktemp -d); trap 'rm -rf "$tmp"' RETURN
  git init -q -b main "$tmp/repo" && cd "$tmp/repo" || return 1
  git -c user.email=t@t -c user.name=t commit -q --allow-empty -m base
  git checkout -q -b feature/x
  echo a > a.txt && git add a.txt && git -c user.email=t@t -c user.name=t commit -q -m "task 1 lands"
  echo 'build:1:2' > .ship-stage; printf '1\n' > .ship-done
  echo '{"plan":"/p/plan.md","tasks":[{"n":1,"label":"1","title":"Task 1: first"},{"n":2,"label":"2","title":"Task 2: second","engine":"fable"}]}' > .ship-route.json
  echo b > b.txt; echo n > next-env.d.ts
  out=$(printf '{"session_id":"","cwd":"%s"}' "$tmp/repo" | recap)
  check() { if eval "$2"; then echo "  ok   $1"; else echo "  FAIL $1"; fails=$((fails+1)); fi; }
  check 'names the stage and branch' '[[ "$out" == *"branch feature/x, stage build:1:2"* ]]'
  check 'counts logged tasks and marks each' '[[ "$out" == *"1 of 2 tasks logged"* && "$out" == *"done Task 1: first"* && "$out" == *"todo Task 2: second"* ]]'
  check 'flags a fable task as possibly built and unchecked' '[[ "$out" == *"todo Task 2: second [fable]"* && "$out" == *"report is gone"* && "$out" != *"first [fable]"* ]]'
  check 'lists the branch commits and uncommitted files, not ship files' '[[ "$out" == *"task 1 lands"* && "$out" == *"b.txt"* && "$out" != *".ship-done"* ]]'
  check 'marks build churn as noise, and only that' '[[ "$out" == *"next-env.d.ts (build noise"* && "$out" != *"b.txt (build"* ]]'
  printf '1\n2\n' > .ship-done
  out=$(printf '{"session_id":"","cwd":"%s"}' "$tmp/repo" | recap)
  check 'no fable warning once its task is logged' '[[ "$out" == *"done Task 2: second [fable]"* && "$out" != *"report is gone"* ]]'
  out=$(printf '{"session_id":"","cwd":"%s"}' "$tmp" | recap)
  check 'silent outside a ship' '[ -z "$out" ]'
  echo "ship-recap self-test: $fails failed"
  [ "$fails" = 0 ]
}

if [ "${1:-}" = --selftest ]; then selftest; exit; fi
recap
exit 0
