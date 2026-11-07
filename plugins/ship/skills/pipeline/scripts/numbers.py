#!/usr/bin/env python3
"""numbers.py <transcript.jsonl> <number>[@word]...: where each number came from.

After a compaction, every number a PR body or card states is rechecked against recorded
output. A number counts only where something the session didn't write showed it: a tool
result, a background task's report, another session's message or Pete's. A match is the
session's own number read back, such as its PR viewed again, when the words just before it
or just after it, up to three, are words the session had already written beside that
number in a message or a tool call. A bare match, with no words beside it, is its own when
the call that printed it had the number in it. Order alone can't tell: muse-spaces' first
20000 was `s.length>20000` in a script, hours before its fuzz printed 20000 runs. A line of
this script's own report never counts, wherever it turns up. A match stops at digits, so 97%
is not 197%. A number the session worked out in its head, such as a sum, may be in no
output, so check its parts. A bare number matches noise, such as a clock time or a grep line
number: 43@test counts a 43 only with a word starting "test" among the three words of
letters on either side, on its own line, as plain-bot-names' vitest line had and its ps
listing didn't. The Read tool's line numbers never count. Prints the newest three sources
per number; exit 1 when one has none, 2 on a bad argument. The recap prints the transcript's
path.
numbers.py --selftest
"""
import json, re, sys

REPORT = re.compile(r'\s*(?:\d+(?:\t|→))?== \S+: ')  # a report line, bare or read back with line numbers


def events(path):
    """(kind, text, call): 'src' for output the session didn't write, with the input of the
    tool call that printed it when there is one; 'own' for what the session wrote."""
    calls = {}
    for line in open(path, encoding='utf-8', errors='replace'):
        try:
            o = json.loads(line)
        except ValueError:
            continue
        if not isinstance(o, dict):
            continue
        a = o.get('attachment')
        if isinstance(a, dict) and a.get('type') == 'queued_command' and isinstance(a.get('prompt'), str):
            yield 'src', a['prompt'], ''  # background results and other sessions' messages
            continue
        msg = o.get('message') if isinstance(o.get('message'), dict) else {}
        content = msg.get('content')
        origin = o.get('origin') if isinstance(o.get('origin'), dict) else {}
        if (o.get('type') == 'user' and not o.get('isCompactSummary')
                and origin.get('kind') in ('human', 'peer', 'task-notification')):
            yield 'src', content if isinstance(content, str) else ' '.join(
                x.get('text', '') for x in content or [] if isinstance(x, dict) and x.get('type') == 'text'), ''
            continue  # Pete's words, another session's message, a background result
        if not isinstance(content, list):
            continue
        mine = (msg.get('role') or o.get('type')) == 'assistant'
        for c in content:
            if not isinstance(c, dict):
                continue
            if c.get('type') == 'tool_result':
                body = c.get('content')
                yield 'src', body if isinstance(body, str) else ' '.join(
                    x.get('text', '') for x in body or [] if isinstance(x, dict)), calls.pop(c.get('tool_use_id'), '')
            elif mine and c.get('type') == 'text':
                yield 'own', c.get('text') or '', ''
            elif mine and c.get('type') == 'tool_use':
                text = json.dumps(c.get('input'), ensure_ascii=False)
                if c.get('id'):
                    calls[c['id']] = text
                yield 'own', text, ''


def words(s):
    s = re.sub(r'\\[nrt]', ' ', s)              # a line break inside a tool call's JSON
    s = re.sub(r'(?m)^\s*\d+(?:\t|→)', ' ', s)  # the Read tool's line numbers
    return re.findall(r'\d+|[a-z]+', s.lower())


def find(path, nums):
    near = {n: n.partition('@')[2].lower() for n in nums}
    pats = {n: re.compile(r'(?<!\d)(?<!\d[.,])' + re.escape(n.partition('@')[0]) + r'(?!\d)(?![.,]\d)')
            for n in nums}
    hits = {n: [] for n in nums}
    echoes = {n: 0 for n in nums}
    seen = {n: set() for n in nums}  # the words the session wrote beside each number
    for kind, text, call in events(path):
        for n, p in pats.items():
            for m in p.finditer(text):
                head = re.split(r'\n|\\n', text[max(0, m.start() - 200):m.start()])[-1]
                tail = re.split(r'\n|\\n', text[m.end():m.end() + 200])[0]
                if not head.strip() and tail[:1] in ('\t', '→'):
                    continue  # the Read tool's line number, not a number the file holds
                before = words(text[max(0, m.start() - 200):m.start()])[-3:]
                after = words(text[m.end():m.end() + 200])[:3]
                if kind == 'own':
                    seen[n].update([('<',) + tuple(before[-k:]) for k in range(1, len(before) + 1)]
                                   + [('>',) + tuple(after[:k]) for k in range(1, len(after) + 1)])
                elif REPORT.match(text, text.rfind('\n', 0, m.start()) + 1):
                    continue
                elif near[n] and not any(w.startswith(near[n]) for w in re.findall(r'[a-z]+', head.lower())[-3:]
                                         + re.findall(r'[a-z]+', tail.lower())[:3]):
                    continue
                elif (('<',) + tuple(before) in seen[n] or ('>',) + tuple(after) in seen[n]
                        if before or after else p.search(call)):
                    echoes[n] += 1
                else:
                    hits[n].append(text[max(0, m.start() - 160):m.end() + 100].replace('\n', ' '))
    return {n: hits[n][-3:] for n in nums}, echoes


def main(argv):
    if argv[1:] == ['--selftest']:
        return selftest()
    if len(argv) < 3:
        print(__doc__.strip().splitlines()[0], file=sys.stderr)
        return 2
    for a in argv[2:]:
        n, at, w = a.partition('@')
        if not n or at and not re.fullmatch(r'[A-Za-z]+', w):
            print(f'numbers.py: {a}: a number, and after @ one word of letters', file=sys.stderr)
            return 2
    hits, echoes = find(argv[1], argv[2:])
    missing = 0
    for n, ctxs in hits.items():
        if not ctxs:
            missing += 1
            print(f'== {n}: in no output the session didn\'t write'
                  + (', only its own words read back' if echoes[n] else ''))
        for ctx in ctxs:
            print(f'== {n}: ...{ctx}...')
    return 1 if missing else 0


def selftest():
    import os, tempfile, io, contextlib
    said = lambda t: {'type': 'assistant', 'message': {'role': 'assistant', 'content': [{'type': 'text', 'text': t}]}}
    result = lambda body, i=None: {'type': 'user', 'message': {'role': 'user', 'content': [{'type': 'tool_result', 'tool_use_id': i, 'content': body}]}}
    ran = lambda i, inp: {'type': 'assistant', 'message': {'role': 'assistant', 'content': [{'type': 'tool_use', 'id': i, 'input': inp}]}}
    note = lambda kind, t: {'type': 'user', 'origin': {'kind': kind}, 'message': {'content': t}}
    rows = [
        result('growth 197% overall'),
        said('Posting 83% and $15.32'),
        ran('n1', {'command': 'numbers.py t.jsonl 83%'}), result("== 83%: in no output the session didn't write", 'n1'),
        note('task-notification', "    12\t== 83%: in no output the session didn't write"),  # its report, read back
        result('## Evidence\n\n**posting 83%** and $15.32'),  # its own words, read back from the PR
        ran('w1', {'file_path': 'pr.md', 'content': 'Fuzz held.\n16/16 tests\n| lcp | 820ms |'}),
        ran('r1', {'file_path': 'pr.md'}), result('     1\tFuzz held.\n     2\t16/16 tests\n     3\t| lcp | 820ms |', 'r1'),
        ran('c1', {'command': 'node -e "if (s.length>20000) big()"'}),
        result('seed 1, 20000 runs each'),  # muse-spaces: real output after an unrelated write
        ran('j1', {'command': 'jq .runs out.json'}), result('20000\n', 'j1'),  # bare, from a call that never had it
        ran('e2', {'command': 'echo 4.39:1'}), result('4.39:1', 'e2'),  # bare, from a call that did
        result('cache hit 97% of 120 calls'),
        result([{'type': 'text', 'text': 'tokens 61,280'}]),
        {'type': 'user', 'message': {'content': 'plain prompt with 1,280'}},
        note('peer', 'ran PACK=swain 16/16'),
        {'type': 'user', 'isCompactSummary': True, 'origin': {'kind': 'human'}, 'message': {'content': 'summary says 55%'}},
        {'type': 'attachment', 'attachment': {'type': 'queued_command', 'prompt': 'reader: 42 findings'}},
        result('      Tests  43 passed'), result('Tests  2 failed | 41 passed (43)'),  # and noise:
        result('STARTED Sat Nov  7 09:26:43 2026'), result('41- the tests below\n43- which merges main'),
        result('elapsed 0:43'), result('    43\tthe tests below'), result('total 43\ntests below'),
        result('run 7 old'), result('run 7 mid'), result('run 7 a'), result('run 7 new'),
        ran('e1', {'command': 'echo 61,280 97%'}), result('61,280 97%', 'e1'),  # what it just typed, printed back
    ]
    fd, path = tempfile.mkstemp(suffix='.jsonl')
    with os.fdopen(fd, 'w') as f:
        f.write('not json\n[]\n' + '\n'.join(json.dumps(r) for r in rows) + '\n')
    try:
        nums = ['97%', '61,280', '1,280', '$15.32', '83%', '42', '7', '16/16', '55%', '20000', '820', '4.39:1',
                '43', '43@test', '43@build']
        hits, echoes = find(path, nums)
        assert hits['16/16'] == ['ran PACK=swain 16/16'], hits['16/16']   # another session; not its own file read back
        assert hits['820'] == [] and echoes['820'] == 1, hits['820']       # 820ms, from the file it wrote
        assert hits['55%'] == [], hits['55%']                              # a compaction summary is no source
        assert hits['97%'] == ['cache hit 97% of 120 calls'], hits['97%']  # not 197%, not the echo after
        assert hits['61,280'] == ['tokens 61,280'], hits['61,280']         # a block result
        assert hits['1,280'] == [], hits['1,280']                          # inside 61,280; a prompt isn't output
        assert hits['$15.32'] == [] and echoes['$15.32'], hits['$15.32']   # only ever its own
        assert hits['83%'] == [] and echoes['83%'] == 1, (hits['83%'], echoes['83%'])  # its PR read back; its reports skipped
        assert hits['20000'] == ['seed 1, 20000 runs each', '20000 '], hits['20000']  # an unrelated write blocks nothing
        assert hits['4.39:1'] == [] and echoes['4.39:1'] == 1, hits['4.39:1']
        assert hits['42'] == ['reader: 42 findings'], hits['42']           # a background report
        assert hits['7'] == ['run 7 mid', 'run 7 a', 'run 7 new'], hits['7']  # the newest three
        assert len(hits['43']) == 3 and 'Tests' not in ' '.join(hits['43']), hits['43']  # noise crowds it out
        assert hits['43@test'] == ['      Tests  43 passed', 'Tests  2 failed | 41 passed (43)'], hits['43@test']
        assert hits['43@build'] == [], hits['43@build']
        with contextlib.redirect_stdout(io.StringIO()) as out:
            rc = main(['numbers.py', path, '97%', '83%'])
        assert rc == 1 and "83%: in no output the session didn't write, only its own words read back" in out.getvalue(), out.getvalue()
        with contextlib.redirect_stdout(io.StringIO()):
            assert main(['numbers.py', path, '97%', '42']) == 0
        with contextlib.redirect_stderr(io.StringIO()):
            assert main(['numbers.py', path, '43@e2e']) == 2 and main(['numbers.py', path, '@test']) == 2
    finally:
        os.unlink(path)
    print('numbers selftest: ok')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
