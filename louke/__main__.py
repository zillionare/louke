"""lk CLI entry point.

Usage:
    lk <command> [options]               # user-facing commands
    lk agent <name> <subcommand> [options]  # agent commands

User-facing commands:
    lk init <name|path>         Initialize/adopt louke project skeleton
    lk models list|doctor|bind|unbind  Manage abstract model bindings
    lk board opencode|status    Generate IDE agent boards
    lk serve [--host H --port P] Start the web collaboration server
    lk upgrade                  Upgrade louke via pip
    lk version                  Print version (also: lk --version, lk -v)
    lk help                     Print help (also: lk --help, lk -h)

Agent commands:
    lk agent scout identity-check --repo owner/repo
    lk agent sage quote-check --spec v0.1-001-init
    lk agent warden foundation-check --repo owner/repo --version v0.1 --spec-id v0.1-001-init
    lk agent lex verify-acceptance --spec v0.1-001-init
    lk agent archer ci-scan --spec v0.1-001-init

Design:
- User-facing commands go through argparse subparsers; once a full Namespace is
  parsed, the module's run() is invoked.
- Agent subcommands `lk agent <name> <cmd>` are routed via agent_main.
- __main__ pre-intercepts --version/-v/--help/-h/version/help/upgrade to avoid
  argparse subparser `required` conflicts.
"""

import argparse
import sys
from pathlib import Path

from . import __version__
from . import init as init_cmd
from . import models as models_cmd
from . import board as board_cmd
from . import serve as serve_cmd
from . import e2e as e2e_cmd
from . import cli_v12
from . import agent as agent_main


USER_COMMANDS = {
    "init": init_cmd,
    "models": models_cmd,
    "board": board_cmd,
    "serve": serve_cmd,
    "e2e": e2e_cmd,
}


def build_parser():
    parser = argparse.ArgumentParser(prog="lk", add_help=False)
    parser.add_argument("--help", "-h", action="store_true")
    parser.add_argument("--version", "-v", action="store_true")
    subparsers = parser.add_subparsers(dest="command", metavar="<command>")
    for name, module in USER_COMMANDS.items():
        sub = subparsers.add_parser(name, add_help=False)
        if hasattr(module, "register"):
            module.register(sub)
    cli_v12.register_subcommands(subparsers)
    subparsers.add_parser("version", add_help=False)
    subparsers.add_parser("help", add_help=False)
    subparsers.add_parser("upgrade", add_help=False)
    agent_parser = subparsers.add_parser("agent", add_help=False)
    if hasattr(agent_main, "register"):
        agent_main.register(agent_parser)
    return parser


def _do_upgrade(extra_args):
    """lk upgrade — find the venv that owns lk and pip install --upgrade louke there.

    Supported louke-level options (the rest are forwarded to pip as-is):
      --index URL        Specify PyPI source (e.g. https://test.pypi.org/simple/);
                         internally translated to pip's --index-url
      --pre              Allow pre-release / dev versions
      --dry-run          Show the pip command that would run, without executing it
    """
    import subprocess
    import os

    # 0. Parse louke-level options; forward the rest to pip unchanged
    parser = argparse.ArgumentParser(prog="lk upgrade", add_help=True)
    parser.add_argument(
        "--index",
        metavar="URL",
        help="PyPI source URL (e.g. https://test.pypi.org/simple/)",
    )
    parser.add_argument(
        "--pre", action="store_true", help="allow pre-release / dev versions"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="show the pip command that would run, without executing it",
    )
    opts, rest = parser.parse_known_args(extra_args)

    # 1. Find the venv pip. Two paths:
    #    - When invoked as the `lk` entry script, sys.argv[0] is /path/to/venv/bin/lk
    #      → dirname → .../venv/bin → pip there.
    #    - When invoked as `python -m louke upgrade`, sys.argv[0] is louke/__main__.py
    #      → that path is wrong. Fall back to sys.executable: it lives at
    #      <venv>/bin/python3 (or /usr/bin/python3), so dirname(sys.executable)/pip
    #      works for venv invocations and falls back to system pip otherwise.
    lk_bin = os.path.realpath(sys.argv[0])
    lk_bin_dir = os.path.dirname(lk_bin)
    if os.path.basename(lk_bin_dir) == "bin" and os.path.isfile(
        os.path.join(lk_bin_dir, "pip")
    ):
        venv_bin = lk_bin_dir
    else:
        venv_bin = os.path.dirname(os.path.realpath(sys.executable))
    venv_pip = os.path.join(venv_bin, "pip")
    venv_python = os.path.join(venv_bin, "python3")

    if not os.path.isfile(venv_pip):
        print(f"lk upgrade: cannot find venv pip at {venv_pip}", file=sys.stderr)
        print("hint: run install.sh again to recreate the venv", file=sys.stderr)
        return 1

    cmd = [venv_python, "-m", "pip", "install", "--upgrade", "louke"]
    if opts.index:
        cmd.extend(["--index-url", opts.index])
    if opts.pre:
        cmd.append("--pre")
    cmd.extend(rest)

    print(f"Running: {' '.join(cmd)}")
    if opts.dry_run:
        return 0
    result = subprocess.run(cmd)
    if result.returncode == 0:
        # Verify
        try:
            out = subprocess.check_output(
                [
                    venv_python,
                    "-c",
                    "from louke import __version__; print(__version__)",
                ],
                text=True,
            ).strip()
            print(f"✓ louke upgraded to {out}")
        except Exception:
            pass
    return result.returncode


def build_command_parser(module, prog):
    """Build a standalone parser for a user-facing command."""
    parser = argparse.ArgumentParser(prog=prog, add_help=True)
    if hasattr(module, "register"):
        module.register(parser)
    return parser


def main(argv=None):
    raw = list(argv if argv is not None else sys.argv[1:])

    if not raw or raw[0] in ("--version", "-v", "version"):
        print(f"lk {__version__}")
        return 0
    if raw[0] in ("--help", "-h", "help"):
        print_help_text()
        return 0
    if raw[0] == "upgrade":
        return _do_upgrade(raw[1:])
    if raw[0] == "agent":
        # Re-parse with help parser so agent subparser handles 'agent scout xxx'
        parser = build_parser()
        try:
            args = parser.parse_args(raw)
        except SystemExit as e:
            return e.code if isinstance(e.code, int) else 1
        return agent_main.run(args)
    if raw[0] == "discuss":
        return _cmd_discuss(raw[1:])
    if raw[0] in {"project", "gate", "workflow", "migrate"}:
        parser = build_parser()
        try:
            args = parser.parse_args(raw)
        except SystemExit as e:
            return e.code if isinstance(e.code, int) else 1
        raise SystemExit(cli_v12.dispatch(args))
    if raw[0] in USER_COMMANDS:
        module = USER_COMMANDS[raw[0]]
        parser = build_command_parser(module, f"lk {raw[0]}")
        try:
            args = parser.parse_args(raw[1:])
        except SystemExit as e:
            return e.code if isinstance(e.code, int) else 1
        try:
            return module.run(args) or 0
        except Exception as e:
            print(f"lk {raw[0]}: {e}", file=sys.stderr)
            return 1

    print(f"lk: unknown command '{raw[0]}'", file=sys.stderr)
    parser = build_parser()
    parser.print_help(sys.stderr)
    return 1


def _dispatch_agent(argv):
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as e:
        return e.code if isinstance(e.code, int) else 1
    return agent_main.run(args)


def print_help_text():
    print(f"lk {__version__} — louke CLI")
    print()
    print("User-facing commands:")
    print("  lk init <name|path>         Initialize/adopt louke project skeleton")
    print("  lk models list|doctor|bind|unbind  Manage abstract model bindings")
    print("  lk board opencode|status    Generate IDE agent boards")
    print(
        "  lk serve [--host H --port P] [--project-root PATH]  Start the web collaboration server"
    )
    print("  lk upgrade [--index URL] [--pre] [--dry-run]  Upgrade louke via pip")
    print("  lk version                  Print version")
    print("  lk help                     Print this help")
    print()
    print("v0.12 commands (B8):")
    print("  lk project list|show        Manage v0.12 projects")
    print("  lk gate approve|reject      Manage v0.12 gates")
    print("  lk workflow graph           Show workflow graph for a run")
    print("  lk migrate preview          Preview legacy workspace migration")
    print()
    print("Agent commands:")
    print("  lk agent <name> <cmd> [opts]")
    print("    scout      identity-check, foundation, invite-owner, commit-foundation")
    print("    sage       quote-check, commit-spec, create-issues, record-lock")
    print("    warden     foundation-check")
    print("    lex        verify-acceptance, verify-issue, verify-project, quote-check")
    print(
        "    archer     ci-scan, check-acs, commit-design, validate-test-plan, validate-arch"
    )
    print("    keeper     gate, regression")
    print("    judge      security-audit, quick-scan")
    print("    prism      review, test-patterns, security-quick-scan, code-quality")
    print("    devon      run-tests, commit-rgr")
    print("    shield     run-e2e, commit-e2e")
    print("    librarian  distill, lint, rebuild-index, compact, rewrite")
    print("    maestro    status, advance, regress, escalate")
    print()
    print("Inline discussion (v0.7-003):")
    print(
        "  lk discuss query --file <path> [--initiator <a>] [--blocker <a>] [--status <s>]"
    )
    print("  lk discuss start --file <path> --anchor-line <N> --speaker <a> <message>")
    print(
        "  lk discuss reply --file <path> --thread-id <id> --anchor-line <N> --anchor-text <t> --root-line <N> --root-text <t> --speaker <a> <message>"
    )
    print(
        "  lk discuss edit --file <path> --thread-id <id> --anchor-line <N> --anchor-text <t> --root-line <N> --root-text <t> --depth <N> --speaker <a> <new>"
    )
    print(
        "  lk discuss set-status --file <path> --thread-id <id> --anchor-line <N> --anchor-text <t> --root-line <N> --root-text <t> --status <resolved|reopen>"
    )
    print()
    print("Run lk <command> --help for detailed usage.")


def _build_discuss_parser() -> argparse.ArgumentParser:
    """FR-0030: lk discuss 5 subcommands (query/start/reply/edit/set-status)."""
    parser = argparse.ArgumentParser(prog="lk discuss", add_help=True)
    sub = parser.add_subparsers(
        dest="discuss_command", required=True, metavar="<command>"
    )

    # 1. query
    p_query = sub.add_parser(
        "query", help="list threads (with 5-tuple locating fields)"
    )
    p_query.add_argument("--file", required=True, help="path to spec.md")
    p_query.add_argument("--initiator", help="filter by initiator (e.g. Sage)")
    p_query.add_argument("--blocker", help="filter by blocker (e.g. Aaron)")
    p_query.add_argument(
        "--status", choices=["open", "resolved", "reopen"], help="filter by status"
    )
    p_query.add_argument(
        "--check-ready",
        action="store_true",
        help="output is_ready + ready_blockers (FR-0060 gate; mutually exclusive with --initiator/--blocker)",
    )

    # 2. start
    p_start = sub.add_parser(
        "start", help="create a new thread (inserted after anchor_line)"
    )
    p_start.add_argument("--file", required=True)
    p_start.add_argument(
        "--anchor-line",
        type=int,
        required=True,
        help="line number of the content being commented on",
    )
    p_start.add_argument("--speaker", required=True, help="initiator (e.g. Sage)")
    p_start.add_argument("message", help="comment content (single line)")

    # 3. reply
    p_reply = sub.add_parser("reply", help="append a reply to the end of a thread")
    p_reply.add_argument("--file", required=True)
    p_reply.add_argument("--thread-id", required=True, help="e.g. T-001")
    p_reply.add_argument("--anchor-line", type=int, required=True)
    p_reply.add_argument("--anchor-text", required=True)
    p_reply.add_argument("--root-line", type=int, required=True)
    p_reply.add_argument("--root-text", required=True)
    p_reply.add_argument("--speaker", required=True)
    p_reply.add_argument("message")

    # 4. edit
    p_edit = sub.add_parser(
        "edit", help="edit one of your own comments (original author only)"
    )
    p_edit.add_argument("--file", required=True)
    p_edit.add_argument("--thread-id", required=True)
    p_edit.add_argument("--anchor-line", type=int, required=True)
    p_edit.add_argument("--anchor-text", required=True)
    p_edit.add_argument("--root-line", type=int, required=True)
    p_edit.add_argument("--root-text", required=True)
    p_edit.add_argument(
        "--depth",
        type=int,
        required=True,
        help="nesting depth of the comment (1 = root comment)",
    )
    p_edit.add_argument(
        "--speaker",
        required=True,
        help="original comment author (validated = initiator)",
    )
    p_edit.add_argument("new_body", help="new comment content")

    # 5. set-status
    p_status = sub.add_parser(
        "set-status", help="change thread status (RESOLVED only by initiator)"
    )
    p_status.add_argument("--file", required=True)
    p_status.add_argument("--thread-id", required=True)
    p_status.add_argument("--anchor-line", type=int, required=True)
    p_status.add_argument("--anchor-text", required=True)
    p_status.add_argument("--root-line", type=int, required=True)
    p_status.add_argument("--root-text", required=True)
    p_status.add_argument("--status", required=True, choices=["resolved", "reopen"])
    p_status.add_argument(
        "--operator",
        required=True,
        help="operator (validated = initiator for RESOLVED to take effect)",
    )

    return parser


def _cmd_discuss(argv: list) -> int:
    """lk discuss 5 subcommand dispatcher."""
    from ._tools import discuss

    parser = _build_discuss_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as e:
        return e.code if isinstance(e.code, int) else 1

    try:
        if args.discuss_command == "query":
            result = discuss.DiscussParser().parse_file(Path(args.file))
            # FR-0060 AC-2: --check-ready outputs is_ready + ready_blockers
            if args.check_ready:
                import json as _json

                out = {
                    "is_ready": result.is_ready,
                    "ready_blockers": result.ready_blockers,
                }
                print(_json.dumps(out, ensure_ascii=False, indent=2))
                return 0 if result.is_ready else 1
            threads = result.threads
            # Apply filters
            if args.initiator:
                threads = [t for t in threads if t.initiator == args.initiator.lower()]
            if args.status:
                threads = [t for t in threads if t.status == args.status]
            if args.blocker:
                # QoderWork P2-2 three categories
                target = args.blocker.lower()
                open_threads = [t for t in threads if t.status == "open"]
                # unanswered: started by me + no replies
                unanswered = [
                    t
                    for t in open_threads
                    if t.initiator == target and t.reply_count == 0
                ]
                # unresolved: started by me + last layer is not me and not resolved
                # (here we only look at reply_count and status)
                # (simplified: reply_count > 0 but status != resolved)
                unresolved = [
                    t
                    for t in open_threads
                    if t.initiator == target and t.reply_count > 0
                ]
                # awaiting_my_reply: @mentioned me
                awaiting = [t for t in open_threads if target in t.mentioned_agents]
                threads = unanswered + unresolved + awaiting
            import json

            out = []
            for t in threads:
                out.append(
                    {
                        "thread_id": t.thread_id,
                        "initiator": t.initiator,
                        "status": t.status,
                        "last_speaker": t.last_speaker,
                        "reply_count": t.reply_count,
                        "snippet": t.snippet,
                        "mentioned_agents": t.mentioned_agents,
                        "total_lines": t.total_lines,
                        "anchor_line": t.anchor_line,
                        "anchor_text": t.anchor_text,
                        "root_line": t.root_line,
                        "root_text": t.root_text,
                    }
                )
            print(json.dumps(out, ensure_ascii=False, indent=2))
            return 0

        elif args.discuss_command == "start":
            p = discuss.DiscussParser()
            t = p.add_thread(
                Path(args.file),
                anchor_line=args.anchor_line,
                initiator=args.speaker,
                body=args.message,
            )
            print(f"created {t.thread_id} ({t.initiator}) at root_line={t.root_line}")
            return 0

        elif args.discuss_command == "reply":
            p = discuss.DiscussParser()
            p.add_reply(
                Path(args.file),
                thread_id=args.thread_id,
                body=args.message,
                speaker=args.speaker,
                anchor_line=args.anchor_line,
                anchor_text=args.anchor_text,
                root_line=args.root_line,
                root_text=args.root_text,
            )
            print(f"reply added to {args.thread_id}")
            return 0

        elif args.discuss_command == "edit":
            p = discuss.DiscussParser()
            p.edit_comment(
                Path(args.file),
                thread_id=args.thread_id,
                depth=args.depth,
                speaker=args.speaker,
                new_body=args.new_body,
                anchor_line=args.anchor_line,
                anchor_text=args.anchor_text,
                root_line=args.root_line,
                root_text=args.root_text,
            )
            print(f"comment at depth {args.depth} in {args.thread_id} edited")
            return 0

        elif args.discuss_command == "set-status":
            p = discuss.DiscussParser()
            p.set_status(
                Path(args.file),
                thread_id=args.thread_id,
                new_status=args.status,
                operator_speaker=args.operator,
                anchor_line=args.anchor_line,
                anchor_text=args.anchor_text,
                root_line=args.root_line,
                root_text=args.root_text,
            )
            print(f"{args.thread_id} status -> {args.status}")
            return 0

    except (FileNotFoundError, ValueError, PermissionError) as e:
        print(f"lk discuss: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
