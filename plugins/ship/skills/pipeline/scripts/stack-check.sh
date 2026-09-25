#!/bin/bash
# stack-check: is this app's Vercel + Convex + Clerk wiring split cleanly into dev and prod?
# Reads each Vercel project and flags anything crossed. Values are never printed.
#   usage: stack-check.sh --scope <team> <project> [<project>...]
# Checks, per project:
#   git      linked to a repo, production branch main
#   guard    protection at least all_except_custom_domains (the custom domain may be public,
#            every *.vercel.app URL needs a login)
#   convex   CONVEX_DEPLOY_KEY on Production only (the production build pushes functions)
#   clerk    pk_live on Production, pk_test on Preview and Development
#   bypass   an automation bypass exposed as an env var: behind the login wall, a durable
#            workflow's own queue callbacks are refused without it, and a session started
#            on a deployment that lacked it never wakes again
# Exit 1 when anything is crossed. Uses the vercel CLI's own login (or VERCEL_TOKEN).
set -uo pipefail
scope=""
[ "${1:-}" = --scope ] && { scope=$2; shift 2; }
[ -n "$scope" ] && [ $# -gt 0 ] || { sed -n '3p' "$0"; exit 2; }
auth="$HOME/Library/Application Support/com.vercel.cli/auth.json"
[ -f "$auth" ] || auth="$HOME/.local/share/com.vercel.cli/auth.json"
token=${VERCEL_TOKEN:-$(jq -r .token "$auth" 2>/dev/null)}
api() { curl -s -H "Authorization: Bearer $token" "https://api.vercel.com$1"; }
team=$(api "/v2/teams/$scope" | jq -r '.id // empty')
[ -n "$team" ] || { echo "no Vercel team '$scope' for this login" >&2; exit 2; }
tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT
bad=0
say() { printf '  %-7s %s %s\n' "$1" "$2" "$3"; [ "$2" = "✗" ] && bad=1; return 0; }

for project in "$@"; do
  echo "$project"
  info=$(api "/v9/projects/$project?teamId=$team")
  repo=$(jq -r '.link.repo // empty' <<<"$info"); branch=$(jq -r '.link.productionBranch // empty' <<<"$info")
  if [ -z "$repo" ]; then say git ✗ "not linked to a repo: a push deploys nothing, and a plain vercel deploy lands on production"
  elif [ "$branch" != main ]; then say git ✗ "production branch is '$branch', not main"
  else say git ✓ "$(jq -r '.link.org // .link.projectNamespace // ""' <<<"$info")/$repo, production = main"; fi

  guard=$(jq -r '.ssoProtection.deploymentType // "none"' <<<"$info")
  case "$guard" in
    all_except_custom_domains) say guard ✓ "custom domain public, every vercel.app URL behind login" ;;
    all) say guard ✓ "everything behind login (the custom domain too: switch to all_except_custom_domains to go public)" ;;
    *) say guard ✗ "protection '$guard': preview URLs are public" ;;
  esac
  if [ "$guard" != none ]; then
    if jq -e '[.protectionBypass // {} | to_entries[] | select(.value.scope=="automation-bypass" and .value.isEnvVar)] | length > 0' <<<"$info" >/dev/null; then
      say bypass ✓ "automation bypass on every new deployment"
    else
      say bypass ✗ "no automation bypass: background jobs (Eve sessions, workflows) are refused by the login wall; add one before the first session"
    fi
  fi

  envs=$(api "/v10/projects/$project/env?teamId=$team")
  targets_of() { jq -r --arg k "$1" '[.envs[] | select(.key==$k) | .target[]] | unique | join(",")' <<<"$envs"; }
  key=$(targets_of CONVEX_DEPLOY_KEY)
  case "$key" in
    production) say convex ✓ "deploy key on Production only" ;;
    "") say convex ✗ "no CONVEX_DEPLOY_KEY on Production: the production build cannot push functions" ;;
    *) say convex ✗ "CONVEX_DEPLOY_KEY on $key: only Production may hold it" ;;
  esac

  # Convex settings: the prod deployment must carry every setting name the dev one has (a
  # fresh prod deployment starts empty, and its first push fails on the first one missing).
  # Needs CONVEX_DEV_<PROJECT> (a CONVEX_DEPLOYMENT like dev:happy-cat-123) and the prod
  # deploy key in ~/.config/<project>/convex-prod-deploy-key; skipped without them.
  dev_ref=$(printenv "CONVEX_DEV_$(tr '[:lower:]-' '[:upper:]_' <<<"$project")")
  prod_key="$HOME/.config/$project/convex-prod-deploy-key"
  if [ -n "$dev_ref" ] && [ -f "$prod_key" ] && [ -n "${CONVEX_DIR:-}" ]; then
    names() { (cd "$CONVEX_DIR/$project" 2>/dev/null || cd "$CONVEX_DIR"; env NODE_OPTIONS=--no-warnings "$@" npx convex env list 2>/dev/null | cut -d= -f1 | sort); }
    missing=$(comm -23 <(names CONVEX_DEPLOYMENT="$dev_ref") <(names CONVEX_DEPLOY_KEY="$(cat "$prod_key")") | tr '\n' ' ')
    [ -z "$missing" ] && say convex ✓ "prod has every setting dev has" || say convex ✗ "prod is missing: $missing"
  fi

  for target in production preview development; do
    file="$tmp/$project.$target"
    vercel env pull "$file" --environment "$target" --project "$project" --scope "$scope" --yes >/dev/null 2>&1
    pk=$(grep -E '^NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=' "$file" 2>/dev/null | cut -d= -f2- | tr -d '"')
    want=pk_test_; [ "$target" = production ] && want=pk_live_
    case "$pk" in
      "") say clerk ✗ "$target has no Clerk publishable key" ;;
      "$want"*) say clerk ✓ "$target on ${want%_}" ;;
      pk_*) say clerk ✗ "$target on ${pk:0:7}, wants ${want%_}" ;;
      *) say clerk "?" "$target key unreadable (stored as sensitive)" ;;
    esac
  done
done
exit $bad
