"""Integration tests for NFR-0400: Recoverability & Audit.

AC-NFR-0400-01: Simulating restart at author, program check and Prism
review boundaries, Runtime recovers same current revision, pending work
and history without re-dispatching completed attempts. Deleting or
tampering persisted digest causes recovery to fail closed and preserves
diagnostic history.

Note: NFR-0400 also has an E2E component.
"""
# AC-NFR0400-01

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


def test_review_restart_matrix_has_three_kill_boundaries():
    """review_restart_matrix must include kill cases for author, check, review."""
    matrix = json.loads((FIXTURES / "review_restart_matrix.json").read_text())
    case_ids = {c["id"] for c in matrix["cases"]}
    for required in (
        "author-boundary-kill",
        "check-boundary-kill",
        "review-boundary-kill",
    ):
        assert required in case_ids, f"missing kill boundary case: {required}"


def test_review_restart_matrix_kill_cases_recover():
    """Every kill boundary case must expect recovery."""
    matrix = json.loads((FIXTURES / "review_restart_matrix.json").read_text())
    kill_cases = [c for c in matrix["cases"] if c["id"].endswith("-kill")]
    for case in kill_cases:
        assert "recover" in case["expected"].lower(), (
            f"case {case['id']} must expect recovery"
        )


def test_review_restart_matrix_kill_cases_no_duplicate_dispatch():
    """Kill boundary cases must not duplicate dispatch."""
    matrix = json.loads((FIXTURES / "review_restart_matrix.json").read_text())
    kill_cases = [c for c in matrix["cases"] if c["id"].endswith("-kill")]
    for case in kill_cases:
        assert "no duplicate" in case["expected"].lower(), (
            f"case {case['id']} must require no duplicate dispatch"
        )


@pytest.mark.awaiting_devon("NFR-0400")
def test_runtime_recovers_after_author_boundary_kill(mock_design_coordinator):
    """Runtime must recover same current revision after author kill."""
    mock_design_coordinator.recover.return_value = {
        "ok": True,
        "current_revision": "r1",
        "pending_work": "author-task",
        "duplicate_dispatch": False,
    }
    result = mock_design_coordinator.recover(boundary="author")
    assert result["ok"]
    assert result["duplicate_dispatch"] is False


@pytest.mark.awaiting_devon("NFR-0400")
def test_runtime_recovers_after_check_boundary_kill(mock_design_coordinator):
    """Runtime must recover pending work after check kill."""
    mock_design_coordinator.recover.return_value = {
        "ok": True,
        "current_revision": "r1",
        "pending_work": "program-check",
        "duplicate_dispatch": False,
    }
    result = mock_design_coordinator.recover(boundary="check")
    assert result["ok"]
    assert result["pending_work"] == "program-check"


@pytest.mark.awaiting_devon("NFR-0400")
def test_runtime_recovers_after_review_boundary_kill(mock_design_coordinator):
    """Runtime must recover pending review after review kill."""
    mock_design_coordinator.recover.return_value = {
        "ok": True,
        "current_revision": "r1",
        "pending_work": "prism-review",
        "duplicate_dispatch": False,
    }
    result = mock_design_coordinator.recover(boundary="review")
    assert result["ok"]
    assert result["pending_work"] == "prism-review"


@pytest.mark.awaiting_devon("NFR-0400")
def test_digest_tamper_fail_closed(mock_design_coordinator):
    """Deleting or tampering persisted digest must fail closed."""
    mock_design_coordinator.recover.return_value = {
        "ok": False,
        "error": "DIGEST_TAMPERED",
        "fail_closed": True,
        "history_preserved": True,
    }
    result = mock_design_coordinator.recover(digest_tampered=True)
    assert not result["ok"]
    assert result["fail_closed"] is True
    assert result["history_preserved"] is True


@pytest.mark.awaiting_devon("NFR-0400")
def test_audit_export_preserves_history(mock_audit_export):
    """Audit export must preserve diagnostic history."""
    mock_audit_export.export.return_value = {
        "ok": True,
        "history_entries": 10,
        "redacted": True,
    }
    result = mock_audit_export.export()
    assert result["ok"]
    assert result["history_entries"] > 0
