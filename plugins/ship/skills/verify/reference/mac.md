# A Mac app, through the repo's own rig

Read when the repo's contract has `mac:`. Run it whenever the Mac app can see the change; it
prints the MAC line. Drive the app the way the repo's checks skill says (its UI test fixtures,
a live test against the branch server). On Pete's Mac that is never desktop control, and the
app launches with `open -g` so it never takes his screen.

## The borrowed VM

A step that needs the app's own screens (a click, a field, what a window shows) runs in a
borrowed Mac VM, a clean headless Mac with none of his logins, apps or permission grants.
`scripts/mac-vm.sh` in the pipeline skill runs it, unsandboxed, from the ship's worktree,
which holds the slot:

1. `borrow --wait` with a 600000 ms timeout, since it waits up to 8 minutes for a slot. It
   prints `SLOT=<n>`, and borrowing again from the same worktree hands back that slot.
2. Build the branch's app against a localhost port of the worktree's server, never a
   `*.localhost` name on :80, which the VM can't take.
3. `put <n> <app>`, `tunnel <n> <port>`, then drive it through `run <n> '<cmd>'` with
   agent-desktop: `open -g` the app, `agent-desktop snapshot --app <name> -i`, then `click` or
   `set-value` on a ref exactly as the snapshot's `ref_id` prints it (`click
   @s2r8zyd7kmosvb:e9`), and `shot <n> <png>` to see the whole screen.
4. `return <n>` the moment the walk ends, pass or fail: an abandoned VM keeps running, and
   only after two idle hours can another ship's borrow take its slot and delete it.

What the VM taught:

- A web view's first snapshot can need `--timeout-ms 20000`.
- In a web view, `type` needs `--headed` (physical input) and `press return --app <App>
  --headed` submits. A ref `click` that fails there, `--headed` too, or lands on a row whose
  one AX button swallows a nested "more" button, goes by coordinates: `mouse-click --headed
  --xy <x>,<y>` in points, half the shot's pixels (1920x1440 shots, scale 2).
- The app's first-run banners (Login Item Added, its notifications ask) sit over the
  top-right for the walk: `dismiss-all-notifications` is refused by policy, and
  `dismiss-notification <i>` from `list-notifications` needs `--expected-title`.
- Never `osascript` there: its Automation prompt hangs the command.

## A rig on Pete's Mac

A rig's own windows are on his screen too, `orderBack` or not, until torn down: open them just
before the steps that need them and tear them down right after (CEL-222's live-node test
windows sat over his terminal until he asked). A window level under `.normal` hides them from
CGWindowList, which the capture needs, so that is no way out.

A Chrome it needs, an extension under test included, is Chrome for Testing launched by the
global rule (`open -g -n -a <app> --args --no-startup-window --use-mock-keychain
--load-extension=<dir>`), never his Chrome.

A rig a run had to build (CEL-198 built a relaunch script and a live-test fixture, and it
found six real bugs) goes into the checks skill by verify §5, so the next run starts from it.

**Check the lock before a step that captures the Mac's screen**: `ioreg -n Root -d1 | grep -q
'"CGSSessionScreenIsLocked"=Yes'` means locked, and a capture then hangs (CEL-198's
`Page.captureScreenshot` sat over 60 s). Locked parks that step with `needs input:` "unlock
the Mac"; steps that capture nothing still run.
