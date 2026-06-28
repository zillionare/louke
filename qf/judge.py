"""Judge commands - 安全审计 (S 级).

Judge 职责: per-milestone 深度安全审计。S 级 agent，慢/深/贵，
跑每个 commit 不现实（成本/收益不匹配）。
"""
import argparse
import subprocess
import sys
from pathlib import Path


def register(subparsers):
    parser = subparsers.add_parser('judge', help='安全审计 (Judge, S 级)')
    sub = parser.add_subparsers(dest='command', required=True, metavar='<command>')

    # security-audit: per-milestone 深度审计
    p = sub.add_parser('security-audit', help='per-milestone 深度安全审计')
    p.add_argument('--release', required=True, help='release 分支, 例 releases/v0.1')
    p.add_argument('--baseline', default='main', help='基线 (默认 main)')
    p.add_argument('--checklist', default='.quanti-forge/templates/security-checklist.md',
                   help='审计基线 (默认 security-checklist.md)')

    # quick-scan: 浅层 pattern 扫描 (per-PR 或 pre-commit)
    p = sub.add_parser('quick-scan', help='浅层安全 quick scan (per-PR 触发)')
    p.add_argument('--diff', required=True, help='要扫描的 diff')


def run(args):
    handlers = {
        'security-audit': cmd_security_audit,
        'quick-scan': cmd_quick_scan,
    }
    return handlers.get(args.command, lambda _: 1)(args) or 0


def cmd_security_audit(args):
    """Per-milestone deep security audit — 占位，需要 S 级 agent 实现."""
    print(f"security-audit: release={args.release}, baseline={args.baseline}, checklist={args.checklist}")
    print("此命令应由 S 级 agent 实现（深度语义审计），当前为占位")
    return 1


def cmd_quick_scan(args):
    """Quick scan for obvious security patterns — 占位."""
    print(f"quick-scan: diff={args.diff}")
    print("此命令扫描明显安全 pattern (eval/exec/硬编码密钥等)")
    return 1