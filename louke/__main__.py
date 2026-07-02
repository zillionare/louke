"""lk CLI entry point.

Usage:
    lk <command> [options]               # user-facing commands
    lk agent <name> <subcommand> [options]  # agent commands

User-facing commands:
    lk init <name|path>         Initialize/adopt louke project skeleton
    lk models list|doctor|bind|unbind  Manage abstract model bindings
    lk board opencode|status    Generate IDE agent boards
    lk upgrade                  Upgrade louke via pip
    lk version                  Print version (also: lk --version, lk -v)
    lk help                     Print help (also: lk --help, lk -h)

Agent commands:
    lk agent scout identity-check --repo owner/repo
    lk agent sage quote-check --spec v0.1-001-init
    lk agent warden foundation-check --repo owner/repo --version v0.1 --spec-id v0.1-001-init
    lk agent lex verify-acceptance --spec v0.1-001-init
    lk agent archer ci-scan --spec v0.1-001-init

设计:
- 用户面命令走 argparse subparser，得到完整 Namespace 后调用模块 run()。
- agent 子命令 lk agent <name> <cmd> 通过 agent_main 路由。
- __main__ 预先拦截 --version/-v/--help/-h/version/help/upgrade，避免 argparse subparser required 冲突。
"""
import argparse
import sys

from . import __version__
from . import init as init_cmd
from . import models as models_cmd
from . import board as board_cmd
from . import agent as agent_main


USER_COMMANDS = {
    'init': init_cmd,
    'models': models_cmd,
    'board': board_cmd,
}


def build_parser():
    parser = argparse.ArgumentParser(prog='lk', add_help=False)
    parser.add_argument('--help', '-h', action='store_true')
    parser.add_argument('--version', '-v', action='store_true')
    subparsers = parser.add_subparsers(dest='command', metavar='<command>')
    for name, module in USER_COMMANDS.items():
        sub = subparsers.add_parser(name, add_help=False)
        if hasattr(module, 'register'):
            module.register(sub)
    subparsers.add_parser('version', add_help=False)
    subparsers.add_parser('help', add_help=False)
    subparsers.add_parser('upgrade', add_help=False)
    agent_parser = subparsers.add_parser('agent', add_help=False)
    if hasattr(agent_main, 'register'):
        agent_main.register(agent_parser)
    return parser


def _do_upgrade(extra_args):
    """lk upgrade — find the venv that owns lk and pip install --upgrade louke there."""
    import subprocess, os

    # 1. Find the venv: lk 入口脚本 shebang 指向 venv python
    lk_bin = os.path.realpath(sys.argv[0])
    # /Users/.../.local/bin/lk -> symlink -> ~/.louke/venv/bin/lk
    venv_bin = os.path.dirname(lk_bin)  # ~/.louke/venv/bin
    venv_pip = os.path.join(venv_bin, 'pip')
    venv_python = os.path.join(venv_bin, 'python3')

    if not os.path.isfile(venv_pip):
        print(f'lk upgrade: cannot find venv pip at {venv_pip}', file=sys.stderr)
        print('hint: run install.sh again to recreate the venv', file=sys.stderr)
        return 1

    cmd = [venv_python, '-m', 'pip', 'install', '--upgrade', 'louke'] + extra_args
    print(f'Running: {" ".join(cmd)}')
    result = subprocess.run(cmd)
    if result.returncode == 0:
        # Verify
        try:
            out = subprocess.check_output([venv_python, '-c', 'from louke import __version__; print(__version__)'], text=True).strip()
            print(f'✓ louke upgraded to {out}')
        except Exception:
            pass
    return result.returncode


def build_command_parser(module, prog):
    """Build a standalone parser for a user-facing command."""
    parser = argparse.ArgumentParser(prog=prog, add_help=True)
    if hasattr(module, 'register'):
        module.register(parser)
    return parser


def main(argv=None):
    raw = list(argv if argv is not None else sys.argv[1:])

    if not raw or raw[0] in ('--version', '-v', 'version'):
        print(f'lk {__version__}')
        return 0
    if raw[0] in ('--help', '-h', 'help'):
        print_help_text()
        return 0
    if raw[0] == 'upgrade':
        return _do_upgrade(raw[1:])
    if raw[0] == 'agent':
        # Re-parse with help parser so agent subparser handles 'agent scout xxx'
        parser = build_parser()
        try:
            args = parser.parse_args(raw)
        except SystemExit as e:
            return e.code if isinstance(e.code, int) else 1
        return agent_main.run(args)
    if raw[0] in USER_COMMANDS:
        module = USER_COMMANDS[raw[0]]
        parser = build_command_parser(module, f'lk {raw[0]}')
        try:
            args = parser.parse_args(raw[1:])
        except SystemExit as e:
            return e.code if isinstance(e.code, int) else 1
        try:
            return module.run(args) or 0
        except Exception as e:
            print(f"lk {raw[0]}: {e}", file=sys.stderr)
            return 1

    parser = build_parser()
    parser.print_help()
    return 0


def _dispatch_agent(argv):
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as e:
        return e.code if isinstance(e.code, int) else 1
    return agent_main.run(args)


def print_help_text():
    print(f'lk {__version__} — louke CLI')
    print()
    print('User-facing commands:')
    print('  lk init <name|path>         Initialize/adopt louke project skeleton')
    print('  lk models list|doctor|bind|unbind  Manage abstract model bindings')
    print('  lk board opencode|status    Generate IDE agent boards')
    print('  lk upgrade                  Upgrade louke via pip')
    print('  lk version                  Print version')
    print('  lk help                     Print this help')
    print()
    print('Agent commands:')
    print('  lk agent <name> <cmd> [opts]')
    print('    scout      identity-check, foundation, invite-owner, commit-foundation')
    print('    sage       quote-check, commit-spec, create-issues, record-lock')
    print('    warden     foundation-check')
    print('    lex        verify-acceptance, verify-issue, verify-project, quote-check')
    print('    archer     ci-scan, check-acs, commit-design, validate-test-plan, validate-arch')
    print('    keeper     gate, regression')
    print('    judge      security-audit, quick-scan')
    print('    prism      review, test-patterns, security-quick-scan, code-quality')
    print('    devon      run-tests, commit-rgr')
    print('    shield     run-e2e, commit-e2e, scaffold')
    print('    librarian  distill, lint, rebuild-index, from-raw, write')
    print('    maestro    status, advance, regress, escalate')
    print()
    print('Run lk <command> --help for detailed usage.')


if __name__ == '__main__':
    sys.exit(main())
