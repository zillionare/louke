"""Warden commands - project foundation validation.

Warden responsibilities: validate Scout's foundation work (F1-F11 checks +
story content sanity).
"""
import argparse
import subprocess
import sys
from pathlib import Path


def register(subparsers):
    parser = subparsers.add_parser('warden', help='project foundation validation (Warden)')
    sub = parser.add_subparsers(dest='command', required=True, metavar='<command>')

    # foundation-check: F1-F11 automated checks
    p = sub.add_parser('foundation-check', help='run F1-F11 automated checks')
    p.add_argument('--repo', required=True)
    p.add_argument('--version', required=True)
    p.add_argument('--spec-id', required=True)
    p.add_argument('--upstream', default='main')


def run(args):
    handlers = {
        'foundation-check': cmd_foundation_check,
    }
    return handlers.get(args.command, lambda _: 1)(args) or 0


def cmd_foundation_check(args):
    """Invoke louke._tools.check_foundation."""
    result = subprocess.run(
        [sys.executable, '-m', 'louke._tools.check_foundation',
         args.repo, '--version', args.version,
         '--spec-id', args.spec_id, '--upstream', args.upstream],
        cwd=Path.cwd(),
    )
    return result.returncode