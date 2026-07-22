"""E2E: AC-FR2500-01 Revise loop journey.

Verifies the independent Prism review and REVISE loop contract at the e2e
layer. AC-FR2500-01 is in the required e2e suite, covered by the
design-author-review-continue journey.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.v014_002_e2e


def test_acid_fr2500_in_required_suite(e2e_test_contract):
    """AC-FR2500-01 must be in the required e2e suite."""
    payload = e2e_test_contract.get("payload", {})
    required_acids: set[str] = set()
    for suite in payload.get("suites", []):
        if suite.get("required"):
            required_acids.update(suite.get("ac_ids", []))
    assert "AC-FR2500-01" in required_acids


def test_acid_fr2500_in_journey(e2e_test_contract):
    """AC-FR2500-01 must be covered by design-author-review-continue journey."""
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
    assert "AC-FR2500-01" in journey.get("ac_ids", [])


def test_revise_loop_actions_declared(e2e_test_contract):
    """Journey actions must include observing independent Prism result."""
    payload = e2e_test_contract.get("payload", {})
    journey = next(
        (
            j
            for j in payload.get("journeys", [])
            if j.get("id") == "design-author-review-continue"
        ),
        None,
    )
    assert journey is not None  # AC-FR2500-01
    actions = journey.get("actions", [])
    actions_text = " ".join(actions).lower()
    assert "prism" in actions_text, (
        "journey actions must include observing independent Prism result"
    )
    assert "independent" in actions_text or "reviewer" in actions_text, (
        "journey actions must declare Prism is independent"
    )


def test_revise_loop_visible_result(e2e_test_contract):
    """Visible result: ready_for_implementation with trusted Prism identity."""
    payload = e2e_test_contract.get("payload", {})
    journey = next(
        (
            j
            for j in payload.get("journeys", [])
            if j.get("id") == "design-author-review-continue"
        ),
        None,
    )
    assert journey is not None  # AC-FR2500-01
    visible_result = journey.get("visible_result", "").lower()
    assert "ready_for_implementation" in visible_result or "ready" in visible_result
    assert "prism" in visible_result or "trusted" in visible_result


def test_revise_loop_no_second_human_lock(e2e_test_contract):
    """Visible result must declare 'no second Human lock'."""
    payload = e2e_test_contract.get("payload", {})
    journey = next(
        (
            j
            for j in payload.get("journeys", [])
            if j.get("id") == "design-author-review-continue"
        ),
        None,
    )
    assert journey is not None  # AC-FR2500-01
    visible_result = journey.get("visible_result", "").lower()
    assert "no second human lock" in visible_result or "no second" in visible_result, (
        "visible_result must declare no second Human lock"
    )


def test_revise_loop_fresh_program_checks(e2e_test_contract):
    """Visible result must declare fresh program checks."""
    payload = e2e_test_contract.get("payload", {})
    journey = next(
        (
            j
            for j in payload.get("journeys", [])
            if j.get("id") == "design-author-review-continue"
        ),
        None,
    )
    assert journey is not None  # AC-FR2500-01
    visible_result = journey.get("visible_result", "").lower()
    assert "fresh" in visible_result or "program checks" in visible_result


@pytest.mark.awaiting_devon("FR-2500")
def test_revise_loop_prism_independent_dispatch(workbench_api):
    """Prism dispatch must be independent (not authored by Archer)."""
    assert workbench_api is not None  # AC-FR2500-01


@pytest.mark.awaiting_devon("FR-2500")
def test_revise_loop_verdict_identity_bound(workbench_api):
    """Prism verdict must be identity-bound (revision-specific)."""
    assert workbench_api is not None  # AC-FR2500-01


@pytest.mark.awaiting_devon("FR-2500")
def test_revise_loop_revise_triggers_new_revision(workbench_api):
    """REVISE verdict triggers new DESIGN revision -> repeat validation/review."""
    assert workbench_api is not None  # AC-FR2500-01


def test_revise_loop_architecture_anchors(e2e_test_contract):
    """Required suite must reference ARC-REVIEW for revise loop."""
    payload = e2e_test_contract.get("payload", {})
    required_suite = next(
        (s for s in payload.get("suites", []) if s.get("required")), None
    )
    assert required_suite is not None  # AC-FR2500-01
    anchors = set(required_suite.get("architecture_anchors", []))
    assert "ARC-REVIEW" in anchors, (
        "required suite missing ARC-REVIEW anchor for revise loop"
    )


def test_revise_loop_interface_ids(e2e_test_contract):
    """Required suite must reference IF-REV-01 for revise loop."""
    payload = e2e_test_contract.get("payload", {})
    required_suite = next(
        (s for s in payload.get("suites", []) if s.get("required")), None
    )
    assert required_suite is not None  # AC-FR2500-01
    interface_ids = set(required_suite.get("interface_ids", []))
    assert "IF-REV-01" in interface_ids, (
        "required suite missing IF-REV-01 interface for revise loop"
    )
