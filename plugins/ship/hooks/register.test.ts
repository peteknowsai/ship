import { expect, mock, test } from 'claude-code/testing'
import type { Engine } from 'claude-code/testing'
import type { On } from 'claude-code'

const WT = '/wt/ship'
const STAGE = `${WT}/.ship-stage`
const BAND = {
  plugin: 'ship',
  component: 'AbovePrompt',
  props: { hasSurvey: false, isWorking: false, maxRows: 10, bodyColumns: 80, scroll: { offset: 0, bodyRows: 10 }, view: {} },
} as const

// The files, git and Chrome beneath the mod: `files` is the disk (tests change it as they
// go), `mtime` each file's age, `drop` makes every submitted prompt come back dropped.
function world(on: On, files: Record<string, string>, opts: { mtime?: Record<string, number>; drop?: boolean } = {}) {
  const opened: string[][] = []
  const submitted: string[] = []
  const toasts: string[] = []
  const clock = mock.clock(on)
  mock.env(on, { HOME: '/home' })
  on('session.start', (_, e) => ({ cwd: e.cwd }))
  on('session.id', () => ({ value: 'sid' }))
  on('session.cwd', () => ({ value: WT }))
  on('fs.exists', (_, e) => ({ value: e.path in files }))
  on('fs.read', (_, e) => ({ value: files[e.path] ?? '' }))
  on('fs.stat', (_, e) => ({ value: { kind: 'file', size: 1, mtimeMs: opts.mtime?.[e.path] ?? 0, isLink: false } }))
  on('process.run', (_, e) => {
    if (e.argv[0] === 'open') opened.push([...e.argv])
    const stdout = e.argv.includes('--show-toplevel') ? WT : e.argv.includes('--show-current') ? 'feature/demo' : ''
    return { value: { exitCode: 0, stdout: stdout + '\n', stderr: '', isStdoutTruncated: false, isStderrTruncated: false } }
  })
  on('prompt.submit', (_, e) => {
    submitted.push(e.text)
    return opts.drop ? { drop: 'removed from the queue' } : { text: e.text }
  })
  on('ui.toast', (_, e) => {
    toasts.push(e.text)
    return { value: undefined }
  })
  // Stand for the engine: its own band when the mod passes it on, and the events it ends.
  on('ui.render', ($, e) => $.ui.resolve(e).Text({ children: ['engine'] }))
  on('turn.complete', () => ({ text: '' }))
  on('classic.SessionStart', () => ({}))
  return { opened, submitted, toasts, clock }
}

const start = ($: Engine) => $.session.start({ cwd: WT, surface: 'terminal', isInteractive: true })
const band = ($: Engine) => $.ui.mount({ ...BAND, surface: 'terminal' })
const buttons = async (ui: Awaited<ReturnType<typeof band>>) => (await ui.findAll({ type: 'Button' })).length
const turnEnds = ($: Engine) =>
  $.turn.complete({ answer: '', durationMs: 1, isAborted: false, turnId: 't1', reason: 'answer' })

test('the storyboard gate shows both buttons on terminal and desktop', async ($, on) => {
  world(on, { [STAGE]: 'gate:1' })
  await start($)
  for (const surface of ['terminal', 'desktop'] as const) {
    const ui = await $.ui.mount({ ...BAND, surface })
    expect((await ui.find({ type: 'Text', text: /demo/ }))?.text).toBe('✋ demo')
    expect(await ui.findAll({ type: 'Button' })).toHaveLength(2)
    await ui.unmount()
  }
})

test('1 raises the recorded page, 2 locks it once, and the band waits for that turn', async ($, on) => {
  const w = world(on, {
    [STAGE]: 'gate:1',
    [`${WT}/.ship-shown/storyboard`]: 'file:///wt/ship/specs/designs/sb.html#ship=ship/demo/storyboard\n',
  })
  await start($)
  const ui = await band($)
  await ui.press({ key: 'ship-show' })
  expect(w.opened).toEqual([['open', '-a', 'Google Chrome', 'file:///wt/ship/specs/designs/sb.html#ship=ship/demo/storyboard&raise']])
  await Promise.allSettled([ui.press({ key: 'ship-answer' }), ui.press({ key: 'ship-answer' })])
  expect(w.submitted).toEqual(['lock it'])
  expect(await buttons(ui)).toBe(0)
  // The answer's turn ends with the marker unmoved: the gate shows again.
  await turnEnds($)
  expect(await buttons(ui)).toBe(2)
  await ui.unmount()
})

test('/clear brings back a band hidden by an answer', async ($, on) => {
  world(on, { [STAGE]: 'gate:1' })
  await start($)
  const ui = await band($)
  await ui.press({ key: 'ship-answer' })
  expect(await buttons(ui)).toBe(0)
  await $.classic.SessionStart({ source: 'clear' })
  expect(await buttons(ui)).toBe(2)
  await ui.unmount()
})

test('a dropped answer brings the band straight back', async ($, on) => {
  const w = world(on, { [STAGE]: 'gate:2' }, { drop: true })
  await start($)
  const ui = await band($)
  await ui.press({ key: 'ship-answer' })
  expect(w.submitted).toEqual(['go'])
  expect(await buttons(ui)).toBe(2)
  await ui.unmount()
})

test('the band follows the marker on the timer', async ($, on) => {
  const files: Record<string, string> = { [STAGE]: 'build:2:5' }
  const w = world(on, files)
  await start($)
  const ui = await band($)
  expect(await buttons(ui)).toBe(0)
  files[STAGE] = 'gate:2'
  await w.clock.advance(2000)
  expect(await buttons(ui)).toBe(2)
  files[STAGE] = 'plan'
  await w.clock.advance(2000)
  expect(await buttons(ui)).toBe(0)
  await ui.unmount()
})

test('the plan gate answers go, read from a Codex stage: line', async ($, on) => {
  const w = world(on, { [STAGE]: 'owner: codex\nstage:\tGATE:2\n' })
  await start($)
  const ui = await band($)
  expect((await ui.find({ key: 'ship-show' }))?.text).toContain('show plan card')
  await ui.press({ key: 'ship-answer' })
  expect(w.submitted).toEqual(['go'])
  await ui.unmount()
})

test('a page never shown, or recorded blank, toasts and opens nothing', async ($, on) => {
  const w = world(on, { [STAGE]: 'gate:2' })
  await start($)
  const ui = await band($)
  await ui.press({ key: 'ship-show' })
  expect(w.toasts).toEqual(['no plan opened yet'])
  expect(w.opened).toEqual([])
  await ui.unmount()
})

test('the try-it gate has only the app button, and opens the newer of preview and localhost', async ($, on) => {
  const preview = `${WT}/.ship-shown/preview`
  const local = `${WT}/.ship-shown/test`
  const w = world(
    on,
    {
      [STAGE]: 'gate:test',
      [preview]: 'https://demo.vercel.app#ship=ship/demo/preview',
      [local]: 'http://localhost:3000#ship=ship/demo/test',
      [`${WT}/.ship-shown/plan`]: '',
    },
    // The newer one is checked first, so taking the last one read would fail here.
    { mtime: { [preview]: 9, [local]: 5 } },
  )
  await start($)
  const ui = await band($)
  expect(await buttons(ui)).toBe(1)
  await ui.press({ key: 'ship-show' })
  expect(w.opened[0]?.[3]).toBe('https://demo.vercel.app#ship=ship/demo/preview&raise')
  await ui.unmount()
})

test('the ship-active pointer wins over the session folder', async ($, on) => {
  const other = '/wt/other-repo'
  world(on, {
    '/home/.claude/ship-active/sid': `${other}\n`,
    [`${other}/.ship-stage`]: 'gate:1',
    [STAGE]: 'build:2:5',
  })
  await start($)
  const ui = await band($)
  expect(await buttons(ui)).toBe(2)
  await ui.unmount()
})

for (const [name, stage] of [['no gate', 'build:2:5'], ['the Codex hand-off', 'gate:codex']] as const) {
  test(`${name} draws nothing`, async ($, on) => {
    world(on, { [STAGE]: stage })
    await start($)
    const ui = await band($)
    expect(await buttons(ui)).toBe(0)
    await ui.unmount()
  })
}

test('a running turn hides the buttons', async ($, on) => {
  world(on, { [STAGE]: 'gate:1' })
  await start($)
  const ui = await $.ui.mount({ ...BAND, surface: 'terminal', props: { ...BAND.props, isWorking: true } })
  expect(await buttons(ui)).toBe(0)
  await ui.unmount()
})
