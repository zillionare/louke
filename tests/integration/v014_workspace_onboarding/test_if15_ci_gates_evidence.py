"""IF-15: CI gates and evidence contract.

AC-FR1501-01, AC-NFR0501-01

Integration tests verify that the CI traceability tool discovers v0.14-004
AC references in the integration test directory, and that the agent
boundary enforcement prevents Maestro from being created as a new agent.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


from louke.web.agent_boundaries import can_create_agent, session_kind

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_maestro_cannot_be_created_as_new_agent():
    """AC-FR1501-01: Maestro cannot be created as a new specialist agent."""
    # AC-FR1501-01
    assert can_create_agent("maestro") is False


def test_guide_cannot_be_created_as_new_agent():
    """AC-FR1501-01: Guide cannot appear as a new agent in Agent picker."""
    # AC-FR1501-01
    assert can_create_agent("guide") is False


def test_specialist_agent_can_be_created():
    """AC-FR1501-01: specialist agents like Scribe, Archer, Devon can be created."""
    # AC-FR1501-01
    assert can_create_agent("Scribe") is True
    assert can_create_agent("Archer") is True
    assert can_create_agent("Devon") is True


def test_historical_maestro_is_read_only():
    """AC-FR1501-01: historical Maestro session is read-only."""
    # AC-FR1501-01
    kind, read_only = session_kind("Maestro", historical=True)
    assert kind == "historical_maestro"
    assert read_only is True


def test_specialist_agent_session_kind():
    """AC-FR1501-01: specialist agent has correct session kind."""
    # AC-FR1501-01
    kind, read_only = session_kind("scribe", historical=False)
    assert kind == "specialist_agent"


def test_integration_tests_have_ac_references():
    """AC-NFR0501-01: integration tests contain AC-FR/NFR references for traceability."""
    # AC-NFR0501-01
    test_dir = REPO_ROOT / "tests" / "integration" / "v014_workspace_onboarding"
    py_files = list(test_dir.glob("test_if*.py"))
    assert len(py_files) >= 14  # IF-01 through IF-15 minus this file

    all_content = ""
    for f in py_files:
        all_content += f.read_text(encoding="utf-8")
    assert "AC-FR" in all_content
    assert "AC-NFR" in all_content


def test_traceability_tool_finds_v014_004_acs():
    """AC-NFR0501-01: traceability scanner discovers v0.14-004 AC references.

    The locked Acceptance baseline contains 44 unique ACs; the host
    CI scanner (``tools/check_ac_traceability.py``) is invoked with
    ``--expected-count 44`` so the dedicated v0.14-004 gate matches
    the canonical count.
    """
    # AC-NFR0501-01
    acceptance = (
        REPO_ROOT
        / ".louke/project/specs/v0.14-004-workspace-onboarding-workflow-status/acceptance.md"
    )
    result = subprocess.run(
        [
            sys.executable,
            "tools/check_ac_traceability.py",
            "--acceptance",
            str(acceptance),
            "--tests",
            "tests",
            "--expected-count",
            "44",
        ],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        timeout=30,
    )
    assert result.returncode == 0, (
        f"traceability scan failed:\n{result.stdout}\n{result.stderr}"
    )
    assert "44/44 covered" in result.stdout
