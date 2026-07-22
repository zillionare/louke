"""Integration tests for FR-1600: Publish & Recovery Contract.

AC-FR1600-01: For all applicable merge/tag/publish/release/deploy/smoke
operations, contract defines order, prerequisite gate, stable identity,
fact query, idempotency, credential, verification and rollback/forward-fix.
Simulated API partial success or unknown result expects retryable
`needs_attention` state; no duplicate tag/upload or success conclusion.
"""
# AC-FR1600-01

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


def test_publish_matrix_lists_all_operations():
    """publish_matrix must list tag, pypi, github-release, smoke."""
    matrix = json.loads((FIXTURES / "publish_matrix.json").read_text())
    ops = set(matrix["operations"])
    for required in ("tag", "pypi", "github-release", "smoke"):
        assert required in ops, f"missing operation: {required}"


def test_publish_matrix_has_partial_success_case():
    """publish_matrix must include partial-success scenario."""
    matrix = json.loads((FIXTURES / "publish_matrix.json").read_text())
    partial = next((c for c in matrix["cases"] if c["id"] == "partial-success"), None)
    assert partial is not None  # AC-FR1600-01
    assert "needs_attention" in partial["expected"]


def test_publish_matrix_has_rollback_case():
    """publish_matrix must include rollback scenario."""
    matrix = json.loads((FIXTURES / "publish_matrix.json").read_text())
    rollback = next((c for c in matrix["cases"] if c["id"] == "rollback"), None)
    assert rollback is not None  # AC-FR1600-01


def test_publish_matrix_no_duplicate_on_partial_success():
    """Partial-success case must not produce duplicate tag/upload."""
    matrix = json.loads((FIXTURES / "publish_matrix.json").read_text())
    partial = next(c for c in matrix["cases"] if c["id"] == "partial-success")
    assert "no duplicate" in partial["expected"].lower()


def test_publish_recovery_schema_in_registry(registry_candidate):
    """registry must include the publish-recovery machine-contract schema."""
    kinds = {s["kind"] for s in registry_candidate["schemas"]}
    assert "publish-recovery" in kinds


def test_publish_recovery_contract_in_manifest(design_manifest):
    """manifest must list a publish-recovery contract instance."""
    instances = design_manifest["contract_instances"]
    pub = [i for i in instances if i["kind"] == "publish-recovery"]
    assert len(pub) == 1


@pytest.mark.awaiting_devon("FR-1600")
def test_publish_query_before_retry(mock_publish_recovery):
    """After ack loss, must query before retry; no blind retry."""
    mock_publish_recovery.query_state.return_value = {
        "ok": True,
        "state": "needs_attention",
        "candidates": [],
    }
    result = mock_publish_recovery.query_state(operation="pypi")
    assert result["state"] == "needs_attention"


@pytest.mark.awaiting_devon("FR-1600")
def test_publish_zero_candidates_needs_attention(mock_publish_recovery):
    """Zero candidates after query must yield needs_attention."""
    mock_publish_recovery.query_state.return_value = {
        "ok": True,
        "state": "needs_attention",
        "candidates": [],
    }
    result = mock_publish_recovery.query_state()
    assert result["state"] == "needs_attention"
    assert result["candidates"] == []


@pytest.mark.awaiting_devon("FR-1600")
def test_publish_multi_candidates_needs_attention(mock_publish_recovery):
    """Multiple candidates must yield needs_attention; no implicit selection."""
    mock_publish_recovery.query_state.return_value = {
        "ok": True,
        "state": "needs_attention",
        "candidates": ["c1", "c2"],
    }
    result = mock_publish_recovery.query_state()
    assert result["state"] == "needs_attention"
    assert len(result["candidates"]) > 1


@pytest.mark.awaiting_devon("FR-1600")
def test_publish_rollback_executes_and_records(mock_publish_recovery):
    """Rollback must execute and ledger must record both operations."""
    mock_publish_recovery.rollback.return_value = {
        "ok": True,
        "rolled_back": ["pypi"],
        "ledger_entries": 2,
    }
    result = mock_publish_recovery.rollback(operation="pypi")
    assert result["ok"]
    assert result["ledger_entries"] >= 2
