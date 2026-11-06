# The ship contract, key by key

A repo declares how ship runs it in its `CLAUDE.md` / `AGENTS.md`, as a short list of
facts. The workflow is ship's; the contract only says what this repo's commands are. Every
key is optional, and the default is what a repo with no contract gets. Read a key's entry
here the first time a stage uses it. An absorb that touched the repo's `CLAUDE.md` or
`AGENTS.md` can change the contract under a running ship: reread it before the next step
(eca-finder's #296 turned `live:` from a hand deploy into merge-deploys mid-ship).

## `gates:`

The commands that must pass: tests, typecheck, production build. Default: whatever you can
find.

**Full or scoped.** Full gates run at BUILD's pre-flight, after an absorb that changed the
tree (REVIEW's runs before either reader starts), and at LAND's step 1 when the tree changed
since their last full run. Every other check,
each BUILD task and each TEST fix round, runs them **scoped**: the typecheck plus only the
tests the uncommitted change touches, by the contract's `scoped <cmd>` if it names one, else
the test runner's changed mode through the repo's own test script, so its pretest hooks run
(`npm test -- --changed`, `-- --onlyChanged` for jest; cells-app's bare `vitest run
--changed` skipped its pretest build and read 60 files red, CEL-132), else in full. The
runner picks the tests, never the driver: a gate script takes no list of test files.
eca-finder's v1 API ship named its files by hand and missed
`tests/convex/catalogApi.test.ts`, which `--changed` picks up on that diff, until
pre-flight's full run went red (2026-11-03). Six ships each running cells-app's full 3.5
minutes per task pushed the load past 150 and timed out load-sensitive tests; the scoped run
took 2 to 7 seconds on seven real changes and caught every failing file the full run did on
two planted bugs, 31 of 31 and 21 of 21 (2026-11-03). A scoped run that finds no tests for a
diff with code in it is a miss to check, not a pass: `vitest related` found none at all on
cells-app's multi-project config.

**How a gate runs.** With the Bash sandbox off, as are smokes and dev servers: they bind
ports and fetch fonts and packages by design, and under the sandbox they fail with `listen
EPERM` or a fetch error that reads as a real red (CEL-147 lost a 7-minute suite to 27 of
them). Each check goes through `route.py gate <cmd>`, which records the run for the ledger.
A multi-step gate run goes in a script file written with the Write tool, then `route.py
gate bash <file>`, since the worktree guard refuses long inline commands. That script
starts with `set -euo pipefail`: without it, `npm test | tail -8` exits with tail's code,
and CEL-180's script printed green over a failed test. Hold the runner's exit before any
filter, and filter with `grep -E` rather than `tail`, so a red names its failing test
(browser-replay reran a 90-second suite only to read the name tail had cut): `rc=0; <test
command> > <log> 2>&1 || rc=$?; grep -E 'FAIL|●|Test Files|Tests:? ' <log> || true; [ "$rc"
= 0 ]`, which stops the script on red and goes on to the next gate on green. A typecheck or
build filters for its own lines (`grep -E 'error' <log>`). A `|| true` on the test pipeline
itself turned six red tests green (CEL-182, CEL-260).

**Stopping a run early.** Kill its own process group: every Bash call runs in a group of
its own, so `kill -- -$(ps -o pgid= -p <runner pid> | tr -d ' ')` from another call takes
that run and nothing else, never a Mac-wide `pkill -f vitest`, which takes sibling ships'
runs with it.

**Red under load.** A run, full or scoped, whose only failures are in files the diff never touched,
under heavy load from sibling ships (timeouts, or a set that moves between unrelated files
from run to run), reruns just those files alone, through the repo's test script. If they
pass alone, it's load: both runs and the `uptime` load figure go in the commit or the
`result:` line, and it isn't root-caused. A scoped run picked each file because it imports
the diff, so there a file passes as load only when its time alone is under half its limit;
nearer the limit, the diff may be what slowed it, and it's a real red. A failure in a file
the diff touched is a real red. A second red on load waits
before the next run until the 1-minute load average (`sysctl -n vm.loadavg`) falls under
the core count (`sysctl -n hw.ncpu`), as a background wait; it never skips, deselects or
loosens a test to get past (cel-315). route.py counts every red run as a fix round, so a
task's first `route.py log` after a load red passes `fix_rounds=` counting only the real
reds, and `gates_first_pass=true` when its first run's only red was load; a `note=` re-log
carries neither (cel-301's scoped run timed out two untouched files at load 80 to 390).
The same holds when the contract's own landing script
runs the gates (cells-app's land-pr.sh): rerun the failed files alone, and when they pass,
run the landing script again (CEL-226 went red on two untouched files at a load near 150,
then landed on the rerun).

**Red on main too.** A red that isn't a timeout (a failed test, or an unhandled error with
every test passing), in a file the diff never touched, while `git diff --quiet origin/main
-- <the file and what it imports>` shows the branch left them as main has them, runs that
file alone five times through the repo's test script. Any failure there makes it main's, a
steady red or a flake, never fixed inside this ship: the PR and the `result:` line name it
with its rate, and it's a follow-up. The gate that lands the branch then runs once more,
after the load falls under the core count, and a pass lands it; a gate that stops on it
again parks (`gate:input`, `needs input:` naming the test, its rate and the runs), since
landing past a red is Pete's call. Five clean runs alone send it to Red under load above.
cel-312 and cel-333 both went red on an unhandled `ReferenceError` from a ProseMirror timer
after cells-app's `test/fileRoundTrip.test.ts`, with every test passing; alone it failed 1
of 5, and cel-333's second land-pr run passed and merged.

**A production build beside a dev server.** A production build in a worktree whose dev
server is up wipes the server's record in `.next`, so the repo's stop command later finds
nothing and the next start dies on EADDRINUSE (CEL-221, CEL-213): stop the dev server before
a build, start it again after.

**A ship whose job is load timeouts** ranks tests by duration from one loaded run, rather
than hand-writing a ranker (CEL-214 and CEL-228 each did): `npm test -- --reporter=json
--outputFile=<job tmp>/run.json` (through the repo's script, as above; jest takes `--json
--outputFile=`), then `jq -r '.testResults[].assertionResults[] | "\(.duration)
\(.fullName)"' <job tmp>/run.json | sort -rn | head -20`.

## `dev:`

The command that starts the worktree's own dev server on a port of its own and prints its
URL (cells-app: `npm run dev`, via `scripts/dev.sh`). Default: the repo's dev script,
detached. Another checkout's listener is never stopped: start this worktree's on a free
port (`PORT=<n>` by default) and read the port back from this command for every link,
smoke, test and app build after.

## `preview:`

A command that prints this branch's preview links, one per app, with each build's state
(cells-app: `scripts/preview-links.sh`, which reads Vercel). Ship runs it after every push
and posts what it prints. A contract may mark it `on demand` (cells-app: a push builds
nothing): then ship posts the localhost after each push and runs `preview:` once before
TEST, only when the change needs what localhost cannot show (the contract says what) or Pete
asks. Default: no hosted preview; the worktree's localhost is the only link.

## `test-auth:`

How the QA run signs in. `seed <how>` is a seeded account and a secret verify may use.
`form <how>` means the app's own sign-in form works with test credentials (Clerk test
instances: any address, code 424242), and verify may use it. `none` makes an auth-gated walk
`unverifiable`. The tricks a fresh account needs (Clerk's bot check, an invite code, a
redeem file) live in the repo's checks file under Sign in, where verify writes them back.

## `backend:`

- `copy [<app-dir>]` (the default where the repo has a `convex.json`): stage 0 gives the
  worktree its own Convex dev deployment, a copy of dev's functions, settings, data and
  stored files, with `scripts/branch-db.py` (app-dir: the folder holding `convex.json`,
  default the root; cells-app names the pack it runs). The worktree tests and breaks its
  copy, and landing puts it back on the shared database. SKILL.md stage 0 runs it.
- `shared-dev` (the default otherwise): previews and localhost use the app's dev database,
  ship never rewrites an env file, and it says so on the card, or in the `result:` line,
  when a branch changes a schema. Its rules: `reference/rare-cases.md`, Backends.
- `per-branch`: ship provisions a database preview per branch at stage 0 and deprovisions it
  at teardown. Its rules: `reference/rare-cases.md`, Backends.

## `stack:`

How to run `scripts/stack-check.sh` for the repo: the host team and the app projects, plus
where each app's Convex dev deployment and prod deploy key are. It checks that dev and prod
never cross: git link and production branch (`--production-branch <branch>` where it is not
main), protection, the Convex deploy key on Production only, every dev Convex setting present
on prod, Clerk `pk_live` on Production and `pk_test` elsewhere. A project with no production
yet is passed as `<project>:unreleased`, which skips the checks only a live app passes (the
deploy key, `pk_live`, prod's settings). Ship runs it before TEST and before landing; a ✗ is
ship's to fix, never Pete's. A ✗ on a project the repo itself marks unreleased (cells-app: its
`pack.json` says `"unreleased": true`) is the contract line missing `:unreleased`: rerun with
it, and fix the line in this PR (cel-323, cel-325, cel-285 each read four ✗ for yonder and
yeoman).

## `ios:` and `mac:`

- `ios:` for a native iOS app: the command that builds the branch's own app, pointed at the
  branch's server, installs it on a device by name ("iPhone PM" or a simulator), and prints
  its IOS line (device, udid, bundle id, and `dd=` for its build cache, `keep=yes` for an app
  every branch installs over). Default: none. verify's `reference/ios.md` runs it.
- `mac:` for a native Mac app: the command that builds the branch's own app, pointed at the
  branch's server, and prints its MAC line (the .app path, bundle id, and how the repo's
  checks skill drives it). Default: none. verify's `reference/mac.md` runs it.

Native repos have rules at the fork, BUILD and LAND: `reference/rare-cases.md`, Native app
repos.

## `worker:`

A long-running local process that serves main's code (a launchd job, a queue runner): the
command that restarts it and the check that says it is idle. It picks up a change only when
it restarts, so LAND restarts it after the merge, once idle, never with a job in flight,
which the restart would fail. Default: none; a repo with such a process and no line gets one
in this PR. Its rules: `reference/rare-cases.md`, Long-running workers.

## `deploy:`

The repo's own command that puts merged main live where the host doesn't build main itself
(a Worker deployed with `wrangler deploy` and no Workers Builds connected:
`wrangler deployments list` shows "Source: Unknown"). LAND runs it once, from the main
checkout after the merge and its pull, then watches what `live:` names. That is the repo's
command, so it is not a hand deploy. Default: none, meaning the host builds main or nothing
deploys. A repo that deploys by hand and has no line gets one in this PR, naming the command
its docs or `package.json` use (screendrop-worker, 2026-11-05).

## `smoke:`

The repo's automated end-to-end smoke, in two halves.

- `branch <cmd>` runs against the worktree's own server once, in BUILD's pre-flight, and
  again only if what the app carries changed before landing (LAND's step 1); never per
  milestone push or per task, because a smoke can cost real model calls (cells-app's: about
  12 bot turns, about 13 cents). Close the QA's browser pages and stop the branch's phone app
  first: their polling slowed a Swain reply past the smoke's 120 s wait, and the rerun with
  them closed passed (swain-goals-skills).
- `main <cmd>` runs once per landing, after the deploy watch, against what landing put live,
  or main's own server where main deploys nothing (cells-app: `local-pack.sh --restart`
  smokes main on localhost). It is the one check that sees ships together: each branch was
  tested alone, and two that land an hour apart are never walked side by side.

Each half runs once. A red whose failing step is a network error reaching a third party (a
connect timeout, a DNS failure, a reset) gets one rerun, said in the `result:` line; the app's
own server resetting is a crash, and any other red is real.
Default: none, and LAND's one load of each live URL is the whole check.

## `live:`

What landing on main deploys, and how to watch it. cells-app: "main is production; each
touched pack's Vercel production build pushes its Convex functions, then the app." Default:
nothing, and ship claims no deploy.

## `land:`

How a branch reaches main.

- `pr` (the default) squash-merges the tracker PR.
- `direct` pushes `HEAD:main` after a rebase and opens no PR.
- `auto`, for a repo whose main deploys nothing, lands on the QA run's `works` without
  waiting for Pete's "merge main" on a one-way door or a try-it change. A money path still
  waits for it, on every repo.
- Any other value is a command ship runs from the worktree in place of the merge (a mirror
  remote, a local-only main, a promote hook that builds on push); the command is the
  repo's, and ship never invents one.

Every value other than `pr`: `reference/rare-cases.md`, Landing variants.

## `release:`

For a repo whose main is a parking lot: the word that puts main on production and the
command it runs (cells-app: "release" runs `npm run release`). Ship runs it only on that
word, never as part of landing, and watches what `live:` names. Without it, landing is the
release wherever main deploys.

## `board:`

Where the repo's tickets live, how to file one, and what each column means (cells-app's
names them and says which a ship may file into). Default: none, and follow-ups stay in the
`result:` message.

## `ship: no`

For repos that shouldn't ship at all (wikis, civic work): decline and say why.
