#!/usr/bin/env python3
"""icon-check: does each page carry a browser icon and a Home Screen icon?

  usage: icon-check.py <url> [<url>...]      exit 0 clean, 2 findings, 1 a page it couldn't load
         icon-check.py --selftest

Per page:
  icon   a <link rel="icon"> (or "shortcut icon") that loads, else /favicon.ico answering 200
  touch  a <link rel="apple-touch-icon">, else /apple-touch-icon.png (what iOS asks for
         unprompted), that loads as a PNG at least 180px on each side

Apps named on the tailnet (homebody/, metube/) show up on Pete's Home Screen and in the
launcher by these icons, and a new app often ships with neither (Pete, 2026-10-14).
"""
import html.parser
import struct
import sys
import urllib.error
import urllib.parse
import urllib.request

UA = {'User-Agent': 'ship-icon-check/1'}
MIN = 180


def fetch(url):
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=10) as r:
            return r.status, r.read(4_000_000)
    except urllib.error.HTTPError as e:
        return e.code, b''
    except (OSError, ValueError):
        return None, b''


class Links(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.found = {}

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'link' and a.get('href'):
            for rel in (a.get('rel') or '').lower().split():
                self.found.setdefault(rel, a['href'])


def png_size(data):
    if data[:8] != b'\x89PNG\r\n\x1a\n' or data[12:16] != b'IHDR':
        return None
    return struct.unpack('>II', data[16:24])


def check(url):
    """Findings for one page as plain sentences; None when the page itself won't load."""
    status, body = fetch(url)
    if status != 200:
        return None
    links = Links()
    links.feed(body.decode('utf-8', 'replace'))
    at = lambda href: urllib.parse.urljoin(url, href)
    out = []

    icon = links.found.get('icon')
    if icon:
        if fetch(at(icon))[0] != 200:
            out.append(f'icon: <link rel="icon"> points at {at(icon)}, which does not load')
    elif fetch(at('/favicon.ico'))[0] != 200:
        out.append('icon: no <link rel="icon"> and /favicon.ico is not there')

    touch = links.found.get('apple-touch-icon')
    where = at(touch or '/apple-touch-icon.png')
    status, data = fetch(where)
    size = png_size(data) if status == 200 else None
    if status != 200:
        out.append(f'touch: no <link rel="apple-touch-icon"> and {where} is not there' if not touch
                   else f'touch: <link rel="apple-touch-icon"> points at {where}, which does not load')
    elif not size:
        out.append(f'touch: {where} is not a PNG')
    elif min(size) < MIN:
        out.append(f'touch: {where} is {size[0]}x{size[1]}, under {MIN}px')
    return out


def main(urls):
    worst = 0
    for url in urls:
        found = check(url)
        if found is None:
            print(f'{url}: page did not load', file=sys.stderr)
            worst = max(worst, 1)
            continue
        for f in found:
            print(f'{url}  {f}', file=sys.stderr)
        if found:
            worst = 2
    return worst


def selftest():
    import http.server
    import threading
    import zlib

    def png(w, h):
        chunk = lambda t, d: struct.pack('>I', len(d)) + t + d + struct.pack('>I', zlib.crc32(t + d))
        return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', w, h, 8, 2, 0, 0, 0))
                + chunk(b'IEND', b''))

    site = {
        '/good': b'<link rel="icon" href="/i.svg"><link rel="apple-touch-icon" href="/t.png">',
        '/i.svg': b'<svg/>', '/t.png': png(180, 180),
        '/bare': b'<p>no head at all</p>',
        '/small': b'<link rel="shortcut icon" href="/i.svg"><link rel="apple-touch-icon" href="/s.png">',
        '/s.png': png(64, 64),
        '/broken': b'<link rel="icon" href="/gone.svg"><link rel="apple-touch-icon" href="/i.svg">',
    }

    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            path = self.path.split('?')[0]
            body = site.get(path, site.get('*' + path))
            self.send_response(200 if body is not None else 404)
            self.end_headers()
            self.wfile.write(body or b'')

        def log_message(self, *a):
            pass

    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), H)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f'http://127.0.0.1:{server.server_port}'
    fails = 0

    def expect(name, ok):
        nonlocal fails
        print(('ok   ' if ok else 'FAIL ') + name)
        fails += not ok

    expect('a page with both icons is clean', check(base + '/good') == [])
    bare = check(base + '/bare')
    expect('a page with neither gets both findings',
           len(bare) == 2 and bare[0].startswith('icon:') and bare[1].startswith('touch:'))
    site['*/favicon.ico'] = b'ico'
    site['*/apple-touch-icon.png'] = png(192, 192)
    expect('the conventional /favicon.ico and /apple-touch-icon.png count', check(base + '/bare') == [])
    small = check(base + '/small')
    expect('a touch icon under 180px is flagged, "shortcut icon" counts',
           small == [f'touch: {base}/s.png is 64x64, under 180px'])
    broken = check(base + '/broken')
    expect('a declared icon that 404s and a touch icon that is not a PNG are flagged',
           len(broken) == 2 and 'does not load' in broken[0] and 'not a PNG' in broken[1])
    expect('a page that will not load is None, exit 1', check(base + '/nope') is None and main([base + '/nope']) == 1)
    expect('findings exit 2', main([base + '/small', base + '/nope']) == 2)
    server.shutdown()
    print('icon-check selftest:', 'FAILED' if fails else 'passed')
    return 1 if fails else 0


if __name__ == '__main__':
    args = sys.argv[1:]
    if args == ['--selftest']:
        sys.exit(selftest())
    if not args or args[0].startswith('-'):
        print(__doc__.split('\n\n')[1], file=sys.stderr)
        sys.exit(1)
    sys.exit(main(args))
