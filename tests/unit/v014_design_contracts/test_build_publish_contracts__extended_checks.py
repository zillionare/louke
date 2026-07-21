"""AC-FR1500-01/AC-FR1600-01: build/artifact + publish/recovery extended checks.

Extends the existing build_publish_contracts semantics tests with additional
edge cases: ordered gate steps, prompt payload check, version comparison
equality, query-before-retry operation identities, deployment N/A, and
operation-ledger stable identity checks.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


_SPEC_ROOT = (
    Path(__file__).resolve().parents[3]
    / ".louke"
    / "project"
    / "specs"
    / "v0.14-002-workflow-reflow-design"
)
_CONTRACTS = _SPEC_ROOT / "design-artifacts" / "contracts"


def _payload(kind: str) -> dict[str, Any]:
    return json.loads((_CONTRACTS / f"{kind}.candidate.json").read_bytes())["payload"]


def test_build_artifact_ordered_gate_has_five_distinct_steps() -> None:
    """AC-FR1500-01: ordered gate has prepare/build/enumerate/compare/install."""
    gate = _payload("build-artifact")["ordered_gate"]
    assert len(gate) >= 5
    assert gate[0].startswith("prepare")
    assert any("build" in step for step in gate)
    assert any("enumerate" in step for step in gate)
    assert any("compare" in step for step in gate)
    assert any("clean-install" in step for step in gate)


def test_build_artifact_artifacts_declare_installed_outlets() -> None:
    """AC-FR1500-01: every artifact declares installed_outlets list."""
    artifacts = _payload("build-artifact")["artifacts"]
    for artifact in artifacts:
        assert artifact["installed_outlets"]
        # Outlets must include both CLI and importlib.metadata checks
        outlets_text = " ".join(artifact["installed_outlets"])
        assert "lk --version" in outlets_text
        assert "importlib.metadata" in outlets_text


def test_build_artifact_prompt_payload_check_in_outlets() -> None:
    """AC-FR1500-01: installed outlets include prompt bundle readback."""
    artifacts = _payload("build-artifact")["artifacts"]
    for artifact in artifacts:
        outlets_text = " ".join(artifact["installed_outlets"])
        assert "prompt" in outlets_text.lower()
        assert "registry" in outlets_text.lower()


def test_build_artifact_comparison_requires_exact_match() -> None:
    """AC-FR1500-01: comparison demands exact 0.14.0 across source/artifacts/outlets."""
    comparison = _payload("build-artifact")["comparison"]
    assert "0.14.0" in comparison
    assert "exact" in comparison.lower()


def test_build_artifact_evidence_has_four_distinct_stages() -> None:
    """AC-FR1500-01: evidence records the four separated stages."""
    evidence = _payload("build-artifact")["evidence"]
    expected = {
        "version-scheme-selected",
        "version-source-prepared",
        "artifacts-built",
        "artifact-versions-verified",
    }
    assert expected <= set(evidence)


def test_publish_recovery_operations_have_unique_order_and_identity() -> None:
    """AC-FR1600-01: each operation has a unique order and a stable expected_identity."""
    operations = _payload("publish-recovery")["operations"]
    orders = [op["order"] for op in operations]
    assert orders == sorted(orders)
    assert len(set(orders)) == len(orders)
    for op in operations:
        assert op["expected_identity"]
        assert op["query"]
        assert op["verify"]
        assert op["recovery"]


def test_publish_recovery_query_before_retry_is_true() -> None:
    """AC-FR1600-01: query_before_retry must be true; no blind retry."""
    payload = _payload("publish-recovery")
    assert payload["query_before_retry"] is True


def test_publish_recovery_idempotency_immutable_targets() -> None:
    """AC-FR1600-01: idempotency declares immutable tag/registry version."""
    payload = _payload("publish-recovery")
    idempotency = payload["idempotency"]
    assert "immutable" in idempotency
    assert "operation_id" in idempotency


def test_publish_recovery_credentials_pr_access_false() -> None:
    """AC-FR1600-01: PRs have no publish credential access."""
    credentials = _payload("publish-recovery")["credentials"]
    assert credentials["PR_access"] is False
    assert credentials["minimum_scope_per_operation"] is True
    assert "secret references" in credentials["storage"].lower()


def test_publish_recovery_deployment_na_for_local_package() -> None:
    """AC-FR1600-01: Louke has no independent deployment endpoint."""
    deployment = _payload("publish-recovery")["deployment"]
    assert deployment["applicable"] is False
    assert (
        "local" in deployment["reason"].lower()
        or "package" in deployment["reason"].lower()
    )


def test_publish_recovery_partial_success_is_needs_attention() -> None:
    """AC-FR1600-01: partial success moves to needs_attention, not retry/success."""
    partial = _payload("publish-recovery")["partial_success"]
    assert "needs_attention" in partial
    assert "preserve" in partial.lower()


def test_publish_recovery_preconditions_include_required_check() -> None:
    """AC-FR1600-01: preconditions include same-commit Louke CI / required success."""
    preconditions = _payload("publish-recovery")["preconditions"]
    text = " ".join(preconditions).lower()
    assert "louke ci" in text
    assert "if-bld-01" in text or "verified" in text


def test_publish_recovery_statuses_include_uncertain_and_needs_attention() -> None:
    """AC-FR1600-01: statuses include uncertain and needs_attention."""
    statuses = _payload("publish-recovery")["statuses"]
    expected = {"confirmed", "failed", "uncertain", "needs_attention"}
    assert expected <= set(statuses)


def test_publish_recovery_failure_policy_explicit_reasons() -> None:
    """AC-FR1600-01: failure policy fail_closed with explicit reasons."""
    policy = _payload("publish-recovery")["failure_policy"]
    assert policy["fail_closed"] is True
    expected = {
        "failed",
        "uncertain",
        "needs_attention",
        "conflict",
        "unknown",
    }
    assert expected <= set(policy["non_success"])


def test_publish_recovery_no_agent_cli_authority() -> None:
    """AC-FR1600-01: Agent has no CLI authority over publish operations."""
    commands = _payload("publish-recovery")["commands"]
    for cmd in commands:
        assert (
            "Agent" not in cmd["command"] or "no Agent CLI authority" in cmd["command"]
        )


def test_build_artifact_failure_policy_does_not_accept_source_declaration() -> None:
    """AC-FR1500-01: source declaration cannot substitute a verified artifact."""
    policy = _payload("build-artifact")["failure_policy"]
    assert policy["fail_closed"] is True
    # The contract must explicitly reject source-only verification
    non_success = set(policy["non_success"])
    assert "outlet-mismatch" in non_success
    assert "extract-failure" in non_success
