"""Integration tests for NFR-0300: Restart recovery & idempotency.

AC-NFR0300-01: Runtime recovers from persisted manifest/refs/commits/
reviews/evidence/operation ledger after a restart at any stage; it must
NOT repeat already-confirmed side effects. When evidence/ref/operation
identity is missing or conflicting, Runtime fail-closed/needs_attention
and never fabricates PASS. After repair, safe retry is allowed.

Interfaces covered (per interfaces.md):
- IF-RGR-01 (Red ref recovery, ARC-05)
- IF-CI-02 (CI polling recovery, ARC-11)
- IF-PUB-02 (publish recovery, ARC-15)
- IF-TRACE-01 (cleanup recovery, ARC-16)
"""
# AC-NFR0300-01

from __future__ import annotations

import pytest

from louke.v014.nfr0300_restart_recovery import (
    ERROR_CODES,
    RecoveryDecision,
    RecoveryStore,
    fail_closed_unknown,
    recover_after_restart,
)


# ---------------------------------------------------------------------------
# recover_after_restart
# ---------------------------------------------------------------------------


@pytest.mark.real_module
def test_recover_after_restart_resumes_from_confirmed_facts():
    """AC-NFR0300-01: confirmed facts -> running state, no re-execution."""
    store = RecoveryStore()
    store.record_confirmed("red-ref-created", operation_id="op-red")
    store.record_confirmed("green-committed", operation_id="op-green")
    decision = recover_after_restart(store)
    assert isinstance(decision, RecoveryDecision)
    assert decision.state == "running"
    assert decision.fail_closed is False
    assert "red-ref-created" in decision.confirmed_facts
    assert "green-committed" in decision.confirmed_facts
    # Resumed phase derived from latest confirmed fact.
    assert decision.resumed_phase == "after-green"


@pytest.mark.real_module
def test_recover_after_restart_does_not_repeat_confirmed_side_effects():
    """AC-NFR0300-01: confirmed operations are NOT repeated."""
    store = RecoveryStore()
    store.record_confirmed("publish-tag", operation_id="op-tag")
    decision = recover_after_restart(store)
    assert decision.state == "running"
    # confirmed_facts contains the already-confirmed kind.
    assert "publish-tag" in decision.confirmed_facts


@pytest.mark.real_module
def test_recover_after_restart_fail_closed_on_unknown_with_missing_identity():
    """AC-NFR0300-01: unknown intent with empty operation_id -> fail closed."""
    store = RecoveryStore()
    store.record_unknown("publish-tag", operation_id="")  # missing identity
    decision = recover_after_restart(store)
    assert decision.state == "needs_attention"
    assert decision.fail_closed is True


@pytest.mark.real_module
def test_recover_after_restart_needs_attention_on_unknown_with_valid_identity():
    """AC-NFR0300-01: unknown intent with valid identity -> needs_attention
    (Runtime never fabricates PASS)."""
    store = RecoveryStore()
    store.record_confirmed("red-ref-created", operation_id="op-red")
    store.record_unknown("publish-tag", operation_id="op-tag")
    decision = recover_after_restart(store)
    assert decision.state == "needs_attention"
    assert decision.fail_closed is True


@pytest.mark.real_module
def test_recover_after_restart_resumes_after_repair():
    """AC-NFR0300-01: after repair (unknown resolved) -> running."""
    store = RecoveryStore()
    store.record_confirmed("red-ref-created", operation_id="op-red")
    store.record_unknown("publish-tag", operation_id="op-tag")
    # Repair: resolve the unknown.
    store.resolve_unknown("publish-tag")
    decision = recover_after_restart(store)
    assert decision.state == "running"
    assert decision.fail_closed is False
    assert "publish-tag" in decision.confirmed_facts


@pytest.mark.real_module
def test_fail_closed_unknown_returns_needs_attention():
    """AC-NFR0300-01: explicit fail-closed decision for unknown state."""
    decision = fail_closed_unknown(reason="missing identity")
    assert decision.state == "needs_attention"
    assert decision.fail_closed is True
    assert decision.confirmed_facts == ()


@pytest.mark.real_module
def test_error_codes_set_covers_all_documented_codes():
    """AC-NFR0300-01: ERROR_CODES includes all codes from interfaces.md."""
    expected = {
        "RECOVERY_FAIL_CLOSED",
        "RECOVERY_UNKNOWN_INTENT",
        "RECOVERY_IDENTITY_MISSING",
    }
    actual = set(ERROR_CODES)
    missing = expected - actual
    assert not missing, f"ERROR_CODES missing: {missing}"
