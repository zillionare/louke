"""Native installed-product checks for the v0.13.1 dual-runtime contract."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess

import pytest


# AC-NFR1503-01@v0.13.1: this suite is a runner-owned product-runtime journey.
pytestmark = pytest.mark.skipif(
    not os.environ.get("LOUKE_E2E_CASE_CWD"),
    reason="install experience journey must run through the unified product runner",
)


def _run(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    shim = os.environ["LOUKE_E2E_SHIM"]
    return subprocess.run(
        [shim, *args],
        cwd=cwd or Path(os.environ["LOUKE_E2E_CASE_CWD"]),
        env=os.environ.copy(),
        text=True,
        capture_output=True,
    )


def test_installer_created_both_runtimes_and_strict_cwd_shim() -> None:
    """AC-FR1503-01/02/04, AC-FR1504-01/02/03, AC-FR1505-01@v0.13.1."""
    case_cwd = Path(os.environ["LOUKE_E2E_CASE_CWD"])
    case_home = Path(os.environ["LOUKE_E2E_CASE_HOME"])
    version = os.environ["LOUKE_E2E_WHEEL_VERSION"]
    runtime = os.environ["LOUKE_E2E_RUNTIME"]
    local_python = (
        case_cwd / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    )
    global_python = (
        case_home
        / ".louke"
        / "venv"
        / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    )
    if runtime == "local":
        assert local_python.is_file()
    assert global_python.is_file()
    result = _run("--version")
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == f"lk {version} ({runtime})"

    child = case_cwd / "child-without-local-runtime"
    child.mkdir()
    child_result = _run("--version", cwd=child)
    assert child_result.returncode == 0, child_result.stderr
    assert child_result.stdout.strip() == f"lk {version} (global)"


def test_upgrade_targets_selected_product_runtime_without_reboarding() -> None:
    """AC-FR1507-01/03/04, AC-FR1508-01/02/03, AC-FR1509-01/03@v0.13.1."""
    runtime = os.environ["LOUKE_E2E_RUNTIME"]
    version = os.environ["LOUKE_E2E_WHEEL_VERSION"]
    result = _run("upgrade", f"--{runtime}", "--version", version)
    assert result.returncode == 0, result.stderr
    assert f"({runtime})" in result.stdout
    assert "board opencode" not in result.stdout
