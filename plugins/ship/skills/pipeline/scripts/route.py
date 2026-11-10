#!/usr/bin/env python3
"""Count a plan's BUILD tasks, and keep the ledger that judges how each was built.

  route.py plan <plan.md>        list the plan's tasks; JSON on stdout, a table on stderr
  route.py gate <cmd> [args...]  run one gate command and record whether it passed
  route.py log key=value ...     append one task's outcome to the ledger
Inside a ship, `plan` moves the stage marker to build:0:<tasks> and each `log` counts one
task done, so the status line reaches BUILD without the driver remembering to say so.
`plan` saves the task list to .ship-route.json beside the marker and starts the clock;
each task row then fills what the driver didn't pass, never a guess:
  seconds           wall time since the last `plan` or task `log`
  gates_first_pass  whether the first `gate` run since then passed
  fix_rounds        how many `gate` runs since then failed
So commit the task, then log it, and run each check as one `gate` call (the scoped gate
script is one command), so a red run is one fix round. Review and recall rows leave the
clock alone.
  route.py log review=<fable|opus|wonder> stage=<plan|branch> real=<n> false=<n> only=<n> ...
                                 append one reader's tally for the ship: findings that
                                 were real, false alarms, and real ones another reader
                                 missed; it never counts as a BUILD task
  route.py log recall=<shown> used=<n> ...
                                 append how many of the decisions `decisions.py relevant`
                                 showed the ship it actually used; never a BUILD task
  route.py log task=<n> status=parked note=<why> ...
                                 a plan task Pete let the ship land without; it counts as
                                 logged and stays out of the report's build times
  route.py log snag=<what, in a sentence> ...
                                 a small thing the run hit, logged where it once sent a
                                 retro; never a BUILD task, and report lists the last ten
  route.py adopt <n>[,<n>...]    from the worktree, mark tasks an earlier session built as done,
                                 with no ledger row, since their time and first pass are its own
  route.py readers repo=<r> ship=<s>
                                 exit 0 once both branch readers are logged for the ship,
                                 Wonder and a Claude reader, fable or opus (a wonder row
                                 whose note starts "out" counts, for Muse being down) and, run from the worktree, every plan task
                                 is logged built or parked, its branch adds the review card
                                 and no line it adds names the worktree itself; exit 1
                                 naming what's missing
  route.py report                the ledger as a table by engine, then the readers', then
                                 the snags
  route.py --selftest

Opus 5.5 drives (Pete, 2026-10-24) and builds every task in its own loop, so `plan` ranks
nothing. Fable 5.2 reads beside Wonder since 2026-11-09, and `report` counts that trial. The Fable window and the pools are in git history (`git log -S FABLE_UNTIL`).
The ledger is ~/.claude/ship-ledger.jsonl, or SHIP_LEDGER.
"""
import json
import os
import re
import subprocess
import sys
import tempfile
import time


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


def beside_marker(start, name):
    marker = stage_marker(start)
    return marker and os.path.join(os.path.dirname(marker), name)


def mark_build(start, task=None, total=None):
    """build:0:<total> when routing ends, then build:<distinct tasks logged>:<total>, so a
    task logged twice (a fix round) counts once and task=4,10 counts two. A task logged while
    a stop holds the marker still goes in .ship-done, so the recap and the count stay right
    once the stage is written back. Outside a ship, nothing."""
    path = stage_marker(start)
    if not path:
        return
    # BUILD's markers never pass through stage.sh, so its check for a copy still owed runs here too.
    subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'branch-db.py'),
                    'check', os.path.dirname(path)], stdout=sys.stderr)
    current = re.match(r'build:(\d+):(\d+)', open(path).read().strip())
    if total is not None and not current:  # a re-route mid-build keeps the count
        open(path, 'w').write(f'build:0:{total}')
    elif task is not None:
        done_file = os.path.join(os.path.dirname(path), '.ship-done')
        seen = set(open(done_file).read().split()) if os.path.isfile(done_file) else set()
        before = len(seen)
        seen.update(t.strip() for t in str(task).split(',') if t.strip())
        if len(seen) == before:
            return
        open(done_file, 'w').write('\n'.join(sorted(seen)) + '\n')
        if not current:
            return
        m = int(current.group(2))
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


def read_route(path):
    try:
        return json.load(open(path))
    except (OSError, ValueError):
        return None


def write_route(path, data):
    try:
        with open(path, 'w') as f:
            json.dump(data, f)
    except OSError as error:  # the table on stdout still carries the tasks
        print(f'route: could not save {path}: {error}', file=sys.stderr)


def plan(path, now=None):
    try:
        tasks = parse_tasks(open(path).read())
    except OSError as error:
        raise SystemExit(f'route: {error}')
    if not tasks:
        raise SystemExit(f'route: no "### Task" headings in {path}')
    where = os.path.dirname(os.path.abspath(path))
    out = [{'n': t['n'], 'label': t['label'], 'title': t['title']} for t in tasks]
    for row in out:
        print(f"{row['label']:4} {row['title'][:80]}", file=sys.stderr)
    result = {'plan': os.path.abspath(path), 'tasks': out}  # ship-recap.sh names it after a compaction
    saved = beside_marker(where, '.ship-route.json')
    if saved:
        old = read_route(saved) or {}
        write_route(saved, {**result, 'anchor': old.get('anchor') or int(now or time.time())})
    mark_build(where, total=len(tasks))
    return result


def gate(argv, start=None):
    """Run one gate command with its output passing through, record the result beside the
    marker, and return its exit code."""
    if not argv:
        raise SystemExit('route gate: give the gate command, e.g. route.py gate bash gates.sh')
    if len(argv) == 1 and any(c.isspace() for c in argv[0]):  # cel-302's "npm run typecheck"
        raise SystemExit(f"route gate: {argv[0]!r} runs as one program name; pass its words "
                         "separately (route.py gate npm run typecheck), or put a multi-step gate in "
                         "a script file and run route.py gate bash <file>")
    began = time.time()
    try:
        code = subprocess.call(argv)
    except OSError as error:
        print(f'route gate: {argv[0]}: {error.strerror}', file=sys.stderr)
        code = 127
    runs = beside_marker(start or os.getcwd(), '.ship-gates')
    if runs:
        with open(runs, 'a') as f:
            f.write(json.dumps({'ts': int(time.time()), 'ok': code == 0, 'cmd': ' '.join(argv)[:200]}) + '\n')
    # the verdict last and on stderr, after the row: a `| tail` can't hide it (cel-263 reran a
    # suite to read one), and a closed stdout pipe can't cost the row
    verdict = 'PASS' if code == 0 else f'FAIL (exit {code})'
    print(f"route gate: {verdict} {' '.join(argv)[:120]} ({time.time() - began:.0f}s)", file=sys.stderr)
    return code


def fill_task(row, start, now=None):
    """Fill seconds, gates_first_pass and fix_rounds from the clock and the gate runs since
    the last task row (or `plan`), and return the clock's new start, which log saves only once
    the row is written. Values passed on the command line win. A re-log with a note (a fix
    round after REVIEW) fills nothing and leaves the clock: its span holds the pre-flight,
    the readers and the absorb, not the task."""
    saved = beside_marker(start, '.ship-route.json')
    route = saved and read_route(saved)
    if not route or not route.get('anchor') or 'note' in row:
        return None
    anchor, now = route['anchor'], int(now or time.time())
    if now > anchor:
        row.setdefault('seconds', now - anchor)
    runs_file = beside_marker(start, '.ship-gates')
    runs = []
    if runs_file and os.path.isfile(runs_file):
        for line in open(runs_file).read().splitlines():
            try:
                run = json.loads(line)
            except ValueError:
                continue
            if isinstance(run.get('ts'), int) and run['ts'] > anchor:
                runs.append(run)
    if runs:
        row.setdefault('gates_first_pass', bool(runs[0].get('ok')))
        row.setdefault('fix_rounds', sum(1 for r in runs if not r.get('ok')))
    return lambda: write_route(saved, {**route, 'anchor': max(now, anchor)})


def coerce(value):
    if value.lower() in ('true', 'false'):
        return value.lower() == 'true'
    for kind in (int, float):
        try:
            return kind(value)
        except ValueError:
            pass
    return value


def pairs_to_row(pairs, cmd):
    row = {}
    for pair in pairs:
        key, sep, value = pair.partition('=')
        if not sep:
            raise SystemExit(f'route {cmd}: "{pair}" is not key=value')
        row[key] = coerce(value)
    return row


def log(pairs):
    if not pairs:
        raise SystemExit('route log: nothing to log; pass key=value pairs')
    row = {'ts': time.strftime('%Y-%m-%dT%H:%M:%S'), **pairs_to_row(pairs, 'log')}
    for part in ('only', 'owned'):
        if 'review' in row and isinstance(row.get(part), int) and isinstance(row.get('real'), int) \
                and row[part] > row['real']:
            raise SystemExit(f"route log: {part}={row[part]} is more than real={row['real']}")
    if 'task' in row and not re.fullmatch(r'\d+[a-z]?(,\d+[a-z]?)*', str(row['task'])):
        raise SystemExit(f"route log: task={row['task']} isn't a plan task (3, 3b or 5,6); "
                         "a reader's tally is review=<engine> stage=<plan|branch> real= false= nits=")
    if 'snag' in row and (not isinstance(row['snag'], str) or not row['snag'].strip() or not row.get('repo')
                          or not row.get('ship') or {'task', 'review', 'recall'} & set(row)):
        raise SystemExit('route log: a snag is repo=<r> ship=<slug> snag="<what, in a sentence>" and '
                         'nothing that counts a task, a read or a recall')
    if row.get('status') == 'parked' and ('task' not in row or 'note' not in row):
        raise SystemExit("route log: a parked task needs task=<n> and note=<why it wasn't built>")
    if 'task' in row and 'review' not in row and 'note' not in row and row.get('repo') and row.get('ship'):
        earlier = logged(row['repo'], row['ship'], set(str(row['task']).split(',')))
        if earlier:
            raise SystemExit(f"route log: task {row['task']} of {row['ship']} is already logged ({earlier}); "
                             "log it again only with note=<why>")
    if 'recall' in row and 'note' not in row and row.get('repo') and row.get('ship'):
        earlier = next((r.get('ts') for r in rows() if 'recall' in r
                        and (r.get('repo'), r.get('ship')) == (row['repo'], row['ship'])), None)
        if earlier:  # LAND step 2's red goes back to step 1, which logs it
            raise SystemExit(f"route log: {row['ship']}'s recall is already logged ({earlier}); "
                             "log it again only with note=<why>")
    out = row.pop('out', None)  # a wrapper's out-dir: its `seconds` file is the run's own wall time
    if out and 'seconds' not in row:
        try:
            row['seconds'] = int(open(os.path.join(str(out), 'seconds')).read().strip())
        except (OSError, ValueError):
            print(f'route log: no seconds file in {out}, so seconds is left out', file=sys.stderr)
    task_row = 'task' in row and 'review' not in row
    restart = task_row and fill_task(row, os.getcwd(), os.environ.get('ROUTE_NOW'))
    if task_row and row.get('status') == 'parked':  # fills nothing, but the next task's clock
        saved = beside_marker(os.getcwd(), '.ship-route.json')  # and gate runs start here, as adopt's do
        route = saved and read_route(saved)
        if route:
            restart = lambda: write_route(saved, {**route, 'anchor': int(os.environ.get('ROUTE_NOW') or time.time())})
    try:
        with open(ledger_path(), 'a') as ledger:
            ledger.write(json.dumps(row) + '\n')
    except PermissionError:  # Claude Code's Bash sandbox can't write ~/.claude: CEL-74 lost four rows to it
        raise SystemExit(f'route log: no write access to {ledger_path()}, so nothing was logged. '
                         'Run this same command again with the Bash sandbox off.')
    if restart:
        restart()
    if task_row:
        mark_build(os.getcwd(), task=row['task'])
    return row


def adopt(tasks, now=None):
    """Mark tasks an earlier session built as done, with no ledger row, and start the clock
    now, so the next task's time and gate runs aren't the stall's or that session's."""
    if not re.fullmatch(r'\d+[a-z]?(,\d+[a-z]?)*', tasks):
        raise SystemExit('route adopt: give plan tasks, e.g. route.py adopt 1,2,3')
    saved = beside_marker(os.getcwd(), '.ship-route.json')
    route = saved and read_route(saved)
    if not route:
        raise SystemExit('route adopt: no saved plan beside the marker; run it from the ship worktree after plan')
    known = {str(t.get('label', t.get('n'))) for t in route.get('tasks', [])}
    unknown = [t for t in tasks.split(',') if t not in known]
    if unknown:
        raise SystemExit(f"route adopt: {', '.join(unknown)} is not a task in {route.get('plan')}")
    mark_build(os.getcwd(), task=tasks)
    write_route(saved, {**route, 'anchor': int(now or time.time())})


def rows():
    out = []
    try:
        for line in open(ledger_path()):
            try:
                out.append(json.loads(line))
            except ValueError:
                pass  # a half-written line from a concurrent ship; the rest still counts
    except FileNotFoundError:
        pass
    return out


def logged(repo, ship, tasks):
    """The timestamp of an earlier build row sharing any of these tasks, if there is one."""
    for r in rows():
        if (r.get('repo'), r.get('ship')) == (repo, ship) and 'task' in r and 'review' not in r \
                and r.get('status') != 'parked' and tasks & set(str(r['task']).split(',')):
            return r.get('ts')
    return None


READERS = ('wonder', 'fable', 'opus')
TRIAL_FROM, TRIAL_SHIPS = '2026-11-09', 20  # Pete: Wonder stays or goes on what only it found over 20 ships


def readers(pairs):
    """Exit 0 once every saved plan task is logged, built or parked, the ship's ledger holds
    both branch readers, logged since the branch's first commit, the branch adds its review
    card and no line it adds names its own worktree; else 1 naming what's missing. Run from
    the worktree or the session the ship's marker points at."""
    want = pairs_to_row(pairs, 'readers')
    if not want.get('repo') or not want.get('ship'):
        raise SystemExit('route readers: give repo=<repo> ship=<slug>')
    marker = stage_marker(os.getcwd())  # a cross-repo ship runs this from the launch repo
    root = os.path.dirname(marker) if marker else '.'
    saved = beside_marker(os.getcwd(), '.ship-route.json')
    route = saved and read_route(saved)
    if route:  # yeoman-coverage landed with task 7 unbuilt, recorded only by a note in the plan
        done_file = beside_marker(os.getcwd(), '.ship-done')
        done = set(open(done_file).read().split()) if os.path.isfile(done_file) else set()
        todo = [str(t.get('label', t.get('n'))) for t in route.get('tasks', [])
                if str(t.get('label', t.get('n'))) not in done]
        if todo:
            print(f"route readers: plan task {', '.join(todo)} is neither built nor parked; build and log "
                  "it (route.py adopt <n> if an earlier session built it), or, on Pete's word to land "
                  "without it, route.py log repo= ship= task=<n> status=parked note=<why> and name it in "
                  "the PR body", file=sys.stderr)
            return 1
    since = branch_start(root)
    seen = {r['review'] for r in rows() if (r.get('repo'), r.get('ship')) == (want['repo'], want['ship'])
            and r.get('review') in READERS
            and not str(r.get('note', '')).startswith('for:')  # a stand-in sits in Wonder's seat, which its out row holds
            and r.get('stage', 'branch') == 'branch'  # main's text logged branch reads with no stage
            and (since is None or logged_at(r) is None or logged_at(r) >= since)}  # a reused slug's old rows
    # the Claude reader is whichever of Fable and Opus didn't drive (Pete, 2026-11-09)
    missing = [name for name, held in (('wonder', {'wonder'}), ('fable', {'fable', 'opus'})) if not held & seen]
    if missing:
        ship = str(want['ship'])
        key = lambda slug: (re.match(r'[a-z]+-\d+', slug) or [slug])[0]  # cel-302 of cel-302-usage-deny
        akin = lambda slug: (slug.startswith(ship + '-') or ship.startswith(slug + '-')
                             or key(slug) == key(ship) or bare_slug(slug) == bare_slug(ship))
        near = sorted({str(r['ship']) for r in rows() if r.get('repo') == want['repo'] and r.get('ship')
                       and str(r['ship']) != ship and r.get('review') in READERS
                       and r.get('stage', 'branch') == 'branch'
                       and (since is None or logged_at(r) is None or logged_at(r) >= since)
                       and akin(str(r['ship']))})
        print(f"route readers: {want['ship']} has no {' or '.join(missing)} branch row since the branch "
              "began; log the read (review=<reader> stage=branch real= false= nits=) before landing, "
              "review=wonder stage=branch note=out:<exit> when Muse was down, or review=fable "
              "stage=branch note=skipped:budget when Pete capped spend"
              + (f"; branch reads also sit under ship={', '.join(near)}: if they are this ship's "
                 f"own, log them again under ship={ship}, never borrow another ship's" if near else ''),
              file=sys.stderr)
        return 1
    if card_missing(want['ship'], root):
        print(f"route readers: this branch adds no review card for {want['ship']}; commit it "
              "(LAND step 1) before the push", file=sys.stderr)
        return 1
    named = names_worktree(root)
    if named:
        print(f"route readers: {', '.join(named)} names this worktree's own path, which teardown removes, so "
              "it fails in every other checkout; resolve the path from the file's own location, rerun "
              "what reads it and commit", file=sys.stderr)
        return 1
    parked = sorted({f"{r['task']} ({r.get('note')})" for r in rows() if r.get('status') == 'parked'
                     and (r.get('repo'), r.get('ship')) == (want['repo'], want['ship'])})
    print(f"route readers: {want['ship']} has both branch readers logged and its card"
          + (f"; parked on Pete's word, so the PR body names them: {', '.join(parked)}" if parked else ''),
          file=sys.stderr)
    return 0


def logged_at(row):
    try:
        return int(time.mktime(time.strptime(str(row.get('ts')), '%Y-%m-%dT%H:%M:%S')))
    except ValueError:
        return None


def git_at(root, *a):
    return subprocess.run(['git', '-C', root, *a], capture_output=True, text=True)


def base_ref(root):
    """The base branch the way stage 0 finds it, or None when git can't tell."""
    head = git_at(root, 'rev-parse', '--abbrev-ref', 'origin/HEAD').stdout.strip()
    for name in ([head] if head else []) + ['origin/main', 'origin/master', 'main', 'master']:
        if git_at(root, 'rev-parse', '-q', '--verify', name).returncode == 0:
            return name
    return None


def branch_start(root):
    """When the branch's first commit was authored (a rebase keeps it), or None."""
    base = base_ref(root)
    out = base and git_at(root, 'log', '--reverse', '--format=%at', f'{base}..HEAD')
    first = out and out.returncode == 0 and out.stdout.split()
    return int(first[0]) if first else None


def bare_slug(ship):
    """The slug without a branch kind's prefix: fix-x is x, as a fix/x branch's card names it."""
    return re.sub(r'^(feature|fix|refactor)-', '', ship, flags=re.I)


def card_missing(ship, root='.'):
    """True when the branch at `root` adds no review card for `ship`: an .html file naming the
    ship's key or slug, with or without a leading feature-, fix- or refactor-, that says review
    outside the slug itself, so cel-12-review-queue's storyboard isn't its card. False when it does or git can't tell (no repo, no base). Only
    SELF-DIRECTED and GATED ships run readers, after the card's commit, so it never nags an
    EXPRESS ship or one mid-LAND (cel-323). thin-search needed a second PR for one."""
    base = base_ref(root)
    added = base and git_at(root, 'diff', '--name-only', '--diff-filter=A', f'{base}...HEAD')
    if not added or added.returncode:
        return False
    bare = bare_slug(ship)  # hello-dead-ends filed fix-hello-dead-ends' card without the fix-
    key = re.match(r'[a-z]+-[0-9]+', bare, re.I)  # cel-221: a card folder may carry just the key
    sid = re.compile(re.escape((key.group(0) if key else bare).lower()) + r'(?![0-9])')
    cut = lambda f: f.replace(ship.lower() if ship.lower() in f else bare.lower(), '')  # fix-review
    return not any(f.endswith('.html') and sid.search(f) and 'review' in cut(f)
                   for f in (line.lower() for line in added.stdout.splitlines()))


def names_worktree(root='.'):
    """The files where the branch at `root` adds a line naming its own linked worktree, a path
    teardown removes: cells-app #515 landed a reader's fuzz rooted at its worktree, and it
    failed in every other checkout once that was gone (1 of 150 merged PRs had such a line).
    Empty in a main checkout, whose path outlives the branch, and when git can't tell."""
    top = git_at(root, 'rev-parse', '--show-toplevel').stdout.strip()
    base = base_ref(root)
    if not top or not base or not os.path.isfile(os.path.join(top, '.git')):  # a linked worktree's .git is a file
        return []
    diff = subprocess.run(['git', '-C', root, 'diff', '--unified=0', f'{base}...HEAD'],
                          capture_output=True, text=True, errors='replace').stdout
    own = re.compile(re.escape(top) + r'(?![\w.-])')  # feature-x is not feature-x-2
    found, name, head = [], None, True
    for line in diff.split('\n'):
        if line.startswith('diff --git '):
            name, head = None, True
        elif line.startswith('@@'):
            head = False
        elif head and line.startswith('+++ '):  # only before a file's first hunk: a line of code may begin ++
            name = line[6:]
        elif not head and line.startswith('+') and name not in found and own.search(line):
            found.append(name)
    return found


def report():
    everything = rows()
    reviews = [r for r in everything if 'review' in r]
    recalls = [r for r in everything if 'recall' in r]
    snags = [r for r in everything if 'snag' in r]
    tasks = [r for r in everything if 'review' not in r and 'recall' not in r and 'snag' not in r
             and r.get('status') != 'parked']

    def mean(group, key):
        values = [r[key] for r in group if isinstance(r.get(key), (int, float)) and not isinstance(r[key], bool)]
        return f'{sum(values) / len(values):.1f}' if values else '-'

    def first_pass(group):
        passed = [r['gates_first_pass'] for r in group if isinstance(r.get('gates_first_pass'), bool)]
        return f'{100 * sum(passed) // len(passed)}%' if passed else '-'
    groups = {}
    for row in tasks:
        groups.setdefault(row.get('engine', '?'), []).append(row)
    lines = [f"{'engine':7} {'tasks':>5} {'timed':>5} {'first pass':>10} {'fix rounds':>10} {'minutes':>8}"]
    for engine, group in sorted(groups.items()):
        minutes = mean(group, 'seconds')
        minutes = minutes if minutes == '-' else f'{float(minutes) / 60:.1f}'
        timed = sum(1 for r in group if isinstance(r.get('seconds'), (int, float)))
        lines.append(f"{engine:7} {len(group):>5} {timed:>5} {first_pass(group):>10} "
                     f"{mean(group, 'fix_rounds'):>10} {minutes:>8}")
    if reviews:
        lines += ['', f"{'reader':8} {'ships':>5} {'real':>5} {'false':>5} {'only it':>7} {'owned':>5} {'minutes':>8}"]
        note = lambda r: str(r.get('note', ''))
        # an outage's note=out row is no read; the stand-in's note=for:wonder row is no Opus read
        reads = [r for r in reviews if not note(r).startswith(('out:', 'skipped:'))]
        reader = lambda r: 'stand-in' if note(r).startswith('for:wonder') else r['review']
        for name in sorted({reader(r) for r in reads}):
            group = [r for r in reads if reader(r) == name]
            total = lambda key: sum(r[key] for r in group if isinstance(r.get(key), int) and not isinstance(r[key], bool))
            secs = [r['seconds'] for r in group if isinstance(r.get('seconds'), (int, float))]
            minutes = f'{sum(secs) / len(secs) / 60:.1f}' if secs else '-'
            lines.append(f"{name:8} {len(group):>5} {total('real'):>5} {total('false'):>5} {total('only'):>7} "
                         f"{total('owned'):>5} {minutes:>8}")
        # the trial: ships whose branch Fable 5.2 and Wonder both read, and what each found alone
        pairs = {}
        for r in reads:  # a ship's last row per reader and stage, so a read logged twice counts once
            if str(r.get('ts', ''))[:10] >= TRIAL_FROM and reader(r) in ('fable', 'wonder') \
                    and '5.2' in str(r.get('model', '5.2')).replace('-', '.') and isinstance(r.get('only'), int):
                pairs.setdefault((r.get('repo'), r.get('ship')), {})[(r['review'], r.get('stage', 'branch'))] = r
        trial = [group for group in pairs.values() if ('fable', 'branch') in group and ('wonder', 'branch') in group]
        if trial:
            alone = lambda name, stage: sum(group[(name, stage)]['only'] for group in trial if (name, stage) in group)
            lines += ['', f"Wonder trial: {len(trial)} of {TRIAL_SHIPS} ships read by Fable 5.2 and Wonder. Real findings "
                          f"only Wonder made: {alone('wonder', 'branch')} on branches, {alone('wonder', 'plan')} on "
                          f"plans; only Fable: {alone('fable', 'branch')} and {alone('fable', 'plan')}"
                          + ('. The count is in: take it to Pete' if len(trial) >= TRIAL_SHIPS else '')]
    if recalls:  # does decision recall earn its keep? (Pete, 2026-10-28)
        count = lambda key: sum(r[key] for r in recalls if isinstance(r.get(key), int) and not isinstance(r[key], bool))
        shown, used = count('recall'), count('used')
        none = sum(1 for r in recalls if r.get('used') == 0)
        lines += ['', f"decision recall: {len(recalls)} ships used {used} of {shown} shown"
                      f" ({100 * used // shown if shown else 0}%); {none} used none"]
    if snags:  # what a run logs where it used to send a retro; the maintainer's daily batch reads these
        recent = [r for r in snags if (logged_at(r) or 0) >= time.time() - 3 * 86400]
        lines += ['', f"snags: {len(snags)} on {len({(r.get('repo'), r.get('ship')) for r in snags})} ships; "
                      f"the last three days' {len(recent)}:"]
        lines += [f"  {str(r.get('ts'))[:10]} {r.get('repo')}/{r.get('ship')}: {r['snag']}" for r in recent]
    return '\n'.join(lines)


def selftest():
    fails = 0

    def check(name, ok):
        nonlocal fails
        print(f"  {'ok  ' if ok else 'FAIL'} {name}")
        fails += 0 if ok else 1

    def refused(fn, *args):
        try:
            fn(*args)
        except SystemExit as error:
            return str(error)
        return ''

    # Never touch the live run's marker: gates run this from inside a ship's worktree, where a
    # task row logged from the cwd counted eight tasks done on the ship-review run (2026-11-05).
    os.environ.pop('CLAUDE_CODE_SESSION_ID', None)
    here = os.getcwd()

    def ship_state():
        marker = stage_marker(here)
        return marker and [open(os.path.join(os.path.dirname(marker), f)).read() if os.path.exists(
            os.path.join(os.path.dirname(marker), f)) else None for f in ('.ship-stage', '.ship-done', '.ship-gates')]
    before = ship_state()
    with tempfile.TemporaryDirectory() as tmp:
        plain = os.path.join(tmp, 'plain')
        os.makedirs(plain)
        os.chdir(plain)
        os.environ['SHIP_LEDGER'] = os.path.join(tmp, 'ledger.jsonl')
        plan_md = os.path.join(tmp, 'plan.md')
        open(plan_md, 'w').write('# Plan\n\n' + ''.join(f'### Task {n}: t{n}\n\nbody\n\n' for n in range(1, 10)))
        result = plan(plan_md)
        check('plan lists every task and saves the plan path; nothing is routed or scored',
              result['plan'] == os.path.abspath(plan_md) and len(result['tasks']) == 9
              and not any('engine' in t or 'score' in t for t in result['tasks']))
        few = os.path.join(tmp, 'few.md')
        open(few, 'w').write('### Task list\n\nan overview, not a task\n\n' +
                             ''.join(f'### Task {n}: t\n\n```md\n### Task 99: an example inside a fence\n```\n\n'
                                     for n in range(1, 6)))
        check('a fenced heading and "### Task list" are not tasks', len(plan(few)['tasks']) == 5)
        gaps = parse_tasks('### Task 1: a\n\nx\n\n### Task 3: b\n\ny\n')
        check('tasks keep the numbers the plan gives them', [t['n'] for t in gaps] == [1, 3])
        split = parse_tasks('### Task 3a: one half\n\nx\n\n### Task 3b: other half\n\ny\n\n### Task 4: z\n\nz\n')
        check('split tasks 3a and 3b are tasks, each with its own number and label',
              [(t['n'], t['label']) for t in split] == [(3, '3a'), (4, '3b'), (5, '4')])

        log(['repo=ship', 'task=2', 'engine=opus', 'seconds=300', 'fix_rounds=1', 'gates_first_pass=false'])
        open(ledger_path(), 'a').write('{"half a line\n')
        log(['repo=ship', 'task=1', 'engine=driver', 'seconds=120', 'fix_rounds=0', 'gates_first_pass=True'])
        log(['repo=ship', 'review=wonder', 'stage=branch', 'real=2', 'false=3', 'only=1', 'owned=1', 'seconds=120'])
        log(['repo=ship', 'review=wonder', 'stage=plan', 'real=1', 'false=0', 'only=0', 'seconds=60'])
        open(ledger_path(), 'a').write(json.dumps({'repo': 'ship', 'task': 4, 'engine': 'sonnet', 'pool': 'anthropic',
                                                   'score': 2.1, 'routed': 'sonnet', 'fix_rounds': 2}) + '\n')
        log(['repo=ship', 'ship=o', 'review=wonder', 'stage=branch', 'note=out:5'])
        log(['repo=ship', 'ship=o', 'review=opus', 'stage=branch', 'real=4', 'false=1', 'only=2',
             'note=for:wonder'])
        table = report()
        check("a Muse outage's rows count as no Wonder read and a stand-in, never as Opus",
              'stand-in     1     4     1       2' in table and '\nopus     ' not in table.split('reader')[1])
        check('an old row with pool, score and routed still reports under its engine',
              'sonnet      1     0          -        2.0        -' in table)
        check('the ledger reports by engine, past a broken line',
              'opus        1     1         0%        1.0      5.0' in table and 'driver      1     1       100%' in table)
        check('readers get their own table, outside the BUILD one',
              'wonder       2     3     3       1     1      1.5' in table)
        log(['repo=ship', 'ship=a', 'recall=6', 'used=2'])
        log(['repo=ship', 'ship=b', 'recall=6', 'used=0'])
        check('recall rows get one line and never join the BUILD table',
              'decision recall: 2 ships used 2 of 12 shown (16%); 1 used none' in report())
        build_table = report().split('reader')[0]
        log(['repo=ship', 'ship=a', 'snag=the smoke waited four minutes on a cold server'])
        open(ledger_path(), 'a').write(json.dumps({'ts': '2019-12-01T00:00:00', 'repo': 'ship', 'ship': 'old',
                                                   'snag': 'a snag from long ago'}) + '\n')
        check('a snag row gets its own lines and never joins the BUILD table; an old one is counted, not listed',
              report().split('reader')[0] == build_table and "snags: 2 on 2 ships; the last three days' 1:" in report()
              and 'ship/a: the smoke waited four minutes' in report() and 'long ago' not in report())
        check('a snag that names a task, has no ship or says nothing is refused',
              all('a snag is' in refused(log, bad) for bad in (
                  ['repo=ship', 'ship=a', 'task=1', 'snag=flaky smoke'], ['repo=ship', 'snag=flaky smoke'],
                  ['repo=ship', 'ship=a', 'snag='], ['repo=ship', 'ship=a', 'snag=42'])))
        check("a ship's second recall row is refused",
              'already logged' in refused(log, ['repo=ship', 'ship=a', 'recall=6', 'used=3']))
        check('task=review is refused, pointing at review=',
              'review=<engine>' in refused(log, ['repo=ship', 'ship=dup', 'task=review', 'engine=opus']))
        check('a review row with only above real is refused',
              'more than real' in refused(log, ['review=opus', 'real=5', 'only=7']))
        log(['repo=ship', 'ship=dup', 'task=3', 'engine=driver'])
        check('a second row for one task is refused without a note',
              'already logged' in refused(log, ['repo=ship', 'ship=dup', 'task=3', 'engine=driver']))
        check('with a note it goes in',
              log(['repo=ship', 'ship=dup', 'task=3', 'engine=driver', 'note=redo'])['note'] == 'redo')
        log(['repo=ship', 'ship=dup', 'task=5,6', 'engine=driver'])
        check('a task inside an earlier combined row is a repeat',
              'already logged' in refused(log, ['repo=ship', 'ship=dup', 'task=6', 'engine=driver']))
        wrapped = os.path.join(tmp, 'wrapped')
        os.makedirs(wrapped)
        open(os.path.join(wrapped, 'seconds'), 'w').write('412\n')
        timed = log(['repo=ship', 'review=wonder', 'stage=branch', 'real=1', f'out={wrapped}'])
        check('out=<dir> fills seconds from the wrapper and keeps out of the row',
              timed.get('seconds') == 412 and 'out' not in timed)

        # readers: both branch rows, or a wonder row marked out
        check('readers refuses a ship with no branch rows, naming both',
              readers(['repo=ship', 'ship=r']) == 1)
        log(['repo=ship', 'ship=r', 'review=wonder', 'stage=plan', 'real=1'])
        log(['repo=ship', 'ship=r', 'review=wonder', 'stage=branch', 'real=1'])
        check('a plan row does not count, and one branch reader is not enough',
              readers(['repo=ship', 'ship=r']) == 1)
        log(['repo=ship', 'ship=r', 'review=opus', 'stage=branch', 'real=2'])
        check('both branch readers logged pass', readers(['repo=ship', 'ship=r']) == 0)
        log(['repo=ship', 'ship=m', 'review=wonder', 'stage=branch', 'note=out:5'])
        log(['repo=ship', 'ship=m', 'review=opus', 'stage=branch', 'real=3'])
        check('a wonder row marked out counts when Muse was down', readers(['repo=ship', 'ship=m']) == 0)
        check('readers needs repo and ship', 'repo=' in refused(readers, ['ship=m']))
        log(['repo=ship', 'ship=f', 'review=fable', 'stage=branch', 'real=3', 'only=2'])
        check('a Claude reader alone is not both readers', readers(['repo=ship', 'ship=f']) == 1)
        log(['repo=ship', 'ship=f', 'review=wonder', 'stage=branch', 'real=2', 'only=1'])
        log(['repo=ship', 'ship=f', 'review=wonder', 'stage=plan', 'real=4', 'only=3'])
        check('Fable and Wonder on the branch are both readers', readers(['repo=ship', 'ship=f']) == 0)
        log(['repo=ship', 'ship=g', 'review=fable', 'stage=branch', 'real=5', 'only=5', 'model=claude-fable-5-1'])
        log(['repo=ship', 'ship=g', 'review=wonder', 'stage=branch', 'real=1', 'only=1'])
        log(['repo=ship', 'ship=h', 'review=fable', 'stage=plan', 'real=6', 'only=6'])
        log(['repo=ship', 'ship=h', 'review=wonder', 'stage=plan', 'real=6', 'only=6'])
        log(['repo=ship', 'ship=f', 'review=fable', 'stage=branch', 'real=3', 'only=2', 'note=logged again'])
        log(['repo=ship', 'ship=i', 'review=fable', 'stage=branch', 'real=1', 'only=1'])
        log(['repo=ship', 'ship=i', 'review=wonder', 'stage=branch', 'note=out:5'])
        log(['repo=ship', 'ship=i', 'review=opus', 'stage=branch', 'real=2', 'only=2', 'note=for:wonder'])
        check('with Muse out, the Claude reader and the outage row are both readers', readers(['repo=ship', 'ship=i']) == 0)
        log(['repo=ship', 'ship=j', 'review=wonder', 'stage=branch', 'note=out:5'])
        log(['repo=ship', 'ship=j', 'review=opus', 'stage=branch', 'real=2', 'note=for:wonder'])
        check("a stand-in doesn't fill the Claude reader's seat", readers(['repo=ship', 'ship=j']) == 1)
        log(['repo=ship', 'ship=n', 'review=fable', 'stage=branch', 'real=1'])
        log(['repo=ship', 'ship=n', 'review=wonder', 'stage=branch', 'real=1', 'only=1'])
        for name in ('fable', 'wonder'):
            open(ledger_path(), 'a').write(json.dumps({'ts': '2026-11-08T23:00:00', 'repo': 'ship', 'ship': 'k',
                                                       'review': name, 'stage': 'branch', 'real': 9, 'only': 9}) + '\n')
        check("the trial counts a ship both read on the branch, its plan rows too and a read logged twice once; never "
              "an older Fable's read, a plan-only pair, an outage, a row with no only= or a pair from before it began",
              'Wonder trial: 1 of 20 ships read by Fable 5.2 and Wonder. Real findings only Wonder made: 1 on '
              'branches, 3 on plans; only Fable: 2 and 0' in report())

        # the review card and the branch's own rows: readers, run from the worktree
        cards = os.path.join(tmp, 'cards')
        os.makedirs(cards)
        g = lambda *a: subprocess.run(['git', '-C', cards, *a], check=True, capture_output=True,
                                      env={**os.environ, 'GIT_AUTHOR_DATE': '@1577836800 +0000'})
        commit = lambda files, msg: ([os.makedirs(os.path.dirname(os.path.join(cards, f)), exist_ok=True)
                                      or open(os.path.join(cards, f), 'w').write('x\n') for f in files],
                                     g('add', '-A'), g('-c', 'user.name=t', '-c', 'user.email=t@t',
                                                       'commit', '-q', '--allow-empty', '-m', msg))
        g('init', '-q', '-b', 'main')
        commit([], 'base')
        g('switch', '-q', '-c', 'feature/cel-9-thing')
        commit(['src/x.ts'], 'code')  # the branch began 2020-01-01
        check('a branch that adds no card is missing one', card_missing('cel-9-thing', cards) is True)
        check('outside a repo the check says nothing', card_missing('cel-9-thing', plain) is False)
        g('switch', '-q', '-c', 'feature/cel-9-review-queue')
        commit(['specs/designs/2026-11-05-cel-9-review-queue.html', 'specs/plans/2026-11-05-cel-9-review-queue.md',
                'docs/review.html', 'specs/qa/2026-11-05-cel-90/review.html'], 'not cards')
        check("a slug's storyboard and plan, a bare review.html and another key's card are not its card",
              card_missing('cel-9-review-queue', cards) is True)
        g('switch', '-q', 'feature/cel-9-thing')
        os.chdir(cards)
        try:
            for name in ('wonder', 'opus'):
                open(ledger_path(), 'a').write(json.dumps({'ts': '2019-12-01T00:00:00', 'repo': 'ship',
                                                           'ship': 'cel-9-thing', 'review': name,
                                                           'stage': 'branch', 'real': 1}) + '\n')
            check("a reused slug's rows from before the branch began don't count",
                  readers(['repo=ship', 'ship=cel-9-thing']) == 1)
            log(['repo=ship', 'ship=cel-9', 'review=opus', 'stage=branch', 'real=1'])
            log(['repo=ship', 'ship=cel-91-other', 'review=opus', 'stage=branch', 'real=1'])
            log(['repo=ship', 'ship=cel-9-plan', 'review=opus', 'stage=plan', 'real=1'])
            import contextlib, io
            hint = io.StringIO()
            with contextlib.redirect_stderr(hint):
                readers(['repo=ship', 'ship=cel-9-thing'])
            check("a refusal names the near slug this branch's rows went under, never a plan-only or "
                  "longer-numbered one", 'under ship=cel-9:' in hint.getvalue())
            log(['repo=ship', 'ship=hello-x', 'review=opus', 'stage=branch', 'real=1'])
            hint = io.StringIO()
            with contextlib.redirect_stderr(hint):
                readers(['repo=ship', 'ship=fix-hello-x'])
            check("a refusal names the slug without fix- the rows went under",
                  'under ship=hello-x:' in hint.getvalue())
            log(['repo=ship', 'ship=cel-9-thing', 'review=wonder', 'stage=branch', 'real=1'])
            log(['repo=ship', 'ship=cel-9-thing', 'review=opus', 'real=2'])
            check('readers refuses a landing with both readers but no card',
                  readers(['repo=ship', 'ship=cel-9-thing']) == 1)
            commit(['specs/qa/2026-11-05-cel-9/review.html'], 'card')
            check('a card in a folder named by the key counts', card_missing('cel-9-thing', cards) is False)
            g('switch', '-q', '-c', 'fix/review-queue')
            commit(['specs/designs/2026-11-05-review-queue.html'], 'storyboard')
            check("a fix- slug's storyboard is not its card", card_missing('fix-review-queue', cards) is True)
            commit(['specs/qa/2026-11-07-review-queue/review.html'], 'card')
            check("a fix- slug's card may drop the fix-", card_missing('fix-review-queue', cards) is False)
            g('switch', '-q', '-c', 'fix/review')
            commit(['specs/qa/2026-11-07-fix-review/review.html'], 'card')
            check("a slug inside the word review still finds its card", card_missing('fix-review', cards) is False)
            g('switch', '-q', 'feature/cel-9-thing')
            check('with the card, a branch row with no stage (main\'s rows) counts as a branch read',
                  readers(['repo=ship', 'ship=cel-9-thing']) == 0)
        finally:
            os.chdir(plain)

        # a line the branch adds that names its own worktree, which teardown removes
        open(os.path.join(cards, 'here.ts'), 'w').write(f'const root = "{os.path.realpath(cards)}";\n')
        commit([], 'names the main checkout')
        check("a main checkout's own path outlives the branch, so it is no finding", names_worktree(cards) == [])
        wt = os.path.join(tmp, 'wt-x')
        g('worktree', 'add', '-q', '-b', 'feature/wt-x', wt, 'main')
        wt = os.path.realpath(wt)
        gw = lambda *a: subprocess.run(['git', '-C', wt, *a], check=True, capture_output=True,
                                       env={**os.environ, 'GIT_AUTHOR_DATE': '@1577836800 +0000'})

        def put(name, text):
            os.makedirs(os.path.dirname(os.path.join(wt, name)), exist_ok=True)
            open(os.path.join(wt, name), 'w').write(text)
            gw('add', '-A')
            gw('-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-q', '-m', name)
        put('specs/qa/2026-11-09-wt-x/review.html', 'x\n')
        put('src/ok.ts', f'const a = "{wt}-2/x", b = "{os.path.realpath(cards)}";\n++ {wt}-2\n')
        os.chdir(wt)
        try:
            log(['repo=ship', 'ship=wt-x', 'review=wonder', 'stage=branch', 'real=1'])
            log(['repo=ship', 'ship=wt-x', 'review=opus', 'stage=branch', 'real=1'])
            check("a sibling worktree's path and the main checkout's are not the branch's own",
                  names_worktree(wt) == [] and readers(['repo=ship', 'ship=wt-x']) == 0)
            put('test/fuzz.test.ts', f'const ROOT = process.env.FUZZ_ROOT ?? "{wt}";\n')
            put('test/later.test.ts', f'++ a line of code that begins ++\nconst at = "{wt}/src";\n')
            hint = io.StringIO()
            with contextlib.redirect_stderr(hint):
                code = readers(['repo=ship', 'ship=wt-x'])
            check('readers refuses a branch that adds lines naming its own worktree, and names each file',
                  code == 1 and 'test/fuzz.test.ts, test/later.test.ts names' in hint.getvalue())
        finally:
            os.chdir(plain)

        # a ship: marker, plan, gate runs, logs, on a clock the test sets
        repo = os.path.join(tmp, 'repo')
        subprocess.run(['git', 'init', '-q', repo], check=True)
        stage = os.path.join(repo, '.ship-stage')
        open(stage, 'w').write('plan')
        os.makedirs(os.path.join(repo, 'specs'))
        shipped = os.path.join(repo, 'specs', 'plan.md')
        open(shipped, 'w').write(open(plan_md).read())

        def gate_at(at, ok):
            open(os.path.join(repo, '.ship-gates'), 'a').write(json.dumps({'ts': at, 'ok': ok}) + '\n')

        def at(t, pairs):
            os.environ['ROUTE_NOW'] = str(t)
            try:
                return log(pairs)
            finally:
                del os.environ['ROUTE_NOW']

        t0 = 1_900_000_000
        plan(shipped, now=t0)
        check('plan moves the marker to build:0:9 and starts the clock',
              open(stage).read() == 'build:0:9' and read_route(os.path.join(repo, '.ship-route.json'))['anchor'] == t0)
        gate_at(t0 + 100, False)
        gate_at(t0 + 200, True)
        os.chdir(repo)
        try:
            one = at(t0 + 300, ['task=1', 'engine=driver'])
            at(t0 + 350, ['repo=ship', 'ship=clock', 'review=opus', 'stage=branch', 'real=1'])
            gate_at(t0 + 400, True)
            two = at(t0 + 500, ['task=2', 'engine=driver', 'seconds=7'])
            three = at(t0 + 560, ['task=3', 'engine=driver'])
            fixed = at(t0 + 9000, ['task=2', 'engine=driver', 'note=fix round'])
            fixed_anchor = read_route(os.path.join(repo, '.ship-route.json'))['anchor']
            plan(shipped)
            log(['task=5,6', 'engine=opus'])
            import contextlib, io
            gate_out = io.StringIO()
            with contextlib.redirect_stderr(gate_out):
                code = gate([sys.executable, '-c', 'import sys; sys.exit(3)'])
        finally:
            os.chdir(plain)
        check('log fills seconds from the clock, and first pass and fix rounds from the gate runs',
              one.get('seconds') == 300 and one.get('gates_first_pass') is False and one.get('fix_rounds') == 1)
        check('a value on the command line wins; a review row in between leaves the clock alone',
              two.get('seconds') == 7 and two.get('gates_first_pass') is True and two.get('fix_rounds') == 0)
        check('the next task times from the last task row, and no gate runs leaves first pass out',
              three.get('seconds') == 60 and 'gates_first_pass' not in three)
        check('a fix round re-logged with a note fills nothing and leaves the clock',
              'seconds' not in fixed and 'gates_first_pass' not in fixed and fixed_anchor == t0 + 560)
        check('a re-plan keeps the clock', read_route(os.path.join(repo, '.ship-route.json'))['anchor'] >= t0 + 560)
        check('distinct logged tasks count done, a re-log counts once, a re-route keeps the count, 5,6 counts two',
              open(stage).read() == 'build:5:9')
        os.chdir(repo)
        try:
            open(stage, 'w').write('gate:input')
            log(['task=7', 'engine=driver'])
            check('a task logged while a stop holds the marker joins the done list and leaves the stop',
                  open(stage).read() == 'gate:input' and '7' in open(os.path.join(repo, '.ship-done')).read().split())
            open(stage, 'w').write('build:6:9')
            anchor = read_route(os.path.join(repo, '.ship-route.json'))['anchor']
            locked = os.path.join(tmp, 'locked')
            os.makedirs(locked)
            os.chmod(locked, 0o500)
            os.environ['SHIP_LEDGER'], kept = os.path.join(locked, 'ledger.jsonl'), os.environ['SHIP_LEDGER']
            os.environ['ROUTE_NOW'] = str(t0 + 20000)
            try:
                said = refused(log, ['task=8', 'engine=driver'])
            finally:
                os.environ['SHIP_LEDGER'] = kept
                del os.environ['ROUTE_NOW']
                os.chmod(locked, 0o700)
        finally:
            os.chdir(plain)
        check('a ledger it cannot write says to rerun with the sandbox off, and the clock stays for the rerun',
              'sandbox off' in said and read_route(os.path.join(repo, '.ship-route.json'))['anchor'] == anchor
              and open(stage).read() == 'build:6:9')
        os.chdir(repo)
        try:
            ledger_before, n_before = len(rows()), int(open(stage).read().split(':')[1])
            adopt('8', now=t0 + 30000)
            adopted = (len(rows()) == ledger_before and open(stage).read() == f'build:{n_before + 1}:9'
                       and '8' in open(os.path.join(repo, '.ship-done')).read().split()
                       and read_route(os.path.join(repo, '.ship-route.json'))['anchor'] == t0 + 30000)
            bad, outside = refused(adopt, 'all'), refused(adopt, '12')
        finally:
            os.chdir(plain)
        check('adopt marks a plan task done, writes no ledger row and restarts the clock; '
              'a non-task or a task the plan lacks refuses',
              adopted and 'give plan tasks' in bad and 'not a task' in outside)
        import contextlib, io
        os.chdir(repo)
        try:
            todo_before, todo_after = io.StringIO(), io.StringIO()
            with contextlib.redirect_stderr(todo_before):
                todo_code = readers(['repo=ship', 'ship=routed'])
            done = set(open(os.path.join(repo, '.ship-done')).read().split())
            left = [str(t.get('label', t.get('n'))) for t in read_route(os.path.join(repo, '.ship-route.json'))['tasks']
                    if str(t.get('label', t.get('n'))) not in done]
            no_note = refused(log, ['repo=ship', 'ship=routed', f'task={left[0]}', 'status=parked'])
            for t in left:
                at(t0 + 40000, ['repo=ship', 'ship=routed', f'task={t}', 'status=parked', 'note=needs the Mac'])
            parked_clock = read_route(os.path.join(repo, '.ship-route.json'))['anchor'] == t0 + 40000
            built_later = refused(log, ['repo=ship', 'ship=routed', f'task={left[0]}', 'engine=driver'])
            with contextlib.redirect_stderr(todo_after):
                readers(['repo=ship', 'ship=routed'])
        finally:
            os.chdir(plain)
        check('readers refuses while a plan task is neither built nor parked; a parked one needs its '
              'note, restarts the clock, can still be logged built, and then clears it',
              left and todo_code == 1 and parked_clock and built_later == ''
              and f'plan task {left[0]}' in todo_before.getvalue()
              and 'note=<why' in no_note and 'neither built' not in todo_after.getvalue())
        last = open(os.path.join(repo, '.ship-gates')).read().splitlines()[-1]
        check('gate returns the command\'s exit code and records the run beside the marker',
              code == 3 and json.loads(last)['ok'] is False)
        rows_before = open(os.path.join(repo, '.ship-gates')).read()
        check('a command in one quoted string is refused before it runs or logs',
              'separately' in refused(gate, ['npm run typecheck'])
              and open(os.path.join(repo, '.ship-gates')).read() == rows_before)
        check('gate ends on its own verdict line', gate_out.getvalue().startswith('route gate: FAIL (exit 3) '))
        os.remove(stage)
        plan(shipped)
        check('outside a ship no marker appears', not os.path.exists(stage))
        os.chdir(here)
        check('a ship the self-test runs inside keeps its marker, its done list and its gate runs',
              ship_state() == before)
    print(f'route self-test: {fails} failed')
    return fails == 0


if __name__ == '__main__':
    args = sys.argv[1:]
    if args == ['--selftest']:
        sys.exit(0 if selftest() else 1)
    if len(args) == 2 and args[0] == 'plan':
        print(json.dumps(plan(args[1]), indent=1))
    elif args and args[0] == 'gate':
        sys.exit(gate(args[1:]))
    elif args and args[0] == 'log':
        log(args[1:])
    elif len(args) == 2 and args[0] == 'adopt':
        adopt(args[1])
    elif args and args[0] == 'readers':
        sys.exit(readers(args[1:]))
    elif args == ['report']:
        print(report())
    else:
        sys.exit(__doc__)
