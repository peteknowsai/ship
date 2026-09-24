#!/usr/bin/env python3
"""Pick each BUILD task's engine from its difficulty, and keep the ledger that judges the pick.

  route.py plan <plan.md>        rank the plan's tasks with Jev; JSON on stdout, a table on stderr
  route.py log key=value ...     append one task's outcome to the ledger
  route.py report                the ledger as a table by engine and difficulty
  route.py --selftest

The ladder (Pete, 2026-09-24) ranks the routable tasks by Jev's difficulty score: the
bottom half goes to Astra, the 50th to 75th percentile to Opus 5.5, the top quarter to
Fable. A task whose heading says (driver) or (inline) stays with the driver and is not
ranked. Jev unreachable or no key: every task goes to Astra and `fallback` says why,
because a router must never stop a build.

The key comes from TYPESAFE_API_KEY, else the macOS keychain (service "typesafe").
The ledger is ~/.claude/ship-ledger.jsonl, or SHIP_LEDGER.
"""
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.request

JEV_URL = 'https://api.typesafe.ai/v1/systemone'
LEVELS = [
    'Transcription: the task text already contains the code to write; one file, no decisions left for the worker.',
    'Contained change: one or two files, following a pattern the repo already has; the tests named in the task prove it.',
    'Integration: several files wired together; the worker has to find where things connect and choose the shape itself.',
    'Cross-cutting or stateful: concurrency, persistence, protocols, lifecycles or changes that ripple through callers; '
    'mistakes tend to show only at runtime.',
    'Novel and risky: a mechanism with no precedent in the repo, a security, auth or money boundary, or subtle failure '
    'modes that need careful reasoning to get right.',
]
QUESTION = 'How hard is this coding task for an AI coding agent to complete correctly on the first attempt?'
# Jev takes 64k tokens per request, and pasted code runs near 3 characters a token. Each
# task's question repeats the rubric (~800 characters), so a request packs tasks until
# text plus questions reach this, and a big plan takes several requests. The scores sit
# on one fixed rubric, so tasks from different requests still rank against each other.
REQUEST_CHARS = 120_000
TASK_CHARS = 20_000
QUESTION_CHARS = 800


def ledger_path():
    return os.environ.get('SHIP_LEDGER') or os.path.expanduser('~/.claude/ship-ledger.jsonl')


def parse_tasks(text):
    """`## Task` / `### Task` headings outside code fences; a plan pastes code into its tasks."""
    tasks, fenced = [], False
    for line in text.splitlines():
        if line.lstrip().startswith(('```', '~~~')):
            fenced = not fenced
        heading = None if fenced else re.match(r'#{2,3} (Task\b.*)', line)
        if heading:
            title = heading.group(1).strip()
            tasks.append({'n': len(tasks) + 1, 'title': title, 'lines': [],
                          'driver': bool(re.search(r'\((driver|inline)\)', title, re.I))})
        elif tasks:
            tasks[-1]['lines'].append(line)
    for t in tasks:
        t['body'] = '\n'.join(t.pop('lines')).strip()
    return tasks


def api_key():
    key = os.environ.get('TYPESAFE_API_KEY')
    if key is not None or os.environ.get('ROUTE_NO_KEYCHAIN'):
        return key or None
    try:
        return subprocess.check_output(['security', 'find-generic-password', '-s', 'typesafe', '-w'],
                                       text=True, stderr=subprocess.DEVNULL).strip() or None
    except (OSError, subprocess.CalledProcessError):
        return None


def batches(routable):
    batch, size = [], 0
    for t in routable:
        cost = min(len(t['title']) + len(t['body']) + 1, TASK_CHARS) + QUESTION_CHARS
        if batch and size + cost > REQUEST_CHARS:
            yield batch
            batch, size = [], 0
        batch.append(t)
        size += cost
    if batch:
        yield batch


def ask_jev(routable):
    """Scores by task number, and the model that gave them. Raises on any failure."""
    if os.environ.get('ROUTE_RESPONSE'):  # the self-test's canned reply
        replies = [json.load(open(os.environ['ROUTE_RESPONSE']))]
    else:
        key = api_key()
        if not key:
            raise RuntimeError('no TypeSafe key (TYPESAFE_API_KEY or keychain service "typesafe")')
        replies = []
        for batch in batches(routable):
            state = {'tasks': {f"t{t['n']}": (t['title'] + '\n' + t['body'])[:TASK_CHARS] for t in batch}}
            questions = {f"t{t['n']}": {'type': 'score', 'criteria': LEVELS,
                                        'instructions': {'task': f"`tasks.t{t['n']}`", 'question': QUESTION}}
                         for t in batch}
            body = json.dumps({'model': 'jev-latest', 'state': state, 'questions': questions}).encode()
            request = urllib.request.Request(JEV_URL, body, {'Authorization': f'Bearer {key}',
                                                             'Content-Type': 'application/json'})
            with urllib.request.urlopen(request, timeout=30) as response:
                replies.append(json.load(response))
    answers = {k: v for reply in replies for k, v in reply['answers'].items()}
    scores = {}
    for t in routable:
        answer = answers[f"t{t['n']}"]
        if not isinstance(answer.get('score'), (int, float)) or isinstance(answer['score'], bool):
            raise ValueError(f"t{t['n']}: no numeric score in {answer!r}"[:200])
        scores[t['n']] = answer
    return scores, replies[0].get('model')


def assign(routable, scores):
    """The ladder: rank by score, ties in plan order. The easier half goes to Astra
    (rounded up), the hardest quarter to Fable (rounded down, but the hardest task
    always), and Opus takes what is between. Rounding favours the plentiful engine."""
    ranked = sorted(routable, key=lambda t: (scores[t['n']]['score'], t['n']))
    n = len(ranked)
    fable = max(1, n // 4)
    astra = min(n - fable, (n + 1) // 2)
    return {t['n']: 'astra' if i < astra else 'fable' if i >= n - fable else 'opus'
            for i, t in enumerate(ranked)}


def plan(path):
    try:
        tasks = parse_tasks(open(path).read())
    except OSError as error:
        raise SystemExit(f'route: {error}')
    if not tasks:
        raise SystemExit(f'route: no "### Task" headings in {path}')
    routable = [t for t in tasks if not t['driver']]
    fallback, model, scores, engines = None, None, {}, {}
    if routable:
        try:
            scores, model = ask_jev(routable)
            engines = assign(routable, scores)
        except Exception as error:  # a router must never stop a build
            fallback = f'{type(error).__name__}: {error}'
            scores, engines = {}, {t['n']: 'astra' for t in routable}
    out = []
    for t in tasks:
        s = scores.get(t['n'], {})
        out.append({'n': t['n'], 'title': t['title'], 'engine': 'driver' if t['driver'] else engines[t['n']],
                    'score': s.get('score'), 'confidence': s.get('confidence')})
    for row in out:
        score = '  -  ' if row['score'] is None else f"{row['score']:.2f}"
        print(f"{row['engine']:6} {score}  {row['title'][:80]}", file=sys.stderr)
    if fallback:
        print(f'route: Jev unavailable, every task on Astra ({fallback})', file=sys.stderr)
    return {'model': model, 'fallback': fallback, 'tasks': out}


def coerce(value):
    if value.lower() in ('true', 'false'):
        return value.lower() == 'true'
    for kind in (int, float):
        try:
            return kind(value)
        except ValueError:
            pass
    return value


def log(pairs):
    if not pairs:
        raise SystemExit('route log: nothing to log; pass key=value pairs')
    row = {'ts': time.strftime('%Y-%m-%dT%H:%M:%S')}
    for pair in pairs:
        key, sep, value = pair.partition('=')
        if not sep:
            raise SystemExit(f'route log: "{pair}" is not key=value')
        row[key] = coerce(value)
    with open(ledger_path(), 'a') as ledger:
        ledger.write(json.dumps(row) + '\n')
    return row


def band(score):
    if not isinstance(score, (int, float)):
        return 'unscored'
    return 'easy <1.5' if score < 1.5 else 'mid <2.5' if score < 2.5 else 'hard 2.5+'


def report():
    rows = []
    try:
        for line in open(ledger_path()):
            try:
                rows.append(json.loads(line))
            except ValueError:
                pass  # a half-written line from a concurrent ship; the rest still counts
    except FileNotFoundError:
        pass
    groups = {}
    for row in rows:
        groups.setdefault((row.get('engine', '?'), band(row.get('score'))), []).append(row)
    lines = [f"{'engine':7} {'difficulty':10} {'tasks':>5} {'first pass':>10} {'fix rounds':>10} {'minutes':>8}"]
    for (engine, difficulty), group in sorted(groups.items()):
        def mean(key):
            values = [r[key] for r in group if isinstance(r.get(key), (int, float)) and not isinstance(r[key], bool)]
            return f'{sum(values) / len(values):.1f}' if values else '-'
        passed = [r['gates_first_pass'] for r in group if isinstance(r.get('gates_first_pass'), bool)]
        rate = f'{100 * sum(passed) // len(passed)}%' if passed else '-'
        minutes = mean('seconds')
        minutes = minutes if minutes == '-' else f'{float(minutes) / 60:.1f}'
        lines.append(f"{engine:7} {difficulty:10} {len(group):>5} {rate:>10} {mean('fix_rounds'):>10} {minutes:>8}")
    return '\n'.join(lines)


def selftest():
    fails = 0

    def check(name, ok):
        nonlocal fails
        print(f"  {'ok  ' if ok else 'FAIL'} {name}")
        fails += 0 if ok else 1

    with tempfile.TemporaryDirectory() as tmp:
        plan_md = os.path.join(tmp, 'plan.md')
        titles = ['Task 1: docs', 'Task 2: hard socket', 'Task 3: glue (driver)', 'Task 4: medium wiring',
                  'Task 5: easy rename', 'Task 6: auth boundary', 'Task 7: small test', 'Task 8: mid state',
                  'Task 9: one file']
        open(plan_md, 'w').write('# Plan\n\n' + ''.join(f'### {t}\n\nbody {i}\n\n' for i, t in enumerate(titles)))
        scores = {1: 0.8, 2: 3.4, 4: 2.1, 5: 0.9, 6: 3.6, 7: 1.0, 8: 2.9, 9: 1.2}
        reply = os.path.join(tmp, 'reply.json')
        json.dump({'model': 'jev-test', 'answers': {f't{n}': {'score': s, 'confidence': 0.7}
                                                    for n, s in scores.items()}}, open(reply, 'w'))
        os.environ.update(ROUTE_RESPONSE=reply, SHIP_LEDGER=os.path.join(tmp, 'ledger.jsonl'))
        got = {t['n']: t['engine'] for t in plan(plan_md)['tasks']}
        check('the driver task stays with the driver', got[3] == 'driver')
        check('bottom half on Astra', sorted(n for n, e in got.items() if e == 'astra') == [1, 5, 7, 9])
        check('50th to 75th on Opus', sorted(n for n, e in got.items() if e == 'opus') == [4, 8])
        check('top quarter on Fable', sorted(n for n, e in got.items() if e == 'fable') == [2, 6])
        for name, answers in [('bare numbers', {f't{n}': 1 for n in scores}),
                              ('string scores', {f't{n}': {'score': str(s)} for n, s in scores.items()})]:
            json.dump({'answers': answers}, open(reply, 'w'))
            result = plan(plan_md)
            check(f'a reply of {name} falls back instead of crashing', result['fallback'] and
                  {t['engine'] for t in result['tasks'] if t['n'] != 3} == {'astra'})
        few = os.path.join(tmp, 'few.md')
        open(few, 'w').write(''.join(f'### Task {n}: t\n\n```md\n### Task 99: an example inside a fence\n```\n\n'
                                     for n in range(1, 6)))
        json.dump({'answers': {f't{n}': {'score': n} for n in range(1, 6)}}, open(reply, 'w'))
        got = [t['engine'] for t in plan(few)['tasks']]
        check('a heading inside a code fence is not a task', len(got) == 5)
        check('five tasks round toward Astra: 3, 1, 1', got == ['astra'] * 3 + ['opus', 'fable'])
        del os.environ['ROUTE_RESPONSE']
        os.environ.update(TYPESAFE_API_KEY='', ROUTE_NO_KEYCHAIN='1')
        result = plan(plan_md)
        check('no key falls back to Astra', result['fallback'] and
              {t['engine'] for t in result['tasks'] if t['n'] != 3} == {'astra'})
        log(['repo=ship', 'task=2', 'engine=fable', 'score=3.4', 'seconds=300', 'fix_rounds=1', 'gates_first_pass=false'])
        open(ledger_path(), 'a').write('{"half a line\n')
        log(['repo=ship', 'task=1', 'engine=astra', 'score=0.8', 'seconds=120', 'fix_rounds=0', 'gates_first_pass=True'])
        table = report()
        check('the ledger reports by engine and difficulty, past a broken line',
              'fable   hard 2.5+      1         0%        1.0      5.0' in table and
              'astra   easy <1.5      1       100%' in table)
    print(f'route self-test: {fails} failed')
    return fails == 0


if __name__ == '__main__':
    args = sys.argv[1:]
    if args == ['--selftest']:
        sys.exit(0 if selftest() else 1)
    if len(args) == 2 and args[0] == 'plan':
        print(json.dumps(plan(args[1]), indent=1))
    elif args and args[0] == 'log':
        log(args[1:])
    elif args == ['report']:
        print(report())
    else:
        sys.exit(__doc__)
