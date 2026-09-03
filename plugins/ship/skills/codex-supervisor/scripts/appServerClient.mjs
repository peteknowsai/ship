// A JSON-RPC-over-stdio client for `codex app-server`, with no dependencies, for
// scripts that run under a bare `node`. One message per line; an incrementing integer
// id; a line with `method` and `id` is a request FROM the server, `method` alone is a
// notification, `id` alone is a response to us.
//
// Three things the naive version lacked, each from a run that hung:
//   * stderr is drained. A full pipe stops the child dead, and the last few KB are the
//     only explanation a bad flag or a dead login ever gives.
//   * every server request is answered. An unanswered approval wedges the thread
//     forever; the default here is a JSON-RPC error, which codex treats as a decline.
//   * `method` is read before `id`. app-server numbers its own requests, so a server
//     request carrying id 1 while our request 1 is in flight would settle the wrong
//     promise with a question.
import { spawn } from 'node:child_process';

const STDERR_TAIL_BYTES = 8_000;
const METHOD_NOT_FOUND = { code: -32601, message: 'client does not handle this request' };

export class AppServerClient {
  #child;
  #buffer = '';
  #nextId = 0;
  #pending = new Map();
  #stderr = '';
  #closed = false;
  #opts;

  constructor(opts = {}) {
    this.#opts = opts;
  }

  get pid() {
    return this.#child?.pid;
  }

  get stderrTail() {
    return this.#stderr;
  }

  get closed() {
    return this.#closed;
  }

  start() {
    if (this.#child) return this.#child;
    const { bin = 'codex', args = [], cwd, env = process.env, spawnChild } = this.#opts;
    const child = spawnChild
      ? spawnChild()
      : spawn(bin, ['app-server', ...args], { cwd, env, stdio: ['pipe', 'pipe', 'pipe'] });
    this.#child = child;
    child.stdout.setEncoding('utf8');
    child.stdout.on('data', (chunk) => this.#consume(chunk));
    child.stderr.setEncoding('utf8');
    child.stderr.on('data', (chunk) => {
      this.#stderr = (this.#stderr + chunk).slice(-STDERR_TAIL_BYTES);
      this.#opts.onStderr?.(chunk);
    });
    // A missing binary is an async 'error' event, never a throw; with no listener the
    // emitter rethrows and takes the whole script down with a useless stack.
    child.on('error', (error) => this.#die(`spawn failed: ${error.message}`, null));
    child.on('exit', (code, signal) => this.#die(`app-server exited${code == null ? ` (${signal})` : ` (${code})`}`, code));
    return child;
  }

  #die(reason, code) {
    if (this.#closed) return;
    this.#closed = true;
    this.#child = undefined;
    for (const [id, { reject }] of [...this.#pending]) {
      this.#pending.delete(id);
      reject(new Error(reason));
    }
    this.#opts.onNotification?.({ method: 'app-server/closed', params: { reason, code } });
  }

  #consume(chunk) {
    this.#buffer += chunk;
    let index = this.#buffer.indexOf('\n');
    while (index >= 0) {
      const line = this.#buffer.slice(0, index);
      this.#buffer = this.#buffer.slice(index + 1);
      index = this.#buffer.indexOf('\n');
      if (!line.trim()) continue;
      let message;
      try {
        message = JSON.parse(line);
      } catch {
        this.#opts.onStderr?.(`[unparseable stdout] ${line.slice(0, 200)}\n`);
        continue;
      }
      this.#route(message);
    }
  }

  #route(message) {
    const { method, id } = message;
    if (typeof method === 'string') {
      const params = message.params ?? {};
      if (id != null) void this.#answer(id, method, params);
      else this.#opts.onNotification?.({ method, params });
      return;
    }
    if (id == null) return;
    const entry = this.#pending.get(id);
    if (!entry) return;
    this.#pending.delete(id);
    if (message.error) entry.reject(Object.assign(new Error(message.error.message ?? `${entry.method} failed`), { rpc: message.error }));
    else entry.resolve(message.result ?? {});
  }

  async #answer(id, method, params) {
    let reply;
    try {
      reply = await this.#opts.onServerRequest?.({ method, params });
    } catch (error) {
      reply = { __error: { code: -32000, message: String(error?.message ?? error) } };
    }
    const frame = reply === undefined
      ? { id, error: METHOD_NOT_FOUND }
      : reply && reply.__error
        ? { id, error: reply.__error }
        : { id, result: reply };
    this.#write(frame);
  }

  #write(frame) {
    const child = this.#child;
    if (!child || this.#closed) return;
    try {
      child.stdin.write(`${JSON.stringify(frame)}\n`);
    } catch {
      // The child is going; its exit handler reports it.
    }
  }

  request(method, params, { timeoutMs } = {}) {
    this.start();
    if (this.#closed) return Promise.reject(new Error('app-server is closed'));
    const id = ++this.#nextId;
    const budget = timeoutMs ?? this.#opts.requestTimeoutMs ?? 60_000;
    return new Promise((resolve, reject) => {
      this.#pending.set(id, { method, resolve, reject });
      this.#write({ id, method, ...(params === undefined ? {} : { params }) });
      const timer = setTimeout(() => {
        if (this.#pending.delete(id)) reject(new Error(`${method} got no answer in ${budget}ms`));
      }, budget);
      timer.unref?.();
    });
  }

  notify(method, params) {
    this.start();
    this.#write({ method, ...(params === undefined ? {} : { params }) });
  }

  async handshake({ name = 'ship-dispatch', title = 'ship dispatch', version = '1.0.0' } = {}) {
    const ready = await this.request('initialize', {
      clientInfo: { name, title, version },
      capabilities: { experimentalApi: true },
    });
    this.notify('initialized', {});
    return ready;
  }

  stop(signal = 'SIGTERM') {
    const child = this.#child;
    if (!child) return;
    try {
      child.stdin.end();
    } catch {
      // Already gone.
    }
    if (child.exitCode == null) child.kill(signal);
  }
}
