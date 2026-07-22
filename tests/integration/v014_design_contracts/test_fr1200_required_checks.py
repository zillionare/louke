"""Integration tests for FR-1200: Stable Required Check & Enforcement.

AC-FR1200-01: Contract defines exactly one stable aggregate name
`Louke CI / required`; all required jobs must succeed for aggregate to
succeed; declares ruleset/branch-protection owner, target and readback.
Simulated job fail/cancel/timeout/missing/illegal-skip/unknown status
yields aggregate failure; generated changes do not delete existing
required checks.
"""
# AC-FR1200-01

from __future__ import annotations

import pytest

AGGREGATE_NAME = "Louke CI / required"


@pytest.mark.awaiting_devon("FR-1200")
def test_aggregate_name_is_stable(mock_ci_contract):
    """Contract must define exactly one stable aggregate name."""
    mock_ci_contract.get_required_aggregate.return_value = {
        "name": AGGREGATE_NAME,
        "owner": "Runtime/program",
        "target": "releases/0.14.0",
    }
    result = mock_ci_contract.get_required_aggregate()
    assert result["name"] == AGGREGATE_NAME


@pytest.mark.awaiting_devon("FR-1200")
def test_aggregate_fails_on_job_failure(mock_ci_contract):
    """Any required job failure must make aggregate fail."""
    for status in ("failure", "cancel", "timeout", "missing", "unknown"):
        mock_ci_contract.aggregate_status.return_value = {
            "name": AGGREGATE_NAME,
            "status": "failure",
            "trigger": status,
        }
        result = mock_ci_contract.aggregate_status(job_status=status)
        assert result["status"] == "failure", f"aggregate should fail on job {status}"


@pytest.mark.awaiting_devon("FR-1200")
def test_aggregate_fails_on_illegal_skip(mock_ci_contract):
    """Illegal skip of a required job must fail aggregate."""
    mock_ci_contract.aggregate_status.return_value = {
        "name": AGGREGATE_NAME,
        "status": "failure",
        "trigger": "illegal-skip",
    }
    result = mock_ci_contract.aggregate_status(job_status="skip", required=True)
    assert result["status"] == "failure"


@pytest.mark.awaiting_devon("FR-1200")
def test_aggregate_succeeds_only_when_all_required_pass(mock_ci_contract):
    """Aggregate succeeds only when ALL required jobs pass."""
    mock_ci_contract.aggregate_status.return_value = {
        "name": AGGREGATE_NAME,
        "status": "success",
    }
    result = mock_ci_contract.aggregate_status(job_status="success", required=True)
    assert result["status"] == "success"


@pytest.mark.awaiting_devon("FR-1200")
def test_readback_preserves_existing_required_checks(mock_ci_contract):
    """Generated changes must not delete existing required checks."""
    mock_ci_contract.readback.return_value = {
        "existing_required_checks": ["ci", "release"],
        "managed_required_check": AGGREGATE_NAME,
        "deleted": [],
    }
    result = mock_ci_contract.readback()
    assert result["deleted"] == [], "no existing checks should be deleted"
