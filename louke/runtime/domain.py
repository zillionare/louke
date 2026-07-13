"""Immutable command/result/value schema and error classification for Runtime."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


class RuntimeStateError(Exception):
    """Base class for workflow runtime state errors."""


class RevisionConflictError(RuntimeStateError):
    """Raised when an update is based on a stale revision."""

    def __init__(
        self,
        message: str,
        current_revision: int | None = None,
    ) -> None:
        super().__init__(message)
        self.current_revision = current_revision


class IllegalTransitionError(RuntimeStateError):
    """Raised when a requested transition is not allowed by the definition."""


class UndeclaredResultError(RuntimeStateError):
    """Raised when a step result does not match any declared transition."""


@dataclass(frozen=True, slots=True)
class RuntimeCommand:
    """A request for Runtime to advance a run.

    Attributes:
        run_id: The opaque run identifier.
        expected_revision: The revision the caller last observed.
        result: The outcome of the current step, if any.
        requested_next_step: A caller-supplied target step; Runtime ignores it
            when a matching declared transition exists and rejects the command
            when it is the only payload.
        idempotency_key: Optional stable key for the step attempt.  When a
            command with the same key has already been committed, Runtime
            returns the previously committed outcome without re-executing the
            step or advancing state again.
    """

    run_id: str
    expected_revision: int
    result: str | None = None
    requested_next_step: str | None = None
    idempotency_key: str | None = None


@dataclass(frozen=True, slots=True)
class WorkflowEvent:
    """An append-only workflow event.

    Attributes:
        event_id: Opaque stable identifier.
        run_id: Opaque run identifier.
        sequence: Monotonic sequence number within the run.
        type: Stable event type.
        at: ISO 8601 UTC timestamp.
        actor: Actor metadata (kind, id).
        from_step: Previous step, if applicable.
        to_step: New step, if applicable.
        revision: Run revision at which the event was committed.
        details: Redacted event details.
    """

    event_id: str
    run_id: str
    sequence: int
    type: str
    at: str
    actor: dict[str, str] = field(default_factory=dict)
    from_step: str | None = None
    to_step: str | None = None
    revision: int = 0
    details: dict[str, Any] = field(default_factory=dict)
