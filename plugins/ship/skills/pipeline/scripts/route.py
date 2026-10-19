#!/usr/bin/env python3
"""Pick each BUILD task's engine from its difficulty, and keep the ledger that judges the pick.

  route.py plan <plan.md>        rank the plan's tasks with the decision model; JSON on stdout, a table on stderr
  route.py log key=value ...     append one task's outcome to the ledger
Inside a ship, `plan` moves the stage marker to build:0:<tasks> and each `log` counts one
task done, so the status line reaches BUILD without the driver remembering to say so.
`plan` also saves its picks to .ship-route.json beside the marker, and `log task=<n>`
fills that task's `score` and `routed` engine from it, so an override shows as
engine != routed and nobody re-asks the router or types a score by hand.
  route.py log review=<opus|sol|...> real=<n> false=<n> only=<n> owned=<n> seconds=<n> ...
                                 append one REVIEW reader's tally for the ship: findings
                                 that were real, false alarms, real ones the other reader
                                 missed, and real ones in the tasks it owned; it never
                                 counts as a BUILD task
  route.py owners <slug>         which branch reader owns which of the ship's tasks: Sol
                                 the ones a Claude model wrote, the Claude reader GPT's,
                                 both the ones Muse wrote, by the ledger's last engine per task
  route.py report                the ledger as a table by engine and difficulty, by
                                 pool, then the reviewers'
  route.py quota                 the four pools, one line each (quota.py --table)
  route.py reader                fable while Fable's week lags the main pool's, else opus:
                                 the Claude model that reads the branch at REVIEW
  route.py --selftest

The router ranks the routable tasks by their difficulty score, cuts them into TIERS by
rank (easy, middle, hard), and picks an engine inside each tier: the hard tier is fixed
(the hardest 3/4 to Opus, the rest to Fable, then the Opus cap and Fable-empty
overrides), the middle tier alternates Fable and Wonder Full down the rank, and the easy tier is dealt
across Wonder Full and Astra by each pool's spare rate from quota.py. A confidential repo never reaches Muse; an empty pool's engines leave
the middle and easy tiers, and a tier with no engine left escalates one tier up. A task
whose heading says (driver) or (inline) stays with the driver and is not ranked. Scores
come from SubQ Snap (Pete, 2026-10-16), else Jev when SubQ has no key or fails. Neither
answering: every task goes to fable, tier unknown, and `fallback` says why, because a
router must never stop a build.

Keys: SUBQ_API_KEY else keychain service "subq"; TYPESAFE_API_KEY else keychain "typesafe".
The ledger is ~/.claude/ship-ledger.jsonl, or SHIP_LEDGER.
"""
import json
import math
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
LEVELS = [
    'Transcription: the task text already contains the code to write; one file, no decisions left for the worker.',
    'Contained change: one or two files, following a pattern the repo already has; the tests named in the task prove it.',
    'Integration: several files wired together; the worker has to find where things connect and choose the shape itself.',
    'Cross-cutting or stateful: concurrency, persistence, protocols, lifecycles or changes that ripple through callers; '
    'mistakes tend to show only at runtime.',
    'Novel and risky: a mechanism with no precedent in the repo, a security, auth or money boundary, or subtle failure '
    'modes that need careful reasoning to get right.',
]
# Each tier's share of the ranked tasks, easiest first; the last tier takes the rest and
# always gets the hardest task. Pete, 2026-10-17: no cheap builders. Sol only reviews and
# Spark is out; Fable moves down into the middle in Astra's place, Wonder Full ranks over
# Astra, and Opus keeps its share (hard, 3/4). Before it (10-16): three tiers across Claude Code, Codex
# and Muse, each tier's engines picked by spare quota (hard is fixed 3/4 Opus). Before
# it (10-05): Fable 5.1 took the easier half and Opus 5.5 the harder; Sonnet 25 / Fable
# 50 / Opus 25 (10-02); thirds of Sonnet, Fable and Opus (10-01), and the same day a
# quarter each to Sol, Sonnet, Fable and Opus. Codex left BUILD then because its sandbox
# made the driver rerun the tests on most of Sol's tasks, as it had on Astra's; before
# that, Astra 33%, Fable 42%, Opus 25%.
TIERS = [('easy', 1 / 3), ('middle', 1 / 3), ('hard', 1 / 3)]
ENGINES = {'easy': ['wonder', 'astra'], 'middle': ['fable', 'wonder'], 'hard': ['opus', 'fable']}
POOL = {'opus': 'anthropic', 'fable': 'fable', 'astra': 'openai', 'wonder': 'muse',
        'sol': 'openai', 'spark': 'muse'}  # sol and spark build nothing now; old ledger rows keep their pool
HARD_OPUS_SHARE = 0.75
HARD_OPUS_SHARE_FABLE_BEHIND = 0.5


def fable_behind(pools):
    """Fable has used less of its week than the main Anthropic pool. The account stops when
    the main pool runs out, whatever Fable has left, so Fable must drain first (Pete,
    2026-10-17): while it lags, it takes all of middle and half of hard, and reads the branch."""
    f, a = pools.get('fable', {}), pools.get('anthropic', {})
    return bool(f.get('known') and a.get('known') and not f.get('empty') and f['used'] < a['used'])
FALLBACK_ENGINE = 'fable'
QUESTION = 'How hard is this coding task for an AI coding agent to complete correctly on the first attempt?'
# Jev, the smaller window, takes 64k tokens per request, and pasted code runs near 3 characters a token. Each
# task's question repeats the rubric (~800 characters), so a request packs tasks until
# text plus questions reach this, and a big plan takes several requests. The scores sit
# on one fixed rubric, so tasks from different requests still rank against each other.
REQUEST_CHARS = 120_000
TASK_CHARS = 20_000
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
            tasks.append({'n': n, 'label': label, 'title': title, 'lines': [],
                          'driver': bool(re.search(r'\((driver|inline)\)', title, re.I)),
                          'inline': bool(re.search(r'\(inline\)', title, re.I))})
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


def ask_scores(routable):
    """Scores by task number, and the model that gave them. Raises on any failure."""
    if os.environ.get('ROUTE_RESPONSE'):  # the self-test's canned reply
        reply = json.load(open(os.environ['ROUTE_RESPONSE']))
        answers, model = reply['answers'], reply.get('model')
    else:
        def build(batch):
            state = {'tasks': {f"t{t['n']}": (t['title'] + '\n' + t['body'])[:TASK_CHARS] for t in batch}}
            questions = {f"t{t['n']}": {'type': 'score', 'criteria': LEVELS,
                                        'instructions': {'task': f"`tasks.t{t['n']}`", 'question': QUESTION}}
                         for t in batch}
            return state, questions
        answers, model = decide(routable, build,
                                lambda t: min(len(t['title']) + len(t['body']) + 1, TASK_CHARS) + QUESTION_CHARS)
    scores = {}
    for t in routable:
        answer = answers[f"t{t['n']}"]
        if not isinstance(answer.get('score'), (int, float)) or isinstance(answer['score'], bool):
            raise ValueError(f"t{t['n']}: no numeric score in {answer!r}"[:200])
        scores[t['n']] = answer
    return scores, model


def assign(routable, scores):
    """Rank by score, ties in plan order, and cut at each tier's running share. Returns
    {n: tier} in rank order, easiest first; the hardest task is always in the last tier."""
    ranked = sorted(routable, key=lambda t: (scores[t['n']]['score'], t['n']))
    n, total, cuts = len(ranked), 0, []
    for _, share in TIERS[:-1]:
        total += share
        cuts.append(min(n - 1, int(n * total + 0.5)))
    return {t['n']: TIERS[sum(i >= c for c in cuts)][0] for i, t in enumerate(ranked)}


def deal(tasks, engines, pools):
    """Share `tasks` (rank order) across `engines` in proportion to each pool's spare rate:
    largest remainder, ties to the first engine, then dealt round-robin down the rank so
    every engine sees both ends of the tier."""
    rates = [pools[POOL[e]]['rate'] for e in engines]
    weights = rates if sum(rates) > 0 else [1] * len(engines)
    shares = [len(tasks) * w / sum(weights) for w in weights]
    counts = [int(s) for s in shares]
    for i in sorted(range(len(engines)), key=lambda i: counts[i] - shares[i])[:len(tasks) - sum(counts)]:
        counts[i] += 1
    out, i = {}, 0
    for n in tasks:
        while not counts[i % len(engines)]:
            i += 1
        out[n] = engines[i % len(engines)]
        counts[i % len(engines)] -= 1
        i += 1
    return out


def pick(tiers, pools, confidential):
    """An engine for every task in `tiers` ({n: tier}, rank order) from the pools quota.py
    read. Returns ({n: engine}, {n: tier the task landed in}, notes). Pure: no I/O."""
    engines, landed, notes = {}, {}, []
    for name, p in pools.items():
        if not p['known']:
            notes.append(f"{name} quota unknown ({p['note']}): counted as {p['used']:.0f}% used")
    if confidential:
        notes.append('confidential repo: Muse (wonder) left out')
    carried = []
    for tier, _ in TIERS:
        tasks = carried + [n for n, t in tiers.items() if t == tier]
        carried = []
        if not tasks:
            continue
        candidates = [e for e in ENGINES[tier] if not (confidential and POOL[e] == 'muse')]
        if tier == 'hard':  # fixed split, then the caps; this tier never escalates or empties
            share = HARD_OPUS_SHARE_FABLE_BEHIND if fable_behind(pools) else HARD_OPUS_SHARE
            k = min(math.ceil(share * len(tasks)), max(len(tasks) - 1, 1))
            chosen = {n: 'opus' if i >= len(tasks) - k else 'fable' for i, n in enumerate(tasks)}
            capped, drained = pools['anthropic'].get('opus_blocked'), pools['fable']['empty']
            if capped:
                chosen = dict.fromkeys(tasks, 'fable')
                notes.append('Opus capped (weekly_all >= 70% or session >= 85%): hard tasks on fable'
                             + (', though the Fable pool is empty too' if drained else ''))
            elif drained:
                chosen = dict.fromkeys(tasks, 'opus')
                notes.append('Fable pool empty: hard tasks on opus')
        else:
            candidates = [e for e in candidates if not pools[POOL[e]]['empty']]
            if not candidates:
                notes.append(f'{tier} tier has no engine left: {len(tasks)} task(s) escalate one tier up')
                carried = tasks
                continue
            # ponytail: middle alternates down the rank, Fable first, so Fable's share holds even
            # when Muse's spare rate dwarfs it (Pete, 2026-10-17); easy alone deals by spare rate
            if tier == 'middle' and 'fable' in candidates and fable_behind(pools):
                chosen = dict.fromkeys(tasks, 'fable')
            elif tier == 'middle':
                chosen = {n: candidates[i % len(candidates)] for i, n in enumerate(tasks)}
            else:
                chosen = deal(tasks, candidates, pools)
        engines.update(chosen)
        landed.update(dict.fromkeys(tasks, tier))
    return engines, landed, notes


def read_quota(where):
    """(pools, confidential, notes) from quota.py, never raising: a broken quota reader
    counts every pool as unknown and the repo as confidential, and says so."""
    notes = []
    try:
        pools = quota.pools()
        confidential = quota.confidential(where)  # also checks the main checkout of the repo holding `where`
        if getattr(quota, 'list_missing', lambda: False)():
            notes.append('no confidential list at ~/.config/ship/confidential-paths: Muse is off until it exists '
                         '(an empty file means none)')
    except Exception as error:
        why = f'{type(error).__name__}: {error}'[:200]
        pools = {name: {'used': 50, 'unused': 50, 'rate': 14.29, 'empty': False, 'resets_at': None, 'known': False,
                        'note': f'quota.py failed: {why}', **({'session': None, 'opus_blocked': False}
                                                               if name == 'anthropic' else {})}
                 for name in ('anthropic', 'fable', 'openai', 'muse')}
        confidential = True
        notes.append(f'quota.py failed ({why}): every pool counted 50% used, Muse engines left out')
    return pools, confidential, notes


def plan(path):
    try:
        tasks = parse_tasks(open(path).read())
    except OSError as error:
        raise SystemExit(f'route: {error}')
    if not tasks:
        raise SystemExit(f'route: no "### Task" headings in {path}')
    where = os.path.dirname(os.path.abspath(path))
    routable = [t for t in tasks if not t['driver']]
    pools, confidential, notes = read_quota(where)
    fallback, model, scores, engines, tiers = None, None, {}, {}, {}
    if routable:
        try:
            scores, model = ask_scores(routable)
            engines, tiers, picked = pick(assign(routable, scores), pools, confidential)
            notes += picked
        except Exception as error:  # a router must never stop a build
            fallback = f'{type(error).__name__}: {error}'
            scores = {}
            engines = {t['n']: FALLBACK_ENGINE for t in routable}
            tiers = {t['n']: 'unknown' for t in routable}
    out = []
    for t in tasks:
        s = scores.get(t['n'], {})
        # an (inline) task is small but still code: a Fable subagent writes it while Fable has
        # quota, sparing the driver's Opus (Pete, 2026-10-18); (driver) stays with the driver
        engine = (('driver' if pools['fable']['empty'] else 'fable') if t['inline']
                  else 'driver' if t['driver'] else engines[t['n']])
        out.append({'n': t['n'], 'label': t['label'], 'title': t['title'], 'engine': engine, 'tier': tiers.get(t['n']),
                    'pool': POOL.get(engine), 'score': s.get('score'), 'confidence': s.get('confidence')})
    for row in out:
        score = '  -  ' if row['score'] is None else f"{row['score']:.2f}"
        print(f"{row['engine']:6} {row['tier'] or '-':7} {score}  {row['title'][:80]}", file=sys.stderr)
    print(quota.table(pools), file=sys.stderr)
    for note in notes:
        print(f'route: {note}', file=sys.stderr)
    if fallback:
        print(f'ROUTER DOWN: no decision model answered, every task on {FALLBACK_ENGINE} ({fallback})',
              file=sys.stderr)
    result = {'model': model, 'fallback': fallback, 'tasks': out, 'quota': pools, 'quota_notes': notes}
    saved = route_file(where)
    if saved:
        try:
            with open(saved, 'w') as f:
                json.dump(result, f)
        except OSError as error:  # the table on stdout still carries the picks
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
        raise SystemExit(f"route log: only={row['only']} is more than real={row['real']}; "
                         "count each reader's findings the other missed, from both lists")
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
        row.setdefault('score', picked['score'])
        row.setdefault('routed', picked['engine'])
    elif 'task' in row and 'routed' not in row and row.get('engine') != 'driver':  # EXPRESS routes nothing
        print('route log: no saved route for this task here, so score and routed are not filled '
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


READERS = {'anthropic': ['sol'], 'fable': ['sol'], 'openai': ['claude'], 'muse': ['claude', 'sol']}


def owners(slug):
    """Each branch reader's tasks: the other lab's work, Muse's to both (Pete, 2026-10-16)."""
    last = {}
    try:
        for line in open(ledger_path()):
            try:
                row = json.loads(line)
            except ValueError:
                continue
            if row.get('ship') == slug and 'task' in row and 'review' not in row and 'engine' in row:
                for n in str(row['task']).split(','):
                    last[n.strip()] = row['engine']
    except FileNotFoundError:
        pass
    owned = {}
    for n, engine in last.items():
        pool = 'anthropic' if engine == 'driver' else POOL.get(engine)
        for reader in READERS.get(pool, ['claude', 'sol']):  # an unknown engine gets both
            owned.setdefault(reader, []).append((n, engine))
    key = lambda t: (0, int(t[0])) if t[0].isdigit() else (1, t[0])
    return {r: sorted(ts, key=key) for r, ts in sorted(owned.items())}


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
        T, DAY = 1_800_000_000, quota.DAY
        caches = {k: os.path.join(tmp, f'{k}.json') for k in ('anthropic', 'codex', 'muse')}
        no_list, empty_list = os.path.join(tmp, 'no-list'), os.path.join(tmp, 'empty-list')
        open(empty_list, 'w').close()  # an empty list: nothing is confidential
        os.environ.update(SHIP_QUOTA_NOW=str(T), SHIP_QUOTA_ANTHROPIC=caches['anthropic'],
                          SHIP_QUOTA_CODEX=caches['codex'], SHIP_QUOTA_MUSE=caches['muse'],
                          SHIP_CONFIDENTIAL_PATHS=empty_list)

        def write_caches(weekly=10, session=10, fable=10, codex=40, codex_days=1, muse=20, muse_days=4):
            """Spare rates: anthropic 15, fable 7.5, openai 60, muse 20 by default."""
            data = {'anthropic': {'limits': [
                {'kind': 'session', 'percent': session, 'resets_at': quota.iso(T + 3600)},
                {'kind': 'weekly_all', 'percent': weekly, 'resets_at': quota.iso(T + 6 * DAY)},
                {'kind': 'weekly_scoped', 'percent': fable, 'resets_at': quota.iso(T + 6 * DAY),
                 'scope': {'model': {'display_name': 'Fable'}}}]},
                'codex': {'rate_limit': {'primary_window': {'used_percent': codex, 'reset_at': T + codex_days * DAY,
                                                            'limit_window_seconds': 7 * DAY}}},
                'muse': {'weekly': {'usedPercent': muse, 'resetsAtMs': (T + muse_days * DAY) * 1000},
                         'window': {'usedPercent': 10, 'resetsAtMs': (T + 3600) * 1000}}}
            for kind, body in data.items():
                json.dump(body, open(caches[kind], 'w'))
                os.utime(caches[kind], (T - 60, T - 60))
        write_caches()

        def P(rate=10.0, used=50, empty=False, known=True, note=None, **extra):
            return {'used': used, 'unused': 100 - used, 'rate': rate, 'empty': empty, 'resets_at': None,
                    'known': known, 'note': note, **extra}

        def pools(**over):
            base = {'anthropic': P(15, opus_blocked=False), 'fable': P(7.5), 'openai': P(60), 'muse': P(20)}
            base.update(over)
            return base
        nine = [{'n': n} for n in range(1, 10)]
        tiers = assign(nine, {n: {'score': n} for n in range(1, 10)})
        check('nine tasks split 3/3/3 by rank',
              [tiers[n] for n in range(1, 10)] == ['easy'] * 3 + ['middle'] * 3 + ['hard'] * 3)
        engines, landed, notes = pick(tiers, pools(), False)
        check('hard: 2 of 3 to Opus, the hardest among them, 1 to Fable',
              [engines[n] for n in (7, 8, 9)] == ['fable', 'opus', 'opus'])
        check('middle alternates fable and wonder whatever the spare rates, fable first',
              [engines[n] for n in (4, 5, 6)] == ['fable', 'wonder', 'fable'])
        check('easy deals the same way on wonder and astra, and sol and spark build nothing',
              [engines[n] for n in (1, 2, 3)] == ['wonder', 'astra', 'astra'] and not notes
              and not {'sol', 'spark'} & set(engines.values()))
        behind = pools(anthropic=P(15, used=40, opus_blocked=False), fable=P(7.5, used=21))
        engines, _, notes = pick(tiers, behind, False)
        check('Fable behind the main pool: middle all fable, hard half opus, easy unchanged',
              fable_behind(behind) and {engines[n] for n in (4, 5, 6)} == {'fable'}
              and [engines[n] for n in (7, 8, 9)] == ['fable', 'opus', 'opus']
              and [engines[n] for n in (1, 2, 3)] == ['wonder', 'astra', 'astra'])
        twelve = assign([{'n': n} for n in range(1, 13)], {n: {'score': n} for n in range(1, 13)})
        got12 = pick(twelve, behind, False)[0]
        check('twelve tasks with Fable behind: hard 2 opus + 2 fable, middle 4 fable',
              [got12[n] for n in (9, 10, 11, 12)] == ['fable', 'fable', 'opus', 'opus']
              and {got12[n] for n in (5, 6, 7, 8)} == {'fable'})
        check('Fable not behind when level, unknown or empty',
              not fable_behind(pools()) and not fable_behind(pools(fable=P(7.5, used=21, known=False)))
              and not fable_behind(pools(anthropic=P(15, used=40), fable=P(0, used=21, empty=True))))
        hard = lambda n, **over: list(pick({i: 'hard' for i in range(1, n + 1)}, pools(**over), False)[0].values())
        check('a hard tier of 1 is opus, of 3 is 2 opus + 1 fable, of 4 is 3 + 1',
              hard(1) == ['opus'] and hard(3) == ['fable', 'opus', 'opus'] and hard(4) == ['fable'] + ['opus'] * 3)
        engines, landed, notes = pick(tiers, pools(), True)
        check('confidential drops wonder: easy all astra, middle all fable',
              {engines[n] for n in (1, 2, 3)} == {'astra'} and {engines[n] for n in (4, 5, 6)} == {'fable'}
              and any('confidential' in n for n in notes))
        engines, _, notes = pick(tiers, pools(anthropic=P(15, used=72, opus_blocked=True)), False)
        check('the Opus cap moves hard to fable, noted',
              {engines[n] for n in (7, 8, 9)} == {'fable'} and any('Opus capped' in n for n in notes))
        engines, _, notes = pick(tiers, pools(fable=P(0, used=96, empty=True)), False)
        check('an empty Fable pool moves hard to opus', {engines[n] for n in (7, 8, 9)} == {'opus'})
        engines, landed, notes = pick(tiers, pools(anthropic=P(0, used=99, opus_blocked=True),
                                                   fable=P(0, used=99, empty=True)), False)
        check('the hard tier never escalates: both Anthropic pools full is all fable, noted',
              {engines[n] for n in (7, 8, 9)} == {'fable'} and landed[9] == 'hard'
              and any('Fable pool is empty too' in n for n in notes))
        engines, _, _ = pick(tiers, pools(muse=P(0, used=97, empty=True)), False)
        check('muse empty sends middle all to fable and easy all to astra',
              {engines[n] for n in (4, 5, 6)} == {'fable'} and {engines[n] for n in (1, 2, 3)} == {'astra'})
        engines, landed, notes = pick(tiers, pools(muse=P(0, empty=True), openai=P(0, empty=True)), False)
        check('both easy pools empty escalates easy to middle, where fable takes it',
              {landed[n] for n in range(1, 7)} == {'middle'} and {engines[n] for n in range(1, 7)} == {'fable'}
              and sum('escalate' in n for n in notes) == 1)
        engines, landed, notes = pick(tiers, pools(muse=P(0, empty=True), fable=P(0, empty=True)), False)
        check('fable and muse empty: easy on astra, middle escalates to hard, all opus',
              {engines[n] for n in (1, 2, 3)} == {'astra'} and {landed[n] for n in (4, 5, 6)} == {'hard'}
              and {engines[n] for n in range(4, 10)} == {'opus'})
        engines, _, _ = pick({1: 'middle', 2: 'middle', 3: 'middle'},
                             pools(fable=P(14.29, known=False, note='x'), muse=P(14.29, known=False, note='x')), False)
        check('a middle of 3 with unknown pools still alternates, the extra to fable',
              list(engines.values()) == ['fable', 'wonder', 'fable'])
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
        result = plan(plan_md)
        got = {t['n']: t['engine'] for t in result['tasks']}
        tier = {t['n']: t['tier'] for t in result['tasks']}
        check('the driver task stays with the driver', got[3] == 'driver' and tier[3] is None)
        small = os.path.join(tmp, 'small.md')
        open(small, 'w').write('### Task 1: a config line (inline)\n\nx\n\n### Task 2: wire 1 to 3 (driver)\n\ny\n')
        picked_small = [(t['engine'], t['tier']) for t in plan(small)['tasks']]
        check('an (inline) task goes to fable unranked, a (driver) task stays with the driver',
              picked_small == [('fable', None), ('driver', None)])
        check('eight routable tasks cut 3/2/3 by rank',
              sorted(n for n in tier if tier[n] == 'easy') == [1, 5, 7]
              and sorted(n for n in tier if tier[n] == 'middle') == [4, 9]
              and sorted(n for n in tier if tier[n] == 'hard') == [2, 6, 8])
        check('plan picks from the live pools: easy wonder/astra, middle fable/wonder, hard 2 opus + fable',
              got == {1: 'wonder', 5: 'astra', 7: 'astra', 9: 'fable', 4: 'wonder', 8: 'fable', 2: 'opus', 6: 'opus',
                      3: 'driver'})
        check('the JSON carries pool per task and the quota pools',
              {t['pool'] for t in result['tasks'] if t['n'] in (5, 7)} == {'openai'}
              and result['quota']['openai']['rate'] == 60 and result['quota_notes'] == [])
        os.remove(caches['muse'])
        result = plan(plan_md)
        check('unknown quota counts 50 and is noted, never an error',
              result['quota']['muse']['used'] == 50 and not result['fallback']
              and any('muse quota unknown' in n for n in result['quota_notes']))
        write_caches()
        os.environ['SHIP_CONFIDENTIAL_PATHS'] = no_list
        result = plan(plan_md)
        os.environ['SHIP_CONFIDENTIAL_PATHS'] = empty_list
        check('no confidential list at all keeps Muse off and says so',
              not any(t['pool'] == 'muse' for t in result['tasks'])
              and any('no confidential list' in n for n in result['quota_notes']))
        real_pools = quota.pools

        def broken():
            raise RuntimeError('boom')
        quota.pools = broken
        try:
            result = plan(plan_md)
        finally:
            quota.pools = real_pools
        check('a quota.py that raises never stops the build: pools unknown, Muse off, noted',
              not result['fallback'] and not any(t['pool'] == 'muse' for t in result['tasks'])
              and {t['engine'] for t in result['tasks'] if t['tier'] in ('easy', 'middle')} == {'fable', 'astra'}
              and all(not p['known'] for p in result['quota'].values())
              and any('quota.py failed (RuntimeError: boom)' in n for n in result['quota_notes']))
        for name, answers in [('bare numbers', {f't{n}': 1 for n in scores}),
                              ('string scores', {f't{n}': {'score': str(s)} for n, s in scores.items()})]:
            json.dump({'answers': answers}, open(reply, 'w'))
            result = plan(plan_md)
            check(f'a reply of {name} falls back instead of crashing', result['fallback'] and
                  {(t['engine'], t['tier']) for t in result['tasks'] if t['n'] != 3} == {('fable', 'unknown')})
        few = os.path.join(tmp, 'few.md')
        open(few, 'w').write('### Task list\n\nan overview, not a task\n\n' +
                             ''.join(f'### Task {n}: t\n\n```md\n### Task 99: an example inside a fence\n```\n\n'
                                     for n in range(1, 6)))
        json.dump({'answers': {f't{n}': {'score': n} for n in range(1, 6)}}, open(reply, 'w'))
        got = [t['engine'] for t in plan(few)['tasks']]
        check('a fenced heading and "### Task list" are not tasks', len(got) == 5)
        check('five tasks spread over every tier', got == ['wonder', 'astra', 'fable', 'fable', 'opus'])
        one = os.path.join(tmp, 'one.md')
        open(one, 'w').write('### Task 1: t\n\nx\n')
        check('a lone task is hard, on opus',
              [(t['engine'], t['tier']) for t in plan(one)['tasks']] == [('opus', 'hard')])
        del os.environ['ROUTE_RESPONSE']
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
        os.environ.update(SUBQ_API_KEY='', TYPESAFE_API_KEY='', ROUTE_NO_KEYCHAIN='1')
        result = plan(plan_md)
        check('no key falls back to fable, tier unknown', result['fallback'] and
              {(t['engine'], t['tier']) for t in result['tasks'] if t['n'] != 3} == {('fable', 'unknown')})
        log(['repo=ship', 'task=2', 'engine=fable', 'score=3.4', 'seconds=300', 'fix_rounds=1', 'gates_first_pass=false'])
        open(ledger_path(), 'a').write('{"half a line\n')
        log(['repo=ship', 'task=1', 'engine=astra', 'score=0.8', 'seconds=120', 'fix_rounds=0', 'gates_first_pass=True'])
        sol = log(['repo=ship', 'task=9', 'engine=sol', 'score=1.2', 'fix_rounds=2', 'gates_first_pass=True'])
        old = log(['repo=ship', 'task=7', 'engine=sonnet', 'score=1.0'])
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
        json.dump({'model': 'jev-test', 'answers': {f't{n}': {'score': s, 'confidence': 0.7}
                                                    for n, s in scores.items()}}, open(reply, 'w'))
        os.environ['ROUTE_RESPONSE'] = reply
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
        for pairs in (['ship=xl', 'task=1', 'engine=opus'], ['ship=xl', 'task=2', 'engine=astra'],
                    ['ship=xl', 'task=3', 'engine=driver'], ['ship=xl', 'task=4,5', 'engine=spark'],
                    ['ship=xl', 'task=2', 'engine=fable', 'verdict=redone'], ['ship=other', 'task=9', 'engine=sol'],
                    ['ship=xl', 'task=6', 'engine=sol'], ['ship=xl', 'review=sol', 'real=1']):
            log(pairs)
        got = {r: [n for n, _ in ts] for r, ts in owners('xl').items()}
        check('owners: Sol gets Claude-written tasks, Opus GPT-written, both Muse, last engine wins',
              got == {'claude': ['4', '5', '6'], 'sol': ['1', '2', '3', '4', '5']})
        try:
            log(['review=opus', 'real=1', 'owned=2'])
            bad = False
        except SystemExit:
            bad = True
        check('a review row with owned above real is refused', bad)
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
        check('log fills the score and the routed engine from the saved picks',
              row.get('score') == 3.4 and row.get('routed') == 'opus' and row['engine'] == 'opus')
        check('an override shows as engine differing from routed, and an unknown task logs unfilled',
              moved.get('routed') == 'wonder' and moved['engine'] == 'opus' and 'routed' not in missing)
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
    elif len(args) == 2 and args[0] == 'owners':
        for reader, tasks in owners(args[1]).items():
            print(f"{reader:5} " + ', '.join(f'{n} ({e})' for n, e in tasks))
    elif args == ['report']:
        print(report())
    elif args == ['reader']:  # the Claude model that reads the branch at REVIEW
        print('fable' if fable_behind(quota.pools()) else 'opus')
    elif args == ['quota']:
        print(quota.table())
    else:
        sys.exit(__doc__)
