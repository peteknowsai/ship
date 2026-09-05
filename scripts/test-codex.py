#!/usr/bin/env python3
"""Check a portable build against the shared source, without invoking models."""
import importlib.util
import json
import tempfile
from pathlib import Path

root = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('builder', root / 'scripts/build-codex.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)
with tempfile.TemporaryDirectory() as temporary:
    output = builder.build(Path(temporary) / 'ship')
    assert set(p.name for p in (output / 'skills').iterdir()) == {'ship', 'verify'}
    for name, upstream in [('ship', 'pipeline'), ('verify', 'verify')]:
        assert (output / f'skills/{name}/SKILL.md').read_bytes() == (root / f'codex/{name}.md').read_bytes()
    for source in (root / 'plugins/ship/skills/pipeline/reference').glob('*.html'):
        expected = source.read_text().replace('Merge? &nbsp;·&nbsp; or call a change?', '{{LANDING_STATUS}}')
        assert (output / 'skills/ship/reference' / source.name).read_text() == expected
    assert '{{LANDING_STATUS}}' in (output / 'skills/ship/reference/review-card.html').read_text()
    manifest = json.loads((output / '.codex-plugin/plugin.json').read_text())
    assert (output / manifest['skills']).is_dir()
    assert not list(output.rglob('dispatch.mjs'))
    try:
        builder.build(output)
    except SystemExit:
        pass
    else:
        raise AssertionError('Builder must not overwrite an existing installation')
print('PASS: portable package, native skills and exact shared templates, native-agent-only skills, overwrite protection')
