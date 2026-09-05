#!/usr/bin/env python3
"""Bundle native Codex/Astra instructions with the shared ship templates."""
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def build(destination):
    destination = Path(destination).resolve()
    if destination.exists():
        raise SystemExit(f'Destination must be new: {destination}')
    source = ROOT / 'plugins/ship'
    for skill, upstream in [('ship', 'pipeline'), ('verify', 'verify')]:
        target = destination / 'skills' / skill
        target.mkdir(parents=True)
        shutil.copyfile(ROOT / f'codex/{skill}.md', target / 'SKILL.md')
        refs = target / 'reference'
        refs.mkdir()
        if skill == 'ship':
            for name in ['storyboard.html', 'go-card.html', 'review-card.html']:
                text = (source / 'skills/pipeline/reference' / name).read_text()
                if name == 'review-card.html':
                    text = text.replace('Merge? &nbsp;·&nbsp; or call a change?', '{{LANDING_STATUS}}')
                (refs / name).write_text(text)
    manifest = json.loads((source / '.codex-plugin/plugin.json').read_text())
    manifest['description'] = 'Ship express, self-directed, and storyboard-led changes with Astra subagents.'
    manifest['interface']['shortDescription'] = 'Ship changes with Astra subagents and design gates when needed.'
    manifest['interface']['longDescription'] = 'The shared ship workflow adapted for Codex: express, design, and next; native Astra subagents; real verification; repository landing contracts.'
    (destination / '.codex-plugin').mkdir()
    (destination / '.codex-plugin/plugin.json').write_text(json.dumps(manifest, indent=2) + '\n')
    revision = subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip()
    (destination / 'SOURCE.json').write_text(json.dumps({'repository': 'peteknowsai/ship', 'revision': revision}, indent=2) + '\n')
    return destination


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('usage: build-codex.py NEW_OUTPUT_DIRECTORY')
    print(build(sys.argv[1]))
