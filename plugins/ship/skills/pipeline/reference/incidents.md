# Learned environment facts — from real failed runs

Facts about how this environment actually behaves, each learned from a real incident.
Consult the relevant section before merges, teardowns, deploys, or debugging a dispatch.
These are facts, not process — the process lives in SKILL.md.

## Worktrees & git

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
  after `wt remove`. Keep them out of the repo (the job tmp dir), and copy anything a
  presented card references somewhere durable before the merge.

## Backends & deploys

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

The four codex bullets below are kept as history: codex stopped being a ship engine on
2026-09-06 (Engines). Every other line here is about delegation itself and still holds.

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
  review DID NOT RUN — never a clean bill. A plain retry of the identical command then
  produced five genuine findings, two of them serious.
- **`codex exec` runs went dark and nobody could tell** (Pete, 2026-09-03). A held stdin,
  a startup error and a model that stopped calling tools all looked like a slow
  high-effort run from outside; the supervisor's only tells were a rollout file under
  `~/.codex/sessions` and `ps`, and a ship lost an hour on a dispatch that had died at
  startup. Every run is now `codex app-server` through `dispatch.mjs`: events with a
  clock, a `status.json` with `idleSeconds` and `lastCommand`, a watchdog that
  interrupts a silent turn and exits 3. Slow still is not failure; unknown is.
- **codex's workspace-write sandbox can't commit from a linked worktree** — the index
  lives under the primary repo's `.git`, outside the sandbox root. Add the common git dir
  (`git rev-parse --git-common-dir`) to `sandbox_workspace_write.writable_roots`.
- **codex's ChatGPT auth can die mid-BUILD.** A second machine refreshing the same OAuth
  session invalidated it (`refresh_token_invalidated`); in-flight runs survived on their
  access token while every new dispatch was instantly dead. Recover with
  `codex logout && codex login --device-auth` (approve the code at
  `auth.openai.com/codex/device` — fill the segmented boxes with `form_input`, synthetic
  keystrokes get eaten); build inline meanwhile rather than parking the ship.
