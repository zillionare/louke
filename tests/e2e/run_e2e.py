"""The single v0.13.1 host runner for integration and E2E profiles."""

from __future__ import annotations

import argparse
import importlib.metadata
import os
from pathlib import Path
import subprocess
import sys


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _expected_python(root: Path) -> Path:
    candidates = (
        root / ".venv" / "bin" / "python",
        root / ".venv" / "Scripts" / "python.exe",
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    return candidates[0].resolve()


def _inside(path: Path, directory: Path) -> bool:
    try:
        path.relative_to(directory)
    except ValueError:
        return False
    return True


def _verify_host_identity(root: Path) -> str:
    expected_python = _expected_python(root)
    actual_python = Path(sys.executable).resolve()
    if actual_python != expected_python:
        raise RuntimeError(
            f"runner Python mismatch: expected {expected_python}, got {actual_python}"
        )
    import louke

    louke_file = Path(louke.__file__).resolve()
    venv_root = expected_python.parent.parent
    if not _inside(louke_file, venv_root):
        raise RuntimeError(
            f"runner louke is outside project venv: expected under {venv_root}, got {louke_file}"
        )
    return importlib.metadata.version("louke")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="run-project-venv")
    subparsers = parser.add_subparsers(dest="command", required=True)
    integration = subparsers.add_parser("integration")
    integration.add_argument("pytest_args", nargs=argparse.REMAINDER)
    e2e = subparsers.add_parser("e2e")
    e2e.add_argument("--profile", choices=("install", "chromium", "all"), required=True)
    e2e.add_argument("--runtime", choices=("local", "global", "both"), required=True)
    e2e.add_argument("pytest_args", nargs=argparse.REMAINDER)
    return parser


def _run_pytest(root: Path, paths: list[str], extra: list[str]) -> int:
    command = [sys.executable, "-m", "pytest", *paths, *extra]
    environment = os.environ.copy()
    environment["LOUKE_PROJECT_RUNNER_PYTHON"] = str(Path(sys.executable).resolve())
    return subprocess.run(command, cwd=root, env=environment).returncode


def main(argv: list[str] | None = None) -> int:
    root = _repo_root()
    try:
        version = _verify_host_identity(root)
    except (ImportError, RuntimeError, importlib.metadata.PackageNotFoundError) as exc:
        print(f"run-project-venv: {exc}", file=sys.stderr)
        return 127
    args = _parser().parse_args(argv)
    print(f"runner={Path(sys.executable).resolve()} louke_version={version}")
    if args.command == "integration":
        return _run_pytest(
            root, ["tests/integration", "tests/ground_truth"], args.pytest_args
        )

    profiles = ("install", "chromium") if args.profile == "all" else (args.profile,)
    runtimes = ("local", "global") if args.runtime == "both" else (args.runtime,)
    for profile in profiles:
        for runtime in runtimes:
            print(f"profile={profile} runtime={runtime}")
            os.environ["LOUKE_E2E_PROFILE"] = profile
            os.environ["LOUKE_E2E_RUNTIME"] = runtime
            result = _run_pytest(root, ["tests/e2e"], ["-m", "e2e", *args.pytest_args])
            if result:
                return result
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
