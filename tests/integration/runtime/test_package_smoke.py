"""Wheel packaging smoke test for v0.12 subpackages and version convergence.

S1 (#174): prove the built wheel actually contains the v0.12 subpackages
(``louke.runtime``, ``louke.opencode``, ``louke.web.api``, ``louke.web.pages``)
and that importing them from a clean install succeeds. Source-tree tests
pass even when the wheel is broken because Python sees the files on disk;
this test builds a real wheel and inspects its contents, so a packaging
regression fails here regardless of how the source tree looks.

S2 (#175): prove the installed package version, wheel METADATA version,
``louke.__version__`` and ``lk --version`` all converge on the expected
release string. Drift between any of these is a release-blocker.

The test is hermetic: the wheel is built into a per-run temp directory and
the install happens in a throwaway venv created under ``tempfile.gettempdir()``.
No state leaks between runs.
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

#: Subpackages that MUST appear in the built wheel as real package directories.
#: Each entry is matched as a path prefix inside the wheel zip so that, e.g.,
#: ``louke/runtime`` also matches ``louke/runtime/__init__.py``.
EXPECTED_WHEEL_SUBPACKAGES: tuple[str, ...] = (
    "louke/runtime/",
    "louke/opencode/",
    "louke/web/api/",
    "louke/web/pages/",
)

#: Concrete module files that MUST be present in the wheel, proving the
#: subpackage is not just an empty ``__init__.py``. Each is checked as a
#: path inside the wheel zip.
EXPECTED_WHEEL_MODULES: tuple[str, ...] = (
    "louke/runtime/__init__.py",
    "louke/opencode/__init__.py",
    "louke/web/api/__init__.py",
    "louke/web/pages/__init__.py",
)

#: The release version every source must converge on. Bumped per release.
#: Must match ``pyproject.toml [project].version`` and the release identity
#: declared in ``.louke/project/project.toml`` so wheel METADATA, the
#: installed ``louke.__version__`` and ``lk --version`` all report the same
#: string as the release branch/tag (e.g. ``releases/0.14.0`` / ``v0.14.0``).
EXPECTED_VERSION = "0.14.0"


def _repo_root() -> Path:
    """Return the repository root (this test lives under it).

    This file lives at ``<root>/tests/integration/runtime/test_package_smoke.py``,
    so the repo root is three parents up from the file: the file's parent is
    ``runtime``, then ``integration``, then ``tests``, then the root.
    """
    return Path(__file__).resolve().parents[3]


def _subprocess_env() -> dict[str, str]:
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


def _build_wheel(out_dir: Path) -> Path:
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


def _wheel_metadata_version(wheel_path: Path) -> str:
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


def _create_clean_venv(prefix: Path) -> Path:
    """Create a throwaway virtualenv at ``prefix`` and return its python path.

    Creates the venv without pip, then bootstraps pip by running
    ``ensurepip`` from the venv python with the parent interpreter's lib
    dir on ``DYLD_LIBRARY_PATH``. The direct ``with_pip=True`` path is
    skipped because on some standalone CPython builds (uv-managed
    interpreters on macOS) the internal ensurepip subprocess crashes
    before the library path can be propagated.

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
            env=_subprocess_env(),
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
        env=_subprocess_env(),
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


def _install_wheel(venv_python: Path, wheel_path: Path) -> None:
    """Install ``wheel_path`` (with its declared deps) into the target venv.

    Deps are required because ``louke/__init__.py`` imports submodules that
    depend on runtime dependencies (starlette, httpx, etc.); a ``--no-deps``
    install would let the wheel file land but fail on first import.

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
        env=_subprocess_env(),
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"pip install failed:\nstdout:\n{completed.stdout}\n"
            f"stderr:\n{completed.stderr}"
        )


def _run_in_venv(venv_python: Path, *args: str) -> subprocess.CompletedProcess:
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
        env=_subprocess_env(),
    )


@pytest.fixture()
def built_wheel(tmp_path: Path) -> Path:
    """Build the louke wheel once per test into a temp dir and return it.

    The wheel build is isolated (``python -m build`` creates its own build
    venv), so reusing one wheel across tests would not save much; building
    per-test keeps each test fully independent and hermetic.
    """
    return _build_wheel(tmp_path)


@pytest.fixture()
def clean_venv(tmp_path: Path) -> tuple[Path, Path]:
    """Create a clean venv with pip and return ``(venv_dir, venv_python)``.

    The venv has no access to the repo source tree, so any import success
    proves the wheel (not the source tree) supplies the package.
    """
    venv_dir = tmp_path / "clean_venv"
    return venv_dir, _create_clean_venv(venv_dir)


class TestWheelPackageContents:
    """S1 (#174): the built wheel must contain every v0.12 subpackage."""

    def test_wheel_contains_v012_subpackages(self, built_wheel: Path) -> None:
        """Every expected v0.12 subpackage dir exists inside the wheel zip.

        Asserts that ``louke/runtime/``, ``louke/opencode/``, ``louke/web/api/``
        and ``louke/web/pages/`` each contribute at least one file to the
        wheel. A bare top-level ``louke`` package without these subpackages
        fails this test, matching the gap-analysis Batch 0 baseline.
        """
        with zipfile.ZipFile(built_wheel) as zf:
            names = zf.namelist()
        for subpkg in EXPECTED_WHEEL_SUBPACKAGES:
            matching = [n for n in names if n.startswith(subpkg)]
            assert matching, (
                f"wheel missing subpackage {subpkg!r}; "
                f"wheel contents do not include any file under {subpkg}"
            )

    def test_wheel_contains_subpackage_init_modules(self, built_wheel: Path) -> None:
        """Each v0.12 subpackage ships its ``__init__.py`` in the wheel.

        This is stronger than the directory-prefix check: it proves the
        subpackages are real importable Python packages, not incidental
        data files that happen to sit under those paths.
        """
        with zipfile.ZipFile(built_wheel) as zf:
            names = set(zf.namelist())
        for module in EXPECTED_WHEEL_MODULES:
            assert module in names, (
                f"wheel missing module {module!r}; subpackage __init__.py not packaged"
            )

    def test_clean_venv_can_import_v012_subpackages(
        self, built_wheel: Path, clean_venv: tuple[Path, Path]
    ) -> None:
        """A clean venv that installs the wheel can import every subpackage.

        This is the exit-condition smoke from gap-analysis §3 P0-1: source
        tree visibility must not mask a broken wheel. The venv has no access
        to the repo source, so this only passes if the wheel is complete.
        """
        _, venv_python = clean_venv
        _install_wheel(venv_python, built_wheel)
        completed = _run_in_venv(
            venv_python,
            "-c",
            "import louke.runtime, louke.opencode, louke.web.api, louke.web.pages",
        )
        assert completed.returncode == 0, (
            f"clean-venv import failed:\nstdout:\n{completed.stdout}\n"
            f"stderr:\n{completed.stderr}"
        )


class TestVersionConvergence:
    """S2 (#175): every version surface converges on the release version."""

    def test_wheel_metadata_version_matches_release(self, built_wheel: Path) -> None:
        """The wheel METADATA ``Version`` header equals the expected release.

        Drift here means the built artifact reports a different version from
        the one intended for release, which is a release-blocker.
        """
        assert _wheel_metadata_version(built_wheel) == EXPECTED_VERSION

    def test_installed_dunder_version_matches_release(
        self, built_wheel: Path, clean_venv: tuple[Path, Path]
    ) -> None:
        """``louke.__version__`` in a clean install equals the release version.

        Guards against a hardcoded fallback or stale constant in
        ``louke/__init__.py`` diverging from the wheel METADATA.
        """
        _, venv_python = clean_venv
        _install_wheel(venv_python, built_wheel)
        completed = _run_in_venv(
            venv_python, "-c", "from louke import __version__; print(__version__)"
        )
        assert completed.returncode == 0, (
            f"reading __version__ failed:\nstdout:\n{completed.stdout}\n"
            f"stderr:\n{completed.stderr}"
        )
        assert completed.stdout.strip() == EXPECTED_VERSION

    def test_lk_cli_version_matches_release(
        self, built_wheel: Path, clean_venv: tuple[Path, Path]
    ) -> None:
        """``lk --version`` in a clean venv reports the release version.

        This exercises the full CLI entry point, proving the console script
        and version string agree with the wheel METADATA.
        """
        venv_dir, venv_python = clean_venv
        _install_wheel(venv_python, built_wheel)
        lk_bin = venv_dir / "bin" / "lk"
        completed = subprocess.run(
            [str(lk_bin), "--version"],
            capture_output=True,
            text=True,
            env=_subprocess_env(),
        )
        assert completed.returncode == 0, (
            f"lk --version failed:\nstdout:\n{completed.stdout}\n"
            f"stderr:\n{completed.stderr}"
        )
        assert EXPECTED_VERSION in completed.stdout, (
            f"lk --version output {completed.stdout!r} does not contain "
            f"{EXPECTED_VERSION!r}"
        )
