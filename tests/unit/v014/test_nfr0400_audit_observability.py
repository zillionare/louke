"""AC-NFR0400-01: Audit & observability.

History API/UI must be able to query each task/gate/review/ref/commit/CI/
artifact/finding/Human decision/operation for actor, timestamp, attempt,
input/output identity and state.  PASS/FAIL/STALE/SKIP/UNKNOWN must remain
semantically distinct in storage and presentation; summary text cannot
overwrite original evidence.
"""

from __future__ import annotations


import pytest

from louke.v014.nfr0400_audit_observability import (
    AuditEvent,
    AuditStore,
    EvidenceStatus,
    audit_query,
    record_event,
    summarize,
)

_RUN = "run-1"


def test_record_event_binds_actor_timestamp_attempt_identity() -> None:
    """AC-NFR0400-01: each event carries actor/time/attempt/input/output identity."""
    store = AuditStore()
    event = record_event(
        store,
        run_id=_RUN,
        kind="task-completed",
        actor="runtime:program",
        attempt_no=1,
        input_identities=("ev-1", "ev-2"),
        output_identity="ev-out-1",
        state="PASS",
    )
    assert isinstance(event, AuditEvent)
    assert event.actor == "runtime:program"
    assert event.attempt_no == 1
    assert event.input_identities == ("ev-1", "ev-2")
    assert event.output_identity == "ev-out-1"
    assert event.state == EvidenceStatus.PASS
    assert event.event_id  # stable id
    assert event.observed_at  # timestamp


def test_audit_query_returns_full_history() -> None:
    """AC-NFR0400-01: history API returns full event list with all fields."""
    store = AuditStore()
    record_event(
        store,
        run_id=_RUN,
        kind="task-1",
        actor="devon:1",
        attempt_no=1,
        input_identities=("ev-1",),
        output_identity="ev-2",
        state="PASS",
    )
    record_event(
        store,
        run_id=_RUN,
        kind="task-2",
        actor="devon:1",
        attempt_no=1,
        input_identities=("ev-3",),
        output_identity="ev-4",
        state="FAIL",
    )
    events = audit_query(store, run_id=_RUN)
    assert len(events) == 2
    assert events[0].kind == "task-1"
    assert events[1].kind == "task-2"


def test_audit_query_filters_by_kind() -> None:
    """AC-NFR0400-01: history API supports filtering by event kind."""
    store = AuditStore()
    record_event(
        store,
        run_id=_RUN,
        kind="gate",
        actor="runtime",
        attempt_no=1,
        input_identities=(),
        output_identity="",
        state="PASS",
    )
    record_event(
        store,
        run_id=_RUN,
        kind="review",
        actor="prism",
        attempt_no=1,
        input_identities=(),
        output_identity="",
        state="PASS",
    )
    events = audit_query(store, run_id=_RUN, kind="review")
    assert len(events) == 1
    assert events[0].kind == "review"


def test_evidence_status_distinct_in_storage() -> None:
    """AC-NFR0400-01: PASS/FAIL/STALE/SKIP/UNKNOWN are distinct enum values."""
    statuses = {
        EvidenceStatus.PASS,
        EvidenceStatus.FAIL,
        EvidenceStatus.STALE,
        EvidenceStatus.SKIP,
        EvidenceStatus.UNKNOWN,
    }
    assert len(statuses) == 5
    assert all(
        s != s2 for i, s in enumerate(statuses) for s2 in list(statuses)[i + 1 :]
    )


def test_summary_does_not_overwrite_original_evidence() -> None:
    """AC-NFR0400-01: summary text cannot change original evidence status/bytes."""
    store = AuditStore()
    record_event(
        store,
        run_id=_RUN,
        kind="gate",
        actor="runtime",
        attempt_no=1,
        input_identities=("ev-1",),
        output_identity="ev-2",
        state="FAIL",
    )
    summary = summarize(store, run_id=_RUN)
    assert "FAIL" in summary
    # The original event still has FAIL state, not overwritten.
    events = audit_query(store, run_id=_RUN)
    assert events[0].state == EvidenceStatus.FAIL


def test_audit_query_returns_empty_for_unknown_run() -> None:
    """AC-NFR0400-01: unknown run returns empty list (not error)."""
    store = AuditStore()
    events = audit_query(store, run_id="run-nonexistent")
    assert events == []


def test_audit_event_immutable() -> None:
    """AC-NFR0400-01: audit events are immutable."""
    store = AuditStore()
    event = record_event(
        store,
        run_id=_RUN,
        kind="x",
        actor="a",
        attempt_no=1,
        input_identities=(),
        output_identity="",
        state="PASS",
    )
    with pytest.raises(Exception):
        event.state = EvidenceStatus.FAIL  # type: ignore[misc]
