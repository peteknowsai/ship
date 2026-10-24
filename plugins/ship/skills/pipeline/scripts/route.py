#!/usr/bin/env python3
"""Count a plan's BUILD tasks, and keep the ledger that judges how each was built.

  route.py plan <plan.md>        list the plan's tasks; JSON on stdout, a table on stderr
  route.py log key=value ...     append one task's outcome to the ledger
Inside a ship, `plan` moves the stage marker to build:0:<tasks> and each `log` counts one
task done, so the status line reaches BUILD without the driver remembering to say so.
`plan` also saves the task list to .ship-route.json beside the marker, and `log task=<n>`
fills that task's `routed` engine from it, so a task the driver handed to a subagent
shows as engine=opus, routed=driver.
  route.py log review=<opus|...> real=<n> false=<n> only=<n> seconds=<n> ...
                                 append one REVIEW reader's tally for the ship: findings
                                 that were real, false alarms, and real ones another
                                 reader missed; it never counts as a BUILD task
  route.py report                the ledger as a table by engine and difficulty, by
                                 pool, then the reviewers'
  route.py quota                 the pools, one line each (quota.py --table)
  route.py reader                the model that reads the branch at REVIEW (opus)
  route.py --selftest

Opus 5.5 only (Pete, 2026-10-24): the driver builds every task in its own loop, so `plan`
ranks nothing. The difficulty ranker that split tasks across Opus, Wonder and Sonnet is in
git history (`git log -S ask_scores`). decisions.py still asks SubQ, else Jev, through
`decide` below.

Keys: SUBQ_API_KEY else keychain service "subq"; TYPESAFE_API_KEY else keychain "typesafe".
The ledger is ~/.claude/ship-ledger.jsonl, or SHIP_LEDGER.
"""
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # quota.py is a sibling, whoever imports us
import quota  # noqa: E402

# Decision models, asked in order: the same /v1/systemone shape, so one call fits both.
# SubQ answers at most 16 questions a request; Jev reads 64k tokens, SubQ 384k.
DECIDERS = [
    {'name': 'SubQ', 'url': 'https://api.subq.ai/v1/systemone', 'model': 'subq-snap-preview',
     'env': 'SUBQ_API_KEY', 'keychain': 'subq', 'questions': 16},
    {'name': 'Jev', 'url': 'https://api.typesafe.ai/v1/systemone', 'model': 'jev-latest',
     'env': 'TYPESAFE_API_KEY', 'keychain': 'typesafe', 'questions': 1000},
]
# Old ledger rows keep their pool; only opus and driver build since 2026-10-24.
POOL = {'opus': 'anthropic', 'driver': 'anthropic', 'wonder': 'muse', 'sonnet': 'anthropic',
        'fable': 'fable', 'astra': 'openai', 'sol': 'openai', 'spark': 'muse'}
# Jev, the smaller window, takes 64k tokens per request, and pasted text runs near 3
# characters a token, so a request packs items until text plus questions reach this.
REQUEST_CHARS = 120_000
QUESTION_CHARS = 800


def ledger_path():
    return os.environ.get('SHIP_LEDGER') or os.path.expanduser('~/.claude/ship-ledger.jsonl')


def stage_marker(start):
    """The run's .ship-stage: the repo holding `start`, else the session's cross-repo pointer."""
    roots = []
    try:
        roots.append(subprocess.check_output(['git', '-C', start, 'rev-parse', '--show-toplevel'],
                                             text=True, stderr=subprocess.DEVNULL).strip())
    except (OSError, subprocess.CalledProcessError):
        pass
    session = os.environ.get('CLAUDE_CODE_SESSION_ID')
    pointer = os.path.expanduser(f'~/.claude/ship-active/{session}')
    if session and os.path.isfile(pointer):
        roots.append(open(pointer).read().strip())
    for root in roots:
        path = os.path.join(root, '.ship-stage')
        if os.path.isfile(path):
            return path
    return None


def route_file(start):
    marker = stage_marker(start)
    return marker and os.path.join(os.path.dirname(marker), '.ship-route.json')


def mark_build(start, task=None, total=None):
    """build:0:<total> when routing ends, then build:<distinct tasks logged>:<total>, so a
    task logged twice (a fix round) counts once and task=4,10 counts two. Outside a ship,
    nothing."""
    path = stage_marker(start)
    if not path:
        return
    current = re.match(r'build:(\d+):(\d+)', open(path).read().strip())
    if total is not None and not current:  # a re-route mid-build keeps the count
        open(path, 'w').write(f'build:0:{total}')
    elif task is not None and current:
        m = int(current.group(2))
        done_file = os.path.join(os.path.dirname(path), '.ship-done')
        seen = set(open(done_file).read().split()) if os.path.isfile(done_file) else set()
        before = len(seen)
        seen.update(t.strip() for t in str(task).split(',') if t.strip())
        if len(seen) == before:
            return
        open(done_file, 'w').write('\n'.join(sorted(seen)) + '\n')
        n = min(len(seen), m)
        open(path, 'w').write(f'build:{n}:{m}')
        if n == m:  # the muse-tools ship sat on build:32:32 through review, test and land
            print(f'all {m} tasks logged: BUILD is done, so the next command is '
                  f'stage.sh {os.path.dirname(path)} review', file=sys.stderr)


def parse_tasks(text):
    """`## Task` / `### Task` headings outside code fences; a plan pastes code into its tasks."""
    tasks, fenced = [], False
    for line in text.splitlines():
        if line.lstrip().startswith(('```', '~~~')):
            fenced = not fenced
        heading = None if fenced else re.match(r'#{2,3} (Task\s+\d+[a-z]?\b.*)', line)
        if heading:
            title = heading.group(1).strip()
            label = re.match(r'Task\s+(\d+[a-z]?)', title).group(1)  # "3b" for a split task
            n = int(re.match(r'\d+', label).group(0))  # the plan's own number, gaps and all
            if any(t['n'] == n for t in tasks):
                n = max(t['n'] for t in tasks) + 1
            tasks.append({'n': n, 'label': label, 'title': title, 'lines': []})
        elif tasks:
            tasks[-1]['lines'].append(line)
    for t in tasks:
        t['body'] = '\n'.join(t.pop('lines')).strip()
    return tasks


def api_key(decider):
    key = os.environ.get(decider['env'])
    if key is not None or os.environ.get('ROUTE_NO_KEYCHAIN'):
        return key or None
    try:
        return subprocess.check_output(['security', 'find-generic-password', '-s', decider['keychain'], '-w'],
                                       text=True, stderr=subprocess.DEVNULL).strip() or None
    except (OSError, subprocess.CalledProcessError):
        return None


def batches(items, cost, most):
    """Split items so each request stays under REQUEST_CHARS and `most` questions."""
    batch, size = [], 0
    for item in items:
        if batch and (size + cost(item) > REQUEST_CHARS or len(batch) == most):
            yield batch
            batch, size = [], 0
        batch.append(item)
        size += cost(item)
    if batch:
        yield batch


def decide(items, build, cost=lambda item: QUESTION_CHARS):
    """Ask the first decision model that answers about every item; build(batch) gives one
    request's (state, questions). Returns (answers by question name, model). Raises when
    none answers."""
    failures = []
    for decider in DECIDERS:
        key = api_key(decider)
        if not key:
            failures.append(f"{decider['name']}: no key (env {decider['env']} or keychain \"{decider['keychain']}\")")
            continue
        try:
            answers, model = {}, None
            for batch in batches(items, cost, decider['questions']):
                state, questions = build(batch)
                body = json.dumps({'model': decider['model'], 'state': state, 'questions': questions}).encode()
                request = urllib.request.Request(decider['url'], body, {'Authorization': f'Bearer {key}',
                                                                        'Content-Type': 'application/json'})
                with urllib.request.urlopen(request, timeout=30) as response:
                    reply = json.load(response)
                answers.update(reply['answers'])
                model = model or reply.get('model') or decider['model']
            return answers, model
        except Exception as error:
            why = 'out of credits; tell Pete now' if '402' in str(error) else f'{type(error).__name__}: {error}'
            failures.append(f"{decider['name']}: {why}")
            print(f"route: {decider['name']} failed ({why})", file=sys.stderr)
    raise RuntimeError('; '.join(failures))


def plan(path):
    try:
        tasks = parse_tasks(open(path).read())
    except OSError as error:
        raise SystemExit(f'route: {error}')
    if not tasks:
        raise SystemExit(f'route: no "### Task" headings in {path}')
    where = os.path.dirname(os.path.abspath(path))
    out = [{'n': t['n'], 'label': t['label'], 'title': t['title'], 'engine': 'driver'} for t in tasks]
    for row in out:
        print(f"{row['label']:4} {row['title'][:80]}", file=sys.stderr)
    result = {'tasks': out}
    saved = route_file(where)
    if saved:
        try:
            with open(saved, 'w') as f:
                json.dump(result, f)
        except OSError as error:  # the table on stdout still carries the tasks
            print(f'route: could not save {saved}: {error}', file=sys.stderr)
    mark_build(where, total=len(tasks))
    return result


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
    if 'review' in row and isinstance(row.get('only'), int) and isinstance(row.get('real'), int) \
            and row['only'] > row['real']:
        raise SystemExit(f"route log: only={row['only']} is more than real={row['real']}")
    if 'review' in row and isinstance(row.get('owned'), int) and isinstance(row.get('real'), int) \
            and row['owned'] > row['real']:
        raise SystemExit(f"route log: owned={row['owned']} is more than real={row['real']}")
    out = row.pop('out', None)  # a wrapper's out-dir: its `seconds` file is the run's own wall time
    if out and 'seconds' not in row:
        try:
            row['seconds'] = int(open(os.path.join(str(out), 'seconds')).read().strip())
        except (OSError, ValueError):
            print(f'route log: no seconds file in {out}, so seconds is left out', file=sys.stderr)
    saved = route_file(os.getcwd())
    picked = None
    if saved and os.path.isfile(saved) and 'task' in row:
        try:
            saved_tasks = json.load(open(saved))['tasks']  # task=3b finds its label, task=4 its number
            picked = ({t['label']: t for t in saved_tasks if t.get('label')}.get(str(row['task']))
                      or {t['n']: t for t in saved_tasks}.get(row['task']))
        except (OSError, ValueError, KeyError, TypeError):
            pass  # a broken route file costs the fill, never the row
    if row.get('engine') in POOL:
        row.setdefault('pool', POOL[row['engine']])
    if picked:
        if picked.get('score') is not None:  # routes saved before 10-24 carry a score
            row.setdefault('score', picked['score'])
        row.setdefault('routed', picked['engine'])
    elif 'task' in row and 'routed' not in row and row.get('engine') != 'driver':  # EXPRESS routes nothing
        print('route log: no saved route for this task here, so routed is not filled '
              '(run log from the ship worktree)', file=sys.stderr)
    try:
        with open(ledger_path(), 'a') as ledger:
            ledger.write(json.dumps(row) + '\n')
    except PermissionError:  # Claude Code's Bash sandbox can't write ~/.claude: CEL-74 lost four rows to it
        raise SystemExit(f'route log: no write access to {ledger_path()}, so nothing was logged. '
                         'Run this same command again with the Bash sandbox off.')
    if 'review' not in row and 'task' in row:
        mark_build(os.getcwd(), task=row['task'])
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
    reviews = [r for r in rows if 'review' in r]
    rows = [r for r in rows if 'review' not in r]
    def mean(group, key):
        values = [r[key] for r in group if isinstance(r.get(key), (int, float)) and not isinstance(r[key], bool)]
        return f'{sum(values) / len(values):.1f}' if values else '-'

    def first_pass(group):
        passed = [r['gates_first_pass'] for r in group if isinstance(r.get('gates_first_pass'), bool)]
        return f'{100 * sum(passed) // len(passed)}%' if passed else '-'
    groups = {}
    for row in rows:
        groups.setdefault((row.get('engine', '?'), band(row.get('score'))), []).append(row)
    lines = [f"{'engine':7} {'difficulty':10} {'tasks':>5} {'first pass':>10} {'fix rounds':>10} {'minutes':>8}"]
    for (engine, difficulty), group in sorted(groups.items()):
        minutes = mean(group, 'seconds')
        minutes = minutes if minutes == '-' else f'{float(minutes) / 60:.1f}'
        lines.append(f"{engine:7} {difficulty:10} {len(group):>5} {first_pass(group):>10} "
                     f"{mean(group, 'fix_rounds'):>10} {minutes:>8}")
    by_pool = {}  # rows logged before pools existed derive theirs from the engine
    for row in rows:
        by_pool.setdefault(row.get('pool') or POOL.get(row.get('engine')) or '-', []).append(row)
    if by_pool:
        lines += ['', f"{'pool':9} {'tasks':>5} {'first pass':>10} {'fix rounds':>10}"]
        for name, group in sorted(by_pool.items()):
            lines.append(f"{name:9} {len(group):>5} {first_pass(group):>10} {mean(group, 'fix_rounds'):>10}")
    if reviews:
        lines += ['', f"{'reviewer':8} {'ships':>5} {'real':>5} {'false':>5} {'only it':>7} {'owned':>5} {'minutes':>8}"]
        for name in sorted({r['review'] for r in reviews}):
            group = [r for r in reviews if r['review'] == name]
            total = lambda key: sum(r[key] for r in group if isinstance(r.get(key), int) and not isinstance(r[key], bool))
            secs = [r['seconds'] for r in group if isinstance(r.get('seconds'), (int, float))]
            minutes = f'{sum(secs) / len(secs) / 60:.1f}' if secs else '-'
            lines.append(f"{name:8} {len(group):>5} {total('real'):>5} {total('false'):>5} {total('only'):>7} "
                         f"{total('owned'):>5} {minutes:>8}")
    return '\n'.join(lines)


def selftest():
    fails = 0

    def check(name, ok):
        nonlocal fails
        print(f"  {'ok  ' if ok else 'FAIL'} {name}")
        fails += 0 if ok else 1

    os.environ.pop('CLAUDE_CODE_SESSION_ID', None)  # never touch the live run's marker
    with tempfile.TemporaryDirectory() as tmp:
        plan_md = os.path.join(tmp, 'plan.md')
        titles = ['Task 1: docs', 'Task 2: hard socket', 'Task 3: glue (driver)', 'Task 4: medium wiring',
                  'Task 5: easy rename', 'Task 6: auth boundary', 'Task 7: small test', 'Task 8: mid state',
                  'Task 9: one file']
        open(plan_md, 'w').write('# Plan\n\n' + ''.join(f'### {t}\n\nbody {i}\n\n' for i, t in enumerate(titles)))
        os.environ['SHIP_LEDGER'] = os.path.join(tmp, 'ledger.jsonl')
        result = plan(plan_md)
        check('every task is the driver\'s, (driver) or not, and nothing is scored',
              [t['engine'] for t in result['tasks']] == ['driver'] * 9
              and not any('score' in t for t in result['tasks']))
        few = os.path.join(tmp, 'few.md')
        open(few, 'w').write('### Task list\n\nan overview, not a task\n\n' +
                             ''.join(f'### Task {n}: t\n\n```md\n### Task 99: an example inside a fence\n```\n\n'
                                     for n in range(1, 6)))
        check('a fenced heading and "### Task list" are not tasks', len(plan(few)['tasks']) == 5)
        sizes, urls = [], []

        class Reply:
            def __init__(self, body):
                self.body = body

            def __enter__(self):
                return self

            def __exit__(self, *_):
                return False

            def read(self):
                return self.body

        def fake(request, timeout):
            urls.append(request.full_url)
            if 'subq' in request.full_url:
                raise urllib.error.HTTPError(request.full_url, 402, 'Payment Required', {}, None)
            asked = json.loads(request.data)['questions']
            sizes.append(len(asked))
            return Reply(json.dumps({'model': 'jev-test', 'answers': {k: {'score': 1} for k in asked}}).encode())
        real = urllib.request.urlopen
        urllib.request.urlopen = fake
        os.environ.update(SUBQ_API_KEY='k', TYPESAFE_API_KEY='k', ROUTE_NO_KEYCHAIN='1')
        try:
            answers, model = decide(list(range(40)), lambda b: ({}, {f'q{i}': {} for i in b}))
            subq_sizes = [n for n in batches(list(range(40)), lambda i: 1, DECIDERS[0]['questions'])]
        finally:
            urllib.request.urlopen = real
        check('SubQ asks at most 16 questions a request', [len(b) for b in subq_sizes] == [16, 16, 8])
        check('a SubQ 402 falls through to Jev, which answers everything',
              'subq' in urls[0] and model == 'jev-test' and len(answers) == 40 and sizes == [40])
        log(['repo=ship', 'task=2', 'engine=fable', 'score=3.4', 'seconds=300', 'fix_rounds=1', 'gates_first_pass=false'])
        open(ledger_path(), 'a').write('{"half a line\n')
        log(['repo=ship', 'task=1', 'engine=astra', 'score=0.8', 'seconds=120', 'fix_rounds=0', 'gates_first_pass=True'])
        sol = log(['repo=ship', 'task=9', 'engine=sol', 'score=1.2', 'fix_rounds=2', 'gates_first_pass=True'])
        old = log(['repo=ship', 'task=7', 'engine=haiku', 'score=1.0'])
        check('log engine=sol fills pool=openai; an engine outside the map logs no pool',
              sol['pool'] == 'openai' and 'pool' not in old)
        log(['repo=ship', 'review=sol', 'real=2', 'false=3', 'only=1', 'owned=1', 'seconds=120'])
        log(['repo=ship', 'review=sol', 'real=1', 'false=0', 'only=0', 'seconds=60'])
        table = report()
        check('the ledger reports by engine and difficulty, past a broken line',
              'fable   hard 2.5+      1         0%        1.0      5.0' in table and
              'astra   easy <1.5      1       100%' in table)
        check('and by pool, deriving the pool from the engine for older rows',
              'openai        2       100%        1.0' in table and 'fable         1         0%        1.0' in table
              and '-             1' in table)
        check('reviewers get their own table, outside the BUILD one',
              'sol          2     3     3       1     1      1.5' in table and 'sol      unscored' not in table)
        repo = os.path.join(tmp, 'repo')
        subprocess.run(['git', 'init', '-q', repo], check=True)
        stage = os.path.join(repo, '.ship-stage')
        open(stage, 'w').write('plan')
        os.makedirs(os.path.join(repo, 'specs'))
        shipped = os.path.join(repo, 'specs', 'plan.md')
        open(shipped, 'w').write(open(plan_md).read())
        plan(shipped)
        check('routing moves the marker to build:0:9', open(stage).read() == 'build:0:9')
        open(stage, 'w').write('plan')
        plan(shipped)
        here = os.getcwd()
        os.chdir(repo)
        try:
            row = log(['task=2', 'engine=opus'])
            moved = log(['task=1', 'engine=opus'])
            missing = log(['task=42', 'engine=astra'])
            log(['task=2', 'engine=opus', 'note=fix round'])
            plan(shipped)
        finally:
            os.chdir(here)
        check('distinct logged tasks count done, a re-log counts once, a re-route keeps the count',
              open(stage).read() == 'build:3:9')
        os.chdir(repo)
        try:
            log(['task=5,6', 'engine=opus'])
            try:
                log(['review=fable', 'real=5', 'only=7'])
                bad = False
            except SystemExit:
                bad = True
        finally:
            os.chdir(here)
        check('a combined task=5,6 counts two', open(stage).read() == 'build:5:9')
        check('a review row with only above real is refused', bad)
        wrapped = os.path.join(tmp, 'wrapped')
        os.makedirs(wrapped)
        open(os.path.join(wrapped, 'seconds'), 'w').write('412\n')
        timed = log(['repo=ship', 'task=8', 'engine=astra', f'out={wrapped}'])
        check('out=<dir> fills seconds from the wrapper and keeps out of the row',
              timed.get('seconds') == 412 and 'out' not in timed)
        locked = os.path.join(tmp, 'locked')
        os.makedirs(locked)
        os.chmod(locked, 0o500)
        os.environ['SHIP_LEDGER'], kept = os.path.join(locked, 'ledger.jsonl'), os.environ['SHIP_LEDGER']
        try:
            log(['repo=ship', 'task=1', 'engine=opus'])
            said = ''
        except SystemExit as stop:
            said = str(stop)
        finally:
            os.environ['SHIP_LEDGER'] = kept
            os.chmod(locked, 0o700)
        check('a ledger it cannot write says to rerun with the sandbox off', 'sandbox off' in said)
        check('log fills routed=driver from the saved plan, and a subagent\'s task shows engine=opus',
              row.get('routed') == 'driver' and row['engine'] == 'opus' and 'score' not in row)
        check('an unknown task logs unfilled', moved.get('routed') == 'driver' and 'routed' not in missing)
        gaps = os.path.join(tmp, 'gaps.md')
        open(gaps, 'w').write('### Task 1: a\n\nx\n\n### Task 3: b\n\ny\n')
        check('tasks keep the numbers the plan gives them', [t['n'] for t in parse_tasks(open(gaps).read())] == [1, 3])
        split = parse_tasks('### Task 3a: one half\n\nx\n\n### Task 3b: other half\n\ny\n\n### Task 4: z\n\nz\n')
        check('split tasks 3a and 3b are tasks, each with its own number and label',
              [(t['n'], t['label']) for t in split] == [(3, '3a'), (4, '3b'), (5, '4')])
        json.dump({'tasks': [{'n': 3, 'label': '3a', 'score': 1, 'engine': 'wonder'},
                             {'n': 4, 'label': '3b', 'score': 2, 'engine': 'fable'},
                             {'n': 5, 'label': '4', 'score': 3, 'engine': 'opus'}]},
                  open(os.path.join(repo, '.ship-route.json'), 'w'))
        os.chdir(repo)
        try:
            by_label, plain = log(['task=3b', 'engine=fable']), log(['task=4', 'engine=opus'])
        finally:
            os.chdir(here)
        check('log finds task=3b by its label, and task=4 is the plan\'s Task 4, not 3b',
              by_label.get('routed') == 'fable' and plain.get('routed') == 'opus')
        os.remove(stage)
        plan(shipped)
        check('outside a ship no marker appears', not os.path.exists(stage))
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
    elif args == ['reader']:  # the Claude model that reads the branch at REVIEW
        print('opus')
    elif args == ['quota']:
        print(quota.table())
    else:
        sys.exit(__doc__)
