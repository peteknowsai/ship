---
paths:
  - "menubar/**"
  - "plugins/ship/skills/pipeline/scripts/mac-vm.sh"
  - "plugins/ship/skills/verify/reference/mac.md"
---

# ship-vms — the Mac VMs in the menu bar

`menubar/ship-vms.swift` is Pete's menu bar item for the Mac VMs. Apple lets two run at once, so
ships get one slot, always a fresh clone, and Pete gets one VM of his own, `pete-mac`, kept between
uses with his Apple Account and apps in it. Agents drive his VM only through his `my-mac` skill
(claude-home), never a ship, since his messages are on its screen; `mine` refuses from a worktree
with a `.ship-stage`, a tripwire for accidents rather than a lock. The icon counts the ship VMs in
use, the menu lists the slot's holder from `mac-vm.sh status` and starts, opens or shuts down his
VM (`mine up`, `view mine`, `mine down`), and a click on a held slot
runs `mac-vm.sh view <n>`, which asks the VM's own headless `lume run` process to show its screen
in a window. Closing or quitting that window only hides it; the VM keeps running. The catch: a
viewed VM's Lume process then refuses to quit, so it holds up a logout or restart until its ship
returns the slot or Pete shuts his VM down (`lume stop ship-mac-<n>` ends a ship's sooner, and its
walk with it). A click
while the slot is still booting says the VM isn't running yet. Only Pete's click opens one: a
ship never runs `view`, and nothing but that rule stops it. A launchd agent (`md.cells.ship-vms`, plist in
`menubar/`) starts it at login and calls mac-vm.sh in THIS main checkout, so a script change goes
live on the next click. A change to the Swift file goes live only after `bash menubar/install.sh`
from main, which rebuilds `~/.local/bin/ship-vms` and restarts the agent;
`~/.local/bin/ship-vms --selftest` is its check.

`mac-vm.sh base` rebuilds the base image in about 30 minutes, so run it in the background.
