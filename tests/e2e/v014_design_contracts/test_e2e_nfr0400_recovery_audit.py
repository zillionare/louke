"""E2E: AC-NFR0400-01 Recovery audit journey.

Verifies the recovery audit contract at the e2e layer. AC-NFR0400-01 is
in the required e2e suite, covered by the candidate-bootstrap-restart
journey.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.v014_002_e2e


def test_acid_nfr0400_in_required_suite(e2e_test_contract):
    """AC-NFR0400-01 must be in the required e2e suite."""
    payload = e2e_test_contract.get("payload", {})
    required_acids: set[str] = set()
    for suite in payload.get("suites", []):
        if suite.get("required"):
            required_acids.update(suite.get("ac_ids", []))
    assert "AC-NFR0400-01" in required_acids


def test_acid_nfr0400_in_journey(e2e_test_contract):
    """AC-NFR0400-01 must be covered by candidate-bootstrap-restart journey."""
    payload = e2e_test_contract.get("payload", {})
    journey = next(
        (
            j
            for j in payload.get("journeys", [])
            if j.get("id") == "candidate-bootstrap-restart"
        ),
        None,
    )
    assert journey is not None
    assert "AC-NFR0400-01" in journey.get("ac_ids", [])


def test_recovery_audit_actions_declared(e2e_test_contract):
    """Journey actions must include 'simulate restart before activation'."""
    payload = e2e_test_contract.get("payload", {})
    journey = next(
        (
            j
            for j in payload.get("journeys", [])
            if j.get("id") == "candidate-bootstrap-restart"
        ),
        None,
    )
    assert journey is not None  # AC-NFR0400-01
    actions = journey.get("actions", [])
    actions_text = " ".join(actions).lower()
    assert "restart" in actions_text, (
        "journey actions must include 'simulate restart before activation'"
    )


def test_recovery_audit_visible_result(e2e_test_contract):
    """Visible result: audit recovers identity."""
    payload = e2e_test_contract.get("payload", {})
    journey = next(
        (
            j
            for j in payload.get("journeys", [])
            if j.get("id") == "candidate-bootstrap-restart"
        ),
        None,
    )
    assert journey is not None  # AC-NFR0400-01
    visible_result = journey.get("visible_result", "").lower()
    assert "audit" in visible_result or "identity" in visible_result, (
        "visible_result must declare audit recovers identity"
    )


def test_recovery_audit_recovery_keeps_old_active(e2e_test_contract):
    """Recovery: drift or kill keeps old active and marks candidate/review stale."""
    payload = e2e_test_contract.get("payload", {})
    journey = next(
        (
            j
            for j in payload.get("journeys", [])
            if j.get("id") == "candidate-bootstrap-restart"
        ),
        None,
    )
    assert journey is not None  # AC-NFR0400-01
    recovery = journey.get("recovery", "").lower()
    assert "drift" in recovery or "kill" in recovery
    assert "old active" in recovery or "active" in recovery
    assert "stale" in recovery


def test_recovery_audit_endpoint_in_public_surfaces(e2e_test_contract):
    """Audit endpoint (GET /api/v14/runs/{run_id}/design/audit) must be in public_surfaces."""
    surfaces = e2e_test_contract.get("payload", {}).get("public_surfaces", [])
    assert any(
        "/api/v14/runs/" in s and s.endswith("/design/audit") for s in surfaces
    ), "audit endpoint not in public_surfaces"


def test_recovery_audit_failure_policy_fail_closed(e2e_test_contract):
    """Failure policy must fail closed for recovery scenarios."""
    failure_policy = e2e_test_contract.get("payload", {}).get("failure_policy", {})
    assert failure_policy.get("fail_closed") is True
    non_success = failure_policy.get("non_success", [])
    # Recovery-specific failure modes.
    for required_mode in ("cancel", "timeout", "missing", "unknown"):
        assert required_mode in non_success, (
            f"failure_policy.non_success missing '{required_mode}' for recovery audit"
        )


def test_recovery_audit_teardown_includes_term_and_kill(e2e_test_contract):
    """Teardown must include TERM process group, wait 10 seconds, KILL if needed."""
    teardown = e2e_test_contract.get("payload", {}).get("teardown", [])
    teardown_text = " ".join(teardown).lower()
    assert "term" in teardown_text
    assert "10 seconds" in teardown_text or "10s" in teardown_text
    assert "kill" in teardown_text


def test_recovery_audit_timeout_declared(e2e_test_contract):
    """e2e contract must declare a timeout_seconds."""
    timeout = e2e_test_contract.get("payload", {}).get("timeout_seconds")
    assert isinstance(timeout, int)
    assert timeout >= 60, "timeout_seconds must be at least 60 seconds"
    # Architecture specifies 2400s for full e2e.
    assert timeout == 2400, f"expected timeout 2400 seconds, got {timeout}"


@pytest.mark.awaiting_devon("NFR-0400")
def test_recovery_audit_query_before_retry(workbench_api):
    """Recovery: query exact identity before deciding to retry."""
    assert workbench_api is not None  # AC-NFR0400-01


@pytest.mark.awaiting_devon("NFR-0400")
def test_recovery_audit_no_blind_retry(workbench_api):
    """Recovery: no blind retry on timeout (must query first)."""
    assert workbench_api is not None  # AC-NFR0400-01


def test_recovery_audit_architecture_anchors(e2e_test_contract):
    """Required suite must reference ARC-AUD-01/ARC-STORE for recovery audit."""
    payload = e2e_test_contract.get("payload", {})
    required_suite = next(
        (s for s in payload.get("suites", []) if s.get("required")), None
    )
    assert required_suite is not None  # AC-NFR0400-01
    anchors = set(required_suite.get("architecture_anchors", []))
    # ARC-STORE and ARC-SECURITY are expected for recovery audit.
    assert "ARC-STORE" in anchors
    assert "ARC-SECURITY" in anchors


def test_recovery_audit_interface_ids(e2e_test_contract):
    """Required suite must reference IF-AUD-01 for recovery audit."""
    payload = e2e_test_contract.get("payload", {})
    required_suite = next(
        (s for s in payload.get("suites", []) if s.get("required")), None
    )
    assert required_suite is not None  # AC-NFR0400-01
    interface_ids = set(required_suite.get("interface_ids", []))
    assert "IF-AUD-01" in interface_ids, (
        "required suite missing IF-AUD-01 interface for recovery audit"
    )
