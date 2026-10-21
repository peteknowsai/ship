// Gate buttons: while this session's ship is parked at a gate, the band above the prompt
// offers `1` to bring the page Pete answers forward and `2` to answer it. A bare digit in
// an empty prompt presses a band button, and a click does too. "merge main" stays typed.
import type { EngineInterface, Register } from 'claude-code'

type Kind = 'storyboard' | 'plan' | 'test'
type Gate = { kind: Kind; stage: string; root: string; slug: string }

const SHOW: Record<Kind, string> = { storyboard: 'show storyboard', plan: 'show plan card', test: 'open the app' }
const ANSWER: Partial<Record<Kind, string>> = { storyboard: 'lock it', plan: 'go' }

let gate: Gate | null = null
// Hides the band between a press and the turn it starts, so a second `2` can't answer twice.
let answered = false
// The git top of the session's cwd, read again only when the cwd moves.
let top: { cwd: string; dir: string | null } | null = null
// One look at a time: a slow git must not let an older tick land last with a stale gate.
let looking = false

// Same reading as statusline.sh: a Codex `stage:` line wins, else the first line.
function parseStage(text: string): string {
  const lines = text.split('\n')
  const keyed = lines.find(l => l.startsWith('stage:'))?.replace(/^stage:\s*/, '')
  return (keyed || lines[0] || '').replace(/[ \n]/g, '').toLowerCase()
}

function kindOf(stage: string): Kind | null {
  if (stage.startsWith('gate:1')) return 'storyboard'
  if (stage.startsWith('gate:2')) return 'plan'
  if (stage.startsWith('gate:test')) return 'test'
  return null
}

// Same order as statusline.sh: this session's ship-active pointer, else the cwd's git top.
async function shipRoot($: EngineInterface): Promise<string | null> {
  const ptr = `${await $.env.get('HOME')}/.claude/ship-active/${await $.session.id()}`
  if (await $.fs.exists(ptr)) {
    const wt = (await $.fs.read(ptr)).split('\n')[0]?.trim()
    if (wt && (await $.fs.exists(`${wt}/.ship-stage`))) return wt
  }
  const cwd = await $.session.cwd()
  if (top?.cwd !== cwd) {
    const r = await $.process.run(['git', '-C', cwd, 'rev-parse', '--show-toplevel'])
    top = { cwd, dir: r.exitCode === 0 ? r.stdout.trim() : null }
  }
  return top.dir
}

async function readGate($: EngineInterface): Promise<Gate | null> {
  const root = await shipRoot($)
  if (!root || !(await $.fs.exists(`${root}/.ship-stage`))) return null
  const stage = parseStage(await $.fs.read(`${root}/.ship-stage`))
  const kind = kindOf(stage)
  if (!kind) return null
  let slug = gate?.root === root ? gate.slug : ''
  if (!slug) {
    const r = await $.process.run(['git', '-C', root, 'branch', '--show-current'])
    const branch = r.exitCode === 0 ? r.stdout.trim() : ''
    slug = branch ? branch.replace(/^[^/]*\//, '') : root.split('/').pop() ?? 'ship'
  }
  return { kind, stage, root, slug }
}

async function refresh($: EngineInterface) {
  if (looking) return
  looking = true
  let found: Gate | null = null
  try {
    found = await readGate($)
  } catch {
    // An unreadable marker or a git that won't start reads as no gate.
  } finally {
    looking = false
  }
  if (found?.root === gate?.root && found?.stage === gate?.stage) return
  gate = found
  answered = false
  $.ui.invalidate('ui.render')
}

// Brings the page forward without -g: Pete pressed it, so Chrome coming up is the point.
// The URL keeps show.sh's #ship= tag, so ship-tabs replaces the old tab, and `raise`
// tells it to leave this one in front rather than hand back the tab he was on.
async function show($: EngineInterface, g: Gate) {
  let best: { url: string; at: number } | null = null
  for (const kind of g.kind === 'test' ? ['preview', 'test'] : [g.kind]) {
    const file = `${g.root}/.ship-shown/${kind}`
    if (!(await $.fs.exists(file))) continue
    const url = (await $.fs.read(file)).trim()
    const at = (await $.fs.stat(file)).mtimeMs
    if (url && (!best || at > best.at)) best = { url, at }
  }
  if (!best) {
    $.ui.toast(`no ${g.kind === 'test' ? 'app' : g.kind} opened yet`)
    return
  }
  await $.process.run(['open', '-a', 'Google Chrome', `${best.url}&raise`])
}

function reopen($: EngineInterface) {
  answered = false
  $.ui.invalidate('ui.render')
}

function answer($: EngineInterface, text: string) {
  if (answered) return
  answered = true
  $.ui.invalidate('ui.render')
  $.prompt.submit({ text, asUser: true }).then(
    r => {
      if (r?.drop !== undefined) reopen($)
    },
    () => reopen($),
  )
}

export const register: Register = on => {
  on('session.start', async ($, e, next) => {
    // Nothing draws in `-p` or the SDK, so nothing to poll for.
    if (e.isInteractive) {
      await refresh($)
      $.clock.every(2000, () => refresh($))
    }
    return next(e)
  })

  // The answer's turn ended, or was stopped: show the gate again if it still stands.
  on('turn.complete', async ($, e, next) => {
    const result = await next(e)
    if (e.agentId === undefined) {
      reopen($)
      await refresh($)
    }
    return result
  })

  // /clear, /resume and /branch start no turn and no session.start.
  on('classic.SessionStart', { source: ['clear', 'resume', 'fork'] }, async ($, e, next) => {
    reopen($)
    return next(e)
  })

  on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
    const g = gate
    if (!g || answered || e.props.hasSurvey || e.props.isWorking) return next(e)
    const { Box, Text, Button } = $.ui.resolve(e)
    const reply = ANSWER[g.kind]
    return Box({
      flexDirection: 'row',
      columnGap: 2,
      children: [
        Text({ color: 'warning', weight: 'semibold', children: [`✋ ${g.slug}`] }),
        Button({ key: 'ship-show', label: SHOW[g.kind], hotkey: '1', plain: true, onPress: () => show($, g) }),
        ...(reply
          ? [Button({ key: 'ship-answer', label: reply, hotkey: '2', plain: true, onPress: () => answer($, reply) })]
          : []),
      ],
    })
  })
}
