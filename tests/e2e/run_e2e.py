"""Single project-venv bootstrap for v0.13.1 integration and product E2E."""

from __future__ import annotations

import argparse
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
    e2e.add_argument("--profile", choices=("install", "chromium", "all"), required=True)
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


def _prepare_wheelhouse(root: Path, temporary_root: Path, version: str) -> Path:
    configured = os.environ.get("LOUKE_E2E_WHEELHOUSE", "").strip()
    if configured:
        wheelhouse = Path(configured).resolve()
        if not list(wheelhouse.glob(f"louke-{version}-*.whl")):
            raise RuntimeError(f"wheelhouse has no louke {version} wheel: {wheelhouse}")
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
    manifest = {
        "version": version,
        "runner_python": str(Path(sys.executable).absolute()),
        "wheel": wheels[0].name,
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
        ]
    else:
        command = ["bash", str(root / "install.sh"), "--version", version]
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
    probe = subprocess.run(
        [
            str(product_python),
            "-c",
            "import importlib.metadata,json,louke,sys; "
            "print(json.dumps({'python':sys.executable,'louke':louke.__file__,"
            "'version':importlib.metadata.version('louke')}))",
        ],
        env=environment,
        text=True,
        capture_output=True,
    )
    if probe.returncode:
        raise RuntimeError(f"product identity probe failed: {probe.stderr.strip()}")
    identity = json.loads(probe.stdout)
    product_root = product_python.parent.parent.absolute()
    if Path(identity["python"]).absolute() != product_python.absolute():
        raise RuntimeError(f"product executable mismatch: {identity}")
    if not _inside(Path(identity["louke"]).absolute(), product_root):
        raise RuntimeError(f"product louke is outside product venv: {identity}")
    if identity["version"] != version:
        raise RuntimeError(f"product metadata mismatch: {identity}")


def _profile_paths(profile: str) -> tuple[list[str], list[str]]:
    if profile == "install":
        return ["tests/e2e/install_experience"], []
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
            ["tests/integration/install_experience"],
            args.pytest_args,
            os.environ.copy(),
        )

    profiles = ("install", "chromium") if args.profile == "all" else (args.profile,)
    runtimes = ("local", "global") if args.runtime == "both" else (args.runtime,)
    try:
        with tempfile.TemporaryDirectory(prefix="louke-v0131-e2e-") as temporary:
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
