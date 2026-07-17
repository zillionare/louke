"""Unit checks for the Windows installer's public contract."""

from pathlib import Path


ROOT = Path(__file__).parents[3]


def test_ac_fr1502_installer_pair_is_available() -> None:
    """AC-FR1502-03: bat and PowerShell are independently runnable assets."""
    assert (ROOT / "install.bat").is_file()
    assert (ROOT / "install.ps1").is_file()


def test_ac_fr1502_bat_bypasses_restricted_execution_policy() -> None:
    """AC-FR1502-03: the batch wrapper explicitly bypasses PowerShell policy."""
    batch = (ROOT / "install.bat").read_text(encoding="utf-8").lower()

    assert "-executionpolicy bypass" in batch
    assert "install.ps1" in batch


def test_ac_fr1502_powershell_creates_project_venv_and_rejects_old_python() -> None:
    """AC-FR1502-01/02: install locally and require Python 3.11 or newer."""
    script = (ROOT / "install.ps1").read_text(encoding="utf-8").lower()

    assert ".venv" in script
    assert "3.11" in script
    assert "python" in script
    assert "non-zero" in script or "exit 1" in script


def test_ac_fr1503_powershell_verifies_installed_runtime_versions() -> None:
    """AC-FR1503-01/04: local and global installs report verified package truth."""
    script = (ROOT / "install.ps1").read_text(encoding="utf-8")

    assert "Get-RuntimeVersion" in script
    assert "Runtime version mismatch" in script
    assert "Requested louke $Version but installed $projectVersion" in script
