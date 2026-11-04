#!/bin/bash
# mac-vm.sh: a macOS VM that ships borrow to check a Mac app with agent-desktop, so nothing a
# check opens, clicks or captures shows on Pete's screen or touches his apps, logins and
# permissions, and Pete's own VM beside it. Lume runs them headless, with no window and no VNC,
# until Pete opens one from his menu bar (menubar/ in the ship repo). Every borrow boots a fresh
# clone of the base, so a ship never sees another's leftovers. Pete's VM is kept: it holds his
# Apple Account and apps, and agents drive it only through his my-mac skill, never a ship.
#   mac-vm.sh borrow [--wait]      take a free slot (--wait: up to 8 min) and boot a fresh clone; prints SLOT=<n> IP=<ip>
#   mac-vm.sh run <n> <cmd>        a shell command in slot n as user lume (agent-desktop and node on PATH)
#   mac-vm.sh tunnel <n> <port>    the VM's localhost:<port> reaches this Mac's localhost:<port>
#   mac-vm.sh put <n> <path.app>   quit and replace the app in the VM's ~/Applications; prints its path there
#   mac-vm.sh shot <n> <out.png>   the VM's whole screen, saved on this Mac
#   mac-vm.sh return <n>           stop and delete the clone, free the slot
#   mac-vm.sh status               each slot's holder and when it last used it
#   mac-vm.sh view <n>|mine        that VM's screen in a window on this Mac: Pete's menu bar click, never a ship
#   mac-vm.sh mine up|down         start Pete's VM (the first start clones the base), or shut it down cleanly
#   mac-vm.sh mine run <cmd>       a shell command in Pete's VM; mine shot <out.png> its whole screen
#   mac-vm.sh base                 rebuild the base from Apple's newest macOS (~30 min, a 20 GB download)
#   mac-vm.sh grant                rerun only the base's last step, the offline one, after it failed
#   mac-vm.sh --selftest           the slot bookkeeping, against a fake lume and ssh
# Run it unsandboxed from the ship's worktree: the worktree is the slot's holder, and only the
# holder can drive or return it. It drives ~/.lume and ssh to the VMs' 192.168.64.x addresses.
set -euo pipefail
self=$(cd "$(dirname "$0")" && pwd)/$(basename "$0")
dir=${SHIP_MAC_DIR:-$HOME/.config/ship-mac}
key=$dir/vm_key
base=ship-mac-base
slots=${SHIP_MAC_SLOTS:-1}  # Apple allows two macOS VMs running on one Mac, and Virtualization
mine=pete-mac               # enforces it: one for ships, one Pete's own, kept between uses
stale=$((2 * 3600))  # a slot unused this long, or whose worktree is gone, can be taken again

vm() { echo "ship-mac-$1"; }
info() { lume get "$1" -f json 2>/dev/null | jq -r "(if type == \"array\" then .[0] else . end).$2 // empty" 2>/dev/null; }
ipof() { info "$1" ipAddress; }
sshv() {  # sshv <vm> <args...>: one control connection per VM, kept until return, so tunnels ride it
  local name=$1 ip alias=ship-mac kh=$dir/known_hosts strict=yes; shift
  ip=$(ipof "$name" || true); [ -n "$ip" ] || { echo "$name isn't running" >&2; return 255; }
  # Pete's VM keeps its host key across base rebuilds, which replace the clones' shared one.
  [ "$name" = "$mine" ] && { alias=$mine; kh=$dir/known_hosts.mine; strict=accept-new; }
  ssh -i "$key" -o IdentitiesOnly=yes -o BatchMode=yes -o HostKeyAlias="$alias" -o CheckHostIP=no \
    -o StrictHostKeyChecking="$strict" -o UserKnownHostsFile="$kh" -o ConnectTimeout=5 \
    -o LogLevel=ERROR -o ControlMaster=auto -o ControlPath="$dir/$name.sock" -o ControlPersist=yes \
    -o ServerAliveInterval=15 -o ServerAliveCountMax=4 "lume@$ip" "$@"
}
close() { ssh -o ControlPath="$dir/$1.sock" -O exit x 2>/dev/null || true; }

# A lease is a symlink whose target is "<worktree>|<epoch>": creating one is atomic, so two
# ships can't take the same slot. ponytail: a reclaim racing a fresh borrow, or the holder's
# refresh in the same second its lease turns two hours old, could drop one; a lock file waits
# until that happens.
holder() { git rev-parse --show-toplevel 2>/dev/null || pwd; }
lease() { readlink "$dir/slots/$1" 2>/dev/null; }
refresh() { ln -s "$2|$(date +%s)" "$dir/slots/$1.$$" && mv -f "$dir/slots/$1.$$" "$dir/slots/$1"; }  # a rename is atomic
held() {
  local v; v=$(lease "$1") || return 1
  [ -d "${v%|*}" ] && [ $(( $(date +%s) - ${v##*|} )) -lt $stale ]
}
take() {
  mkdir -p "$dir/slots"
  local n l v me; me=$(holder)
  # A worktree that borrows again gets its own slot back, freshly cloned, not the other one too.
  for n in $(seq 1 $slots); do
    v=$(lease "$n") && [ "${v%|*}" = "$me" ] && { refresh "$n" "$me"; echo "$n"; return 0; }
  done
  for n in $(seq 1 $slots); do
    l=$dir/slots/$n
    if [ -L "$l" ] && ! held "$n"; then mv "$l" "$l.stale.$$" 2>/dev/null && rm -f "$l.stale.$$"; fi
    ln -s "$me|$(date +%s)" "$l" 2>/dev/null && { echo "$n"; return 0; }
  done
  return 1
}
not_a_ship() {  # a tripwire, not a lock: any local process can still reach Pete's VM
  [ ! -f "$(holder)/.ship-stage" ] || { echo "a ship never uses Pete's VM; borrow a slot instead" >&2; exit 2; }
}
valid() { [[ "${1:-}" =~ ^[1-9]$ ]] && [ "$1" -le $slots ] || { echo "no slot '${1:-}'" >&2; exit 2; }; }
slot() {  # slot <n>: the caller's own slot, its lease refreshed; prints the VM's name
  valid "${1:-}"
  local v me; v=$(lease "$1") || v=; me=$(holder)
  [ "${v%|*}" = "$me" ] || { echo "slot $1 isn't held from $me: $(status | sed -n "${1}p")" >&2; exit 2; }
  refresh "$1" "$me"; vm "$1"
}

status() {
  local n v
  for n in $(seq 1 $slots); do
    if held "$n"; then v=$(lease "$n"); echo "slot $n: ${v%|*}, last used $(( ($(date +%s) - ${v##*|}) / 60 )) min ago"
    else echo "slot $n: free"; fi
  done
  echo "mine: $(info "$mine" status || true)"
}

boot() {  # boot <vm>: headless, then wait for ssh and the logged-in desktop. Called under if, so set -e
  local name=$1 i  # is off here and each step returns on its own failure.
  lume run "$name" --display none --vnc disabled --detach >/dev/null || return 1
  for i in $(seq 90); do [ -n "$(ipof "$name")" ] && sshv "$name" true 2>/dev/null && break; sleep 2; done
  sshv "$name" 'for i in $(seq 60); do pgrep -qx Finder && exit 0; sleep 1; done; exit 1' || return 1
  # About ten seconds after the first capture, slower on a busy Mac, macOS asks over the screen
  # whether ssh may keep capturing it, and one Allow lasts the borrow. Its approvals file can't be
  # seeded: replayd rewrites it and asks anyway. The last capture checks agent-desktop runs.
  sshv "$name" 'for i in $(seq 20); do agent-desktop screenshot --screen 0 /tmp/w.png >/dev/null 2>&1
    r=$(agent-desktop snapshot --app UserNotificationCenter -i --timeout-ms 1500 2>/dev/null |
      jq -r "[.. | objects | select(.role == \"button\" and .name == \"Allow\") | .ref_id][0] // empty")
    [ -n "$r" ] && { agent-desktop click "$r" >/dev/null; break; }; sleep 2; done
    [ -n "$r" ] || echo "no capture prompt came; if a shot shows one, click its Allow in UserNotificationCenter" >&2
    agent-desktop screenshot --screen 0 /tmp/w.png >/dev/null; s=$?; rm -f /tmp/w.png; exit $s'
}

wipe() {  # wipe <vm>: its connection, then the VM. Lume's delete leaves a --detach VM running,
  close "$1"; lume stop "$1" --force >/dev/null 2>&1 || true  # so only a stopped one is deleted.
  case "$(info "$1" status)" in
    ""|stopped) lume delete "$1" --force >/dev/null 2>&1 || true ;;
    *) echo "$1 would not stop and is still running: lume stop $1 --force" >&2 ;;
  esac
}
borrow() {
  local n waited=0
  until n=$(take); do
    [ "${1:-}" = --wait ] || { echo "every ship Mac VM is out:" >&2; status >&2; exit 3; }
    [ $waited -lt 480 ] || { echo "no Mac VM came free in 8 min:" >&2; status >&2; exit 3; }
    sleep 20; waited=$((waited + 20))
  done
  local name o; name=$(vm "$n")
  # A slot whose holder is gone or two hours idle still has its clone running: stop that too.
  for o in $(seq 1 $slots); do [ "$o" = "$n" ] || [ ! -L "$dir/slots/$o" ] || held "$o" || give_back "$o"; done
  wipe "$name"
  if ! { lume clone "$base" "$name" >/dev/null && boot "$name"; }; then
    give_back "$n"; echo "slot $n did not boot; it is free again" >&2; exit 1
  fi
  echo "SLOT=$n IP=$(ipof "$name")"
}
give_back() { wipe "$(vm "$1")"; rm -f "$dir/slots/$1"; }
halt() {  # halt <vm>: shut down from inside, since lume stop powers off and a kept disk loses writes
  local i
  sshv "$1" 'sudo shutdown -h now' >/dev/null 2>&1 || true; close "$1"
  for i in $(seq 60); do [ "$(info "$1" status)" = stopped ] && return 0; sleep 2; done
  return 1
}
mine_up() {  # the first start clones the base; every later one boots the same kept disk
  local i
  case "$(info "$mine" status)" in
    running) for i in $(seq 60); do sshv "$mine" true 2>/dev/null && return 0; sleep 2; done; return 1 ;;
    "") lume clone "$base" "$mine" >/dev/null || return 1 ;;
  esac
  boot "$mine"
}
capture() {  # capture <vm> <out.png>: its whole screen, saved on this Mac
  sshv "$1" 'f=/tmp/shot-$$.png; agent-desktop screenshot --screen 0 "$f" >/dev/null && cat "$f"; rm -f "$f"' > "$2" || true
  [ -s "$2" ] || { rm -f "$2"; echo "no screenshot" >&2; exit 1; }
}

grant_offline() {  # the base's last step, on its stopped disk, where nothing running can write it back
  local whole rc=0
  [ "$(info "$base" status)" = stopped ] || { echo "$base is running or missing; stop it first" >&2; return 1; }
  whole=$(hdiutil attach -imagekey diskimage-class=CRawDiskImage -nomount -nobrowse "$HOME/.lume/$base/disk.img" 2>/dev/null |
    awk '$2 == "GUID_partition_scheme" {print $1; exit}')  # its lines come in any order
  [ -n "$whole" ] || { echo "could not attach the base's disk" >&2; return 1; }
  write_offline "$whole" || rc=$?
  hdiutil detach "$whole" -force >/dev/null 2>&1 || { echo "could not detach it: hdiutil detach $whole -force" >&2; rc=1; }
  return $rc
}
write_offline() {  # called under ||, where set -e is off, so every step is one chain
  local data mp lw
  # The disk holds several APFS containers; only the main one has the Data volume.
  data=$(diskutil apfs list -plist | python3 -c '
import plistlib, sys
w = sys.argv[1].replace("/dev/", "") + "s"
for c in plistlib.loads(sys.stdin.buffer.read())["Containers"]:
    if any(s.get("DeviceIdentifier", "").startswith(w) for s in c.get("PhysicalStores", [])):
        for v in c["Volumes"]:
            if "Data" in v.get("Roles", []): print(v["DeviceIdentifier"]); sys.exit()' "$1") && [ -n "$data" ] &&
  diskutil mount -mountOptions nobrowse "$data" >/dev/null &&
  mp=$(diskutil info -plist "$data" | python3 -c 'import plistlib,sys; print(plistlib.loads(sys.stdin.buffer.read())["MountPoint"])') &&
  # csreq: identifier "com.apple.sshd-keygen-wrapper" and anchor apple, the row macOS itself writes.
  sqlite3 "$mp/Library/Application Support/com.apple.TCC/TCC.db" "INSERT OR REPLACE INTO access
    (service, client, client_type, auth_value, auth_reason, auth_version, csreq, flags, last_reminded) VALUES
    ('kTCCServiceAccessibility', '/usr/libexec/sshd-keygen-wrapper', 1, 2, 4, 1, $req, 0, 4102444800),
    ('kTCCServiceScreenCapture', '/usr/libexec/sshd-keygen-wrapper', 1, 2, 4, 1, $req, 0, 4102444800),
    ('kTCCServiceSystemPolicyAllFiles', '/usr/libexec/sshd-keygen-wrapper', 1, 2, 4, 1, $req, 0, 4102444800);" &&
  # Setup Assistant's mini mode opened at every login on the Apple Account page. A login turns
  # MiniBuddyLaunch on when the key is missing, and setup turns it off once finished, as on Pete's
  # Mac; so it is written off, and the saved session that reopened Setup Assistant goes.
  lw="$mp/Users/lume/Library/Preferences/com.apple.loginwindow.plist" &&
  { [ -f "$lw" ] || plutil -create xml1 "$lw"; } && plutil -replace MiniBuddyLaunch -bool NO "$lw" &&
  { plutil -remove MiniBuddyLaunchCount "$lw" 2>/dev/null; true; } &&
  rm -f "$mp/Users/lume/Library/Group Containers/group.com.apple.loginwindow.persistent-apps/persistantApps" &&
  diskutil unmount "$data" >/dev/null
}
req="X'FADE0C000000003C0000000100000006000000020000001D636F6D2E6170706C652E737368642D6B657967656E2D7772617070657200000000000003'"

build_base() {
  local n
  for n in $(seq 1 $slots); do ! held "$n" || { echo "slot $n is out; the base waits until it is back" >&2; status >&2; exit 3; }; done
  [ "$(info "$mine" status)" != running ] || { echo "Pete's VM is running, and the base would be a third: mine down first" >&2; exit 3; }
  for n in $(seq 1 $slots); do give_back "$n"; done  # a stale slot's clone can still be running
  mkdir -p "$dir" && chmod 700 "$dir"
  [ -f "$key" ] || ssh-keygen -q -t ed25519 -N '' -C ship-mac -f "$key"
  rm -f "$dir/known_hosts"
  wipe "$base"
  # --unattended writes Lume's lume/lume admin user, autologin and sshd onto the disk offline.
  lume create "$base" --ipsw latest --cpu 4 --memory 6GB --disk-size 80GB --unattended tahoe
  trap 'close "$base"; lume stop "$base" --force >/dev/null 2>&1 || true' EXIT  # a failed build stops it
  lume run "$base" --display none --vnc disabled --detach >/dev/null
  local ip i; for i in $(seq 90); do ip=$(ipof "$base"); [ -n "$ip" ] && nc -z -G 2 "$ip" 22 2>/dev/null && break; sleep 2; done
  # The one password login: it installs the key, and provisioning turns password logins off.
  local ask; ask=$(mktemp); printf '#!/bin/sh\necho lume\n' > "$ask"; chmod 700 "$ask"
  SSH_ASKPASS=$ask SSH_ASKPASS_REQUIRE=force DISPLAY=:0 ssh -o PubkeyAuthentication=no -o HostKeyAlias=ship-mac \
    -o StrictHostKeyChecking=accept-new -o UserKnownHostsFile="$dir/known_hosts" "lume@$ip" \
    'umask 077; mkdir -p ~/.ssh; cat >> ~/.ssh/authorized_keys' < "$key.pub"
  rm -f "$ask"
  sshv "$base" "TZNAME='$(readlink /etc/localtime | sed 's#.*zoneinfo/##')' NODE=v26.13.0 bash -s" <<'EOF'
set -euo pipefail
echo lume | sudo -S -p '' sh -c 'echo "lume ALL=(ALL) NOPASSWD: ALL" > /etc/sudoers.d/lume; chmod 440 /etc/sudoers.d/lume'
sudo ln -sf "/usr/share/zoneinfo/$TZNAME" /etc/localtime
cd ~ && f=node-$NODE-darwin-arm64.tar.gz
curl -fsSLO "https://nodejs.org/dist/$NODE/$f"
curl -fsSL "https://nodejs.org/dist/$NODE/SHASUMS256.txt" | grep " $f\$" | shasum -a 256 -c - >/dev/null
rm -rf node && tar -xzf "$f" && mv "node-$NODE-darwin-arm64" node && rm "$f"
echo 'export PATH=$HOME/node/bin:$PATH' > ~/.zshenv
export PATH=$HOME/node/bin:$PATH
npm i -g --silent agent-desktop
# Lume stamps setup as seen on a macOS 26 build, so a newer macOS reopens Setup Assistant at
# login on the Apple Account page; stamp this build and every page as seen.
b=$(sw_vers -buildVersion); v=$(sw_vers -productVersion)
for k in Accessibility ActivationLock AppStore AppearanceSetup ApplePaySetup CloudSetup Intelligence LockdownMode \
  Privacy ScreenTime SiriSetup SyncSetup SyncSetup2 TermsOfAddress TouchIDSetup TrueToneSetup iCloudLoginForStorageServices; do
  defaults write com.apple.SetupAssistant "DidSee$k" -bool true
done
defaults delete com.apple.SetupAssistant MiniBuddyLaunchReason 2>/dev/null || true
defaults write com.apple.SetupAssistant LastSeenBuddyBuildVersion "$b"
defaults write com.apple.SetupAssistant LastSeenCloudProductVersion "$v"
sudo defaults write /Library/Preferences/com.apple.SetupAssistant LastSeenBuddyBuildVersion "$b"
sudo defaults write /Library/Preferences/com.apple.SetupAssistant LastSeenCloudProductVersion "$v"
sudo sh -c 'printf "PasswordAuthentication no\nKbdInteractiveAuthentication no\n" > /etc/ssh/sshd_config.d/100-ship.conf'
echo "base: macOS $v ($b), node $(node -v), agent-desktop $(agent-desktop version | jq -r .data.version)"
EOF
  # Shut down from inside: lume stop powers off, and provisioning's last writes could be lost.
  halt "$base" || lume stop "$base" >/dev/null
  trap - EXIT
  grant_offline
  echo "base ready"
}

selftest() {
  t=$(cd "$(mktemp -d)" && pwd -P); trap 'rm -rf "$t"' EXIT
  mkdir -p "$t/bin" "$t/cfg"
  cat > "$t/bin/lume" <<EOF
#!/bin/sh
echo "\$@" >> $t/lume.log
case "\$1" in  # a VM is made by clone, running from run, stopped by stop, gone after delete
  get) s=; [ -f $t/made.\$2 ] && s=\$(cat $t/state.\$2 2>/dev/null || echo stopped)
       ip=; [ "\$s" = running ] && ip=192.168.64.9
       echo "{\\"ipAddress\\":\\"\$ip\\",\\"status\\":\\"\$s\\"}" ;;
  clone) touch $t/made.\$3 ;;
  run) echo running > $t/state.\$2 ;;
  stop) echo stopped > $t/state.\$2 ;;
  delete) rm -f $t/made.\$2 $t/state.\$2 ;;
esac
exit 0
EOF
  printf '#!/bin/sh\ncase "$*" in *shutdown*) echo stopped > %s/state.pete-mac ;; esac\nexit 0\n' "$t" > "$t/bin/ssh"
  chmod +x "$t/bin/lume" "$t/bin/ssh"
  for w in a b c; do git init -q "$t/$w"; done
  me() { (cd "$t/$1" && SHIP_MAC_SLOTS=${ts:-2} SHIP_MAC_DIR=$t/cfg PATH="$t/bin:$PATH" bash "$self" "${@:2}"); }
  local fail=0 out
  check() { if [ "$2" = "$3" ]; then echo "ok   $1"; else echo "FAIL $1: got '$2', want '$3'"; fail=1; fi; }
  check "first borrow gets slot 1" "$(me a borrow)" "SLOT=1 IP=192.168.64.9"
  check "second borrow gets slot 2" "$(me b borrow)" "SLOT=2 IP=192.168.64.9"
  me c borrow >/dev/null 2>&1 && out=0 || out=$?
  check "a third borrow without --wait is refused" "$out" 3
  check "the borrow cloned the base into the slot" "$(grep -c '^clone ship-mac-base ship-mac-1$' "$t/lume.log")" 1
  check "status names each holder" "$(me c status | grep -c "slot [12]: $t/[ab],")" 2
  me c run 1 true >/dev/null 2>&1 && out=0 || out=$?
  check "another worktree can't drive a slot" "$out" 2
  me c return 2 >/dev/null 2>&1 && out=0 || out=$?
  check "another worktree can't return a slot" "$out" 2
  check "the holder drives its slot" "$(me a run 1 true >/dev/null 2>&1 && echo yes)" yes
  me c base >/dev/null 2>&1 && out=0 || out=$?
  check "the base won't rebuild while a slot is out" "$out" 3
  rm -rf "$t/a"
  check "a slot whose worktree is gone is free again" "$(me c borrow)" "SLOT=1 IP=192.168.64.9"
  check "borrowing again recycles your own slot" "$(me c borrow)" "SLOT=1 IP=192.168.64.9"
  ln -sfn "$t/b|$(( $(date +%s) - stale - 1 ))" "$t/cfg/slots/2"
  check "a slot unused past the limit is free" "$(me c status | sed -n 2p)" "slot 2: free"
  me c borrow >/dev/null
  check "a borrow stops the stale slot's clone" "$([ -L "$t/cfg/slots/2" ] || grep -c '^delete ship-mac-2 --force$' "$t/lume.log")" 2
  me c return 1
  check "return frees the slot" "$(me c status | sed -n 1p)" "slot 1: free"
  check "every borrow and return deletes the old clone" "$(grep -c '^delete ship-mac-1 --force$' "$t/lume.log")" 5
  me c run 7 true >/dev/null 2>&1 && out=0 || out=$?
  check "a slot past the two is refused" "$out" 2
  me c view 2 >/dev/null
  check "view opens any slot's screen, held or not" "$(grep -c '^attach ship-mac-2 --display native$' "$t/lume.log")" 1
  me c view 3 >/dev/null 2>&1 && out=0 || out=$?
  check "view refuses a slot past the two" "$out" 2
  ts=1; me b borrow >/dev/null
  me c borrow >/dev/null 2>&1 && out=0 || out=$?
  check "by default ships share one slot" "$out" 3
  me b return 1; ts=
  check "Pete's VM shows as not made yet" "$(me c status | tail -1)" "mine: "
  me c mine run true >/dev/null 2>&1 && out=0 || out=$?
  check "a command in Pete's VM while it's off fails" "$out" 255
  touch "$t/b/.ship-stage"; me b mine up >/dev/null 2>&1 && out=0 || out=$?
  check "a ship's worktree can't start Pete's VM" "$out" 2
  me b view mine >/dev/null 2>&1 && out=0 || out=$?
  check "or open it" "$out" 2
  rm "$t/b/.ship-stage"
  me c mine up >/dev/null; me c mine down; me c mine up >/dev/null
  check "Pete's VM is cloned from the base once, then kept" "$(grep -c '^clone ship-mac-base pete-mac$' "$t/lume.log")" 1
  check "and boots again on the same disk" "$(grep -c '^run pete-mac ' "$t/lume.log")" 2
  check "status shows it running" "$(me c status | tail -1)" "mine: running"
  me c base >/dev/null 2>&1 && out=0 || out=$?
  check "the base won't build beside Pete's running VM" "$out" 3
  me b borrow >/dev/null; me b return 1
  check "no borrow or return touches Pete's VM" "$(grep -c -E '^(delete|stop) pete-mac' "$t/lume.log")" 0
  me c view mine >/dev/null
  check "view mine opens Pete's VM" "$(grep -c '^attach pete-mac --display native$' "$t/lume.log")" 1
  [ $fail = 0 ] && echo "mac-vm.sh selftest ok" || exit 1
}

case "${1:-}" in
  borrow) borrow "${2:-}" ;;
  run) name=$(slot "${2:-}"); shift 2; sshv "$name" "$@" ;;
  tunnel) name=$(slot "${2:-}"); port=${3:?usage: mac-vm.sh tunnel <n> <port>}
          sshv "$name" true; ssh -o ControlPath="$dir/$name.sock" -O forward -R "$port:localhost:$port" x ;;
  put) name=$(slot "${2:-}"); app=${3:?usage: mac-vm.sh put <n> <path.app>}; app=${app%/}; b=$(basename "$app")
       tar -C "$(dirname "$app")" -cf - "$b" |
         sshv "$name" "pkill -f '/Users/lume/Applications/${b//./[.]}/' && sleep 1; mkdir -p ~/Applications && rm -rf ~/Applications/'$b' && tar -C ~/Applications -xf -"
       echo "/Users/lume/Applications/$b" ;;
  shot) name=$(slot "${2:-}"); capture "$name" "${3:?usage: mac-vm.sh shot <n> <out.png>}" ;;
  return) slot "${2:-}" >/dev/null; give_back "$2" ;;
  status) status ;;
  view) if [ "${2:-}" = mine ]; then not_a_ship; name=$mine; else valid "${2:-}"; name=$(vm "$2"); fi
        lume attach "$name" --display native ;;  # no VNC to fall back on; closing or quitting the viewer only hides it
  mine) not_a_ship
        case "${2:-}" in
          up) mine_up || { echo "$mine did not come up" >&2; exit 1; } ;;
          down) [ "$(info "$mine" status)" != running ] || halt "$mine" || { echo "$mine did not shut down in 2 min" >&2; exit 1; } ;;
          run) shift 2; sshv "$mine" "$@" ;;
          shot) capture "$mine" "${3:?usage: mac-vm.sh mine shot <out.png>}" ;;
          *) echo "usage: mac-vm.sh mine up|down|run <cmd>|shot <out.png>" >&2; exit 2 ;;
        esac ;;
  base) build_base ;;
  grant) grant_offline && echo "base ready" ;;  # the base's last step alone, after a failure there
  --selftest) selftest ;;
  *) sed -n '2,22p' "$self"; exit 2 ;;
esac
