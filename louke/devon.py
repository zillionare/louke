"""Devon commands - R-G-R 编码.

Devon 职责: Red → Green → Refactor 循环, 单元测试驱动。
lk 提供: 运行测试 + 按 R-G-R 规范 commit。
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

from ._common import git


RGR_PREFIX = {
    'red': 'test: red',
    'green': 'feat: green',
    'refactor': 'refactor',
}


def register(subparsers):
    parser = subparsers.add_parser('devon', help='R-G-R 编码 (Devon)')
    sub = parser.add_subparsers(dest='command', required=True, metavar='<command>')

    p = sub.add_parser('run-tests', help='运行测试 (按 scope, FR-0570)')
    p.add_argument('--scope', default='unit',
                   choices=['unit', 'integration', 'e2e', 'all'],
                   help='测试范围')
    p.add_argument('--fast', action='store_true', help='快速失败模式 (-x)')

    p = sub.add_parser('commit-rgr', help='按 R-G-R 规范 commit (FR-0580 默认 no-push)')
    p.add_argument('--phase', required=True, choices=['red', 'green', 'refactor'])
    p.add_argument('--message', required=True, help='commit message 主体')
    p.add_argument('--task-id', required=True, help='任务编号, 例 TASK-01')
    p.add_argument('--issue', default='', help='issue 编号 (会写 Closes #N)')
    p.add_argument('--push', action='store_true', help='显式 push（默认 no-push）')


def run(args):
    handlers = {
        'run-tests': cmd_run_tests,
        'commit-rgr': cmd_commit_rgr,
    }
    return handlers.get(args.command, lambda _: 1)(args) or 0


# ---- FR-0570 project config ----

DEFAULT_TEST_CONFIG = {
    'command': 'python3',
    'args': ['-m', 'pytest', '-q', '--tb=short'],
    'paths': {
        'unit': 'tests/unit/',
        'integration': 'tests/',
        'e2e': 'tests/e2e/',
        'all': 'tests/',
    },
}


def _load_pyproject_test_config():
    try:
        import tomllib
    except ImportError:
        try:
            import tomli as tomllib  # type: ignore
        except ImportError:
            return None
    for path in (Path.cwd() / 'pyproject.toml',):
        if not path.exists():
            continue
        with open(path, 'rb') as f:
            data = tomllib.load(f)
        cfg = data.get('tool', {}).get('louke', {}).get('test')
        if not cfg:
            continue
        out = {
            'command': cfg.get('command', DEFAULT_TEST_CONFIG['command']),
            'args': list(cfg.get('args', [])),
            'paths': dict(DEFAULT_TEST_CONFIG['paths']),
        }
        out['paths'].update(cfg.get('paths', {}))
        return out
    return None


def _resolve_test_config(scope):
    cfg = _load_pyproject_test_config() or DEFAULT_TEST_CONFIG
    if not cfg.get('command'):
        print('tool.louke.test.command is empty; please set [tool.louke.test] in pyproject.toml', file=sys.stderr)
        return None
    args = list(cfg['args'])
    test_path = cfg['paths'].get(scope, cfg['paths']['all'])
    return cfg['command'], args, test_path


def cmd_run_tests(args):
    """FR-0570: per-project [tool.louke.test] or fallback hardcoded pytest."""
    cwd = Path.cwd()
    resolved = _resolve_test_config(args.scope)
    if resolved is None:
        return 1
    command, base_args, test_path = resolved
    cmd = [command, *base_args, test_path]
    if args.fast and '-x' not in cmd:
        cmd.append('-x')

    print(f"=== Run Tests ({args.scope}) ===")
    print(f"Command: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd)
    return result.returncode


def cmd_commit_rgr(args):
    """FR-0580: 默认 no-push；--push 才 push；支持 --issue #N 写 Closes #N。"""
    cwd = Path.cwd()
    prefix = RGR_PREFIX[args.phase]
    closes = f'Closes {args.issue}' if args.issue else ''
    full_msg = ' – '.join([p for p in [prefix, args.task_id, args.message, closes] if p])

    print(f"=== R-G-R Commit ===")
    print(f"Phase:  {args.phase}")
    print(f"Prefix: {prefix}")
    print(f"Full:   {full_msg}")
    print()

    rc, out, _ = git('commit', '-m', full_msg, cwd=cwd)
    if rc != 0:
        print(f"git commit failed: {out}", file=sys.stderr)
        return 1

    rc, sha, _ = git('rev-parse', '--short', 'HEAD', cwd=cwd)
    print(f"✓ Committed: {sha}")
    if args.push:
        rc, out, _ = git('push', cwd=cwd)
        if rc != 0:
            print(f"git push failed: {out}", file=sys.stderr)
            return rc
        print(f"✓ Pushed: {sha}")
    else:
        print('(push skipped; pass --push to push)')
    return 0