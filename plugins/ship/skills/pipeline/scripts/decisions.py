#!/usr/bin/env python3
"""Settled calls per repo, so a later ship doesn't re-ask Pete what he already decided.

  decisions.py recent [N]                    the N newest active decisions (default 5)
  decisions.py log '<json>'                  record one: {"decision","rationale","source"}
  decisions.py supersede <id> '<json>'       record a reversal; the old one stops showing
  decisions.py --selftest

Run from inside the repo. Each repo has one append-only event log,
~/.claude/ship-decisions/<owner>-<repo>.jsonl (SHIP_DECISIONS overrides the directory),
named from the origin remote, else from the main checkout's folder. The format is the
one gstack's decision store used, so its history migrated as is.
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


def recent(path, n):
    lines = []
    for e in sorted(active(path), key=lambda e: e.get('date', ''), reverse=True)[:n]:
        lines.append(f"- {e['decision']} ({e.get('source', '?')}, {e.get('date', '')[:10]}) [{e['id'][:8]}]")
        if e.get('rationale'):
            lines.append(f"  why: {e['rationale']}")
    return '\n'.join(lines)


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
    print(f'decisions self-test: {fails} failed')
    return fails == 0


if __name__ == '__main__':
    args = sys.argv[1:]
    if args == ['--selftest']:
        sys.exit(0 if selftest() else 1)
    if args and args[0] == 'recent' and len(args) <= 2:
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
