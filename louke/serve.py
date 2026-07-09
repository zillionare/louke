"""lk serve - run louke web server."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ._common import git_root


def register(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument(
        "--project-root",
        default="",
        help="louke project root (default: current git root, else cwd)",
    )


def run(args: argparse.Namespace) -> int:
    root = _resolve_project_root(args.project_root)
    project_toml = root / ".louke" / "project" / "project.toml"
    if not project_toml.exists():
        print(
            f"lk serve: {project_toml} not found; run inside a louke project or pass --project-root",
            file=sys.stderr,
        )
        return 1

    try:
        import uvicorn
    except ImportError as exc:
        print(f"lk serve: missing runtime dependency uvicorn ({exc})", file=sys.stderr)
        return 1

    from .web.app import create_app

    app = create_app(root)
    spec_id = app.state.store.spec_id
    print(f"lk serve listening on http://{args.host}:{args.port}")
    print(f"project root: {root}")
    print(f"spec id: {spec_id}")
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
    return 0


def _resolve_project_root(explicit: str) -> Path:
    if explicit:
        return Path(explicit).expanduser().resolve()
    root = git_root()
    if root is not None:
        return Path(root)
    return Path.cwd().resolve()
