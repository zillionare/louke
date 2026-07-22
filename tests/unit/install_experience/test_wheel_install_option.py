"""Contract tests for the ``--wheel`` install-source option.

The v0.14.0 CI install matrix installs the wheel built in the same CI run
instead of pulling a not-yet-published version from PyPI. ``install.sh`` gains
``--wheel <path>`` and ``install.ps1`` gains ``-Wheel <path>``; the wheel path
becomes the pip install target while ``--version`` / ``-Version`` continue to
drive post-install runtime version validation only.
"""

from __future__ import annotations

import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
INSTALL_SH = ROOT / "install.sh"
INSTALL_PS1 = ROOT / "install.ps1"


def test_unix_installer_parses_wheel_flag() -> None:
    """install.sh recognizes ``--wheel <path>`` as a first-class flag.

    The flag must consume a path argument and store it in a ``WHEEL``
    variable (mirrors ``--version``'s arity) so a local wheel can be
    installed verbatim.
    """
    script = INSTALL_SH.read_text(encoding="utf-8")
    assert "--wheel" in script, "install.sh does not recognize --wheel"
    assert "WHEEL=" in script, "install.sh does not store the wheel path"


def test_unix_installer_help_advertises_wheel() -> None:
    """``install.sh --help`` lists ``--wheel`` so CI and users can discover it.

    Help is emitted on stderr (see the existing ``-h|--help`` branch), so the
    assertion reads ``result.stderr``.
    """
    result = subprocess.run(
        ["bash", str(INSTALL_SH), "--help"],
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0
    assert "--wheel" in result.stderr, "install.sh --help does not document --wheel"


def test_unix_installer_wheel_is_the_install_target() -> None:
    """With ``--wheel``, ``PKG_SPEC`` is the wheel path, not ``louke==$VERSION``.

    The wheel branch must short-circuit the PyPI name pin so a local wheel is
    installed verbatim rather than resolved from PyPI.
    """
    script = INSTALL_SH.read_text(encoding="utf-8")
    decision = script[script.index("Decide install source") :]
    assert "WHEEL" in decision, "install.sh install-source decision ignores --wheel"
    assert "PKG_SPEC" in decision


def test_unix_installer_keeps_version_validation_with_wheel() -> None:
    """``--version`` still drives post-install validation when ``--wheel`` is used.

    Regression guard: the existing ``requested louke $VERSION but installed``
    check must survive the ``--wheel`` change so a wheel reporting the wrong
    version still fails the installer.
    """
    script = INSTALL_SH.read_text(encoding="utf-8")
    assert "requested louke $VERSION but installed $PROJECT_PACKAGE_VERSION" in script


def test_windows_installer_declares_wheel_parameter() -> None:
    """install.ps1 declares ``-Wheel`` as a typed parameter.

    Declaring it in the ``param()`` block is what makes ``Get-Help`` advertise
    the parameter to callers.
    """
    script = INSTALL_PS1.read_text(encoding="utf-8")
    assert "[string]$Wheel" in script, "install.ps1 does not declare -Wheel"


def test_windows_installer_wheel_is_the_install_target() -> None:
    """With ``-Wheel``, the package spec is the wheel path, not ``louke==$Version``.

    The wheel must take precedence in the ``$package`` assignment so a local
    wheel is installed verbatim.
    """
    script = INSTALL_PS1.read_text(encoding="utf-8")
    assert "$Wheel" in script, "install.ps1 package assignment ignores -Wheel"
    assert "louke==$Version" in script


def test_windows_installer_keeps_version_validation_with_wheel() -> None:
    """``-Version`` still validates the installed runtime when ``-Wheel`` is used.

    Regression guard: the existing ``Requested louke $Version but installed``
    check must survive the ``-Wheel`` change.
    """
    script = INSTALL_PS1.read_text(encoding="utf-8")
    assert "Requested louke $Version but installed $projectVersion" in script
