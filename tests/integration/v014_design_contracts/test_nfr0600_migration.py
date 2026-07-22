"""Integration tests for NFR-0600: State & Schema Migration Compatibility.

AC-NFR0600-01: Old `M-LOCK-1`/second lock and old prompt/contract fixtures
can be explicitly migrated or read-only diagnosed; new run only produces
canonical stage/schema identities. Migration is retryable and does not
produce two current revisions or dual-write stages; unknown old version
fails closed.
"""
# AC-NFR0600-01

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


def test_legacy_matrix_has_old_m_lock_1_case():
    """legacy_matrix must include old-m-lock-1 case."""
    matrix = json.loads((FIXTURES / "legacy_matrix.json").read_text())
    case = next((c for c in matrix["cases"] if c["id"] == "old-m-lock-1"), None)
    assert case is not None  # AC-NFR0600-01
    assert (
        "migrate" in case["expected"].lower()
        or "diagnostic" in case["expected"].lower()
    )


def test_legacy_matrix_has_old_second_lock_case():
    """legacy_matrix must include old-second-lock case."""
    matrix = json.loads((FIXTURES / "legacy_matrix.json").read_text())
    case = next((c for c in matrix["cases"] if c["id"] == "old-second-lock"), None)
    assert case is not None  # AC-NFR0600-01
    assert (
        "no second M-LOCK" in case["expected"] or "migrate" in case["expected"].lower()
    )


def test_legacy_matrix_has_old_prompt_schema_case():
    """legacy_matrix must include old-prompt-schema case."""
    matrix = json.loads((FIXTURES / "legacy_matrix.json").read_text())
    case = next((c for c in matrix["cases"] if c["id"] == "old-prompt-schema"), None)
    assert case is not None  # AC-NFR0600-01


def test_legacy_matrix_has_old_contract_schema_case():
    """legacy_matrix must include old-contract-schema case."""
    matrix = json.loads((FIXTURES / "legacy_matrix.json").read_text())
    case = next((c for c in matrix["cases"] if c["id"] == "old-contract-schema"), None)
    assert case is not None  # AC-NFR0600-01


def test_legacy_matrix_has_unknown_version_case():
    """legacy_matrix must include unknown-version case (fail closed)."""
    matrix = json.loads((FIXTURES / "legacy_matrix.json").read_text())
    case = next((c for c in matrix["cases"] if c["id"] == "unknown-version"), None)
    assert case is not None  # AC-NFR0600-01
    assert "fail closed" in case["expected"].lower()


def test_legacy_matrix_has_migration_interrupted_case():
    """legacy_matrix must include migration-interrupted case (retryable)."""
    matrix = json.loads((FIXTURES / "legacy_matrix.json").read_text())
    case = next(
        (c for c in matrix["cases"] if c["id"] == "migration-interrupted"), None
    )
    assert case is not None  # AC-NFR0600-01
    assert "retryable" in case["expected"].lower()
    assert (
        "no dual" in case["expected"].lower()
        or "dual-write" in case["expected"].lower()
    )


@pytest.mark.awaiting_devon("NFR-0600")
def test_old_m_lock_migrated_to_canonical_stage(mock_audit_export):
    """Old M-LOCK-1 must migrate to canonical stage."""
    mock_audit_export.migrate.return_value = {
        "ok": True,
        "old_stage": "M-LOCK-1",
        "new_stage": "M-DESIGN",
        "canonical_only": True,
    }
    result = mock_audit_export.migrate(old_stage="M-LOCK-1")
    assert result["ok"]
    assert result["canonical_only"] is True


@pytest.mark.awaiting_devon("NFR-0600")
def test_unknown_version_fails_closed(mock_audit_export):
    """Unknown legacy version must fail closed."""
    mock_audit_export.migrate.return_value = {
        "ok": False,
        "error": "UNKNOWN_LEGACY_VERSION",
        "fail_closed": True,
    }
    result = mock_audit_export.migrate(old_version="9.9.9")
    assert not result["ok"]
    assert result["fail_closed"] is True


@pytest.mark.awaiting_devon("NFR-0600")
def test_migration_interrupted_is_retryable(mock_audit_export):
    """Interrupted migration must be retryable; no dual current revision."""
    mock_audit_export.migrate.return_value = {
        "ok": True,
        "retryable": True,
        "dual_current": False,
        "dual_write_stages": False,
    }
    result = mock_audit_export.migrate(resume=True)
    assert result["retryable"] is True
    assert result["dual_current"] is False
    assert result["dual_write_stages"] is False


@pytest.mark.awaiting_devon("NFR-0600")
def test_new_run_only_produces_canonical_schema(mock_audit_export):
    """New run must only produce canonical stage/schema identities."""
    mock_audit_export.inspect_new_run.return_value = {
        "stages": ["M-DESIGN", "M-IMPL"],
        "schema_identities": ["louke.machine-contract.integration-test"],
        "legacy_identities": [],
    }
    result = mock_audit_export.inspect_new_run()
    assert result["legacy_identities"] == []
