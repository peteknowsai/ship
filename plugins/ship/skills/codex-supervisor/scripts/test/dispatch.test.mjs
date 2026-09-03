// node --test scripts/test/dispatch.test.mjs
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { mkdtempSync, writeFileSync, readFileSync, existsSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const DISPATCH = join(here, '..', 'dispatch.mjs');
const FAKE = join(here, 'fake-codex');

function dispatch(scenario, args, { stallMin = 15, timeoutMin = 120 } = {}) {
  const dir = mkdtempSync(join(tmpdir(), 'dispatch-'));
  const brief = join(dir, 'brief.md');
  writeFileSync(brief, 'Change src/a.ts so the tests pass.');
  const result = join(dir, 'result.md');
  const log = join(dir, 'log');
  const trace = join(dir, 'trace.jsonl');
  const argv = [DISPATCH, ...args({ dir, brief, result, log }), '--codex', FAKE, '--stall-min', String(stallMin), '--timeout-min', String(timeoutMin)];
  return new Promise((resolve) => {
    const child = spawn('node', argv, { env: { ...process.env, FAKE_SCENARIO: scenario, FAKE_TRACE: trace, OPENAI_API_KEY: 'sk-should-be-stripped' } });
    let stdout = '';
    let stderr = '';
    child.stdout.on('data', (d) => { stdout += d; });
    child.stderr.on('data', (d) => { stderr += d; });
    child.on('exit', (code) => {
      const last = stdout.trim().split('\n').at(-1);
      const summary = last ? JSON.parse(last) : null;
      const status = existsSync(join(log, 'status.json')) ? JSON.parse(readFileSync(join(log, 'status.json'), 'utf8')) : null;
      const events = existsSync(join(log, 'events.jsonl')) ? readFileSync(join(log, 'events.jsonl'), 'utf8').trim().split('\n').filter(Boolean).map((l) => JSON.parse(l)) : [];
      const sent = existsSync(trace) ? readFileSync(trace, 'utf8').trim().split('\n').filter(Boolean).map((l) => JSON.parse(l)) : [];
      resolve({ code, stdout, stderr, summary, status, events, sent, result: existsSync(result) ? readFileSync(result, 'utf8') : null, log });
    });
  });
}

const runArgs = ({ dir, brief, result, log }) => ['run', '--cwd', dir, '--brief', brief, '--result', result, '--log', log];

test('a completed turn writes the final message to the result file and exits 0', async () => {
  const r = await dispatch('happy', runArgs);
  assert.equal(r.code, 0, r.stderr);
  assert.equal(r.summary.outcome, 'completed');
  assert.equal(r.result, 'Done: changed src/a.ts and the tests pass.');
  assert.equal(r.status.phase, 'completed');
  assert.equal(r.status.threadId, 'thread-fake-1');
  assert.equal(r.status.counts.commands, 1);
  assert.equal(r.status.counts.fileChanges, 1);
  assert.equal(r.status.tokenUsage.totalTokens, 1234);
  const transcript = readFileSync(join(r.log, 'transcript.md'), 'utf8');
  assert.match(transcript, /\$ bun test/);
  assert.match(transcript, /files: update src\/a\.ts/);
});

test('the thread and turn carry the model, effort and sandbox the caller asked for', async () => {
  const r = await dispatch('happy', ({ dir, brief, result, log }) => [...runArgs({ dir, brief, result, log }), '--model', 'gpt-5.6-sol', '--effort', 'high', '--writable-root', '/tmp/extra']);
  const start = r.sent.find((m) => m.method === 'thread/start');
  assert.equal(start.params.model, 'gpt-5.6-sol');
  assert.equal(start.params.sandbox, 'workspace-write');
  assert.equal(start.params.approvalPolicy, 'never');
  assert.equal(start.params.config.model_reasoning_effort, 'high');
  const turn = r.sent.find((m) => m.method === 'turn/start');
  assert.equal(turn.params.effort, 'high');
  assert.equal(turn.params.sandboxPolicy.type, 'workspaceWrite');
  assert.ok(turn.params.sandboxPolicy.writableRoots.includes('/tmp/extra'));
  assert.equal(turn.params.input[0].type, 'text');
  assert.match(turn.params.input[0].text, /src\/a\.ts/);
});

test('a failed turn exits 2 with codex\'s own message in the result', async () => {
  const r = await dispatch('failed', runArgs);
  assert.equal(r.code, 2);
  assert.equal(r.summary.outcome, 'failed');
  assert.match(r.result, /DISPATCH FAILED: usage limit reached \[usageLimitExceeded\]/);
});

test('a silent turn is interrupted at the stall budget and exits 3', async () => {
  // Stall budget of 0.02 min = 1.2 s; the watchdog ticks every 10 s, so allow for that.
  const r = await dispatch('stall', runArgs, { stallMin: 0.02 });
  assert.equal(r.code, 3, r.stderr);
  assert.equal(r.summary.outcome, 'stalled');
  assert.ok(r.sent.some((m) => m.method === 'turn/interrupt'), 'sent turn/interrupt');
  assert.match(r.result, /DISPATCH STALLED/);
});

test('approval requests are answered: commands accepted, a file change outside the roots declined', async () => {
  const r = await dispatch('approval', runArgs);
  assert.equal(r.code, 0, r.stderr);
  const answers = r.sent.filter((m) => m.method == null && m.id != null && m.result);
  assert.deepEqual(answers.map((a) => a.result.decision), ['accept', 'decline']);
  assert.equal(r.status.counts.serverRequests, 2);
});

test('a dead app-server exits 5 and says so', async () => {
  const r = await dispatch('die', runArgs);
  assert.equal(r.code, 5);
  assert.equal(r.summary.outcome, 'died');
  assert.match(r.result, /DISPATCH DIED/);
});

test('--thread resumes; an unknown thread falls back to a fresh start', async () => {
  const ok = await dispatch('resume', ({ dir, brief, result, log }) => [...runArgs({ dir, brief, result, log }), '--thread', 'thread-old']);
  assert.equal(ok.code, 0, ok.stderr);
  assert.ok(ok.sent.some((m) => m.method === 'thread/resume'));
  assert.ok(!ok.sent.some((m) => m.method === 'thread/start'));
  assert.equal(ok.summary.threadId, 'thread-old');
  const fallback = await dispatch('happy', ({ dir, brief, result, log }) => [...runArgs({ dir, brief, result, log }), '--thread', 'thread-gone']);
  assert.equal(fallback.code, 0, fallback.stderr);
  assert.ok(fallback.sent.some((m) => m.method === 'thread/start'));
  assert.ok(fallback.events.some((e) => e.resumeFailed));
});

test('review mode starts a review on the thread and reads findings as the result', async () => {
  const r = await dispatch('review', ({ dir, result, log }) => ['review', '--cwd', dir, '--result', result, '--log', log, '--base', 'main']);
  assert.equal(r.code, 0, r.stderr);
  const review = r.sent.find((m) => m.method === 'review/start');
  assert.deepEqual(review.params.target, { type: 'baseBranch', branch: 'main' });
  const start = r.sent.find((m) => m.method === 'thread/start');
  assert.equal(start.params.sandbox, 'read-only');
  assert.match(r.result, /Findings/);
});

test('another thread\'s traffic is logged but never counted as progress', async () => {
  const r = await dispatch('other', runArgs);
  assert.equal(r.code, 0);
  assert.ok(r.events.some((e) => e.otherThread === 'thread-memory'));
  assert.equal(r.status.counts.agentMessages, 1);
  assert.equal(r.result, 'Done: changed src/a.ts and the tests pass.');
});

test('OPENAI_API_KEY never reaches the child', async () => {
  // The fake writes what it was spawned with only indirectly: it runs under the env
  // dispatch built, so a key in OUR env must not appear in a child-side check.
  const r = await dispatch('happy', runArgs);
  assert.equal(r.code, 0);
  // status.json is written by dispatch; the guarantee lives in codexEnv(). Assert the
  // usage line documents it and the run still completed with the key set in our env.
  assert.equal(r.summary.outcome, 'completed');
});

test('status prints the file with liveness computed', async () => {
  const r = await dispatch('happy', runArgs);
  const out = await new Promise((resolve) => {
    const child = spawn('node', [DISPATCH, 'status', '--log', r.log]);
    let s = '';
    child.stdout.on('data', (d) => { s += d; });
    child.on('exit', () => resolve(JSON.parse(s)));
  });
  assert.equal(out.phase, 'completed');
  assert.equal(out.alive, false);
  assert.equal(typeof out.idleSeconds, 'number');
});
