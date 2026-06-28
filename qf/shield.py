"""Shield commands - e2e 测试编写 (B 级).

Shield 职责: 按 test-plan §6 写 e2e 测试（Playwright/testclient/DB 直查）。
B 级 agent — 方法固定，省成本。
"""
import argparse


def register(subparsers):
    parser = subparsers.add_parser('shield', help='e2e 测试编写 (Shield, B 级)')
    sub = parser.add_subparsers(dest='command', required=True, metavar='<command>')

    # run-e2e: 运行 e2e 测试
    p = sub.add_parser('run-e2e', help='运行 e2e 测试套件')
    p.add_argument('--spec', default='', help='spec-id (过滤)')

    # commit-e2e: 提交 e2e 测试
    p = sub.add_parser('commit-e2e', help='提交 e2e 测试 (按 PactKit 规范)')
    p.add_argument('--spec', required=True)
    p.add_argument('--message', required=True)


def run(args):
    print(f"shield {args.command}: 占位实现")
    return 1