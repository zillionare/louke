"""Keeper commands - gate 检查.

Keeper 职责: per-commit gate (R-G-R + tests pass + lint + commit 格式) +
回归判断（合并 Shield 的判断部分）。
"""
import argparse
import subprocess
import sys
from pathlib import Path


def register(subparsers):
    parser = subparsers.add_parser('keeper', help='gate 检查 (Keeper)')
    sub = parser.add_subparsers(dest='command', required=True, metavar='<command>')

    # gate: 完整 gate 检查
    p = sub.add_parser('gate', help='per-commit gate 检查 (R-G-R + tests + lint + commit)')
    p.add_argument('--commit-range', default='HEAD~1..HEAD',
                   help='要检查的 commit 范围 (默认 HEAD~1..HEAD)')

    # regression: 回归判断 (合并 Shield 的判断部分)
    p = sub.add_parser('regression', help='回归判断 (per-bug-fix, 对比修复前后)')
    p.add_argument('--baseline', default='main', help='基线 commit/branch')
    p.add_argument('--current', default='HEAD', help='当前 commit/branch')


def run(args):
    handlers = {
        'gate': cmd_gate,
        'regression': cmd_regression,
    }
    return handlers.get(args.command, lambda _: 1)(args) or 0


def cmd_gate(args):
    """Per-commit gate check — 占位 + 调 check_assertions.py 浅扫."""
    print(f"gate check: range={args.commit_range}")
    # 调 check_assertions.py 做 assertion hygiene 浅扫
    result = subprocess.run(
        ['python3', 'tools/check_assertions.py', 'tests/'],
        cwd=Path.cwd(),
    )
    return result.returncode


def cmd_regression(args):
    """Regression judgment — 占位."""
    print(f"regression: baseline={args.baseline}, current={args.current}")
    print("此命令对比修复前后测试结果，需完整实现")
    return 1