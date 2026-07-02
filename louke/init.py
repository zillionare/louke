"""Top-level init command for installing louke assets into a project."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

from ._common import git, git_root, package_root, ensure_gitignore_line


AGENT_COUNT = 12


def register(parser):
    """Register init arguments on the given parser."""
    _add_arguments(parser)


def _add_arguments(parser):
    parser.add_argument('target', help='新项目名或既存项目路径')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--backup', action='store_true')
    parser.add_argument('--force', action='store_true')
    parser.add_argument('--no-gitignore', action='store_true')
    parser.add_argument('--no-migrate', action='store_true')
    parser.add_argument('--board', default='opencode', choices=['opencode', 'none'])
    parser.add_argument('--with-issue-template', action='store_true', default=True)
    parser.add_argument('--no-issue-template', action='store_true')
    parser.add_argument('--with-workflows', action='store_true', default=True)
    parser.add_argument('--no-workflows', action='store_true')
    parser.add_argument('--no-default-agent', action='store_true')
    parser.add_argument('--force-default-agent', action='store_true')
    parser.add_argument('--json', action='store_true')
    parser.set_defaults(command='run')


def run(args):
    return cmd_init(args)


def _is_existing_path(raw: str) -> bool:
    expanded = Path(raw).expanduser()
    if raw in {'.', './'} or raw.startswith('../') or raw.startswith('~/'):
        return True
    if raw.startswith('/'):
        return expanded.exists()
    return raw.startswith('./') and expanded.exists()


def _target_path(raw: str) -> tuple[Path, bool]:
    if _is_existing_path(raw):
        return Path(raw).expanduser().resolve(), True
    return (Path.cwd() / raw).resolve(), False


def _copy_tree_files(src: Path, dst: Path, args, report: dict[str, list[str]], skip_names: set[str] | None = None):
    skip_names = skip_names or set()
    for source in sorted(src.glob('*.md')):
        if source.name in skip_names:
            continue
        dest = dst / source.name
        rel = str(dest)
        if not dest.exists():
            report['added'].append(rel)
            if not args.dry_run:
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, dest)
        elif dest.read_bytes() == source.read_bytes():
            report['skipped'].append(rel)
        elif args.force:
            report['skipped'].append(rel)
            if not args.dry_run:
                shutil.copy2(source, dest)
        elif args.backup:
            report['backed_up'].append(rel)
            if not args.dry_run:
                shutil.copy2(dest, dest.with_suffix(dest.suffix + '.bak'))
        else:
            report['skipped'].append(rel)


def _write_file_if_needed(src: Path, dest: Path, args, report: dict[str, list[str]]):
    rel = str(dest)
    if not src.exists():
        return
    if not dest.exists():
        report['added'].append(rel)
        if not args.dry_run:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
    elif dest.read_bytes() == src.read_bytes():
        report['skipped'].append(rel)
    elif args.force:
        report['skipped'].append(rel)
        if not args.dry_run:
            shutil.copy2(src, dest)
    elif args.backup:
        report['backed_up'].append(rel)
        if not args.dry_run:
            shutil.copy2(dest, dest.with_suffix(dest.suffix + '.bak'))
    else:
        report['skipped'].append(rel)


def _write_default_agent(root: Path, args, report: dict[str, list[str]]) -> int:
    if args.no_default_agent:
        return 0
    path = root / 'opencode.json'
    rel = str(path)
    data = {}
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
        except json.JSONDecodeError:
            print(f'opencode.json is not valid JSON: {path}', file=sys.stderr)
            return 1
    existing = data.get('default_agent')
    if existing and existing != 'maestro' and not args.force_default_agent:
        print('default_agent already set; use --force-default-agent to overwrite', file=sys.stderr)
        return 1
    if existing == 'maestro':
        report['skipped'].append(rel)
        return 0
    data['default_agent'] = 'maestro'
    report['added'].append(rel)
    if not args.dry_run:
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return 0


def _migrate_legacy(root: Path, args, report: dict[str, list[str]]) -> int:
    if args.no_migrate:
        return 0
    for name in ('wiki', 'raw'):
        old = root / name
        new = root / '.louke' / name
        if old.exists() and new.exists():
            print(f'legacy path conflict: {old} and {new}', file=sys.stderr)
            return 1
        if old.exists() and not new.exists():
            report['migrated'].append(f'{old} -> {new}')
            if not args.dry_run:
                new.parent.mkdir(parents=True, exist_ok=True)
                shutil.move(str(old), str(new))
    return 0


def cmd_init(args):
    target, adopt = _target_path(args.target)
    pkg = package_root()
    report = {'added': [], 'skipped': [], 'backed_up': [], 'migrated': []}

    if adopt:
        if not target.exists() or not target.is_dir():
            print(f'target does not exist: {target}', file=sys.stderr)
            return 1
        if not (target / '.git').exists():
            print(f'not a git repo: {target}', file=sys.stderr)
            return 2
    else:
        if target.exists() and any(target.iterdir()):
            print(f"Directory '{target.name}' already exists", file=sys.stderr)
            return 1
        if not args.dry_run:
            target.mkdir(parents=True, exist_ok=True)

    rc = _migrate_legacy(target, args, report)
    if rc:
        return rc

    dirs = [
        '.louke/agents', '.louke/templates', '.louke/project',
        '.louke/project/specs', '.louke/wiki/pages', '.louke/wiki/decisions',
        '.louke/raw',
    ]
    for d in dirs:
        path = target / d
        if not path.exists():
            report['added'].append(str(path))
            if not args.dry_run:
                path.mkdir(parents=True, exist_ok=True)

    _copy_tree_files(pkg / 'agents', target / '.louke/agents', args, report, skip_names={'README.md'})
    _copy_tree_files(pkg / 'templates', target / '.louke/templates', args, report)

    if not args.no_issue_template:
        _write_file_if_needed(pkg / '.github/ISSUE_TEMPLATE/feature.yml', target / '.github/ISSUE_TEMPLATE/feature.yml', args, report)
    if not args.no_workflows:
        _write_file_if_needed(pkg / '.github/workflows/louke-ci.yml', target / '.github/workflows/louke-ci.yml', args, report)

    if not args.no_gitignore:
        for line in ('.louke/agents/', '.louke/templates/'):
            ensure_gitignore_line(target / '.gitignore', line, dry_run=args.dry_run, report=report)

    if args.board == 'opencode':
        from . import board
        board_args = argparse.Namespace(command='opencode', dry_run=args.dry_run, root=target, quiet=args.json)
        rc = board.cmd_opencode(board_args)
        if rc:
            return rc
        ensure_gitignore_line(target / '.gitignore', '.opencode/agents/', dry_run=args.dry_run, report=report)

    rc = _write_default_agent(target, args, report)
    if rc:
        return rc

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        for key, marker in (('migrated', '[→]'), ('added', '[+]'), ('skipped', '[=]'), ('backed_up', '[!]')):
            for item in report[key]:
                print(f'{marker} {item}')
        print(f'louke initialized at {target}')
    return 0
