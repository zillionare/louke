"""Integration tests for NFR-0400: Audit & observability.

AC-NFR0400-01: History API/UI can query each task/gate/review/ref/
commit/CI/artifact/finding/Human decision/operation for actor,
timestamp, attempt, input/output identity and state. PASS/FAIL/STALE/
SKIP/UNKNOWN must remain semantically distinct in storage and
presentation; summary text cannot overwrite original evidence.

Interfaces covered (per interfaces.md):
- IF-TRACE-01 (Primary ARC-16)
- IF-WFR-01 (history projection, ARC-01)
"""
# AC-NFR0400-01

from __future__ import annotations

import pytest

from louke.runtime.audit_observability import (
    AuditEvent,
    AuditStore,
    EvidenceStatus,
    audit_query,
    record_event,
    summarize,
)


# ---------------------------------------------------------------------------
# EvidenceStatus distinct values
# ---------------------------------------------------------------------------


@pytest.mark.real_module
def test_evidence_status_has_five_distinct_values():
    """AC-NFR0400-01: PASS/FAIL/STALE/SKIP/UNKNOWN are semantically distinct.

    v0.14-004 (IF-AUDIT-01) extends the enum with lowercase canonical
    names (``queued``, ``running``, ``passed``, ``failed``,
    ``uncertain``) so the v0.14-004 audit envelope can carry the
    contract vocabulary. Both vocabularies are valid; legacy
    v0.14-003 callers continue to use the uppercase spelling.
    """
    expected_v14_003 = {"PASS", "FAIL", "STALE", "SKIP", "UNKNOWN"}
    expected_v14_004 = {"queued", "running", "passed", "failed", "uncertain"}
    actual = {s.value for s in EvidenceStatus}
    # Both vocabularies must be present in the enum.
    assert expected_v14_003 <= actual
    assert expected_v14_004 <= actual
    # The union is exactly the two vocabularies.
    assert actual == expected_v14_003 | expected_v14_004


# ---------------------------------------------------------------------------
# record_event + audit_query
# ---------------------------------------------------------------------------


@pytest.mark.real_module
def test_record_event_persists_actor_time_attempt_identity_state():
    """AC-NFR0400-01: every event has actor/timestamp/attempt/input+output identity/state."""
    store = AuditStore()
    event = record_event(
        store,
        run_id="run-001",
        kind="task-completed",
        actor="runtime:program",
        attempt_no=1,
        input_identities=("ev-1", "ev-2"),
        output_identity="ev-out",
        state="PASS",
    )
    assert isinstance(event, AuditEvent)
    assert event.run_id == "run-001"
    assert event.kind == "task-completed"
    assert event.actor == "runtime:program"
    assert event.attempt_no == 1
    assert event.input_identities == ("ev-1", "ev-2")
    assert event.output_identity == "ev-out"
    assert event.state == EvidenceStatus.PASS
    assert event.observed_at  # timestamp present
    assert event.event_id.startswith("ev:")


@pytest.mark.real_module
def test_audit_query_returns_all_events_for_run():
    """AC-NFR0400-01: query returns every event for the run."""
    store = AuditStore()
    for i in range(3):
        record_event(
            store,
            run_id="run-001",
            kind=f"kind-{i}",
            actor="x",
            attempt_no=i,
            input_identities=(),
            output_identity="x",
            state="PASS",
        )
    events = audit_query(store, run_id="run-001")
    assert len(events) == 3


@pytest.mark.real_module
def test_audit_query_filters_by_kind():
    """AC-NFR0400-01: query with kind filter returns only matching events."""
    store = AuditStore()
    record_event(
        store,
        run_id="r1",
        kind="task-completed",
        actor="x",
        attempt_no=1,
        input_identities=(),
        output_identity="x",
        state="PASS",
    )
    record_event(
        store,
        run_id="r1",
        kind="ci-passed",
        actor="x",
        attempt_no=1,
        input_identities=(),
        output_identity="x",
        state="PASS",
    )
    events = audit_query(store, run_id="r1", kind="ci-passed")
    assert len(events) == 1
    assert events[0].kind == "ci-passed"


# ---------------------------------------------------------------------------
# Status distinctness in storage
# ---------------------------------------------------------------------------


@pytest.mark.real_module
def test_audit_events_keep_distinct_status_in_storage():
    """AC-NFR0400-01: PASS/FAIL/STALE/SKIP/UNKNOWN stored distinctly."""
    store = AuditStore()
    for status in ("PASS", "FAIL", "STALE", "SKIP", "UNKNOWN"):
        record_event(
            store,
            run_id="r1",
            kind=f"event-{status}",
            actor="x",
            attempt_no=1,
            input_identities=(),
            output_identity="x",
            state=status,
        )
    events = audit_query(store, run_id="r1")
    statuses = {e.state.value for e in events}
    assert statuses == {"PASS", "FAIL", "STALE", "SKIP", "UNKNOWN"}


# ---------------------------------------------------------------------------
# summarize cannot overwrite original evidence
# ---------------------------------------------------------------------------


@pytest.mark.real_module
def test_summarize_does_not_overwrite_original_evidence():
    """AC-NFR0400-01: summary text cannot change stored state or bytes."""
    store = AuditStore()
    record_event(
        store,
        run_id="r1",
        kind="task-completed",
        actor="runtime",
        attempt_no=1,
        input_identities=(),
        output_identity="ev-out",
        state="PASS",
    )
    summary_text = summarize(store, run_id="r1")
    assert "task-completed" in summary_text
    assert "PASS" in summary_text
    # Original event state is still PASS.
    events = audit_query(store, run_id="r1")
    assert events[0].state == EvidenceStatus.PASS


@pytest.mark.real_module
def test_summarize_returns_no_events_for_empty_run():
    """AC-NFR0400-01: empty run -> 'no events' summary."""
    store = AuditStore()
    summary_text = summarize(store, run_id="empty-run")
    assert "no events" in summary_text


# ---------------------------------------------------------------------------
# Append-only audit store
# ---------------------------------------------------------------------------


@pytest.mark.real_module
def test_audit_store_is_append_only():
    """AC-NFR0400-01: events cannot be removed or modified after append."""
    store = AuditStore()
    e1 = record_event(
        store,
        run_id="r1",
        kind="k1",
        actor="x",
        attempt_no=1,
        input_identities=(),
        output_identity="x",
        state="PASS",
    )
    events_before_count = len(audit_query(store, run_id="r1"))
    # Append another event.
    record_event(
        store,
        run_id="r1",
        kind="k2",
        actor="y",
        attempt_no=2,
        input_identities=(),
        output_identity="y",
        state="FAIL",
    )
    events_after = audit_query(store, run_id="r1")
    # Original event unchanged.
    assert events_after[0] == e1
    assert len(events_after) == events_before_count + 1
