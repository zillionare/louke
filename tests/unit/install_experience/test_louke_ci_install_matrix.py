"""Static contract over ``.github/workflows/louke-ci.yml`` install-matrix.

The v0.14.0 install matrix must install the wheel built in the same CI run
(``needs: build-artifacts`` + ``download-artifact``) instead of pulling a
not-yet-published version from PyPI. The Unix step passes the wheel to
``install.sh --wheel`` and the Windows step to ``install.ps1 -Wheel``;
``--version`` / ``-Version`` continue to validate the installed runtime.
``install-matrix`` must remain a mandatory input to ``Louke CI / required``.

This is a static contract check over the checked-in YAML; it does not run the
workflow. It goes Red before the workflow is wired and Green after, giving the
CI change fail-then-pass executable evidence (architecture §9.3 / IF-CI-01).
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[3]
WORKFLOW = ROOT / ".github" / "workflows" / "louke-ci.yml"
SUPPORTED_INSTALL_RUNNERS = ("ubuntu-22.04", "macos-14", "windows-2022")
SUPPORTED_INSTALL_PYTHON_VERSIONS = ("3.11", "3.12", "3.13")
UNIT_PYTHON_VERSIONS = (*SUPPORTED_INSTALL_PYTHON_VERSIONS, "3.14")
BUILD_ARTIFACT = "louke-build-artifacts-${{ github.sha }}"


@pytest.fixture(scope="module")
def workflow() -> dict:
    """Parse ``louke-ci.yml`` once and return the full workflow mapping.

    Returns:
        The parsed workflow as a dict (jobs under the ``jobs`` key).

    Raises:
        FileNotFoundError: If ``louke-ci.yml`` is absent (the contract test
            then fails with a clear message at the call site).
    """
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))


def _install_matrix(workflow: dict) -> dict:
    return workflow["jobs"]["install-matrix"]


def test_install_matrix_needs_build_artifacts(workflow: dict) -> None:
    """install-matrix depends on build-artifacts so the wheel exists this run.

    Before this change install-matrix needed only ``quality`` and pulled
    ``louke==0.14.0`` from PyPI, which fails while 0.14.0 is unreleased.
    """
    needs = _install_matrix(workflow)["needs"]
    assert "build-artifacts" in needs, (
        "install-matrix must need build-artifacts to consume this run's wheel"
    )


def test_install_matrix_downloads_build_artifacts(workflow: dict) -> None:
    """install-matrix downloads this commit's build artifact into ``dist/``."""
    steps = _install_matrix(workflow)["steps"]
    downloads = [s for s in steps if "download-artifact" in s.get("uses", "")]
    assert downloads, "install-matrix has no download-artifact step"
    download = downloads[0]
    assert download["with"]["name"] == BUILD_ARTIFACT
    assert download["with"]["path"] == "dist/"


def test_install_matrix_unix_step_installs_local_wheel(workflow: dict) -> None:
    """Unix first-install passes ``--wheel dist/louke-0.14.0*.whl`` to install.sh."""
    steps = _install_matrix(workflow)["steps"]
    unix = next(s for s in steps if s.get("name") == "Unix first install")
    run = unix["run"]
    assert "install.sh" in run
    assert "--wheel" in run
    assert "dist/louke-0.14.0" in run
    # --version still drives post-install validation.
    assert "--version 0.14.0" in run


def test_install_matrix_windows_step_installs_local_wheel(workflow: dict) -> None:
    """Windows first-install passes ``-Wheel dist/louke-0.14.0*.whl`` to install.ps1."""
    steps = _install_matrix(workflow)["steps"]
    win = next(s for s in steps if s.get("name") == "Windows first install")
    run = win["run"]
    assert "install.ps1" in run
    assert "-Wheel" in run
    assert "dist/louke-0.14.0" in run
    assert "-Version 0.14.0" in run


def test_install_matrix_remains_required(workflow: dict) -> None:
    """install-matrix stays a mandatory input to ``Louke CI / required``.

    Regression guard: the aggregated required check must still fail closed
    when install-matrix does not succeed.
    """
    required_needs = workflow["jobs"]["required"]["needs"]
    assert "install-matrix" in required_needs


def test_install_matrix_uses_available_supported_runners(workflow: dict) -> None:
    """The canonical first-install matrix uses only available supported runners."""
    expected = {
        (os, python_version)
        for os in SUPPORTED_INSTALL_RUNNERS
        for python_version in SUPPORTED_INSTALL_PYTHON_VERSIONS
    }
    entries = _install_matrix(workflow)["strategy"]["matrix"]["include"]
    actual = {(entry["os"], entry["python-version"]) for entry in entries}

    assert actual == expected


def test_unit_matrix_retains_python_314(workflow: dict) -> None:
    """The unit matrix continues to cover Python 3.14 independently."""
    versions = workflow["jobs"]["unit"]["strategy"]["matrix"]["python-version"]

    assert versions == list(UNIT_PYTHON_VERSIONS)
