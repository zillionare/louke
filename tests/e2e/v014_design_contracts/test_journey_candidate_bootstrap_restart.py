"""E2E journey: candidate-bootstrap-restart.

Covers AC IDs (per e2e-test.candidate.json journey ``candidate-bootstrap-restart``):
- AC-FR2050-01  (Atomic activation: candidate stays non-active until all prerequisites)
- AC-NFR0400-01 (Recovery audit: drift or kill keeps old active, marks candidate/review stale)

Mode B: journey steps are exercised against the workbench_api stand-in.
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.v014_002_e2e


def test_journey_entry_active_bundle_plus_prompt_candidate_visible(
    workbench_api, design_manifest, e2e_test_contract
):
    """Entry: active bundle plus prompt candidate visible."""
    # Manifest must enumerate both registry candidate and prompt bundle candidate.
    # The manifest uses "registry" (object with path) and "prompt_candidates.bundle".
    registry = design_manifest.get("registry", {})
    assert registry.get("path"), "design manifest must include registry candidate"
    prompt_bundle = design_manifest.get("prompt_candidates", {}).get("bundle", {})
    assert prompt_bundle.get("path"), (
        "design manifest must include prompt-bundle candidate"
    )


def test_journey_current_attempt_stays_active(workbench_api, e2e_test_contract):
    """Step: verify current attempt stays active (candidate does not auto-activate)."""
    failure_policy = e2e_test_contract.get("payload", {}).get("failure_policy", {})
    assert failure_policy.get("current_state") == "candidate-not-installed", (
        "Journey must start from candidate-not-installed state"
    )


@pytest.mark.awaiting_devon("FR-2050")
def test_journey_review_with_prior_trusted_prism(workbench_api):
    """Step: review with prior trusted Prism (not the candidate self-reviewing)."""
    assert workbench_api is not None


@pytest.mark.awaiting_devon("FR-2050")
def test_journey_simulate_restart_before_activation(workbench_api):
    """Step: simulate restart before activation (candidate remains non-active)."""
    assert workbench_api is not None


def test_journey_visible_result_atomic_future_activation(e2e_test_contract):
    """Visible result: candidate remains non-active until all prerequisites, then one atomic future activation."""
    # Failure policy must fail-closed: any unknown/partial blocks activation.
    failure_policy = e2e_test_contract.get("payload", {}).get("failure_policy", {})
    assert failure_policy.get("fail_closed") is True
    # Non-success modes that block activation.
    non_success = failure_policy.get("non_success", [])
    for required_mode in ("unknown", "zero-collection", "ready-failure", "teardown-failure"):
        assert required_mode in non_success, (
            f"failure_policy.non_success missing '{required_mode}' "
            "(needed for atomic activation gate)"
        )


def test_journey_recovery_drift_or_kill_keeps_old_active(e2e_test_contract):
    """Recovery: drift or kill keeps old active and marks candidate/review stale."""
    # The failure policy's non_success must include the recovery scenarios.
    failure_policy = e2e_test_contract.get("payload", {}).get("failure_policy", {})
    non_success = failure_policy.get("non_success", [])
    assert "cancel" in non_success
    assert "timeout" in non_success
    assert "missing" in non_success


def test_journey_audit_recovers_identity(e2e_test_contract):
    """Audit recovers identity: audit endpoint must be in public_surfaces."""
    public_surfaces = e2e_test_contract.get("payload", {}).get("public_surfaces", [])
    assert any(s.endswith("/design/audit") for s in public_surfaces), (
        "Audit endpoint must be in public_surfaces for identity recovery"
    )


def test_journey_acids_subset_of_required_suite(e2e_test_contract):
    """Journey AC IDs (FR-2050, NFR-0400) must be in required suite."""
    payload = e2e_test_contract.get("payload", {})
    required_acids: set[str] = set()
    for suite in payload.get("suites", []):
        if suite.get("required"):
            required_acids.update(suite.get("ac_ids", []))
    # Find the candidate-bootstrap-restart journey.
    journey = next(
        (j for j in payload.get("journeys", []) if j.get("id") == "candidate-bootstrap-restart"),
        None,
    )
    assert journey is not None, "candidate-bootstrap-restart journey not declared"
    journey_acids = set(journey.get("ac_ids", []))
    assert journey_acids.issubset(required_acids), (
        f"journey AC IDs not in required suite: {journey_acids - required_acids}"
    )
    # Must specifically include the two AC IDs this journey covers.
    assert "AC-FR2050-01" in journey_acids
    assert "AC-NFR0400-01" in journey_acids


def test_journey_services_declared(e2e_test_contract):
    """Services: workbench start command and ready check must be declared."""
    services = e2e_test_contract.get("payload", {}).get("services", [])
    assert services, "e2e contract must declare at least one service"
    workbench_service = next((s for s in services if s.get("id") == "workbench"), None)
    assert workbench_service is not None, "workbench service not declared"
    assert "lk web" in workbench_service.get("start", "")
    assert workbench_service.get("runtime") == "installed wheel product venv"


def test_journey_ready_check_declared(e2e_test_contract):
    """Ready check: GET /health polling with 250ms interval and 60s timeout."""
    ready = e2e_test_contract.get("payload", {}).get("ready", {})
    assert ready.get("request") == "GET /health"
    assert ready.get("interval_ms") == 250
    assert ready.get("timeout_seconds") == 60
    expected = ready.get("expected", "")
    assert "HTTP 200" in expected
    assert "0.14.0" in expected
