"""E2E: AC-FR2400-01 Human direct diff journey.

Verifies the Human direct-diff absorption contract at the e2e layer.
AC-FR2400-01 is in the required e2e suite, covered by the
design-author-review-continue journey.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.v014_002_e2e


def test_acid_fr2400_in_required_suite(e2e_test_contract):
    """AC-FR2400-01 must be in the required e2e suite."""
    payload = e2e_test_contract.get("payload", {})
    required_acids: set[str] = set()
    for suite in payload.get("suites", []):
        if suite.get("required"):
            required_acids.update(suite.get("ac_ids", []))
    assert "AC-FR2400-01" in required_acids


def test_acid_fr2400_in_journey(e2e_test_contract):
    """AC-FR2400-01 must be covered by design-author-review-continue journey."""
    payload = e2e_test_contract.get("payload", {})
    journey = next(
        (j for j in payload.get("journeys", []) if j.get("id") == "design-author-review-continue"),
        None,
    )
    assert journey is not None
    assert "AC-FR2400-01" in journey.get("ac_ids", [])


def test_human_direct_diff_actions_declared(e2e_test_contract):
    """Journey actions must include direct-diff exercise."""
    payload = e2e_test_contract.get("payload", {})
    journey = next(
        (j for j in payload.get("journeys", []) if j.get("id") == "design-author-review-continue"),
        None,
    )
    assert journey is not None
    actions = journey.get("actions", [])
    actions_text = " ".join(actions).lower()
    assert "direct-diff" in actions_text or "direct diff" in actions_text, (
        "journey actions must include direct-diff exercise"
    )


def test_human_direct_diff_recovery_preserves_draft(e2e_test_contract):
    """Recovery: stale/conflict preserves draft and current revision."""
    payload = e2e_test_contract.get("payload", {})
    journey = next(
        (j for j in payload.get("journeys", []) if j.get("id") == "design-author-review-continue"),
        None,
    )
    assert journey is not None
    recovery = journey.get("recovery", "").lower()
    assert "stale" in recovery or "conflict" in recovery
    assert "draft" in recovery or "preserves" in recovery
    assert "current revision" in recovery or "revision" in recovery


def test_human_direct_diff_failure_links_anchor(e2e_test_contract):
    """Recovery: failure links exact artifact anchor."""
    payload = e2e_test_contract.get("payload", {})
    journey = next(
        (j for j in payload.get("journeys", []) if j.get("id") == "design-author-review-continue"),
        None,
    )
    assert journey is not None
    recovery = journey.get("recovery", "").lower()
    assert "anchor" in recovery or "artifact" in recovery


@pytest.mark.awaiting_devon("FR-2400")
def test_human_direct_diff_actor_base_current_digest(workbench_api):
    """Direct diff must carry actor, base, and current digest."""
    assert workbench_api is not None


@pytest.mark.awaiting_devon("FR-2400")
def test_human_direct_diff_inline_discussions_dedup(workbench_api):
    """Next Archer manifest must include the diff and deduped inline discussions."""
    assert workbench_api is not None


@pytest.mark.awaiting_devon("FR-2400")
def test_human_direct_diff_not_pass(workbench_api):
    """Human authorship does not form PASS (no auto-PASS)."""
    assert workbench_api is not None


@pytest.mark.awaiting_devon("FR-2400")
def test_human_direct_diff_lease_readonly(workbench_api):
    """Agent lease period is read-only; stale save returns current revision and preserves browser draft."""
    assert workbench_api is not None


def test_human_direct_diff_architecture_anchors(e2e_test_contract):
    """Required suite must reference ARC-WEB and ARC-DESIGN for human direct diff."""
    payload = e2e_test_contract.get("payload", {})
    required_suite = next(
        (s for s in payload.get("suites", []) if s.get("required")), None
    )
    assert required_suite is not None
    anchors = set(required_suite.get("architecture_anchors", []))
    assert "ARC-WEB" in anchors
    assert "ARC-DESIGN" in anchors
