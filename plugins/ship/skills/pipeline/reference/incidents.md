# Learned environment facts — from real failed runs

Facts about how this environment actually behaves, each learned from a real incident.
Consult the relevant section before merges, teardowns, deploys, or debugging a dispatch.
These are facts, not process — the process lives in SKILL.md.

## Worktrees & git

- **Eve's dev registry outlives its server** (2026-10-15). After a dev restart,
  `agents/<agent>/.eve/next-dev-server.json` still named the old eve dev port, and
  `withEve` reused it because the dying process still answered its 1 s probe. Delete
  that file before restarting a dev server in an Eve app.

- **Fifteen worktrees sat in cells-app after their ships landed** (2026-09-27). A
  session launched inside its worktree can't remove it, the sweep waited 12 hours and
  skipped any tree with a live session, and build lanes never counted as landed because
  they merge into their branch, not main. Now: `stage.sh <root> landed` at landing, a
  SessionEnd hook (`wt-sweep --end`) that removes a landed tree as its session closes,
  lanes removed right after they merge and swept when their changes are in the parent,
  and the sweep every 10 minutes.

- **A PR stacked on an unlanded branch stranded at "merge main"** (cells-app local-hosts,
  2026-09-25). Pete said to build on top of feature/muse-chat, still a draft (#19), so
  #24 took it as its base. At "merge main" #19 hadn't landed: reset onto origin/main,
  cherry-pick our commits and the two of theirs we needed, force-push, retarget. Branch
  off main and cherry-pick from the start.
- **Removing the worktree a session was launched in locks the session out** (same
  landing). The session's launch directory was the worktree, so `ExitWorktree` was a
  no-op; after `wt remove` the guard refused every Bash command, a subagent inherited
  the pin, and the only way out was recreating the directory by hand. Such a session
  merges from the worktree and removes it last, or leaves it to `wt-sweep`.
  An entered worktree removed without `ExitWorktree` first does the same to the next ship
  in that session (eca-finder thin-search, 2026-10-26): its cwd pointed at a deleted
  folder, `EnterWorktree` refused with "not in a git repository", Bash kept resetting
  there, and chrome-devtools would save shots only under the dead path, recreating it.
  joined-search had to drive its whole worktree by absolute path.
  `ExitWorktree` first doesn't prevent it (eca-finder class-id-followups, 2026-11-05): it
  answered that the session was back in the main checkout, and two Bash calls later the
  shell reset into the worktree `wt remove` had just deleted, and kept resetting there. The
  second ship's `EnterWorktree` took that folder as its origin, its `ExitWorktree` answered
  that the original directory no longer exists and stayed put, and chrome-devtools refused
  shots under the main checkout, the new worktree and the dead path alike; shots taken
  with no `filePath` still saved under the session's `tool-results/`.

- **The browser writes screenshots only inside the session's workspace roots**
  (2026-09-24, when gstack's `/browse` gave way to the chrome-devtools MCP). A verifier
  saving to `/tmp` got "Access denied: not within any of the configured workspace
  roots". The session's launch directory and its added directories are roots, and they
  stay put when the session enters a worktree; the scratchpad, the job's tmp and
  `~/.claude` are not. Hence `.ship-shots/<slug>/` under the launch directory, excluded
  from git (cel-315 wrote shots to the worktree it had entered and was refused).
  cel-300 (2026-11-05) went the other way: launched in cells-app's main checkout, it
  entered its worktree, compacted, and its first browser call was refused a redeem script
  under the main checkout and took the same file under the worktree. Hence verify tries
  the launch directory, then the worktree, then inline shots.
- **Landed worktrees piled up in cells, 82 GB of instances with them** (2026-09-24).
  Seven clean, merged worktrees sat for days, three holding a later ship's branch
  because a session had switched branches inside a finished tree; cells names each
  instance after the branch, so every switch orphaned one, and `wt remove` never ran
  `make wt-clean` anyway. Teardown misses from many causes (a crashed session, a closed
  terminal), so the backstop is `wt-sweep -f` hourly from launchd (`md.pete.wt-sweep`),
  skipping any worktree under 12h old, dirty, or with a live session; cells' own
  `pre-remove` hook runs `make wt-clean` on every removal.
- **Cross-repo `EnterWorktree` silently doesn't take.** It only adopts worktrees of the
  session's *primary* repo. Against any other repo the cwd never moves and the status
  line stays blind — the worktree and `.ship-stage` are real but invisible. Work by
  absolute path and narrate the fork (SKILL.md: Talking to Pete).
- **In a multi-repo workspace, the target repo is itself a recon finding.** A run forked
  in the repo the conversation was about; recon then established the feature needed zero
  changes there and landed entirely in a sibling repo. Fork-first stays (it's how Pete
  sees engagement), but when recon contradicts the fork: exit, `wt remove` the empty
  worktree, re-fork in the right repo, and narrate the move.
- **`gh pr merge --delete-branch` run from inside the worktree fails** with `fatal: 'main'
  is already used by worktree …`: the flag checks main out locally after the merge, the PR
  has merged on GitHub, and the teardown never runs, stranding an orphan worktree. LAND
  merges from the worktree without the flag, so nothing local runs, and deletes the branch
  from the main checkout at step 5.
- **A lane that borrowed `node_modules` by symlink committed the link** (cells,
  2026-09-19). Five lane worktrees symlinked `agent/`, `web/` and
  `electron/node_modules` to the main worktree's installs. The repo ignored
  `node_modules/`, which matches a directory and not a link, so one lane's `git add -A`
  tracked `agent/node_modules`, and merging that lane replaced the main worktree's real
  install with a link pointing at itself. Typecheck and build then failed with exit 127
  (`tsc: command not found`), which read as broken code. The fix was `git rm --cached`,
  a reinstall, and dropping the slash from the ignore pattern. Exclude the links in
  `info/exclude` before the first lane commit.
- **Tearing down a worktree before confirming its PR is `MERGEABLE`** strands the ship
  with no worktree and no merge — that recovery is all manual. Pre-flight first.
- **Squash merges from the GitHub UI don't satisfy `git branch --merged`** and don't
  delete the local branch. To prove a worktree landed, check
  `gh pr list --state merged --head <branch> --json number,headRefOid` against the
  worktree's HEAD.
- **A dirty main checkout may hold another session's uncommitted work.** Never ff or
  deploy from it — deploying would ship their unfinished work and miss your merge. Use a
  throwaway worktree pinned to `origin/main` for the deploy step.
- **A file written in main before the fork and copied, not moved, into the worktree**
  (cel-401-comal-pack, 2026-11-10): the design page, drawn while the session was still a
  chat, stayed untracked in cells-app's main checkout. Once #534 landed that path, the twin
  stopped local-pack.sh's `merge --ff-only`, main kept serving the old commit unsmoked, and
  land-pr exited 1. Such a file goes over with `mv`. When main's move still stops on an
  untracked file the branch adds, a copy this session wrote is removed and the move rerun
  (`local-pack.sh <pack> --restart` in cells-app); anyone else's waits for Pete, named in
  `result:`.
- **A pre-existing sibling worktree (Zero's convention) is not ship's to tear down** —
  the session and its dev server live there. Merge with `-R <owner/repo>` without
  `--delete-branch`, delete the remote branch explicitly, leave the worktree.
- **Mid-round `git merge` while a verifier is driving** left conflict markers in a
  hot-reloading file, broke the dev server under the verifier, and wasted the round.
  Freeze the tree while any verify round is live.
- **Review against a stale fork reviews apparent reversions** of other ships' work —
  full review runs have been wasted. Sync with origin/main before dispatching review,
  and again before the merge.
- **`git add -A` sweeps `.ship-stage` into commits.** The marker is untracked-but-present,
  so busy build stages commit it; one reached a PR and would have put a stale `review`
  marker on main, confusing the status line for every main-checkout session. Add it to
  `.git/info/exclude` right after writing it — session-local state never belongs in the
  repo's `.gitignore`.
- **An uncommitted artifact in a parked worktree is unprotected.** A GATE 1 spec sat
  uncommitted while the ship waited; a concurrent session's cleanup saw a branch with no
  commits and swept the worktree. Commit gate artifacts to the branch *before* firing the
  gate.
- **Screenshots don't belong in the branch, and don't survive teardown.** ~6MB of verify
  PNGs committed to a branch broke the push outright (sideband disconnect, branch had to
  be rebuilt); storyboard images left in the worktree 404'd on the published review card
  after `wt remove`. Keep them out of commits (`.ship-shots/`, excluded; SKILL.md says
  where), and copy anything a presented card references somewhere durable before the
  merge.

## GitHub

- **GraphQL runs out before REST.** `gh pr create`, `view`, `edit`, `ready` and `merge` all
  spend GitHub's GraphQL budget, which sibling ships on one token exhaust, and its secondary
  limit refuses while `gh api rate_limit` still shows budget (six eca-finder runs, 2026-10-29).
  The REST forms: `gh api repos/<o>/<r>/pulls -f head=<branch> -f base=main -f title=<t> -F
  body=@<file> -F draft=true` to open, `gh api -X PATCH repos/<o>/<r>/pulls/<n> -F
  body=@<file>` to edit, `gh api repos/<o>/<r>/pulls/<n> -q .mergeable_state` (`clean`, `has_hooks`, or `unstable` with
  only optional checks red, merges; `behind` absorbs main first; `unknown` means GitHub is still working it out: ask again; a PR whose head still names the
  old sha three minutes after a push that `git ls-remote` shows landed is stuck: push an
  empty commit (`git commit --allow-empty`) first; still stuck after a fast-forward push, a
  REST close then reopen (`-X PATCH .../pulls/<n> -f state=closed`, then `state=open`)
  resyncs it at once, but never after a force-push, which GitHub may refuse to reopen
  (cel-257's #358 sat 10 minutes),
  `gh api -X PUT repos/<o>/<r>/pulls/<n>/merge -f merge_method=squash -f sha=<head> -f
  commit_title='<title> (#<n>)' -F commit_message=@<body file>` to merge, so the squash commit
  takes the PR body, then `git push origin --delete <branch>`.
  Taking a PR out of draft has no REST form: wait on `gh pr ready` and retry it.
- **A background `git push` can hang on a credential prompt** no one sees.
  `GIT_TERMINAL_PROMPT=0 timeout 90 git push` fails fast instead (eca-finder, 2026-10-29).

## Backends & deploys

- **A retire question that named one zone's hosts** (homies-name, 2026-11-06): Pete was
  asked to retire the buzz tunnel "on hq, community and *.homezero.md", and its ingress also
  served buzz.cells.md, live. Before Pete is asked to retire shared infra (a tunnel, a
  Worker, a bucket), read its own config and list every host it serves, in every zone, not the zone's DNS
  alone: a tunnel's ingress (`cf zero-trust tunnels cloudflared configurations get <id>`
  for a remotely managed one, its local yml such as `~/.cloudflared/*.yml` otherwise, where
  that command comes back empty), a Worker's custom domains account-wide (`cf workers
  domains list`, since `routes list` reads one zone), a bucket's (`cf r2 buckets domains
  custom list`).

Most entries below are about `backend: per-branch`, a database preview per branch. Since
2026-10-14 a Convex repo defaults to `copy`: `branch-db.py` makes the worktree its own dev
deployment with `convex deployment create dev/<branch> --expiration`, and copies dev into it. A
local deployment was ruled out: it dies with `convex dev`, Stripe, Clerk and the phone can't
reach it, and its Node actions run on the Mac. Measured on homebody: about 95 seconds, 5,790
documents and 98 MB of stored files. The CLI can't delete a deployment, so the expiry is the
cleanup. `convex env set` reads stdin; `--from-file <(...)` sees an empty file. `convex import`
needs a folder with a package.json even with `--deployment`. A deployment runs one snapshot
export at a time ("already requested or in progress"), so two worktrees copying dev at once
queue; `branch-db.py` waits its turn. The clobbering entry below is why `shared-dev` is now an
opt-out. A ship that never ran `up` ran its dev server and smoke on shared dev until TEST
(save-files-to-mac, 2026-11-09), so `branch-db.py check` now prints one line while no app-dir
has a copy: `stage.sh` runs it at each flip after stage 0's, and `route.py` at each task it
logs, since BUILD's markers skip `stage.sh`. EXPRESS has neither between the fork and `test`, so
its pre-flight is still on the driver. A Convex repo with no `backend:` line and no
`convex.json` shares dev by default and stays quiet (homezero).

- **`launchctl bootstrap` right after `bootout` fails with "5: Input/output error"**
  (2026-10-14): the old job is still tearing down. Under `set -e` it killed an install
  script before its last plist was written, and an installer's own rollback hit it too and
  left the app down. Restarting a launchd service: bootout, poll until `launchctl print
  gui/$UID/<label>` fails, then bootstrap, retrying once on error 5.

- **Main is production, so the build does the production push (2026-09-24, cells-app).**
  A manual "network deploy after merge" step was forgotten or run from the wrong checkout;
  now each pack's Vercel production build pushes its Convex functions (drop check first)
  before building the app, with the deploy key only in the Production environment. Ship
  watches those builds after landing and never pushes a production database itself.
- **A session started on a deployment without an automation bypass never wakes again.** Eve
  sessions are durable workflows pinned to the deployment that started them, and behind
  Vercel's login wall the workflow queue's own callbacks get a challenge page unless that
  deployment carries an automation bypass as an env var. A new project's first sessions were
  born before the bypass existed: every later message to them was accepted (202) and never
  run, retried every 5 s as `ForbiddenError: This request requires a challenge`. Add the
  bypass before the first session; `stack-check.sh` flags a project without one. Sessions
  already stuck stay stuck: start a fresh account.
- **A Vercel project with no git link deploys to production on a plain `vercel deploy`.**
  So does any project's first deployment, a git push of a branch included: a new project's
  first branch push built as production and began a production build that would have pushed
  its database. Before a new project's first push, give it a placeholder production deployment
  (a static page from a scratch dir) with its database deploy key pulled, then restore the key.
  By hand, always `--target preview`.

- **A worktree building against a shared backend clobbers it** — pushing the branch's
  schema reconciles the shared plane to this branch and drops indexes other branches
  added. Per-branch preview backends exist for this; the shared dev deploy runs only
  from the main checkout.
- **A red `smoke: main` reading "Could not find public function" can be a shared dev
  backend that lost its functions, not the merge** (cel-402-parenting-pack: two other ships
  had hit it before the merge). The proof is the same error from before the merge, in a
  sibling ship's smoke or the land script's log; without it, revert as LAND says. With it,
  revert nothing: restore main's functions with the command the repo's contract or checks
  file names for that, from the main checkout, then run `smoke: main` once more, land
  script or not. With no command named, live functions that main lacks, or a production
  backend, the `result:` line names the missing functions for Pete instead.
- **The inherited `.env.local` is a loaded gun, and `--preview-name` does NOT override
  it.** `wt` reflinks the main checkout's env file into the worktree, carrying the SHARED
  dev deploy key; a per-command `export` doesn't survive to the next command. A bare
  `convex deploy` has landed on shared dev and reconciled it backward past six merged
  PRs. After provisioning, rewrite the worktree's Convex trio (`CONVEX_DEPLOY_KEY`,
  `NEXT_PUBLIC_CONVEX_URL`, `CONVEX_HTTP_URL`; drop `CONVEX_DEPLOYMENT`) before the first
  convex command, and confirm the first deploy's output host is the preview.
- **The preview's name is whatever provisioning slugified it to**, not the branch name.
  `feature/desk-doorway` provisioned as `feature-desk-doorway`; passing the branch
  verbatim silently created a SECOND preview, so deploys and seeds went to one backend
  while the browser read another. Read the name from
  the worktree's `.env.local` (`CONVEX_DEPLOYMENT=preview:<name>`) and use that
  everywhere; error loudly if it's absent.
- **A fresh verifier's unpinned CLI calls resolve to a different deployment than the app
  serves** — its seeds landed on one backend while localhost read another, and it
  reported the feature broken. Pin `--preview-name` / `--deployment` on every CLI call in
  a verify brief.
- **The Bash shell's cwd persists between calls.** A gates command ending in `cd flue`
  sent the next `convex deploy` from that subdir; Convex scaffolded an untracked
  `flue/convex/` and deployed ZERO functions over the preview backend. Anchor
  cwd-sensitive commands with the worktree root explicitly.
- **An auth-gated surface 403s on localhost when its secret lives only on the deployed
  Workers** — the admin console rendered while every admin API route failed, and it read
  as a broken feature. Before presenting, put the
  gate secret in the worktree's env, or say plainly which paths can't be exercised
  locally.
- **tsc + vitest green ≠ deployable.** Frameworks with their own production build
  (`next build`, `flue build`, wrangler/vite bundling) have failed on deploy after green
  tests. Run the production build in the pre-flight.
- **A dev server booted through a bounded pipe dies mid-verify.** `npm run dev 2>&1 |
  head -50` got SIGPIPE'd the moment `head` exited; the verifier reported "localhost
  refused connection". Detach with output redirected to a
  file (`nohup npm run dev > dev.log 2>&1 &`) and curl-probe before dispatching.
- **A batch once merged 18 green PRs onto a dev lane that had been red for an hour.**
  A red deploy is unfinished work on every lane — watch to conclusion.
- **`gh run list --commit` matches only the full 40-char SHA.** Armed with a short SHA
  from `git log --oneline`, the deploy watch returned `[]` forever while the run existed
  and succeeded. Use
  `$(git rev-parse <short-sha>)`.
- **Workflow concurrency can cancel your deploy run**; the superseding run's green reads
  as yours while the lane is mid-deploy. Watch the run for YOUR commit
  (`gh run list --commit <sha>`), and artifact-check the lane before handing back a URL.
- **Two sessions once raced identical fixes to a red shared lane** and one ship was
  thrown away. Check for an existing fix PR first; open a draft PR as the claim.
- **A diff that `live:` puts out in two parts, one at the merge and one at a later release,
  can send the first at a page production doesn't have yet.** cel-361's websites went live
  at the merge with Sign up and "Ask to join" pointing at `app.homezero.md/sign-up`, an app
  page that stayed 404 until Pete's release, and the run found it by chance at the review
  card. Before the merge, grep the lines the diff adds to merge-deployed files for the later
  part's host, and curl each URL found, link, fetch or redirect alike, on production. A page
  another ship put on main but not out counts too. Anything but 2xx parks
  (`stage.sh <root> gate:input`, `needs input:`) offering two passes, the app part landed
  and released before the links as Check the wiring lands a removal, or "merge now".

## Design & review

- **A server-down case met the phone's cache** (iosvoicepads, 2026-11-07): plan case 12
  stopped the server to show "The voices could not be loaded", but GET /api/voice/voices
  answers `public, max-age=86400` and the sheet keeps its list in memory, so the phone opened
  it from what it had. The Simulator's gallery showed the words, but it never fetches, so it
  proved the text renders, not the path. cells-app reaches a load error with a fresh launch
  under `CELLS_DEBUG_OFFLINE=1` (`NetworkPath.swift`), which fails before URLSession and its
  cache, with no server stopped.

- **Stopping the dev server cut off a bot turn** (the same ship): a worker run started
  seconds before the stop kept answering 500 while the walk went on, and the QA person's
  `DELETE /api/account` failed at its Eve wipe. cells-app's checks skill already says never
  to restart dev mid-turn, and the offline switch above needs no stop. Once that delete has
  failed at the Eve wipe, after its Plaid and connector revokes, the prune's own way out
  finishes it: Clerk's deleteUser, then `deleteOrphan` in `lib/account.ts`. Never before
  those revokes, since a connector grant outlives the Clerk user.

- **A test that forbids the old value breaks when the value comes back** (homezero-www,
  2026-11-07): packDocs asserted that no doc said "$1 trial", and Pete's move back to $1 at
  "merge main" broke it. A test for a changed value checks every copy against its one
  source, here `pack.trialUsd`, rather than pinning a copy to a literal or checking that the
  old value is gone.

- **A QA case whose starting state nothing reaches** (cel-278, 2026-11-06): "an approval
  it can't describe" had no live path, since the tool refuses every unknown write before
  an approval exists, and TEST spent a probe and a model turn before forcing a fetch failure
  from an initScript. A case names how its state is reached; one only a seed or a forced
  failure reaches says so, so the plan review can keep it as a defense or cut it.

- **A fix to motion proven on a still** (cells-faces, 2026-11-06): both readers found Mito's
  film specks orbiting the old bean's oval, and the fix resized the oval, while her membrane
  swells, dents, squashes and hops every frame. TEST's per-frame `requestAnimationFrame`
  sampler then found specks on or past her outline at 0.7 to 1.3 s and 16.0 to 21.7 s of the
  film. A fix to something that moves is checked over the whole loop before its commit: a
  test that samples the moving shape and the fixed parts at many times, or a browser
  sampler on `requestAnimationFrame` through `evaluate_script` (the repo's checks file may
  keep one), with the fixed parts kept inside the live shapes at every sample.

- **QA cases that walked apps the contract assumes work** (muse-icons, 2026-11-06): the
  plan walked five other packs' web colors, Swain's iPhone app and a Cells lab, while
  cells-app checks on Homebody only and says the other packs are the same code. At TEST,
  verify's "partial is unverifiable" met that rule and the run settled it from memory at
  landing. The walks go on the app the contract checks, a lab switched on there, and a
  frame that app lacks on one that has it (cells-faces drew Cells' faces); another
  app's part of a shared frame is its own tests, under its own switch where the diff changed its
  files (muse-icons edited four packs' `skin.css`; `PACK=swain` runs `skin.test.ts`), never a
  step (verify: Write qa.md).

- **Safari won't load local CSS into a storyboard's srcdoc frames over file://**
  (2026-10-13). When Pete wants a storyboard in Safari, serve its folder over http
  (`python3 -m http.server`) and open that; Chrome is fine with file://.
- **A plan once specced a fresh `events` table the repo already had** — three tasks got
  rewritten mid-build. The reuse audit (grep the whole repo for every core noun,
  data layer included) exists because of this.
- **A hypothesized bug cause once produced a fix that would have made an agent fabricate
  data** — the real cause was a 500ing dependency. Bug-shaped asks get an empirical
  root-cause check before the spec commits to a cause.
- **A run once designed against a repo's old cream mockups while the live product had
  moved to a dark terminal UI** — caught at GATE 1, whole spec redone. The running app is
  the design source of truth, never in-repo mockups.
- **A deprecated page serves happily.** A feature was designed, approved and built onto a
  public route the repo had abandoned; Pete caught it mid-REVIEW and the work had to move.
  "Grounded in the live product" proves a surface *renders*, not that it's *current* —
  classify liveness (on the current design system? reachable from primary nav? touched by
  recent commits?) and name the chosen surface explicitly in the spec.
- **The first design artifact read as a document, not a design** (Pete, 2026-09-03: "it's
  more of a document and less like working with a designer who gives me HTML which is
  mostly just mockups of the app"). Round 1 had a TL;DR, research sections and a scope
  contract with the comps somewhere below. DISCOVER now opens with a storyboard — frames
  of the app at ship size, captions, the questions — and the spec is written after his
  go, never before.
- **Idealized-input tests hide writer/reader contract drift.** Unit tests over hand-built
  rows passed while the real ledger writers produced garbage for two of three metrics
  (one always 100%, one always null); only the adversarial review caught it. A task that
  computes from rows another code path writes needs at least one case through the real
  writer.
- **A fix that rebuilds the rule a finding was about is code no reader has seen**
  (eca-finder stable-class-ids, 2026-11-05: the first fix redesigned the id rule, and a read
  of it found 12 real, two high). A fix rebuilds the rule when it changes what the rule
  decides for inputs no finding named (a new state, a rewritten branch), not when it adds
  the case a finding named. It gets one delta read before TEST: the other lab's reader
  where the lane has one, else the lane's reader in a fresh context; the branch brief with
  `git diff <sha before the fix>..HEAD` as the diff and the findings it fixed in place of
  the plan's tasks; logged `review=<wonder|fable|opus> stage=delta`, which `route.py readers`
  doesn't count as a branch read. Its findings join the triage file.
- **A stateful rule that keeps drawing findings has a hole the readers can't size.** Reads
  two, three and four of the same ship each found one more move sequence that lost an id,
  and each fix patched that sequence; a seeded fuzz written after the fourth failed 100 of
  200 runs of eight moves, and a rebuilt rule, each row storing the id it handed on, held
  2,000. When any read after the first finds a new real case in a rule a fix already
  touched, write a seeded property test before the next fix (random sequences of the inputs
  the findings used, one invariant), run the current code through it, fix the rule rather
  than the case, and commit the test with the fix. A delta read's finding that would rebuild
  the rule again comes here, not to another delta read. The harness counts an effect inside
  the mock once it succeeds, or reads vitest's `mock.settledResults`, never an async mock's
  `mock.results`, which records a rejected call as type "return": hello-straight-in's first
  harness counted every failed tell as delivered and read green on broken code. A test the
  branch adds or gives more work whose time alone, times 25, passes the runner's default timeout gets
  its own of that size when it's written, since load slows a run that much (cel-303's land
  run at 446 on 18 cores), and cel-284's 500-case fuzz ran 3.1 s alone and timed out at
  vitest's 5 s at load 130; an untouched test's limit: contract.md, Red under load.
- **A QA case can press a control main doesn't have.** cel-332's plan copied the card's
  acceptance criteria as cases: the phone's long-press strip showed no chosen mark, and
  neither app let you react to your own line, which cost a fix round and a step rewritten
  mid-walk. Each control a case presses either exists on main, found in its code or a
  snapshot before the plan is written, or is built by a task the plan names.
- **A read still out while QA walks moves code the walk proved** (the same ship: a read
  launched mid-walk led to a fix that changed what step 7 had proved, and step 7 ran
  again). No read is out when the walk starts and none starts during it; a fix made after
  the walk reruns the steps it touched.

## The worktree guard

Inside a worktree session the harness refuses any command it can't prove stays in the
worktree, and it misreads some that do. Each of these was refused in a real run; the fix is
always a script file in the job's tmp (Write tool), run by its path typed out in full, or
one plain command per call.
- `$(git …)` substitutions, `git merge-base` inside one too; a redirect of git's output
  (`git show <ref>:<path> > <file>`); a `git diff` on a computed path. Conflict triage hits
  all three.
- `cd <dir> && git …`, and any command on the main checkout (`cd <main> && git`, `git -C
  <main>`) while the session sits in the worktree.
- A script wrapped in a redirect with a chained `echo $?` or `tail` (CEL-229's land-pr
  call): start it bare with `run_in_background` and read its output file.
- Loops and heredocs that name git; a heredoc, a loop or a program named by a variable at
  all (six refusals in eca-finder's v1 API ship); `sed -i` chains (one run hit the guard
  eight times reaching for them).
- A computed script path, `python3 "$TMPDIR/x.py"`, or a `$VAR` argument even to a binary
  that isn't git (`sed -n 1,9p "$R"`); a stage script called through a shell variable.
- Process substitution (`jq … <(sed …)`), and a `<cmd>; cd <dir> && <cmd>` compound even of
  read-only commands that aren't git (cel-300 lost three calls to these and a `$VAR`
  operand): one plain call each, or a script file.
- Read-only commands it misparses: a path segment named `source`, a zsh `echo ==`, a `for`
  loop over `sed`, a heredoc that only writes files, a docker `--format '{{…}}'` string, a
  `python3 -` heredoc whose text says "git", a jq string interpolation `"\(…)"` even in one
  `gh … -q` call.
- `ref=$(…)` then `press "$ref"` inline (CEL-223 lost five rounds to it).
- Quoted JSON on a command line (`decisions.py log '{…}'`): use `log --file <json>`.
- `set -a && . ./.env.local`: give the tool the file instead (`tsx --env-file=.env.local`,
  `node --env-file=.env.local`).
- A process substitution (`comm -12 <(…) <(…)`).

Two runs lost 40 commands to split-and-retry, and two more lost about ten each
(2026-10-05).

## Dispatch

Lessons from handing work to a subagent, kept where they hold for any worker; the history
of building through other engines is in git.

- **A reader that exits 0 without writing its result did not run** (2026-09): a review hit
  an unrelated skill-loading error and stopped in seconds. A missing or empty result file
  is never a clean bill; a plain retry of the identical command produced five genuine
  findings, two of them serious.
- **Runs killed at a 2-minute timeout got mislogged as failures** — they were healthy
  high-effort runs that hadn't written anything yet. **Slow is not failure; unknown is.**
  Give a dispatch a generous window and check in rather than killing; escalate on a wrong
  diff or a run with no sign of life, never on a slow one.
- **A worker has auto-opened PRs and committed unprompted** — git stays with the driver,
  whoever drafts. One also committed its own result markdown into the repo, and a `--hard`
  reset cleaning that up ate an unstaged driver edit: a worker reports its result and
  never commits, and workers never run `git reset/checkout/stash`.
- **A vague brief costs more than it saves** — the fix rounds eat the delegation savings
  outright. Exact files, signatures, test cases, constraints, or write it inline.
- **A read-only brief needs the driver to check it held** — nothing enforces read-only at
  the tool layer for a general subagent. A design-QA round briefed as judge-only applied
  its own fixes to a tree the driver believed was frozen. Eyeball `git status` after any
  verify or QA walk; dirt means the round was incomplete, not that the feature works.
- **A touch-only file allowlist collides with "whole suite green"** whenever the planned
  behavior change invalidates an assertion in a test file outside the list — two of three
  dispatches stopped mid-run to ask permission, each costing a resume round-trip. Briefs
  say so up front: test files whose assertions the change invalidates are always in scope.
- **`muse.py` writes `last.md` only after its frame loop ends**, so a wrapper killed after
  Wonder's turn completed, by a session restart, leaves no `last.md` (save-files-to-mac,
  2026-11-09). The answer is still in `<out-dir>/events.jsonl`: the last `item/completed`
  agentMessage whose `messagePhase` is `finalAnswer`.
