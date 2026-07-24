"""NFR-0400: Audit & observability.

History API/UI must be able to query each task/gate/review/ref/commit/CI/
artifact/finding/Human decision/operation for actor, timestamp, attempt,
input/output identity and state.  PASS/FAIL/STALE/SKIP/UNKNOWN must remain
semantically distinct in storage and presentation; summary text cannot
overwrite original evidence (AC-NFR0400-01).
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from enum import Enum


class EvidenceStatus(str, Enum):
    """Stable evidence status values (AC-NFR0400-01, IF-AUDIT-01).

    The v0.14-004 contract (interfaces §IF-AUDIT-01) requires the
    audit envelope to use ``queued|running|passed|failed|uncertain``.
    The legacy ``PASS``/``FAIL``/``STALE``/``SKIP``/``UNKNOWN``
    values are retained as aliases so existing callers keep working
    while downstream surfaces migrate to the canonical vocabulary.
    """

    # v0.14-004 canonical vocabulary (interfaces §IF-AUDIT-01).
    QUEUED = "queued"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    UNCERTAIN = "uncertain"

    # Legacy aliases (v0.13.x) retained for backward compatibility.
    PASS = "passed"
    FAIL = "failed"
    STALE = "uncertain"
    SKIP = "failed"
    UNKNOWN = "uncertain"


@dataclass(frozen=True)
class AuditEvent:
    """An immutable audit event (AC-NFR0400-01).

    Attributes:
        event_id: Stable event identity.
        run_id: Bound run id.
        kind: Stable event kind (e.g. ``task-completed``).
        actor: Actor identity.
        attempt_no: Bound attempt number.
        input_identities: Tuple of input evidence ids.
        output_identity: Output evidence id.
        state: :class:`EvidenceStatus`.
        observed_at: RFC 3339 timestamp.
    """

    event_id: str
    run_id: str
    kind: str
    actor: str
    attempt_no: int
    input_identities: tuple[str, ...]
    output_identity: str
    state: EvidenceStatus
    observed_at: str


class AuditStore:
    """Append-only audit event store (AC-NFR0400-01)."""

    def __init__(self) -> None:
        self._events: list[AuditEvent] = []

    def append(self, event: AuditEvent) -> None:
        self._events.append(event)

    def query(self, *, run_id: str, kind: str | None = None) -> list[AuditEvent]:
        return [
            e
            for e in self._events
            if e.run_id == run_id and (kind is None or e.kind == kind)
        ]


def record_event(
    store: AuditStore,
    *,
    run_id: str,
    kind: str,
    actor: str,
    attempt_no: int,
    input_identities: tuple[str, ...],
    output_identity: str,
    state: str,
) -> AuditEvent:
    """Record an audit event in the store (AC-NFR0400-01)."""
    event = AuditEvent(
        event_id="ev:"
        + hashlib.sha256(
            f"{run_id}|{kind}|{actor}|{attempt_no}|{time.time_ns()}".encode()
        ).hexdigest()[:12],
        run_id=run_id,
        kind=kind,
        actor=actor,
        attempt_no=attempt_no,
        input_identities=tuple(input_identities),
        output_identity=output_identity,
        state=EvidenceStatus(state),
        observed_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    )
    store.append(event)
    return event


def audit_query(
    store: AuditStore, *, run_id: str, kind: str | None = None
) -> list[AuditEvent]:
    """Query audit events for a run, optionally filtered by kind (AC-NFR0400-01)."""
    return store.query(run_id=run_id, kind=kind)


def summarize(store: AuditStore, *, run_id: str) -> str:
    """Return a human-readable summary of run events (AC-NFR0400-01).

    The summary is derived from the original events; it cannot change the
    stored state or bytes.
    """
    events = store.query(run_id=run_id)
    if not events:
        return f"run {run_id}: no events"
    parts = [f"run {run_id}: {len(events)} events"]
    for e in events:
        parts.append(
            f"  - {e.kind} by {e.actor} attempt={e.attempt_no} state={e.state.value}"
        )
    return "\n".join(parts)
