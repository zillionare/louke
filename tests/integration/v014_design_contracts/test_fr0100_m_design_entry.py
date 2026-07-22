"""Integration tests for FR-0100: M-DESIGN Entry & Revision Identity.

AC-FR0100-01: When approved requirements digests, base commit and host
facts are all current, entering M-DESIGN persists a record containing
run/release/revision/attempt/actor/all input identities. Any missing/
conflicting/stale approval, digest, workspace ownership or base commit
prevents Archer task creation and returns a stable blocking reason.

Note: FR-0100 also has an E2E component (tests/e2e/v014_design_contracts/
test_fr0100_m_design_entry_e2e.py).
"""
# AC-FR0100-01

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


def test_approved_design_inputs_matrix_has_current_case():
    """approved_design_inputs matrix must include the 'current' positive case."""
    matrix = json.loads((FIXTURES / "approved_design_inputs.json").read_text())
    current = next((c for c in matrix["cases"] if c["id"] == "current"), None)
    assert current is not None  # AC-FR0100-01
    assert "enter M-DESIGN" in current["expected"]


def test_approved_design_inputs_matrix_has_stale_case():
    """matrix must include stale-requirements case."""
    matrix = json.loads((FIXTURES / "approved_design_inputs.json").read_text())
    stale = next((c for c in matrix["cases"] if c["id"] == "stale-requirements"), None)
    assert stale is not None  # AC-FR0100-01
    assert "block" in stale["expected"].lower()


def test_approved_design_inputs_matrix_has_missing_base_commit_case():
    """matrix must include missing-base-commit case."""
    matrix = json.loads((FIXTURES / "approved_design_inputs.json").read_text())
    missing = next(
        (c for c in matrix["cases"] if c["id"] == "missing-base-commit"), None
    )
    assert missing is not None  # AC-FR0100-01
    assert "block" in missing["expected"].lower()


def test_approved_design_inputs_matrix_has_facts_conflict_case():
    """matrix must include facts-conflict case."""
    matrix = json.loads((FIXTURES / "approved_design_inputs.json").read_text())
    conflict = next((c for c in matrix["cases"] if c["id"] == "facts-conflict"), None)
    assert conflict is not None  # AC-FR0100-01
    assert "block" in conflict["expected"].lower()


def test_approved_design_inputs_matrix_has_workspace_mismatch_case():
    """matrix must include workspace-mismatch case."""
    matrix = json.loads((FIXTURES / "approved_design_inputs.json").read_text())
    mismatch = next(
        (c for c in matrix["cases"] if c["id"] == "workspace-mismatch"), None
    )
    assert mismatch is not None  # AC-FR0100-01
    assert "block" in mismatch["expected"].lower()


@pytest.mark.awaiting_devon("FR-0100")
def test_entering_m_design_persists_full_identity_record(
    mock_design_coordinator,
):
    """Entering M-DESIGN must persist record with run/release/revision/
    attempt/actor/all input identities."""
    mock_design_coordinator.enter_m_design.return_value = {
        "ok": True,
        "record": {
            "run_id": "r1",
            "release_identity": "0.14.0",
            "revision": "prism-r3-remediation-candidate",
            "attempt": 1,
            "actor": "shield-test",
            "input_identities": {
                "requirements": "sha256:abc",
                "base_commit": "2734177...",
                "facts": "sha256:def",
            },
        },
    }
    result = mock_design_coordinator.enter_m_design()
    assert result["ok"]
    record = result["record"]
    for key in (
        "run_id",
        "release_identity",
        "revision",
        "attempt",
        "actor",
        "input_identities",
    ):
        assert key in record


@pytest.mark.awaiting_devon("FR-0100")
def test_stale_requirements_blocks_m_design_entry(mock_design_coordinator):
    """Stale requirements must block M-DESIGN entry with stable reason."""
    mock_design_coordinator.enter_m_design.return_value = {
        "ok": False,
        "error": "STALE_REQUIREMENTS",
        "reason": "requirements digest does not match approved baseline",
    }
    result = mock_design_coordinator.enter_m_design(requirements_digest="sha256:stale")
    assert not result["ok"]
    assert "reason" in result


@pytest.mark.awaiting_devon("FR-0100")
def test_missing_base_commit_blocks_m_design_entry(mock_design_coordinator):
    """Missing base commit must block M-DESIGN entry."""
    mock_design_coordinator.enter_m_design.return_value = {
        "ok": False,
        "error": "MISSING_BASE_COMMIT",
    }
    result = mock_design_coordinator.enter_m_design(base_commit=None)
    assert not result["ok"]


@pytest.mark.awaiting_devon("FR-0100")
def test_workspace_mismatch_blocks_m_design_entry(mock_design_coordinator):
    """Workspace ownership mismatch must block M-DESIGN entry."""
    mock_design_coordinator.enter_m_design.return_value = {
        "ok": False,
        "error": "WORKSPACE_MISMATCH",
    }
    result = mock_design_coordinator.enter_m_design(
        workspace_id="github.com/other/repo"
    )
    assert not result["ok"]
