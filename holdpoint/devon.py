"""Devon commands - R-G-R 编码.

Devon 职责: Red → Green → Refactor 循环, 单元测试驱动。
hp 提供: 运行测试 + 按 R-G-R 规范 commit。
"""
import argparse
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

    p = sub.add_parser('run-tests', help='运行测试 (按 scope)')
    p.add_argument('--scope', default='unit',
                   choices=['unit', 'integration', 'e2e', 'all'],
                   help='测试范围')
    p.add_argument('--fast', action='store_true', help='快速失败模式 (-x)')

    p = sub.add_parser('commit-rgr', help='按 R-G-R 规范 commit (检查前缀格式)')
    p.add_argument('--phase', required=True, choices=['red', 'green', 'refactor'])
    p.add_argument('--message', required=True, help='commit message 主体')
    p.add_argument('--task-id', required=True, help='任务编号, 例 TASK-01')

    p = sub.add_parser('branch-create', help='创建任务分支 (feat/{spec-id}/{task-id})')
    p.add_argument('--spec-id', required=True)
    p.add_argument('--task-id', required=True)


def run(args):
    handlers = {
        'run-tests': cmd_run_tests,
        'commit-rgr': cmd_commit_rgr,
        'branch-create': cmd_branch_create,
    }
    return handlers.get(args.command, lambda _: 1)(args) or 0


def cmd_run_tests(args):
    """Run tests by scope."""
    cwd = Path.cwd()
    scope_map = {
        'unit': 'tests/unit/',
        'integration': 'tests/',
        'e2e': 'tests/e2e/',
        'all': 'tests/',
    }
    test_path = scope_map[args.scope]
    cmd = ['python3', '-m', 'pytest', test_path, '-q', '--tb=short']
    if args.fast:
        cmd.append('-x')

    print(f"=== Run Tests ({args.scope}) ===")
    print(f"Path: {test_path}")
    result = subprocess.run(cmd, cwd=cwd)
    return result.returncode


def cmd_commit_rgr(args):
    """按 R-G-R 规范 commit - 强制 phase 前缀."""
    cwd = Path.cwd()
    prefix = RGR_PREFIX[args.phase]
    full_msg = f"{prefix} – {args.task_id} {args.message}"

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
    return 0


def cmd_branch_create(args):
    """创建任务分支 feat/{spec-id}/{task-id}."""
    cwd = Path.cwd()
    branch_name = f"feat/{args.spec_id}/{args.task_id}"

    print(f"=== Branch Create ===")
    print(f"Branch: {branch_name}")

    rc, out, _ = git('checkout', '-b', branch_name, cwd=cwd)
    if rc != 0:
        print(f"git checkout failed: {out}", file=sys.stderr)
        return 1

    rc, _, _ = git('push', '-u', 'origin', branch_name, cwd=cwd)
    if rc != 0:
        print(f"git push failed (branch still created locally)", file=sys.stderr)

    print(f"✓ Branch created: {branch_name}")
    return 0