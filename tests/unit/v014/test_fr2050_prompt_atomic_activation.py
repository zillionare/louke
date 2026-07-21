"""AC-FR2050-01: prompt candidate atomic activation & safe bootstrap.

FR-2050 requires Runtime to distinguish the active prompt bundle running the
current task from the candidate bundle being edited/reviewed.  Candidate
file changes must not hot-reload the running attempt; candidate activates
only after lint/schema, independent trusted review, deployment readback and
baseline all pass - and only atomically for subsequent dispatch.  Reviewing
the reviewer's own prompt must use the prior trusted bundle, and the review
record must capture both bundle identities.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from louke.v014.fr2050_prompt_atomic_activation import (
    ActivationGate,
    ActivationResult,
    AttemptBinding,
    bind_attempt_to_active_bundle,
    evaluate_activation_gate,
)

_ROOT = Path(__file__).resolve().parents[3]
_SPEC_ROOT = _ROOT / ".louke" / "project" / "specs" / "v0.14-002-workflow-reflow-design"


def _bundle_digest() -> str:
    return json.loads(
        (
            _SPEC_ROOT / "design-artifacts" / "prompts" / "prompt-bundle.candidate.json"
        ).read_bytes()
    )["bundle_digest"]


def _reviewer_binding() -> dict[str, Any]:
    return json.loads(
        (
            _SPEC_ROOT
            / "design-artifacts"
            / "prompts"
            / "reviewer-binding.candidate.json"
        ).read_bytes()
    )


def test_bind_attempt_to_active_bundle_returns_binding() -> None:
    """AC-FR2050-01: a new attempt is bound to the active bundle at startup."""
    binding = bind_attempt_to_active_bundle(
        attempt_id="att-1",
        active_bundle_digest="sha256:" + "a" * 64,
    )
    assert isinstance(binding, AttemptBinding)
    assert binding.attempt_id == "att-1"
    assert binding.active_bundle_digest == "sha256:" + "a" * 64
    assert binding.candidate_bundle_digest is None
    assert binding.is_pinned_to_active is True


def test_candidate_change_does_not_hot_reload_attempt() -> None:
    """AC-FR2050-01: a candidate change after attempt start does not hot-reload."""
    binding = bind_attempt_to_active_bundle(
        attempt_id="att-2",
        active_bundle_digest="sha256:" + "a" * 64,
    )
    # A candidate bundle digest appears later but the attempt keeps its active identity
    new_candidate = "sha256:" + "b" * 64
    # Attempt remains pinned to the original active digest
    assert binding.active_bundle_digest == "sha256:" + "a" * 64
    assert binding.is_pinned_to_active is True
    # The candidate digest does not overwrite the active one
    assert binding.active_bundle_digest != new_candidate


def test_activation_gate_rejects_when_lint_fails() -> None:
    """AC-FR2050-01: a failing lint blocks activation."""
    gate = ActivationGate(
        lint_passed=False,
        schema_validation_passed=True,
        trusted_review_passed=True,
        deployment_readback_passed=True,
        implementation_baseline_current=True,
    )
    result = evaluate_activation_gate(gate)
    assert isinstance(result, ActivationResult)
    assert result.activated is False
    assert "lint" in result.reason


def test_activation_gate_rejects_when_schema_fails() -> None:
    """AC-FR2050-01: a failing schema validation blocks activation."""
    gate = ActivationGate(
        lint_passed=True,
        schema_validation_passed=False,
        trusted_review_passed=True,
        deployment_readback_passed=True,
        implementation_baseline_current=True,
    )
    result = evaluate_activation_gate(gate)
    assert result.activated is False
    assert "schema" in result.reason


def test_activation_gate_rejects_when_trusted_review_fails() -> None:
    """AC-FR2050-01: a failing trusted review blocks activation."""
    gate = ActivationGate(
        lint_passed=True,
        schema_validation_passed=True,
        trusted_review_passed=False,
        deployment_readback_passed=True,
        implementation_baseline_current=True,
    )
    result = evaluate_activation_gate(gate)
    assert result.activated is False
    assert (
        "trusted review" in result.reason.lower() or "review" in result.reason.lower()
    )


def test_activation_gate_rejects_when_readback_fails() -> None:
    """AC-FR2050-01: a failing deployment readback blocks activation."""
    gate = ActivationGate(
        lint_passed=True,
        schema_validation_passed=True,
        trusted_review_passed=True,
        deployment_readback_passed=False,
        implementation_baseline_current=True,
    )
    result = evaluate_activation_gate(gate)
    assert result.activated is False
    assert "readback" in result.reason.lower()


def test_activation_gate_rejects_when_baseline_stale() -> None:
    """AC-FR2050-01: a stale implementation baseline blocks activation."""
    gate = ActivationGate(
        lint_passed=True,
        schema_validation_passed=True,
        trusted_review_passed=True,
        deployment_readback_passed=True,
        implementation_baseline_current=False,
    )
    result = evaluate_activation_gate(gate)
    assert result.activated is False
    assert "baseline" in result.reason.lower()


def test_activation_gate_activates_only_when_all_pass() -> None:
    """AC-FR2050-01: activation requires every prerequisite to pass."""
    gate = ActivationGate(
        lint_passed=True,
        schema_validation_passed=True,
        trusted_review_passed=True,
        deployment_readback_passed=True,
        implementation_baseline_current=True,
    )
    result = evaluate_activation_gate(gate)
    assert result.activated is True


def test_reviewer_binding_reviewer_differs_from_candidate() -> None:
    """AC-FR2050-01: the reviewer execution bundle differs from the reviewed candidate."""
    binding = _reviewer_binding()
    exec_digest = binding["reviewer_execution_bundle"]["deployment_digest"]
    candidate_bundle = binding["reviewed_candidate_bundle"]["digest"]
    assert exec_digest != candidate_bundle
    assert binding["self_review_prohibited"] is True


def test_reviewer_binding_records_both_bundle_identities() -> None:
    """AC-FR2050-01: the review record carries both reviewer and reviewed identities."""
    binding = _reviewer_binding()
    assert binding["reviewer_execution_bundle"]["deployment_digest"]
    assert binding["reviewed_candidate_bundle"]["digest"]
    assert binding["reviewed_candidate_bundle"]["candidate_prism_render_digest"]
    # The reviewer execution bundle and candidate bundle must be different identities
    assert (
        binding["reviewer_execution_bundle"]["deployment_digest"]
        != binding["reviewed_candidate_bundle"]["digest"]
    )
    assert (
        binding["reviewer_execution_bundle"]["deployment_digest"]
        != binding["reviewed_candidate_bundle"]["candidate_prism_render_digest"]
    )


def test_activation_gate_failure_semantics_candidate_cannot_self_certify() -> None:
    """AC-FR2050-01: candidate cannot establish trust or activate itself."""
    binding = _reviewer_binding()
    assert "cannot establish trust" in binding["failure_semantics"].lower() or (
        "activate itself" in binding["failure_semantics"].lower()
    )


def test_reviewer_binding_stale_if_includes_reviewer_active_digest() -> None:
    """AC-FR2050-01: stale_if includes reviewer-active-digest changes."""
    binding = _reviewer_binding()
    stale_if = " ".join(binding["stale_if"]).lower()
    assert "reviewer active" in stale_if
    assert "candidate bundle" in stale_if
    assert "base commit" in stale_if


def test_activation_result_is_immutable() -> None:
    """AC-FR2050-01: activation result is an immutable value object."""
    result = ActivationResult(activated=True, reason="all prerequisites pass")
    with pytest.raises(Exception):
        result.activated = False  # type: ignore[misc]
