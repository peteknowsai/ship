#!/usr/bin/env node
// A stand-in for `codex app-server` over stdio: enough of the JSON-RPC contract to drive
// dispatch.mjs end to end without codex, a login or a model. FAKE_SCENARIO picks the
// story; FAKE_TRACE names a file every incoming frame is appended to, so a test can
// assert what the client sent.
//
//   happy     two commands, a file change, a final message, turn/completed completed
//   failed    turn/completed with status failed and a codex error
//   stall     turn/started, then silence; a turn/interrupt is answered with interrupted
//   approval  asks for a command approval and a file-change approval, then completes
//   resume    thread/resume works and the turn completes
//   die       exits mid-turn
//   review    review/start runs a turn that ends with findings as the final message
//   other     interleaves another thread's notifications before completing
import { createInterface } from 'node:readline';
import { appendFileSync } from 'node:fs';

const scenario = process.env.FAKE_SCENARIO ?? 'happy';
const trace = process.env.FAKE_TRACE;
const send = (m) => process.stdout.write(`${JSON.stringify(m)}\n`);
let THREAD = 'thread-fake-1';
const TURN = 'turn-fake-1';
let nextServerId = 1;
const pendingServerRequests = new Map();

function item(type, extra) {
  return { threadId: THREAD, turnId: TURN, item: { id: `${type}-${Math.random().toString(36).slice(2, 6)}`, type, ...extra } };
}

function completeTurn(status, extra = {}) {
  send({ method: 'turn/completed', params: { threadId: THREAD, turn: { id: TURN, status, items: [], ...extra } } });
}

function finalMessage(text) {
  send({ method: 'item/completed', params: item('agentMessage', { text, phase: 'final_answer' }) });
}

function storyAfterTurnStart() {
  send({ method: 'turn/started', params: { threadId: THREAD, turn: { id: TURN, status: 'inProgress', items: [] } } });
  if (scenario === 'stall') return;
  if (scenario === 'die') {
    setTimeout(() => process.exit(9), 50);
    return;
  }
  if (scenario === 'failed') {
    completeTurn('failed', { error: { message: 'usage limit reached', codexErrorInfo: 'usageLimitExceeded' } });
    return;
  }
  if (scenario === 'approval') {
    const id = nextServerId++;
    pendingServerRequests.set(id, 'command');
    send({ id, method: 'item/commandExecution/requestApproval', params: { threadId: THREAD, turnId: TURN, itemId: 'cmd-1', command: ['rm', '-rf', 'dist'], cwd: process.cwd() } });
    return; // the rest of the story continues when the answer arrives
  }
  if (scenario === 'other') {
    send({ method: 'turn/started', params: { threadId: 'thread-memory', turn: { id: 'turn-m', status: 'inProgress', items: [] } } });
    send({ method: 'item/completed', params: { threadId: 'thread-memory', turnId: 'turn-m', item: { id: 'x', type: 'agentMessage', text: 'not yours' } } });
  }
  send({ method: 'item/started', params: item('commandExecution', { command: ['bun', 'test'], status: 'inProgress' }) });
  send({ method: 'item/commandExecution/outputDelta', params: { threadId: THREAD, turnId: TURN, itemId: 'c1', delta: '3 pass\n' } });
  send({ method: 'item/completed', params: item('commandExecution', { command: ['bun', 'test'], status: 'completed', exitCode: 0, aggregatedOutput: '3 pass', durationMs: 1200 }) });
  send({ method: 'item/completed', params: item('fileChange', { status: 'completed', changes: [{ path: 'src/a.ts', kind: { type: 'update' } }] }) });
  send({ method: 'item/agentMessage/delta', params: { threadId: THREAD, turnId: TURN, itemId: 'm1', delta: 'Done' } });
  send({ method: 'thread/tokenUsage/updated', params: { threadId: THREAD, tokenUsage: { total: { totalTokens: 1234 } } } });
  finalMessage(scenario === 'review' ? 'Findings:\n1. none' : 'Done: changed src/a.ts and the tests pass.');
  completeTurn('completed');
}

const rl = createInterface({ input: process.stdin });
rl.on('line', (line) => {
  if (!line.trim()) return;
  if (trace) appendFileSync(trace, `${line}\n`);
  const msg = JSON.parse(line);
  if (msg.method === 'initialize') return send({ id: msg.id, result: { userAgent: 'fake/0.0.0' } });
  if (msg.method === 'initialized') return;
  if (msg.method === 'thread/start') {
    return send({ id: msg.id, result: { thread: { id: THREAD }, model: msg.params?.model, reasoningEffort: 'high' } });
  }
  if (msg.method === 'thread/resume') {
    if (scenario !== 'resume') return send({ id: msg.id, error: { code: -32000, message: `thread ${msg.params?.threadId} not found` } });
    THREAD = msg.params.threadId; // the resumed thread is the one every later event names
    return send({ id: msg.id, result: { thread: { id: THREAD }, model: msg.params?.model } });
  }
  if (msg.method === 'turn/start' || msg.method === 'review/start') {
    send({ id: msg.id, result: { turn: { id: TURN, status: 'inProgress', items: [] } } });
    setTimeout(storyAfterTurnStart, 10);
    return;
  }
  if (msg.method === 'turn/interrupt') {
    send({ id: msg.id, result: {} });
    setTimeout(() => completeTurn('interrupted'), 10);
    return;
  }
  if (msg.method == null && msg.id != null && pendingServerRequests.has(msg.id)) {
    const kind = pendingServerRequests.get(msg.id);
    pendingServerRequests.delete(msg.id);
    if (kind === 'command') {
      const id = nextServerId++;
      pendingServerRequests.set(id, 'file');
      send({ id, method: 'item/fileChange/requestApproval', params: { threadId: THREAD, turnId: TURN, itemId: 'fc-1', grantRoot: '/etc' } });
      return;
    }
    if (kind === 'file') {
      finalMessage(`approvals: ${JSON.stringify(msg)}`);
      completeTurn('completed');
    }
    return;
  }
  if (msg.id != null) send({ id: msg.id, error: { code: -32601, message: `fake: no ${msg.method}` } });
});
rl.on('close', () => process.exit(0));
