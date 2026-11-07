---
name: verify
description: >
  Prove the feature just built actually works before anything merges: write a QA script,
  run it yourself on the running app the way Pete would (a browser through chrome-devtools;
  a simulator or his iPhone through agent-device for a native app), fix what fails and run
  it again until it passes. Use in ship's TEST stage (it's invoked there automatically) or
  standalone when a change is ready and you want proof it works: "verify this", "prove it
  works", "/verify". It never declares a feature working off the diff alone; it drives the
  real app.
user_invocable: true
---

# /verify — prove the feature works, then hand proof to TEST

**You test it yourself** (Pete, 2026-10-05), in whatever session runs this skill: in
ship, the driver itself (pipeline TEST), never a hand-off between two: write the QA script, run it
on the running app, fix what fails, run it again. The one who sees the bug reads the logs
and makes the fix, so a round costs a rerun, not a hand-off. Split across two sessions it
cost six rounds on one iPhone scroll bug: the tester could see it but not fix it, and the
fixer could fix it but not see it. Objective checks (tsc / lint / unit / e2e) are the
regression sweep (§3).

**Works means every step of the script passed on the running app**, each with its
evidence: a screenshot, the agent-device diff, a response body. Each device the run walks
on (browser, phone, Mac) has at least one screenshot among them, since the review card shows
each (cel-311's iPhone pass had none, and LAND rebuilt the app to take it). Reading the diff and
concluding "looks right" is exactly the failure this skill exists to prevent.

**Read a reference when its case is in the run:**
- `reference/ios.md` when the contract has `ios:`, or the spec or storyboard says mobile
  web: the phone, simulators, Safari, and a locked phone.
- `reference/mac.md` when the contract has `mac:`, or the walk drives a rig on the Mac (a
  Chrome extension, a live-node rig): the borrowed Mac VM, the lock check, and a rig's
  windows, its Chrome for Testing and what the checks file keeps of it.
- `reference/browser.md` when the target is a protected preview, chrome-devtools is missing,
  or the walk prints, copies, drives a browser on another box, or runs a terminal UI.

**Two paths, named once:**
- `<out-dir>` holds qa.md, result.md, the QA script and the dev log: an absolute path under
  the job's tmp directory (`$CLAUDE_JOB_DIR/tmp`), else the launch directory's
  `.ship-shots/<slug>/`.
  Never `/tmp`, where a restart mid-QA wiped one, and never inside the repo's tracked tree.
  The sandbox denies a shell's writes under `~/.claude/jobs`, so its files are written with
  the Write or Edit tool, or by a shell with the sandbox off (cel-312's pr-body.md,
  eca-finder).
- `<shots-root>` is the session's launch directory unless a chrome-devtools walk's probe
  finds otherwise. That MCP reads and writes only inside its workspace roots, which usually
  stay at the launch directory after the session enters a worktree (CEL-175, CEL-226,
  cel-315), but were the worktree for cel-300, whose first browser call came after a
  compaction, and neither for eca-finder's second ship in one session. So such a walk's
  first call after opening its page is a probe, before any proof shot, snapshot or redeem
  file: `take_screenshot` to the launch directory's `.ship-shots/<slug>/probe.png`, then to
  the worktree's; the one that saves is `<shots-root>`, and result.md's `SHOTS:` names it.
  The MCP can restart mid-run without notice and come back on other roots, so the probe runs
  again when a call is refused a path it took before, a call fails outright, or the walk's
  page is gone from `list_pages` (yonder's came back rooted at the worktree).
  Screenshots, `take_snapshot` files and any file the MCP reads go in
  `<shots-root>/.ship-shots/<slug>/`, always as absolute paths; `.ship-shots` is never
  committed (the `.ship-*` exclude covers it). In ship the driver passes the launch
  directory. **A probe that saves in neither** makes it `SHOTS: inline`: shots and snapshots
  go with no `filePath`, a shot's result names the copy saved under the session's
  `tool-results/`, and the shell copies that into the launch directory's
  `.ship-shots/<slug>/`, sandbox off, which EVIDENCE then names. A file the MCP must read (a
  redeem script, whose secret stays out of the transcript) has no inline form, so its step
  is `unverifiable` and says why.

## 1. Preconditions — the caller owns these

The running app is **already up** — in ship's TEST the target is the branch's preview link
when ship built one (the host, database and sign-in Pete will test), else the worktree's dev
server, booted for you; standalone, boot it first and note the URL. Ready means the URL answers:
for the worktree's own server, `scripts/listener.sh <port>` in the pipeline skill's directory,
then one request to the URL, both with the Bash sandbox off (a sandboxed curl at localhost
prints 000); for a remote URL, a curl loop up to a deadline, in a script file. Watch the dev
log for errors, never a process grep, since a dev server can build for minutes before it
listens. Then, on the worktree's dev server, GET each page and read route the change added once
before the walk, never one that starts work: a dev server compiles a route on its first request, and CEL-192's first call to a new API route came back 401 while it
compiled. Reuse that stack, never boot a second. A preview behind the host's login wall
(Vercel protection) is reached with its automation bypass through the CLI, never through
Pete's browser, and the secret never sits in a tool call, a URL or qa.md
(`reference/browser.md`).

A web app is tested in the browser, its mobile layout at phone width (390px) there. Never
control Pete's Mac desktop.

**The generic seam (don't cross it):** if the feature is behind auth, the **repo** must
provide a test way to reach authed surfaces: its contract's `test-auth:`. `seed <how>` is a
seeded account and its secret. `form <how>` means the app's own sign-in form works with test
credentials (a Clerk test instance: any address, the fixed code 424242), and then signing in
through that form, with a fresh test address per walk, is the path. The tricks a fresh
account needs in one repo (an invite code, a redeem file, a PIN) live in that repo's checks
file under Sign in. verify does **not** mint
sessions, set auth cookies, hit a dev-login endpoint, bypass auth, or stand up infra — that's
repo plumbing. If authed surfaces are unreachable and the repo offers no test-auth path, the
result is `unverifiable` naming the wall, and Pete walks it — never fake a pass.

**Start the test target from the final tree.** A target that copies or freezes the
branch's files when it starts (a run that snapshots its tools at prepare, a container
built once) tests whatever was there then: start it after the last fix, and one at a time
where the host is small (two starts at once ran an 8 GB Docker VM out of memory).

**The seeded account is the QA run's alone while it walks.** Never invite Pete to poke at
the app on the same seeded user mid-run — his concurrent clicks read as bugs. Seed a second
user for his hands-on look, or wait for the result. The run's own other pages count too:
before a step that reads or clears what's unread, send every other page signed in as that
person to `about:blank`, since an open page marks replies read as they arrive (yonder-skin's
phone showed no unread dot for three tries while a web page sat on the chat).

## 2. Write the QA script → run it → fix → rerun (≤ 3 fix rounds per failing step)

**A diff of only tests, evals or test scripts** has no page: its own run, green, with no
assertion, skip or threshold loosened that the PR doesn't name with its reason, is the walk.

**A diff that touches only docs gets a fact check in place of the app walk.** Every path,
command, script, function, table and section the doc names exists and is tracked on the
branch (`git ls-files`, not the disk), every constant it quotes matches the code, it renders
on GitHub, and any mermaid in it parses. handoff-readme's check found a spec the README cited
that existed only untracked in the main checkout.

**Start from the repo's checks.** A repo keeps how it is proven in a project skill,
`.claude/skills/checks/SKILL.md`: how to start it, sign in, walk each screen, the pass
lines it must meet, and the noise to ignore. Read it first and build the QA script on it, so a run never rediscovers
what the last one learned (Pete, 2026-10-19). No file yet: §5 writes it from this run.

**Write `<out-dir>/qa.md`.** On a ship with a plan, its steps start from the plan's
`## QA cases`, which PLAN wrote before any code: walk each as written, add any the build
showed were missing, and drop none. A step that switches a feature off runs last or in a bot
chat of its own: a bot that saw it gone keeps believing so once it's back on (yonder). On EXPRESS or a standalone `/verify`, write the cases
yourself from the spec, else the acceptance criteria. Its head names what the run uses: URL, AUTH (the test-auth path, with everything
a fresh account needs, an invite code or a PIN), IOS (the line `ios:` printed, or none),
BACKEND (on `backend: copy` or `per-branch`, the exact deployment, pinned on every CLI call, or seeds
land on one backend and the app reads another), ENV (any variable the dev script sets only
for its own server that a data-level script needs too; cells-app's `LOCAL_STAGE=local-<port>`,
without which a script reads main's stage and comes back empty), PROTECTION (`protected` or
none, never the bypass value), STORYBOARD (a GATED ship's frames and
`~/.claude/skills/impeccable/reference/craft-floor.md`,
or none). Then numbered steps, each one thing a person does and what they should see:
"4. Scroll up slowly past the first page of history → the message you were reading stays
put". Cover every acceptance criterion, every frame the change built (a visible gap from
its frame is a failure), the edges the spec names, and a clean console. A repo whose
contract checks one app of several (cells-app: Homebody) walks every frame there, and a
frame that app lacks on one that has it, from this worktree's server switched to it as the
repo's checks file says, never that app's own checkout of main (cells-faces drew Cells'
faces). The gates and smoke follow the contract's own rule. Another app's part of a shared
frame is proven by its own tests, run under its own switch (`PACK=<pack>`) where the diff
changed its files, and is neither a step nor unwalked. A changed helper's callers, and theirs, decide
which screens the script walks: eca-finder-193 planned a page that renders none of the helpers
it changed. Start at least
one walk the way a person most naturally would, from nothing, not from seeded state: the
walkie-visit QA only walked showings at a seeded home, and Pete's first try, a showing at
a new address, hit a path nobody had built. A step that sets by hand a state the feature
claims to reach on its own (a stage, a status, a phase) comes after one that proves the
feature writes it: run the loop, read the field back. swain-ideas moved its captains' stage
with a setter, and every real captain stayed on the first one, since the code knew only
Homebody's stages. Post one line
before running, `QA: <n> steps on <surface> — <qa.md path>`, so Pete can watch and steer;
what he says mid-run changes the run.

**Pick cases that can fail.** A step that would pass on main's code proves nothing. A page
main's server can't show at all gives the walk nothing to compare (cells-app main's
localhost sends /hello to sign-in, lacking the branch's Turnstile test keys): the swap
below, run with the change's own new tests (a fix's regression test, a feature's tests), is
the red, and the evidence says main's page was unreachable.
- A fix's regression test runs once against main's copy of the fix's source files and goes
  red: one script swaps them in (`git show origin/main:<path> > <path>`), runs the test and
  restores them (`git checkout HEAD -- <path>`), outside any walk, since the swap hot-reloads
  a running server. A page or app open on that server runs main's code while it is swapped
  in, so a walk already under way records its verdicts and closes each one first
  (`close_page`, or the app quit), and whatever is judged after the restore is judged from a
  fresh load, console, requests and audits included (cel-326's open page logged 11 "Export
  doesn't exist" errors that read as a branch bug); quote that red in the evidence (CEL-100). A data fix is checked on a row main's
  code gets wrong: every card live-label-rows first reached was labeled right by the old match.
- A feature that returns a list gets one case where a large result is certain, and a small
  count there fails: homebody-onboarding's rental search found 1 of 6 real Denver homes, and
  the small-town walks read the same gap as a thin market.
- Removing an element walks the other jobs it did: homebody-skin's disc behind the phone face
  also caught taps and hid scrolled text.
- A bug in saved state that main gets right on the reported path gets a case for each other
  code path that writes that state, found by searching the code for every write to it, and
  the fix is walked on each: cel-313's reported write read right on main 8 of 8, and only a
  direct edit of the same field made main's checker reject the right $19,500 and write the
  old $18,000 back.
- A field a model fills or judges gets cases that vary what it reads, the time, the place,
  the phrasing, each run through main's wording and the branch's, the same inputs, 3 fresh
  sessions each, both quoted (the pipeline's replay rule): cel-264's "being there answers
  it" passed an evening showing and failed a morning one. A batch that needs no hands (those
  sessions, a replay, an eval) starts in the background before the walk, as a test person of
  its own: prompt-cache's 15 x 3 cases took 45 minutes after it, and LAND waited. A fix to
  what it tests starts it again.
- A feature that reads a number a provider reports (cost, tokens) gets one real value read
  back from the runtime before a walk is built on it: cel-302 lost two rounds to $0.03 and
  $0.002 caps before finding its model reports a cost of 0.
- A CSS rule is proven by computed style on the real element (`evaluate_script` with
  `getComputedStyle`), never by a test that greps the stylesheet: yonder-skin's underline
  passed one and read `none` on the page, beaten by a more specific rule.
- A race fix walks every ordering it claims to handle, the same instant among them, started
  the way the real race starts: two processes for two workers or devices, one page for a
  double submit. A same-instant case counts only with proof the contended calls overlapped,
  each call's start and end time or the server's log of the second arriving before the first
  answered; a run that serialized is repeated, and the case goes red on main's code first.
  cel-306's box race passed with the second open 5 s late; started together from two
  processes, since one process deduped its own calls, the Sandbox API answered 400 "already
  exists", not the 409 the fix handled.
- On a shared backend, the job a step counts is one this run started: read back its starter
  and the deployment it ran on (live-label-rows' guest joined a search another session had
  begun a minute earlier, on other code).

**Time the hot path.** A change to a query or endpoint a page waits on gets timed at data
level on production-sized data, main's code against the branch's, and a slowdown toward
the backend's limit is a failure (Convex stops a function at 1 s of execution). Loading
one row per section took a catalog search from 2.1 s to 7 s past the gates and both
reviewers; only this timing caught it. Time it in the runtime it runs in: node ran
eca-finder's Convex scan 10 to 15 times faster than Convex did (53 ms in node, over 1 s on
prod), so a Convex function runs read-only through `convex run --inline-query` and its time
comes from `convex logs --success --jsonl` (eca-finder's checks skill has the recipe). A memory claim is timed the same way: five or more
runs of main and the branch, interleaved, and a peak confirmed with the heap capped
(`--max-old-space-size`); CEL-113's one max-RSS reading showed a 0.4 GB rise that was GC
timing, and the peak had gone down.

**Seed, then read it back.** Before the walk, read each seeded record back through the
same backend and stage the app's server uses, and print which one. Two cells-app runs
seeded main's stage from a worktree because the script read `.env.local` before setting
its origin, and the walk lost a round to "No alert by that id". Read back the model a bot
turn will run on too, against the repo's checks file, before the first one: app-look's and
prompt-cache's test people ran on OpenRouter and Sonnet until Pete stepped in.

**Run it** the way a person would, with real clicks, taps and keys:
- **Browser: the chrome-devtools MCP** (`mcp__chrome-devtools__*`, loaded with one
  ToolSearch call; headless, a fresh profile, never Pete's Chrome). Click, hover, fill and
  press keys through its tools; `evaluate_script` reads state, never fires events, because a
  script-fired event passes where a real right-click or drag fails. `emulate` covers the
  390px layout and dark mode (a screenshot right after a viewport change can come back blank
  with the DOM fine: take it again before calling it a bug), and a breakpoint crossing changes the width alone,
  every other setting passed again (each call replaces them all, dark mode included), since
  flipping mobile or touch reloads the page (cel-263 read that
  fresh load as a bug); `handle_dialog` answers a native prompt. Check the console and
  failed requests as you go. A desktop walk starts with `resize_page` at 1440x900, since the
  default page is narrower (CEL-184 opened in its overlay layout). A proof shot waits for a known row's text first, since one taken
  right after `navigate_page` catches the loading frame (a `.jpg` path saves as `.jpeg`). After
  an edit mid-walk, judge the step again from a fresh load: a hot reload of the open page reads
  as a bug. On a long page, `take_snapshot` with a `filePath` and grep
  the file for the uid you need, rather than reading the whole tree back each time. A form
  that starts paid work (a model, a tier, a run): set its cost fields first and submit with
  its button, never Enter in a field, which submits with whatever defaults are left. Where
  Enter in a field does start paid work, that is a failure to report: a real user hits it too.
  A test person a case moves off the default model or tier goes back, or is deleted, when
  that case ends: prompt-cache's, left on Sonnet, kept running loops through the local
  dispatcher until LAND. A React controlled input can ignore `fill` (the value snaps back): click it and
  `type_text`. The tool's clicks are slower than a person's, so a control with a short
  settle timer (picks counted after ~2s) can read three picks as three separate ones: judge
  its result, not each click. A screen shown only while async work runs needs a target whose work
  outlasts the walk to it (reading-tally's small town finished during the intro, and a
  second paid search went to a mid-size one). `navigate_page`'s `initScript` lasts that one
  navigation, since the MCP removes it after, so pass it again on every navigation that needs it.
  A file the MCP reads (a sign-in redeem script for `evaluate_script`'s `sourcePath`) goes in
  `<shots-root>/.ship-shots/<slug>/` too. A copy or `sips` into it needs the Bash sandbox off
  (exit 13 otherwise); delete a redeem file once it has run.
- **iOS: the agent-device CLI**, by `reference/ios.md`.
- **API, CLI, script:** run the real commands; their output is the evidence. A server-side
  change no surface reaches before the merge (code a background worker runs): replay the
  reported case at data level, the changed function against a read-only copy of the real
  data, before and after, and show both numbers. On Convex, `npx convex run --inline-query
  '<code>'` evaluates a changed read on a deployment's real data, sandboxed and read-only,
  with nothing pushed: the way to prove a query or index range while sibling worktrees hold
  shared dev (eca-finder #297 checked its claim range on prod so). Copy out only the tables
  the replay reads, never a whole export: prod holds people's details.

Screenshots only at the beats that prove a step (start → action → result), as absolute
paths under `<shots-root>/.ship-shots/<slug>/`; the agent-device diff and a page snapshot
are cheaper evidence where they show the result.

**A step fails:** you have the app open, so look before you change code — the console, the
network, the device log, a trace — and fix the cause where it lives, not on the surface
that showed it: when one view gets state wrong, find every other view that reads the same
state and walk them all in the rerun (CEL-56 fixed a stale flag in a chat header, then QA
found it again in the bot panel). A chat with a bot: the old thread keeps what the bot
believed before the fix ("I can't move it"), so rerun in a fresh conversation, and check
each sent message shows in the thread before waiting on a reply. One typed while the chat
reads "Connecting..." can vanish, which is a finding, not a retype. Re-run the gates scoped (§3), push a fix under `convex/` to the BACKEND (on a `copy`, the pipeline's `branch-db.py push
<worktree> [<app-dir>]`, which refuses shared dev; else `npx convex dev --once`),
and put the target on the fix before the rerun: a preview needs the branch pushed and its
new build ready on the same alias; a target that builds the fixed code only at start (a
container, a snapshot, a production build, or what the repo's docs say its dev server
builds once, like cells-app's `lib/` into `lib/dist`) is rebuilt from the fixed tree and
started the way §1 says, the old one stopped first and the URL polled until it answers
(catalogue-soul reran against the old `lib/dist` for a round). Then rerun the failed steps plus
every step the fix could touch. The same step failing twice means the
last fix was a guess: call the Skill tool with `mattpocock-skills:diagnosing-bugs` and get a loop that goes red
on it (a test, a script, a trace) before the next fix. Three fix rounds on the same
failing step without a pass: stop, and hand the caller what keeps failing with its evidence. A run that never reached the feature (a model chose not
to take the path under test) tested nothing: rerun it, never call it a fail; after two such
misses, prove the route directly and feed one model session its exact input (CEL-60's voice
model answered itself on 3 of 3 calls; CEL-241 spent 25 minutes on spoken calls). That direct
proof is the step's pass, and the natural misses go under TASTE with their count, so Pete sees
how often real sessions skip the path. A model
provider out of credit or down: check once more, use the repo's alternate billing where it has
one, else the step is `unverifiable` with the provider's error (CEL-127, CEL-132, CEL-73). A
step the pipeline proves at data level instead (its TEST: a path no person can trigger, real
records that cost money or that test-auth can't seed, a walk the brief forbids) counts as
walked that way, along with the check of each screen that reads the result, and its EVIDENCE
line says so. Any other step you can't reach (a mic, a bot
check, a missing device, an auth wall with no test-auth path) makes the result
`unverifiable`, naming the step, even when everything else passed. Never loop forever; never
merge unproven.

**The result** goes to `<out-dir>/result.md`:

```
VERDICT: works | broken | unverifiable
UNWALKED: every step the run didn't walk itself, handed to Pete or skipped, or "none"
EVIDENCE: ordered list of "<screenshot path or output> — <plain-language caption>"
SHOTS: <shots-root>, or "inline"
EXPECTED / OBSERVED: for every step that didn't pass
TASTE: <0-3 short "looked off / couldn't confirm" notes, or "none">
```

`works` needs `UNWALKED: none`; anything else is `unverifiable`. A compaction summary once
carried "step 13 is Pete's" as settled, and the result put it under `works` as a footnote;
the rig built for it found a real bug (yeoman-listing-readers, 2026-11-03).

**Measure what a person feels.** On a change with a screen, after the walk passes, run
these on each page it touched, and every pass line the repo's checks add:

| Check | Passes when | On a fail |
|---|---|---|
| Layout shift: `performance_start_trace` (it reloads the page, so it goes in a message of its own, never beside `emulate` or `navigate_page`: on a slow dev server feed-imagery's pair both hit the 10 s navigation timeout), at desktop and 390px; the summary prints CLS | CLS under 0.1 from the change | `performance_analyze_insight` with `CLSCulprits` and the insight set id names the element that moved: reserve its space, rerun. A shift main's layout already has goes in TASTE, and its number in the checks file's Noise table: the change's share is then the difference of two traces taken the same way, one with the change's new elements hidden by an `initScript` style (the trace's own reload drops a `navigate_page` initScript, so: `about:blank`, start the trace with `reload: false` and `autoStop: false`, `navigate_page` with the initScript, wait for a known row, stop), and only a difference over 0.1 fails (cel-320's Mail tab: 0.38 with them, 0.29 hidden, so 0.09 passed) |
| Accessibility: `lighthouse_audit` (`mode: "snapshot"` for a state the walk reached), its accessibility failures and the nodes they flag | no failure on an element the change added or changed, a new one styled with main's tokens included | fix it and rerun; one main already had goes in TASTE |
| Load time, only on a production build or a preview (a dev server compiles on first load) | LCP under 2.5 s | the trace's LCP breakdown says which part is slow |

A failed measure is a failed step like any other, with the number as its evidence. Trace
each page on its own URL before blaming a shift on the change: Settings opened over
/activity scored 0.26 from that view's sheet animating in, and 0.00 on its own. A false
alarm the repo's checks list under noise is skipped, except a page's layout shift: its
Noise row holds main's number, and the change on that page is still measured against it.

**Catch a transient element** (a toast, a flash) with a MutationObserver armed by
`evaluate_script` before the action, never a poll after it: cel-278's 4 s toast was gone by
the time the click returned. Observe `document.documentElement` with `subtree: true`, since
toasts render in portals, and keep each hit on `window`. An action that navigates takes the
observer with the old page, so record it with `screencast_start` instead.

**Prove something stays idle** (a spinner that must not appear, a message that must not
come): `wait_for` on the failure text with the step's timeout (`timeout: 90000` for 90 s).
A timeout is the pass; the text showing up is the fail. `sleep` is blocked. A fixed wait
before a check (a box's idle stop) is timed by the clock, never by the wait returning: note
`date` before it and check the time has passed after, since yonder's 660 s background
`sleep` came back with no output or exit code. When the step
claims why something never shows, the walk can't tell that cause from another, so also run
the code that decides it on the saved state with the cause and without, and show both:
signup-status's closed deck pick never dealt, but only the deal's own `leftOf` (`[]`
marked, `['Barracuda']` unmarked) told the mark apart from Jev's ranking.

**Wait on the real thing.** A server: `scripts/listener.sh <port>` (in the pipeline skill's
directory), then one request, as in §1. A process: `pgrep -f <pattern>`, never `ps | grep`, which matches its own grep
and reports a server that isn't there yet (CEL-169 ran its checks early that way). A reply to
a request that starts agent work: snapshot once within about 30 s before a long `wait_for`, since
the work can stop first on a confirm or approval card ("Allow Yonder to open this website?" held
yonder-parity's wait 280 s). Keep each `wait_for` under about 110 s and repeat it: past the
harness's ~120 s it moves to the background and still holds the page, so the next snapshot or
click queues behind it (CEL-149). On a long page, poll for the text with `evaluate_script`
instead, since `wait_for` prints the whole snapshot each call (homebody-skin's Settings ran
700 lines).

## 3. Regression sweep — you run the codified checks; fix red directly

Run it with the Bash sandbox off: a `listen EPERM` or a failed font or package fetch under
the sandbox is the sandbox, never a red to fix.

Run it in full before the first QA run, and again once after the last fix round, once its
last edit is in: a sweep started before then reports on code that's gone. Between rounds,
run it **scoped** to what the fix touched: the typecheck, plus the tests that cover the
changed files (the contract's `scoped` command, else the runner's changed mode through the
repo's test script so its pretest hooks run, `npm test -- --changed` or `-- --onlyChanged` for
jest; a scoped run that finds none for a code change is a miss to check, not a pass, and one
never follows a path a test computes to the code or data it reads: contract.md `gates:`). In ship, the final full run can wait for
LAND's step 1, which runs it when the tree changed since the last one. Stop the worktree's dev server
before a production build (`next build` and `next dev` both write `.next`) and restart it
after. In ship, BUILD's pre-flight is
the first run, so skip it then unless the tree changed since. Run the repo's `tsc` / lint / unit / existing e2e as a regression sweep — and **run what the
DEPLOY workflow runs, not just the test gate.** If deploy does a build/typecheck the test job
skips (`next build`, `flue build`, an app-level tsc that vitest never touches), run it locally
here. The host also builds from less than your tree: an ignore file (`.vercelignore`) drops
paths, so a local build passes an import the host never receives (a runner that imported
`scripts/` built locally and failed on the preview). A diff that adds an import into an
ignored path gets a preview build. Deploy-only failures are the most expensive class because they land *after* merge (a
TS7023 invisible to vitest once sailed through to a red dev deploy). Triage failures
(real-bug vs stale-test); **never weaken an assertion to go green.**

## 4. Crystallize — core journeys only

If the feature is a genuine **core journey** — auth, money, a primary product flow, NOT every
small feature — write the drive you just walked as a committed Playwright `.spec.ts` in the
repo's e2e location, folded into the feature's own diff. Stable selectors (role/label/text;
add a small `data-testid` only when there's no good handle — never a brittle CSS path). Most
features: skip this — drive, prove, report, done. The standing suite stays thin: core flows,
not a spec per micro-feature. **Running** the committed spec in the gate is the **repo's** job
(the seam) — verify writes it, the repo wires it.

## 5. Write back what the run learned

Update the repo's `.claude/skills/checks/SKILL.md` in the branch, so it lands with the
change, with the Edit or Write tool (the Bash sandbox denies a script's writes under
`.claude/`, cel-325): a screen the change added (how to reach it, what it shows), a step that changed, a
trick the run had to discover (a sign-in trick under Sign in, a seed, a port), a pass line
Pete asked for, and noise: console noise the app always prints, or a false alarm a measured
check raises on every run (cells-app's localhost branch strip in each Lighthouse audit),
added to its noise table so the next run skips it.

**One line per lesson.** A new lesson on a subject a line already covers replaces that line,
never sits beside it. A file over its cap gets pruned in the same edit, back under it: merge
the lines on one subject, and drop a line whose screen or code is gone. No file yet: write it
from `reference/checks-template.md` with what this run proved, and say so in the hand-back.
Name it `checks`, never `verify`, which is Claude Code's own skill. A run that learned
nothing leaves it alone.

**Commit before handing back, in a ship's worktree on `works`**: the run's fixes, §4's spec
and this write-back, whichever exist, staged by path so generated churn a running dev server
writes (`next-env.d.ts`) stays out. Left uncommitted until landing, a write-back makes the
absorb refuse when main changed the same file; committed, the absorb merges it or shows a
real conflict (cel-303: main rewrote cells-app's checks file to one line per lesson
meanwhile). A conflict there resolves to main's copy with this branch's own changes to it
(`git diff $(git merge-base HEAD origin/main) HEAD -- <path>`) put back, and the cap's prune
redone on the result: two ships pruned it the same day, 10 s apart (cells-faces and #495). A `broken` or `unverifiable` run commits nothing, and a standalone run outside a
ship commits nothing either: it names the changed files in the hand-back.

## 6. Hand back proof

Return to the caller: `VERDICT`, `UNWALKED`, `EVIDENCE` (the ordered screenshot + caption storyboard),
`SHOTS`, `TASTE` notes, and the crystallized spec path (or none). In ship they go on the review card:
the storyboard becomes "Proof it works," the taste notes "Flagged." Pete reviews proof, not
faith.
