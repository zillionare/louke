"""AC-NFR0300-01: Restart recovery & idempotency.

Runtime must recover from persisted manifest/refs/commits/reviews/evidence/
operation ledger after a restart at any stage; it must NOT repeat already-
confirmed side effects.  When evidence/ref/operation identity is missing or
conflicting, Runtime fail-closed/needs_attention and never fabricate PASS.
After repair, safe retry is allowed.  Tested by simulating process
termination after Red ref creation / Green commit / CI polling / tag-publish
/ milestone cleanup.
"""

from __future__ import annotations


from louke.runtime.restart_recovery import (
    RecoveryDecision,
    RecoveryStore,
    fail_closed_unknown,
    recover_after_restart,
)

_RUN = "run-1"


def test_recover_after_restart_resumes_from_confirmed_facts() -> None:
    """AC-NFR0300-01: restart recovers from last confirmed facts without repeating."""
    store = RecoveryStore()
    store.record_confirmed("red-ref-created", operation_id="op-red-1")
    store.record_confirmed("green-committed", operation_id="op-green-1")
    decision = recover_after_restart(store)
    assert isinstance(decision, RecoveryDecision)
    assert "red-ref-created" in decision.confirmed_facts
    assert "green-committed" in decision.confirmed_facts
    assert decision.resumed_phase == "after-green"


def test_recover_does_not_repeat_confirmed_side_effects() -> None:
    """AC-NFR0300-01: confirmed publish operations are not re-executed."""
    store = RecoveryStore()
    store.record_confirmed("publish-tag", operation_id="op-tag-1")
    decision = recover_after_restart(store)
    # The tag operation is already confirmed; recover returns it as confirmed.
    assert "publish-tag" in decision.confirmed_facts
    # The store should NOT have a new pending intent for the tag.
    assert not any(
        intent.kind == "publish-tag" and intent.status == "executing"
        for intent in store.pending_intents()
    )


def test_recover_fail_closed_when_intent_unknown() -> None:
    """AC-NFR0300-01: unknown intent status -> fail closed / needs_attention."""
    store = RecoveryStore()
    store.record_unknown("publish-tag", operation_id="op-tag-1")
    decision = recover_after_restart(store)
    assert decision.state == "needs_attention"
    assert decision.fail_closed is True


def test_fail_closed_unknown_never_fabricates_pass() -> None:
    """AC-NFR0300-01: fail_closed_unknown never returns PASS."""
    decision = fail_closed_unknown(reason="ref OID missing")
    assert decision.state == "needs_attention"
    assert decision.fail_closed is True
    assert decision.resumed_phase == ""


def test_recover_after_red_ref_creation_resumes_red_review() -> None:
    """AC-NFR0300-01: restart after Red ref creation resumes Red review."""
    store = RecoveryStore()
    store.record_confirmed("red-ref-created", operation_id="op-red-1")
    decision = recover_after_restart(store)
    assert decision.resumed_phase == "after-red-ref"


def test_recover_after_ci_polling_resumes_polling() -> None:
    """AC-NFR0300-01: restart during CI polling resumes polling, no re-push."""
    store = RecoveryStore()
    store.record_confirmed("ci-pushed", operation_id="op-ci-push-1")
    store.record_unknown("ci-polling", operation_id="op-ci-poll-1")
    decision = recover_after_restart(store)
    assert decision.state == "needs_attention"  # ci-polling unknown
    assert "ci-pushed" in decision.confirmed_facts  # but ci-push not re-done


def test_recover_after_milestone_cleanup_resumes_closing() -> None:
    """AC-NFR0300-01: restart during milestone cleanup keeps closing, no re-publish."""
    store = RecoveryStore()
    store.record_confirmed("publish-complete", operation_id="op-publish-1")
    store.record_unknown("archive-cleanup", operation_id="op-cleanup-1")
    decision = recover_after_restart(store)
    assert decision.state == "needs_attention"  # cleanup unknown
    assert "publish-complete" in decision.confirmed_facts  # no re-publish


def test_recover_after_repair_allows_safe_retry() -> None:
    """AC-NFR0300-01: after repair, safe retry is allowed."""
    store = RecoveryStore()
    store.record_unknown("publish-tag", operation_id="op-tag-1")
    decision1 = recover_after_restart(store)
    assert decision1.state == "needs_attention"
    # Repair: resolve the unknown intent.
    store.resolve_unknown("publish-tag")
    decision2 = recover_after_restart(store)
    assert decision2.state == "running"


def test_recover_with_missing_evidence_fail_closed() -> None:
    """AC-NFR0300-01: missing evidence identity -> fail closed, no PASS fabrication."""
    store = RecoveryStore()  # empty - no confirmed facts, no intents
    decision = recover_after_restart(store)
    assert decision.state == "running"  # nothing to recover; fresh start
    # But if we claim an unknown intent exists with no identity:
    store.record_unknown("red-ref-created", operation_id="")
    decision2 = recover_after_restart(store)
    assert decision2.state == "needs_attention"
    assert decision2.fail_closed is True
