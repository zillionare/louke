"""Agent subcommand router.

Usage: lk agent <name> <subcommand> [options]

All agent commands are dispatched through this module.
"""
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


def register(parser):
    sub = parser.add_subparsers(dest='agent_name', required=True, metavar='<agent>')
    for name, module in AGENTS.items():
        if hasattr(module, 'register'):
            module.register(sub)


def run(args):
    module = AGENTS.get(args.agent_name)
    if not module or not hasattr(module, 'run'):
        print(f"lk agent: '{args.agent_name}' not found", flush=True)
        return 1
    return module.run(args) or 0
