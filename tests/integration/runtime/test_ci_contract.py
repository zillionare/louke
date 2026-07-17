"""CI contract test asserting the v0.13.1 CI gates.

S6 (#179): the main ``.github/workflows/ci.yml`` must, on every push/PR,
actually run the v0.12 Python behavior gates from the current checkout.
Before this change CI only ran pre-commit + build + ``lk --help`` + BATS;
it never executed pytest, never measured coverage, and never proved the
built wheel's v0.12 subpackages import or that ``lk --version`` reports
the release version (gap-analysis §3 P0-3 / Batch 4 / §6 #8).

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
    """Return the path to the primary CI workflow file.

    Returns:
        ``<repo_root>/.github/workflows/ci.yml``.
    """
    return _repo_root() / ".github" / "workflows" / "ci.yml"


def _ci_workflow_text() -> str:
    """Read and return the raw text of ``ci.yml``.

    Returns:
        The full file contents as a string.

    Raises:
        FileNotFoundError: If ``ci.yml`` does not exist (the contract test
            then fails with a clear message at the call site).
    """
    path = _ci_workflow_path()
    return path.read_text(encoding="utf-8")


class TestCIWorkflowContract:
    """Static contract over ``.github/workflows/ci.yml`` for v0.13.1.

    Each assertion maps to a gap-analysis §3 P0-3 / Batch 4 acceptance
    criterion: the workflow must run unit+integration+ground_truth with
    coverage from the current checkout, must smoke-import the v0.12
    subpackages from the installed wheel, and must verify ``lk --version``.
    None of these may be removed to make CI green; the coverage gate must
    not be lowered (§6 #8).
    """

    def test_ci_workflow_file_exists(self) -> None:
        """``ci.yml`` exists at the conventional GitHub Actions path."""
        assert _ci_workflow_path().exists(), (
            f"expected CI workflow at {_ci_workflow_path()} but it is absent"
        )

    def test_ci_runs_pytest_unit_integration_ground_truth(self) -> None:
        """CI runs pytest over unit, integration and ground_truth layers.

        Asserts the workflow contains a step whose ``run`` invokes
        ``pytest tests/unit tests/integration tests/ground_truth``. Before
        S6 the workflow never ran pytest at all (gap-analysis Batch 0
        §0.9: ``contains 'pytest': False``), so unit/integration/ground_truth
        regressions were invisible to CI.
        """
        text = _ci_workflow_text()
        pattern = r"pytest\s+tests/unit\s+tests/integration\s+tests/ground_truth"
        assert re.search(pattern, text), (
            "ci.yml does not contain a step running "
            "'pytest tests/unit tests/integration tests/ground_truth'"
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
            "ci.yml does not measure coverage of louke.runtime "
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
            "ci.yml does not install pytest-cov; coverage step would fail "
            "on a clean CI runner"
        )

    def test_ci_smoke_imports_v012_subpackages_from_wheel(self) -> None:
        """CI smoke-imports every v0.12 subpackage from the installed wheel.

        Asserts the workflow contains a step running
        ``import louke.runtime, louke.opencode, louke.web.api,
        louke.web.pages, louke.cli_v12``. This is the S1/S7 packaging
        gate (gap-analysis §3 P0-1): a wheel that drops any subpackage
        would still pass ``lk --help`` but fails here.
        """
        text = _ci_workflow_text()
        for module in (
            "louke.runtime",
            "louke.opencode",
            "louke.web.api",
            "louke.web.pages",
            "louke.cli_v12",
        ):
            assert module in text, (
                f"ci.yml package-smoke step does not import {module}; "
                f"a wheel missing this subpackage would not be caught"
            )

    def test_ci_checks_lk_version_reports_release(self) -> None:
        """CI asserts ``lk --version`` reports the release version.

        Asserts the workflow contains a step running ``lk --version`` and
        grepping for ``0.13.1``. This is the version-convergence gate:
        drift between wheel METADATA, ``louke.__version__`` and the CLI
        version string must fail CI, not just be discovered post-release.
        """
        text = _ci_workflow_text()
        assert "lk --version" in text, (
            "ci.yml does not run 'lk --version' from the installed wheel"
        )
        assert "0.13.1" in text, "ci.yml does not assert lk --version reports 0.13.1"

    def test_ci_retains_bats_suite(self) -> None:
        """CI retains the legacy BATS suite (v0.5 commit-policy).

        gap-analysis Batch 4: the BATS job must be preserved as legacy
        pipeline regression coverage; it must not be deleted when adding
        the pytest/coverage gates.
        """
        text = _ci_workflow_text()
        assert "bats" in text.lower(), (
            "ci.yml no longer references bats; the legacy BATS regression "
            "suite must be retained (gap-analysis Batch 4)"
        )


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
