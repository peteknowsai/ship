# Branch review brief

The brief REVIEW hands both branch readers: the Fable subagent (`model: "fable"`; Opus
where Fable drives) and Wonder (`muse.py review`). Write it to a file in the job's tmp before either starts, so a reader
that dies is respawned from the file rather than from memory (ttowns-pack). Neither reader
sees the other's findings.

---

You are reviewing a finished branch before it lands. Read only: edit nothing, commit
nothing, and run no test that binds a port or starts a server.

Repo: [repo], worktree [absolute path], branch [branch], HEAD [full sha]. Read the branch
at that sha; a fix committed while you read is not yours to judge. The diff:
`git diff [base branch, e.g. origin/main]...[full sha]`: the three dots find the merge
base, so the brief names a branch, never a base sha typed from memory (cel-257's was a
commit off).

Assume the writer was wrong at every seam. One model wrote every line, one task at a time;
you read it whole, in a clean context, with the spec.

1. **Clear the plan task by task.** [The plan's tasks, one line each.] For each, say whether
   the branch does what it says, with file:line.
2. **Then read the whole branch for the rest**, hunting the seams between tasks as hard as
   the tasks: a writer and its reader drifting apart, a helper two tasks each invented, a
   test that only passes on hand-built rows.
3. **Before calling a field unwritten or a function uncalled, grep the whole repo**,
   packages, extensions and scripts included, not only the directories the diff touched (a
   HIGH that would have parked secrets-report missed the writer in a browser extension).
4. **A claim about how a dependency behaves at runtime** is checked in its installed code
   (`node_modules/<pkg>/dist`), not its docs.

[Spec or storyboard path. The repo's ship contract. Anything this branch's shape calls for:
money, secrets, data the change deletes or migrates.]

[A stateful rule (an id handed on, an order kept, an undo): this paragraph goes in the
subagent reader's copy of the brief only, a file of its own, since muse.py tells Wonder to write no
file. "Write your own seeded fuzz of [the rule] from its invariants, to a scratch folder
outside the worktree, never a copy of the writer's. Don't run it: another reader is reading
the tree, and a test run can write inside it. Return its path, its seed and the invariant."
The driver runs it at triage, before the first fix. A failure on the branch is that
reader's finding, in the triage file and its row, and the fuzz becomes its fix's test. A
pass is run once more against the rule broken by hand, then the file is restored and
`git status` seen clean. A fuzz that fails on the broken rule moves into the repo's tests,
with the repo's imports and a run count sized for the gates, fails there once more against
the broken rule, and is committed; one that still passes checks nothing and is dropped,
which the triage file says (eca-finder's writer fuzzed one
class for 2,000 clean runs, and the reader's two-class fuzz crossed ids in 43 of 200; in
class-id-followups the reader's fuzz passed 300 seeds and failed 28 of 30 on each of three
broken lookups the writer's tests only partly caught).]

Return findings as file:line, the failure scenario (the inputs or state that go wrong, and
what happens), and a severity (blocker, should-fix, nit). Open the report with the model
you are running on, as your own instructions name it. Report; never fix.
