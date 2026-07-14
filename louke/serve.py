"""lk serve - run louke web server with v0.12 init-wizard and runtime selection.

Behavior:
- Resolve project root by walking up for `.louke/project/project.toml`.
- If project.toml is missing or its current_stage is unrecognized, auto-create a
  minimal v0.12 project.toml and start in setup-only mode.
- If project.toml exists but no first principal is initialized, start in
  setup-only mode.
- If everything is ready, resolve RuntimeSelector and fail-closed on any
  integrity/version/runtime error (never silently fall back to global).
- Always start uvicorn unless --dry-run is set (for tests).
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path
from typing import Any

from .runtime.runtime_selector import (
    GlobalModeError,
    IntegrityError,
    InvalidRuntimeError,
    RuntimeSelector,
    VersionMismatchError,
)

# Module-level seams so tests can patch without starting a real server.
# `uvicorn_run` is set lazily to the real uvicorn.run on first use; tests
# replace it with a no-op via monkeypatch.
uvicorn_run: Any = None


def create_app(project_root: str | Path | None = None, *, setup_only: bool = False):
    """Create the Starlette app, recording setup_only on app.state.

    This is a thin seam over louke.web.app.create_app so tests can patch it.
    """
    from .web.app import create_app as _create_app

    return _create_app(project_root, setup_only=setup_only)

_VALID_STAGES = frozenset(
    {
        "M-FOUND",
        "M-SPEC",
        "M-TESTPLAN",
        "M-ARCH",
        "M-LOCK",
        "M-DEV",
        "M-E2E",
        "M-BUGFIX",
        "M-SECURITY",
        "M-MILESTONE",
    }
)

_MINIMAL_PROJECT_TOML = """\
[project]
version = "0.12"
repo = "github.com/zillionare/louke"
project = "louke-v0.12"
project_id = ""
spec_id = "v0.12-001-programmatic-workflow-runtime"
release_branch = "main"

[meta]
created = "{today}"
tag = "unreleased"
current_stage = "M-FOUND"
security_audit = "disabled"
smoke_test_issue = "to be created after M-LOCK"
smoke_test_pr = "to be created after M-LOCK"
pre_commit = "installed (python + base)"
test_framework = "pytest"
acknowledged_orphan_releases = []
"""


def register(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument(
        "--project-root",
        default="",
        help="louke project root (default: search from current directory upward)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="resolve + dry-run; do not start uvicorn (for tests)",
    )
    parser.add_argument(
        "--opencode-backend",
        default="mock",
        choices=["mock", "real"],
        help="OpenCode adapter kind; default mock until real adapter lands",
    )


def run(args: argparse.Namespace) -> int:
    root = _resolve_project_root(args.project_root)
    project_toml = root / ".louke" / "project" / "project.toml"
    setup_url = f"http://{args.host}:{args.port}/setup"
    print(f"lk serve: opencode backend = {args.opencode_backend} (real adapter pending)")

    if not project_toml.exists() or not _current_stage_valid(project_toml):
        created = _ensure_minimal_project_toml(project_toml)
        if created:
            print(
                f"lk serve: setup-only mode; created minimal project.toml at {project_toml}. "
                f"Visit {setup_url} to complete init.",
                file=sys.stderr,
            )
        else:
            print(
                f"lk serve: setup-only mode; {project_toml} has unrecognized current_stage. "
                f"Visit {setup_url} to complete init.",
                file=sys.stderr,
            )
        return _start_or_dry_run(args, root, setup_only=True)

    principal_ok = _has_first_principal(root)
    if not principal_ok:
        print(
            f"lk serve: readiness incomplete; visiting {setup_url} completes init.",
            file=sys.stderr,
        )
        return _start_or_dry_run(args, root, setup_only=True)

    return _serve_ready(args, root)


def _serve_ready(
    args: argparse.Namespace, root: Path
) -> int:
    declared_version = "0.12.0"
    selector = RuntimeSelector(
        project_root=str(root), declared_version=declared_version
    )
    try:
        identity = selector.resolve()
    except (IntegrityError, VersionMismatchError, InvalidRuntimeError, GlobalModeError) as exc:
        print(
            f"lk serve: runtime selection failed: {exc}. "
            f"Inspect .louke/project/project.toml (version/declared) and the local "
            f"runtime under {root}/.louke/runtime. No global fallback.",
            file=sys.stderr,
        )
        return 1
    except Exception as exc:
        print(f"lk serve: unexpected error resolving runtime: {exc}", file=sys.stderr)
        return 1

    if args.opencode_backend == "real":
        # B4 wires the real OpenCode adapter; until then fail-closed so no
        # semantic task is dispatched against a non-existent backend.
        print(
            "lk serve: opencode backend 'real' is not yet available; "
            "use --opencode-backend=mock or wait for the B4 adapter. "
            "No global fallback.",
            file=sys.stderr,
        )
        return 1

    print(
        f"lk serve: runtime = {identity.mode.name}, mode=local, "
        f'version="{identity.version}"'
    )
    print(f"lk serve: effective root = {identity.effective_root}")
    print(f"lk serve: listening on http://{args.host}:{args.port}")
    if args.dry_run:
        return 0
    return _run_uvicorn(args, root, setup_only=False)


def _start_or_dry_run(
    args: argparse.Namespace, root: Path, *, setup_only: bool
) -> int:
    if args.dry_run:
        create_app(root, setup_only=setup_only)
        return 0
    return _run_uvicorn(args, root, setup_only=setup_only)


def _run_uvicorn(
    args: argparse.Namespace, root: Path, *, setup_only: bool
) -> int:
    runner = uvicorn_run
    if runner is None:
        try:
            import uvicorn

            runner = uvicorn.run
        except ImportError as exc:
            print(f"lk serve: missing runtime dependency uvicorn ({exc})", file=sys.stderr)
            return 1
    app = create_app(root, setup_only=setup_only)
    runner(app, host=args.host, port=args.port, log_level="info")
    return 0


def _resolve_project_root(explicit: str) -> Path:
    if explicit:
        return Path(explicit).expanduser().resolve()
    discovered = _find_project_root(Path.cwd())
    if discovered is not None:
        return discovered
    return Path.cwd().resolve()


def _find_project_root(start: Path) -> Path | None:
    current = start.resolve()
    for candidate in [current, *current.parents]:
        project_toml = candidate / ".louke" / "project" / "project.toml"
        if project_toml.exists():
            return candidate
    return None


def _current_stage_valid(project_toml: Path) -> bool:
    try:
        from ._common import _toml_load

        data = _toml_load(project_toml)
    except Exception:
        return False
    stage = str((data.get("meta") or {}).get("current_stage") or "")
    return stage in _VALID_STAGES


def _ensure_minimal_project_toml(project_toml: Path) -> bool:
    """Create a minimal v0.12 project.toml if it does not exist.

    Returns True if a new file was created, False if it already existed
    (but had an unrecognized current_stage).
    """
    if project_toml.exists():
        return False
    project_toml.parent.mkdir(parents=True, exist_ok=True)
    project_toml.write_text(
        _MINIMAL_PROJECT_TOML.format(today=date.today().isoformat()),
        encoding="utf-8",
    )
    return True


def _has_first_principal(root: Path) -> bool:
    """Return whether the workspace has a persisted first human principal.

    The principal is persisted as a user in `.louke/web-users.json`, which is
    the same store the Web auth layer reads. This keeps the readiness signal
    observable on disk rather than tied to an in-memory wizard instance.
    """
    try:
        from .web.store import ProjectStore

        store = ProjectStore(root)
        return bool(store.list_users())
    except Exception:
        return False
