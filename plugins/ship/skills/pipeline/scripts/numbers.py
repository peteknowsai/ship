#!/usr/bin/env python3
"""numbers.py <transcript.jsonl> <number>...: where each number came from.

After a compaction, every number a PR body or card states is rechecked against recorded
output. A number counts only where something the session didn't write (a tool result, a
background task's report, another session's message, Pete's) showed it, and not as its own
words read back: a match whose three words on either side the session had already written,
in a message or a tool call, is a number it posted coming back (its PR, read again), and
this script's own output never counts. Order alone can't tell: muse-spaces' first 20000 was
`s.length>20000` in a script, hours before its fuzz printed 20000 runs. A match stops at
digits, so 97% is not 197%. A number the session worked out (a sum, a share) is in no
output: check its parts. Prints the nearest three sources per number; exit 1 when one has
none. The recap prints the transcript's path.
numbers.py --selftest
"""
import json, re, sys


def events(path):
    """('src', text) for output the session didn't write, ('own', text) for what it did."""
    checks = set()  # ids of this script's own runs, whose output is never a source
    for line in open(path, encoding='utf-8', errors='replace'):
        try:
            o = json.loads(line)
        except ValueError:
            continue
        if not isinstance(o, dict):
            continue
        a = o.get('attachment')
        if isinstance(a, dict) and a.get('type') == 'queued_command' and isinstance(a.get('prompt'), str):
            yield 'src', a['prompt']  # background results and other sessions' messages
            continue
        msg = o.get('message') if isinstance(o.get('message'), dict) else {}
        content = msg.get('content')
        origin = o.get('origin') if isinstance(o.get('origin'), dict) else {}
        if (o.get('type') == 'user' and not o.get('isCompactSummary')
                and origin.get('kind') in ('human', 'peer', 'task-notification')):
            yield 'src', content if isinstance(content, str) else ' '.join(
                x.get('text', '') for x in content or [] if isinstance(x, dict) and x.get('type') == 'text')
            continue  # Pete's words, another session's message, a background result
        if not isinstance(content, list):
            continue
        mine = (msg.get('role') or o.get('type')) == 'assistant'
        for c in content:
            if not isinstance(c, dict):
                continue
            if c.get('type') == 'tool_result':
                if c.get('tool_use_id') in checks:
                    continue
                body = c.get('content')
                yield 'src', body if isinstance(body, str) else ' '.join(
                    x.get('text', '') for x in body or [] if isinstance(x, dict))
            elif mine and c.get('type') == 'text':
                yield 'own', c.get('text') or ''
            elif mine and c.get('type') == 'tool_use':
                text = json.dumps(c.get('input'), ensure_ascii=False)
                if 'numbers.py' in text:
                    checks.add(c.get('id'))
                yield 'own', text


def words(s):
    return re.findall(r'[0-9a-z]+', s.lower())


def find(path, nums):
    pats = {n: re.compile(r'(?<!\d)(?<!\d[.,])' + re.escape(n) + r'(?!\d)(?![.,]\d)') for n in nums}
    hits = {n: [] for n in nums}
    echoes = {n: 0 for n in nums}
    own = ' '  # every word the session has written so far, markup and punctuation dropped
    for kind, text in events(path):
        if kind == 'own':
            own += ' '.join(words(text)) + ' '
            continue
        for n, p in pats.items():
            for m in p.finditer(text):
                num = words(m.group())
                before = words(text[max(0, m.start() - 200):m.start()])[-3:]
                after = words(text[m.end():m.end() + 200])[:3]
                sides = [s for s in (before and before + num, after and num + after) if s] or [num]
                if any(' ' + ' '.join(s) + ' ' in own for s in sides):
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
    ran = lambda i, cmd: {'type': 'assistant', 'message': {'role': 'assistant', 'content': [{'type': 'tool_use', 'id': i, 'input': {'command': cmd}}]}}
    rows = [
        result('growth 197% overall'),
        said('posting 83% and $15.32'),
        ran('n1', 'numbers.py t.jsonl 83%'), result("== 83%: in no output the session didn't write", 'n1'),
        result('## Evidence\n\n**posting 83%** and $15.32'),  # its own words, read back from the PR
        ran('c1', 'node -e "if (s.length>20000) big()"'),
        result('seed 1, 20000 runs each'),  # muse-spaces: real output after an unrelated write
        result('cache hit 97% of 120 calls'),
        result([{'type': 'text', 'text': 'tokens 61,280'}]),
        {'type': 'user', 'message': {'content': 'plain prompt with 1,280'}},
        {'type': 'user', 'origin': {'kind': 'peer'}, 'message': {'content': 'ran PACK=swain 16/16'}},
        {'type': 'user', 'isCompactSummary': True, 'origin': {'kind': 'human'}, 'message': {'content': 'summary says 55%'}},
        {'type': 'attachment', 'attachment': {'type': 'queued_command', 'prompt': 'reader: 42 findings'}},
        result('run 7 old'), result('run 7 mid'), result('run 7 a'), result('run 7 new'),
        ran('e1', 'echo 61,280 97%'), result('61,280 97%', 'e1'),  # what it just typed, printed back
    ]
    fd, path = tempfile.mkstemp(suffix='.jsonl')
    with os.fdopen(fd, 'w') as f:
        f.write('not json\n[]\n' + '\n'.join(json.dumps(r) for r in rows) + '\n')
    try:
        hits, echoes = find(path, ['97%', '61,280', '1,280', '$15.32', '83%', '42', '7', '16/16', '55%', '20000'])
        assert hits['16/16'] == ['ran PACK=swain 16/16'], hits['16/16']   # another session's message
        assert hits['55%'] == [], hits['55%']                              # a compaction summary is no source
        assert hits['97%'] == ['cache hit 97% of 120 calls'], hits['97%']  # not 197%, not the echo after
        assert hits['61,280'] == ['tokens 61,280'], hits['61,280']         # a block result
        assert hits['1,280'] == [], hits['1,280']                          # inside 61,280; a prompt isn't output
        assert hits['$15.32'] == [] and echoes['$15.32'], hits['$15.32']   # only ever its own
        assert hits['83%'] == [] and echoes['83%'] == 1, (hits['83%'], echoes['83%'])  # the PR read back; this script's report is skipped
        assert hits['20000'] == ['seed 1, 20000 runs each'], hits['20000']  # an unrelated earlier write blocks nothing
        assert hits['42'] == ['reader: 42 findings'], hits['42']           # a background report
        assert hits['7'] == ['run 7 mid', 'run 7 a', 'run 7 new'], hits['7']  # the newest three
        with contextlib.redirect_stdout(io.StringIO()) as out:
            rc = main(['numbers.py', path, '97%', '83%'])
        assert rc == 1 and "83%: in no output the session didn't write, only its own words read back" in out.getvalue(), out.getvalue()
        with contextlib.redirect_stdout(io.StringIO()):
            assert main(['numbers.py', path, '97%', '42']) == 0
    finally:
        os.unlink(path)
    print('numbers selftest: ok')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
