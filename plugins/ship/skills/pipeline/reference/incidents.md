# Learned environment facts — from real failed runs

Facts about how this environment actually behaves, each learned from a real incident.
Consult the relevant section before merges, teardowns, deploys, or debugging a dispatch.
These are facts, not process — the process lives in SKILL.md.

## Worktrees & git

- **Cross-repo `EnterWorktree` silently doesn't take.** It only adopts worktrees of the
  session's *primary* repo. Against any other repo the cwd never moves and the status
  line stays blind — the worktree and `.ship-stage` are real but invisible. Work by
  absolute path and narrate the fork (see the narration contract).
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

## Backends & deploys

- **A worktree building against a shared backend clobbers it** — pushing the branch's
  schema reconciles the shared plane to this branch and drops indexes other branches
  added. Per-branch preview backends exist for this; the shared dev deploy runs only
  from the main checkout.
- **Convex previews hold stage-0 code and drift behind every `convex/` commit.**
  Re-push before the smoke-walk: `npx convex deploy --preview-name <branch> -y`.
- **tsc + vitest green ≠ deployable.** Frameworks with their own production build
  (`next build`, `flue build`, wrangler/vite bundling) have failed on deploy after green
  tests. Run the production build in the smoke-walk.
- **A batch once merged 18 green PRs onto a dev lane that had been red for an hour.**
  A red deploy is unfinished work on every lane — watch to conclusion.
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

## codex dispatch

(The router skill carries the operational rules; these are the underlying incidents.)

- **`codex exec` with stdin held open hangs at startup forever** — no session file, no
  error. It once ate a night of dispatches and got misblamed on fast mode. `< /dev/null`
  is mandatory.
- **Runs killed at a 2-minute timeout got mislogged as failures** — they were healthy
  xhigh runs that hadn't written a file yet. Liveness tell: the `~/.codex/sessions`
  rollout file appears within seconds; patience (15–30 min) applies only after it exists.
- **`codex exec resume --last` picks whichever run finished most recently anywhere on
  the machine** — with concurrent sessions, that's usually not your task. Resume by
  session id.
- **`codex exec review` errors when a prompt is combined with `--base`** (or any
  diff-source flag) — review mode applies its own rubric; no focus prompt.
- **The codex-companion runtime's per-worktree broker dies mid-run** in a multi-session,
  restart-heavy workflow — it killed a 25-minute review that sat "running" forever.
  Background work goes through `codex exec` only.
- **Codex has auto-opened PRs and committed unprompted** — git stays with the driver.
