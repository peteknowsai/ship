#!/usr/bin/env python3
"""TEST with Pete in the Codex app: hand the brief to a Codex thread, then wait for its verdict.

  codex-handoff.py start  <worktree> <brief.md> <out-dir> [effort]   first turn drafts the test
                                                    plan, then the thread opens in the Codex app,
                                                    named "🧪 Test · <repo> · <branch>", with
                                                    ship's go queued so testing starts at once
  codex-handoff.py wait   <out-dir>                 block until a turn ends on a VERDICT line
  codex-handoff.py retest <out-dir> <note.md>       a fix round: the note is queued into the same
                                                    thread, which the Codex app runs once it has it open
  codex-handoff.py --selftest

`start` runs its own `codex app-server` over stdio for one turn and exits; the thread lives
on in ~/.codex, and `codex://threads/<id>` opens it in the desktop app, whose own app-server
resumes it and runs the queued go. Pete steers it there, and Codex tests with whatever the app
gives it: the browser, computer use, his iPhone. <out-dir> gets thread.json (id, rollout
path, link) and plan.md; `wait` writes last.md, prints the verdict and exits 0, or 2 when
the thread is gone. The verdict travels in the thread's rollout, so the tester never has
to write a file. A thread takes one writer, and the app holds the thread once Pete opens
it, so a retest goes through `codex queue`, which the app drains (2026-10-05). The daemon's control socket (`app-server proxy`) does not answer bare
JSON lines, which is why this starts its own server (2026-10-05).
"""
import json
import os
import re
import subprocess
import sys
import tempfile
import time

MODEL = os.environ.get('ASTRA_MODEL', 'gpt-6-astra')
CODEX = os.environ.get('ASTRA_CODEX', 'codex')
VERDICT = re.compile(r'^\s*\**VERDICT:?\**\s*:?\s*(works|broken|unverifiable)\b', re.I | re.M)

RULES = """You are ship's tester, working live with Pete in the Codex app. Ship (a Claude Code
session) built this change and wrote the brief below; you stand in for the user and prove
whether it works.

Turn 1: read the brief and reply with a numbered test plan: each flow, what you will see when
it passes, and where you run it (browser, computer use, or the iPhone app). Turn 1 runs
before the thread reaches Pete, with no network and nobody to approve anything, so use
nothing but reading files: no `curl`, browser, computer use or device. Ship already checked
the app is up. Then stop. Ship's go arrives as the next message, in the Codex app with Pete
watching: start testing straight away, and take his steers as they come.

While testing: use the app the way Pete would, and show him what you see. Never edit, create
or delete a file in the repo and never fix anything: ship fixes. Screenshots go in the shots
path the brief names.

The phone is the native app only: the one the brief's IOS line names, which ship built from
this branch and pointed at this branch's server. Never test a web page in the phone's Safari.
If that app is missing from the phone, or talks to another server, do not build or install
one: end with `VERDICT: unverifiable` saying the branch app is missing, and ship installs it
and sends a retest.

When you and Pete agree testing is done, your final message is the report the brief asks for,
starting with exactly one line `VERDICT: works`, `VERDICT: broken` or `VERDICT: unverifiable`.
That line hands the result back to ship, so write it only then, never in the plan or a
progress note. After a retest note from ship, test what it names and end the same way."""


class Server:
    """One stdio app-server for one turn: answer nothing, collect until the turn ends."""

    def __init__(self):
        self.p = subprocess.Popen([CODEX, 'app-server'], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                  stderr=subprocess.DEVNULL, text=True, bufsize=1)
        self.n = 0
        self.call('initialize', {'clientInfo': {'name': 'ship', 'title': 'ship', 'version': '1'}})
        self.send({'method': 'initialized', 'params': {}})

    def send(self, msg):
        self.p.stdin.write(json.dumps(msg) + '\n')
        self.p.stdin.flush()

    def call(self, method, params):
        self.n += 1
        self.send({'id': self.n, 'method': method, 'params': params})
        for line in self.p.stdout:
            m = json.loads(line)
            if m.get('id') == self.n and 'method' not in m:
                if 'error' in m:
                    raise SystemExit(f'codex-handoff: {method} failed: {m["error"]}')
                return m['result']
        raise SystemExit(f'codex-handoff: app-server exited during {method}')

    def turn(self, thread_id, text, effort):
        self.call('turn/start', {'threadId': thread_id, 'effort': effort,
                                 'input': [{'type': 'text', 'text': text}]})
        for line in self.p.stdout:
            m = json.loads(line)
            if m.get('method') == 'turn/completed':
                return m['params']['turn']
            if 'id' in m and 'method' in m:  # an approval the first turn should never need
                self.send({'id': m['id'], 'result': {'decision': 'decline'}})
        raise SystemExit('codex-handoff: app-server exited mid-turn')

    def close(self):
        self.p.stdin.close()
        self.p.wait(timeout=10)


def last_message(rollout, start=0):
    """The last agent message of each completed turn in a rollout, from byte offset `start`."""
    out = []
    with open(rollout) as f:
        f.seek(start)
        for line in f:
            try:
                p = json.loads(line).get('payload') or {}
            except ValueError:
                continue  # a line still being written
            if p.get('type') == 'task_complete' and p.get('last_agent_message'):
                out.append(p['last_agent_message'])
    return out


def rollout_of(thread_id):
    db = os.path.expanduser('~/.codex/state_5.sqlite')
    q = f"select rollout_path from threads where id='{thread_id}'"
    r = subprocess.run(['sqlite3', '-readonly', db, q], capture_output=True, text=True)
    return r.stdout.strip()


def label(worktree):
    """The thread's name in the Codex app: the first message would title it otherwise, and a
    brief opens with the same READ-ONLY rules every time."""
    def git(*a):
        return subprocess.run(['git', '-C', worktree, *a], capture_output=True, text=True).stdout.strip()
    common = os.path.abspath(os.path.join(worktree, git('rev-parse', '--git-common-dir')))
    repo = os.path.basename(os.path.dirname(common)) if common.endswith('/.git') else os.path.basename(common)
    branch = re.sub(r'^(feature|fix|refactor)/', '', git('branch', '--show-current') or 'detached')
    return f'🧪 Test · {repo} · {branch}'


def clear_browser_denials(thread_id, home=os.path.expanduser('~')):
    """Turn 1 runs here with nobody to approve, so any browser request it makes is declined, and
    the browser plugin saves that per thread (~/.codex/browser/sessions/<thread>.toml, `denied`),
    which beats every allow once Pete opens the thread (cells-app, 2026-10-05). The thread is
    new, so everything in that file came from turn 1."""
    path = os.path.join(home, '.codex', 'browser', 'sessions', f'{thread_id}.toml')
    if os.path.exists(path):
        os.remove(path)


def queue(meta, text):
    """Put a message into the thread and open it: the Codex app runs a queued message as soon as
    it has the thread loaded, so the run happens there, where Pete watches and can approve."""
    r = subprocess.run([CODEX, 'queue', '--thread', meta['id'], '--message', text], capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(f'codex-handoff: codex queue failed: {r.stderr.strip() or r.stdout.strip()}')
    if not os.environ.get('HANDOFF_NO_OPEN'):
        subprocess.run(['open', meta['link']])
    print(meta['link'])


GO = 'Go from ship: run the plan now.'


def start(worktree, brief, out, effort='high'):
    os.makedirs(out, exist_ok=True)
    s = Server()
    t = s.call('thread/start', {'cwd': os.path.abspath(worktree), 'model': MODEL, 'sandbox': 'read-only',
                                'approvalPolicy': 'on-request', 'developerInstructions': RULES,
                                'threadSource': 'user'})['thread']
    s.call('thread/name/set', {'threadId': t['id'], 'name': label(worktree)})
    turn = s.turn(t['id'], open(brief).read(), effort)
    s.close()
    clear_browser_denials(t['id'])
    plan = next((i.get('text', '') for i in reversed(turn.get('items', [])) if i.get('type') == 'agentMessage'), '')
    open(os.path.join(out, 'plan.md'), 'w').write(plan)
    meta = {'id': t['id'], 'rollout': rollout_of(t['id']), 'link': f'codex://threads/{t["id"]}', 'out': out}
    meta['offset'] = os.path.getsize(meta['rollout']) if meta['rollout'] else 0
    json.dump(meta, open(os.path.join(out, 'thread.json'), 'w'), indent=1)
    queue(meta, GO)  # Pete wants it to just go (2026-10-05); he steers in the thread
    print(plan)


def wait(out, tick=5):
    meta = json.load(open(os.path.join(out, 'thread.json')))
    while True:
        if not os.path.exists(meta['rollout']):
            print(f'codex-handoff: {meta["rollout"]} is gone', file=sys.stderr)
            return 2
        for msg in last_message(meta['rollout'], meta.get('offset', 0)):
            m = VERDICT.search(msg)
            if m:
                open(os.path.join(out, 'last.md'), 'w').write(msg)
                print(m.group(1).lower())
                return 0
        time.sleep(tick)


def retest(out, note):
    """Queue the note into the same thread, so Pete watches the retest where he left it."""
    meta = json.load(open(os.path.join(out, 'thread.json')))
    meta['offset'] = os.path.getsize(meta['rollout'])
    json.dump(meta, open(os.path.join(out, 'thread.json'), 'w'), indent=1)
    queue(meta, 'Retest from ship. ' + open(note).read())


def selftest():
    bad = 0

    def check(name, ok):
        nonlocal bad
        bad += not ok
        print(f'  {"ok  " if ok else "FAIL"} {name}')

    def event(msg):
        return json.dumps({'type': 'event_msg', 'payload': {'type': 'task_complete', 'last_agent_message': msg}}) + '\n'

    with tempfile.TemporaryDirectory() as tmp:
        roll = os.path.join(tmp, 'rollout.jsonl')
        open(roll, 'w').write(event('1. sign in\n2. send an invite\nSay go and I start.'))
        offset = os.path.getsize(roll)
        open(roll, 'a').write(event('VERDICT: works\nEVIDENCE: shots/1.png — signed in') + '{"half a li')
        json.dump({'rollout': roll, 'offset': 0}, open(os.path.join(tmp, 'thread.json'), 'w'))
        check('a plan turn is not a verdict', not VERDICT.search(last_message(roll)[0]))
        check('wait takes the verdict turn, past a half-written line', wait(tmp, 0) == 0 and
              open(os.path.join(tmp, 'last.md')).read().startswith('VERDICT: works'))
        check('wait reads from the offset', last_message(roll, offset) == [last_message(roll)[1]])
        check('a bolded verdict counts', VERDICT.search('**VERDICT:** broken').group(1) == 'broken')
        check('a verdict mentioned mid-sentence does not',
              not VERDICT.search('I will end with a VERDICT: works line once done'))
        json.dump({'rollout': os.path.join(tmp, 'gone.jsonl')}, open(os.path.join(tmp, 'thread.json'), 'w'))
        check('a missing rollout exits 2', wait(tmp, 0) == 2)
        global CODEX
        stub, saved = os.path.join(tmp, 'codex'), CODEX
        open(stub, 'w').write(f'#!/bin/sh\nprintf "%s\\n" "$@" > {tmp}/args\n')
        os.chmod(stub, 0o755)
        open(roll, 'a').write('\n')
        json.dump({'id': 't9', 'rollout': roll, 'link': 'codex://threads/t9'}, open(os.path.join(tmp, 'thread.json'), 'w'))
        open(os.path.join(tmp, 'note.md'), 'w').write('fixed the invite button')
        CODEX, os.environ['HANDOFF_NO_OPEN'] = stub, '1'
        retest(tmp, os.path.join(tmp, 'note.md'))
        CODEX = saved
        args = open(os.path.join(tmp, 'args')).read().split('\n')
        check('a retest queues the note into the same thread', args[:3] == ['queue', '--thread', 't9'] and
              args[4] == 'Retest from ship. fixed the invite button')
        check('and waits from the end of the rollout',
              json.load(open(os.path.join(tmp, 'thread.json')))['offset'] == os.path.getsize(roll))
        repo = os.path.join(tmp, 'cells-app')
        subprocess.run(f'git init -q -b main {repo} && git -C {repo} commit -q --allow-empty -m x && '
                       f'git -C {repo} worktree add -q -b feature/eve-071 {tmp}/wt', shell=True, check=True)
        check('the thread is named for the repo and branch', label(f'{tmp}/wt') == '🧪 Test · cells-app · eve-071')
        sessions = os.path.join(tmp, '.codex', 'browser', 'sessions')
        os.makedirs(sessions)
        open(os.path.join(sessions, 't1.toml'), 'w').write('[origins]\ndenied = ["http://app.localhost:3266"]\n')
        clear_browser_denials('t1', tmp)
        clear_browser_denials('t2', tmp)
        check("turn 1's saved browser decline is cleared, and a thread with none is fine",
              not os.path.exists(os.path.join(sessions, 't1.toml')))
        check('turn 1 is told to touch nothing that needs the network', 'no `curl`, browser' in RULES)
        check('the phone is the native app, never its Safari', 'Never test a web page in the phone' in RULES)
    print(f'codex-handoff self-test: {bad} failed')
    return 1 if bad else 0


if __name__ == '__main__':
    a = sys.argv[1:]
    if a == ['--selftest']:
        sys.exit(selftest())
    elif a and a[0] == 'start' and len(a) in (4, 5):
        start(*a[1:])
    elif a and a[0] == 'wait' and len(a) == 2:
        sys.exit(wait(a[1]))
    elif a and a[0] == 'retest' and len(a) == 3:
        retest(*a[1:])
    else:
        sys.exit(__doc__)
