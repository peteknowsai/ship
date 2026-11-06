# iOS: the phone, simulators and Safari

Read when the repo's contract has `ios:`, or the spec or storyboard says mobile web. The
driver is the agent-device CLI from the shell (`agent-device help manual-qa` and
`help debugging` are its guides): a native app on Pete's own iPhone ("iPhone PM") or an Xcode
simulator, and mobile web only in a simulator. Never control the Mac's desktop.

## Which device

**Mobile web runs in a simulator's Safari**, added when the build is meant for phones (the
spec or storyboard says mobile web): a judgment call on what's being built, never a default.
The web walk at 390px in the browser still runs. iPhone PM's Safari is used only when Pete
asks for it or the feature lives on a network only the phone joins (a VPN or tailnet name a
simulator can't reach) (Pete, 2026-10-05). Then drive it by coordinates: `press` the address
field, `fill` the URL, `press` the keyboard's Go key; `open <url>` doesn't navigate the open
tab and `keyboard return` times out on the device (2026-10-14).

**A simulator check that only looks at a page runs headless**, with no agent-device and no
Simulator.app, which opens on Pete's screen, on a clone of its own (below): `xcrun simctl
bootstatus <udid> -b` boots it and waits, `xcrun simctl openurl <udid> <url>`, then `xcrun
simctl io <udid> screenshot <png>` until two shots a few seconds apart match, since Safari
may still be loading.

**A native app runs on the phone** whenever `agent-device devices` lists it, since the phone
is the real thing: three scroll fixes passed in a simulator and failed on iPhone PM.
Otherwise a booted simulator, and the result says which ran.

**A locked or held phone stops nothing.** Locked, or showing an XCTest passcode or Enable UI
Automation prompt: walk the step on a simulator, unless the change needs the phone itself,
meaning a simulator can't show it (touch and scroll feel, the camera, the mic, push,
location or another system prompt, a network only the phone joins). Then park only that step with `needs input:` ("unlock the
phone", or the prompt it shows) and walk the rest.

## The `ios:` command

`ios:` is the repo's: its contract names the command, which builds the branch's own app
pointed at the branch's server, installs it and prints the IOS line. verify runs it whenever
the app can see the change (its native code, or the server and APIs it calls). Without `ios:`
there is no device step. The pipeline's LAND removes the branch app from the device again,
unless its IOS line says `keep=yes`.

The `ios:` build restarts the branch's server, so it runs before or after a smoke or e2e,
never beside one: a showing-followups smoke went 6/12 red on ECONNRESET while it ran, and
12/12 on the rerun.

**One ship on the phone at a time.** A second ship that finds it held tests on a simulator of
its own: `xcrun simctl clone <base> ship-<slug>`, boot it, pass it to the repo's `ios:`
command by UDID (cells-app: `IOS_SIM=<udid>`; without it the install lands on whichever
simulator is booted, maybe another ship's), and `simctl delete` it at LAND. A shared booted
one is another ship's to shut down mid-QA (2026-10-14).

## The walk

`agent-device open <bundle> --device "iPhone PM" --foreground` (without `--device` it picks a
simulator), then press, fill and scroll with `--settle` and judge from the diff it prints;
`close` when done. What the phone taught (cells-app, 2026-10-05):

- A simulator just cloned or created times out on its first snapshot ("Daemon request timed
  out ... run agent-device prepare ios-runner"): run `agent-device prepare ios-runner
  --platform ios` with its `--udid` and `--session` first, about a minute (cel-257).
- One XCTest runner drives a device at a time. `open` failing twice with "BUILD INTERRUPTED"
  means another session holds it: `pgrep -fl 'xcodebuild.*AgentDeviceRunner'` shows the
  device id and the owner pid in the xctestrun name. Ask that session (ListAgents) or test in
  a simulator, and say which in the result (2026-10-14).
- On a loaded Mac `open` can hang: give it `--timeout 300000` rather than retrying, since each
  retry restarts the shared daemon a sibling ship may be using. After one hang, check the
  phone once with `xcrun devicectl device process launch --device <udid> <bundle>`, then test
  in a simulator and say so (CEL-192, CEL-193).
- A fresh simulator clone asks for the mic, then the camera, mid-walk: decline unless the step
  needs them (cel-202).
- A ref that reads `[covered]` (a SwiftUI `.sheet`'s controls) ignores `press` and `fill`
  without an error: tap its coordinates in points, the screenshot's pixels over the device's
  scale as for `gesture pan` below, then snapshot to see it took (CEL-135, CEL-193).
- A phone another ship just released can still answer `DEVICE_IN_USE` for that ship's session
  handle: reuse it with `--session <that id>`, never close it, since it is theirs.
- Never `press` a ref you didn't just read back from a snapshot. An empty or stale one stops
  the script: on Pete's own phone a misfired tap lands somewhere real. A step that reads a ref
  and presses it (snapshot, pick, press, wait for a text) is one script file under the job's
  tmp run with `bash`, since the worktree guard refuses `ref=$(…)` then `press "$ref"` inline
  (CEL-223 lost five rounds to it).
- On iPhone PM the hand holding the phone is Pete's. Post him one line before the walk ("QA is
  on your phone now, hands off until it says done") and one when it ends; a tap no tool sent
  is his before it is a bug (CEL-223 traced an "Always allow" to one).
- A walk of anything that records on iPhone PM records Pete's room. Say so in the hands-off
  line, keep each recording under a minute, and delete the test person before landing
  (cells-app: `PACK=<pack> npm run prune -- --people --finish <clerk id>`): a 7-minute walk of
  the Homebody walkie transcribed talk near his desk into the test person's showing.
- Read the app's own prints with `xcrun devicectl device process launch --console
  --terminate-existing --device <udid> <bundle>`, and write debug traces to stderr: a
  `print()` block-buffers off a terminal, so its lines arrive late or never.
- Scroll a feed with `agent-device gesture pan <x> <y> <dx> <dy> <ms>` from mid-screen, in
  points: the screenshot's pixels over the device's scale (402×874 on iPhone PM, a third of its
  screenshot; showing-issues' first pan in pixels threw the deck off the screen). `scroll up`
  starts at the bottom edge and can land on the composer, and an open keyboard swallows it.
  After a pan, press only from a snapshot taken once the scroll has stopped (two snapshots a
  second apart that match): a ref read during momentum taps where the element was (CEL-213).
- Seed content from the Mac (the repo's own test helpers or API), never by typing it on the
  phone: `fill` garbles long text.
- To reach a state a short test account can't (paging, a long list), shrink the constants in a
  debug build and never commit them.
