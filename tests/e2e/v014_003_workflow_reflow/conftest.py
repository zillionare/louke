"""Shared pytest configuration for v0.14-003 workflow-reflow-impl e2e tests.

Per spec-003 test-plan.md §3.2: E2E tests cover ONLY normal paths (user
journeys); boundary/error/exception cases belong in integration tests.
Per §2.3: E2E runner = ``tests/e2e/run-project-venv e2e --profile all
--runtime both``. The tests below call Devon's real ``louke.runtime.*``
modules to exercise end-to-end user journeys (M-IMPL -> M-TEST ->
M-VERIFY -> M-RELEASE -> M-PUBLISH -> M-MILESTONE and sub-journeys).

Each journey test references the AC IDs it covers (at minimum the
entry/exit AC for that journey).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SPEC_ROOT = (
    REPO_ROOT / ".louke" / "project" / "specs" / "v0.14-003-workflow-reflow-impl"
)


def _read_text(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"Required spec file missing: {path}")
    return path.read_text(encoding="utf-8")


def in_venv() -> bool:
    """Return True if the current Python is running inside a managed env."""
    if hasattr(sys, "real_prefix"):
        return True
    if sys.prefix != sys.base_prefix:
        return True
    conda_prefix = os.environ.get("CONDA_PREFIX")
    if conda_prefix:
        executable = Path(sys.executable).resolve()
        try:
            executable.relative_to(Path(conda_prefix).resolve())
            return True
        except ValueError:
            # AC-NFR0500-01: executable not inside conda prefix; continue
            # checking other managed-environment markers below.
            pass
    executable = Path(sys.executable).resolve()
    if ".louke" in executable.parts and "venv" in executable.parts:
        return True
    if os.environ.get("VIRTUAL_ENV"):
        return True
    return False


@pytest.fixture(scope="session")
def venv_python() -> str:
    """Return the venv Python executable path for subprocess calls."""
    if not in_venv():
        pytest.skip(
            # AC-NFR0500-01: e2e tests require a venv to avoid polluting system Python.
            "E2E test requires a virtual environment (AC-NFR0500-01). "
            "Create one with: python -m venv .venv && source .venv/bin/activate "
            "&& pip install -e '.[dev]', then re-run pytest."
        )
    return sys.executable


@pytest.fixture(scope="session")
def spec_root() -> Path:
    """Path to the v0.14-003 spec directory."""
    return SPEC_ROOT


@pytest.fixture(scope="session")
def acceptance_md() -> str:
    """``acceptance.md`` contents."""
    return _read_text(SPEC_ROOT / "acceptance.md")


def pytest_configure(config):
    """Register v0.14-003 specific markers."""
    config.addinivalue_line(
        "markers",
        "v014_003_e2e: v0.14-003 workflow-reflow-impl end-to-end journey test",
    )


def pytest_collection_modifyitems(config, items):
    """Auto-mark every test under tests/e2e/v014_003_workflow_reflow/."""
    for item in items:
        if "tests/e2e/v014_003_workflow_reflow" in str(item.fspath):
            item.add_marker(pytest.mark.e2e)
            item.add_marker(pytest.mark.v014_003_e2e)
