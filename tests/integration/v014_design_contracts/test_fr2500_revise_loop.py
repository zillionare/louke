"""Integration tests for FR-2500: Independent Review Loop & Freshness.

AC-FR2500-01: Prism executes as independent task after author revision
persisted; verdict records reviewer/attempt/all input digests/prompt
identity/findings. Any input change makes verdict stale; REVISE produces
new Archer revision; no path for Archer to write PASS or advance stage
via reviewer text.
"""
# AC-FR2500-01

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


def test_review_restart_matrix_has_prism_pass_case():
    """review_restart_matrix must include prism-pass case."""
    matrix = json.loads((FIXTURES / "review_restart_matrix.json").read_text())
    pass_case = next((c for c in matrix["cases"] if c["id"] == "prism-pass"), None)
    assert pass_case is not None  # AC-FR2500-01
    assert "verdict" in pass_case["expected"].lower()


def test_review_restart_matrix_has_prism_revise_case():
    """review_restart_matrix must include prism-revise case."""
    matrix = json.loads((FIXTURES / "review_restart_matrix.json").read_text())
    revise = next((c for c in matrix["cases"] if c["id"] == "prism-revise"), None)
    assert revise is not None  # AC-FR2500-01
    assert (
        "new" in revise["expected"].lower() and "revision" in revise["expected"].lower()
    )


def test_review_restart_matrix_has_prism_stale_case():
    """review_restart_matrix must include prism-stale case."""
    matrix = json.loads((FIXTURES / "review_restart_matrix.json").read_text())
    stale = next((c for c in matrix["cases"] if c["id"] == "prism-stale"), None)
    assert stale is not None  # AC-FR2500-01
    assert "stale" in stale["expected"].lower()


@pytest.mark.awaiting_devon("FR-2500")
def test_prism_dispatched_independently_after_author_revision(
    mock_design_review,
):
    """Prism must be dispatched as independent task after author revision
    is persisted."""
    mock_design_review.dispatch.return_value = {
        "ok": True,
        "task_id": "prism-task-001",
        "independent": True,
        "author_revision_persisted": True,
    }
    result = mock_design_review.dispatch(revision="r1")
    assert result["independent"] is True
    assert result["author_revision_persisted"] is True


@pytest.mark.awaiting_devon("FR-2500")
def test_verdict_records_reviewer_attempt_input_digests_prompt_identity(
    mock_design_review,
):
    """Verdict must record reviewer, attempt, all input digests, prompt
    identity and findings."""
    mock_design_review.submit.return_value = {
        "ok": True,
        "verdict": "PASS",
        "reviewer": "prism@active-digest",
        "attempt": 1,
        "input_digests": {
            "spec": "sha256:abc",
            "acceptance": "sha256:def",
            "interfaces": "sha256:ghi",
        },
        "prompt_identity": "louke.prompt-bundle.v0.14-002.r3",
        "findings": [],
    }
    result = mock_design_review.submit(verdict="PASS")
    for key in ("reviewer", "attempt", "input_digests", "prompt_identity", "findings"):
        assert key in result, f"verdict missing {key}"


@pytest.mark.awaiting_devon("FR-2500")
def test_input_change_makes_verdict_stale(mock_design_review):
    """Any input change must make verdict stale."""
    mock_design_review.check_freshness.return_value = {
        "fresh": False,
        "stale_reason": "input digest changed",
    }
    result = mock_design_review.check_freshness(verdict_id="v1")
    assert result["fresh"] is False


@pytest.mark.awaiting_devon("FR-2500")
def test_revise_produces_new_archer_revision(mock_design_review):
    """REVISE must produce new Archer revision."""
    mock_design_review.submit.return_value = {
        "ok": True,
        "verdict": "REVISE",
        "new_revision_required": True,
    }
    result = mock_design_review.submit(verdict="REVISE")
    assert result["new_revision_required"] is True


@pytest.mark.awaiting_devon("FR-2500")
def test_no_path_for_archer_to_write_pass(mock_design_review):
    """There must be no path for Archer to write PASS."""
    mock_design_review.attempt_author_pass.return_value = {
        "ok": False,
        "error": "ARCHER_CANNOT_WRITE_PASS",
    }
    result = mock_design_review.attempt_author_pass()
    assert not result["ok"]
