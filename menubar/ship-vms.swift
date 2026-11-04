// ship-vms: Pete's menu bar for the Mac VMs (mac-vm.sh). Each ship slot shows the worktree
// holding it and when it last used it, and clicking a held one opens its screen in Lume's viewer;
// under it, his own VM starts, opens and shuts down. Closing or quitting the viewer only hides it,
// so the VM keeps running.
//   ship-vms [<mac-vm.sh>]   run it (launchd does, from md.cells.ship-vms.plist)
//   ship-vms --selftest      check how status lines become menu rows
// It calls mac-vm.sh in the main checkout, so a merged script change goes live on the next click.
import AppKit

struct Slot: Equatable { let n: String; let title: String; let held: Bool }

// "slot 1: /Users/pete/Projects/.worktrees/cells-app/fix-x, last used 3 min ago"
//   -> "1  cells-app/fix-x · 3 min ago"; "slot 2: free" -> "2  free"
func parse(_ line: Substring) -> Slot? {
  guard line.hasPrefix("slot "), let colon = line.firstIndex(of: ":") else { return nil }
  let n = String(line[line.index(line.startIndex, offsetBy: 5)..<colon])
  let rest = line[line.index(after: colon)...].trimmingCharacters(in: .whitespaces)
  if rest == "free" { return Slot(n: n, title: "\(n)  free", held: false) }
  let parts = rest.components(separatedBy: ", last used ")
  let tree = parts[0].split(separator: "/").suffix(2).joined(separator: "/")
  return Slot(n: n, title: "\(n)  \(tree)" + (parts.count > 1 ? " · \(parts[1])" : ""), held: true)
}

// "mine: running" -> "running"; "mine: " -> "" (not made yet); no line -> nil (status failed)
func mineState(_ lines: [Substring]) -> String? {
  lines.first { $0.hasPrefix("mine:") }.map { $0.dropFirst(5).trimmingCharacters(in: .whitespaces) }
}

if CommandLine.arguments.contains("--selftest") {
  let cases: [(Substring, Slot?)] = [
    ("slot 1: /Users/pete/Projects/.worktrees/cells-app/fix-x, last used 3 min ago",
     Slot(n: "1", title: "1  cells-app/fix-x · 3 min ago", held: true)),
    ("slot 2: free", Slot(n: "2", title: "2  free", held: false)),
    ("no slot '7'", nil),
    ("mine: running", nil),
  ]
  for (line, want) in cases where parse(line) != want {
    print("FAIL \(line): got \(String(describing: parse(line)))"); exit(1)
  }
  for (lines, want) in [(["slot 1: free", "mine: running"], "running"), (["mine: "], ""), (["slot 1: free"], nil)]
  where mineState(lines.map { Substring($0) }) != want {
    print("FAIL mine state of \(lines)"); exit(1)
  }
  print("ship-vms selftest ok"); exit(0)
}

let script = CommandLine.arguments.dropFirst().first
  ?? NSHomeDirectory() + "/Projects/ship/plugins/ship/skills/pipeline/scripts/mac-vm.sh"

func vm(_ args: [String], timeout: Double = 5) -> (ok: Bool, out: String) {
  let p = Process(), pipe = Pipe()
  p.executableURL = URL(fileURLWithPath: "/bin/bash")
  p.arguments = [script] + args
  p.standardOutput = pipe
  p.standardError = pipe
  do { try p.run() } catch { return (false, "\(error)") }
  // A hung status would freeze the menu, Quit included, since KeepAlive sees it alive.
  DispatchQueue.global().asyncAfter(deadline: .now() + timeout) { if p.isRunning { p.terminate() } }
  let out = String(decoding: pipe.fileHandleForReading.readDataToEndOfFile(), as: UTF8.self)
  p.waitUntilExit()
  return (p.terminationStatus == 0, out)
}

func status() -> (slots: [Slot], mine: String?) {
  let lines = vm(["status"]).out.split(separator: "\n")
  return (lines.compactMap(parse), mineState(lines))
}

final class Menu: NSObject, NSApplicationDelegate, NSMenuDelegate {
  let item = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
  let menu = NSMenu()
  var busy: String?  // "Your Mac · starting…" while his VM starts or shuts down

  func applicationDidFinishLaunching(_ note: Notification) {
    item.button?.image = NSImage(systemSymbolName: "macwindow", accessibilityDescription: "Mac VMs")
    item.button?.imagePosition = .imageLeading
    menu.delegate = self
    item.menu = menu
    count(status().slots)
    Timer.scheduledTimer(withTimeInterval: 15, repeats: true) { _ in self.count(status().slots) }
  }

  func count(_ s: [Slot]) {  // the number beside the icon: ship VMs in use now
    let busy = s.filter(\.held).count
    item.button?.title = busy > 0 ? " \(busy)" : ""
  }

  func add(_ title: String, _ action: Selector?, tip: String? = nil, slot: String? = nil) {
    let row = NSMenuItem(title: title, action: action, keyEquivalent: "")
    row.target = self
    row.representedObject = slot
    row.toolTip = tip
    menu.addItem(row)
  }

  func menuNeedsUpdate(_ menu: NSMenu) {
    let s = status()
    count(s.slots)
    menu.removeAllItems()
    menu.addItem(.sectionHeader(title: "Ship Mac VM"))
    for slot in s.slots {
      add(slot.title, slot.held ? #selector(open(_:)) : nil,
          tip: slot.held ? "Open its screen. A ship may be driving it, and your clicks reach the VM." : nil, slot: slot.n)
    }
    if s.slots.isEmpty { add("mac-vm.sh status gave nothing", nil) }
    menu.addItem(.separator())
    menu.addItem(.sectionHeader(title: "Your Mac VM"))
    if let busy {
      add(busy, nil)
    } else if s.mine == "running" {
      add("Open your Mac", #selector(openMine), tip: "Agents may be driving it too, through the my-mac skill.")
      add("Shut down your Mac", #selector(stopMine), tip: "Do this before restarting this Mac: a VM you've opened holds up a restart.")
    } else {
      add(s.mine == "" ? "Start your Mac (the first start makes it)" : "Start your Mac", #selector(startMine))
    }
    menu.addItem(.separator())
    menu.addItem(withTitle: "Quit", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q")
  }

  // Runs mac-vm.sh off the main thread (lume attach checks the VM's lock with lsof, up to 10 s;
  // a start boots for a minute or more), then `next` on success, and alerts on a failure.
  func run(_ args: [String], timeout: Double, doing: String? = nil, next: [String]? = nil) {
    busy = doing
    DispatchQueue.global().async {
      var r = vm(args, timeout: timeout)
      if r.ok, let next { r = vm(next, timeout: 30) }
      DispatchQueue.main.async {
        self.busy = nil
        guard !r.ok else { return }
        let alert = NSAlert()
        alert.messageText = "mac-vm.sh \(args.joined(separator: " ")) failed"
        alert.informativeText = r.out
        NSApp.activate()
        alert.runModal()
      }
    }
  }

  @objc func open(_ row: NSMenuItem) {
    if let n = row.representedObject as? String { run(["view", n], timeout: 30) }
  }
  @objc func openMine() { run(["view", "mine"], timeout: 30) }
  @objc func startMine() { run(["mine", "up"], timeout: 600, doing: "Your Mac · starting…", next: ["view", "mine"]) }
  @objc func stopMine() { run(["mine", "down"], timeout: 150, doing: "Your Mac · shutting down…") }
}

let app = NSApplication.shared
let delegate = Menu()
app.delegate = delegate
app.setActivationPolicy(.accessory)
app.run()
