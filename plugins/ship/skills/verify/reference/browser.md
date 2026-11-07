# Browser extras: protected previews, Playwright, print, copy, paste, right-click, terminal UI

Read when the target is a protected preview, chrome-devtools is missing, or the walk prints,
copies, pastes, right-clicks, drives a browser on another box, or runs a terminal UI.

## A protected preview

A preview behind the host's login wall (Vercel protection) is reached with its automation
bypass, never through Pete's browser. The secret never sits in a tool call, a URL or qa.md,
where the transcript or the file keeps it (chrome-devtools' `emulate` extraHttpHeaders would
put it there); qa.md's PROTECTION line says `protected`. Let the CLI read it and set the
cookie:

```bash
vercel curl / --deployment <host> -- --silent --output /dev/null \
  --header 'x-vercel-set-bypass-cookie: true' --cookie-jar <jar in <out-dir>>
```

then load the jar's cookies into a Playwright context (`addCookies`) and walk the preview
there (below). Walk one stable host across fix rounds so the cookie, driver and harness carry
over: the branch's git alias (`<project>-git-<branch>-<team>.vercel.app`) when the host builds
each push, else alias each new deploy to one name (`vercel alias set <deploy-url>
<name>.vercel.app`); live-search rebuilt all three for seven fresh deploy URLs.

The measured checks still run on chrome-devtools, against the worktree's own production build
(`next build && next start`, or the repo's equivalent): CLS and accessibility don't change with
the host, and CLS summed by hand from layout-shift entries misreads it (0.12 against a real
0.056).

## Playwright, when chrome-devtools is missing

No chrome-devtools tools in the session (ToolSearch finds none: its `npx` start failed at
launch), or a protected preview: drive headless Chrome through Playwright, imported by its
absolute path from a script in `<out-dir>`, since a bare `import "playwright"` there finds
nothing:

```js
const { chromium } = await import(process.env.HOME + "/node_modules/playwright/index.mjs");
await chromium.launch({ executablePath: /* the chrome-headless-shell binary under
  ~/.cache/puppeteer/chrome-headless-shell/, newest version */ });
```

Never `channel: "chrome"`: that starts the Google Chrome app, and a hidden copy of it makes
macOS switch Pete's Dock click to that copy instead of opening his Chrome (2026-10-12). Use
real locator clicks and keys, never events fired from `evaluate`, read the console through
`page.on("console")`, and say in the result which browser ran.

## Print, copy, paste and right-click

- **Print**: headless `window.print()` stalls the browser, so judge the printout with
  print-media emulation first and click Print last.
- **Copy**: headless Chrome refuses `navigator.clipboard.writeText`, so every Copy button
  reads "Failed to copy". That is the environment, not the app: before the real click, swap
  `writeText` for a recorder with `evaluate_script`, then click, and check the recorded text
  and the success toast.
- **Paste**: chrome-devtools' `fill` and `type_text` fire no paste event, and its page
  refuses `writeText`, so a field that acts on a paste never gets one: hello-dead-ends'
  place field emptied itself at "https://" as a link was typed, and looked up a pasted one.
  Paste through Playwright on chrome-headless-shell, as above: grant
  `['clipboard-read', 'clipboard-write']` with `context.grantPermissions`, await
  `navigator.clipboard.writeText(<text>)` in `page.evaluate` and check that it resolved,
  since a failed write pastes whatever the browser held last, click the field, then
  `page.keyboard.press('ControlOrMeta+V')`.
- **Right-click**: chrome-devtools' click has no right button, so a menu that opens on
  `contextmenu` opens from the keyboard: focus the element with `evaluate_script` and check
  that `document.activeElement` is it, setting `tabIndex = -1` first on one that takes no
  focus, then `press_key` `ContextMenu`. Shift+F10 does nothing on macOS, as muse-spaces'
  Unpin menu showed.

## A browser on another box

When the app drives a browser of its own on another box (a bot's remote Chrome), capture that
box's real screen (its X display) as soon as clicks there stop landing: in browser-replay a
Chrome dialog swallowed every click and only the screen showed it.

## A terminal UI

A Claude Code mod or a CLI screen: run it in a detached tmux session (`tmux new-session -d`,
then `send-keys` and `capture-pane -p` for each step) against a scratch repo, with a stub
`open` first on `PATH` so nothing reaches Pete's screen. A `claude --plugin-dir` load writes
`tsconfig.json` and `.claude-plugin/types` into the plugin folder; delete them before
committing.
