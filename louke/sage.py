"""Sage commands - 需求澄清 + spec/issue 流程.

Sage 职责: 多轮提问 → spec.md → acceptance.md → 创建 GitHub issues。
所有命令通过本模块暴露。
"""
import argparse
import subprocess
import sys
from pathlib import Path


def register(subparsers):
    parser = subparsers.add_parser('sage', help='需求澄清 (Sage)')
    sub = parser.add_subparsers(dest='command', required=True, metavar='<command>')

    # quote-check: 检查 spec.md 的 quote 状态
    p = sub.add_parser('quote-check', help='检查 spec.md 是否所有 quote 都 ✓ resolved')
    p.add_argument('--spec', required=True, help='spec-id, 例 v0.1-001-init')

    # commit-spec: 封装多步 git 操作
    p = sub.add_parser('commit-spec', help='提交 spec + acceptance (git add + commit + push)')
    p.add_argument('--spec', required=True)
    p.add_argument('--message', required=True)

    # create-issues: 从 spec 创建 GitHub issues (含 schema)
    p = sub.add_parser('create-issues', help='从 spec 创建 GitHub issues (含 schema 验证)')
    p.add_argument('--spec', required=True)

    # lock-spec: 锁定 spec (前置: 所有 quote resolved + 用户确认)
    p = sub.add_parser('lock-spec', help='锁定 spec.md (quote_parser exit 0 + 用户确认)')
    p.add_argument('--spec', required=True)


def run(args):
    handlers = {
        'quote-check': cmd_quote_check,
        'commit-spec': cmd_commit_spec,
        'create-issues': cmd_create_issues,
        'lock-spec': cmd_lock_spec,
    }
    return handlers.get(args.command, lambda _: 1)(args) or 0


def cmd_quote_check(args):
    """调用 louke._tools.quote_parser --check-ready."""
    spec_path = f".louke/project/specs/{args.spec}/spec.md"
    result = subprocess.run(
        [sys.executable, '-m', 'louke._tools.quote_parser', spec_path, '--check-ready'],
        cwd=Path.cwd(),
    )
    return result.returncode


def cmd_commit_spec(args):
    """git add spec.md + acceptance.md + commit + push (封装多步)."""
    spec_path = f".louke/project/specs/{args.spec}"
    cmds = [
        ['git', 'add', f"{spec_path}/spec.md", f"{spec_path}/acceptance.md"],
        ['git', 'commit', '-m', args.message],
        ['git', 'push'],
    ]
    for cmd in cmds:
        result = subprocess.run(cmd, cwd=Path.cwd())
        if result.returncode != 0:
            print(f"failed: {' '.join(cmd)}", file=sys.stderr)
            return result.returncode
    return 0


def cmd_create_issues(args):
    """Create issues from spec — 占位."""
    print(f"create-issues: spec={args.spec} (to be implemented)")
    return 1


def cmd_lock_spec(args):
    """Lock spec — 占位."""
    print(f"lock-spec: spec={args.spec} (to be implemented)")
    return 1