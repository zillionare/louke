"""Integration tests for FR-2700: Retry, waiver & cancel.

AC-FR2700-01: Runtime may only retry operations declared idempotent/
reconcile-safe by the WorkflowDefinition; each attempt is independent
and does NOT rewrite old facts. Red ref same-attempt retry requires
compare-and-set yielding the same commit; otherwise a new attempt is
allocated. Waiver applies only to current policy non-critical checks
and must bind actor/reason/scope/candidate/expiry; requirement
approval, release approval, trace/freshness, required CI, artifact
version, critical security and publish identity are NOT waivable.
Human may cancel unpublished runs; runs with published facts may only
enter recovery/close.

Interfaces covered (per interfaces.md):
- IF-WFR-01 (Primary ARC-01)
- IF-PUB-02 (publish recovery, ARC-15)
- IF-RGR-01 (Red ref CAS, ARC-05)
- IF-TRACE-01 (trace, ARC-16)
"""
# AC-FR2700-01

from __future__ import annotations

import pytest

from louke.runtime.retry_waiver import (
    ERROR_CODES,
    CancelDecision,
    RetryDecision,
    RetryWaiverError,
    WaiverDecision,
    WaiverEvaluation,
    evaluate_cancel,
    evaluate_retry,
    evaluate_waiver,
)


def _valid_waiver() -> WaiverDecision:
    return WaiverDecision(
        actor="security-officer",
        reason="residual risk accepted",
        scope="louke/v014/x.py",
        issue_id=42,
        expires_at="2026-12-31",
        policy_digest="sha256:policy",
    )


# ---------------------------------------------------------------------------
# evaluate_retry
# ---------------------------------------------------------------------------


@pytest.mark.real_module
def test_evaluate_retry_allows_idempotent_safe_within_max_attempts():
    """AC-FR2700-01: idempotent operation + within max -> new attempt allocated."""
    decision = evaluate_retry(
        operation_kind="query-ledger",
        idempotent_safe=True,
        prior_attempts=1,
        max_attempts=3,
    )
    assert isinstance(decision, RetryDecision)
    assert decision.allowed is True
    assert decision.new_attempt_no == 2


@pytest.mark.real_module
def test_evaluate_retry_rejects_non_idempotent_operation():
    """AC-FR2700-01: non-idempotent operation cannot be retried."""
    with pytest.raises(RetryWaiverError) as exc:
        evaluate_retry(
            operation_kind="create-tag",
            idempotent_safe=False,
            prior_attempts=0,
            max_attempts=3,
        )
    assert exc.value.code == "RETRY_NOT_IDEMPOTENT"


@pytest.mark.real_module
def test_evaluate_retry_rejects_max_attempts_exceeded():
    """AC-FR2700-01: prior_attempts >= max -> RETRY_MAX_ATTEMPTS_EXCEEDED."""
    with pytest.raises(RetryWaiverError) as exc:
        evaluate_retry(
            operation_kind="query-ledger",
            idempotent_safe=True,
            prior_attempts=3,
            max_attempts=3,
        )
    assert exc.value.code == "RETRY_MAX_ATTEMPTS_EXCEEDED"


# ---------------------------------------------------------------------------
# evaluate_waiver
# ---------------------------------------------------------------------------


@pytest.mark.real_module
def test_evaluate_waiver_allows_medium_severity_with_full_metadata():
    """AC-FR2700-01: medium severity + full metadata -> allowed."""
    result = evaluate_waiver(
        gate_name="lint",
        severity="medium",
        waiver=_valid_waiver(),
    )
    assert isinstance(result, WaiverEvaluation)
    assert result.allowed is True


@pytest.mark.real_module
def test_evaluate_waiver_forbidden_for_required_ci():
    """AC-FR2700-01: required CI is non-waivable."""
    with pytest.raises(RetryWaiverError) as exc:
        evaluate_waiver(
            gate_name="required-ci",
            severity="low",
            waiver=_valid_waiver(),
        )
    assert exc.value.code == "WAIVER_FORBIDDEN"


@pytest.mark.real_module
def test_evaluate_waiver_forbidden_for_release_approval():
    """AC-FR2700-01: release approval is non-waivable."""
    with pytest.raises(RetryWaiverError) as exc:
        evaluate_waiver(
            gate_name="release-approval",
            severity="low",
            waiver=_valid_waiver(),
        )
    assert exc.value.code == "WAIVER_FORBIDDEN"


@pytest.mark.real_module
def test_evaluate_waiver_forbidden_for_critical_severity():
    """AC-FR2700-01: critical severity is non-waivable."""
    with pytest.raises(RetryWaiverError) as exc:
        evaluate_waiver(
            gate_name="lint",
            severity="critical",
            waiver=_valid_waiver(),
        )
    assert exc.value.code == "WAIVER_FORBIDDEN"


@pytest.mark.real_module
def test_evaluate_waiver_forbidden_for_high_severity():
    """AC-FR2700-01: high severity is non-waivable."""
    with pytest.raises(RetryWaiverError) as exc:
        evaluate_waiver(
            gate_name="lint",
            severity="high",
            waiver=_valid_waiver(),
        )
    assert exc.value.code == "WAIVER_FORBIDDEN"


@pytest.mark.real_module
def test_evaluate_waiver_invalid_when_metadata_missing():
    """AC-FR2700-01: waiver must bind actor/reason/scope/issue/expiry/policy."""
    result = evaluate_waiver(
        gate_name="lint",
        severity="medium",
        waiver=None,
    )
    assert result.allowed is False
    assert result.reason_code == "WAIVER_INVALID"


@pytest.mark.real_module
def test_non_waivable_gates_includes_all_documented_gates():
    """AC-FR2700-01: non-waivable list includes required CI, release approval,
    trace/freshness, artifact version, critical security, publish identity,
    requirement approval."""
    from louke.runtime.retry_waiver import _NON_WAIVABLE_GATES

    expected = {
        "required-ci",
        "release-approval",
        "trace-freshness",
        "artifact-version",
        "critical-security",
        "publish-identity",
        "requirement-approval",
    }
    actual = set(_NON_WAIVABLE_GATES)
    missing = expected - actual
    assert not missing, f"non-waivable gates missing: {missing}"


# ---------------------------------------------------------------------------
# evaluate_cancel
# ---------------------------------------------------------------------------


@pytest.mark.real_module
def test_evaluate_cancel_allows_human_for_unpublished_run():
    """AC-FR2700-01: Human may cancel unpublished run."""
    decision = evaluate_cancel(has_published_facts=False, actor_role="human")
    assert isinstance(decision, CancelDecision)
    assert decision.allowed is True
    assert decision.new_state == "cancelled"


@pytest.mark.real_module
def test_evaluate_cancel_rejects_agent_initiated_cancel():
    """AC-FR2700-01: only Human may cancel; Agents cannot."""
    with pytest.raises(RetryWaiverError) as exc:
        evaluate_cancel(has_published_facts=False, actor_role="devon")
    assert exc.value.code == "CANCEL_FORBIDDEN_AGENT"


@pytest.mark.real_module
def test_evaluate_cancel_rejects_after_published_facts():
    """AC-FR2700-01: published facts -> only recovery/close; no cancel."""
    with pytest.raises(RetryWaiverError) as exc:
        evaluate_cancel(has_published_facts=True, actor_role="human")
    assert exc.value.code == "CANCEL_FORBIDDEN_AFTER_EFFECT"


@pytest.mark.real_module
def test_error_codes_set_covers_all_documented_codes():
    """AC-FR2700-01: ERROR_CODES includes all codes from interfaces.md (§4 row)."""
    expected = {
        "RETRY_NOT_IDEMPOTENT",
        "RETRY_MAX_ATTEMPTS_EXCEEDED",
        "WAIVER_FORBIDDEN",
        "WAIVER_INVALID",
        "CANCEL_FORBIDDEN_AFTER_EFFECT",
        "CANCEL_FORBIDDEN_AGENT",
    }
    actual = set(ERROR_CODES)
    missing = expected - actual
    assert not missing, f"ERROR_CODES missing: {missing}"
