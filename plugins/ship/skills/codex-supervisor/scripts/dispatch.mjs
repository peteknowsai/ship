#!/usr/bin/env node
// dispatch.mjs -- one codex coding task on `codex app-server`, watched.
//
// The supervisor used to launch `codex exec`, and an exec run that went dark (a held
// stdin, a startup error, a model that stopped calling tools) looked exactly like a slow
// one from outside. This script owns the app-server process instead and makes the run
// legible while it is running, not only after:
//
//   <log>/events.jsonl   every notification codex sent, with a clock
//   <log>/status.json    phase, thread id, turn id, last event and when, counts
//   <log>/transcript.md  agent messages, commands and file changes, in order
//   <log>/stderr.log     app-server's stderr, whole
//   <result>             the final agent message (or the failure), written last
//
// It exits with a code that says what happened: 0 completed, 2 the turn failed, 3 the
// turn stalled past --stall-min and was interrupted, 4 the hard --timeout-min cap, 5
// app-server died or could not start, 6 usage. The last line on stdout is one JSON
// object with the same facts, for a caller that reads output rather than files.
//
//   dispatch.mjs run    --cwd DIR --brief FILE --result FILE --log DIR [options]
//   dispatch.mjs review --cwd DIR --result FILE --log DIR (--base REF | --uncommitted | --commit SHA)
//   dispatch.mjs status --log DIR
//
// Options: --model (gpt-5.6-sol) --effort (high) --sandbox (workspace-write)
//   --writable-root DIR (repeatable; the git common dir of a linked worktree is added
//   for you) --thread ID (resume a thread for a fix round) --stall-min N (15)
//   --timeout-min N (120) --tag TEXT --codex BIN --allow-api-key
import { existsSync, mkdirSync, readFileSync, writeFileSync, appendFileSync, statSync } from 'node:fs';
import { execFileSync } from 'node:child_process';
import { resolve, join, isAbsolute } from 'node:path';
import { AppServerClient } from './appServerClient.mjs';

const EXIT = { completed: 0, failed: 2, stalled: 3, timedOut: 4, died: 5, usage: 6 };

function usage(message) {
  if (message) console.error(`dispatch: ${message}`);
  console.error('usage: dispatch.mjs run|review|status ... (see the header of this file)');
  process.exit(EXIT.usage);
}

function parseArgs(argv) {
  const out = { writableRoots: [] };
  const mode = argv[0];
  for (let i = 1; i < argv.length; i += 1) {
    const flag = argv[i];
    const next = () => {
      i += 1;
      if (i >= argv.length) usage(`${flag} needs a value`);
      return argv[i];
    };
    switch (flag) {
      case '--cwd': out.cwd = resolve(next()); break;
      case '--brief': out.brief = next(); break;
      case '--result': out.result = resolve(next()); break;
      case '--log': out.log = resolve(next()); break;
      case '--model': out.model = next(); break;
      case '--effort': out.effort = next(); break;
      case '--sandbox': out.sandbox = next(); break;
      case '--writable-root': out.writableRoots.push(resolve(next())); break;
      case '--thread': out.thread = next(); break;
      case '--stall-min': out.stallMin = Number(next()); break;
      case '--timeout-min': out.timeoutMin = Number(next()); break;
      case '--tag': out.tag = next(); break;
      case '--codex': out.codex = next(); break;
      case '--base': out.reviewTarget = { type: 'baseBranch', branch: next() }; break;
      case '--commit': out.reviewTarget = { type: 'commit', sha: next() }; break;
      case '--uncommitted': out.reviewTarget = { type: 'uncommittedChanges' }; break;
      case '--allow-api-key': out.allowApiKey = true; break;
      default: usage(`unknown flag ${flag}`);
    }
  }
  return { mode, ...out };
}

const now = () => new Date().toISOString();
const clip = (text, n = 400) => (typeof text === 'string' && text.length > n ? `${text.slice(0, n)}…` : text);

/** The env codex runs under. An OPENAI_API_KEY in the environment silently bills per
 *  call instead of the ChatGPT subscription; the supervisor's billing rule says it must
 *  never reach a dispatch. */
function codexEnv(allowApiKey) {
  const env = { ...process.env };
  if (!allowApiKey) {
    delete env.OPENAI_API_KEY;
    delete env.OPENAI_BASE_URL;
  }
  return env;
}

/** A linked worktree's index lives under the primary repo's `.git`, outside the sandbox
 *  root, so a worker that tries to `git add` there is refused. Add the common dir. */
function gitCommonDir(cwd) {
  try {
    const dir = execFileSync('git', ['rev-parse', '--git-common-dir'], { cwd, encoding: 'utf8' }).trim();
    return isAbsolute(dir) ? dir : resolve(cwd, dir);
  } catch {
    return undefined;
  }
}

function within(path, roots) {
  const p = resolve(path);
  return roots.some((root) => p === root || p.startsWith(`${root}/`));
}

class Run {
  constructor(opts) {
    this.opts = opts;
    this.startedAt = Date.now();
    this.lastEventAt = this.startedAt;
    this.lastEvent = 'starting';
    this.phase = 'starting';
    this.counts = { items: 0, commands: 0, fileChanges: 0, agentMessages: 0, serverRequests: 0, warnings: 0 };
    this.lastCommand = undefined;
    this.agentMessages = [];
    this.tokenUsage = undefined;
    this.threadId = opts.thread;
    this.turnId = undefined;
    this.interrupting = false;
    this.done = false;
    mkdirSync(opts.log, { recursive: true });
    this.events = join(opts.log, 'events.jsonl');
    this.transcript = join(opts.log, 'transcript.md');
    this.stderrLog = join(opts.log, 'stderr.log');
    this.statusFile = join(opts.log, 'status.json');
    writeFileSync(this.events, '');
    writeFileSync(this.transcript, `# dispatch ${opts.tag ?? ''}\n\n`);
    writeFileSync(this.stderrLog, '');
    this.client = new AppServerClient({
      bin: opts.codex ?? process.env.CODEX_BIN ?? 'codex',
      cwd: opts.cwd,
      env: codexEnv(opts.allowApiKey),
      requestTimeoutMs: 120_000,
      onNotification: (event) => this.onNotification(event),
      onServerRequest: (request) => this.onServerRequest(request),
      onStderr: (chunk) => appendFileSync(this.stderrLog, chunk),
    });
    this.writeStatus(true);
  }

  log(record) {
    appendFileSync(this.events, `${JSON.stringify({ t: now(), ...record })}\n`);
  }

  note(text) {
    appendFileSync(this.transcript, `${text}\n\n`);
  }

  writeStatus(force = false) {
    const at = Date.now();
    if (!force && this.statusWrittenAt && at - this.statusWrittenAt < 500) return;
    this.statusWrittenAt = at;
    const status = {
      phase: this.phase,
      mode: this.opts.mode,
      tag: this.opts.tag,
      pid: this.client.pid ?? null,
      threadId: this.threadId ?? null,
      turnId: this.turnId ?? null,
      model: this.opts.model,
      effort: this.opts.effort,
      cwd: this.opts.cwd,
      startedAt: new Date(this.startedAt).toISOString(),
      updatedAt: new Date(at).toISOString(),
      lastEventAt: new Date(this.lastEventAt).toISOString(),
      lastEvent: this.lastEvent,
      idleSeconds: Math.round((at - this.lastEventAt) / 1000),
      elapsedSeconds: Math.round((at - this.startedAt) / 1000),
      stallBudgetSeconds: this.opts.stallMin * 60,
      counts: this.counts,
      lastCommand: this.lastCommand,
      lastAgentMessage: clip(this.agentMessages.at(-1), 200),
      tokenUsage: this.tokenUsage,
      result: this.opts.result,
      log: this.opts.log,
    };
    writeFileSync(this.statusFile, `${JSON.stringify(status, null, 2)}\n`);
  }

  touch(what) {
    this.lastEventAt = Date.now();
    this.lastEvent = what;
    this.writeStatus();
  }

  setPhase(phase) {
    if (this.phase === phase) return;
    this.phase = phase;
    console.error(`dispatch: ${phase}${this.threadId ? ` thread=${this.threadId}` : ''}`);
    this.writeStatus(true);
  }

  onNotification({ method, params }) {
    if (method === 'app-server/closed') {
      this.log({ method, ...params });
      if (!this.done) this.finish('died', `app-server closed: ${params.reason}`);
      return;
    }
    const theirs = params.threadId;
    const ours = this.threadId;
    // Other threads share the connection (memory consolidation, for one). Log them,
    // never let them count as this run's progress.
    if (theirs && ours && theirs !== ours) {
      this.log({ method, otherThread: theirs });
      return;
    }
    const isDelta = method.endsWith('/delta') || method.endsWith('Delta') || method.endsWith('/outputDelta');
    this.log(isDelta ? { method, delta: clip(params.delta, 120) } : { method, ...this.compact(params) });
    this.touch(method);
    switch (method) {
      case 'thread/started':
        if (!this.threadId && params.thread?.id) this.threadId = params.thread.id;
        break;
      case 'turn/started':
        this.turnId = params.turn?.id ?? this.turnId;
        this.setPhase('running');
        break;
      case 'item/started': {
        const item = params.item ?? {};
        if (item.type === 'commandExecution') {
          this.lastCommand = clip(Array.isArray(item.command) ? item.command.join(' ') : item.command, 200);
          this.note(`$ ${this.lastCommand}`);
        }
        break;
      }
      case 'item/completed':
        this.onItem(params.item ?? {});
        break;
      case 'thread/status/changed': {
        const flags = params.status?.activeFlags ?? [];
        if (flags.includes('waitingOnApproval') || flags.includes('waitingOnUserInput')) {
          // We answer every request, so this should clear at once; if it stays, the
          // stall watchdog will say so and the events log will show the request.
          this.setPhase('waiting-on-client');
        } else if (this.phase === 'waiting-on-client') this.setPhase('running');
        break;
      }
      case 'thread/tokenUsage/updated':
        this.tokenUsage = params.tokenUsage?.total ?? params.tokenUsage ?? this.tokenUsage;
        break;
      case 'error': {
        const message = params.error?.message ?? 'unknown error';
        this.counts.warnings += 1;
        this.note(`> error${params.willRetry ? ' (codex will retry)' : ''}: ${message}`);
        // A retried error is progress of a kind; a final one is followed by
        // turn/completed with status failed, which settles the run.
        break;
      }
      case 'warning':
      case 'configWarning':
      case 'deprecationNotice':
        this.counts.warnings += 1;
        break;
      case 'turn/completed':
        this.onTurnCompleted(params.turn ?? {});
        break;
      default:
        break;
    }
  }

  /** What of a notification's params goes in the events log. Items are logged whole
   *  minus their long fields; everything else as is. */
  compact(params) {
    const out = { ...params };
    if (out.item) {
      const item = { ...out.item };
      for (const key of ['aggregatedOutput', 'text', 'result', 'content', 'summary']) {
        if (key in item) item[key] = clip(item[key], 300);
      }
      if (Array.isArray(item.changes)) item.changes = item.changes.map((c) => ({ path: c.path, kind: c.kind?.type ?? c.kind }));
      out.item = item;
    }
    if (out.turn?.items) out.turn = { ...out.turn, items: `[${out.turn.items.length} items]` };
    return out;
  }

  onItem(item) {
    this.counts.items += 1;
    switch (item.type) {
      case 'agentMessage':
        this.counts.agentMessages += 1;
        if (typeof item.text === 'string') {
          this.agentMessages.push(item.text);
          this.note(item.text);
        }
        break;
      case 'commandExecution': {
        this.counts.commands += 1;
        const exit = item.exitCode == null ? item.status : `exit ${item.exitCode}`;
        this.note(`  (${exit}${item.durationMs ? `, ${Math.round(item.durationMs / 1000)}s` : ''})${item.aggregatedOutput ? `\n\`\`\`\n${clip(item.aggregatedOutput, 1500)}\n\`\`\`` : ''}`);
        break;
      }
      case 'fileChange': {
        this.counts.fileChanges += 1;
        const paths = (item.changes ?? []).map((c) => `${c.kind?.type ?? c.kind ?? 'change'} ${c.path}`);
        this.note(`* files: ${paths.join(', ') || '(none listed)'} (${item.status})`);
        break;
      }
      default:
        break;
    }
  }

  onServerRequest({ method, params }) {
    this.counts.serverRequests += 1;
    const roots = [this.opts.cwd, ...this.opts.writableRoots];
    let reply;
    switch (method) {
      case 'item/commandExecution/requestApproval':
        reply = { decision: 'accept' };
        break;
      case 'item/fileChange/requestApproval':
        reply = { decision: params.grantRoot && !within(params.grantRoot, roots) ? 'decline' : 'accept' };
        break;
      case 'execCommandApproval':
        reply = { decision: 'approved' };
        break;
      case 'applyPatchApproval':
        reply = { decision: params.grantRoot && !within(params.grantRoot, roots) ? 'denied' : 'approved' };
        break;
      case 'item/tool/requestUserInput':
        // No human here. Empty answers let codex continue without one.
        reply = { answers: {} };
        break;
      default:
        reply = undefined; // -> method not found, which codex treats as a decline
    }
    this.log({ serverRequest: method, params: this.compact(params), reply: reply ?? 'method-not-found' });
    this.note(`> codex asked ${method}; answered ${JSON.stringify(reply ?? 'method-not-found')}`);
    this.touch(`request:${method}`);
    return reply;
  }

  onTurnCompleted(turn) {
    if (this.done) return;
    const status = turn.status;
    if (status === 'completed') return this.finish('completed');
    if (status === 'interrupted') return this.finish(this.interrupting === 'timeout' ? 'timedOut' : 'stalled', 'turn interrupted');
    const error = turn.error?.message ?? 'turn failed';
    const info = turn.error?.codexErrorInfo;
    return this.finish('failed', info ? `${error} [${typeof info === 'string' ? info : JSON.stringify(info)}]` : error);
  }

  async interrupt(reason) {
    if (this.interrupting) return;
    this.interrupting = reason;
    this.setPhase(reason === 'timeout' ? 'timing-out' : 'stalled');
    this.log({ interrupt: reason, idleSeconds: Math.round((Date.now() - this.lastEventAt) / 1000) });
    if (this.threadId && this.turnId) {
      try {
        await this.client.request('turn/interrupt', { threadId: this.threadId, turnId: this.turnId }, { timeoutMs: 15_000 });
      } catch (error) {
        this.log({ interruptFailed: error.message });
      }
    }
    // codex answers an interrupt with turn/completed { status: interrupted }; if that
    // never comes the run is settled here anyway.
    setTimeout(() => {
      if (!this.done) this.finish(reason === 'timeout' ? 'timedOut' : 'stalled', 'no turn/completed after interrupt');
    }, 20_000).unref?.();
  }

  watch() {
    this.watchdog = setInterval(() => {
      if (this.done) return;
      const at = Date.now();
      this.writeStatus(true);
      if (at - this.startedAt > this.opts.timeoutMin * 60_000) void this.interrupt('timeout');
      else if (at - this.lastEventAt > this.opts.stallMin * 60_000) void this.interrupt('stall');
    }, 10_000);
  }

  finalMessage() {
    return this.agentMessages.at(-1);
  }

  finish(outcome, detail) {
    if (this.done) return;
    this.done = true;
    clearInterval(this.watchdog);
    this.phase = outcome;
    const final = this.finalMessage();
    const body = outcome === 'completed'
      ? (final ?? '')
      : `DISPATCH ${outcome.toUpperCase()}: ${detail ?? ''}\n\n${final ? `Last agent message:\n\n${final}` : '(no agent message)'}\n\n${this.client.stderrTail ? `stderr tail:\n${this.client.stderrTail.slice(-2000)}` : ''}`;
    writeFileSync(this.opts.result, body);
    this.writeStatus(true);
    this.log({ outcome, detail: detail ?? null });
    const summary = {
      outcome,
      exitCode: EXIT[outcome],
      detail: detail ?? null,
      threadId: this.threadId ?? null,
      turnId: this.turnId ?? null,
      result: this.opts.result,
      log: this.opts.log,
      finalMessage: Boolean(final),
      durationSeconds: Math.round((Date.now() - this.startedAt) / 1000),
      counts: this.counts,
    };
    console.error(`dispatch: ${outcome}${detail ? ` (${detail})` : ''} -> ${this.opts.result}`);
    process.stdout.write(`${JSON.stringify(summary)}\n`);
    this.client.stop();
    // Give the child a moment to exit on SIGTERM before the process goes.
    setTimeout(() => process.exit(EXIT[outcome]), 300).unref?.();
    setTimeout(() => process.exit(EXIT[outcome]), 2_000);
  }

  async openThread() {
    const thread = {
      cwd: this.opts.cwd,
      model: this.opts.model,
      sandbox: this.opts.sandbox,
      approvalPolicy: 'never',
      approvalsReviewer: 'user',
      // The effort rides on every turn/start too; setting it here as well means the
      // thread never reports the config default (xhigh on Pete's Mac) as its own.
      config: { model_reasoning_effort: this.opts.effort },
    };
    if (this.opts.thread) {
      try {
        const resumed = await this.client.request('thread/resume', { threadId: this.opts.thread, ...thread });
        this.threadId = resumed.thread?.id ?? this.opts.thread;
        this.log({ resumed: this.threadId });
        return;
      } catch (error) {
        // An expired or foreign thread id is recoverable: start fresh and say so.
        this.log({ resumeFailed: error.message });
        this.note(`> could not resume ${this.opts.thread} (${error.message}); started a new thread`);
      }
    }
    const started = await this.client.request('thread/start', thread);
    this.threadId = started.thread?.id;
    if (!this.threadId) throw new Error('thread/start returned no thread id');
    this.log({ started: this.threadId, model: started.model ?? null, reasoningEffort: started.reasoningEffort ?? null });
  }

  async run() {
    this.watch();
    try {
      await this.client.handshake();
      await this.openThread();
      this.writeStatus(true);
      if (this.opts.mode === 'review') {
        const turn = await this.client.request('review/start', {
          threadId: this.threadId,
          target: this.opts.reviewTarget,
          delivery: 'inline',
        });
        this.turnId = turn.turn?.id ?? this.turnId;
      } else {
        const brief = readFileSync(this.opts.brief, 'utf8');
        this.note(`## brief\n\n${brief}\n\n## run`);
        const turn = await this.client.request('turn/start', {
          threadId: this.threadId,
          input: [{ type: 'text', text: brief, text_elements: [] }],
          effort: this.opts.effort,
          sandboxPolicy: this.opts.sandbox === 'workspace-write'
            ? { type: 'workspaceWrite', writableRoots: this.opts.writableRoots }
            : this.opts.sandbox === 'read-only' ? { type: 'readOnly' } : { type: 'dangerFullAccess' },
        });
        this.turnId = turn.turn?.id ?? this.turnId;
      }
      this.setPhase('running');
      this.touch('turn accepted');
    } catch (error) {
      this.finish('died', error.message);
    }
  }
}

function status(opts) {
  const file = join(opts.log ?? '', 'status.json');
  if (!opts.log || !existsSync(file)) usage(`no status.json under ${opts.log ?? '(no --log)'}`);
  const s = JSON.parse(readFileSync(file, 'utf8'));
  const age = Math.round((Date.now() - new Date(s.updatedAt).getTime()) / 1000);
  s.idleSeconds = Math.round((Date.now() - new Date(s.lastEventAt).getTime()) / 1000);
  s.statusAgeSeconds = age;
  s.alive = s.pid ? (() => { try { process.kill(s.pid, 0); return true; } catch { return false; } })() : false;
  process.stdout.write(`${JSON.stringify(s, null, 2)}\n`);
}

function main() {
  const opts = parseArgs(process.argv.slice(2));
  if (opts.mode === 'status') return status(opts);
  if (opts.mode !== 'run' && opts.mode !== 'review') usage(`mode must be run, review or status`);
  if (!opts.cwd || !existsSync(opts.cwd) || !statSync(opts.cwd).isDirectory()) usage('--cwd must be an existing directory');
  if (!opts.result || !opts.log) usage('--result and --log are required');
  if (opts.mode === 'run' && (!opts.brief || !existsSync(opts.brief))) usage('--brief must be an existing file');
  if (opts.mode === 'review' && !opts.reviewTarget) usage('review needs --base REF, --commit SHA or --uncommitted');
  opts.model ??= 'gpt-5.6-sol';
  opts.effort ??= 'high';
  opts.sandbox ??= opts.mode === 'review' ? 'read-only' : 'workspace-write';
  opts.stallMin = Number.isFinite(opts.stallMin) ? opts.stallMin : 15;
  opts.timeoutMin = Number.isFinite(opts.timeoutMin) ? opts.timeoutMin : 120;
  const common = gitCommonDir(opts.cwd);
  if (common && !within(common, [opts.cwd, ...opts.writableRoots])) opts.writableRoots.push(common);
  mkdirSync(resolve(opts.result, '..'), { recursive: true });
  const run = new Run(opts);
  void run.run();
}

main();
