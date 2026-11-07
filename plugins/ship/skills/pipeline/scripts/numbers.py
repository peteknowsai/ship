#!/usr/bin/env python3
"""numbers.py <transcript.jsonl> <number>...: where each number came from.

After a compaction, every number a PR body or card states is rechecked against recorded
output. This prints the text around each number in the session transcript's tool results,
never in the session's own messages, which are what's being checked. Exit 1 when a number
appears in no tool result. The recap prints the transcript's path.
numbers.py --selftest
"""
import json, sys


def tool_texts(path):
    for line in open(path, encoding='utf-8', errors='replace'):
        try:
            content = (json.loads(line).get('message') or {}).get('content')
        except (ValueError, AttributeError):
            continue
        if not isinstance(content, list):
            continue
        for c in content:
            if not isinstance(c, dict) or c.get('type') != 'tool_result':
                continue
            body = c.get('content')
            yield body if isinstance(body, str) else ' '.join(
                x.get('text', '') for x in body or [] if isinstance(x, dict))


def find(path, nums):
    hits = {n: [] for n in nums}
    for text in tool_texts(path):
        for n in nums:
            i = text.find(n)
            while i >= 0 and len(hits[n]) < 3:
                ctx = text[max(0, i - 160):i + len(n) + 100].replace('\n', ' ')
                if ctx not in hits[n]:
                    hits[n].append(ctx)
                i = text.find(n, i + 1)
    return hits


def main(argv):
    if argv[1:] == ['--selftest']:
        return selftest()
    if len(argv) < 3:
        print(__doc__.strip().splitlines()[0], file=sys.stderr)
        return 2
    missing = 0
    for n, ctxs in find(argv[1], argv[2:]).items():
        if not ctxs:
            missing += 1
            print(f'== {n}: in no tool result')
        for ctx in ctxs:
            print(f'== {n}: ...{ctx}...')
    return 1 if missing else 0


def selftest():
    import os, tempfile, io, contextlib
    rows = [
        {'type': 'assistant', 'message': {'content': [{'type': 'text', 'text': 'hit rate 97% and $15.32'}]}},
        {'type': 'user', 'message': {'content': [{'type': 'tool_result', 'content': 'cache hit 97% of 120 calls'}]}},
        {'type': 'user', 'message': {'content': [{'type': 'tool_result', 'content': [{'type': 'text', 'text': 'tokens 61,280'}]}]}},
        {'type': 'user', 'message': {'content': 'plain prompt with 61,280'}},
    ]
    fd, path = tempfile.mkstemp(suffix='.jsonl')
    with os.fdopen(fd, 'w') as f:
        f.write('not json\n' + '\n'.join(json.dumps(r) for r in rows) + '\n')
    try:
        hits = find(path, ['97%', '61,280', '$15.32'])
        assert hits['97%'] == ['cache hit 97% of 120 calls'], hits['97%']  # a string result
        assert hits['61,280'] == ['tokens 61,280'], hits['61,280']         # a block result, not the prompt
        assert hits['$15.32'] == [], hits['$15.32']                        # only in its own message
        with contextlib.redirect_stdout(io.StringIO()) as out:
            rc = main(['numbers.py', path, '97%', '$15.32'])
        assert rc == 1 and '$15.32: in no tool result' in out.getvalue(), (rc, out.getvalue())
        with contextlib.redirect_stdout(io.StringIO()):
            assert main(['numbers.py', path, '97%']) == 0
    finally:
        os.unlink(path)
    print('numbers selftest: ok')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
