# Learned environment facts — from real failed runs

Facts about how this environment actually behaves, each learned from a real incident.
Consult the relevant section before merges, teardowns, deploys, or debugging a dispatch.
These are facts, not process — the process lives in SKILL.md.

## Worktrees & git

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

- **The browser writes screenshots only inside the session's workspace roots**
  (2026-09-24, when gstack's `/browse` gave way to the chrome-devtools MCP). A verifier
  saving to `/tmp` got "Access denied: not within any of the configured workspace
  roots". The session's working directory and its added directories are roots; the
  scratchpad and `~/.claude` are not. Hence `.ship-shots/<slug>/` under the session's
  working directory, excluded from git.
- **Landed worktrees piled up in cells, 82 GB of instances with them** (2026-09-24).
  Seven clean, merged worktrees sat for days, three holding a later ship's branch
  because a session had switched branches inside a finished tree; cells names each
  instance after the branch, so every switch orphaned one, and `wt remove` never ran
  `make wt-clean` anyway. Teardown misses from many causes (a Codex session, a closed
  terminal), so the backstop is `wt-sweep -f` hourly from launchd (`md.pete.wt-sweep`),
  skipping any worktree under 12h old, dirty, or with a live session; cells' own
  `pre-remove` hook runs `make wt-clean` on every removal.
- **Cross-repo `EnterWorktree` silently doesn't take.** It only adopts worktrees of the
  session's *primary* repo. Against any other repo the cwd never moves and the status
  line stays blind — the worktree and `.ship-stage` are real but invisible. Work by
  absolute path and narrate the fork (see the narration contract).
- **In a multi-repo workspace, the target repo is itself a recon finding.** A run forked
  in the repo the conversation was about; recon then established the feature needed zero
  changes there and landed entirely in a sibling repo. Fork-first stays (it's how Pete
  sees engagement), but when recon contradicts the fork: exit, `wt remove` the empty
  worktree, re-fork in the right repo, and narrate the move.
- **`gh pr merge` run from inside the worktree fails** with `fatal: 'main' is already
  used by worktree …` — the PR merges on GitHub but local teardown never runs, stranding
  an orphan worktree. Merge from the main checkout, always.
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

## Backends & deploys

Most entries below are about `backend: per-branch`, a database preview per branch. The
default since 2026-09-24 is `shared-dev`: previews and localhost use the app's dev database
and ship edits no env file, because a solo dev rarely has two branches changing one schema
at once, and the card says so when one does. The clobbering entry below is the reason to
opt a repo into `per-branch`.

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
  while the browser read another — three verification rounds burned. Read the name from
  the worktree's `.env.local` (`CONVEX_DEPLOYMENT=preview:<name>`) and use that
  everywhere; error loudly if it's absent.
- **Convex previews hold stage-0 code and drift behind every `convex/` commit.**
  Re-push before the smoke-walk: `npx convex deploy --preview-name <name> -y`.
- **Absorbing main can bring function skew the gates can't see.** A rebase pulled in a
  new Convex function the branch's preview didn't have; tsc, vitest and `next build` were
  all green and the page hard-crashed on the preview. After any sync whose diff touched
  `convex/`, re-deploy the preview before further verification.
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
  as a broken feature (Pete reported "delete doesn't work"). Before presenting, put the
  gate secret in the worktree's env, or say plainly which paths can't be exercised
  locally.
- **tsc + vitest green ≠ deployable.** Frameworks with their own production build
  (`next build`, `flue build`, wrangler/vite bundling) have failed on deploy after green
  tests. Run the production build in the smoke-walk.
- **A dev server booted through a bounded pipe dies mid-verify.** `npm run dev 2>&1 |
  head -50` got SIGPIPE'd the moment `head` exited; the verifier reported "localhost
  refused connection" and a full round was wasted. Detach with output redirected to a
  file (`nohup npm run dev > dev.log 2>&1 &`) and curl-probe before dispatching.
- **A batch once merged 18 green PRs onto a dev lane that had been red for an hour.**
  A red deploy is unfinished work on every lane — watch to conclusion.
- **`gh run list --commit` matches only the full 40-char SHA.** Armed with a short SHA
  from `git log --oneline`, the deploy watch returned `[]` forever while the run existed
  and succeeded — it timed out silently after 25 minutes. Use
  `$(git rev-parse <short-sha>)`.
- **Workflow concurrency can cancel your deploy run**; the superseding run's green reads
  as yours while the lane is mid-deploy. Watch the run for YOUR commit
  (`gh run list --commit <sha>`), and artifact-check the lane before handing back a URL.
- **Two sessions once raced identical fixes to a red shared lane** and one ship was
  thrown away. Check for an existing fix PR first; open a draft PR as the claim.

## Design & review

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

## Dispatch

- **The first two days on the ladder, read from nine ship sessions** (2026-09-24 to 26).
  Pete found at TEST what the walk skipped: a right-click menu synthetic events can't
  reproduce, a voice path no walk reached, a localhost broken by a shared sign-in
  cookie. `verify` ran by its bare name and was refused, or not at all. Worktree
  isolation refused over 100 compound commands, the skill's own stage-0 line among
  them. Two runs built before Fable's plan review landed. Fable's plan and branch
  reviews found real bugs in every run. On the ledger Astra came back clean on 13 of
  29 tasks against Opus's 18 of 26, and 4 of 13 above a Jev score of 2.

Since 2026-09-24 BUILD routes each task by difficulty: Astra through `codex exec` inside
`scripts/astra.sh` for the easier half, Opus 5.5 and Fable subagents above it
(Engines). Codex was the only engine from 2026-09-18, through `codex app-server` and a
supervisor from 2026-08-12, and not an engine at all from 2026-09-06. The codex bullets
below are why the wrapper has each of its guards; every other line is about delegation
itself and holds for any worker.

- **Sol is not 6x faster on a coding task** (2026-09-24). The same brief (a model
  argument for `astra.sh` plus a selftest case) at high effort: Sol 81 s, Astra 91 s,
  both 10/10. Sol wrote 75% more tokens in less time, so it generates about twice as
  fast, but reading files and running tests set a task's wall time. That is why Sol
  left the ladder. Put it back only on a ledger showing generation-heavy tasks.
- **The first ladder build ran its Astra tasks on Opus and sat on `plan`** (cells-app
  packs, 2026-09-24). The driver's own ship args said "Codex is out", carried over from
  a September 23 outage, so it overrode the router's three Astra picks without trying one.
  The same run went from the router straight to fan-out and never wrote `build:0:<M>`,
  and Pete asked which stage it was in. The router now moves the marker, and "down"
  needs this ship's own failed run.
- **`app-server` over `exec` buys nothing a fire-and-collect task uses** (measured
  2026-09-18): a new task costs about 5 s either way, and app-server saves 2 to 3 s only
  on a second turn in a live thread, while needing a long-lived client that answers
  the server or wedges the thread.

- **Astra's sandbox cannot bind a loopback port**, so any test that starts a local
  server fails inside a run with `listen EPERM` or `EADDRINUSE` on port 0 (cells,
  2026-09-19: `loopback.test.ts`, `bridgeWorkflows.test.ts`, in all seven runs). It is
  never the task's fault and never worth a fix round. Tell the worker in the brief which
  tests those are so it reports and moves on, and treat the driver's own gate run,
  outside the sandbox, as the only real one.
- **Runs killed at a 2-minute timeout got mislogged as failures** — they were healthy
  high-effort runs that hadn't written anything yet. **Slow is not failure.** Give a
  dispatch a generous window and check in rather than killing; escalate on a wrong diff,
  never on a slow one.
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
- **`codex exec review` can exit 0 in seconds without writing its result file** (it hit an
  unrelated skill-loading error and stopped). A missing or empty result file means the
  review DID NOT RUN — never a clean bill. `astra.sh` exits 4 on exactly this. A plain retry of the identical command then
  produced five genuine findings, two of them serious.
- **`codex exec` runs went dark and nobody could tell** (Pete, 2026-09-03). A held stdin,
  a startup error and a model that stopped calling tools all looked like a slow
  high-effort run from outside; the supervisor's only tells were a rollout file under
  `~/.codex/sessions` and `ps`, and a ship lost an hour on a dispatch that had died at
  startup. The first answer was `codex app-server` through `dispatch.mjs` with a model
  watching the stream, retired on 2026-09-06 as heavier than the work it watched. The
  answer now is `astra.sh`: the brief from a file so stdin closes, a startup deadline on
  `thread.started`, an idle deadline on the JSONL's mtime, exit 3 for either. Slow
  still is not failure; unknown is.
- **codex's workspace-write sandbox can't commit from a linked worktree** — the index
  lives under the primary repo's `.git`, outside the sandbox root. The driver commits, so
  nothing needs this now; kept for anyone tempted to let the worker commit. Add the common git dir
  (`git rev-parse --git-common-dir`) to `sandbox_workspace_write.writable_roots`.
- **codex's ChatGPT auth can die mid-BUILD.** A second machine refreshing the same OAuth
  session invalidated it (`refresh_token_invalidated`); in-flight runs survived on their
  access token while every new dispatch was instantly dead. Recover with
  `codex logout && codex login --device-auth` (approve the code at
  `auth.openai.com/codex/device` — fill the segmented boxes with `form_input`, synthetic
  keystrokes get eaten); build inline meanwhile rather than parking the ship.
