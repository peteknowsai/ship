// ship-vms: Pete's menu bar list of the Mac VMs ships borrow (mac-vm.sh). Each slot shows the
// worktree holding it and when it last used it; clicking a held slot opens its screen in Lume's
// viewer. Closing or quitting that viewer only hides it, so the ship's VM keeps running.
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

if CommandLine.arguments.contains("--selftest") {
  let cases: [(Substring, Slot?)] = [
    ("slot 1: /Users/pete/Projects/.worktrees/cells-app/fix-x, last used 3 min ago",
     Slot(n: "1", title: "1  cells-app/fix-x · 3 min ago", held: true)),
    ("slot 2: free", Slot(n: "2", title: "2  free", held: false)),
    ("no slot '7'", nil),
  ]
  for (line, want) in cases where parse(line) != want {
    print("FAIL \(line): got \(String(describing: parse(line)))"); exit(1)
  }
  print("ship-vms selftest ok"); exit(0)
}

let script = CommandLine.arguments.dropFirst().first
  ?? NSHomeDirectory() + "/Projects/ship/plugins/ship/skills/pipeline/scripts/mac-vm.sh"

func vm(_ args: [String]) -> (ok: Bool, out: String) {
  let p = Process(), pipe = Pipe()
  p.executableURL = URL(fileURLWithPath: "/bin/bash")
  p.arguments = [script] + args
  p.standardOutput = pipe
  p.standardError = pipe
  do { try p.run() } catch { return (false, "\(error)") }
  let out = String(decoding: pipe.fileHandleForReading.readDataToEndOfFile(), as: UTF8.self)
  p.waitUntilExit()
  return (p.terminationStatus == 0, out)
}

func slots() -> [Slot] { vm(["status"]).out.split(separator: "\n").compactMap(parse) }

final class Menu: NSObject, NSApplicationDelegate, NSMenuDelegate {
  let item = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
  let menu = NSMenu()

  func applicationDidFinishLaunching(_ note: Notification) {
    item.button?.image = NSImage(systemSymbolName: "macwindow", accessibilityDescription: "Ship Mac VMs")
    item.button?.imagePosition = .imageLeading
    menu.delegate = self
    item.menu = menu
    count(slots())
    Timer.scheduledTimer(withTimeInterval: 15, repeats: true) { _ in self.count(slots()) }
  }

  func count(_ s: [Slot]) {  // the number beside the icon: VMs in use now
    let busy = s.filter(\.held).count
    item.button?.title = busy > 0 ? " \(busy)" : ""
  }

  func menuNeedsUpdate(_ menu: NSMenu) {
    let s = slots()
    count(s)
    menu.removeAllItems()
    menu.addItem(.sectionHeader(title: "Ship Mac VMs"))
    for slot in s {
      let row = NSMenuItem(title: slot.title, action: slot.held ? #selector(open(_:)) : nil, keyEquivalent: "")
      row.target = self
      row.representedObject = slot.n
      if slot.held { row.toolTip = "Open its screen. A ship may be driving it, and your clicks reach the VM." }
      menu.addItem(row)
    }
    if s.isEmpty { menu.addItem(withTitle: "mac-vm.sh status gave nothing", action: nil, keyEquivalent: "") }
    menu.addItem(.separator())
    menu.addItem(withTitle: "Quit", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q")
  }

  @objc func open(_ row: NSMenuItem) {
    guard let n = row.representedObject as? String else { return }
    DispatchQueue.global().async {  // lume attach checks the VM's lock with lsof, up to 10 s
      let r = vm(["view", n])
      guard !r.ok else { return }
      DispatchQueue.main.async {
        let alert = NSAlert()
        alert.messageText = "Couldn't open VM \(n)"
        alert.informativeText = r.out
        NSApp.activate()
        alert.runModal()
      }
    }
  }
}

let app = NSApplication.shared
let delegate = Menu()
app.delegate = delegate
app.setActivationPolicy(.accessory)
app.run()
