#!/usr/bin/env python3
"""TEST with Pete in the Codex app: hand the brief to a Codex thread, then wait for its verdict.

  codex-handoff.py start  <worktree> <brief.md> <out-dir> [effort]   first turn drafts the test
                                                    plan, then the thread opens in the Codex app
  codex-handoff.py wait   <out-dir>                 block until a turn ends on a VERDICT line
  codex-handoff.py retest <out-dir> <note.md>       a fix round: the note goes into the same thread,
                                                    or to the clipboard (exit 3) while the app holds it
  codex-handoff.py --selftest

`start` runs its own `codex app-server` over stdio for one turn and exits; the thread lives
on in ~/.codex, and `codex://threads/<id>` opens it in the desktop app, whose own app-server
resumes it. Pete and Codex revise the plan there, and Codex tests with whatever the app
gives it: the browser, computer use, his iPhone. <out-dir> gets thread.json (id, rollout
path, link) and plan.md; `wait` writes last.md, prints the verdict and exits 0, or 2 when
the thread is gone. The verdict travels in the thread's rollout, so the tester never has
to write a file. The daemon's control socket (`app-server proxy`) does not answer bare
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

Turn 1: read the brief, check the app is reachable, and reply with a numbered test plan:
each flow, what you will see when it passes, and where you run it (browser, computer use,
iPhone PM or a simulator). Then stop. Pete revises the plan with you; start testing when he
says go.

While testing: use the app the way Pete would, and show him what you see. Never edit, create
or delete a file in the repo and never fix anything: ship fixes. Screenshots go in the shots
path the brief names.

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


def start(worktree, brief, out, effort='high'):
    os.makedirs(out, exist_ok=True)
    s = Server()
    t = s.call('thread/start', {'cwd': os.path.abspath(worktree), 'model': MODEL, 'sandbox': 'read-only',
                                'approvalPolicy': 'on-request', 'developerInstructions': RULES,
                                'threadSource': 'user'})['thread']
    turn = s.turn(t['id'], open(brief).read(), effort)
    s.close()
    plan = next((i.get('text', '') for i in reversed(turn.get('items', [])) if i.get('type') == 'agentMessage'), '')
    open(os.path.join(out, 'plan.md'), 'w').write(plan)
    meta = {'id': t['id'], 'rollout': rollout_of(t['id']), 'link': f'codex://threads/{t["id"]}', 'out': out}
    meta['offset'] = os.path.getsize(meta['rollout']) if meta['rollout'] else 0
    json.dump(meta, open(os.path.join(out, 'thread.json'), 'w'), indent=1)
    if not os.environ.get('HANDOFF_NO_OPEN'):
        subprocess.run(['open', meta['link']])
    print(meta['link'])
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
    meta = json.load(open(os.path.join(out, 'thread.json')))
    meta['offset'] = os.path.getsize(meta['rollout'])
    json.dump(meta, open(os.path.join(out, 'thread.json'), 'w'), indent=1)
    text = 'Retest from ship. ' + open(note).read()
    s = Server()
    try:
        s.call('thread/resume', {'threadId': meta['id']})
    except SystemExit as e:
        if 'active writer' not in str(e):
            raise
        # The Codex app holds the thread, and only one writer may: Pete pastes the note.
        s.close()
        subprocess.run(['pbcopy'], input=text, text=True)
        print(f'{meta["link"]} is open in the Codex app: the retest note is on the clipboard to paste there')
        if not os.environ.get('HANDOFF_NO_OPEN'):
            subprocess.run(['open', meta['link']])
        return 3
    s.turn(meta['id'], text, 'high')
    s.close()
    if not os.environ.get('HANDOFF_NO_OPEN'):
        subprocess.run(['open', meta['link']])
    print(meta['link'])


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
        sys.exit(retest(*a[1:]))
    else:
        sys.exit(__doc__)
