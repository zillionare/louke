"""Devon commands - R-G-R 编码.

Devon 职责: Red → Green → Refactor 循环，单元测试驱动。
当前阶段没有专属工具（git 操作足够）；此模块为未来扩展预留。
"""
import argparse


def register(subparsers):
    parser = subparsers.add_parser('devon', help='R-G-R 编码 (Devon)')
    sub = parser.add_subparsers(dest='command', required=True, metavar='<command>')

    # run-tests: 运行当前任务的测试
    p = sub.add_parser('run-tests', help='运行测试（unit/集成）')
    p.add_argument('--scope', default='unit', choices=['unit', 'integration', 'all'])

    # commit-rgr: R-G-R 提交（按 PactKit 规范）
    p = sub.add_parser('commit-rgr', help='R-G-R 阶段提交 (按 PactKit commit 规范)')
    p.add_argument('--phase', required=True, choices=['red', 'green', 'refactor'])
    p.add_argument('--message', required=True)
    p.add_argument('--task-id', required=True, help='任务编号, 例 TASK-01')


def run(args):
    print(f"devon {args.command}: 占位实现")
    return 1