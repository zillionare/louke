"""Archer commands - test-plan + architecture/interfaces 编写.

Archer 职责: 阶段一（test-plan.md）+ 阶段二（architecture.md + interfaces.md）。
"""
import argparse
import subprocess
import sys
from pathlib import Path


def register(subparsers):
    parser = subparsers.add_parser('archer', help='test-plan + 架构设计 (Archer)')
    sub = parser.add_subparsers(dest='command', required=True, metavar='<command>')

    # ci-scan: AC 引用 + 反模式校验
    p = sub.add_parser('ci-scan', help='CI 扫描（AC 引用闭合 + 反模式）')
    p.add_argument('--spec', required=True)

    # check-acs: AC 覆盖率检查
    p = sub.add_parser('check-acs', help='AC 引用闭合检查')
    p.add_argument('--spec', required=True)

    # commit-test-plan: 提交 test-plan + architecture + interfaces
    p = sub.add_parser('commit-design', help='提交 test-plan + architecture + interfaces (git add + commit + push)')
    p.add_argument('--spec', required=True)
    p.add_argument('--message', required=True)


def run(args):
    handlers = {
        'ci-scan': cmd_ci_scan,
        'check-acs': cmd_check_acs,
        'commit-design': cmd_commit_design,
    }
    return handlers.get(args.command, lambda _: 1)(args) or 0


def cmd_ci_scan(args):
    """调用 holdpoint._tools.ci_scan."""
    result = subprocess.run(
        [sys.executable, '-m', 'holdpoint._tools.ci_scan',
         '--acceptance', f".holdpoint/project/specs/{args.spec}/acceptance.md",
         '--tests', 'tests/'],
        cwd=Path.cwd(),
    )
    return result.returncode


def cmd_check_acs(args):
    """调用 holdpoint._tools.check_acs."""
    result = subprocess.run(
        [sys.executable, '-m', 'holdpoint._tools.check_acs',
         '--acceptance', f".holdpoint/project/specs/{args.spec}/acceptance.md"],
        cwd=Path.cwd(),
    )
    return result.returncode


def cmd_commit_design(args):
    """git add test-plan.md + architecture.md + interfaces.md + commit + push."""
    spec_path = f".holdpoint/project/specs/{args.spec}"
    cmds = [
        ['git', 'add', f"{spec_path}/test-plan.md",
         f"{spec_path}/architecture.md", f"{spec_path}/interfaces.md"],
        ['git', 'commit', '-m', args.message],
        ['git', 'push'],
    ]
    for cmd in cmds:
        result = subprocess.run(cmd, cwd=Path.cwd())
        if result.returncode != 0:
            print(f"failed: {' '.join(cmd)}", file=sys.stderr)
            return result.returncode
    return 0