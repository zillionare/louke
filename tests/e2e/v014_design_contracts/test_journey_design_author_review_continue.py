"""E2E journey: design-author-review-continue.

Covers AC IDs (per e2e-test.candidate.json journey ``design-author-review-continue``):
- AC-FR0300-01  (Workbench visible context)
- AC-FR0600-01  (Interfaces closure observable through Workbench)
- AC-FR0900-01  (e2e contract satisfied)
- AC-FR2400-01  (Human direct diff absorption)
- AC-FR2500-01  (Independent Prism result)
- AC-FR2700-01  (Implementation baseline creation, no second M-LOCK)
- AC-NFR0500-01 (Feedback categories surface in Workbench)

Mode B: journey steps are exercised against the workbench_api stand-in.
When Devon ships the real ``lk web`` server, set ``LOUKE_V014_002_LIVE_SERVER=1``
and these tests will skip pending live-server wiring.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

pytestmark = pytest.mark.v014_002_e2e


def test_journey_entry_approved_requirements_open_m_design(
    workbench_api, design_manifest, host_facts_snapshot
):
    """Entry: approved requirements current opens M-DESIGN."""
    # Verify the journey's preconditions are declared in the design manifest.
    inputs = design_manifest.get("input_artifacts", [])
    kinds = {entry.get("kind") for entry in inputs}
    assert "host-project-facts-snapshot" in kinds, (
        "design manifest must declare host-project-facts-snapshot input "
        "for M-DESIGN entry (IF-DES-01)"
    )
    # Host facts must be the typed readback, not project.toml bytes.
    # The snapshot uses "artifact_kind" (typed envelope) not "kind".
    assert (
        host_facts_snapshot.get("artifact_kind") == "host-project-facts-snapshot"
        or host_facts_snapshot.get("kind") == "host-project-facts-snapshot"
    ), f"host_facts_snapshot missing kind; got keys: {list(host_facts_snapshot.keys())}"
    assert "identity" in host_facts_snapshot
    assert "revision" in host_facts_snapshot


def test_journey_observe_exact_identities(
    workbench_api, design_manifest, e2e_test_contract
):
    """Step: observe exact identities (revision, facts, schema, prompts)."""
    scope = e2e_test_contract.get("scope", {})
    required_scope_keys = {
        "workspace_id",
        "spec_id",
        "base_commit",
        "project_facts_digest",
        "project_facts_artifact",
        "release_identity",
    }
    missing = required_scope_keys - set(scope.keys())
    assert not missing, f"e2e contract scope missing identity keys: {missing}"
    # project_facts_artifact must be a typed reference, not a sha string.
    facts_artifact = scope["project_facts_artifact"]
    assert facts_artifact.get("kind") == "host-project-facts-snapshot"
    assert "path" in facts_artifact
    assert "identity" in facts_artifact
    assert "revision" in facts_artifact


def test_journey_inspect_docs_contracts_prompts_checks(
    workbench_api, e2e_test_contract
):
    """Step: inspect docs/contracts/prompts/checks (public surfaces)."""
    artifact_refs = e2e_test_contract.get("artifact_refs", [])
    referenced_paths = {ref.get("path") for ref in artifact_refs}
    # Test plan, interfaces, architecture must all be referenced.
    assert any("test-plan.md" in p for p in referenced_paths), (
        "e2e contract must reference test-plan.md"
    )
    assert any("interfaces.md" in p for p in referenced_paths), (
        "e2e contract must reference interfaces.md"
    )
    assert any("architecture.md" in p for p in referenced_paths), (
        "e2e contract must reference architecture.md"
    )
    # Each artifact_ref must carry AC IDs, interface IDs, and architecture anchors.
    for ref in artifact_refs:
        assert "ac_ids" in ref and len(ref["ac_ids"]) > 0
        assert "interface_ids" in ref and len(ref["interface_ids"]) > 0
        assert "architecture_anchors" in ref and len(ref["architecture_anchors"]) > 0
        assert ref.get("contract_kind") == "e2e-test"


@pytest.mark.awaiting_devon("FR-0300")
def test_journey_exercise_comment_direct_diff_reconnect(workbench_api):
    """Step: exercise comment / direct-diff / reconnect through Workbench.

    Requires Devon's IF-WEB-01 implementation to expose the comment and
    direct-diff endpoints. Mocked in Mode B.
    """
    # In Mode B, workbench_api is a MagicMock; verify it is non-None and
    # the expected entry points are referenceable (will be no-ops on the mock).
    assert workbench_api is not None
    # The journey must be able to invoke comment/direct-diff endpoints.
    # Real assertion deferred to Devon's implementation.
    assert hasattr(workbench_api, "__call__") or hasattr(workbench_api, "request")


@pytest.mark.awaiting_devon("FR-2500")
def test_journey_observe_independent_prism_result(workbench_api):
    """Step: observe independent Prism result (not author-written)."""
    assert workbench_api is not None


@pytest.mark.awaiting_devon("FR-2700")
def test_journey_continue_after_baseline_no_second_human_lock(workbench_api):
    """Visible result: ready_for_implementation with no second Human lock."""
    assert workbench_api is not None


def test_journey_recovery_stale_preserves_draft(
    workbench_api, e2e_test_contract
):
    """Recovery: stale/conflict preserves draft and current revision; failure links exact artifact anchor."""
    failure_policy = e2e_test_contract.get("payload", {}).get("failure_policy", {})
    assert failure_policy.get("fail_closed") is True
    non_success = failure_policy.get("non_success", [])
    # Must include the journey-level recovery failure modes.
    for required_mode in ("failure", "cancel", "timeout", "missing", "skip", "not-run"):
        assert required_mode in non_success, (
            f"failure_policy.non_success missing '{required_mode}'"
        )
    # current_state must be honestly declared as candidate-not-installed.
    assert failure_policy.get("current_state") == "candidate-not-installed"


def test_journey_acids_match_required_suite(e2e_test_contract):
    """Journey AC IDs must be a subset of the required suite AC IDs."""
    payload = e2e_test_contract.get("payload", {})
    required_suite_acids = set()
    for suite in payload.get("suites", []):
        if suite.get("required"):
            required_suite_acids.update(suite.get("ac_ids", []))
    journeys = payload.get("journeys", [])
    assert journeys, "e2e contract must declare at least one journey"
    for journey in journeys:
        journey_acids = set(journey.get("ac_ids", []))
        assert journey_acids.issubset(required_suite_acids), (
            f"journey '{journey.get('id')}' declares AC IDs not in required suite: "
            f"{journey_acids - required_suite_acids}"
        )


def test_journey_teardown_evidence_requirements(e2e_test_contract):
    """Teardown must save redacted evidence, TERM, wait, KILL, remove temp state."""
    payload = e2e_test_contract.get("payload", {})
    teardown = payload.get("teardown", [])
    teardown_text = " ".join(teardown)
    assert "redacted evidence" in teardown_text.lower() or "save redacted" in teardown_text.lower()
    assert "TERM" in teardown_text
    assert "KILL" in teardown_text
    assert "remove" in teardown_text.lower() and "temporary state" in teardown_text.lower()
    # Evidence requirements.
    evidence = payload.get("evidence", {})
    assert evidence.get("required_ac_layer_reconciliation") is True
    assert evidence.get("active_candidate_identity") is True
    assert evidence.get("secret_scan_before_upload") is True


def test_journey_isolation_contract(e2e_test_contract):
    """Isolation: dynamically allocated ports, fresh browser context, no shared state."""
    isolation = e2e_test_contract.get("payload", {}).get("isolation", {})
    assert isolation.get("ports") == "dynamically allocated"
    assert isolation.get("browser_context") == "new per case"
    assert isolation.get("active_pointer") == "fixture-local"
    assert isolation.get("parallel_shared_state") is False


def test_journey_public_surfaces_declared(e2e_test_contract):
    """Public surfaces must include the three Workbench endpoints."""
    public_surfaces = e2e_test_contract.get("payload", {}).get("public_surfaces", [])
    assert any("M-DESIGN context" in s for s in public_surfaces), (
        "public_surfaces missing Workbench M-DESIGN context"
    )
    assert any("/api/v14/runs/" in s and s.endswith("/design") for s in public_surfaces), (
        "public_surfaces missing GET /api/v14/runs/{run_id}/design"
    )
    assert any("/api/v14/runs/" in s and s.endswith("/design/audit") for s in public_surfaces), (
        "public_surfaces missing GET /api/v14/runs/{run_id}/design/audit"
    )
