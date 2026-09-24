#!/usr/bin/env python3
"""Settled calls per repo, so a later ship doesn't re-ask Pete what he already decided.

  decisions.py relevant "<idea>" [N]         the N decisions (default 6) that bear on the idea
  decisions.py recent [N]                    the N newest active decisions (default 5)
  decisions.py log '<json>'                  record one: {"decision","rationale","source"}
  decisions.py supersede <id> '<json>'       record a reversal; the old one stops showing
  decisions.py --selftest

Run from inside the repo. Each repo has one append-only event log,
~/.claude/ship-decisions/<owner>-<repo>.jsonl (SHIP_DECISIONS overrides the directory),
named from the origin remote, else from the main checkout's folder. The format is the
one gstack's decision store used, so its history migrated as is.

`relevant` asks Jev (route.py's key and endpoint) to score every active decision
against the idea in one request, because the newest five hide the old call that
settles the thing being changed. Any failure falls back to `recent`, so recall never
blocks a run.
"""
import datetime
import json
import os
import re
import subprocess
import sys
import tempfile
import uuid


def store():
    def run(*args):
        return subprocess.run(args, capture_output=True, text=True).stdout.strip()
    url = run('git', 'remote', 'get-url', 'origin')
    match = re.search(r'[:/]([^/:]+)/([^/]+?)(?:\.git)?/?$', url)
    if match:
        slug = f'{match.group(1)}-{match.group(2)}'
    else:
        common = run('git', 'rev-parse', '--path-format=absolute', '--git-common-dir')
        slug = os.path.basename(os.path.dirname(common)) if common else os.path.basename(os.getcwd())
    slug = re.sub(r'[^A-Za-z0-9._-]', '-', slug.replace('.', '-'))
    root = os.environ.get('SHIP_DECISIONS') or os.path.expanduser('~/.claude/ship-decisions')
    os.makedirs(root, exist_ok=True)
    return os.path.join(root, f'{slug}.jsonl')


def events(path):
    try:
        lines = open(path).read().splitlines()
    except FileNotFoundError:
        return []
    out = []
    for line in lines:
        try:
            out.append(json.loads(line))
        except ValueError:
            pass  # a half-written line; the rest still counts
    return out


def active(path):
    evs = events(path)
    retired = {e.get('supersedes') for e in evs if e.get('kind') in ('supersede', 'redact')}
    return [e for e in evs if e.get('kind') == 'decide' and e.get('id') not in retired]


def append(path, event):
    with open(path, 'a') as log:
        log.write(json.dumps(event) + '\n')


def decide(raw, supersedes=None):
    try:
        payload = json.loads(raw)
    except ValueError:
        payload = None
    if not isinstance(payload, dict):
        raise SystemExit('decisions: the decision must be a JSON object')
    if not str(payload.get('decision', '')).strip() or not str(payload.get('rationale', '')).strip():
        raise SystemExit('decisions: "decision" and "rationale" are both required')
    for key in ('id', 'kind', 'date', 'supersedes'):  # the store owns these
        payload.pop(key, None)
    event = {'scope': 'repo', 'source': 'user', **payload, 'id': str(uuid.uuid4()), 'kind': 'decide',
             'date': datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds')}
    if supersedes:
        event['supersedes'] = supersedes
    return event


def show(chosen):
    lines = []
    for e in chosen:
        lines.append(f"- {e['decision']} ({e.get('source', '?')}, {e.get('date', '')[:10]}) [{e['id'][:8]}]")
        if e.get('rationale'):
            lines.append(f"  why: {e['rationale']}")
    return '\n'.join(lines)


def recent(path, n):
    return show(sorted(active(path), key=lambda e: e.get('date', ''), reverse=True)[:n])


RELEVANCE = [
    'Unrelated to the idea',
    'Same area, but does not settle anything the idea needs',
    'Settles a choice the idea will face, or rules out an approach to it',
]
BATCH = 150  # decisions per Jev request, well under its 64k-token limit


def scores(idea, decisions):
    """Jev's relevance score for each decision, in order. Raises on any failure."""
    if os.environ.get('DECISIONS_RESPONSE'):  # the self-test's canned reply
        answers = json.load(open(os.environ['DECISIONS_RESPONSE']))['answers']
    else:
        import urllib.request
        import route
        key = route.api_key()
        if not key:
            raise RuntimeError('no TypeSafe key')
        answers = {}
        for start in range(0, len(decisions), BATCH):
            chunk = {f'd{i}': decisions[i]['decision'][:2000]
                     for i in range(start, min(start + BATCH, len(decisions)))}
            questions = {k: {'type': 'score', 'criteria': RELEVANCE, 'instructions': {
                'decision': f'`decisions.{k}`', 'idea': '`idea`',
                'question': 'Does this settled decision constrain or answer something the new idea will have to decide?'}}
                for k in chunk}
            body = json.dumps({'model': 'jev-latest', 'state': {'idea': idea, 'decisions': chunk},
                               'questions': questions}).encode()
            request = urllib.request.Request(route.JEV_URL, body, {'Authorization': f'Bearer {key}',
                                                                   'Content-Type': 'application/json'})
            with urllib.request.urlopen(request, timeout=30) as response:
                answers.update(json.load(response)['answers'])
    out = []
    for i in range(len(decisions)):
        score = answers[f'd{i}']['score']
        if not isinstance(score, (int, float)) or isinstance(score, bool):
            raise ValueError(f'd{i}: no numeric score')
        out.append(score)
    return out


def relevant(path, idea, n):
    decisions = active(path)
    if not decisions:
        return ''
    try:
        ranked = sorted(zip(scores(idea, decisions), decisions), key=lambda p: -p[0])
    except Exception as error:  # recall must never block a run
        print(f'decisions: Jev unavailable ({type(error).__name__}: {error}); showing the newest instead',
              file=sys.stderr)
        return recent(path, n)
    return show(e for _, e in ranked[:n])


def full_id(path, prefix):
    matches = [e['id'] for e in active(path) if e['id'].startswith(prefix)]
    if len(matches) != 1:
        raise SystemExit(f'decisions: "{prefix}" matches {len(matches)} active decisions; give more of the id')
    return matches[0]


def selftest():
    fails = 0

    def check(name, ok):
        nonlocal fails
        print(f"  {'ok  ' if ok else 'FAIL'} {name}")
        fails += 0 if ok else 1

    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, 'd.jsonl')
        first = decide('{"decision":"A","rationale":"because"}')
        append(path, first)
        check('a logged decision shows', '- A (user' in recent(path, 5))
        replacement = decide('{"decision":"B","rationale":"changed mind"}', first['id'])
        append(path, replacement)
        append(path, {'kind': 'supersede', 'supersedes': first['id'], 'id': str(uuid.uuid4())})
        shown = recent(path, 5)
        check('a superseded decision stops showing', '- B' in shown and '- A' not in shown)
        check('a short id prefix resolves', full_id(path, replacement['id'][:8]) == replacement['id'])
        open(path, 'a').write('{"half\n')
        check('a broken line is skipped', len(active(path)) == 1)
        for name, raw in [('without a rationale', '{"decision":"no why"}'), ('that is not an object', '["a"]')]:
            try:
                decide(raw)
                check(f'a decision {name} is refused', False)
            except SystemExit:
                check(f'a decision {name} is refused', True)
        forged = decide('{"decision":"C","rationale":"r","id":"aaaa","kind":"note"}')
        check('a payload cannot set its own id or kind', forged['id'] != 'aaaa' and forged['kind'] == 'decide')

        many = os.path.join(tmp, 'many.jsonl')
        for i, text in enumerate(['old voice rule', 'billing', 'newest thing', 'sidebar']):
            append(many, {**decide(json.dumps({'decision': text, 'rationale': 'r'})), 'date': f'2026-09-0{i + 1}'})
        reply = os.path.join(tmp, 'reply.json')
        json.dump({'answers': {'d0': {'score': 1.9}, 'd1': {'score': 0.1},
                               'd2': {'score': 0.2}, 'd3': {'score': 0.3}}}, open(reply, 'w'))
        os.environ['DECISIONS_RESPONSE'] = reply
        check('relevance beats recency', relevant(many, 'pick a voice', 1).startswith('- old voice rule'))
        json.dump({'answers': {'d0': 1}}, open(reply, 'w'))
        check('a bad reply falls back to the newest', relevant(many, 'pick a voice', 1).startswith('- sidebar'))
        del os.environ['DECISIONS_RESPONSE']
    print(f'decisions self-test: {fails} failed')
    return fails == 0


if __name__ == '__main__':
    args = sys.argv[1:]
    if args == ['--selftest']:
        sys.exit(0 if selftest() else 1)
    if args and args[0] == 'relevant' and len(args) in (2, 3):
        if len(args) == 3 and not args[2].isdigit():
            sys.exit('decisions: relevant takes a positive count')
        print(relevant(store(), args[1], int(args[2]) if len(args) == 3 else 6))
    elif args and args[0] == 'recent' and len(args) <= 2:
        if len(args) == 2 and not args[1].isdigit():
            sys.exit('decisions: recent takes a positive count')
        print(recent(store(), int(args[1]) if len(args) == 2 else 5))
    elif len(args) == 2 and args[0] == 'log':
        append(store(), decide(args[1]))
    elif len(args) == 3 and args[0] == 'supersede':
        path = store()
        old = full_id(path, args[1])
        append(path, decide(args[2], old))
        append(path, {'id': str(uuid.uuid4()), 'kind': 'supersede', 'supersedes': old,
                      'date': datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds')})
    else:
        sys.exit(__doc__)
