#!/usr/bin/env python3
"""Settled calls per repo, so a later ship doesn't re-ask Pete what he already decided.

  decisions.py relevant "<idea>" [N] [--ship <slug>]
                                             the N decisions (default 6) that bear on the idea;
                                             --ship records what that ship was shown
  decisions.py used <slug> <id> "<what it changed>"
                                             record that a shown decision changed what the ship did
  decisions.py tally <slug>                  "recall=<shown> used=<n>" for route.py log, distinct
                                             decisions each; exit 1 when the ship ran no recall
  decisions.py recent [N]                    the N newest active decisions (default 5)
  decisions.py log '<json>'                  record one: {"decision","rationale","source"}
  decisions.py supersede <id> [<id> ...] '<json>'
                                             record one decision that replaces every named
                                             one; the old ones stop showing
  ... --file <path>                          log or supersede with the JSON read from a file,
                                             which keeps quotes out of a shell the worktree
                                             guard refuses
  decisions.py stale                         active calls, made before an engine or tool was
                                             retired, that give it a ship job
  decisions.py --selftest

Run from inside the repo. Each repo has one append-only event log,
~/.claude/ship-decisions/<owner>-<repo>.jsonl (SHIP_DECISIONS overrides the directory),
named from the origin remote, else from the main checkout's folder; a repo that gains a
remote keeps the folder-named log, merged in on first use and left as <folder>.jsonl.merged (a run lost its log, 2026-10-13). The format is the
one gstack's decision store used, so its history migrated as is.

`relevant` asks Jev, TypeSafe's decision model, to score every active decision against
the idea, because the newest five hide the old call that settles the thing being changed.
Any failure falls back to `recent`, so recall never blocks a run. `relevant` and `recent`
mark a stale call `[stale: ...]`: the skill's current text wins over it.
Key: TYPESAFE_API_KEY else keychain service "typesafe".
"""
import datetime
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
import uuid


# The decision model: TypeSafe's newest Jev. SubQ is out (Pete, 2026-11-03: "all jev").
JEV = {'url': 'https://api.typesafe.ai/v1/systemone', 'model': 'jev-latest',
       'env': 'TYPESAFE_API_KEY', 'keychain': 'typesafe'}
# Jev takes 64k tokens per request but only 32k for the state plus any one question
# (docs.typesafe.ai/models), and dense text runs 2.5 characters a token, so a request
# packs items until text plus questions reach this. 442 decisions take about 10 requests.
REQUEST_CHARS = 60_000
QUESTION_CHARS = 800
# What ship stopped using as a builder, reader or tester, and when. A call made before that
# date that gives it one of those jobs was settled for a world that's gone; one made on or
# after it already knows. A product call naming the same model (cells-app's Codex login,
# its Muse Spark picker) isn't one, so only a clause of the decision itself that pairs the
# name with a ship job counts.
RETIRED = [
    ('Codex', '2026-10-22', r'\bcodex\b'),
    ('Astra', '2026-10-22', r'\bastra\b'),
    ('Sol', '2026-10-22', r'\bsol\b'),  # Spark isn't here: it's a live product model (Muse Spark) in cells-app
    ('Sonnet', '2026-10-24', r'\bsonnet\b'),
    ('Fable', '2026-10-29', r'\bfable\b'),  # 5.1's build window; 5.2 reads since 2026-11-09, which no call that old means
    ('SubQ', '2026-11-03', r'\bsubq\b'),
    ('quota pacing', '2026-11-05', r'quota\.py|\bquota[ -](?:pac|pool|window)|\bpac\w*\b.{0,30}\bquota'),  # not a product's billing quota
    ('the shipboard', '2026-11-05', r'shipboard|board\.cells\.md'),
]
SHIP_JOB = re.compile(r'\b(build|builds|built|builder|review|reviews|reviewer|reader|reads|qa|parity|tests?|'
                      r'testing|verify|verifies|fix|fixes|brief|briefs|dispatch|task|tasks|engine|'
                      r'launch|launches|pace|paces|departure)\b')


def store():
    def run(*args):
        return subprocess.run(args, capture_output=True, text=True).stdout.strip()
    root = os.environ.get('SHIP_DECISIONS') or os.path.expanduser('~/.claude/ship-decisions')
    os.makedirs(root, exist_ok=True)
    at = lambda slug: os.path.join(root, re.sub(r'[^A-Za-z0-9._-]', '-', slug.replace('.', '-')) + '.jsonl')
    common = run('git', 'rev-parse', '--path-format=absolute', '--git-common-dir')
    folder = at(os.path.basename(os.path.dirname(common)) if common else os.path.basename(os.getcwd()))
    match = re.search(r'[:/]([^/:]+)/([^/]+?)(?:\.git)?/?$', run('git', 'remote', 'get-url', 'origin'))
    if not match:
        return folder
    path = at(f'{match.group(1)}-{match.group(2)}')
    if os.path.exists(folder):
        seen = {e.get('id') for e in events(path)}
        for e in events(folder):
            if e.get('id') not in seen:
                append(path, e)
        os.rename(folder, folder + '.merged')
    return path


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


def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='seconds')


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
    event = {'scope': 'repo', 'source': 'user', **payload, 'id': str(uuid.uuid4()), 'kind': 'decide', 'date': now()}
    if supersedes:
        event['supersedes'] = supersedes
    return event


def supersede(path, prefixes, raw):
    """One new decision replacing every named one, written after every id resolves."""
    olds = list(dict.fromkeys(full_id(path, p) for p in prefixes))
    event = decide(raw, olds[0] if len(olds) == 1 else olds)
    append(path, event)
    for old in olds:
        append(path, {'id': str(uuid.uuid4()), 'kind': 'supersede', 'supersedes': old, 'date': now()})
    return event, olds


def staleness(e):
    """The retired engines or tools this call gives a ship job, if it predates their retirement."""
    day = str(e.get('date', ''))[:10]
    clauses = [c for c in re.split(r'[.;:,()]', str(e.get('decision', '')).lower()) if SHIP_JOB.search(c)]
    return [name for name, since, pattern in RETIRED
            if day < since and any(re.search(pattern, c) for c in clauses)]


def show(chosen):
    lines = []
    for e in chosen:
        gone = staleness(e)
        flag = f" [stale: gives {', '.join(gone)} a ship job; the skill's text wins]" if gone else ''
        lines.append(f"- {e['decision']} ({e.get('source', '?')}, {e.get('date', '')[:10]}) [{e['id'][:8]}]{flag}")
        if e.get('rationale'):
            lines.append(f"  why: {e['rationale']}")
    return '\n'.join(lines)


def recent(path, n):
    return show(sorted(active(path), key=lambda e: e.get('date', ''), reverse=True)[:n])


def stale(path):
    return show(e for e in active(path) if staleness(e))


def api_key():
    key = os.environ.get(JEV['env'])
    if key is not None or os.environ.get('DECISIONS_NO_KEYCHAIN'):
        return key or None
    try:
        return subprocess.check_output(['security', 'find-generic-password', '-s', JEV['keychain'], '-w'],
                                       text=True, stderr=subprocess.DEVNULL).strip() or None
    except (OSError, subprocess.CalledProcessError):
        return None


def batches(items, cost):
    """Split items so each request stays under REQUEST_CHARS."""
    batch, size = [], 0
    for item in items:
        if batch and size + cost(item) > REQUEST_CHARS:
            yield batch
            batch, size = [], 0
        batch.append(item)
        size += cost(item)
    if batch:
        yield batch


def ask_jev(items, build, cost=lambda item: QUESTION_CHARS):
    """Ask Jev about every item; build(batch) gives one request's (state, questions).
    Returns answers by question name. Raises when Jev doesn't answer."""
    key = api_key()
    if not key:
        raise RuntimeError(f"Jev: no key (env {JEV['env']} or keychain \"{JEV['keychain']}\")")
    answers = {}
    try:
        for batch in batches(items, cost):
            state, questions = build(batch)
            body = json.dumps({'model': JEV['model'], 'state': state, 'questions': questions}).encode()
            request = urllib.request.Request(JEV['url'], body, {'Authorization': f'Bearer {key}',
                                                                'Content-Type': 'application/json'})
            with urllib.request.urlopen(request, timeout=30) as response:
                answers.update(json.load(response)['answers'])
    except Exception as error:
        code = getattr(error, 'code', None)  # an HTTPError's status
        why = ('out of credits; tell Pete now' if code == 402 else
               f"key rejected (env {JEV['env']} or keychain \"{JEV['keychain']}\")" if code == 401 else
               f'{type(error).__name__}: {error}')
        raise RuntimeError(f'Jev: {why}') from error
    return answers


RELEVANCE = [
    'Unrelated to the idea',
    'Same area, but does not settle anything the idea needs',
    'Settles a choice the idea will face, or rules out an approach to it',
]


def scores(idea, decisions):
    """The decision model's relevance score for each decision, in order. Raises on any failure."""
    if os.environ.get('DECISIONS_RESPONSE'):  # the self-test's canned reply
        answers = json.load(open(os.environ['DECISIONS_RESPONSE']))['answers']
    else:
        def build(batch):
            chunk = {f'd{i}': decisions[i]['decision'][:2000] for i in batch}
            questions = {k: {'type': 'score', 'criteria': RELEVANCE, 'instructions': {
                'decision': f'`decisions.{k}`', 'idea': '`idea`',
                'question': 'Does this settled decision constrain or answer something the new idea will have to decide?'}}
                for k in chunk}
            return {'idea': idea, 'decisions': chunk}, questions
        answers = ask_jev(list(range(len(decisions))), build,
                          lambda i: min(len(decisions[i]['decision']), 2000) + QUESTION_CHARS)
    out = []
    for i in range(len(decisions)):
        score = answers[f'd{i}']['score']
        if not isinstance(score, (int, float)) or isinstance(score, bool):
            raise ValueError(f'd{i}: no numeric score')
        out.append(score)
    return out


def pick(path, idea, n):
    decisions = active(path)
    if not decisions:
        return []
    try:
        ranked = sorted(zip(scores(idea, decisions), decisions), key=lambda p: -p[0])
    except Exception as error:  # recall must never block a run
        print(f'decisions: no decision model answered ({error}); showing the newest instead', file=sys.stderr)
        return sorted(decisions, key=lambda e: e.get('date', ''), reverse=True)[:n]
    return [e for _, e in ranked[:n]]


def relevant(path, idea, n, ship=None):
    chosen = pick(path, idea, n)
    if ship:  # in the repo's log, not the worktree, so a resume, a compaction or teardown keeps it
        append(path, {'id': str(uuid.uuid4()), 'kind': 'shown', 'ship': ship,
                      'ids': [e['id'] for e in chosen], 'date': now()})
    return show(chosen)


def mark(path, ship, prefix, note):
    """A use of one decision the ship was shown, superseded since or not (a reversal is a use)."""
    if not note.strip():
        raise SystemExit('decisions: say what the decision changed')
    seen = {i for e in events(path) if e.get('kind') == 'shown' and e.get('ship') == ship
            for i in e.get('ids', []) if i.startswith(prefix)}
    if len(seen) != 1:
        raise SystemExit(f'decisions: "{prefix}" matches {len(seen)} decisions {ship} was shown')
    event = {'id': str(uuid.uuid4()), 'kind': 'used', 'ship': ship, 'of': seen.pop(),
             'note': note, 'date': now()}
    append(path, event)
    return event


def tally(path, ship):
    """Distinct decisions shown to the ship and used by it; None when it ran no recall."""
    # ponytail: a reused slug sums both runs; scope by run once that skews the report
    evs = [e for e in events(path) if e.get('ship') == ship]
    runs = [e for e in evs if e.get('kind') == 'shown']
    shown = {i for e in runs for i in e.get('ids', [])}
    used = {e.get('of') for e in evs if e.get('kind') == 'used'}
    return (len(shown), len(used)) if runs else None


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

    def refused(fn, *args):
        try:
            fn(*args)
        except SystemExit as error:
            return str(error)
        return ''

    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, 'd.jsonl')
        first = decide('{"decision":"A","rationale":"because"}')
        append(path, first)
        check('a logged decision shows', '- A (user' in recent(path, 5))
        replacement, _ = supersede(path, [first['id'][:8]], '{"decision":"B","rationale":"changed mind"}')
        shown = recent(path, 5)
        check('a superseded decision stops showing', '- B' in shown and '- A' not in shown)
        check('a short id prefix resolves', full_id(path, replacement['id'][:8]) == replacement['id'])
        open(path, 'a').write('{"half\n')
        check('a broken line is skipped', len(active(path)) == 1)
        for name, raw in [('without a rationale', '{"decision":"no why"}'), ('that is not an object', '["a"]')]:
            check(f'a decision {name} is refused', bool(refused(decide, raw)))
        forged = decide('{"decision":"C","rationale":"r","id":"aaaa","kind":"note"}')
        check('a payload cannot set its own id or kind', forged['id'] != 'aaaa' and forged['kind'] == 'decide')

        three = os.path.join(tmp, 'three.jsonl')
        olds = [decide(json.dumps({'decision': f'old {i}', 'rationale': 'r'})) for i in range(3)]
        for e in olds:
            append(three, e)
        merged, gone = supersede(three, [e['id'][:8] for e in olds] + [olds[0]['id'][:8]],
                                 '{"decision":"one call","rationale":"r"}')
        left = active(three)
        check('supersede with three ids writes one decision and retires all three, a repeat id once',
              [e['decision'] for e in left] == ['one call'] and len(gone) == 3
              and merged['supersedes'] == [e['id'] for e in olds])
        before = open(three).read()
        check('an id that matches nothing refuses before anything is written',
              'matches 0' in refused(supersede, three, [merged['id'][:8], 'ffffffff'], '{"decision":"x","rationale":"r"}')
              and open(three).read() == before)

        old_engines = os.path.join(tmp, 'engines.jsonl')
        for text, day in [('Astra builds the mechanical tasks', '2026-10-01'),
                          ('No Codex, no Fable, no Sonnet: Opus writes and reviews', '2026-11-05'),
                          ('Groom paces launches to the quota', '2026-10-19'),
                          ('The model picker offers only Muse Spark 1.3', '2026-10-01'),
                          ('Billing quota tests run nightly', '2026-10-01'),
                          ('Sidebar stays on the left', '2026-09-01')]:
            append(old_engines, {**decide(json.dumps({'decision': text, 'rationale': 'Sol reviewed it'})), 'date': day})
        listed = stale(old_engines)
        check('stale lists calls giving a retired engine a ship job, not newer calls, product calls or rationales',
              'Astra builds' in listed and 'paces launches' in listed and 'Opus writes' not in listed
              and 'model picker' not in listed and 'Billing quota' not in listed and 'Sidebar' not in listed)
        check('recent marks a stale call in place', '[stale: gives Astra a ship job' in recent(old_engines, 5))

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
        relevant(many, 'pick a voice', 2, ship='s1')
        json.dump({'answers': {'d0': {'score': 1.9}, 'd1': {'score': 0.1},
                               'd2': {'score': 0.2}, 'd3': {'score': 0.3}}}, open(reply, 'w'))
        relevant(many, 'pick a voice', 2, ship='s1')  # a resumed ship asks again
        voice = active(many)[0]['id']
        mark(many, 's1', voice[:8], 'skipped the voice question')
        supersede(many, [voice[:8]], '{"decision":"new voice rule","rationale":"r"}')
        mark(many, 's1', voice[:8], 'reversed it out loud')
        check('tally counts distinct decisions shown across reruns and used, a reversal included, once each',
              tally(many, 's1') == (3, 1) and tally(many, 's2') is None)
        check('a use that says nothing, or of a decision the ship was never shown, is refused',
              'say what' in refused(mark, many, 's1', voice[:8], ' ')
              and 'matches 0' in refused(mark, many, 's2', voice[:8], 'never shown'))
        empty = os.path.join(tmp, 'empty.jsonl')
        relevant(empty, 'anything', 6, ship='s3')
        check('a recall over no decisions still tallies as zero', tally(empty, 's3') == (0, 0))
        del os.environ['DECISIONS_RESPONSE']

        sizes, urls, models, broke = [], [], [], []

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
            sent = json.loads(request.data)
            models.append(sent['model'])
            if broke:
                raise urllib.error.HTTPError(request.full_url, broke[-1], 'refused', {}, None)
            sizes.append(len(sent['questions']))
            return Reply(json.dumps({'answers': {k: {'score': 1} for k in sent['questions']}}).encode())
        real, kept = urllib.request.urlopen, {k: os.environ.get(k) for k in (JEV['env'], 'DECISIONS_NO_KEYCHAIN')}
        urllib.request.urlopen = fake
        os.environ.update({JEV['env']: 'k', 'DECISIONS_NO_KEYCHAIN': '1'})
        ask = lambda b: ({}, {f'q{i}': {} for i in b})  # noqa: E731
        try:
            answers = ask_jev(list(range(40)), ask)
            split = ask_jev(list(range(3)), ask, lambda i: REQUEST_CHARS // 2 + 1)
            failures = []
            for key, code in (('k', 402), ('k', 401), ('', 0)):
                broke.append(code)
                os.environ[JEV['env']] = key
                try:
                    ask_jev([0], ask)
                except RuntimeError as error:
                    failures.append(str(error))
        finally:
            urllib.request.urlopen = real
            for k, v in kept.items():
                os.environ.pop(k, None) if v is None else os.environ.__setitem__(k, v)
        check('jev-latest at TypeSafe answers every item, a new request each REQUEST_CHARS',
              set(urls) == {'https://api.typesafe.ai/v1/systemone'} and set(models) == {'jev-latest'}
              and len(answers) == 40 and sizes == [40, 1, 1, 1] and len(split) == 3)
        check('a Jev 402 says to tell Pete, a 401 names where the key came from, no key raises too',
              len(failures) == 3 and 'out of credits; tell Pete now' in failures[0]
              and 'key rejected (env TYPESAFE_API_KEY or keychain "typesafe")' in failures[1] and 'no key' in failures[2])

        repo, here = os.path.join(tmp, 'app'), os.getcwd()
        os.environ['SHIP_DECISIONS'] = os.path.join(tmp, 'store')
        subprocess.run(['git', 'init', '-q', repo])
        os.chdir(repo)
        try:
            append(store(), decide('{"decision":"before the remote","rationale":"r"}'))
            subprocess.run(['git', 'remote', 'add', 'origin', 'git@github.com:acme/app.git'])
            append(os.path.join(tmp, 'store', 'acme-app.jsonl'), decide('{"decision":"after","rationale":"r"}'))
            shown = recent(store(), 5)
            check('a repo that gains a remote merges its old log in, once', store().endswith('acme-app.jsonl')
                  and '- before the remote' in shown and '- after' in shown and shown.count('before the remote') == 1
                  and os.path.exists(os.path.join(tmp, 'store', 'app.jsonl.merged')))
        finally:
            os.chdir(here)
            del os.environ['SHIP_DECISIONS']
        check('--file reads the JSON from a file', payload(['log', '--file', reply]) == ['log', open(reply).read()])
        check('a missing --file exits with one line',
              "can't read it" in refused(payload, ['log', '--file', os.path.join(tmp, 'absent.json')]))
    print(f'decisions self-test: {fails} failed')
    return fails == 0


def payload(args):
    if len(args) >= 2 and args[-2] == '--file':
        try:
            return args[:-2] + [open(args[-1]).read()]
        except OSError as error:
            raise SystemExit(f"decisions: --file {args[-1]}: can't read it ({error.strerror})")
    return args


if __name__ == '__main__':
    args = payload(sys.argv[1:])
    if args == ['--selftest']:
        sys.exit(0 if selftest() else 1)
    ship = None
    if args and args[0] == 'relevant' and '--ship' in args:
        at = args.index('--ship')
        ship = args[at + 1] if at + 1 < len(args) else ''
        if not ship.strip():
            sys.exit("decisions: --ship takes the ship's slug")
        args = args[:at] + args[at + 2:]
    if args and args[0] == 'relevant' and len(args) in (2, 3):
        if len(args) == 3 and not args[2].isdigit():
            sys.exit('decisions: relevant takes a positive count')
        print(relevant(store(), args[1], int(args[2]) if len(args) == 3 else 6, ship))
    elif args and args[0] == 'used':
        if len(args) != 4:
            sys.exit('decisions: used takes <slug> <id> "<what it changed>"')
        event = mark(store(), args[1], args[2], args[3])
        print(f"decisions: {args[1]} used {event['of'][:8]}")
    elif args and args[0] == 'tally':
        if len(args) != 2:
            sys.exit('decisions: tally takes <slug>')
        counts = tally(store(), args[1])
        if not counts:
            sys.exit(f'decisions: {args[1]} ran no recall, so log no recall row')
        print(f'recall={counts[0]} used={counts[1]}')
    elif args and args[0] == 'recent' and len(args) <= 2:
        if len(args) == 2 and not args[1].isdigit():
            sys.exit('decisions: recent takes a positive count')
        print(recent(store(), int(args[1]) if len(args) == 2 else 5))
    elif args == ['stale']:
        print(stale(store()) or 'decisions: no stale calls')
    elif len(args) == 2 and args[0] == 'log':
        event = decide(args[1])
        append(store(), event)
        print(f"decisions: logged {event['id'][:8]}")
    elif len(args) >= 3 and args[0] == 'supersede':
        event, olds = supersede(store(), args[1:-1], args[-1])
        print(f"decisions: logged {event['id'][:8]}, superseding {', '.join(o[:8] for o in olds)}")
    else:
        sys.exit(__doc__)
