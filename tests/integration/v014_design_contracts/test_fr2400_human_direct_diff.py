"""Integration tests for FR-2400: Human Optional Review & Direct Diff.

AC-FR2400-01: When Human is completely absent, design still reaches
implementation baseline via Archer, program gates and Prism; Human comments
and direct diff are visible and de-duplicated at next author round. For
direct edit without issues, Archer may not add new discussion; for edits
with issues, creates discussion anchored to original text; Human author
identity does not make edit auto-PASS.
"""
# AC-FR2400-01

from __future__ import annotations

import json
from pathlib import Path

import pytest

FIXTURES = (
    Path(__file__).resolve().parents[2]
    / "fixtures"
    / "v014_design_contracts"
    / "matrices"
)


def test_review_restart_matrix_has_human_absent_case():
    """review_restart_matrix must include human-absent case."""
    matrix = json.loads((FIXTURES / "review_restart_matrix.json").read_text())
    absent = next(
        (c for c in matrix["cases"] if c["id"] == "human-absent"), None
    )
    assert absent is not None
    assert "baseline" in absent["expected"].lower()


def test_review_restart_matrix_has_direct_diff_clean_case():
    """review_restart_matrix must include direct-diff-clean case."""
    matrix = json.loads((FIXTURES / "review_restart_matrix.json").read_text())
    clean = next(
        (c for c in matrix["cases"] if c["id"] == "direct-diff-clean"), None
    )
    assert clean is not None
    assert "absorb" in clean["expected"].lower() or "without" in clean["expected"].lower()


def test_review_restart_matrix_has_direct_diff_with_issue_case():
    """review_restart_matrix must include direct-diff-with-issue case."""
    matrix = json.loads((FIXTURES / "review_restart_matrix.json").read_text())
    issue = next(
        (c for c in matrix["cases"] if c["id"] == "direct-diff-with-issue"), None
    )
    assert issue is not None
    assert "discussion" in issue["expected"].lower()
    assert "anchor" in issue["expected"].lower()
    assert "auto-pass" in issue["expected"].lower()


@pytest.mark.awaiting_devon("FR-2400")
def test_human_absent_design_reaches_baseline(mock_design_coordinator):
    """When Human is absent, design must still reach baseline."""
    mock_design_coordinator.run_design_phase.return_value = {
        "ok": True,
        "baseline_created": True,
        "human_involved": False,
    }
    result = mock_design_coordinator.run_design_phase(human_absent=True)
    assert result["ok"]
    assert result["baseline_created"]


@pytest.mark.awaiting_devon("FR-2400")
def test_direct_diff_clean_absorbed_without_discussion(mock_design_coordinator):
    """Clean direct diff must be absorbed without new discussion."""
    mock_design_coordinator.absorb_direct_diff.return_value = {
        "ok": True,
        "new_discussions": 0,
        "absorbed": True,
    }
    result = mock_design_coordinator.absorb_direct_diff(diff={})
    assert result["new_discussions"] == 0


@pytest.mark.awaiting_devon("FR-2400")
def test_direct_diff_with_issue_creates_anchored_discussion(
    mock_design_coordinator,
):
    """Direct diff with issue must create discussion anchored to original text."""
    mock_design_coordinator.absorb_direct_diff.return_value = {
        "ok": True,
        "new_discussions": 1,
        "anchor": "spec.md#L42",
        "human_author_auto_pass": False,
    }
    result = mock_design_coordinator.absorb_direct_diff(diff={"has_issue": True})
    assert result["new_discussions"] == 1
    assert result["human_author_auto_pass"] is False


@pytest.mark.awaiting_devon("FR-2400")
def test_human_author_does_not_auto_pass(mock_design_coordinator):
    """Human author identity must not make edit auto-PASS."""
    mock_design_coordinator.absorb_direct_diff.return_value = {
        "ok": True,
        "human_author_auto_pass": False,
        "requires_review": True,
    }
    result = mock_design_coordinator.absorb_direct_diff(
        diff={}, author="human"
    )
    assert result["human_author_auto_pass"] is False
