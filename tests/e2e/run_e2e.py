"""Single project-venv bootstrap for integration and product E2E.

The v0.14-001 runner keeps the historical integration discovery and the
delivered install/Chromium e2e profiles.  The v0.14-002 design-contracts
profile is intentionally not exposed here because its execution lifecycle is
not wired in this release; an undelivered profile must not enter the stand-in
DAG.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import tomllib


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _expected_python(root: Path) -> Path:
    candidates = (
        root / ".venv" / "bin" / "python",
        root / ".venv" / "Scripts" / "python.exe",
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate.absolute()
    return candidates[0].absolute()


def _inside(path: Path, directory: Path) -> bool:
    try:
        path.relative_to(directory)
    except ValueError:
        return False
    return True


def _declared_version(root: Path) -> str:
    with (root / "pyproject.toml").open("rb") as stream:
        return str(tomllib.load(stream)["project"]["version"])


def _git_revision(root: Path) -> str:
    """Return the exact source revision used for the product wheel."""
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True
    )
    if result.returncode:
        raise RuntimeError(f"cannot resolve source revision: {result.stderr.strip()}")
    return result.stdout.strip()


def _assert_clean_source(root: Path) -> None:
    """Reject a wheel build that cannot be attributed to one Git revision."""
    result = subprocess.run(
        ["git", "diff", "--quiet", "HEAD", "--"],
        cwd=root,
        capture_output=True,
        text=True,
    )
    staged = subprocess.run(
        ["git", "diff", "--cached", "--quiet", "HEAD", "--"],
        cwd=root,
        capture_output=True,
        text=True,
    )
    untracked = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=root,
        capture_output=True,
        text=True,
    )
    if result.returncode or staged.returncode or untracked.stdout.strip():
        raise RuntimeError("source tree is dirty; cannot build a same-SHA wheel")


def _verify_host_identity(root: Path) -> str:
    expected_python = _expected_python(root)
    actual_python = Path(sys.executable).absolute()
    if actual_python != expected_python:
        raise RuntimeError(
            f"runner Python mismatch: expected {expected_python}, got {actual_python}"
        )
    import louke

    louke_file = Path(louke.__file__).resolve()
    # On uv-managed macOS interpreters, `.venv/bin/python` resolves to the
    # shared base interpreter.  Package ownership is still determined by the
    # project venv directory, not by that resolved interpreter's parent.
    venv_root = (root / ".venv").absolute()
    if not _inside(louke_file, venv_root):
        raise RuntimeError(
            f"runner louke is outside project venv: expected under {venv_root}, got {louke_file}"
        )
    installed = importlib.metadata.version("louke")
    declared = _declared_version(root)
    if installed != declared:
        raise RuntimeError(
            f"runner metadata mismatch: pyproject declares {declared}, installed {installed}"
        )
    return installed


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="run-project-venv")
    subparsers = parser.add_subparsers(dest="command", required=True)
    integration = subparsers.add_parser("integration")
    integration.add_argument("pytest_args", nargs=argparse.REMAINDER)
    e2e = subparsers.add_parser("e2e")
    e2e.add_argument(
        "--profile",
        choices=("install", "chromium", "v014", "all"),
        required=True,
    )
    e2e.add_argument("--runtime", choices=("local", "global", "both"), required=True)
    e2e.add_argument("pytest_args", nargs=argparse.REMAINDER)
    return parser


def _run(command: list[str], *, cwd: Path, env: dict[str, str]) -> None:
    completed = subprocess.run(command, cwd=cwd, env=env, text=True)
    if completed.returncode:
        raise RuntimeError(
            f"child failed ({completed.returncode}): {' '.join(command)}"
        )


def _run_pytest(
    root: Path, paths: list[str], extra: list[str], env: dict[str, str]
) -> int:
    command = [sys.executable, "-m", "pytest", *paths, *extra]
    environment = env.copy()
    environment["LOUKE_PROJECT_RUNNER_PYTHON"] = str(Path(sys.executable).absolute())
    return subprocess.run(command, cwd=root, env=environment).returncode


def _resolve_playwright_browsers_path(
    environment: dict[str, str], *, executable_path: Path | None = None
) -> Path:
    """Resolve and export the canonical Playwright browser cache directory.

    Args:
        environment: Child-process environment to update with the explicit
            ``PLAYWRIGHT_BROWSERS_PATH`` value.
        executable_path: Optional already discovered Chromium executable,
            provided by unit tests or a caller that owns discovery.

    Returns:
        The existing Playwright browser cache directory.

    Raises:
        RuntimeError: If the configured cache or Chromium executable is absent
            or cannot be mapped to a Playwright cache root.
    """
    configured = environment.get("PLAYWRIGHT_BROWSERS_PATH", "").strip()
    if configured:
        cache = Path(configured).expanduser().resolve()
        if not cache.is_dir():
            raise RuntimeError(f"PLAYWRIGHT_BROWSERS_PATH does not exist: {cache}")
        environment["PLAYWRIGHT_BROWSERS_PATH"] = str(cache)
        return cache
    if executable_path is None:
        try:
            from playwright.sync_api import sync_playwright

            with sync_playwright() as playwright:
                executable_path = Path(playwright.chromium.executable_path)
        except Exception as exc:
            raise RuntimeError(
                "Chromium discovery failed; set PLAYWRIGHT_BROWSERS_PATH "
                "to an installed Playwright browser cache"
            ) from exc
    executable = executable_path.expanduser().resolve()
    if not executable.is_file():
        raise RuntimeError(f"Chromium executable does not exist: {executable}")
    version_directory = next(
        (
            parent
            for parent in executable.parents
            if parent.name.startswith("chromium-")
        ),
        None,
    )
    if version_directory is None or not version_directory.parent.is_dir():
        raise RuntimeError(
            f"Chromium executable is outside a Playwright cache: {executable}"
        )
    cache = version_directory.parent
    environment["PLAYWRIGHT_BROWSERS_PATH"] = str(cache)
    return cache


def _require_chromium(environment: dict[str, str]) -> None:
    """Fail the required browser profile when Chromium cannot launch."""
    _resolve_playwright_browsers_path(environment)
    probe = subprocess.run(
        [
            sys.executable,
            "-c",
            "from pathlib import Path; "
            "from playwright.sync_api import sync_playwright; "
            "p=sync_playwright().start(); "
            "path=Path(p.chromium.executable_path); "
            "p.stop(); "
            "raise SystemExit(0 if path.is_file() else 1)",
        ],
        cwd=_repo_root(),
        env=environment,
        capture_output=True,
        text=True,
    )
    if probe.returncode:
        detail = probe.stderr.strip() or probe.stdout.strip()
        raise RuntimeError(f"Chromium is unavailable for required E2E: {detail}")


def _prepare_wheelhouse(root: Path, temporary_root: Path, version: str) -> Path:
    _assert_clean_source(root)
    source_sha = _git_revision(root)
    configured = os.environ.get("LOUKE_E2E_WHEELHOUSE", "").strip()
    if configured:
        wheelhouse = Path(configured).resolve()
        wheels = list(wheelhouse.glob(f"louke-{version}-*.whl"))
        if not wheels:
            raise RuntimeError(f"wheelhouse has no louke {version} wheel: {wheelhouse}")
        manifest_path = wheelhouse / "manifest.json"
        if not manifest_path.is_file():
            raise RuntimeError(f"wheelhouse lacks same-SHA manifest: {manifest_path}")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("source_sha") != source_sha:
            raise RuntimeError(
                f"wheelhouse source SHA mismatch: expected {source_sha}, got {manifest.get('source_sha')}"
            )
        wheel = _wheel_path(wheelhouse, version)
        if manifest.get("wheel") != wheel.name:
            raise RuntimeError(
                "wheelhouse manifest does not identify the selected wheel"
            )
        if (
            manifest.get("wheel_sha256")
            != hashlib.sha256(wheel.read_bytes()).hexdigest()
        ):
            raise RuntimeError("wheelhouse wheel digest does not match its manifest")
        return wheelhouse

    artifacts = temporary_root / "artifacts"
    wheelhouse = temporary_root / "wheelhouse"
    artifacts.mkdir()
    wheelhouse.mkdir()
    _run(
        [sys.executable, "-m", "build", "--wheel", "--outdir", str(artifacts)],
        cwd=root,
        env=os.environ.copy(),
    )
    wheels = list(artifacts.glob(f"louke-{version}-*.whl"))
    if len(wheels) != 1:
        raise RuntimeError(f"expected one louke {version} wheel, found {wheels}")
    _run(
        [
            sys.executable,
            "-m",
            "pip",
            "download",
            "--dest",
            str(wheelhouse),
            str(wheels[0]),
            "pip",
        ],
        cwd=root,
        env=os.environ.copy(),
    )
    wheel_digest = hashlib.sha256(wheels[0].read_bytes()).hexdigest()
    manifest = {
        "version": version,
        "source_sha": source_sha,
        "runner_python": str(Path(sys.executable).absolute()),
        "wheel": wheels[0].name,
        "wheel_sha256": wheel_digest,
        "editable": False,
    }
    (wheelhouse / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return wheelhouse


def _fixture_python_bin(case_root: Path) -> Path:
    fixture_bin = case_root / "fixture-bin"
    fixture_bin.mkdir()
    runner = Path(sys.executable).absolute()
    if os.name == "nt":
        return runner.parent
    for name in ("python3", f"python3.{sys.version_info.minor}"):
        (fixture_bin / name).symlink_to(runner)
    return fixture_bin


def _base_case_env(case_root: Path, wheelhouse: Path) -> dict[str, str]:
    case_home = case_root / "user-home"
    case_home.mkdir()
    fixture_bin = _fixture_python_bin(case_root)
    environment = os.environ.copy()
    environment["HOME"] = str(case_home)
    environment["USERPROFILE"] = str(case_home)
    environment["PIP_NO_INDEX"] = "1"
    environment["PIP_FIND_LINKS"] = str(wheelhouse)
    system_paths = [
        path for path in os.environ.get("PATH", "").split(os.pathsep) if path
    ]
    if os.name == "nt":
        keep = [str(fixture_bin), *system_paths]
    else:
        keep = [str(fixture_bin), "/usr/bin", "/bin", "/usr/sbin", "/sbin"]
    environment["PATH"] = os.pathsep.join(dict.fromkeys(keep))
    environment.pop("PYTHONPATH", None)
    return environment


def _install_case(
    root: Path, case_root: Path, wheelhouse: Path, version: str, runtime: str
) -> tuple[Path, Path, dict[str, str]]:
    environment = _base_case_env(case_root, wheelhouse)
    wheel = _wheel_path(wheelhouse, version)
    seed = case_root / ("workspace" if runtime == "local" else "seed")
    seed.mkdir()
    if os.name == "nt":
        command = [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(root / "install.ps1"),
            "-Version",
            version,
            "-Wheel",
            str(wheel),
        ]
    else:
        command = [
            "bash",
            str(root / "install.sh"),
            "--version",
            version,
            "--wheel",
            str(wheel),
        ]
    _run(command, cwd=seed, env=environment)

    case_home = Path(environment["HOME"])
    if runtime == "local":
        cwd = seed
        product_python = (
            cwd / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        )
    else:
        cwd = case_root / "workspace"
        cwd.mkdir()
        product_python = (
            case_home
            / ".louke"
            / "venv"
            / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        )
    shim_dir = case_home / (".louke/bin" if os.name == "nt" else ".local/bin")
    environment["PATH"] = str(shim_dir) + os.pathsep + environment["PATH"]
    environment["LOUKE_RUNTIME_MODE"] = runtime
    environment["LOUKE_E2E_RUNTIME"] = runtime
    environment["LOUKE_E2E_PRODUCT_PYTHON"] = str(product_python.absolute())
    environment["LOUKE_E2E_SERVER_PYTHON"] = str(product_python.absolute())
    environment["LOUKE_E2E_CASE_CWD"] = str(cwd.resolve())
    environment["LOUKE_E2E_CASE_HOME"] = str(case_home.resolve())
    environment["LOUKE_E2E_WHEEL_VERSION"] = version
    environment["LOUKE_E2E_SOURCE_SHA"] = _git_revision(root)
    wheel_manifest = json.loads(
        (wheelhouse / "manifest.json").read_text(encoding="utf-8")
    )
    environment["LOUKE_E2E_WHEEL_SHA256"] = str(wheel_manifest["wheel_sha256"])
    environment["LOUKE_E2E_SERVER_COMMAND"] = json.dumps(
        _server_command(product_python, cwd), separators=(",", ":")
    )
    environment["LOUKE_E2E_SHIM"] = str(
        (shim_dir / ("lk.cmd" if os.name == "nt" else "lk")).absolute()
    )
    _verify_product_identity(product_python, version, root, environment)
    return cwd, product_python, environment


def _verify_product_identity(
    product_python: Path, version: str, root: Path, environment: dict[str, str]
) -> None:
    if product_python.absolute() == Path(sys.executable).absolute():
        raise RuntimeError("product Python must differ from project runner Python")
    if _inside(product_python.absolute(), (root / ".venv").absolute()):
        raise RuntimeError("product Python must not be inside the repository .venv")
    # Run the probe from the case workspace (a temp dir with no louke/ source
    # tree).  ``python -c`` puts cwd (``''``) on sys.path[0]; if the probe
    # inherits the repo root cwd, ``import louke`` resolves to the checkout's
    # source package instead of the product venv's installed wheel, causing a
    # false "product louke is outside product venv" failure.
    probe_cwd = Path(environment["LOUKE_E2E_CASE_CWD"])
    probe = subprocess.run(
        [
            str(product_python),
            "-c",
            "import importlib.metadata,json,louke,sys; "
            "print(json.dumps({'python':sys.executable,'louke':louke.__file__,"
            "'version':importlib.metadata.version('louke')}))",
        ],
        cwd=probe_cwd,
        env=environment,
        text=True,
        capture_output=True,
    )
    if probe.returncode:
        raise RuntimeError(f"product identity probe failed: {probe.stderr.strip()}")
    identity = json.loads(probe.stdout)
    resolved_product_python = product_python.resolve()
    product_root = product_python.parent.parent.resolve()
    if Path(identity["python"]).resolve() != resolved_product_python:
        raise RuntimeError(f"product executable mismatch: {identity}")
    if not _inside(Path(identity["louke"]).resolve(), product_root):
        raise RuntimeError(f"product louke is outside product venv: {identity}")
    if identity["version"] != version:
        raise RuntimeError(f"product metadata mismatch: {identity}")


def _wheel_path(wheelhouse: Path, version: str) -> Path:
    """Resolve exactly one non-editable product wheel from a wheelhouse."""
    wheels = list(wheelhouse.glob(f"louke-{version}-*.whl"))
    if len(wheels) != 1:
        raise RuntimeError(
            f"expected exactly one louke {version} wheel, found {wheels}"
        )
    return wheels[0].absolute()


def _server_command(product_python: Path, workspace: Path) -> list[str]:
    """Return the public installed-product command Shield uses to start Louke."""
    return [
        str(product_python.absolute()),
        "-m",
        "louke",
        "serve",
        "--project-root",
        str(workspace.absolute()),
        "--host",
        "127.0.0.1",
        "--opencode-backend",
        "mock",
    ]


# Locked v014 runner evidence schema (project-runner.candidate.json §evidence_schema).
EVIDENCE_REQUIRED_FIELDS: tuple[str, ...] = (
    "schema_version",
    "release_identity",
    "spec_id",
    "base_commit",
    "runner_digest",
    "command",
    "profile",
    "runtime",
    "expected_node_ids",
    "collected_node_ids",
    "ac_layers",
    "suite_results",
    "service_lifecycle",
    "started_at",
    "finished_at",
    "exit_reason",
    "evidence_digest",
)

_INTEGRATION_PATHS: tuple[str, ...] = (
    "tests/integration/install_experience",
    "tests/integration/v014_design_contracts",
    "tests/integration/v014_workflow_reflow",
)


def _integration_paths() -> list[str]:
    """Ordered integration discovery: historical suite then the v014 suite."""
    return list(_INTEGRATION_PATHS)


def _expand_profiles(profile: str) -> list[str]:
    """Expand a selected profile; ``all`` includes the v0.14 entry suite."""
    if profile == "all":
        return ["install", "chromium", "v014"]
    return [profile]


def _profile_paths(profile: str) -> tuple[list[str], list[str]]:
    if profile == "install":
        return ["tests/e2e/install_experience"], []
    if profile == "v014":
        return ["tests/e2e/v014_workflow_reflow"], ["-m", "chromium_e2e"]
    return ["tests/e2e/test_v013_chromium_journey_e2e.py"], ["-m", "chromium_e2e"]


def main(argv: list[str] | None = None) -> int:
    root = _repo_root()
    try:
        version = _verify_host_identity(root)
    except (
        ImportError,
        OSError,
        RuntimeError,
        importlib.metadata.PackageNotFoundError,
    ) as exc:
        print(f"run-project-venv: {exc}", file=sys.stderr)
        return 127
    args = _parser().parse_args(argv)
    print(f"runner={Path(sys.executable).absolute()} louke_version={version}")
    if args.command == "integration":
        return _run_pytest(
            root,
            _integration_paths(),
            args.pytest_args,
            os.environ.copy(),
        )

    profiles = _expand_profiles(args.profile)
    runtimes = ("local", "global") if args.runtime == "both" else (args.runtime,)
    try:
        with tempfile.TemporaryDirectory(prefix="louke-v014-e2e-") as temporary:
            temporary_root = Path(temporary)
            wheelhouse = _prepare_wheelhouse(root, temporary_root, version)
            for profile in profiles:
                for runtime in runtimes:
                    print(f"profile={profile} runtime={runtime}")
                    case_root = temporary_root / f"{profile}-{runtime}"
                    case_root.mkdir()
                    cwd, _, environment = _install_case(
                        root, case_root, wheelhouse, version, runtime
                    )
                    environment["LOUKE_E2E_PROFILE"] = profile
                    if profile in {"chromium", "v014"}:
                        _require_chromium(environment)
                    paths, selection = _profile_paths(profile)
                    result = _run_pytest(
                        root,
                        paths,
                        [*selection, *args.pytest_args],
                        environment,
                    )
                    if result:
                        return result
                    if not cwd.exists():
                        raise RuntimeError(f"case workspace disappeared: {cwd}")
    except (
        OSError,
        RuntimeError,
        subprocess.SubprocessError,
        json.JSONDecodeError,
    ) as exc:
        print(f"run-project-venv: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
