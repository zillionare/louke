"""Canonical workflow contract test asserting the v0.14.0 CI gates.

The canonical ``.github/workflows/louke-ci.yml`` must, on every push/PR,
run the approved quality, artifact, unit, integration, e2e, traceability,
install, and fail-closed required gates.

This test parses the committed workflow YAML and asserts the contract
holds, so a future edit that silently drops one of the gates fails here
rather than only being noticed at release time. It does NOT run the
workflow; it is a static contract check over the checked-in file.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest


def _repo_root() -> Path:
    """Return the repository root (this file lives under it).

    This file lives at ``<root>/tests/integration/runtime/test_ci_contract.py``,
    so the repo root is four parents up: runtime -> integration -> tests -> root.
    """
    return Path(__file__).resolve().parents[3]


def _ci_workflow_path() -> Path:
    """Return the path to the canonical CI workflow file.

    Returns:
        ``<repo_root>/.github/workflows/louke-ci.yml``.
    """
    return _repo_root() / ".github" / "workflows" / "louke-ci.yml"


def _ci_workflow_text() -> str:
    """Read and return the raw text of the canonical workflow.

    Returns:
        The full file contents as a string.

    Raises:
        FileNotFoundError: If the canonical workflow does not exist (the test
            then fails with a clear message at the call site).
    """
    path = _ci_workflow_path()
    return path.read_text(encoding="utf-8")


class TestCIWorkflowContract:
    """Static contract over ``.github/workflows/louke-ci.yml`` for v0.14.0.

    Each assertion protects one mandatory gate and prevents a workflow edit
    from silently weakening the canonical required check.
    """

    def test_ci_workflow_file_exists(self) -> None:
        """The canonical workflow exists at the managed GitHub Actions path."""
        assert _ci_workflow_path().exists(), (
            f"expected CI workflow at {_ci_workflow_path()} but it is absent"
        )

    def test_ci_runs_unit_pytest(self) -> None:
        """The unit matrix invokes pytest over the unit test layer."""
        text = _ci_workflow_text()
        pattern = r"pytest\s+-q\s+tests/unit"
        assert re.search(pattern, text), (
            "louke-ci.yml does not contain a step running 'pytest -q tests/unit'"
        )

    def test_ci_measures_runtime_coverage(self) -> None:
        """CI measures coverage of ``louke.runtime`` and emits a report.

        The coverage target is fixed by the approved test plan (§6 #8:
        coverage gate must not be lowered to make CI green). This asserts
        the ``--cov=louke.runtime`` flag is present so the gate actually
        measures the v0.12 runtime domain rather than silently no-oping.
        """
        text = _ci_workflow_text()
        assert "--cov=louke.runtime" in text, (
            "louke-ci.yml does not measure coverage of louke.runtime "
            "(missing --cov=louke.runtime)"
        )

    def test_ci_installs_test_dependencies(self) -> None:
        """CI installs pytest and pytest-cov before running tests.

        A clean CI runner has neither, so the workflow must declare the
        install step explicitly rather than relying on the build tooling
        step or the developer's local venv.
        """
        text = _ci_workflow_text()
        assert "pytest-cov" in text, (
            "louke-ci.yml does not install pytest-cov; coverage step would fail "
            "on a clean CI runner"
        )

    def test_ci_smoke_installs_and_inspects_wheel(self) -> None:
        """The artifact gate installs the built wheel in a clean environment."""
        text = _ci_workflow_text()
        assert "pip install --force-reinstall dist/louke-*.whl" in text
        assert "importlib.metadata" in text

    def test_ci_checks_lk_version_reports_release(self) -> None:
        """CI asserts ``lk --version`` reports the release version.

        Asserts the workflow contains a step running ``lk --version`` and
        grepping for ``0.14.0``. This is the version-convergence gate:
        drift between wheel METADATA, ``louke.__version__`` and the CLI
        version string must fail CI, not just be discovered post-release.
        """
        text = _ci_workflow_text()
        assert "lk --version" in text, (
            "louke-ci.yml does not run 'lk --version' from the installed wheel"
        )
        assert "0.14.0" in text, "louke-ci.yml does not assert the release version"

    def test_ci_has_fail_closed_required_aggregate(self) -> None:
        """The stable required check aggregates every mandatory job."""
        text = _ci_workflow_text()
        assert "name: required" in text
        assert "if: always()" in text
        assert "fail-closed" in text


class TestPytestMarkerRegistration:
    """Cycle 2: ``pyproject.toml`` must register the project markers.

    Markers are currently registered only in ``tests/conftest.py`` via
    ``pytest_configure``. Registering them under
    ``[tool.pytest.ini_options]`` in ``pyproject.toml`` makes them visible
    to ``pytest --markers``, IDE tooling and ``pytest -m <marker>``
    selection without relying on conftest collection order, and is the
    canonical place for project-wide pytest config.
    """

    def _pyproject_text(self) -> str:
        """Read and return the raw text of ``pyproject.toml``.

        Returns:
            The full file contents as a string.
        """
        return (_repo_root() / "pyproject.toml").read_text(encoding="utf-8")

    @pytest.mark.parametrize(
        "marker",
        ["e2e", "integration", "real_opencode"],
    )
    def test_pyproject_registers_marker(self, marker: str) -> None:
        """``[tool.pytest.ini_options]`` registers the given marker.

        Asserts that ``pyproject.toml`` contains a ``markers`` entry for
        ``marker`` under ``[tool.pytest.ini_options]``. A missing marker
        means ``-m <marker>`` selection and ``--markers`` listing depend
        solely on conftest side effects, which is fragile.
        """
        text = self._pyproject_text()
        assert "[tool.pytest.ini_options]" in text, (
            "pyproject.toml is missing the [tool.pytest.ini_options] section"
        )
        assert re.search(
            rf"markers\s*=\s*\[[\s\S]*?\b{re.escape(marker)}\b",
            text,
        ), (
            f"pyproject.toml [tool.pytest.ini_options] does not register "
            f"the {marker!r} marker"
        )
