"""Model alias commands."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path

from ._common import git_root

SCHEMA = 'louke://models-config'


def register(parser):
    """Register models subcommands on the given parser."""
    sub = parser.add_subparsers(dest='command', required=True, metavar='<command>')
    sub.add_parser('list', help='列出模型解析结果')
    p = sub.add_parser('doctor', help='检查模型解析')
    p.add_argument('--fix-auto', action='store_true')
    p.add_argument('--ide', default='opencode')
    p = sub.add_parser('bind', help='绑定抽象名')
    p.add_argument('abstract')
    p.add_argument('full')
    p.add_argument('--project', action='store_true')
    p = sub.add_parser('unbind', help='解绑抽象名')
    p.add_argument('abstract')
    p.add_argument('--project', action='store_true')


def run(args):
    return {
        'list': cmd_list,
        'doctor': cmd_doctor,
        'bind': cmd_bind,
        'unbind': cmd_unbind,
    }[args.command](args)


def config_path(project: bool = False, root=None) -> Path:
    if project:
        root = root or git_root() or Path.cwd()
        return root / '.louke/models.json'
    return Path.home() / '.louke/models.json'


def load_config(path: Path) -> dict:
    if not path.exists():
        return {'$schema': SCHEMA, 'version': 1, 'aliases': {}, 'assignments': {}}
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
    except json.JSONDecodeError:
        data = {}
    data.setdefault('$schema', SCHEMA)
    data.setdefault('version', 1)
    data.setdefault('aliases', {})
    data.setdefault('assignments', {})
    return data


def save_config(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    data['$schema'] = SCHEMA
    data.setdefault('version', 1)
    data.setdefault('aliases', {})
    data.setdefault('assignments', {})
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def normalize(value: str) -> str:
    return re.sub(r'[^a-z0-9]+', '', value.lower())


def opencode_models() -> list[str]:
    try:
        out = subprocess.check_output(['opencode', 'models'], text=True, stderr=subprocess.DEVNULL)
    except Exception:
        env = ''
        return [x.strip() for x in env.splitlines() if x.strip()]
    models = []
    for line in out.splitlines():
        token = line.strip().split()[0] if line.strip() else ''
        if '/' in token:
            models.append(token)
    return models


def used_models(root=None) -> list[str]:
    root = root or git_root() or Path.cwd()
    from .board import agent_source, parse_frontmatter
    result = []
    for fp in sorted(agent_source(root).glob('*.md')):
        if fp.name in {'README.md', 'ROSTER.md'}:
            continue
        fm, _ = parse_frontmatter(fp.read_text(encoding='utf-8'))
        models = fm.get('models') or []
        if isinstance(models, str):
            models = [models]
        result.extend(models)
    return sorted(set(result))


def resolve_model(name: str, root=None, models=None) -> str:
    root = root or git_root() or Path.cwd()
    project_aliases = load_config(config_path(True, root)).get('aliases', {})
    user_aliases = load_config(config_path(False)).get('aliases', {})
    if name in project_aliases:
        return project_aliases[name]
    if name in user_aliases:
        return user_aliases[name]
    candidates = models if models is not None else opencode_models()
    target = normalize(name)
    strong = [m for m in candidates if normalize(m.split('/')[-1]) == target]
    if strong:
        non_opencode = sorted([m for m in strong if not m.startswith('opencode/')])
        return (non_opencode or sorted(strong))[0]
    weak = [m for m in candidates if target in normalize(m.split('/')[-1]) or normalize(m.split('/')[-1]) in target]
    if len(weak) == 1:
        return weak[0]
    return name


def cmd_list(args):
    for name in used_models():
        resolved = resolve_model(name)
        print(f'{name}\t{resolved if resolved != name else "-"}')
    return 0


def cmd_doctor(args):
    models = opencode_models()
    ok = True
    fixes = {}
    for name in used_models():
        resolved = resolve_model(name, models=models)
        if resolved == name and '/' not in resolved:
            print(f'✗ {name} unresolved; run: lk models bind {name} provider/{name}')
            ok = False
        else:
            print(f'✓ {name} -> {resolved}')
            fixes[name] = resolved
    if args.fix_auto and fixes:
        path = config_path(False)
        data = load_config(path)
        data['aliases'].update(fixes)
        save_config(path, data)
    return 0 if ok else 1


def cmd_bind(args):
    path = config_path(args.project)
    data = load_config(path)
    data['aliases'][args.abstract] = args.full
    save_config(path, data)
    return 0


def cmd_unbind(args):
    path = config_path(args.project)
    data = load_config(path)
    data['aliases'].pop(args.abstract, None)
    save_config(path, data)
    return 0
