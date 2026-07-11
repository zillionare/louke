"""e2e CLI: orchestrate the louke server + a mock OpenCode for tests/M-E2E.

Subcommands:
  louke e2e start --host HOST --port PORT --opencode mock   # spawn server + mock, write state
  louke e2e stop  --port PORT --cleanup-workspace            # kill server, clean tmp
"""
from __future__ import annotations

import argparse
import json
import os
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path


def _free_port(host: str = "127.0.0.1", port: int = 0) -> int:
    """Bind a transient socket to discover a free TCP port on ``host``.

    Args:
        host: bind host, defaults to 127.0.0.1.
        port: bind port, 0 lets the OS choose.

    Returns:
        The free port number chosen by the OS.
    """
    s = socket.socket()
    s.bind((host, port))
    p = s.getsockname()[1]
    s.close()
    return p


def cmd_e2e_start(args: argparse.Namespace) -> int:
    """Start louke server in background, with optional mock opencode.

    Args:
        args: argparse Namespace with ``host``, ``port``, ``opencode`` fields.

    Returns:
        0 on success. Writes a JSON state file to ``$LOUKE_E2E_STATE/e2e-state.json``
        containing pid, host, port and opencode backend for later ``e2e stop``.
    """
    state_dir = Path(os.environ.get("LOUKE_E2E_STATE", ".louke/server"))
    state_dir.mkdir(parents=True, exist_ok=True)
    state_file = state_dir / "e2e-state.json"

    host = args.host
    port = args.port or _free_port(host)
    opencode = args.opencode  # "mock" or "real"

    env = os.environ.copy()
    env["LOUKE_OPENCODE_BACKEND"] = opencode
    proc = subprocess.Popen(
        [sys.executable, "-m", "louke", "serve",
         "--host", host, "--port", str(port)],
        env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    state = {
        "host": host, "port": port, "opencode": opencode,
        "pid": proc.pid, "started_at": int(time.time()),
    }
    state_file.write_text(json.dumps(state, indent=2), encoding="utf-8")
    print(f"e2e start: pid={proc.pid} port={port} opencode={opencode}")
    return 0


def cmd_e2e_stop(args: argparse.Namespace) -> int:
    """Stop a previously e2e-launched server and optionally clean its workspace.

    Args:
        args: argparse Namespace with ``port`` and ``cleanup_workspace`` fields.

    Returns:
        0 on success (including no-op when no state exists).
    """
    state_dir = Path(os.environ.get("LOUKE_E2E_STATE", ".louke/server"))
    state_file = state_dir / "e2e-state.json"
    if not state_file.exists():
        print("e2e stop: no state, nothing to do")
        return 0
    state = json.loads(state_file.read_text(encoding="utf-8"))
    pid = state.get("pid")
    if pid:
        try:
            os.kill(pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
    if args.cleanup_workspace:
        import shutil
        # 仅清理本次 e2e 的 tmp workspace,不删 .louke
        ws = Path(state.get("workspace", ".louke/e2e-ws"))
        if ws.exists():
            shutil.rmtree(ws, ignore_errors=True)
    state_file.unlink(missing_ok=True)
    print(f"e2e stop: pid={pid} cleaned={args.cleanup_workspace}")
    return 0


def register(parser: argparse.ArgumentParser) -> None:
    """Register the ``e2e`` command on a top-level argparse subparser.

    Used by ``louke.__main__`` USER_COMMANDS dispatch.
    """
    register_subcommand(parser)


def register_subcommand(parser: argparse.ArgumentParser) -> None:
    """Register ``e2e start`` / ``e2e stop`` subcommands on ``parser``.

    Args:
        parser: the argparse parser (or subparser) to attach ``start`` and
            ``stop`` subparsers to.
    """
    sub = parser.add_subparsers(dest="e2e_action", required=True)

    p_start = sub.add_parser("start", help="start louke server + (mock) opencode")
    p_start.add_argument("--host", default="127.0.0.1")
    p_start.add_argument("--port", type=int, default=0)
    p_start.add_argument("--opencode", default="mock", choices=["mock", "real"])
    p_start.set_defaults(func=cmd_e2e_start)

    p_stop = sub.add_parser("stop", help="stop e2e-launched server")
    p_stop.add_argument("--port", type=int, default=0)
    p_stop.add_argument("--cleanup-workspace", action="store_true")
    p_stop.set_defaults(func=cmd_e2e_stop)


def run(args: argparse.Namespace) -> int:
    """Dispatch a parsed ``e2e`` Namespace to its ``func`` handler.

    Args:
        args: argparse Namespace produced by the e2e parser; must carry a
            ``func`` callable (set via ``set_defaults``).

    Returns:
        The handler's integer exit code, or 1 if no handler is bound.
    """
    func = getattr(args, "func", None)
    if func is None:
        print("lk e2e: missing subcommand (start|stop)", file=sys.stderr)
        return 1
    return func(args) or 0
