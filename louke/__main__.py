"""lk CLI entry point.

Usage:
    lk <agent> <command> [options]

Examples:
    lk scout identity-check --repo owner/repo
    lk sage quote-check --spec v0.1-001-init
    lk warden foundation-check --repo owner/repo --version v0.1 --spec-id v0.1-001-init
    lk lex verify-acceptance --spec v0.1-001-init
    lk archer ci-scan --spec v0.1-001-init

设计:
- 每 agent 一个模块 (louke/{agent}.py)，暴露 register(subparsers) 和 run(args)
- __main__ 解析 lk <agent> <command>，dispatch 到对应 agent.run()
"""
import argparse
import sys

from . import __version__
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
    init as init_cmd,
    board,
    models,
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
    'init': init_cmd,
    'board': board,
    'models': models,
}


def build_parser():
    parser = argparse.ArgumentParser(
        prog='lk',
        description='louke CLI - 工具统一入口（每 agent 一个子命令空间）',
    )
    parser.add_argument('--version', '-v', action='version', version=f'lk {__version__}')
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
        print(f"lk {args.agent} {getattr(args, 'command', '?')}: {e}", file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())