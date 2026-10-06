#!/usr/bin/env python3
"""Bundle a storyboard and every local file it loads, ready to publish as a Claude artifact.

  storyboard-bundle.py <storyboard.html> <out-dir>   writes <out-dir>/index.html and <out-dir>/a/,
                                                      prints {"page": ..., "files": {...}} as JSON
  storyboard-bundle.py --selftest

An artifact serves its page plus the files published beside it, at paths with no `../`,
while a repo's storyboard reaches its stylesheets wherever they live (cells-app:
`../../web/public/grok-shipped.css`). So every href/src that names a real local file, and
every url() inside a copied stylesheet, is copied into a/ under a unique name and
rewritten to it. A path a script names or builds (`'assets/mark.svg'`,
`assets/tiles/${name}.webp`) can't be relinked, so the file it names, or every file in
the folder its fixed part ends in, is published at that same path beside the page; that
only reaches files under the storyboard's own folder. Anything else (a CDN, a data: URI) is
left alone. The page loses its doctype, html, head and body tags, because the publish wraps
it in its own. The repo's storyboard is never touched: it stays the design of record.
Pass the JSON's `page` as Artifact's file_path and its `files` as `files`.
"""
import json
import os
import re
import shutil
import sys
import tempfile

ATTR = re.compile(r'''(\b(?:href|src)=)(["'])([^"'#?]+)([#?][^"']*)?\2''')
CSS_URL = re.compile(r'''url\(\s*(["']?)([^"')#?]+)([#?][^"')]*)?\1\s*\)''')
LITERAL = re.compile(r'''["'`]((?:\./)?[\w-][\w.-]*(?:/[\w.${}-]+)+)''')
SKELETON = re.compile(r'<!doctype[^>]*>|</?html[^>]*>|</?head>|</?body[^>]*>', re.I)


def bundle(page, out):
    page = os.path.abspath(page)
    os.makedirs(os.path.join(out, 'a'), exist_ok=True)
    names, files = {}, {}

    def local(ref, base):
        if re.match(r'^[a-z][a-z0-9+.-]*:|^//', ref, re.I) or '{{' in ref:
            return None
        path = os.path.normpath(os.path.join(base, ref))
        return path if os.path.isfile(path) else None

    def place(path):
        if path in names:
            return names[path]
        stem, n = os.path.basename(path), 1
        name = stem
        while name in names.values():
            n += 1
            root, ext = os.path.splitext(stem)
            name = f'{root}-{n}{ext}'
        names[path] = name
        dest = os.path.join(out, 'a', name)
        if path.endswith('.css'):
            css = open(path, encoding='utf-8').read()
            base = os.path.dirname(path)

            def css_ref(m):
                hit = local(m.group(2), base)
                return f'url({m.group(1)}{place(hit)}{m.group(3) or ""}{m.group(1)})' if hit else m.group(0)
            open(dest, 'w', encoding='utf-8').write(CSS_URL.sub(css_ref, css))
        else:
            shutil.copyfile(path, dest)
        files[f'a/{name}'] = dest
        return name

    html = open(page, encoding='utf-8').read()
    base = os.path.dirname(page)

    def attr(m):
        hit = local(m.group(3), base)
        return f'{m.group(1)}{m.group(2)}a/{place(hit)}{m.group(4) or ""}{m.group(2)}' if hit else m.group(0)
    html = ATTR.sub(attr, html)

    def keep(path):
        rel = os.path.relpath(path, base)
        dest = os.path.join(out, rel)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copyfile(path, dest)
        files[rel] = dest
    # After the relink, so an attribute's path (now a/...) isn't published twice.
    for m in LITERAL.finditer(html):
        ref = m.group(1)
        built = '${' in ref
        # ponytail: one folder deep, not recursive; a script that builds nested paths needs more.
        target = os.path.normpath(os.path.join(base, os.path.dirname(ref.split('${')[0]) if built else ref))
        if not target.startswith(base + os.sep):
            continue
        if not built and os.path.isfile(target):
            keep(target)
        elif built and os.path.isdir(target):
            for f in sorted(os.listdir(target)):
                if os.path.isfile(os.path.join(target, f)):
                    keep(os.path.join(target, f))
    html = SKELETON.sub('', html).strip() + '\n'
    index = os.path.join(out, 'index.html')
    open(index, 'w', encoding='utf-8').write(html)
    return {'page': index, 'files': files}


def selftest():
    bad = 0

    def check(name, ok):
        nonlocal bad
        bad += not ok
        print(f'  {"ok  " if ok else "FAIL"} {name}')

    with tempfile.TemporaryDirectory() as tmp:
        os.makedirs(f'{tmp}/repo/web/public/fonts')
        os.makedirs(f'{tmp}/repo/specs/designs/assets')
        open(f'{tmp}/repo/web/public/grok.css', 'w').write(
            '@font-face{src:url("fonts/Sans.woff2") format("woff2")}\n.x{background:url(data:image/png;base64,AA)}')
        open(f'{tmp}/repo/web/public/fonts/Sans.woff2', 'wb').write(b'w')
        open(f'{tmp}/repo/specs/designs/assets/logo.svg', 'w').write('<svg/>')
        open(f'{tmp}/repo/specs/designs/logo.svg', 'w').write('<svg id="other"/>')
        os.makedirs(f'{tmp}/repo/specs/designs/assets/tiles')
        for r_ in ('one', 'two'):
            open(f'{tmp}/repo/specs/designs/assets/tiles/{r_}.webp', 'wb').write(b'w')
        open(f'{tmp}/repo/specs/designs/assets/mark.svg', 'w').write('<svg/>')
        open(f'{tmp}/repo/specs/designs/sb.html', 'w').write(
            '<!doctype html>\n<html lang="en"><head><title>Walkie</title>'
            '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=X"></head>\n<body>'
            '<template data-frame="a"><link rel="stylesheet" href="../../web/public/grok.css">'
            '<img src="assets/logo.svg#mark"><img src="logo.svg"><a href="#b">b</a></template>'
            '<script>f.srcdoc=\'<base href="\' + location.href + \'">\';'
            'img.src=`assets/tiles/${name}.webp`; logo="assets/mark.svg"; up="../../web/public/grok.css"</script>'
            '</body></html>')
        r = bundle(f'{tmp}/repo/specs/designs/sb.html', f'{tmp}/out')
        page = open(r['page']).read()
        check('a ../ stylesheet is copied beside the page and relinked',
              'href="a/grok.css"' in page and 'a/grok.css' in r['files'])
        check('a font inside it comes too, relinked from the copy',
              'url("Sans.woff2")' in open(r['files']['a/grok.css']).read() and 'a/Sans.woff2' in r['files'])
        check('two files with one name both survive', 'src="a/logo.svg#mark"' in page and 'src="a/logo-2.svg"' in page)
        check('a CDN, an anchor, a data: URI and a built string are left alone',
              'fonts.googleapis.com' in page and 'href="#b"' in page and 'location.href' in page and
              'data:image/png' in open(r['files']['a/grok.css']).read())
        check('the skeleton is stripped and the title kept',
              '<!doctype' not in page.lower() and '<body' not in page and page.startswith('<title>Walkie</title>'))
        check('a path a script builds publishes its folder at the same path',
              {'assets/tiles/one.webp', 'assets/tiles/two.webp'} <= set(r['files']) and
              '`assets/tiles/${name}.webp`' in page)
        check('a path a script names is published at that path', 'assets/mark.svg' in r['files'])
        check('a script path outside the storyboard folder is not', not any('grok.css' in k and k != 'a/grok.css' for k in r['files']))
        check('every published path is relative, with no ../', all(not k.startswith(('/', '..')) for k in r['files']))
    print(f'storyboard-bundle self-test: {bad} failed')
    return 1 if bad else 0


if __name__ == '__main__':
    a = sys.argv[1:]
    if a == ['--selftest']:
        sys.exit(selftest())
    if len(a) != 2:
        sys.exit(__doc__)
    print(json.dumps(bundle(*a), indent=1))
