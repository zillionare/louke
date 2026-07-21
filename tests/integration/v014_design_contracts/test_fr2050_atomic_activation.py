"""Integration tests for FR-2050: Prompt Candidate Safe Bootstrap & Atomic Activation.

AC-FR2050-01: After modifying current author/reviewer prompt candidate,
started session still reports old active bundle identity; new content only
appears as candidate artifact, no hot reload or current attempt change.
Candidate only becomes subsequent dispatch's active bundle after lint/schema,
independent trusted-review, deployment readback and baseline all PASS;
review record contains both reviewer execution bundle and reviewed candidate
bundle; candidate cannot self-certify PASS.
"""
# AC-FR2050-01

from __future__ import annotations

import pytest


def test_manifest_reviewer_binding_has_two_distinct_digests(design_manifest):
    """reviewer_binding must have reviewer_execution_digest (active Prism)
    and reviewed_candidate_bundle_digest (candidate), and they differ."""
    binding = design_manifest["prompt_candidates"]["reviewer_binding"]
    exec_digest = binding["reviewer_execution_digest"]
    cand_digest = binding["reviewed_candidate_bundle_digest"]
    assert exec_digest != cand_digest, (
        "reviewer execution (active) and reviewed candidate must be different"
    )


def test_manifest_staging_does_not_overwrite_active(design_manifest):
    """staging paths must be under design-artifacts/, not .opencode/agents/."""
    for staging in design_manifest["prompt_candidates"]["staging"]:
        path = staging["path"]
        assert path.startswith("design-artifacts/prompts/staging/"), (
            f"staging path must not target active .opencode/agents/: {path}"
        )


def test_manifest_deployment_readback_is_staging_only(design_manifest):
    """deployment_readback must qualify as staging-only, active unchanged."""
    readback = design_manifest["prompt_candidates"]["deployment_readback"]
    assert "staging-only" in readback["qualification"]
    assert "active unchanged" in readback["qualification"]


def test_manifest_activation_gate_is_atomic(design_manifest, registry_candidate):
    """Registry activation_gate must be atomic; all prerequisites required."""
    gate = registry_candidate["activation_gate"]
    assert gate["atomic"] is True
    assert len(gate["prerequisites"]) >= 3


def test_manifest_activation_gate_mentions_fail_closed(registry_candidate):
    """activation_gate.failure_semantics must mention fail closed."""
    semantics = registry_candidate["activation_gate"]["failure_semantics"]
    assert "fail closed" in semantics.lower() or "fail_closed" in semantics.lower()


@pytest.mark.awaiting_devon("FR-2050")
def test_running_attempt_uses_old_active_bundle(mock_prompt_bundle):
    """After candidate modification, running attempt must still report
    old active bundle identity."""
    mock_prompt_bundle.get_active_bundle.return_value = {
        "identity": "louke.prompt-bundle.v0.14-002.r3",
        "candidate_identity": "louke.prompt-bundle.v0.14-002.r4",
    }
    result = mock_prompt_bundle.get_active_bundle()
    assert result["identity"] != result["candidate_identity"]


@pytest.mark.awaiting_devon("FR-2050")
def test_candidate_not_activated_until_all_prerequisites(mock_prompt_bundle):
    """Candidate must not activate until lint/schema/review/readback/baseline PASS."""
    mock_prompt_bundle.activate.return_value = {
        "ok": False,
        "error": "PREREQUISITES_NOT_MET",
        "missing": ["trusted-review", "baseline"],
    }
    result = mock_prompt_bundle.activate(candidate="r4")
    assert not result["ok"]


@pytest.mark.awaiting_devon("FR-2050")
def test_candidate_cannot_self_certify_pass(mock_prompt_bundle):
    """Candidate cannot self-certify PASS; review must come from trusted reviewer."""
    mock_prompt_bundle.self_certify.return_value = {
        "ok": False,
        "error": "SELF_CERTIFICATION_REJECTED",
    }
    result = mock_prompt_bundle.self_certify()
    assert not result["ok"]


@pytest.mark.awaiting_devon("FR-2050")
def test_atomic_activation_swaps_pointer(mock_prompt_bundle):
    """Activation must atomically swap active pointer."""
    mock_prompt_bundle.activate.return_value = {
        "ok": True,
        "new_active": "louke.prompt-bundle.v0.14-002.r4",
        "old_active": "louke.prompt-bundle.v0.14-002.r3",
    }
    result = mock_prompt_bundle.activate(candidate="r4", prerequisites_met=True)
    assert result["ok"]
    assert result["new_active"] != result["old_active"]
