# Codex as the tester — only when Pete asks

Pete asks for Codex ("test in codex", "hand it to codex"): the driver writes the brief
below instead of running the QA script itself. A change he can try goes to his Codex app (the
hand-off); anything else gets the headless tester. The scripts live in the pipeline skill's
`scripts/`. Everything in SKILL.md §1 (preconditions, auth seam, iOS rule) still holds.

**The hand-off.** From the pipeline skill's directory:

```bash
scripts/codex-handoff.py start <worktree> <out-dir>/brief.md <out-dir> --url <the app's URL>
```

`--url` (repeat it for a health URL the contract names) makes `start` and every later
`retest` check the app answers first; exit 5 means it didn't and nothing went to Codex:
restart the dev server (the contract's `dev:`) and run it again. Codex never gets a round
against a dead server (2026-10-05).

It starts a Codex thread in the worktree (Astra on high, read-only, approvals on request)
whose first turn turns the brief into a numbered test plan, opens the thread in Pete's
Codex app (`codex://threads/<id>`), queues ship's go so Codex starts testing at once,
and prints the link and the plan. Pete watches and steers there; nobody has to say go
(Pete, 2026-10-05). The first turn runs before the app has the thread, with no network,
so it only plans: the pre-flight already proved the app is up. Then, in the background:

```bash
scripts/codex-handoff.py wait <out-dir>
```

It returns when a turn ends on a `VERDICT:` line, prints the verdict, and writes the
report to `<out-dir>/last.md`. Pete sets the pace, so re-arm it when its background
timeout ends; exit 2 means the thread is gone, so start a new one. **The loop runs without
Pete** (Pete, 2026-10-05): Codex hands back on its own and ship answers on its own. **broken**,
or **unverifiable** naming something ship can fix (a dead server, a stale or missing build,
a device it couldn't drive): fix it, re-gate, push, write what changed and what to retest to `<out-dir>/retest.md`, run
`codex-handoff.py retest <out-dir> <out-dir>/retest.md`, and `wait` again. The same
thread keeps the context Pete built with it, which a fresh run would lose. `retest`
queues the note with `codex queue` and opens the thread: the Codex app runs it there as
soon as it has the thread loaded, so the fix round needs nothing from Pete but his eyes.
A finding that comes back a second time gets `diagnosing-bugs` (call the Skill tool) and a
loop that goes red on it before the next fix.
Post one line saying what was fixed and that Codex is retesting. Up to three retests go
without a word from Pete; a fourth verdict that still isn't `works` stops: `needs input:`
with what keeps failing and the thread link. If `start` fails (the Codex app
missing, Codex signed out), run the headless tester and say so.

**Local sites never prompt.** The Codex app's browser asks per site, and a site is host plus
port, so every worktree's port would ask again. `~/.codex/browser/config.toml` allows them all
once: `[origins] allowed = ["localhost", "localhost:*", "*.localhost", "*.localhost:*",
"127.0.0.1", "127.0.0.1:*"]` (entries are `*` globs on `host:port`). If the thread still
can't open the app, look for a `denied` entry in `~/.codex/browser/sessions/<thread>.toml`:
a thread's own decline beats that allow, and `start` clears the ones its first turn leaves.

**The headless tester.** From the pipeline skill's directory, in the background:

```bash
scripts/astra.sh test <worktree> <out-dir>/brief.md <out-dir>
```

`test` runs `codex exec` read-only with two MCP servers on and pre-approved: the
chrome-devtools browser, headless, and agent-device (iOS). The browser may write only in
the worktree and the out-dir, so the Codex tester's shots path is `<out-dir>/shots`, and
the driver copies what the card shows into `<shots-root>/.ship-shots/<slug>/`. The
verdict is `<out-dir>/last.md`. Every
round is a **fresh run** in a new out-dir: a tester that saw the bug is no longer
independent of the fix. Exit 3 or 4 means the run didn't happen; retry
once. Codex down or signed out (the same exit repeating, `refresh_token_invalidated` in
`stderr.txt`): fall back to a fresh Opus subagent driving the chrome-devtools MCP
(`mcp__chrome-devtools__*`, loaded with one ToolSearch call; never the claude-in-chrome
tools) with the same brief, and any iOS step in it is `unverifiable`.
The sandbox stops the tester writing to the tree, and the driver still checks `git
status` after the run (any dirt → discard it, count the round as `unverifiable`):

```
READ-ONLY: you may not edit, create, or delete any source file — screenshots go under
<absolute shots path>/ only, always as absolute paths (the browser tool can write
nowhere else, and it resolves relative paths somewhere it can't write).
You are the tester, standing in for the user. Independently confirm THIS feature works
by using the running app (the stack is already up at <URL> — reuse it, never boot your
own): in a browser through the chrome-devtools MCP, and on iOS through the agent-device
MCP when the IOS line names a device. Never control the Mac's desktop. Report what you
find; never fix anything, and never write outside the shots path.
Most new features have no automated spec — verify it agentically.
Drive it the way a person would: click, hover, fill and press keys through the browser
tools, and press, fill and scroll through agent-device. evaluate_script is for reading
state, never for firing events, because a script-fired event passes where a real
right-click or drag fails. Walk the surface you
were given, signed in the way the AUTH line says. A step you could not reach (a mic, a
bot check, a missing device) makes the verdict `unverifiable`, naming the step, even
when everything else worked.

FEATURE (what a user should now be able to do + the observable success state):
  <intent / acceptance criteria>            (or: see plan/spec file <path>)
HOW TO EXERCISE IT:
  <route + steps / API call / CLI>
STORYBOARD (a GATED ship's locked design, else 'none'):
  <storyboard path#frame-ids>, and ~/.claude/skills/impeccable/reference/craft-floor.md.
  The built screens should match their frames; a visible gap is a finding.
IOS (a native app the change reaches, or mobile web the build is meant for, else 'none'):
  Native: the IOS line the contract's `ios:` printed, the device ("iPhone PM" or the
  booted simulator) and the branch app's bundle id; only that app, never Safari. Mobile
  web: the booted simulator's name and "Safari at <URL>", never iPhone PM. Start with
  agent-device `open <bundle or com.apple.mobilesafari> --foreground`; close the session
  when done.
AUTH (if behind login):
  <the repo's test-auth path: a seeded account, or `form` with its test credentials and
  everything a fresh account needs to get in, an invite code or a PIN, or 'none'>. Use ONLY that path. Do NOT mint sessions, set auth cookies, or hit a dev-login
  endpoint yourself, and use the real login UI only when the path is `form`. If it's 'none' or
  the path fails, return `unverifiable` and stop — never improvise a way past auth.
PROTECTION (a preview behind the host's login wall):
  <the bypass value, or 'none'>. Send it as the `x-vercel-protection-bypass` header on
  every request of your page; never sign in to the host yourself.
BACKEND (repos with `backend: per-branch`):
  <the exact deployment the app is serving>. Pin it on EVERY CLI call
  (--preview-name/--deployment). Unpinned calls resolve to a different deployment than the
  app reads, so your seeds land on one backend and the browser on another — that split-brain
  reports as a broken feature and burns the whole round.

Drive the REAL flow — walk the exact steps a user would, clicking through it. Check the
console for errors along the way. A print flow: headless `window.print()` stalls the
browser tool, so judge the printout with print-media emulation first and click Print last.
Screenshot the MEANINGFUL BEATS (start → action → success), not a random dump. Judge
observed vs expected. Return ONLY:

VERDICT: works | broken | unverifiable
EVIDENCE: ordered list of "<screenshot path> — <plain-language caption>"   (the storyboard)
EXPECTED: <criteria>
OBSERVED: <what actually happened>
TASTE: <0-3 short "looked off / couldn't confirm" notes, or "none">
FIX: for each failure or taste note, its likely cause and the fix you'd make, with the
     file:line when you can read it (read files; never edit them), or "none"

This report is your FINAL MESSAGE — it is what the caller reads;
finishing without it is an incomplete run.
```

**Auth-walled surface with no test-auth path (the AUTH line says so):** the verifier
walks everything short of the wall, and the verdict is `unverifiable` naming the
wall. Park with a `needs input:` so Pete walks that part himself.

- **broken** → fix the implementation. The tester's `FIX` lines are leads, not orders:
  check each against the code and fix the root cause, which may sit elsewhere. Then spawn a **fresh** verifier (never reuse the one
  that saw the bug — it's no longer independent of the fix). Cap at ~3 rounds.
- **still broken after the cap**, or **unverifiable** for a reason ship can't fix (a hand-off
  fixes and retests the ones it can, above) → stop and hand the verdict + evidence up to
  the caller for Pete. Never loop forever; never merge unproven.
