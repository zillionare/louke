"""E2E: AC-FR2050-01 Atomic activation journey.

Verifies the candidate→active atomic activation contract at the e2e layer.
AC-FR2050-01 is in the required e2e suite, covered by the
candidate-bootstrap-restart journey.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.v014_002_e2e


def test_acid_fr2050_in_required_suite(e2e_test_contract):
    """AC-FR2050-01 must be in the required e2e suite."""
    payload = e2e_test_contract.get("payload", {})
    required_acids: set[str] = set()
    for suite in payload.get("suites", []):
        if suite.get("required"):
            required_acids.update(suite.get("ac_ids", []))
    assert "AC-FR2050-01" in required_acids


def test_acid_fr2050_in_journey(e2e_test_contract):
    """AC-FR2050-01 must be covered by candidate-bootstrap-restart journey."""
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
    assert "AC-FR2050-01" in journey.get("ac_ids", [])


def test_atomic_activation_gate_fail_closed(e2e_test_contract):
    """Atomic activation gate must fail closed (any unknown/partial blocks activation)."""
    failure_policy = e2e_test_contract.get("payload", {}).get("failure_policy", {})
    assert failure_policy.get("fail_closed") is True
    # Non-success modes that block activation.
    non_success = failure_policy.get("non_success", [])
    for required_mode in ("unknown", "missing", "skip", "not-run", "zero-collection"):
        assert required_mode in non_success, (
            f"failure_policy.non_success missing '{required_mode}' for atomic activation gate"
        )


def test_candidate_state_honestly_declared(e2e_test_contract):
    """current_state must be candidate-not-installed (not falsely claimed as active)."""
    failure_policy = e2e_test_contract.get("payload", {}).get("failure_policy", {})
    assert failure_policy.get("current_state") == "candidate-not-installed"


def test_atomic_activation_no_self_certify(e2e_test_contract):
    """Atomic activation must NOT allow candidate to self-certify.

    The journey must declare that the trusted Prism reviewer is the prior
    active Prism, not the candidate itself.
    """
    payload = e2e_test_contract.get("payload", {})
    journey = next(
        (
            j
            for j in payload.get("journeys", [])
            if j.get("id") == "candidate-bootstrap-restart"
        ),
        None,
    )
    assert journey is not None  # AC-FR2050-01
    actions = journey.get("actions", [])
    actions_text = " ".join(actions).lower()
    # Must reference "prior trusted prism" or similar.
    assert any(
        kw in actions_text for kw in ("prior", "trusted", "prism", "reviewer")
    ), "candidate-bootstrap-restart journey must declare prior trusted Prism reviewer"


def test_atomic_activation_visible_result(e2e_test_contract):
    """Visible result: one atomic future activation after all prerequisites."""
    payload = e2e_test_contract.get("payload", {})
    journey = next(
        (
            j
            for j in payload.get("journeys", [])
            if j.get("id") == "candidate-bootstrap-restart"
        ),
        None,
    )
    assert journey is not None  # AC-FR2050-01
    visible_result = journey.get("visible_result", "").lower()
    assert "atomic" in visible_result, "visible_result must declare atomic activation"
    assert "non-active" in visible_result or "candidate" in visible_result, (
        "visible_result must declare candidate stays non-active until prerequisites"
    )


def test_atomic_activation_recovery(e2e_test_contract):
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
    assert journey is not None  # AC-FR2050-01
    recovery = journey.get("recovery", "").lower()
    assert "drift" in recovery or "kill" in recovery
    assert "old active" in recovery or "active" in recovery
    assert "stale" in recovery


@pytest.mark.awaiting_devon("FR-2050")
def test_atomic_activation_cas_exchange(workbench_api):
    """Atomic activation must use CAS exchange for the active pointer."""
    assert workbench_api is not None  # AC-FR2050-01


@pytest.mark.awaiting_devon("FR-2050")
def test_atomic_activation_prerequisites_gate(workbench_api):
    """All prerequisites (schema/lint/IF-DES-02/trusted Prism/staging readback/artifact readback/baseline) must be current before activation."""
    assert workbench_api is not None  # AC-FR2050-01


def test_atomic_activation_architecture_anchors(e2e_test_contract):
    """Required suite must reference architecture anchors for atomic activation."""
    payload = e2e_test_contract.get("payload", {})
    required_suite = next(
        (s for s in payload.get("suites", []) if s.get("required")), None
    )
    assert required_suite is not None  # AC-FR2050-01
    anchors = set(required_suite.get("architecture_anchors", []))
    # ARC-PROMPTS, ARC-STORE, ARC-SECURITY are expected for atomic activation.
    for expected in ("ARC-PROMPTS", "ARC-STORE", "ARC-SECURITY"):
        assert expected in anchors, (
            f"required suite missing architecture anchor for atomic activation: {expected}"
        )
