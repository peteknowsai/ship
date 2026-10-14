#!/usr/bin/env python3
"""Share a ship doc to a public, unlisted, versioned link on share.peteknowsai.xyz.

  share.py publish <key> <file>      bundle the page, upload it, copy the link; prints JSON
  share.py republish <key> <file>    publish again only if <key> was shared before, never
                                     touching the clipboard; never fails, since show.sh runs
                                     it in the background after every redraw
  share.py status|stop|copy <key>    is it shared, take it down, copy the link again
  share.py host                      Chrome's native messaging host com.pete.ship.share:
                                     one framed request on stdin, one framed answer on stdout
  share.py install <extension-id>... [--dir <NativeMessagingHosts dir>]
  share.py --selftest

<key> is the Ship tabs tag key: repo/slug/kind for a storyboard, plan or review, else the
doc's absolute path. Links follow the key, not the path, so a doc shared from main keeps
its link when a worktree redraws it.

The bundle is one self-contained file: local stylesheets, scripts, images and iframes
become <style>, inline <script>, data URIs and srcdoc. Only those src, href and url()
references change; inline scripts, comments and all other markup pass through byte for
byte. SHIP_SHARE_HOME (default ~/.config/ship-share) holds links.json, key to link. The
upload key comes from SHIP_SHARE_TOKEN, else the Keychain item ship-share, and is never
printed. SHIP_SHARE_URL points at another server, SHIP_SHARE_KEYCHAIN at another item.

Chrome spawns the host through share-host.sh with a bare PATH under /usr/bin/python3,
which is 3.9: binaries by absolute path, nothing newer than 3.9, and nothing on stdout
but the one framed answer.
"""
import base64
import contextlib
import fcntl
import html
import http.client
import http.server
import io
import json
import mimetypes
import os
import re
import secrets
import struct
import subprocess
import sys
import tempfile
import threading
import traceback
import urllib.error
import urllib.parse
import urllib.request

HOST = 'com.pete.ship.share'
SERVER = 'https://share.peteknowsai.xyz'
NO_ANSWER = "share.peteknowsai.xyz didn't answer. Check your connection, then try again."
REFUSED = 'The upload key was refused. Check the ship-share key in your Keychain.'
NO_KEY = 'No upload key in your Keychain (ship-share).'
TOO_BIG = 'This page is too big to share (over 20 MB).'
GONE = "That file isn't on disk anymore."
MAX = 20 * 1024 * 1024  # the Worker refuses bigger bodies with a 413
DEPTH = 3  # iframes inside iframes, at most
ALNUM = 'abcdefghijklmnopqrstuvwxyz0123456789'


class ShareError(Exception):
    """A failure Pete reads: the message is the one sentence the Share button shows."""


def clip(text):
    subprocess.run(['/usr/bin/pbcopy'], input=text.encode(), stdout=subprocess.DEVNULL, check=True)


# Bundler. One pass over the page; comments and inline scripts are matched whole so
# nothing inside them is rewritten. Groups: script 1-2, style 3-4, any other tag 5-6.
ATTRS = r'((?:"[^"]*"|\'[^\']*\'|[^\'">])*)'
PART = re.compile(r'<!--.*?-->'
                  r'|<script\b' + ATTRS + r'>(.*?)</script\s*>'
                  r'|<style\b' + ATTRS + r'>(.*?)</style\s*>'
                  r'|<([a-zA-Z][\w-]*)(?=[\s/>])' + ATTRS + '>', re.S | re.I)
ATTR = re.compile(r'([^\s"\'>/=]+)(?:\s*=\s*("[^"]*"|\'[^\']*\'|[^\s"\'>]+))?')
URL = re.compile(r'url\(\s*(?:"([^"]*)"|\'([^\']*)\'|([^)\'"\s]*))\s*\)', re.I)
MEDIA = {'img': ('src',), 'source': ('src',), 'video': ('src', 'poster'), 'audio': ('src',)}


def read(path):
    with open(path, 'rb') as f:
        return f.read().decode('utf-8', 'replace')


def local(url, here):
    """The file a relative URL points at, or None for remote, data, anchor or missing ones."""
    url = url.strip()
    if not url or url.startswith(('#', '//')) or re.match(r'[a-zA-Z][\w+.-]*:', url):
        return None
    path = os.path.realpath(os.path.join(here, urllib.parse.unquote(re.split('[?#]', url)[0])))
    # The bundle goes public: only files inside the doc's own repo, and no dotfiles or dot
    # folders but ship's screenshots, so a stray reference can't publish ~/.ssh or .env.
    rel = os.path.relpath(path, ROOT[0]).split(os.sep) if ROOT else ['..']
    if rel[0] == '..' or any(p.startswith('.') and p != '.ship-shots' for p in rel):
        return None
    return path if os.path.isfile(path) else None


ROOT = []  # the repo the page being bundled lives in; set by bundle()


def repo_of(path):
    d = os.path.dirname(path)
    while d != os.path.dirname(d):
        if os.path.exists(os.path.join(d, '.git')):
            return d
        d = os.path.dirname(d)
    return os.path.dirname(path)


def data_uri(path):
    with open(path, 'rb') as f:
        data = base64.b64encode(f.read()).decode()
    return f"data:{mimetypes.guess_type(path)[0] or 'application/octet-stream'};base64,{data}"


def inline_css(css, here):
    def one(m):
        path = local(next(g for g in m.groups() if g is not None), here)
        return f'url({data_uri(path)})' if path else m.group(0)
    return URL.sub(one, css)


def attrs_of(text):
    found = {}
    for m in ATTR.finditer(text):
        if m.group(2) is not None:
            found.setdefault(m.group(1).lower(), m)  # the first of a repeated attribute wins, as in a browser
    return found


def value(m):
    raw = m.group(2)
    return html.unescape(raw[1:-1] if raw[0] in '"\'' else raw)


def script(m, here):
    attrs = m.group(1)
    src = attrs_of(attrs).get('src')
    path = src and local(value(src), here)
    if not path:
        return m.group(0)
    if {a.group(1).lower() for a in ATTR.finditer(attrs)} & {'defer', 'async'}:
        # An inline script ignores defer and async, so it would run before the page it
        # waits for; a data: URL keeps it external and keeps its timing.
        return f'<script{attrs[:src.start(2)]}"{data_uri(path)}"{attrs[src.end(2):]}></script>'
    js = re.sub(r'</(script)', r'<\\/\1', read(path), flags=re.I)
    return f'<script{attrs[:src.start()].rstrip()}{attrs[src.end():]}>{js}</script>'


def tag(m, here, depth, seen):
    name, attrs = m.group(5).lower(), m.group(6)
    found = attrs_of(attrs)
    rel = value(found['rel']).lower().split() if 'rel' in found else []
    targets = MEDIA.get(name, ()) + (('href',) if name == 'link' else ())
    paths = {a: local(value(found[a]), here) for a in targets if a in found}
    if name == 'link' and paths.get('href') and 'stylesheet' in rel:
        media = f' media="{html.escape(value(found["media"]))}"' if 'media' in found else ''
        return f"<style{media}>{inline_css(read(paths['href']), os.path.dirname(paths['href']))}</style>"
    edits = [(found[a].start(2), found[a].end(2), f'"{data_uri(p)}"') for a, p in paths.items()
             if p and (name != 'link' or 'icon' in rel)]
    if 'style' in found:
        css = value(found['style'])
        if inline_css(css, here) != css:
            edits.append((found['style'].start(2), found['style'].end(2), f'"{html.escape(inline_css(css, here))}"'))
    child = name == 'iframe' and 'src' in found and local(value(found['src']), here)
    if child and child.lower().endswith(('.html', '.htm')) and depth < DEPTH and child not in seen:
        edits.append((found['src'].start(1), found['src'].end(2),
                      f'srcdoc="{html.escape(bundle(child, depth + 1, seen))}"'))
    for start, end, text in sorted(edits, reverse=True):
        attrs = attrs[:start] + text + attrs[end:]
    return f'<{m.group(5)}{attrs}>'


def bundle(path, depth=0, seen=()):
    """The page at `path` as one self-contained HTML string."""
    path = os.path.realpath(path)
    here, seen = os.path.dirname(path), seen + (path,)
    if depth == 0:
        ROOT[:] = [repo_of(path)]

    def part(m):
        if m.group(5):
            return tag(m, here, depth, seen)
        if m.group(3) is not None:
            return m.group(0)[:m.start(4) - m.start()] + inline_css(m.group(4), here) + m.group(0)[m.end(4) - m.start():]
        if m.group(1) is not None:
            return script(m, here)
        return m.group(0)
    out = PART.sub(part, read(path))
    if depth == 0 and len(out.encode()) > MAX:
        raise ShareError(TOO_BIG)
    return out


def name_for(key, file):
    """The link's cosmetic name: slug-kind for a card key, else the file's undated stem."""
    parts = key.split('/')
    if len(parts) == 3 and not key.startswith('/'):
        raw = f'{parts[1]}-{parts[2]}'
    else:
        raw = re.sub(r'^\d{4}-\d{2}-\d{2}-', '', os.path.splitext(os.path.basename(file))[0])
    return re.sub('[^a-z0-9]+', '-', raw.lower()).strip('-')[:80].strip('-') or 'doc'


# Links, the key and the server.
def home():
    return os.environ.get('SHIP_SHARE_HOME') or os.path.expanduser('~/.config/ship-share')


def links():
    try:
        with open(os.path.join(home(), 'links.json')) as f:
            return json.load(f)
    except (FileNotFoundError, ValueError):
        return {}


@contextlib.contextmanager
def locked():
    """One read-modify-write of links.json at a time, across the host, the CLI and show.sh."""
    os.makedirs(home(), exist_ok=True)
    with open(os.path.join(home(), 'links.lock'), 'w') as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        yield


def save(data):
    os.makedirs(home(), exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=home(), suffix='.tmp')
    with os.fdopen(fd, 'w') as f:
        json.dump(data, f, indent=1)
    os.replace(tmp, os.path.join(home(), 'links.json'))


def token():
    if os.environ.get('SHIP_SHARE_TOKEN'):
        return os.environ['SHIP_SHARE_TOKEN']
    try:
        found = subprocess.run(['/usr/bin/security', 'find-generic-password', '-s',
                                os.environ.get('SHIP_SHARE_KEYCHAIN') or 'ship-share', '-w'],
                               capture_output=True, text=True)
    except OSError:
        found = None
    if found and found.returncode == 0 and found.stdout.strip():
        return found.stdout.strip()
    raise ShareError(NO_KEY)


def api(method, path, body=None):
    request = urllib.request.Request((os.environ.get('SHIP_SHARE_URL') or SERVER).rstrip('/') + path, body, method=method,
                                     # Cloudflare's bot check 403s urllib's own User-Agent.
                                     headers={'authorization': 'Bearer ' + token(), 'user-agent': 'ship-share/1',
                                              'content-type': 'text/html; charset=utf-8'})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        raise ShareError({401: REFUSED, 413: TOO_BIG}.get(
            error.code, f'share.peteknowsai.xyz answered {error.code}. Try again in a minute.'))
    except (OSError, ValueError, http.client.HTTPException):  # URLError, refused, timeout, garbage
        raise ShareError(NO_ANSWER)


def shown(entry):
    fields = ('url', 'version', 'versions', 'at')
    return {'ok': True, 'shared': bool(entry), **{k: (entry or {}).get(k) for k in fields}}


def publish(key, file, copy=True):
    if not os.path.isfile(file):
        raise ShareError(GONE)
    page = bundle(file).encode()
    doc = (links().get(key) or {}).get('id') or ''.join(secrets.choice(ALNUM) for _ in range(6))
    name = name_for(key, file)
    was = key in links()
    answer = api('PUT', f'/api/{doc}?name={name}', page)
    with locked():
        data = links()  # reread: the upload took a while
        if was and key not in data:
            # Pete pressed Stop sharing while this redraw uploaded: the upload must not
            # bring the page back.
            api('DELETE', f'/api/{doc}')
            return shown(None)
        data[key] = {'id': doc, 'name': name, **{k: answer.get(k) for k in ('url', 'version', 'versions', 'at')}}
        save(data)
    if copy:
        clip(data[key]['url'])
    return shown(data[key])


def republish(key, file):
    """Follow a redraw of a doc Pete shared; None when he never shared it. Never raises."""
    try:
        return publish(key, file, copy=False) if key in links() else None
    except ShareError as error:
        return {'ok': False, 'error': str(error)}
    except Exception as error:
        return {'ok': False, 'error': f'{type(error).__name__}: {error}'}


def handle(req):
    """One native messaging request (see the Seams in the plan) to its answer."""
    cmd, key = req.get('cmd'), req.get('key')
    try:
        if not isinstance(key, str) or not key:
            raise ShareError('The share request named no page.')
        if cmd == 'publish':
            if not isinstance(req.get('file'), str):
                raise ShareError(GONE)
            return publish(key, req['file'])
        entry = links().get(key)
        if cmd == 'status':
            return shown(entry)
        if cmd == 'copy':
            if not entry:
                raise ShareError("This page isn't shared yet.")
            clip(entry['url'])
            return shown(entry)
        if cmd == 'stop':
            if entry:
                api('DELETE', f"/api/{entry['id']}")
                with locked():
                    data = links()
                    data.pop(key, None)
                    save(data)
            return shown(None)
        raise ShareError(f'The share helper has no "{cmd}" command.')
    except ShareError as error:
        return {'ok': False, 'error': str(error)}


# Chrome native messaging: a 4-byte native-endian length, then that many bytes of JSON.
def read_msg(stream):
    head = stream.read(4)
    if len(head) != 4:
        raise ValueError('no message on stdin')
    return json.loads(stream.read(struct.unpack('=I', head)[0]).decode('utf-8'))


def write_msg(stream, obj):
    data = json.dumps(obj).encode('utf-8')
    stream.write(struct.pack('=I', len(data)) + data)
    stream.flush()


def host():
    out = sys.stdout.buffer
    sys.stdout = sys.stderr  # a stray print must not corrupt the one frame Chrome reads
    try:
        answer = handle(read_msg(sys.stdin.buffer))
    except Exception:
        traceback.print_exc()
        answer = {'ok': False, 'error': 'Something went wrong in the share helper.'}
    write_msg(out, answer)
    return 0


def install(ids, dir=None):
    """Write Chrome's host manifest for these extension ids; returns its path."""
    for i in ids:
        if not re.fullmatch('[a-p]{32}', i):
            raise SystemExit(f'share: {i} is not a Chrome extension id')
    dir = dir or os.path.expanduser('~/Library/Application Support/Google/Chrome/NativeMessagingHosts')
    os.makedirs(dir, exist_ok=True)
    path = os.path.join(dir, f'{HOST}.json')
    with open(path, 'w') as f:
        json.dump({'name': HOST, 'description': 'Ship tabs Share button',
                   'path': os.path.join(os.path.dirname(os.path.realpath(__file__)), 'share-host.sh'),
                   'type': 'stdio', 'allowed_origins': [f'chrome-extension://{i}/' for i in ids]}, f, indent=2)
    return path


class Fake(http.server.BaseHTTPRequestHandler):
    """The share Worker's API in miniature: versions per id, token t0k."""
    store = {}
    hits = []

    def log_message(self, *args):
        pass

    def reply(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header('content-type', 'application/json')
        self.send_header('content-length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def handle_api(self):
        self.hits.append((self.command, self.path))
        body = self.rfile.read(int(self.headers.get('content-length') or 0))
        if (self.headers.get('user-agent') or '').startswith('Python-urllib'):
            self.reply(403, {'error': 'Cloudflare refuses the default Python agent'})
            return None, None, None
        if self.headers.get('authorization') != 'Bearer t0k':
            self.reply(401, {'error': 'unauthorized'})
            return None, None, None
        url = urllib.parse.urlsplit(self.path)
        return url.path.rsplit('/', 1)[-1], (urllib.parse.parse_qs(url.query).get('name') or [''])[0], body

    def do_PUT(self):
        doc, name, body = self.handle_api()
        if doc is None:
            return
        versions = self.store.setdefault(doc, [])
        changed = not versions or versions[-1] != body
        if changed:
            versions.append(body)
        self.reply(200, {'url': f'https://share.peteknowsai.xyz/{doc}/{name}', 'version': len(versions),
                         'versions': len(versions), 'changed': changed, 'at': '2026-10-14T21:10:00Z'})

    def do_DELETE(self):
        doc, _, _ = self.handle_api()
        if doc is not None:
            gone = self.store.pop(doc, [])
            self.reply(200, {'deleted': len(gone) + 1 if gone else 0})


def selftest():
    fails = 0

    def check(name, ok):
        nonlocal fails
        print(f"  {'ok  ' if ok else 'FAIL'} {name}")
        fails += 0 if ok else 1

    def write(path, text):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'wb') as f:
            f.write(text if isinstance(text, bytes) else text.encode())

    here = os.path.dirname(os.path.realpath(__file__))
    env_keys = ('SHIP_SHARE_HOME', 'SHIP_SHARE_URL', 'SHIP_SHARE_TOKEN', 'SHIP_SHARE_KEYCHAIN')
    saved_env = {k: os.environ.pop(k, None) for k in env_keys}
    clipped = []
    real_clip, real_max = globals()['clip'], MAX
    globals()['clip'] = clipped.append  # never Pete's clipboard
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), Fake)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    fake_url = f'http://127.0.0.1:{server.server_port}'
    try:
        with tempfile.TemporaryDirectory() as tmp:
            tmp = os.path.realpath(tmp)
            doc = os.path.join(tmp, 'doc')
            png = b'\x89PNG\r\n\x1a\nfake'
            write(f'{doc}/a.css', 'body{background:url(i.png)}')
            write(f'{doc}/s.js', 'var x = "</script>";')
            write(f'{doc}/i.png', png)
            write(f'{doc}/f.html', '<p>frame</p><img src="i.png">')
            template = ('<template data-frame="idle"><style>.a{color:red}</style>'
                        '<div class="a" title="a>b">hi</div>'
                        '<script>if (a < b) document.body.innerHTML = \'<img src="i.png">\';</script></template>')
            inline = ('<script type="module">const f = \'<iframe src="f.html"></iframe>'
                      '<link rel="stylesheet" href="a.css">\';</script>')
            comment = '<!-- <img src="i.png"> -->'
            page = (f'<!doctype html><html><head>\n<link rel="stylesheet" href="a.css">\n'
                    f'<script src="s.js"></script>\n{comment}\n</head><body>\n'
                    '<img src="i.png"><iframe src="f.html"></iframe>\n'
                    '<img src="https://x.test/r.png"><img src="missing.png"><img src="data:image/png;base64,AA==">\n'
                    f'{template}\n{inline}\n<div style="background:url(\'i.png\')">x</div>\n</body></html>\n')
            write(f'{doc}/page.html', page)
            out = bundle(f'{doc}/page.html')
            rest = out.replace(template, '').replace(inline, '').replace(comment, '')
            b64 = 'data:image/png;base64,' + base64.b64encode(png).decode()
            check('a local stylesheet becomes a <style> with its images inlined',
                  'href="a.css"' not in rest and f'<style>body{{background:url({b64})}}</style>' in out)
            check('a local script is inlined with </script> escaped',
                  'src="s.js"' not in rest and '<script>var x = "<\\/script>";</script>' in out)
            check('a local image becomes a data URI', f'<img src="{b64}">' in out)
            check('a local iframe becomes srcdoc holding its own inlined image',
                  'src="f.html"' not in rest and '<iframe srcdoc="&lt;p&gt;frame&lt;/p&gt;&lt;img src=&quot;'
                  + b64 + '&quot;&gt;"></iframe>' in out)
            check('remote, data and missing URLs are left alone',
                  all(t in out for t in ('<img src="https://x.test/r.png">', '<img src="missing.png">',
                                         '<img src="data:image/png;base64,AA==">')))
            check('a style attribute gets its url() inlined', f'<div style="background:url({b64})">' in out)
            check('Review Focus 1: a <template> and an inline script pass through byte for byte',
                  template in out and inline in out and comment in out)
            write(f'{tmp}/secret.png', png)
            write(f'{doc}/.env/i.png', png)
            write(f'{doc}/.ship-shots/i.png', png)
            write(f'{doc}/p2.html', '<link rel="stylesheet" media="print" href="a.css">'
                                    '<script defer src="s.js"></script>'
                                    f'<img src="../secret.png"><img src="{tmp}/secret.png">'
                                    '<img src=".env/i.png"><img src=".ship-shots/i.png">')
            out2 = bundle(f'{doc}/p2.html')
            check('a deferred script stays external, as a data URL, so it keeps its timing',
                  '<script defer src="data:' in out2 and 'var x' not in out2)
            check("a stylesheet keeps its media", '<style media="print">' in out2)
            check('nothing outside the repo or under a dot folder is published, but ship screenshots are',
                  f'<img src="../secret.png"><img src="{tmp}/secret.png"><img src=".env/i.png"><img src="{b64}">' in out2)
            board = os.path.join(here, '..', '..', '..', '..', '..', 'specs', 'designs', '2026-10-14-doc-share.html')
            if os.path.isfile(board):  # only in a checkout; the installed plugin has no specs/
                with open(board, 'rb') as f:
                    check('the real storyboard bundles to itself', bundle(board).encode() == f.read())
            write(f'{doc}/loop.html', '<p>loop</p><iframe src="loop.html"></iframe>')
            write(f'{doc}/x.html', '<iframe src="y.html"></iframe>')
            write(f'{doc}/y.html', '<p>why</p><iframe src="x.html"></iframe>')
            looped = bundle(f'{doc}/x.html')
            check('iframes that frame each other stop at the cycle',
                  '<iframe src="loop.html">' in bundle(f'{doc}/loop.html')
                  and 'why' in looped and 'src=&quot;x.html&quot;' in looped)
            for n in range(5):
                write(f'{doc}/c{n}.html', f'<p>page-{n}</p><iframe src="c{n + 1}.html"></iframe>')
            chain = bundle(f'{doc}/c0.html')
            check('iframes nest at most three deep', 'page-3' in chain and 'page-4' not in chain)
            globals()['MAX'] = 10
            try:
                bundle(f'{doc}/page.html')
                check('a bundle over the cap is refused', False)
            except Exception as error:
                check('a bundle over the cap is refused', str(error) == TOO_BIG)
            globals()['MAX'] = real_max

            names = [name_for('eca/smarter-search/storyboard', '/x/specs/designs/2026-10-01-smarter-search.html'),
                     name_for('/x/specs/2026-10-01-Pricing Notes.html', '/x/specs/2026-10-01-Pricing Notes.html'),
                     name_for('/x/***.html', '/x/***.html'), name_for('/x/' + 'Ab' * 60 + '.html', '/x/a.html')]
            check('names: card keys, dated stems, empty and long ones',
                  names[:3] == ['smarter-search-storyboard', 'pricing-notes', 'doc']
                  and all(re.fullmatch('[a-z0-9-]{1,80}', n) for n in names))

            buf = io.BytesIO()
            write_msg(buf, {'a': 'é'})
            raw = buf.getvalue()
            buf.seek(0)
            check('a native message round-trips with a 4-byte length',
                  struct.unpack('=I', raw[:4])[0] == len(raw) - 4 and read_msg(buf) == {'a': 'é'})

            home = os.path.join(tmp, 'home')
            os.environ.update(SHIP_SHARE_HOME=home, SHIP_SHARE_URL=fake_url, SHIP_SHARE_TOKEN='t0k')
            key = 'ship/doc-share/storyboard'
            check('status before sharing says not shared',
                  handle({'cmd': 'status', 'key': key}) == {'ok': True, 'shared': False, 'url': None,
                                                             'version': None, 'versions': None, 'at': None})
            first = handle({'cmd': 'publish', 'key': key, 'file': f'{doc}/page.html'})
            saved = links().get(key, {})
            check('publish uploads version 1 and copies the link',
                  first.get('ok') and first.get('shared') and first.get('version') == 1
                  and first.get('url') == f"https://share.peteknowsai.xyz/{saved.get('id')}/doc-share-storyboard"
                  and clipped == [first['url']] and bool(re.fullmatch('[a-z0-9]{6}', saved.get('id', ''))))
            check('the upload is the bundle', Fake.store.get(saved.get('id'), [b''])[-1] == out.encode())
            redraw = os.path.join(tmp, 'worktree', 'specs', 'designs', 'other-name.html')
            write(redraw, page.replace('<body>', '<body><p>round 2</p>'))
            second = republish(key, redraw) or {}
            check('Review Focus 2: a redraw from another path republishes as version 2 under the same id',
                  second.get('version') == 2 and links()[key]['id'] == saved.get('id') and len(clipped) == 1)
            hits = len(Fake.hits)
            check('republish of a never-shared key does nothing',
                  republish('ship/other/plan', redraw) is None and len(Fake.hits) == hits and len(links()) == 1)
            copied = handle({'cmd': 'copy', 'key': key})
            check('copy puts the link on the clipboard again', copied.get('version') == 2 and len(clipped) == 2)

            for label, cmd in (('the host script', [os.path.join(here, 'share-host.sh')]),
                               ('this python', [sys.executable, os.path.join(here, 'share.py'), 'host'])):
                buf = io.BytesIO()
                write_msg(buf, {'cmd': 'status', 'key': key})
                ran = subprocess.run(cmd, input=buf.getvalue(), capture_output=True,
                                     env={'HOME': tmp, 'SHIP_SHARE_HOME': home, 'SHIP_SHARE_URL': fake_url,
                                          'SHIP_SHARE_TOKEN': 't0k'})
                size = struct.unpack('=I', ran.stdout[:4])[0] if len(ran.stdout) >= 4 else -1
                answer = json.loads(ran.stdout[4:]) if size == len(ran.stdout) - 4 else {}
                check(f'the host under a bare env via {label} writes exactly one framed answer',
                      answer.get('ok') is True and answer.get('version') == 2)
            stopped = handle({'cmd': 'stop', 'key': key})
            check('stop takes it down and forgets it',
                  stopped.get('shared') is False and key not in links() and saved.get('id') not in Fake.store
                  and len(clipped) == 2)
            race, real_api = 'ship/race/plan', api
            publish(race, f'{doc}/page.html', copy=False)
            race_id = links()[race]['id']

            def stop_mid_upload(method, path, body=None):
                answer = real_api(method, path, body)
                if method == 'PUT':  # Pete presses Stop sharing while the redraw uploads
                    handle({'cmd': 'stop', 'key': race})
                return answer
            globals()['api'] = stop_mid_upload
            try:
                raced = republish(race, redraw) or {}
            finally:
                globals()['api'] = real_api
            check('Stop pressed during a redraw upload stays stopped',
                  raced.get('shared') is False and race not in links() and race_id not in Fake.store)

            check('a missing file says so',
                  handle({'cmd': 'publish', 'key': key, 'file': f'{doc}/gone.html'}) == {'ok': False, 'error': GONE})
            os.environ['SHIP_SHARE_URL'] = 'http://127.0.0.1:9'
            check('a dead server says it did not answer',
                  handle({'cmd': 'publish', 'key': key, 'file': f'{doc}/page.html'}) == {'ok': False, 'error': NO_ANSWER})
            os.environ.update(SHIP_SHARE_URL=fake_url, SHIP_SHARE_TOKEN='wrong')
            check('a refused key says so',
                  handle({'cmd': 'publish', 'key': key, 'file': f'{doc}/page.html'}) == {'ok': False, 'error': REFUSED})
            del os.environ['SHIP_SHARE_TOKEN']
            os.environ['SHIP_SHARE_KEYCHAIN'] = 'ship-share-selftest-missing'
            check('no key anywhere says so',
                  handle({'cmd': 'publish', 'key': key, 'file': f'{doc}/page.html'}) == {'ok': False, 'error': NO_KEY})
            check('nothing failed touches the clipboard or links.json', len(clipped) == 2 and links() == {})

            ids = ['abcdefghijklmnopabcdefghijklmnop', 'ponmlkjihgfedcbaponmlkjihgfedcba']
            with open(install(ids, dir=os.path.join(tmp, 'hosts'))) as f:
                manifest = json.load(f)
            check('install writes a host manifest Chrome can run',
                  manifest['name'] == HOST and manifest['type'] == 'stdio'
                  and os.access(manifest['path'], os.X_OK)
                  and manifest['allowed_origins'] == [f'chrome-extension://{i}/' for i in ids])
    finally:
        server.shutdown()
        globals()['clip'], globals()['MAX'] = real_clip, real_max
        for k, v in saved_env.items():
            os.environ.pop(k, None)
            if v is not None:
                os.environ[k] = v
    print('selftest ok' if not fails else f'share self-test: {fails} failed')
    return fails == 0


if __name__ == '__main__':
    args = sys.argv[1:]
    cmd = args[0] if args else ''
    if args == ['--selftest']:
        sys.exit(0 if selftest() else 1)
    elif args == ['host']:
        sys.exit(host())
    elif cmd == 'install' and len(args) >= 2:
        folder = None
        if '--dir' in args:
            at = args.index('--dir')
            if at + 1 >= len(args):
                sys.exit(__doc__)
            folder = args.pop(at + 1)
            args.pop(at)
        print(install(args[1:], folder) if len(args) > 1 else sys.exit(__doc__))
    elif cmd == 'republish' and len(args) == 3:
        print(json.dumps(republish(args[1], os.path.abspath(args[2]))))
    elif (cmd == 'publish' and len(args) == 3) or (cmd in ('status', 'stop', 'copy') and len(args) == 2):
        answer = handle({'cmd': cmd, 'key': args[1], 'file': os.path.abspath(args[2]) if len(args) == 3 else None})
        print(json.dumps(answer))
        sys.exit(0 if answer['ok'] else 1)
    else:
        sys.exit(__doc__)
