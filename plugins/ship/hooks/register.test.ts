import { expect, mock, test } from 'claude-code/testing'
import type { Engine } from 'claude-code/testing'
import type { On } from 'claude-code'

const WT = '/wt/ship'
const BAND = {
  plugin: 'ship',
  component: 'AbovePrompt',
  props: { hasSurvey: false, isWorking: false, maxRows: 10, bodyColumns: 80, scroll: { offset: 0, bodyRows: 10 }, view: {} },
} as const

// The files, git and Chrome beneath the mod: `files` is the disk, `mtime` each file's age.
function world(on: On, files: Record<string, string>, mtime: Record<string, number> = {}) {
  const opened: string[][] = []
  const submitted: string[] = []
  const toasts: string[] = []
  mock.env(on, { HOME: '/home' })
  on('session.start', (_, e) => ({ cwd: e.cwd }))
  on('clock.every', () => ({ value: undefined }))
  on('session.id', () => ({ value: 'sid' }))
  on('session.cwd', () => ({ value: WT }))
  on('fs.exists', (_, e) => ({ value: e.path in files }))
  on('fs.read', (_, e) => ({ value: files[e.path] ?? '' }))
  on('fs.stat', (_, e) => ({ value: { kind: 'file', size: 1, mtimeMs: mtime[e.path] ?? 0, isLink: false } }))
  on('process.run', (_, e) => {
    if (e.argv[0] === 'open') opened.push([...e.argv])
    const stdout = e.argv.includes('--show-toplevel') ? WT : e.argv.includes('--show-current') ? 'feature/demo' : ''
    return { value: { exitCode: 0, stdout: stdout + '\n', stderr: '', isStdoutTruncated: false, isStderrTruncated: false } }
  })
  on('prompt.submit', (_, e) => {
    submitted.push(e.text)
    return { text: e.text }
  })
  on('ui.toast', (_, e) => {
    toasts.push(e.text)
    return { value: undefined }
  })
  // Stands for the engine's own band when the mod passes it on.
  on('ui.render', ($, e) => $.ui.resolve(e).Text({ children: ['engine'] }))
  return { opened, submitted, toasts }
}

const start = ($: Engine) =>
  $.session.start({ cwd: WT, surface: 'terminal', isInteractive: true })

test('the storyboard gate shows both buttons, and 2 locks it once', async ($, on) => {
  const w = world(on, {
    [`${WT}/.ship-stage`]: 'gate:1',
    [`${WT}/.ship-shown/storyboard`]: 'file:///wt/ship/specs/designs/sb.html#ship=ship/demo/storyboard\n',
  })
  await start($)
  for (const surface of ['terminal', 'desktop'] as const) {
    const ui = await $.ui.mount({ ...BAND, surface })
    expect((await ui.find({ type: 'Text', text: /demo/ }))?.text).toBe('✋ demo')
    expect(await ui.findAll({ type: 'Button' })).toHaveLength(2)
    await ui.unmount()
  }
  const ui = await $.ui.mount({ ...BAND, surface: 'terminal' })
  await ui.press({ key: 'ship-show' })
  expect(w.opened).toEqual([['open', '-a', 'Google Chrome', 'file:///wt/ship/specs/designs/sb.html#ship=ship/demo/storyboard']])
  await ui.press({ key: 'ship-answer' })
  expect(w.submitted).toEqual(['lock it'])
  // Answered: the band hides until the turn it started ends.
  expect(await ui.findAll({ type: 'Button' })).toHaveLength(0)
  await ui.unmount()
})

test('the plan gate answers go, read from a Codex stage: line', async ($, on) => {
  const w = world(on, { [`${WT}/.ship-stage`]: 'owner: codex\nstage: GATE:2\n' })
  await start($)
  const ui = await $.ui.mount({ ...BAND, surface: 'terminal' })
  expect((await ui.find({ key: 'ship-show' }))?.text).toContain('show plan card')
  await ui.press({ key: 'ship-answer' })
  expect(w.submitted).toEqual(['go'])
  await ui.unmount()
})

test('a page never shown toasts and opens nothing', async ($, on) => {
  const w = world(on, { [`${WT}/.ship-stage`]: 'gate:2' })
  await start($)
  const ui = await $.ui.mount({ ...BAND, surface: 'terminal' })
  await ui.press({ key: 'ship-show' })
  expect(w.toasts).toEqual(['no plan opened yet'])
  expect(w.opened).toEqual([])
  await ui.unmount()
})

test('the try-it gate has only the app button, and opens the newer of preview and localhost', async ($, on) => {
  const w = world(
    on,
    {
      [`${WT}/.ship-stage`]: 'gate:test',
      [`${WT}/.ship-shown/preview`]: 'https://demo.vercel.app#ship=ship/demo/preview',
      [`${WT}/.ship-shown/test`]: 'http://localhost:3000#ship=ship/demo/test',
    },
    { [`${WT}/.ship-shown/preview`]: 5, [`${WT}/.ship-shown/test`]: 9 },
  )
  await start($)
  const ui = await $.ui.mount({ ...BAND, surface: 'terminal' })
  expect(await ui.findAll({ type: 'Button' })).toHaveLength(1)
  await ui.press({ key: 'ship-show' })
  expect(w.opened[0]?.[3]).toBe('http://localhost:3000#ship=ship/demo/test')
  await ui.unmount()
})

test('the ship-active pointer wins over the session folder', async ($, on) => {
  const other = '/wt/other-repo'
  world(on, {
    '/home/.claude/ship-active/sid': `${other}\n`,
    [`${other}/.ship-stage`]: 'gate:1',
    [`${WT}/.ship-stage`]: 'build:2:5',
  })
  await start($)
  const ui = await $.ui.mount({ ...BAND, surface: 'terminal' })
  expect(await ui.findAll({ type: 'Button' })).toHaveLength(2)
  await ui.unmount()
})

for (const [name, stage] of [['no gate', 'build:2:5'], ['the Codex hand-off', 'gate:codex']] as const) {
  test(`${name} draws nothing`, async ($, on) => {
    world(on, { [`${WT}/.ship-stage`]: stage })
    await start($)
    const ui = await $.ui.mount({ ...BAND, surface: 'terminal' })
    expect(await ui.findAll({ type: 'Button' })).toHaveLength(0)
    await ui.unmount()
  })
}

test('a running turn hides the buttons', async ($, on) => {
  world(on, { [`${WT}/.ship-stage`]: 'gate:1' })
  await start($)
  const ui = await $.ui.mount({ ...BAND, surface: 'terminal', props: { ...BAND.props, isWorking: true } })
  expect(await ui.findAll({ type: 'Button' })).toHaveLength(0)
  await ui.unmount()
})
