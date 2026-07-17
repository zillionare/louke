"""Black-box bootstrap and native installer contract checks."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess


ROOT = Path(__file__).parents[3]


def test_project_venv_bootstrap_has_no_path_fallback(tmp_path: Path) -> None:
    """I-13 / AC-NFR1502-01@v0.13.1: a missing project Python exits 127."""
    copied_root = tmp_path / "checkout"
    launcher_dir = copied_root / "tests" / "e2e"
    launcher_dir.mkdir(parents=True)
    launcher = launcher_dir / "run-project-venv"
    shutil.copy2(ROOT / "tests" / "e2e" / "run-project-venv", launcher)
    launcher.chmod(0o755)
    result = subprocess.run(
        [str(launcher), "integration"], text=True, capture_output=True
    )
    assert result.returncode == 127
    assert str((copied_root / ".venv" / "bin" / "python").resolve()) in result.stderr


def test_unix_installer_rejects_python_310(tmp_path: Path) -> None:
    """I-01 / AC-FR1501-03@v0.13.1: incompatible Python fails clearly."""
    if os.name == "nt":
        return
    fixture_bin = tmp_path / "bin"
    fixture_bin.mkdir()
    python3 = fixture_bin / "python3"
    python3.write_text(
        '#!/bin/sh\nif [ "$1" = "-V" ]; then echo \'Python 3.10.14\'; '
        "else echo '3.10'; fi\n",
        encoding="utf-8",
    )
    python3.chmod(0o755)
    environment = os.environ.copy()
    environment["HOME"] = str(tmp_path / "isolated-user")
    environment["PATH"] = os.pathsep.join((str(fixture_bin), "/usr/bin", "/bin"))
    result = subprocess.run(
        ["bash", str(ROOT / "install.sh")],
        cwd=tmp_path,
        env=environment,
        text=True,
        capture_output=True,
    )
    assert result.returncode != 0
    assert "Python 3.11+ required" in result.stderr


def test_windows_entrypoint_forces_execution_policy_bypass() -> None:
    """I-01 / AC-FR1502-03@v0.13.1: BAT delegates with Bypass."""
    text = (ROOT / "install.bat").read_text(encoding="utf-8")
    assert "-ExecutionPolicy Bypass" in text
    assert "install.ps1" in text


def test_unix_installer_verifies_both_installed_versions() -> None:
    """I-02/I-06 / AC-FR1503-01, AC-FR1506-03@v0.13.1: verify package truth."""
    text = (ROOT / "install.sh").read_text(encoding="utf-8")
    assert "runtime_package_version" in text
    assert "PROJECT_PACKAGE_VERSION" in text
    assert "GLOBAL_PACKAGE_VERSION" in text
    assert "requested louke $VERSION but installed $PROJECT_PACKAGE_VERSION" in text
