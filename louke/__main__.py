"""lk CLI entry point.

Usage:
    lk <command> [options]               # user-facing commands
    lk agent <name> <subcommand> [options]  # agent commands

User-facing commands:
    lk init <name|path>         Initialize/adopt louke project skeleton
    lk models list|doctor|bind|unbind  Manage abstract model bindings
    lk board opencode|status    Generate IDE agent boards
    lk serve [--host H --port P] Start the web collaboration server
    lk install                  Install a project-local runtime
    lk upgrade                  Upgrade louke via pip
    lk version                  Print version (also: lk --version, lk -v)
    lk help                     Print help (also: lk --help, lk -h)

Agent commands:
    lk agent maestro status
    lk agent sage quote-check --spec v0.1-001-init
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
import os
import sys
import tomllib
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
    subparsers.add_parser("install", add_help=False)
    subparsers.add_parser("upgrade", add_help=False)
    agent_parser = subparsers.add_parser("agent", add_help=False)
    if hasattr(agent_main, "register"):
        agent_main.register(agent_parser)
    return parser


def _do_upgrade(extra_args):
    """Upgrade one or both v0.13 runtimes and refresh local harness resources."""
    import subprocess

    parser = argparse.ArgumentParser(prog="lk upgrade", add_help=True)
    targets = parser.add_mutually_exclusive_group()
    targets.add_argument("--local", dest="target", action="store_const", const="local")
    targets.add_argument(
        "--global", dest="target", action="store_const", const="global"
    )
    targets.add_argument("--both", dest="target", action="store_const", const="both")
    parser.set_defaults(target="local")
    parser.add_argument("--index", metavar="URL", help="pip index URL")
    parser.add_argument("--version", metavar="VERSION", help="louke package version")
    parser.add_argument("--pre", action="store_true", help="allow pre-releases")
    parser.add_argument("--dry-run", action="store_true")
    try:
        opts, rest = parser.parse_known_args(extra_args)
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) else 1

    runtimes: list[tuple[str, Path]] = []
    if opts.target in {"local", "both"}:
        local = _runtime_python("local")
        if local is None:
            print(
                f"lk upgrade: local runtime not found at {Path.cwd() / '.venv'}; run lk install first",
                file=sys.stderr,
            )
            return 1
        runtimes.append(("local", local))
    if opts.target in {"global", "both"}:
        global_python = _runtime_python("global")
        if global_python is None:
            print(
                f"lk upgrade: global runtime not found at {Path.home() / '.louke' / 'venv'}; run install.sh / install.bat first",
                file=sys.stderr,
            )
            return 1
        runtimes.append(("global", global_python))

    package = "louke" if not opts.version else f"louke=={opts.version}"
    for name, python in runtimes:
        cmd = [str(python), "-m", "pip", "install", "--upgrade", package]
        if opts.index:
            cmd.extend(["--index-url", opts.index])
        if opts.pre:
            cmd.append("--pre")
        cmd.extend(rest)
        print(f"Running ({name}): {' '.join(cmd)}")
        if opts.dry_run:
            _print_board_dry_run(name)
            continue
        result = subprocess.run(cmd, text=True, capture_output=True)
        stdout = getattr(result, "stdout", "") or ""
        stderr = getattr(result, "stderr", "") or ""
        if stdout:
            print(stdout, end="")
        if stderr:
            print(stderr, end="", file=sys.stderr)
        if result.returncode != 0:
            print(f"lk upgrade: {name} pip upgrade failed", file=sys.stderr)
            return result.returncode
        installed_version = _runtime_package_version(python)
        if installed_version is None:
            print(
                f"lk upgrade: unable to verify the installed {name} runtime version",
                file=sys.stderr,
            )
            return 1
        if opts.version and installed_version != opts.version:
            print(
                f"lk upgrade: {name} runtime version mismatch: "
                f"requested {opts.version}, installed {installed_version}",
                file=sys.stderr,
            )
            return 1
        changed = _pip_changed(stdout, stderr)
        if name == "local" and _project_harness_args(Path.cwd()) and changed:
            board_rc = _run_board(Path.cwd(), python)
            if board_rc != 0:
                return board_rc
        elif name == "local":
            print("lk upgrade: local harness not configured; board skipped")
        print(f"✓ louke {installed_version} ({name})")
    return 0


def _runtime_python(kind: str, root: Path | None = None) -> Path | None:
    """Return the executable for a strict-CWD local or user-global runtime."""
    if kind == "local":
        venv = (root or Path.cwd()) / ".venv"
    elif kind == "global":
        venv = Path.home() / ".louke" / "venv"
    else:  # pragma: no cover - callers use the closed target set
        raise ValueError(f"unknown runtime kind: {kind}")
    candidates = (
        venv / "bin" / "python",
        venv / "bin" / "python3",
        venv / "Scripts" / "python.exe",
        venv / "Scripts" / "python",
    )
    return next((candidate for candidate in candidates if candidate.is_file()), None)


def _runtime_package_version(python: Path) -> str | None:
    """Read the package version from the target runtime after pip succeeds."""
    import subprocess

    result = subprocess.run(
        [
            str(python),
            "-c",
            "import importlib.metadata; print(importlib.metadata.version('louke'))",
        ],
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        return None
    version = (result.stdout or "").strip()
    return version or None


def _project_harness_args(root: Path) -> list[str]:
    """Return board arguments declared by the project harness manifest.

    v0.13.1 deliberately does not infer a harness from generated files such as
    ``opencode.json`` or ``.opencode``.  The project contract is the explicit
    ``[harness].board_args`` string array in project.toml; a missing table is a
    documented no-op.
    """
    manifest = root / ".louke" / "project" / "project.toml"
    if not manifest.is_file():
        return []
    try:
        with manifest.open("rb") as stream:
            data = tomllib.load(stream)
    except (OSError, tomllib.TOMLDecodeError):
        return []
    harness = data.get("harness")
    if not isinstance(harness, dict):
        return []
    board_args = harness.get("board_args")
    if not isinstance(board_args, list) or not all(
        isinstance(argument, str) for argument in board_args
    ):
        return []
    return board_args


def _pip_changed(stdout: str, stderr: str) -> bool:
    """Detect pip's no-op result so repeated upgrades do not re-board."""
    output = f"{stdout}\n{stderr}".lower()
    return "already satisfied" not in output


def _print_board_dry_run(name: str) -> None:
    if name == "local" and _project_harness_args(Path.cwd()):
        print("Running (local board): lk board opencode")
    elif name == "local":
        print("Skipping (local board): no harness configured")


def _run_board(root: Path, python: Path) -> int:
    """Refresh the project's configured harness after a successful local pip run."""
    import subprocess

    board_args = _project_harness_args(root)
    if not board_args:
        return 0
    cmd = [str(python), "-m", "louke", "board", *board_args]
    print(f"Running (local board): {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=str(root), text=True)
    if result.returncode != 0:
        print("lk upgrade: board refresh failed", file=sys.stderr)
    return result.returncode


def _do_install(extra_args):
    """Create a project-local ``.venv`` from the global runtime."""
    import subprocess

    parser = argparse.ArgumentParser(prog="lk install")
    parser.add_argument("--index", metavar="URL")
    parser.add_argument("--version", metavar="VERSION")
    parser.add_argument("--dry-run", action="store_true")
    try:
        opts = parser.parse_args(extra_args)
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) else 1
    root = Path.cwd()
    local_venv = root / ".venv"
    if local_venv.exists():
        print(
            f"lk install: local runtime already exists at {local_venv}; run lk upgrade",
            file=sys.stderr,
        )
        return 1
    package = "louke" if not opts.version else f"louke=={opts.version}"
    create = [sys.executable, "-m", "venv", str(local_venv)]
    print(f"Running: {' '.join(create)}")
    if opts.dry_run:
        return 0
    result = subprocess.run(create)
    if result.returncode != 0:
        return result.returncode
    python = _runtime_python("local", root)
    if python is None:
        print(f"lk install: local Python not found under {local_venv}", file=sys.stderr)
        return 1
    pip = [str(python), "-m", "pip", "install", "--upgrade", package]
    if opts.index:
        pip.extend(["--index-url", opts.index])
    print(f"Running: {' '.join(pip)}")
    return subprocess.run(pip, cwd=str(root)).returncode


def build_command_parser(module, prog):
    """Build a standalone parser for a user-facing command."""
    parser = argparse.ArgumentParser(prog=prog, add_help=True)
    if hasattr(module, "register"):
        module.register(parser)
    return parser


def main(argv=None):
    raw = list(argv if argv is not None else sys.argv[1:])

    if not raw or raw[0] in ("--version", "-v", "version"):
        print(f"lk {__version__} ({_runtime_mode()})")
        return 0
    if raw[0] in ("--help", "-h", "help"):
        print_help_text()
        return 0
    if raw[0] == "install":
        return _do_install(raw[1:])
    if raw[0] == "upgrade":
        return _do_upgrade(raw[1:])
    if raw[0] == "release":
        return _cmd_release(raw[1:])
    if raw[0] == "agent":
        # Re-parse with the help parser so agent subparsers handle agent commands.
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


def _runtime_mode() -> str:
    """Identify the runtime executing this Python process.

    The v0.13 shim may set ``LOUKE_RUNTIME_MODE`` explicitly. Direct calls
    through a project ``.venv`` are also recognized; otherwise the process is
    treated as global. This is presentation only and does not perform runtime
    selection or search parent directories.
    """
    explicit = os.environ.get("LOUKE_RUNTIME_MODE", "").strip().lower()
    if explicit in {"local", "global"}:
        return explicit
    executable = Path(sys.executable).resolve()
    prefix = Path(sys.prefix).resolve()
    parts = set(executable.parts) | set(prefix.parts)
    if prefix.name == ".venv" or ".venv" in parts:
        return "local"
    if ".louke" in parts and "venv" in parts:
        return "global"
    return "global"


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
    print("  lk install                  Install a project-local runtime")
    print(
        "  lk upgrade [--local|--global|--both] [--index URL] [--version VERSION] [--pre] [--dry-run]  Upgrade louke"
    )
    print(
        "  lk release verify --tag TAG --artifact-version VERSION  Verify release identity"
    )
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
    print("    scout      deprecated compatibility onboarding adapter")
    print(
        "    sage       quote-check, commit-spec, create-issues, record-lock (legacy adapters)"
    )
    print("    warden     deprecated compatibility foundation adapter")
    print("    lex        verify-acceptance, verify-issue, verify-project, quote-check")
    print(
        "    archer     ci-scan, check-acs, commit-design, validate-test-plan, validate-arch"
    )
    print("    keeper     deprecated compatibility quality adapter")
    print("    judge      security-audit, quick-scan")
    print(
        "    prism      review, review-testplan, review-arch, test-patterns, "
        "security-quick-scan, code-quality"
    )
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


def _cmd_release(argv: list[str]) -> int:
    """Run release-related public commands and return a process exit code."""
    from dataclasses import asdict
    import json

    from .release_identity import verify_release_identity

    parser = argparse.ArgumentParser(prog="lk release", add_help=True)
    subparsers = parser.add_subparsers(dest="release_command", required=True)
    verify = subparsers.add_parser("verify")
    verify.add_argument("--tag")
    verify.add_argument("--artifact-version")
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else 1
    if args.release_command != "verify":
        return 1
    result = verify_release_identity(args.tag, args.artifact_version)
    print(json.dumps(asdict(result), ensure_ascii=False, sort_keys=True))
    return 0 if result.passed else 1


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
                # Both OPEN and REOPEN are actionable blocker states.  A
                # reopened thread must not disappear from blocker queries.
                open_threads = [t for t in threads if t.status in ("open", "reopen")]
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
