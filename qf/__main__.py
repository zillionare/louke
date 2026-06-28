"""qf CLI entry point.

Usage:
    qf <agent> <command> [options]

Examples:
    qf scout identity-check --repo owner/repo
    qf sage quote-check --spec v0.1-001-init
    qf warden foundation-check --repo owner/repo --version v0.1 --spec-id v0.1-001-init
    qf lex verify-acceptance --spec v0.1-001-init
    qf archer ci-scan --spec v0.1-001-init

设计:
- 每 agent 一个模块 (qf/{agent}.py)，暴露 register(subparsers) 和 run(args)
- __main__ 解析 qf <agent> <command>，dispatch 到对应 agent.run()
"""
import argparse
import sys

from . import (
    scout,
    sage,
    warden,
    lex,
    archer,
    keeper,
    judge,
    prism,
    devon,
    shield,
    librarian,
    maestro,
)

AGENTS = {
    'scout': scout,
    'sage': sage,
    'warden': warden,
    'lex': lex,
    'archer': archer,
    'keeper': keeper,
    'judge': judge,
    'prism': prism,
    'devon': devon,
    'shield': shield,
    'librarian': librarian,
    'maestro': maestro,
}


def build_parser():
    parser = argparse.ArgumentParser(
        prog='qf',
        description='quanti-forge CLI - 工具统一入口（每 agent 一个子命令空间）',
    )
    subparsers = parser.add_subparsers(
        dest='agent', required=True, metavar='<agent>'
    )
    for name, module in AGENTS.items():
        if hasattr(module, 'register'):
            module.register(subparsers)
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    agent_module = AGENTS.get(args.agent)
    if not agent_module or not hasattr(agent_module, 'run'):
        parser.error(f"agent '{args.agent}' 未实现")
        return 1
    try:
        return agent_module.run(args) or 0
    except Exception as e:
        print(f"qf {args.agent} {getattr(args, 'command', '?')}: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())