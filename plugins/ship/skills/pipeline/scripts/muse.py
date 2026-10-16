#!/usr/bin/env python3
"""Muse Code builds through `muse serve`, with astra.sh's guards, and records the plan usage it reports.

  muse.py build <worktree> <brief.md> <out-dir> <model>   BUILD's Muse builder on the model the router picked
  muse.py usage                                           the cached plan usage; no prompt spent
  muse.py --selftest

`muse exec` never reports plan usage; `muse serve` (JSON-RPC 2.0, one object per line on stdio)
sends `usage/changed` after each turn, so a build runs a serve session: initialize, initialized,
session/start, turn/start with the brief, then frames until turn/completed. Every usage report,
and a final `usage/read`, rewrites ~/.claude/muse-usage-cache.json (or SHIP_QUOTA_MUSE), which
quota.py reads for the `muse` pool.

<out-dir> gets events.jsonl (every frame), last.md (the last finalAnswer message, else the last agentMessage), stderr.txt and
home/, the serve's HOME: a shadow of the real home, every entry linked back except the skill
folders (SKIP_HOME), so the login (macOS Keychain), Xcode, npm and Playwright caches all work in
the model's shell while Pete's personal skills never load and never reach Meta. `serve` has no
setting for this: its `--no-foreign-personal-context` skips only ~/.claude and ~/.codex skills,
and it has no shell-environment policy (2026-10-16). A confidential repo is refused
before serve starts: Contributor mode trains on what it sees.

Exit 0: completed with a final message. 1: the turn failed, or a request got a JSON-RPC error.
2: usage error or confidential worktree. 3: killed by the watchdog (no turn/started inside
MUSE_STARTUP seconds, default 60, or no frame for MUSE_IDLE, default 900). 4: completed with no
agent message, which means it DID NOT RUN. 5: quota hit; the cache is marked exhausted until
the reset. MUSE_BIN overrides the `muse` command.
"""
import json
import os
import select
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import uuid

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import quota  # noqa: E402  one reader for confidential()

STARTUP = float(os.environ.get('MUSE_STARTUP') or 60)
IDLE = float(os.environ.get('MUSE_IDLE') or 900)
FLAGS = ['--contributor-mode', 'on', '--disable-sandbox', '--trust-workspace', '--disable-request-user-input']


class Exit(Exception):
    def __init__(self, code, message=''):
        super().__init__(message)
        self.code = code


def uuid7():
    """commandId must be a UUIDv7: 48 bits of epoch ms, then random with version and variant set."""
    b = bytearray(int(time.time() * 1000).to_bytes(6, 'big') + os.urandom(10))
    b[6] = (b[6] & 0x0F) | 0x70
    b[8] = (b[8] & 0x3F) | 0x80
    return str(uuid.UUID(bytes=bytes(b)))


def cache_path():
    return os.environ.get('SHIP_QUOTA_MUSE') or os.path.expanduser('~/.claude/muse-usage-cache.json')


def read_cache(path=None):
    try:
        return json.load(open(path or cache_path()))
    except (OSError, ValueError):
        return None


def write_cache(data):
    """Temp file and rename, so quota.py never reads half a file."""
    path = cache_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), prefix='.muse-usage-')
    with os.fdopen(fd, 'w') as f:
        json.dump(data, f)
    os.replace(tmp, path)


def save_usage(usage):
    """An older observation never overwrites a newer one, such as a parallel build's exhausted mark."""
    seen = usage.get('observedAtMs') or int(time.time() * 1000)
    if ((read_cache() or {}).get('observedAtMs') or 0) > seen:
        return
    write_cache(dict(usage, observedAtMs=seen))


def mark_exhausted(detail):
    """A quota failure empties the pool until the reset it names."""
    now_ms = int(time.time() * 1000)
    reset = detail.get('resetsAtMs') or 0
    if reset <= now_ms:  # a missing or past reset would reopen the pool at once
        reset = now_ms + 5 * 3600 * 1000
    data = read_cache() or {}
    window = dict(data.get('window') or {}, usedPercent=100, resetsAtMs=reset)
    window.setdefault('windowDurationMins', 300)
    data.update(window=window, observedAtMs=now_ms, exhausted=detail)
    data.setdefault('weekly', {'usedPercent': 100, 'resetsAtMs': reset})  # quota.py needs a weekly block
    write_cache(data)
    return reset


class Serve:
    def __init__(self, argv, env, cwd, out):
        self.events = open(os.path.join(out, 'events.jsonl'), 'w', buffering=1)
        try:
            with open(os.path.join(out, 'stderr.txt'), 'wb') as err:
                self.p = subprocess.Popen(argv, cwd=cwd, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                          stderr=err, start_new_session=True)
        except OSError as error:
            self.events.close()
            raise Exit(1, f'could not start {argv[0]}: {error}')
        self.buf, self.ids = b'', 0
        self.began = self.heard = time.time()
        self.turn_started, self.last, self.final, self.done = False, None, None, None

    def kill(self):
        try:
            os.killpg(self.p.pid, signal.SIGKILL)  # the serve and every shell its model started
        except OSError:
            pass
        self.p.wait()
        self.events.close()

    def send(self, msg):
        try:
            self.p.stdin.write((json.dumps(dict(msg, jsonrpc='2.0')) + '\n').encode())
            self.p.stdin.flush()
        except OSError:
            raise Exit(1, 'muse serve closed its input. See stderr.txt')

    def frame(self, limit=None):
        """The next frame, the watchdog running while it waits; None when `limit` passes first."""
        while b'\n' not in self.buf:
            t = time.time()
            if not self.turn_started and t - self.began >= STARTUP:
                raise Exit(3, f'no turn/started after {STARTUP:.0f}s; died at startup. See stderr.txt')
            if t - self.heard >= IDLE:
                raise Exit(3, f'no frame for {IDLE:.0f}s; the run went silent; run a fresh builder')
            if limit and t >= limit:
                return None
            if select.select([self.p.stdout], [], [], 1)[0]:
                chunk = os.read(self.p.stdout.fileno(), 65536)
                if not chunk:
                    raise Exit(1, 'muse serve exited before the turn completed. See stderr.txt')
                self.buf += chunk
        line, self.buf = self.buf.split(b'\n', 1)
        self.heard = time.time()
        text = line.decode(errors='replace').strip()
        if text:
            self.events.write(text + '\n')
        try:
            return json.loads(text)
        except ValueError:
            return {}

    def handle(self, m):
        method, params = m.get('method'), m.get('params') or {}
        if 'id' in m and method:  # a request to us; refuse it so the serve never waits on an answer
            self.send({'id': m['id'], 'error': {'code': -32601, 'message': f'ship does not answer {method}'}})
        elif method == 'turn/started':
            self.turn_started = True
        elif method == 'item/completed':
            item = params.get('item') or {}
            if item.get('kind') == 'agentMessage' and item.get('text'):
                self.last = item['text']
                if item.get('messagePhase') == 'finalAnswer':
                    self.final = item['text']
        elif method == 'usage/changed':
            save_usage(params)
        elif method == 'turn/completed':
            self.done = params

    def call(self, method, params, limit=None):
        self.ids += 1
        self.send({'id': self.ids, 'method': method, 'params': params})
        while True:
            m = self.frame(limit)
            if m is None:
                return None
            if m.get('id') == self.ids and 'method' not in m:
                if 'error' in m:
                    raise Exit(1, f"{method} failed: {(m['error'] or {}).get('message') or m['error']}")
                return m.get('result') or {}
            self.handle(m)


# Where personal skills load from: Muse's own ~/.agents/skills, and the other agents' folders.
SKIP_HOME = {'.agents', '.claude', '.codex'}


def shadow_home(real, home):
    """Link every entry of the real home into `home`, except SKIP_HOME. The login token is in the
    Keychain, found through HOME, so a bare private home answers "not logged in" (live, 2026-10-16)."""
    os.makedirs(home, exist_ok=True)
    for name in os.listdir(real):
        dst = os.path.join(home, name)
        if name in SKIP_HOME or os.path.lexists(dst):
            continue
        os.symlink(os.path.join(real, name), dst)


def build(worktree, brief, out, model):
    if not os.path.isdir(worktree):
        raise Exit(2, f'no worktree at {worktree}')
    if not (os.path.isfile(brief) and os.path.getsize(brief)):
        raise Exit(2, f'brief {brief} is missing or empty')
    if quota.confidential(worktree):
        raise Exit(2, f'{worktree} is confidential: Muse trains on what it sees. Route it to Codex.')
    real = os.path.expanduser('~')  # before the child's HOME moves
    worktree, out = os.path.realpath(worktree), os.path.realpath(out)
    if out == worktree or out.startswith(worktree.rstrip('/') + '/'):
        raise Exit(2, f'out-dir {out} is inside the worktree: Muse would index the shadow home and git add -A '
                      'would commit it. Put it outside.')
    home = os.path.join(out, 'home')
    if os.path.islink(home):  # a reused out-dir: never build on top of the real home or old links
        os.unlink(home)
    elif os.path.isdir(home):
        shutil.rmtree(home)  # removes the links inside, never their targets
    shadow_home(real, home)
    last = os.path.join(out, 'last.md')
    if os.path.exists(last):
        os.remove(last)
    env = dict(os.environ, HOME=home, MUSE_NO_AUTO_UPDATE='1')
    argv = [os.environ.get('MUSE_BIN') or 'muse', 'serve', *FLAGS, '--model', model, '--no-session-log']
    started = time.time()
    serve = Serve(argv, env, worktree, out)
    try:
        serve.call('initialize', {'clientInfo': {'name': 'ship', 'version': '1'}})
        serve.send({'method': 'initialized', 'params': {}})
        session = serve.call('session/start', {'commandId': uuid7(), 'workspaceRoot': worktree, 'modelId': model,
                                               'approvalMode': 'allowAll'})
        sid = (session.get('session') or {}).get('sessionId')
        if not sid:
            raise Exit(1, f'session/start gave no session id: {json.dumps(session)[:300]}')
        serve.call('turn/start', {'commandId': uuid7(), 'sessionId': sid, 'reasoningEffort': 'high',
                                  'input': [{'type': 'text', 'text': open(brief).read()}]})
        while serve.done is None:
            serve.handle(serve.frame())
        try:  # bookkeeping: a failed read must not fail a finished build
            usage = serve.call('usage/read', {}, limit=time.time() + 15) or {}
            if usage.get('usage'):  # `{}` means nothing observed yet
                save_usage(usage['usage'])
        except Exit as error:
            print(f'muse: usage/read: {error}', file=sys.stderr)
    finally:
        serve.kill()
    message = serve.final or serve.last  # the final answer, else whatever it said last
    if message:
        open(last, 'w').write(message)
    done, error = serve.done, serve.done.get('error') or {}
    if done.get('terminal') == 'completed':
        if not message:
            raise Exit(4, 'turn completed and no agent message. The run DID NOT RUN; retry it.')
        print(f'muse: done in {time.time() - started:.0f}s -> {last}')
        return 0
    if error.get('quota'):
        reset = mark_exhausted(error['quota'])
        print(f"muse: quota hit ({error['quota'].get('limitKind')}), resets "
              f"{quota.iso(reset / 1000)}; pool marked exhausted in {cache_path()}")
        return 5
    raise Exit(1, f"turn {done.get('terminal')}: {error.get('message') or done.get('reason') or 'no error given'}"
                  f'. See {out}/events.jsonl')


STUB = r'''
import json, os, sys
d, scenario = os.environ['STUB_DIR'], os.environ['STUB_SCENARIO']
json.dump({'argv': sys.argv[1:], 'home': os.environ['HOME'], 'cwd': os.getcwd(), 'pid': os.getpid(),
           'no_update': os.environ.get('MUSE_NO_AUTO_UPDATE')}, open(os.path.join(d, 'started'), 'w'))
def out(**m): print(json.dumps(dict(m, jsonrpc='2.0')), flush=True)
def usage(p): return {'observedAtMs': 1, 'tier': 'pro', 'weekly': {'usedPercent': p, 'resetsAtMs': 9e12},
                      'window': {'usedPercent': p, 'resetsAtMs': 9e12, 'windowDurationMins': 300}}
for line in sys.stdin:
    m = json.loads(line); i, method = m.get('id'), m.get('method')
    if scenario == 'silent' or i is None:
        continue
    if method == 'session/start' and scenario == 'rpcerror':
        out(id=i, error={'code': -32000, 'message': 'unknown model nope'})
    elif method == 'session/start':
        out(id=i, result={'session': {'sessionId': 's1'}})
    elif method == 'usage/read':
        out(id=i, result={'usage': usage(43)} if scenario == 'quota' else {})
    elif method == 'turn/start':
        out(id=i, result={})
        out(method='turn/started', params={'sessionId': 's1'})
        if scenario != 'nomsg':
            for phase, text in (('finalAnswer', 'built it'), ('commentary', 'one more look')):
                out(method='item/completed', params={'sessionId': 's1', 'item': {
                    'kind': 'agentMessage', 'messagePhase': phase, 'text': text}})
        out(method='usage/changed', params=usage(42))
        if scenario == 'quota':
            out(method='turn/completed', params={'sessionId': 's1', 'terminal': 'failed', 'error': {
                'kind': 'modelError', 'message': 'out of quota', 'retryable': False,
                'quota': {'limitKind': 'tierLimit', 'resetsAtMs': int(os.environ.get('STUB_RESET') or 1900000000000)}}})
        else:
            out(method='turn/completed', params={'sessionId': 's1', 'terminal': 'completed'})
    else:
        out(id=i, result={})
'''


def selftest():
    fails = 0

    def check(name, ok):
        nonlocal fails
        print(f"  {'ok  ' if ok else 'FAIL'} {name}")
        fails += 0 if ok else 1

    with tempfile.TemporaryDirectory() as tmp:
        tmp = os.path.realpath(tmp)
        stub, real, wt = os.path.join(tmp, 'muse'), os.path.join(tmp, 'real'), os.path.join(tmp, 'wt')
        open(stub, 'w').write(f'#!{sys.executable}\n{STUB}')
        os.chmod(stub, 0o755)
        os.makedirs(os.path.join(real, '.config', 'muse'))
        open(os.path.join(real, '.config', 'muse', 'auth.json'), 'w').write('{"fake": true}')
        for skills in ('.agents/skills', '.claude/skills', '.codex/skills', 'Library/Keychains', '.npm'):
            os.makedirs(os.path.join(real, skills))
        os.makedirs(os.path.join(tmp, 'secret', 'wt'))
        os.makedirs(wt)
        open(os.path.join(tmp, 'brief.md'), 'w').write('do the thing')
        open(os.path.join(tmp, 'paths'), 'w').write(f"# clients\n{os.path.join(tmp, 'secret')}\n")
        cache = os.path.join(tmp, 'cache.json')

        def run(scenario, name, worktree=wt, keep_cache=False, **env):
            for f in ('started',) + (() if keep_cache else ('cache.json',)):
                if os.path.exists(os.path.join(tmp, f)):
                    os.remove(os.path.join(tmp, f))
            out = name if os.path.isabs(name) else os.path.join(tmp, name)
            r = subprocess.run([sys.executable, os.path.abspath(__file__), 'build', worktree,
                                os.path.join(tmp, 'brief.md'), out, 'muse-spark-1.3'],
                               capture_output=True, text=True, timeout=60,
                               env=dict(os.environ, **{'HOME': real, 'MUSE_BIN': stub, 'STUB_DIR': tmp,
                                        'STUB_SCENARIO': scenario, 'SHIP_QUOTA_MUSE': cache,
                                        'SHIP_CONFIDENTIAL_PATHS': os.path.join(tmp, 'paths'), **env}))
            started = os.path.join(tmp, 'started')
            return r, out, json.load(open(started)) if os.path.exists(started) else None

        def gone(seen):
            try:
                os.kill(seen['pid'], 0)
                return False
            except OSError:
                return True

        r, out, seen = run('ok', 'o1')
        got = read_cache(cache)
        check('a completed build exits 0 and last.md is the final answer, not later commentary', r.returncode == 0 and
              open(os.path.join(out, 'last.md')).read() == 'built it' and 'done in' in r.stdout)
        check('usage/changed writes the cache; an empty usage/read leaves it',
              got and got['weekly']['usedPercent'] == 42 and got.get('observedAtMs'))
        check('every frame lands in events.jsonl',
              sum(1 for _ in open(os.path.join(out, 'events.jsonl'))) == 9)
        home = os.path.join(out, 'home')
        auth = os.path.join(home, '.config', 'muse', 'auth.json')
        linked = sorted(os.listdir(home))
        check('serve argv carries the flags, the model and no session log',
              seen and seen['argv'][:6] == ['serve', *FLAGS] and
              seen['argv'][6:] == ['--model', 'muse-spark-1.3', '--no-session-log'])
        check('HOME is a shadow home: the real entries linked, the skill folders left out',
              seen and seen['home'] == home and linked == ['.config', '.npm', 'Library'] and
              all(os.path.islink(os.path.join(home, n)) for n in linked) and
              os.path.realpath(auth) == os.path.join(real, '.config', 'muse', 'auth.json'))
        check('no auto-update, and cwd is the worktree', seen and seen['no_update'] == '1' and seen['cwd'] == wt)
        check('the serve is gone after a clean exit', seen and gone(seen))

        r, out, _ = run('quota', 'o2')
        got = read_cache(cache)
        check('a quota failure exits 5 and prints the reset', r.returncode == 5 and 'quota hit' in r.stdout)
        check('the cache is marked exhausted with the reset, the weekly read kept',
              got and got['window']['usedPercent'] == 100 and got['window']['resetsAtMs'] == 1900000000000 and
              got['weekly']['usedPercent'] == 43)

        r, _, _ = run('nomsg', 'o3')
        check('completed with no agent message exits 4', r.returncode == 4 and 'DID NOT RUN' in r.stderr)

        r, _, seen = run('silent', 'o4', MUSE_STARTUP='2')
        check('a silent server is killed with exit 3', r.returncode == 3 and seen and gone(seen))

        r, _, _ = run('rpcerror', 'o5')
        check('a JSON-RPC error exits 1 with its message', r.returncode == 1 and 'unknown model nope' in r.stderr)

        r, _, seen = run('ok', 'o6', worktree=os.path.join(tmp, 'secret', 'wt'))
        check('a confidential worktree exits 2 and never starts the server', r.returncode == 2 and seen is None)

        os.makedirs(os.path.join(tmp, 'o7'))
        os.symlink(real, os.path.join(tmp, 'o7', 'home'))
        r, out, _ = run('ok', 'o7')
        home = os.path.join(out, 'home')
        check('a reused out-dir whose home links to the real home gets a fresh shadow',
              r.returncode == 0 and not os.path.islink(home) and '.agents' not in os.listdir(home) and
              os.path.isdir(os.path.join(real, '.agents', 'skills')))
        os.makedirs(os.path.join(tmp, 'o8', 'home'))
        os.symlink(os.path.join(real, '.agents'), os.path.join(tmp, 'o8', 'home', '.agents'))
        r, out, _ = run('ok', 'o8')
        check("a reused home's old links go, and their targets stay",
              r.returncode == 0 and '.agents' not in os.listdir(os.path.join(out, 'home')) and
              os.path.isdir(os.path.join(real, '.agents', 'skills')) and os.path.isdir(os.path.join(real, '.npm')))

        r, _, seen = run('ok', os.path.join(wt, 'out'))
        check('an out-dir inside the worktree exits 2 and builds no home there',
              r.returncode == 2 and seen is None and not os.path.exists(os.path.join(wt, 'out')))

        mark = int(time.time() * 1000)
        json.dump({'observedAtMs': mark, 'weekly': {'usedPercent': 43, 'resetsAtMs': 9e12},
                   'window': {'usedPercent': 100, 'resetsAtMs': 1900000000000}}, open(cache, 'w'))
        r, _, _ = run('ok', 'o9', keep_cache=True)
        got = read_cache(cache)
        check("a parallel build's older usage never erases an exhausted mark",
              r.returncode == 0 and got['window']['usedPercent'] == 100 and got['observedAtMs'] == mark)

        r, _, _ = run('quota', 'o10', STUB_RESET='1000')
        got = read_cache(cache)
        check('a quota reset already past is floored at five hours from now',
              r.returncode == 5 and got['window']['resetsAtMs'] >= (time.time() + 5 * 3600 - 60) * 1000)

        r, _, _ = run('ok', 'o11', MUSE_BIN=os.path.join(tmp, 'no-such-muse'))
        check('a serve that cannot start exits 1 with a line, not a traceback',
              r.returncode == 1 and 'could not start' in r.stderr and 'Traceback' not in r.stderr)
    print(f'muse self-test: {fails} failed')
    return fails == 0


def main(args):
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(143))  # so `finally` kills the serve
    if args == ['--selftest']:
        return 0 if selftest() else 1
    if args == ['usage']:
        data = read_cache()
        print(json.dumps(data, indent=1) if data else f'muse: no usage observed yet ({cache_path()})')
        return 0
    if len(args) != 5 or args[0] != 'build':
        print(__doc__.split('\n\n')[1], file=sys.stderr)
        return 2
    try:
        return build(*args[1:])
    except Exit as error:
        print(f'muse: {error}', file=sys.stderr)
        return error.code


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
