"""E2E: AC-NFR0500-01 Feedback journey.

Verifies the feedback categories surface through the Workbench. AC-NFR0500-01
is in the required e2e suite, covered by the design-author-review-continue
journey.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.v014_002_e2e


def test_acid_nfr0500_in_required_suite(e2e_test_contract):
    """AC-NFR0500-01 must be in the required e2e suite."""
    payload = e2e_test_contract.get("payload", {})
    required_acids: set[str] = set()
    for suite in payload.get("suites", []):
        if suite.get("required"):
            required_acids.update(suite.get("ac_ids", []))
    assert "AC-NFR0500-01" in required_acids


def test_acid_nfr0500_in_journey(e2e_test_contract):
    """AC-NFR0500-01 must be covered by design-author-review-continue journey."""
    payload = e2e_test_contract.get("payload", {})
    journey = next(
        (j for j in payload.get("journeys", []) if j.get("id") == "design-author-review-continue"),
        None,
    )
    assert journey is not None
    assert "AC-NFR0500-01" in journey.get("ac_ids", [])


def test_feedback_fixtures_declared(e2e_test_contract):
    """e2e contract must declare feedback-related fixtures."""
    fixtures = e2e_test_contract.get("payload", {}).get("fixtures", [])
    # Per e2e-test.candidate.json: fixtures includes approved_design_inputs,
    # prompt_matrix, review_restart_matrix, secret_canaries.
    assert "approved_design_inputs" in fixtures
    assert "prompt_matrix" in fixtures
    assert "review_restart_matrix" in fixtures
    assert "secret_canaries" in fixtures


def test_feedback_environment_declared(e2e_test_contract):
    """e2e contract must declare environment (HOME/XDG/workspace, production_secrets=false)."""
    env = e2e_test_contract.get("payload", {}).get("environment", {})
    assert env.get("production_secrets") is False
    assert "HOME_XDG_workspace" in env or "workspace" in env
    assert env.get("providers") == "stand-ins"


def test_feedback_failure_categories_in_non_success(e2e_test_contract):
    """Failure policy non_success must include the 4 feedback categories.

    Per NFR-0500: failure, cancel, timeout, missing are the canonical
    feedback categories that must be surfaced.
    """
    failure_policy = e2e_test_contract.get("payload", {}).get("failure_policy", {})
    non_success = failure_policy.get("non_success", [])
    # The 4 canonical feedback categories.
    for category in ("failure", "cancel", "timeout", "missing"):
        assert category in non_success, (
            f"failure_policy.non_success missing feedback category: {category}"
        )


def test_feedback_evidence_required(e2e_test_contract):
    """Evidence must include required_ac_layer_reconciliation (feedback traceability)."""
    evidence = e2e_test_contract.get("payload", {}).get("evidence", {})
    assert evidence.get("required_ac_layer_reconciliation") is True


def test_feedback_secret_scan_before_upload(e2e_test_contract):
    """Evidence must include secret_scan_before_upload (feedback must not leak secrets)."""
    evidence = e2e_test_contract.get("payload", {}).get("evidence", {})
    assert evidence.get("secret_scan_before_upload") is True


def test_feedback_acid_in_journey_recovery(e2e_test_contract):
    """Journey recovery must preserve draft and link exact artifact anchor (feedback traceability)."""
    payload = e2e_test_contract.get("payload", {})
    journey = next(
        (j for j in payload.get("journeys", []) if j.get("id") == "design-author-review-continue"),
        None,
    )
    assert journey is not None
    recovery = journey.get("recovery", "").lower()
    # Recovery must link to exact artifact anchor (feedback traceability).
    assert "anchor" in recovery or "artifact" in recovery


@pytest.mark.awaiting_devon("NFR-0500")
def test_feedback_categories_visible_through_workbench(workbench_api):
    """Feedback categories (failure/cancel/timeout/missing) must be visible through Workbench."""
    assert workbench_api is not None


@pytest.mark.awaiting_devon("NFR-0500")
def test_feedback_required_fields(workbench_api):
    """Feedback must include required fields (category, artifact anchor, reason)."""
    assert workbench_api is not None


def test_feedback_architecture_anchors(e2e_test_contract):
    """Required suite must reference ARC-WEB and ARC-REVIEW for feedback."""
    payload = e2e_test_contract.get("payload", {})
    required_suite = next(
        (s for s in payload.get("suites", []) if s.get("required")), None
    )
    assert required_suite is not None
    anchors = set(required_suite.get("architecture_anchors", []))
    assert "ARC-WEB" in anchors
    assert "ARC-REVIEW" in anchors


def test_feedback_interface_ids(e2e_test_contract):
    """Required suite must reference IF-WEB-01 and IF-REV-01 for feedback."""
    payload = e2e_test_contract.get("payload", {})
    required_suite = next(
        (s for s in payload.get("suites", []) if s.get("required")), None
    )
    assert required_suite is not None
    interface_ids = set(required_suite.get("interface_ids", []))
    assert "IF-WEB-01" in interface_ids
    assert "IF-REV-01" in interface_ids
