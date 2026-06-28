"""Lex commands - spec + issue 审核.

Lex 职责: 阶段一/二/三（spec 语义审核 / issue 覆盖验证 / schema 验证）。
"""
import argparse
import subprocess
import sys
from pathlib import Path


def register(subparsers):
    parser = subparsers.add_parser('lex', help='spec + issue 审核 (Lex)')
    sub = parser.add_subparsers(dest='command', required=True, metavar='<command>')

    # verify-acceptance: L1-L5 结构化校验 (Stage 1)
    p = sub.add_parser('verify-acceptance', help='运行 L1-L5 结构化校验 (Stage 1)')
    p.add_argument('--spec', required=True)
    p.add_argument('--repo', required=True, help='owner/repo (被开发的项目, 不是 holdpoint 框架本身)')

    # verify-issue: L1-L8 schema 验证 (Stage 3)
    p = sub.add_parser('verify-issue', help='运行 L1-L8 schema 验证 (Stage 3)')
    p.add_argument('--spec', required=True)
    p.add_argument('--repo', required=True)

    # quote-check: 复用 Sage 的 quote-check (同 tools/quote_parser.py)
    p = sub.add_parser('quote-check', help='检查 spec.md 是否所有 quote 都 ✓ resolved')
    p.add_argument('--spec', required=True)


def run(args):
    handlers = {
        'verify-acceptance': cmd_verify_acceptance,
        'verify-issue': cmd_verify_issue,
        'quote-check': cmd_quote_check,
    }
    return handlers.get(args.command, lambda _: 1)(args) or 0


def cmd_verify_acceptance(args):
    """调用 holdpoint._tools.verify_acceptance."""
    result = subprocess.run(
        [sys.executable, '-m', 'holdpoint._tools.verify_acceptance',
         '--spec', args.spec, '--repo', args.repo],
        cwd=Path.cwd(),
    )
    return result.returncode


def cmd_verify_issue(args):
    """调用 holdpoint._tools.verify_issue_schema."""
    result = subprocess.run(
        [sys.executable, '-m', 'holdpoint._tools.verify_issue_schema',
         '--spec', args.spec, '--repo', args.repo],
        cwd=Path.cwd(),
    )
    return result.returncode


def cmd_quote_check(args):
    """调用 holdpoint._tools.quote_parser (同 Sage quote-check)."""
    spec_path = f".holdpoint/project/specs/{args.spec}/spec.md"
    result = subprocess.run(
        [sys.executable, '-m', 'holdpoint._tools.quote_parser', spec_path, '--check-ready'],
        cwd=Path.cwd(),
    )
    return result.returncode