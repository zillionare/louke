"""Prism commands - 代码 review (含测试代码 + 安全 quick scan).

Prism 职责: 多视角代码 review + 批判性视角 + 测试反模式扫描 + 安全 quick scan。
"""
import argparse


def register(subparsers):
    parser = subparsers.add_parser('prism', help='代码 review (Prism)')
    sub = parser.add_subparsers(dest='command', required=True, metavar='<command>')

    # review: 完整 review (生产 + 测试 + 安全 quick scan)
    p = sub.add_parser('review', help='完整代码 review (生产 + 测试 + 安全)')
    p.add_argument('--diff', required=True, help='要 review 的 git diff')

    # test-patterns: 测试代码反模式扫描 (8 类)
    p = sub.add_parser('test-patterns', help='测试代码反模式扫描 (test-plan §1.3)')
    p.add_argument('--tests', default='tests/')

    # security-quick-scan: 浅层安全 pattern 扫描
    p = sub.add_parser('security-quick-scan', help='浅层安全 pattern (eval/exec/硬编码密钥)')
    p.add_argument('--diff', required=True)


def run(args):
    print(f"prism {args.command}: 占位实现，需集成现有 review 逻辑")
    return 1