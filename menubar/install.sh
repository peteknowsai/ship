#!/bin/bash
# install.sh: build ship-vms into ~/.local/bin and (re)start its launchd agent, which keeps it in
# the menu bar from login on (Quit in its menu stays quit until the next login or install).
# Run it from the main checkout after a change to ship-vms.swift merges; a mac-vm.sh change
# needs no rebuild.
set -euo pipefail
here=$(cd "$(dirname "$0")" && pwd)
mkdir -p ~/.local/bin
swiftc -O "$here/ship-vms.swift" -o ~/.local/bin/ship-vms
~/.local/bin/ship-vms --selftest
plist=~/Library/LaunchAgents/md.cells.ship-vms.plist
cp "$here/md.cells.ship-vms.plist" "$plist"
launchctl bootout "gui/$(id -u)/md.cells.ship-vms" 2>/dev/null && sleep 1 || true
launchctl bootstrap "gui/$(id -u)" "$plist"
echo "ship-vms running: look for the window icon in the menu bar"
