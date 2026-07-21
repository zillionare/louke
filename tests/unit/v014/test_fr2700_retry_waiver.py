"""AC-FR2700-01: Retry, waiver & cancel.

Runtime may only retry operations declared idempotent/reconcile-safe by
the WorkflowDefinition; each attempt is independent and does NOT rewrite
old facts.  Red ref same-attempt retry requires compare-and-set yielding
the same commit; otherwise a new attempt is allocated.  Waiver applies
only to current policy non-critical checks and must bind actor/reason/
scope/candidate/expiry; requirement approval, release approval, trace/
freshness, required CI, artifact version, critical security and publish
identity are NOT waivable.  Human may cancel unpublished runs; runs with
published facts may only enter recovery/close.
"""

from __future__ import annotations

import pytest

from louke.v014.fr2700_retry_waiver import (
    CancelDecision,
    RetryDecision,
    RetryWaiverError,
    WaiverDecision,
    evaluate_cancel,
    evaluate_retry,
    evaluate_waiver,
)

_CAND = "cand:abc"


def test_evaluate_retry_allows_idempotent_operation() -> None:
    """AC-FR2700-01: only idempotent operations may be retried."""
    decision = evaluate_retry(
        operation_kind="tag",
        idempotent_safe=True,
        prior_attempts=2,
        max_attempts=5,
    )
    assert isinstance(decision, RetryDecision)
    assert decision.allowed is True
    assert decision.new_attempt_no == 3


def test_evaluate_retry_rejects_non_idempotent() -> None:
    """AC-FR2700-01: non-idempotent operation may not be retried."""
    with pytest.raises(RetryWaiverError) as exc:
        evaluate_retry(
            operation_kind="custom-side-effect",
            idempotent_safe=False,
            prior_attempts=0,
            max_attempts=3,
        )
    assert exc.value.code == "RETRY_NOT_IDEMPOTENT"


def test_evaluate_retry_rejects_max_attempts_exceeded() -> None:
    """AC-FR2700-01: attempts cannot exceed max_attempts."""
    with pytest.raises(RetryWaiverError) as exc:
        evaluate_retry(
            operation_kind="tag",
            idempotent_safe=True,
            prior_attempts=3,
            max_attempts=3,
        )
    assert exc.value.code == "RETRY_MAX_ATTEMPTS_EXCEEDED"


def test_evaluate_waiver_rejects_non_waivable_gate() -> None:
    """AC-FR2700-01: required CI, release approval, etc. cannot be waived."""
    for gate in (
        "required-ci",
        "release-approval",
        "trace-freshness",
        "artifact-version",
        "critical-security",
        "publish-identity",
        "requirement-approval",
    ):
        with pytest.raises(RetryWaiverError) as exc:
            evaluate_waiver(gate_name=gate, severity="medium")
        assert exc.value.code == "WAIVER_FORBIDDEN"


def test_evaluate_waiver_allows_non_critical_with_metadata() -> None:
    """AC-FR2700-01: medium/low non-critical check may be waived with full metadata."""
    waiver = WaiverDecision(
        actor="human:bob",
        reason="acceptable",
        scope="tests/legacy/",
        issue_id=999,
        expires_at="2026-12-31",
        policy_digest="sha256:" + "p" * 64,
    )
    decision = evaluate_waiver(
        gate_name="lint-warning",
        severity="medium",
        waiver=waiver,
    )
    assert decision.allowed is True


def test_evaluate_waiver_rejects_missing_metadata() -> None:
    """AC-FR2700-01: waiver must bind actor/reason/scope/candidate/expiry."""
    decision = evaluate_waiver(gate_name="lint-warning", severity="medium")
    assert decision.allowed is False
    assert decision.reason_code == "WAIVER_INVALID"


def test_evaluate_cancel_allows_unpublished_run() -> None:
    """AC-FR2700-01: Human may cancel unpublished run."""
    decision = evaluate_cancel(has_published_facts=False, actor_role="human")
    assert isinstance(decision, CancelDecision)
    assert decision.allowed is True
    assert decision.new_state == "cancelled"


def test_evaluate_cancel_rejects_run_with_published_facts() -> None:
    """AC-FR2700-01: runs with published facts may only enter recovery/close."""
    with pytest.raises(RetryWaiverError) as exc:
        evaluate_cancel(has_published_facts=True, actor_role="human")
    assert exc.value.code == "CANCEL_FORBIDDEN_AFTER_EFFECT"


def test_evaluate_cancel_rejects_agent_initiated() -> None:
    """AC-FR2700-01: Agents cannot cancel runs; only Human may."""
    with pytest.raises(RetryWaiverError) as exc:
        evaluate_cancel(has_published_facts=False, actor_role="devon")
    assert exc.value.code == "CANCEL_FORBIDDEN_AGENT"
