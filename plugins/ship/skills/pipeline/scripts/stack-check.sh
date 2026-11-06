#!/bin/bash
# stack-check: is this app's Vercel + Convex + Clerk wiring split cleanly into dev and prod?
# Reads each Vercel project and flags anything crossed. Values are never printed.
#   usage: stack-check.sh --scope <team> [--production-branch <branch>] <project>[:unreleased] ...
# A project marked :unreleased has no production yet, so the checks only a live app can pass
# (the Production deploy key, pk_live, prod's Convex settings) print as skipped, not crossed.
# Checks, per project:
#   git      linked to a repo, production branch main (or --production-branch, for a repo
#            that builds production from a release branch)
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
prod=main
[ "${1:-}" = --scope ] && { scope=$2; shift 2; }
[ "${1:-}" = --production-branch ] && { prod=$2; shift 2; }
[ -n "$scope" ] && [ $# -gt 0 ] || { sed -n '3p' "$0"; exit 2; }
auth="$HOME/Library/Application Support/com.vercel.cli/auth.json"
[ -f "$auth" ] || auth="$HOME/.local/share/com.vercel.cli/auth.json"
token=${VERCEL_TOKEN:-$(jq -r .token "$auth" 2>/dev/null)}
api() { curl -s -H "Authorization: Bearer $token" "https://api.vercel.com$1"; }
team=$(api "/v2/teams/$scope" | jq -r '.id // empty')
[ -n "$team" ] || { echo "no Vercel team '$scope' for this login" >&2; exit 2; }
tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT
bad=0
say() {
  printf '  %-7s %s %s\n' "$1" "$2" "$3"
  case "$2" in "✗") bad=1; crossed=$((crossed + 1)) ;; "?") unchecked=$((unchecked + 1)) ;; esac
  return 0
}
skip() { say "$1" "–" "unreleased: $2"; }

for arg in "$@"; do
  project=${arg%:unreleased}; unreleased=; [ "$project" != "$arg" ] && unreleased=1
  crossed=0; unchecked=0
  echo "$project${unreleased:+ (unreleased)}"
  info=$(api "/v9/projects/$project?teamId=$team")
  repo=$(jq -r '.link.repo // empty' <<<"$info"); branch=$(jq -r '.link.productionBranch // empty' <<<"$info")
  if [ -z "$repo" ]; then say git ✗ "not linked to a repo: a push deploys nothing, and a plain vercel deploy lands on production"
  elif [ "$branch" != "$prod" ]; then say git ✗ "production branch is '$branch', not $prod"
  else say git ✓ "$(jq -r '.link.org // .link.projectNamespace // ""' <<<"$info")/$repo, production = $prod"; fi

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
    "") [ -n "$unreleased" ] && skip convex "no Production deploy key yet" || say convex ✗ "no CONVEX_DEPLOY_KEY on Production: the production build cannot push functions" ;;
    *) say convex ✗ "CONVEX_DEPLOY_KEY on $key: only Production may hold it" ;;
  esac

  # Convex settings: the prod deployment must carry every setting name the dev one has (a
  # fresh prod deployment starts empty, and its first push fails on the first one missing).
  # Needs CONVEX_DEV_<PROJECT> (a CONVEX_DEPLOYMENT like dev:happy-cat-123) and the prod
  # deploy key in ~/.config/<project>/convex-prod-deploy-key; skipped without them.
  dev_ref=$(printenv "CONVEX_DEV_$(tr '[:lower:]-' '[:upper:]_' <<<"$project")")
  prod_key="$HOME/.config/$project/convex-prod-deploy-key"
  if [ -n "$unreleased" ]; then
    skip convex "prod's settings not compared"
  elif [ -z "$dev_ref" ] || [ ! -f "$prod_key" ] || [ -z "${CONVEX_DIR:-}" ]; then
    say convex "?" "prod's settings not compared (needs CONVEX_DEV_<PROJECT>, the prod key file and CONVEX_DIR)"
  else
    names() { (cd "$CONVEX_DIR/$project" 2>/dev/null || cd "$CONVEX_DIR"; env NODE_OPTIONS=--no-warnings "$@" npx convex env list 2>/dev/null | cut -d= -f1 | sort); }
    missing=$(comm -23 <(names CONVEX_DEPLOYMENT="$dev_ref") <(names CONVEX_DEPLOY_KEY="$(cat "$prod_key")") | tr '\n' ' ')
    [ -z "$missing" ] && say convex ✓ "prod has every setting dev has" || say convex ✗ "prod is missing: $missing"
  fi

  for target in production preview development; do
    file="$tmp/$project.$target"
    # a failed pull is a cross naming the pull, never "no key": cel-139's sandboxed pulls said
    # live Homebody's Production had none, though the API lists it
    if ! pulled=$(vercel env pull "$file" --environment "$target" --project "$project" --scope "$scope" --yes 2>&1); then
      say clerk ✗ "$target env not pulled: $({ grep -i -m1 error || tail -1; } <<<"$pulled" | cut -c1-90)"; continue
    fi
    pk=$(grep -E '^NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=' "$file" 2>/dev/null | cut -d= -f2- | tr -d '"')
    hidden=$(jq --arg t "$target" '[.envs[] | select(.key == "NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY" and .type == "sensitive"
      and .gitBranch == null and ((.target // []) | index($t)))] | length' <<<"$envs" 2>/dev/null)
    if [ -z "$pk" ] && [ "${hidden:-0}" -gt 0 ]; then
      say clerk "?" "$target key unreadable (stored as sensitive)"; continue
    fi
    want=pk_test_; [ "$target" = production ] && want=pk_live_
    if [ -n "$unreleased" ] && [ "$target" = production ] && [ "${pk:0:8}" != pk_live_ ]; then
      skip clerk "Production not on live Clerk yet"; continue
    fi
    case "$pk" in
      "") say clerk ✗ "$target has no Clerk publishable key" ;;
      "$want"*) say clerk ✓ "$target on ${want%_}" ;;
      pk_*) say clerk ✗ "$target on ${pk:0:7}, wants ${want%_}" ;;
      *) say clerk "?" "$target key unreadable (stored as sensitive)" ;;
    esac
  done
  if [ "$crossed" != 0 ]; then echo "  = $project: $crossed crossed"
  elif [ "$unchecked" != 0 ]; then echo "  = $project: nothing crossed, $unchecked unchecked"
  else echo "  = $project clean"; fi
done
exit $bad
