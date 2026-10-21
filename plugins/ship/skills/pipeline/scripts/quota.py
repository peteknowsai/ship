#!/usr/bin/env python3
"""Read the four BUILD quota pools from their usage caches, and say which repos are confidential.

  quota.py               the pools as JSON
  quota.py --table       one line per pool: used, unused, spare rate, reset
  quota.py --selftest

Pools: `anthropic` (Opus: weekly_all and the 5h session), `fable` (weekly_scoped), `openai`
(Codex primary window) and `muse` (weekly, plus its 5h window). Each carries `used`, `unused`,
`rate`, `empty`, `resets_at`, `known` and `note`. The spare rate is budget left per day until
the reset, (100 - used) / max(days to reset, 0.25): "use what would otherwise go unused".

A missing or unparseable cache, or a status-line cache older than 30 minutes, is unknown:
50% used, 3.5 days to reset, and a note saying why. Never an error; the router never blocks
a build. Muse's cache only refreshes when a Muse build runs, so it is judged by its reset
times instead: a window or week whose reset has passed reads 0% used.

Caches: ~/.claude/usage-cache.json, ~/.claude/codex-usage-cache.json and
~/.claude/muse-usage-cache.json, or SHIP_QUOTA_ANTHROPIC, SHIP_QUOTA_CODEX, SHIP_QUOTA_MUSE.
SHIP_QUOTA_NOW (epoch seconds) pins the clock for tests.

confidential(path) reads absolute path prefixes from ~/.config/ship/confidential-paths (or
SHIP_CONFIDENTIAL_PATHS), one per line, # comments, ~ expanded, matched ignoring case. That
file stays on Pete's Mac: this repo is public and must not name client repos. It fails
closed: no list file, or one it can't read, makes every repo confidential; an empty list
makes none.
"""
import json
import os
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone

DAY = 86400
STALE = 30 * 60  # the status line's own staleness rule
EMPTY = 95
OPUS_WEEKLY_CAP = 70  # the default; Pete's number in ~/.config/ship/opus-weekly-cap wins


def opus_weekly_cap():
    """Pete tunes how much of the week Opus may build with (2026-10-21: "I can use more of
    Opus, I just need it to last"): one number in a file, else the default."""
    path = os.environ.get('SHIP_OPUS_CAP') or os.path.expanduser('~/.config/ship/opus-weekly-cap')
    try:
        return float(open(path).read().split()[0])
    except (OSError, ValueError, IndexError):
        return OPUS_WEEKLY_CAP
OPUS_SESSION_CAP = 85
UNKNOWN_USED, UNKNOWN_DAYS = 50, 3.5
WEEK, FIVE_HOURS = 7 * DAY, 5 * 3600


def now():
    return float(os.environ.get('SHIP_QUOTA_NOW') or time.time())


def cache(env, default, stale=True):
    """(data, None) or (None, why it is unknown)."""
    path = os.environ.get(env) or os.path.expanduser(default)
    try:
        age = now() - os.path.getmtime(path)
        if stale and age > STALE:
            return None, f'{path} is {age / 60:.0f} min old'
        return json.load(open(path)), None
    except FileNotFoundError:
        return None, f'{path} missing'
    except (OSError, ValueError) as error:
        return None, f'{path} unreadable: {type(error).__name__}'


def roll(used, reset, window, t):
    """A reset that has passed reads 0% used, the next reset whole windows later."""
    if reset <= t:
        return 0.0, reset + window * (1 + (t - reset) // window)
    return float(used), reset


def epoch(iso):
    return datetime.fromisoformat(iso).timestamp()


def iso(seconds):
    return datetime.fromtimestamp(seconds, timezone.utc).isoformat(timespec='seconds')


def spare(used, reset, t):
    return max(0.0, (100 - used) / max((reset - t) / DAY, 0.25))


def pool(used, reset, t, empty=None, **extra):
    return {'used': used, 'unused': 100 - used, 'rate': round(spare(used, reset, t), 2),
            'empty': used >= EMPTY if empty is None else empty, 'resets_at': iso(reset),
            'known': True, 'note': None, **extra}


def unknown(note, **extra):
    return {'used': UNKNOWN_USED, 'unused': 100 - UNKNOWN_USED, 'rate': round((100 - UNKNOWN_USED) / UNKNOWN_DAYS, 2),
            'empty': False, 'resets_at': None, 'known': False, 'note': note, **extra}


def anthropic_limits(data):
    """{'session'|'weekly_all'|'fable': (percent, reset epoch)} from limits[], with fallbacks."""
    found = {}
    for limit in data.get('limits') or []:
        kind = limit.get('kind')
        if kind == 'weekly_scoped':
            if ((limit.get('scope') or {}).get('model') or {}).get('display_name') != 'Fable':
                continue
            kind = 'fable'
        if kind in ('session', 'weekly_all', 'fable') and limit.get('percent') is not None:
            found[kind] = (limit['percent'], limit['resets_at'])
    for kind, field in (('session', 'five_hour'), ('weekly_all', 'seven_day')):
        block = data.get(field) or {}
        if kind not in found and block.get('utilization') is not None:
            found[kind] = (block['utilization'], block['resets_at'])
    parsed, bad = {}, []
    for kind, (percent, reset) in found.items():  # one bad field costs its own limit, not the others
        try:
            parsed[kind] = (float(percent), epoch(reset))
        except Exception:
            bad.append(kind)
    return parsed, bad


def halve(fable):
    fable['rate'] = round(fable['rate'] / 2, 2)  # Fable drains about twice as fast, Pete 2026-10-16
    return fable


def anthropic_pools(t):
    data, why = cache('SHIP_QUOTA_ANTHROPIC', '~/.claude/usage-cache.json')
    found, bad = anthropic_limits(data) if data is not None else ({}, [])
    why = why or (f"usage-cache.json has unreadable {', '.join(bad)}" if bad else None)
    session = None
    if 'session' in found:
        session, _ = roll(*found['session'], FIVE_HOURS, t)
    session_full = (session or 0) >= OPUS_SESSION_CAP  # blocks Opus even when the weekly is unknown
    if 'weekly_all' in found:
        used, reset = roll(*found['weekly_all'], WEEK, t)
        opus = pool(used, reset, t, session=session, opus_blocked=used >= opus_weekly_cap() or session_full)
    else:
        opus = unknown(why or 'no weekly_all limit', session=session, opus_blocked=session_full)
    if 'fable' in found:
        fable = halve(pool(*roll(*found['fable'], WEEK, t), t))
    else:
        fable = halve(unknown(why or 'no Fable weekly_scoped limit'))
    return opus, fable


def openai_pool(t):
    data, why = cache('SHIP_QUOTA_CODEX', '~/.claude/codex-usage-cache.json')
    if data is None:
        return unknown(why)
    limit = data['rate_limit']  # a bad shape raises; pools() reads that as unknown
    window = limit['primary_window']
    used, reset = roll(window['used_percent'], float(window['reset_at']),
                       window.get('limit_window_seconds') or WEEK, t)
    return pool(used, reset, t, empty=bool(limit.get('limit_reached')) or used >= EMPTY)


def muse_pool(t):
    data, why = cache('SHIP_QUOTA_MUSE', '~/.claude/muse-usage-cache.json', stale=False)
    if data is None:
        return unknown(why, window=None)
    weekly, window = data['weekly'], data.get('window') or {}  # a bad shape raises; pools() reads unknown
    used, reset = roll(weekly['usedPercent'], weekly['resetsAtMs'] / 1000, WEEK, t)
    five = None
    if window.get('usedPercent') is not None:
        span = (window.get('windowDurationMins') or 300) * 60
        five, _ = roll(window['usedPercent'], window['resetsAtMs'] / 1000, span, t)
    return pool(used, reset, t, empty=used >= EMPTY or (five or 0) >= EMPTY, window=five)


def pools():
    """Never raises: a pool whose cache won't parse reads unknown, with the error in its note."""
    t = now()
    found = {}
    try:
        found['anthropic'], found['fable'] = anthropic_pools(t)
    except Exception as error:
        why = f'usage-cache.json unparseable: {type(error).__name__}'
        found['anthropic'] = unknown(why, session=None, opus_blocked=False)
        found['fable'] = halve(unknown(why))
    for name, read, label, extra in (('openai', openai_pool, 'codex-usage-cache.json', {}),
                                     ('muse', muse_pool, 'muse-usage-cache.json', {'window': None})):
        try:
            found[name] = read(t)
        except Exception as error:
            found[name] = unknown(f'{label} unparseable: {type(error).__name__}', **extra)
    return found


def table(found=None):
    lines = [f"{'pool':9} {'used%':>5} {'unused%':>7} {'spare/day':>9}  resets"]
    for name, p in (found or pools()).items():
        when = p['resets_at'][:16].replace('T', ' ') if p['resets_at'] else 'unknown'
        flags = [f"session {p['session']:.0f}%"] if p.get('session') is not None else []
        flags += [f"5h {p['window']:.0f}%"] if p.get('window') is not None else []
        flags += ['EMPTY'] if p['empty'] else []
        flags += ['opus blocked'] if p.get('opus_blocked') else []
        flags += [f"unknown: {p['note']}"] if not p['known'] else []
        lines.append(f"{name:9} {p['used']:>5.0f} {p['unused']:>7.0f} {p['rate']:>9.1f}  {when}"
                     + (f"  ({', '.join(flags)})" if flags else ''))
    return '\n'.join(lines)


def list_path():
    return os.environ.get('SHIP_CONFIDENTIAL_PATHS') or os.path.expanduser('~/.config/ship/confidential-paths')


def list_missing():
    """No list file at all: confidential() keeps every repo away from Muse until one exists."""
    return not os.path.exists(list_path())


def prefixes():
    if list_missing():
        return []
    lines = open(list_path()).read().splitlines()  # an unreadable list raises: confidential() fails closed
    return [os.path.realpath(os.path.expanduser(line.strip())) for line in lines
            if line.strip() and not line.strip().startswith('#')]


def main_checkout(path):
    """The main checkout of the repo holding `path`, None outside a repo. Asks git, else walks up to
    a `.git`: a linked worktree's is a file, `gitdir: <main>/.git/worktrees/<name>`. Raises on a
    `.git` file it can't read that way, so confidential() fails closed."""
    try:
        return os.path.dirname(subprocess.check_output(
            ['git', '-C', path, 'rev-parse', '--path-format=absolute', '--git-common-dir'],
            text=True, stderr=subprocess.DEVNULL).strip())
    except (OSError, subprocess.CalledProcessError):
        pass
    here = os.path.abspath(path)
    while True:
        dot = os.path.join(here, '.git')
        if os.path.isdir(dot):
            return here
        if os.path.isfile(dot):
            line = open(dot).read().strip()
            if not line.startswith('gitdir:'):
                raise ValueError(f'{dot} has no gitdir line')
            main, sep, _ = os.path.join(here, line[len('gitdir:'):].strip()).partition('/.git/worktrees/')
            if not sep:
                raise ValueError(f'{dot} does not point into a .git/worktrees folder')
            return main
        if os.path.dirname(here) == here:
            return None
        here = os.path.dirname(here)


def confidential(path):
    """True when `path`, or the main checkout of the repo holding it, sits under a listed prefix,
    and whenever the list file is missing. An empty list means nothing is confidential."""
    try:
        if list_missing():
            return True
        listed = [p.lower().rstrip('/') + '/' for p in prefixes()]  # macOS paths ignore case
        if not listed:
            return False
        places = [path, main_checkout(path)]
        for place in filter(None, places):
            here = os.path.realpath(place).lower().rstrip('/') + '/'
            if any(here.startswith(p) for p in listed):
                return True
        return False
    except Exception:  # fail closed: a broken list must never send a client repo to a training model
        return True


def selftest():
    fails = 0

    def check(name, ok):
        nonlocal fails
        print(f"  {'ok  ' if ok else 'FAIL'} {name}")
        fails += 0 if ok else 1

    t = 1_800_000_000.0
    with tempfile.TemporaryDirectory() as tmp:
        files = {k: os.path.join(tmp, f'{k}.json') for k in ('anthropic', 'codex', 'muse')}
        os.environ.update(SHIP_QUOTA_NOW=str(t), SHIP_QUOTA_ANTHROPIC=files['anthropic'],
                          SHIP_QUOTA_CODEX=files['codex'], SHIP_QUOTA_MUSE=files['muse'])

        def write(kind, data, age=60):
            json.dump(data, open(files[kind], 'w'))
            os.utime(files[kind], (t - age, t - age))

        def claude(weekly, days, session=10, fable=10, fable_days=None):
            limits = [{'kind': 'session', 'group': 'standard', 'percent': session, 'scope': None,
                       'resets_at': iso(t + 3600).replace('+00:00', '.073623+00:00')},
                      {'kind': 'weekly_all', 'percent': weekly, 'scope': None, 'resets_at': iso(t + days * DAY)},
                      {'kind': 'weekly_scoped', 'percent': fable, 'resets_at': iso(t + (fable_days or days) * DAY),
                       'scope': {'model': {'id': None, 'display_name': 'Fable'}, 'surface': None}}]
            write('anthropic', {'five_hour': {'utilization': 99.0, 'resets_at': iso(t + 60)}, 'limits': limits})

        def codex(used, days, reached=False, age=60):
            write('codex', {'plan_type': 'pro', 'rate_limit': {
                'allowed': True, 'limit_reached': reached, 'secondary_window': None,
                'primary_window': {'used_percent': used, 'limit_window_seconds': 604800,
                                   'reset_after_seconds': int(days * DAY), 'reset_at': int(t + days * DAY)}}}, age)

        def muse(weekly, window, window_reset, age=10 * DAY):
            write('muse', {'observedAtMs': (t - age) * 1000, 'tier': 'pro',
                           'window': {'usedPercent': window, 'resetsAtMs': window_reset * 1000,
                                      'windowDurationMins': 300},
                           'weekly': {'usedPercent': weekly, 'resetsAtMs': (t + 3 * DAY) * 1000}}, age)

        claude(10, 6)
        codex(40, 5.42)
        muse(20, 30, t + 3600)
        p = pools()
        check('10% used with 6 days to reset spares 15.0 a day', p['anthropic']['rate'] == 15.0)
        check('limits[] wins over the five_hour fallback', p['anthropic']['session'] == 10)
        check('40% used with 5.42 days spares ~11.1 and is not empty',
              abs(p['openai']['rate'] - 11.07) < 0.01 and not p['openai']['empty'] and p['openai']['known'])
        check('Fable spares half: 10% with 6 days reads 7.5', p['fable']['rate'] == 7.5)
        check('Muse is known from a ten-day-old file whose resets lie ahead',
              p['muse']['known'] and p['muse']['used'] == 20 and p['muse']['window'] == 30)
        claude(50, 1)
        check('50% used with 1 day spares 50', pools()['anthropic']['rate'] == 50)
        claude(50, 0.1)
        check('0.1 days to reset uses the 0.25 floor: 50% spares 200', pools()['anthropic']['rate'] == 200)
        claude(70, 3)
        check('Opus blocked at weekly 70', pools()['anthropic']['opus_blocked'] is True)
        claude(69, 3, session=85)
        check('Opus blocked at session 85', pools()['anthropic']['opus_blocked'] is True)
        claude(69, 3, session=84)
        check('Opus free at weekly 69 and session 84', pools()['anthropic']['opus_blocked'] is False)
        capfile = os.path.join(tmp, 'opus-cap')
        open(capfile, 'w').write('92\n')
        os.environ['SHIP_OPUS_CAP'] = capfile
        claude(80, 3)
        free80 = pools()['anthropic']['opus_blocked'] is False
        claude(92, 3)
        blocked92 = pools()['anthropic']['opus_blocked'] is True
        open(capfile, 'w').write('not a number')
        claude(80, 3)
        fallback = pools()['anthropic']['opus_blocked'] is True
        del os.environ['SHIP_OPUS_CAP']
        check('a cap file of 92 frees Opus at 80 and blocks it at 92; a bad file falls back to 70',
              free80 and blocked92 and fallback)
        claude(10, 6, fable=95)
        check('Fable at 95 is empty', pools()['fable']['empty'] is True)
        muse(20, 99, t - 60)
        m = pools()['muse']
        check('an expired Muse window reads 0% and is not empty', m['window'] == 0 and not m['empty'])
        muse(20, 96, t + 3600)
        check('Muse window at 96% is empty', pools()['muse']['empty'] is True)
        codex(40, 3, reached=True)
        check('limit_reached is empty', pools()['openai']['empty'] is True)
        os.remove(files['muse'])
        m = pools()['muse']
        check('a missing cache is known false, used 50, noted',
              m['known'] is False and m['used'] == 50 and 'missing' in m['note'] and m['rate'] == 14.29)
        codex(40, 3, age=31 * 60)
        o = pools()['openai']
        check('a status-line cache 31 min old is unknown', o['known'] is False and o['used'] == 50)
        open(files['anthropic'], 'w').write('{"limits": [{"kind": "weekly_all"')
        a = pools()
        check('an unparseable cache is unknown, never a crash',
              a['anthropic']['known'] is False and a['fable']['known'] is False and a['fable']['rate'] == 7.14)
        check('the table prints a line per pool', len(table(a).splitlines()) == 5)
        write('anthropic', {'limits': [{'kind': 'session', 'percent': 99, 'resets_at': iso(t + 3600)}]})
        a = pools()['anthropic']
        check('session 99 blocks Opus with the weekly unknown', a['known'] is False and a['opus_blocked'] is True)
        claude(10, 6, session=90)
        broken = json.load(open(files['anthropic']))
        broken['limits'][1]['percent'] = 'unavailable'
        write('anthropic', broken)
        codex(40, 3)
        codex_data = json.load(open(files['codex']))
        codex_data['rate_limit']['primary_window']['reset_at'] = 1e20
        write('codex', codex_data)
        muse(20, 30, t + 3600)
        muse_data = json.load(open(files['muse']))
        muse_data['weekly']['usedPercent'] = 'n/a'
        write('muse', muse_data, age=10 * DAY)
        try:
            p, crashed = pools(), None
        except Exception as error:
            p, crashed = {}, error
        check('a non-numeric percent, an overflowing reset and a bad Muse field each read unknown, never raise',
              crashed is None and not p['anthropic']['known'] and not p['openai']['known'] and not p['muse']['known']
              and 'weekly_all' in p['anthropic']['note'])
        check('one bad Anthropic field keeps the rest: session 90 still blocks Opus, Fable still known',
              crashed is None and p['anthropic']['opus_blocked'] is True and p['fable']['known'] is True)

        git = lambda *args: subprocess.run(['git', *args], check=True, capture_output=True)
        listed = os.path.join(tmp, 'clients')
        main = os.path.join(listed, 'Peg')
        git('init', '-q', main)
        git('-C', main, '-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-q', '--allow-empty', '-m', 'x')
        worktree = os.path.join(tmp, 'worktrees', 'peg-feature')
        git('-C', main, 'worktree', 'add', '-q', '-b', 'feature', worktree)
        other = os.path.join(tmp, 'other', 'repo')
        git('init', '-q', other)
        peggy = os.path.join(tmp, 'clients-x', 'Peggy2')
        os.makedirs(peggy)
        paths = os.path.join(tmp, 'confidential-paths')
        open(paths, 'w').write(f'# clients\n\n{listed}/Peg\n')
        os.environ['SHIP_CONFIDENTIAL_PATHS'] = paths
        check('a worktree outside the prefix is confidential through its main checkout', confidential(worktree) is True)
        check('the main checkout itself is confidential', confidential(main) is True)
        check('a repo under no prefix is not', confidential(other) is False)
        open(paths, 'w').write(f'{tmp}/clients-x/Peg\n')
        check('/a/Peg does not match /a/Peggy2', confidential(peggy) is False)
        check('a path that does not exist is just a path', confidential(os.path.join(tmp, 'nowhere')) is False)
        open(paths, 'w').write(f'{listed}/Peg\n')
        odd = os.path.join(tmp, 'odd')
        os.makedirs(odd)
        open(os.path.join(odd, '.git'), 'w').write('not a gitdir line\n')
        check('a .git file that will not parse fails closed', confidential(odd) is True)
        path, empty_bin = os.environ.get('PATH', ''), os.path.join(tmp, 'empty-bin')
        os.makedirs(empty_bin)
        os.environ['PATH'] = empty_bin  # git is gone
        try:
            no_git = confidential(worktree), confidential(other)
        finally:
            os.environ['PATH'] = path
        check('with git missing, the worktree .git file still leads to the listed main checkout', no_git[0] is True)
        check('with git missing, a repo under no prefix is still not confidential', no_git[1] is False)
        open(paths, 'w').write(os.path.join(tmp, 'CLIENTS', 'PEG') + '\n')
        check('the prefix matches ignoring case, as macOS paths do', confidential(worktree) is True)
        open(paths, 'w').write('# nothing listed yet\n\n')
        check('an empty or comments-only list means nothing is confidential',
              confidential(worktree) is False and list_missing() is False)
        os.environ['SHIP_CONFIDENTIAL_PATHS'] = os.path.join(tmp, 'no-list')
        check('no list file fails closed: every repo is confidential and list_missing says so',
              confidential(other) is True and list_missing() is True)
    print(f'quota self-test: {fails} failed')
    return fails == 0


if __name__ == '__main__':
    args = sys.argv[1:]
    if args == ['--selftest']:
        sys.exit(0 if selftest() else 1)
    if args == ['--table']:
        print(table())
    elif not args:
        print(json.dumps(pools(), indent=1))
    else:
        sys.exit(__doc__)
