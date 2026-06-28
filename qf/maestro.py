"""Maestro commands - 流程推进控制.

Maestro 职责: 协调所有 agent，监控退出条件，决策推进/退回/上报。
"""
import argparse


def register(subparsers):
    parser = subparsers.add_parser('maestro', help='流程推进控制 (Maestro)')
    sub = parser.add_subparsers(dest='command', required=True, metavar='<command>')

    # status: 查看当前阶段 + 退出条件
    p = sub.add_parser('status', help='查看当前 milestone + spec 的阶段进度')

    # advance: 推进到下一阶段
    p = sub.add_parser('advance', help='推进到下一阶段 (前提: 当前阶段评审通过)')
    p.add_argument('--stage', required=True, help='当前阶段代码, 例 M-DEV')

    # regress: 退回当前阶段
    p = sub.add_parser('regress', help='退回当前阶段 (评审不通过)')
    p.add_argument('--stage', required=True)
    p.add_argument('--reason', required=True)

    # escalate: 上报用户
    p = sub.add_parser('escalate', help='上报用户 (连续失响应 / 需求根本矛盾)')
    p.add_argument('--reason', required=True)


def run(args):
    print(f"maestro {args.command}: 占位实现")
    return 1