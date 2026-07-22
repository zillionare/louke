"""Deprecated compatibility adapter for the Runtime foundation program."""

from pathlib import Path

from .runtime.foundation import foundation_program_check


def register(subparsers):
    parser = subparsers.add_parser(
        "warden", help="deprecated compatibility adapter for foundation checks"
    )
    sub = parser.add_subparsers(dest="command", required=True, metavar="<command>")

    # foundation-check: F1-F11 automated checks
    p = sub.add_parser("foundation-check", help="run F1-F11 automated checks")
    p.add_argument("--repo", required=True)
    p.add_argument("--version", required=True)
    p.add_argument("--spec-id", required=True)
    p.add_argument("--upstream", default="main")


def run(args):
    handlers = {
        "foundation-check": cmd_foundation_check,
    }
    return handlers.get(args.command, lambda _: 1)(args) or 0


def cmd_foundation_check(args):
    """Run the shared Runtime foundation program without writing stage state."""
    result = foundation_program_check(Path.cwd())
    print(f"Runtime foundation status: {result.status}")
    if result.details:
        print(result.details)
    return 0 if result.status == "pass" else 1
