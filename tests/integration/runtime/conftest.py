"""Shared fixtures for ``tests/integration/runtime/``.

Exposes hermetic wheel-build + clean-venv-install fixtures reused by the
package smoke (S1/S2) and the server-boot smoke (S7) tests. Keeping the
build/install helpers here lets multiple test modules share one wheel build
per session without copy-pasting the venv bootstrap dance.

References:
- gap-analysis §4 Batch 1 / Batch 5 (S7 installed-wheel server smoke)
- issue #174 (S1), #175 (S2), #180 (S7)
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import venv
import zipfile
from pathlib import Path

import pytest


def _repo_root() -> Path:
    """Return the repository root (this file lives under it).

    This file lives at ``<root>/tests/integration/runtime/conftest.py``, so
    the repo root is three parents up: ``runtime`` -> ``integration`` ->
    ``tests`` -> root.
    """
    return Path(__file__).resolve().parents[3]


def subprocess_env() -> dict[str, str]:
    """Return an env for subprocess calls to clean-venv pythons.

    On macOS with a standalone CPython build (e.g. uv-managed interpreters),
    the venv python cannot find ``libpythonX.Y.dylib`` unless the parent
    interpreter's lib dir is on ``DYLD_LIBRARY_PATH``. This propagates that
    path so subprocess calls to venv pythons do not SIGABRT. On platforms
    where the dylib is not needed the extra path is simply unused.
    """
    env = os.environ.copy()
    for candidate in (
        Path(sys.base_prefix) / "lib",
        Path(sys.base_prefix).parent / "lib",
    ):
        if candidate.exists() and any(candidate.glob("libpython*.dylib")):
            env["DYLD_LIBRARY_PATH"] = (
                str(candidate) + os.pathsep + env.get("DYLD_LIBRARY_PATH", "")
            )
            break
    return env


def build_wheel(out_dir: Path) -> Path:
    """Build the louke wheel into ``out_dir`` and return its path.

    Args:
        out_dir: Directory to receive the built wheel; must exist.

    Returns:
        Path to the built ``*.whl`` file.

    Raises:
        RuntimeError: If ``python -m build`` fails or no wheel is produced.
    """
    completed = subprocess.run(
        [sys.executable, "-m", "build", "--wheel", "--outdir", str(out_dir)],
        cwd=str(_repo_root()),
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"python -m build failed:\nstdout:\n{completed.stdout}\n"
            f"stderr:\n{completed.stderr}"
        )
    wheels = list(out_dir.glob("louke-*.whl"))
    if not wheels:
        raise RuntimeError(f"no wheel produced in {out_dir}")
    if len(wheels) > 1:
        raise RuntimeError(
            f"expected exactly one wheel in {out_dir}, got: {[w.name for w in wheels]}"
        )
    return wheels[0]


def create_clean_venv(prefix: Path) -> Path:
    """Create a throwaway virtualenv at ``prefix`` and return its python path.

    Creates the venv without pip, then bootstraps pip via ``ensurepip`` with
    the parent interpreter's lib dir on ``DYLD_LIBRARY_PATH`` so standalone
    CPython builds do not SIGABRT.

    Args:
        prefix: Directory to create the venv under; must not yet exist.

    Returns:
        Path to the venv's ``python`` executable.

    Raises:
        RuntimeError: If venv creation or pip bootstrap fails.
    """
    venv.create(str(prefix), with_pip=False, clear=True)
    py = prefix / "bin" / "python"
    if not py.exists():
        raise RuntimeError(f"venv python not found at {py}")
    _bootstrap_pip(py)
    return py


def _pip_works(venv_python: Path) -> bool:
    """Return True if ``venv_python -m pip --version`` exits cleanly."""
    return (
        subprocess.run(
            [str(venv_python), "-m", "pip", "--version"],
            capture_output=True,
            text=True,
            env=subprocess_env(),
        ).returncode
        == 0
    )


def _bootstrap_pip(venv_python: Path) -> None:
    """Install pip into ``venv_python``'s venv via ``ensurepip``.

    Args:
        venv_python: Path to the target venv's ``python`` executable.

    Raises:
        RuntimeError: If ``ensurepip`` fails or pip is not usable afterwards.
    """
    completed = subprocess.run(
        [str(venv_python), "-m", "ensurepip", "--upgrade", "--default-pip"],
        capture_output=True,
        text=True,
        env=subprocess_env(),
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"ensurepip failed:\nstdout:\n{completed.stdout}\n"
            f"stderr:\n{completed.stderr}"
        )
    if not _pip_works(venv_python):
        raise RuntimeError(
            f"pip not usable after ensurepip in venv at {venv_python.parent.parent}"
        )


def install_wheel(venv_python: Path, wheel_path: Path) -> None:
    """Install ``wheel_path`` (with its declared deps) into the target venv.

    Args:
        venv_python: Path to the target venv's ``python`` executable.
        wheel_path: Path to the built ``*.whl`` file to install.

    Raises:
        RuntimeError: If ``pip install`` fails.
    """
    completed = subprocess.run(
        [
            str(venv_python),
            "-m",
            "pip",
            "install",
            "--force-reinstall",
            str(wheel_path),
        ],
        capture_output=True,
        text=True,
        env=subprocess_env(),
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"pip install failed:\nstdout:\n{completed.stdout}\n"
            f"stderr:\n{completed.stderr}"
        )


def run_in_venv(venv_python: Path, *args: str) -> subprocess.CompletedProcess:
    """Run ``args`` via ``venv_python`` with the venv-compatible env.

    Args:
        venv_python: Path to the venv's ``python`` executable.
        *args: Command-line arguments to pass to the python interpreter.

    Returns:
        The completed process result (stdout/stderr captured).
    """
    return subprocess.run(
        [str(venv_python), *args],
        capture_output=True,
        text=True,
        env=subprocess_env(),
    )


def wheel_metadata_version(wheel_path: Path) -> str:
    """Extract the ``Version`` field from the wheel's METADATA file.

    Args:
        wheel_path: Path to the built ``*.whl`` file.

    Returns:
        The value of the ``Version`` header from the wheel METADATA.

    Raises:
        RuntimeError: If METADATA is missing or has no Version header.
    """
    with zipfile.ZipFile(wheel_path) as zf:
        metadata_names = [n for n in zf.namelist() if n.endswith(".dist-info/METADATA")]
        if not metadata_names:
            raise RuntimeError(f"no METADATA in {wheel_path}")
        metadata = zf.read(metadata_names[0]).decode("utf-8", errors="replace")
    match = re.search(r"^Version:\s*(.+)$", metadata, re.MULTILINE)
    if not match:
        raise RuntimeError(f"no Version header in METADATA of {wheel_path}")
    return match.group(1).strip()


@pytest.fixture(scope="session")
def built_wheel(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Build the louke wheel once per session and return its path.

    Session-scoped because ``python -m build`` is slow (~20-40s) and the
    wheel is immutable; sharing one build across all server-boot + package
    smoke tests keeps the integration layer fast without sacrificing
    hermeticity (the wheel is built into a per-session temp dir).
    """
    out_dir = tmp_path_factory.mktemp("wheel_build")
    return build_wheel(out_dir)


@pytest.fixture()
def clean_venv(tmp_path: Path) -> tuple[Path, Path]:
    """Create a clean venv with pip and return ``(venv_dir, venv_python)``.

    The venv has no access to the repo source tree, so any import or
    ``lk`` invocation success proves the wheel (not the source tree)
    supplies the package.
    """
    venv_dir = tmp_path / "clean_venv"
    return venv_dir, create_clean_venv(venv_dir)
