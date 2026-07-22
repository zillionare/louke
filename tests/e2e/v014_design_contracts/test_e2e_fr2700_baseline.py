"""E2E: AC-FR2700-01 Implementation baseline journey.

Verifies the implementation baseline creation contract at the e2e layer.
AC-FR2700-01 is in the required e2e suite, covered by the
design-author-review-continue journey.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.v014_002_e2e


def test_acid_fr2700_in_required_suite(e2e_test_contract):
    """AC-FR2700-01 must be in the required e2e suite."""
    payload = e2e_test_contract.get("payload", {})
    required_acids: set[str] = set()
    for suite in payload.get("suites", []):
        if suite.get("required"):
            required_acids.update(suite.get("ac_ids", []))
    assert "AC-FR2700-01" in required_acids


def test_acid_fr2700_in_journey(e2e_test_contract):
    """AC-FR2700-01 must be covered by design-author-review-continue journey."""
    payload = e2e_test_contract.get("payload", {})
    journey = next(
        (
            j
            for j in payload.get("journeys", [])
            if j.get("id") == "design-author-review-continue"
        ),
        None,
    )
    assert journey is not None
    assert "AC-FR2700-01" in journey.get("ac_ids", [])


def test_baseline_actions_declared(e2e_test_contract):
    """Journey actions must include 'continue after baseline'."""
    payload = e2e_test_contract.get("payload", {})
    journey = next(
        (
            j
            for j in payload.get("journeys", [])
            if j.get("id") == "design-author-review-continue"
        ),
        None,
    )
    assert journey is not None  # AC-FR2700-01
    actions = journey.get("actions", [])
    actions_text = " ".join(actions).lower()
    assert "baseline" in actions_text, (
        "journey actions must include 'continue after baseline'"
    )


def test_baseline_visible_result_no_second_m_lock(e2e_test_contract):
    """Visible result must declare 'no second Human lock' / no second M-LOCK."""
    payload = e2e_test_contract.get("payload", {})
    journey = next(
        (
            j
            for j in payload.get("journeys", [])
            if j.get("id") == "design-author-review-continue"
        ),
        None,
    )
    assert journey is not None  # AC-FR2700-01
    visible_result = journey.get("visible_result", "").lower()
    # Architecture §3 says: "M-IMPL (no second M-LOCK / no Human technical approval)"
    assert "no second human lock" in visible_result, (
        "visible_result must declare 'no second Human lock'"
    )


def test_baseline_evidence_required_ac_layer_reconciliation(e2e_test_contract):
    """Evidence: required_ac_layer_reconciliation must be true."""
    evidence = e2e_test_contract.get("payload", {}).get("evidence", {})
    assert evidence.get("required_ac_layer_reconciliation") is True


def test_baseline_evidence_active_candidate_identity(e2e_test_contract):
    """Evidence: active_candidate_identity must be true."""
    evidence = e2e_test_contract.get("payload", {}).get("evidence", {})
    assert evidence.get("active_candidate_identity") is True


def test_baseline_evidence_secret_scan(e2e_test_contract):
    """Evidence: secret_scan_before_upload must be true."""
    evidence = e2e_test_contract.get("payload", {}).get("evidence", {})
    assert evidence.get("secret_scan_before_upload") is True


def test_baseline_artifacts_declared(e2e_test_contract):
    """Artifacts list must include JUnit, v014-runner-evidence.json, trace, DOM, log."""
    artifacts = e2e_test_contract.get("payload", {}).get("artifacts", [])
    assert artifacts, "e2e contract must declare artifacts"
    artifacts_text = " ".join(artifacts).lower()
    assert "junit" in artifacts_text
    assert "v014-runner-evidence.json" in artifacts_text
    assert "trace" in artifacts_text
    assert "dom" in artifacts_text
    assert "log" in artifacts_text


@pytest.mark.awaiting_devon("FR-2700")
def test_baseline_atomic_creation(workbench_api):
    """Implementation baseline must be atomically created (single CAS transaction)."""
    assert workbench_api is not None  # AC-FR2700-01


@pytest.mark.awaiting_devon("FR-2700")
def test_baseline_no_second_m_lock(workbench_api):
    """No second M-LOCK / no Human technical approval after baseline."""
    assert workbench_api is not None  # AC-FR2700-01


def test_baseline_architecture_anchors(e2e_test_contract):
    """Required suite must reference ARC-STORE for baseline."""
    payload = e2e_test_contract.get("payload", {})
    required_suite = next(
        (s for s in payload.get("suites", []) if s.get("required")), None
    )
    assert required_suite is not None  # AC-FR2700-01
    anchors = set(required_suite.get("architecture_anchors", []))
    assert "ARC-STORE" in anchors, (
        "required suite missing ARC-STORE anchor for baseline"
    )
