#!/usr/bin/env python3
"""Muse Code reads a plan or a branch through `muse serve`, read-only, and reports what it found.

  muse.py review <worktree> <brief.md> <out-dir> [model]  a read-only reader (PLAN's plan review, REVIEW's
                                                          other-lab read), Wonder Full by default; exit 6 if
                                                          anything changed the tree during the read
  muse.py --selftest

A read is one `muse serve` session (JSON-RPC 2.0, one object per line on stdio): initialize,
initialized, session/start, turn/start with the brief, then frames until turn/completed. Muse
writes code for ship no more (Pete, 2026-10-24); the build mode is in git history.

<out-dir> gets events.jsonl (every frame), last.md (the last finalAnswer message, else the last
agentMessage), seconds (the read's wall time, which `route.py log out=<out-dir>` reads), stderr.txt and
home/, the serve's HOME: a shadow of the real home, every entry linked back except the skill
folders (SKIP_HOME), so the login (macOS Keychain), Xcode, npm and Playwright caches all work in
the model's shell while Pete's personal skills never load and never reach Meta. `serve` has no
setting for this: its `--no-foreign-personal-context` skips only ~/.claude and ~/.codex skills,
and it has no shell-environment policy (2026-10-16).

Exit 0: completed with a final message. 1: the turn failed, or a request got a JSON-RPC error.
2: usage error. 3: killed by the watchdog (no turn/started inside
MUSE_STARTUP seconds, default 60, or no frame for MUSE_IDLE, default 900). 4: completed with no
agent message, which means it DID NOT RUN. 5: quota hit; it prints the reset. 6: the tree
changed during the read. MUSE_BIN overrides the `muse` command.
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
from datetime import datetime, timezone

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


def run(worktree, brief, out, model):
    """One serve session on the brief in `worktree`; review() checks the paths first."""
    real = os.path.expanduser('~')  # before the child's HOME moves
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
    finally:
        serve.kill()
    message = serve.final or serve.last  # the final answer, else whatever it said last
    if message:
        open(last, 'w').write(message)
    done, error = serve.done, serve.done.get('error') or {}
    if done.get('terminal') == 'completed':
        if not message:
            raise Exit(4, 'turn completed and no agent message. The run DID NOT RUN; retry it.')
        secs = round(time.time() - started)
        open(os.path.join(os.path.dirname(last), 'seconds'), 'w').write(f'{secs}\n')  # route.py log out=<out>
        print(f'muse: done in {secs}s -> {last}')
        return 0
    if error.get('quota'):
        reset = error['quota'].get('resetsAtMs') or 0
        when = (datetime.fromtimestamp(reset / 1000, timezone.utc).isoformat(timespec='seconds')
                if reset > time.time() * 1000 else 'at a time Muse did not give')
        print(f"muse: quota hit ({error['quota'].get('limitKind')}), resets {when}")
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
    elif method == 'turn/start':
        if scenario == 'edit':  # a reader, or anything else, writing in the tree mid-read
            open(os.environ['STUB_EDIT'], 'w').write('x\n')
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
        os.makedirs(wt)
        open(os.path.join(tmp, 'brief.md'), 'w').write('do the thing')
        def read(scenario, name, worktree=wt, **env):
            if os.path.exists(os.path.join(tmp, 'started')):
                os.remove(os.path.join(tmp, 'started'))
            out = name if os.path.isabs(name) else os.path.join(tmp, name)
            r = subprocess.run([sys.executable, os.path.abspath(__file__), 'review', worktree,
                                os.path.join(tmp, 'brief.md'), out, 'muse-wonder-test'],
                               capture_output=True, text=True, timeout=60,
                               env=dict(os.environ, **{'HOME': real, 'MUSE_BIN': stub, 'STUB_DIR': tmp,
                                        'STUB_SCENARIO': scenario, **env}))
            started = os.path.join(tmp, 'started')
            return r, out, json.load(open(started)) if os.path.exists(started) else None

        def gone(seen):
            try:
                os.kill(seen['pid'], 0)
                return False
            except OSError:
                return True

        gwt = os.path.join(tmp, 'gwt')
        os.makedirs(gwt)
        subprocess.run(['git', 'init', '-q', gwt], check=True)
        open(os.path.join(gwt, 'a.txt'), 'w').write('a\n')
        subprocess.run(['git', '-C', gwt, '-c', 'user.email=t@t', '-c', 'user.name=t', 'add', '-A'], check=True)
        subprocess.run(['git', '-C', gwt, '-c', 'user.email=t@t', '-c', 'user.name=t', 'commit', '-qm', 'a'], check=True)
        state = tree_state(gwt)
        rr = subprocess.run([sys.executable, os.path.abspath(__file__), 'review', gwt, os.path.join(tmp, 'brief.md'),
                             os.path.join(tmp, 'rv')], capture_output=True, text=True, timeout=60,
                            env=dict(os.environ, **{'HOME': real, 'MUSE_BIN': stub, 'STUB_DIR': tmp,
                                     'STUB_SCENARIO': 'ok'}))
        sent = open(os.path.join(tmp, 'rv', 'review-brief.md')).read()
        check('review leads the brief with read-only rules and passes on an untouched tree',
              rr.returncode == 0 and sent.startswith('Read only.') and 'one batch of parallel calls' in sent and sent.endswith('do the thing'))
        open(os.path.join(gwt, 'a.txt'), 'w').write('changed\n')
        check('the tree check notices an edit a reader made', tree_state(gwt) != state)
        rr = subprocess.run([sys.executable, os.path.abspath(__file__), 'review', gwt, os.path.join(tmp, 'brief.md'),
                             os.path.join(tmp, 'rv2')], capture_output=True, text=True, timeout=60,
                            env=dict(os.environ, **{'HOME': real, 'MUSE_BIN': stub, 'STUB_DIR': tmp,
                                     'STUB_SCENARIO': 'edit', 'STUB_EDIT': os.path.join(gwt, 'b.txt')}))
        check('a write during the read exits 6 and names the changed file',
              rr.returncode == 6 and 'b.txt' in rr.stderr and 'a build, the gates' in rr.stderr)
        r, out, seen = read('ok', 'o1')
        check('a completed read exits 0, last.md is the final answer, not later commentary, and seconds is written',
              r.returncode == 0 and open(os.path.join(out, 'last.md')).read() == 'built it' and 'done in' in r.stdout
              and open(os.path.join(out, 'seconds')).read().strip().isdigit())
        check('every frame lands in events.jsonl',
              sum(1 for _ in open(os.path.join(out, 'events.jsonl'))) == 8)
        home = os.path.join(out, 'home')
        auth = os.path.join(home, '.config', 'muse', 'auth.json')
        linked = sorted(os.listdir(home))
        check('serve argv carries the flags, the model and no session log',
              seen and seen['argv'][:6] == ['serve', *FLAGS] and
              seen['argv'][6:] == ['--model', 'muse-wonder-test', '--no-session-log'])
        check('HOME is a shadow home: the real entries linked, the skill folders left out',
              seen and seen['home'] == home and linked == ['.config', '.npm', 'Library'] and
              all(os.path.islink(os.path.join(home, n)) for n in linked) and
              os.path.realpath(auth) == os.path.join(real, '.config', 'muse', 'auth.json'))
        check('no auto-update, and cwd is the worktree', seen and seen['no_update'] == '1' and seen['cwd'] == wt)
        check('the serve is gone after a clean exit', seen and gone(seen))

        r, out, _ = read('quota', 'o2')
        check('a quota failure exits 5 and prints the reset',
              r.returncode == 5 and 'quota hit (tierLimit), resets 2030-03-17' in r.stdout)
        r, _, _ = read('quota', 'o2b', STUB_RESET='1000')
        check('a reset already past is not printed as a date', r.returncode == 5 and 'did not give' in r.stdout)

        r, _, _ = read('nomsg', 'o3')
        check('completed with no agent message exits 4', r.returncode == 4 and 'DID NOT RUN' in r.stderr)

        r, _, seen = read('silent', 'o4', MUSE_STARTUP='2')
        check('a silent server is killed with exit 3', r.returncode == 3 and seen and gone(seen))

        r, _, _ = read('rpcerror', 'o5')
        check('a JSON-RPC error exits 1 with its message', r.returncode == 1 and 'unknown model nope' in r.stderr)

        os.makedirs(os.path.join(tmp, 'o7'))
        os.symlink(real, os.path.join(tmp, 'o7', 'home'))
        r, out, _ = read('ok', 'o7')
        home = os.path.join(out, 'home')
        check('a reused out-dir whose home links to the real home gets a fresh shadow',
              r.returncode == 0 and not os.path.islink(home) and '.agents' not in os.listdir(home) and
              os.path.isdir(os.path.join(real, '.agents', 'skills')))
        os.makedirs(os.path.join(tmp, 'o8', 'home'))
        os.symlink(os.path.join(real, '.agents'), os.path.join(tmp, 'o8', 'home', '.agents'))
        r, out, _ = read('ok', 'o8')
        check("a reused home's old links go, and their targets stay",
              r.returncode == 0 and '.agents' not in os.listdir(os.path.join(out, 'home')) and
              os.path.isdir(os.path.join(real, '.agents', 'skills')) and os.path.isdir(os.path.join(real, '.npm')))

        r, _, seen = read('ok', os.path.join(wt, 'out'))
        check('an out-dir inside the worktree exits 2 and makes nothing there',
              r.returncode == 2 and seen is None and not os.path.exists(os.path.join(wt, 'out')))

        r, _, _ = read('ok', 'o11', MUSE_BIN=os.path.join(tmp, 'no-such-muse'))
        check('a serve that cannot start exits 1 with a line, not a traceback',
              r.returncode == 1 and 'could not start' in r.stderr and 'Traceback' not in r.stderr)
    print(f'muse self-test: {fails} failed')
    return fails == 0


REVIEW_MODEL = 'muse-wonder-full-1.0'
# Pacing, from four plan reviews on 2026-10-24: 21-52 serial turns of one read each, 6-17 min,
# the prompt growing from 26k to 270k tokens, and a 37-47k character report that took 3 min alone.
READ_ONLY = ('Read only. Edit no file, commit nothing, and run no command that writes files, binds a port '
             'or starts a server. Report findings as file:line, the failure scenario, and a severity.\n\n'
             'Pace: in your first turn, read every file the brief names in one batch of parallel calls, and '
             'batch every later read and search the same way. How a dependency behaves is checked in its '
             'installed code; the web is only for a platform API with no code on disk. Report once each item '
             'in the brief is checked, within about 25 tool rounds. Report what would break, mislead or miss the spec; '
             'leave out style, naming and comments that are not wrong. The report is every real finding, most '
             'severe first, at most two lines each, with no preamble and no summary of the plan, under 1,000 '
             'words.\n\n')


def tree_state(worktree):
    """What a reader must leave as it found it: HEAD, and the status and diff of the working tree."""
    git = lambda *a: subprocess.run(['git', '-C', worktree, *a], capture_output=True, text=True).stdout
    return git('rev-parse', 'HEAD') + git('status', '--porcelain') + git('diff', 'HEAD')


def review(worktree, brief, out, model=REVIEW_MODEL):
    if not os.path.isdir(worktree):
        raise Exit(2, f'no worktree at {worktree}')
    if not (os.path.isfile(brief) and os.path.getsize(brief)):
        raise Exit(2, f'brief {brief} is missing or empty')
    worktree, out = os.path.realpath(worktree), os.path.realpath(out)
    if out == worktree or out.startswith(worktree.rstrip('/') + '/'):
        raise Exit(2, f'out-dir {out} is inside the worktree: Muse would index the shadow home and git add -A '
                      'would commit it. Put it outside.')
    os.makedirs(out, exist_ok=True)
    ro = os.path.join(out, 'review-brief.md')
    open(ro, 'w').write(READ_ONLY + open(brief).read())
    before = tree_state(worktree)
    code = run(worktree, ro, out, model)
    if tree_state(worktree) != before:
        now = subprocess.run(['git', '-C', worktree, 'status', '--porcelain'], capture_output=True,
                             text=True).stdout.strip() or '(clean again)'
        raise Exit(6, f'the tree changed during the read: its findings are in {out}/last.md. Changed now:\n'
                      f'{now[:1500]}\nAnything else that wrote in the worktree meanwhile (a build, the gates) '
                      'trips this too; check `git diff` before trusting the tree')
    return code


def main(args):
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(143))  # so `finally` kills the serve
    if args == ['--selftest']:
        return 0 if selftest() else 1
    if not (args[:1] == ['review'] and len(args) in (4, 5)):
        print(__doc__.split('\n\n')[1], file=sys.stderr)
        return 2
    try:
        return review(*args[1:])
    except Exit as error:
        print(f'muse: {error}', file=sys.stderr)
        return error.code


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
