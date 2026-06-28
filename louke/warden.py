"""Warden commands - 项目奠基验证.

Warden 职责: 验证 Scout 的奠基工作（F1-F11 检查 + story 内容合理性）。
"""
import argparse
import subprocess
import sys
from pathlib import Path


def register(subparsers):
    parser = subparsers.add_parser('warden', help='项目奠基验证 (Warden)')
    sub = parser.add_subparsers(dest='command', required=True, metavar='<command>')

    # foundation-check: F1-F11 自动化检查
    p = sub.add_parser('foundation-check', help='运行 F1-F11 自动化检查')
    p.add_argument('--repo', required=True)
    p.add_argument('--version', required=True)
    p.add_argument('--spec-id', required=True)
    p.add_argument('--upstream', default='main')


def run(args):
    handlers = {
        'foundation-check': cmd_foundation_check,
    }
    return handlers.get(args.command, lambda _: 1)(args) or 0


def cmd_foundation_check(args):
    """调用 louke._tools.check_foundation."""
    result = subprocess.run(
        [sys.executable, '-m', 'louke._tools.check_foundation',
         args.repo, '--version', args.version,
         '--spec-id', args.spec_id, '--upstream', args.upstream],
        cwd=Path.cwd(),
    )
    return result.returncode