"""IDE board generation commands."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ._common import git_root
from .models import resolve_model


SKIP = {'README.md', 'ROSTER.md'}


def register(subparsers):
    parser = subparsers.add_parser('board', help='生成 IDE agent board')
    sub = parser.add_subparsers(dest='command', required=True, metavar='<command>')
    p = sub.add_parser('opencode', help='生成 OpenCode agents')
    p.add_argument('--dry-run', action='store_true')
    p = sub.add_parser('status', help='查看 board 状态')
    p.add_argument('--root', default='')
    p = sub.add_parser('vscode', help='VS Code board 当前不支持')
    p.add_argument('--dry-run', action='store_true')


def run(args):
    handlers = {'opencode': cmd_opencode, 'status': cmd_status, 'vscode': cmd_vscode}
    return handlers[args.command](args)


def parse_frontmatter(text: str) -> tuple[dict, str]:
    if not text.startswith('---\n'):
        return {}, text
    end = text.find('\n---\n', 4)
    if end == -1:
        return {}, text
    raw = text[4:end].splitlines()
    body = text[end + 5:]
    data = {}
    key = None
    for line in raw:
        if line.startswith('  - ') and key:
            data.setdefault(key, []).append(line[4:].strip())
        elif ':' in line:
            k, v = line.split(':', 1)
            key = k.strip()
            v = v.strip()
            data[key] = [] if not v else v
    return data, body


def agent_source(root: Path) -> Path:
    for candidate in (root / '.louke/agents', root / 'agents'):
        if candidate.exists():
            return candidate
    from ._common import package_root
    return package_root() / 'agents'


def cmd_opencode(args):
    root = getattr(args, 'root', None) or git_root() or Path.cwd()
    quiet = getattr(args, 'quiet', False)
    root = Path(root)
    src = agent_source(root)
    dest_dir = root / '.opencode/agents'
    generated = []
    for fp in sorted(src.glob('*.md')):
        if fp.name in SKIP:
            continue
        text = fp.read_text(encoding='utf-8')
        fm, body = parse_frontmatter(text)
        name = str(fm.get('name') or fp.stem).lower()
        description = fm.get('description') or fp.stem
        mode = fm.get('mode') or 'all'
        models = fm.get('models') or []
        if isinstance(models, str):
            models = [models]
        model = resolve_model(models[0], root=root) if models else ''
        out = f'---\ndescription: {description}\nmode: {mode}\nmodel: {model}\n---\n{body}'
        dest = dest_dir / f'{name}.md'
        generated.append(dest)
        if args.dry_run:
            if not quiet:
                print(f'[+] {dest}')
        else:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(out, encoding='utf-8')
    if not args.dry_run and not quiet:
        print(f'generated {len(generated)} OpenCode agents')
    return 0


def _default_agent_status(root: Path) -> str:
    project = root / 'opencode.json'
    if project.exists():
        try:
            if json.loads(project.read_text(encoding='utf-8')).get('default_agent') == 'maestro':
                return 'maestro (project opencode.json)'
        except json.JSONDecodeError:
            pass
    global_cfg = Path.home() / '.config/opencode/opencode.json'
    if global_cfg.exists():
        try:
            if json.loads(global_cfg.read_text(encoding='utf-8')).get('default_agent') == 'maestro':
                return 'maestro (global opencode.json)'
        except json.JSONDecodeError:
            pass
    return '(not set)'


def cmd_status(args):
    root = Path(args.root).resolve() if getattr(args, 'root', '') else (git_root() or Path.cwd())
    files = list((root / '.opencode/agents').glob('*.md')) if (root / '.opencode/agents').exists() else []
    ok = any('model:' in f.read_text(encoding='utf-8', errors='replace').split('---', 2)[1] for f in files if f.exists())
    mark = '✓' if ok else '-'
    print(f'opencode    {mark}  (.opencode/agents/ — {len(files)} agents)')
    print(f'default_agent: {_default_agent_status(root)}')
    return 0


def cmd_vscode(args):
    print('lk board vscode is not supported in this release', flush=True)
    return 1
