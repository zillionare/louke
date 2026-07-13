"""Workflow event schema and builder for FR-0601.

This module formalises the append-only event stream required by FR-0601.  It
provides a stable event schema, a builder that produces events, and a validator
that rejects events missing required fields.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Protocol

from louke.runtime.domain import WorkflowEvent


class EventValidationError(ValueError):
    """Raised when an event violates the required FR-0601 schema."""


class _RunRef(Protocol):
    """Minimal shape of a WorkflowRun for event builders."""

    run_id: str
    current_step: str
    revision: int
    definition_id: str
    definition_version: str
    contract_digest: str


class _GateRef(Protocol):
    """Minimal shape of a Gate for gate decision events."""

    gate_id: str
    challenge_id: str
    step_id: str
    bound_digest: str


def new_correlation_id() -> str:
    """Return a new opaque correlation identifier."""
    return f"corr_{uuid.uuid4().hex[:12]}"


def digest_value(value: Any) -> str:
    """Return a deterministic sha256 digest of ``value``.

    Strings are digested directly; all other values are serialised as compact
    JSON first so the digest is stable.
    """
    if isinstance(value, str):
        content = value.encode("utf-8")
    else:
        content = json.dumps(value, sort_keys=True, separators=(",", ":")).encode(
            "utf-8"
        )
    return f"sha256:{hashlib.sha256(content).hexdigest()}"


class EventSchemaValidator:
    """Validate that events carry the fields required by FR-0601."""

    _CORE_REQUIRED: tuple[str, ...] = (
        "event_id",
        "run_id",
        "type",
        "at",
        "correlation_id",
    )
    _TYPE_REQUIRED: dict[str, tuple[str, ...]] = {
        "run.created": ("step_id", "input_digest", "output_digest"),
        "step.started": ("step_id", "attempt_id", "input_digest", "output_digest"),
        "step.completed": ("step_id", "attempt_id", "input_digest", "output_digest"),
        "step.blocked": ("step_id", "input_digest", "output_digest"),
        "step.retry": ("step_id", "attempt_id", "input_digest", "output_digest"),
        "step.transition": ("from_step", "to_step", "input_digest", "output_digest"),
        "step.handler_failed": (
            "step_id",
            "attempt_id",
            "input_digest",
            "output_digest",
        ),
        "step.result_undeclared": ("step_id", "input_digest", "output_digest"),
        "gate.created": ("step_id", "input_digest", "output_digest"),
        "gate.approved": ("step_id", "input_digest", "output_digest"),
        "gate.rejected": ("step_id", "input_digest", "output_digest"),
    }

    def validate(self, event: WorkflowEvent) -> None:
        """Validate ``event`` or raise ``EventValidationError``.

        Args:
            event: The event to validate.

        Raises:
            EventValidationError: If a required field is missing or empty.
        """
        missing = [
            field for field in self._CORE_REQUIRED if not getattr(event, field, None)
        ]
        if missing:
            raise EventValidationError(
                f"event missing core fields: {', '.join(missing)}"
            )

        required = self._TYPE_REQUIRED.get(event.type)
        if required is None:
            raise EventValidationError(f"unknown event type {event.type!r}")

        missing_type = [
            field for field in required if getattr(event, field, None) is None
        ]
        if missing_type:
            raise EventValidationError(
                f"event {event.type!r} missing fields: {', '.join(missing_type)}"
            )


def _build_event(
    run: _RunRef,
    event_type: str,
    *,
    step_id: str | None,
    attempt_id: str | None,
    actor: dict[str, str] | None,
    from_step: str | None,
    to_step: str | None,
    details: dict[str, Any] | None,
    input_digest: str | None,
    output_digest: str | None,
    correlation_id: str | None,
) -> WorkflowEvent:
    """Build and validate a ``WorkflowEvent``."""
    event = WorkflowEvent(
        event_id=f"evt_{uuid.uuid4().hex[:12]}",
        run_id=run.run_id,
        sequence=0,
        type=event_type,
        at=datetime.now(timezone.utc).isoformat(),
        actor=actor or {"kind": "runtime", "id": "runtime"},
        from_step=from_step,
        to_step=to_step,
        revision=run.revision,
        details=details or {},
        step_id=step_id,
        attempt_id=attempt_id,
        correlation_id=correlation_id or new_correlation_id(),
        input_digest=input_digest,
        output_digest=output_digest,
    )
    EventSchemaValidator().validate(event)
    return event


class EventBuilder:
    """Build schema-valid workflow events for a given run.

    Args:
        run: The run the event belongs to; only ``run_id``, ``current_step``
            and ``revision`` are used.
        correlation_id: Optional correlation id shared across a single request.
            When omitted a fresh id is generated.
    """

    def __init__(
        self,
        run: _RunRef,
        correlation_id: str | None = None,
    ) -> None:
        self._run = run
        self._correlation_id = correlation_id

    def build(
        self,
        event_type: str,
        *,
        step_id: str | None = None,
        attempt_id: str | None = None,
        actor: dict[str, str] | None = None,
        from_step: str | None = None,
        to_step: str | None = None,
        details: dict[str, Any] | None = None,
        input_digest: str | None = None,
        output_digest: str | None = None,
    ) -> WorkflowEvent:
        """Build an arbitrary schema-valid event.

        Callers should prefer the typed helpers below; ``build`` is useful for
        diagnostic or extension event types.
        """
        return _build_event(
            self._run,
            event_type,
            step_id=step_id,
            attempt_id=attempt_id,
            actor=actor,
            from_step=from_step,
            to_step=to_step,
            details=details,
            input_digest=input_digest,
            output_digest=output_digest,
            correlation_id=self._correlation_id,
        )

    def run_created(
        self,
        *,
        actor: dict[str, str] | None = None,
        details: dict[str, Any] | None = None,
        input_digest: str | None = None,
        output_digest: str | None = None,
    ) -> WorkflowEvent:
        """Build a ``run.created`` event."""
        merged_details = {"definition_id": self._run.definition_id}
        if details:
            merged_details.update(details)
        return _build_event(
            self._run,
            "run.created",
            step_id=self._run.current_step,
            attempt_id=None,
            actor=actor,
            from_step=None,
            to_step=self._run.current_step,
            details=merged_details,
            input_digest=input_digest or digest_value(self._run.contract_digest),
            output_digest=output_digest or self._run.contract_digest,
            correlation_id=self._correlation_id,
        )

    def step_started(
        self,
        step_id: str,
        attempt_id: str,
        *,
        actor: dict[str, str] | None = None,
        details: dict[str, Any] | None = None,
        input_digest: str | None = None,
        output_digest: str | None = None,
    ) -> WorkflowEvent:
        """Build a ``step.started`` event."""
        merged_details = {"step_id": step_id, "attempt_id": attempt_id}
        if details:
            merged_details.update(details)
        return _build_event(
            self._run,
            "step.started",
            step_id=step_id,
            attempt_id=attempt_id,
            actor=actor,
            from_step=None,
            to_step=None,
            details=merged_details,
            input_digest=input_digest or digest_value(step_id),
            output_digest=output_digest or digest_value(""),
            correlation_id=self._correlation_id,
        )

    def step_completed(
        self,
        step_id: str,
        attempt_id: str,
        *,
        result: str | None = None,
        actor: dict[str, str] | None = None,
        details: dict[str, Any] | None = None,
        input_digest: str | None = None,
        output_digest: str | None = None,
    ) -> WorkflowEvent:
        """Build a ``step.completed`` event."""
        merged_details = {"step_id": step_id, "attempt_id": attempt_id}
        if result is not None:
            merged_details["result"] = result
        if details:
            merged_details.update(details)
        return _build_event(
            self._run,
            "step.completed",
            step_id=step_id,
            attempt_id=attempt_id,
            actor=actor,
            from_step=None,
            to_step=None,
            details=merged_details,
            input_digest=input_digest or digest_value(step_id),
            output_digest=output_digest or digest_value(result or ""),
            correlation_id=self._correlation_id,
        )

    def step_blocked(
        self,
        step_id: str,
        *,
        reason: str | None = None,
        actor: dict[str, str] | None = None,
        input_digest: str | None = None,
        output_digest: str | None = None,
    ) -> WorkflowEvent:
        """Build a ``step.blocked`` event."""
        details: dict[str, Any] = {"step_id": step_id}
        if reason is not None:
            details["reason"] = reason
        return _build_event(
            self._run,
            "step.blocked",
            step_id=step_id,
            attempt_id=None,
            actor=actor,
            from_step=None,
            to_step=None,
            details=details,
            input_digest=input_digest or digest_value(step_id),
            output_digest=output_digest or digest_value(""),
            correlation_id=self._correlation_id,
        )

    def step_retry(
        self,
        step_id: str,
        attempt_id: str,
        *,
        reason: str | None = None,
        actor: dict[str, str] | None = None,
        input_digest: str | None = None,
        output_digest: str | None = None,
    ) -> WorkflowEvent:
        """Build a ``step.retry`` event."""
        details: dict[str, Any] = {"step_id": step_id, "attempt_id": attempt_id}
        if reason is not None:
            details["reason"] = reason
        return _build_event(
            self._run,
            "step.retry",
            step_id=step_id,
            attempt_id=attempt_id,
            actor=actor,
            from_step=None,
            to_step=None,
            details=details,
            input_digest=input_digest or digest_value(step_id),
            output_digest=output_digest or digest_value(""),
            correlation_id=self._correlation_id,
        )

    def step_transition(
        self,
        from_step: str,
        to_step: str,
        result: str,
        edge_id: str,
        attempt_id: str | None = None,
        *,
        actor: dict[str, str] | None = None,
        input_digest: str | None = None,
        output_digest: str | None = None,
    ) -> WorkflowEvent:
        """Build a ``step.transition`` event."""
        details: dict[str, Any] = {
            "result": result,
            "edge_id": edge_id,
        }
        if attempt_id is not None:
            details["attempt_id"] = attempt_id
        return _build_event(
            self._run,
            "step.transition",
            step_id=from_step,
            attempt_id=attempt_id,
            actor=actor,
            from_step=from_step,
            to_step=to_step,
            details=details,
            input_digest=input_digest or digest_value(result),
            output_digest=output_digest or digest_value(edge_id),
            correlation_id=self._correlation_id,
        )

    def step_handler_failed(
        self,
        step_id: str,
        attempt_id: str,
        *,
        error_code: str,
        message: str,
        idempotency_key: str,
        actor: dict[str, str] | None = None,
        input_digest: str | None = None,
        output_digest: str | None = None,
    ) -> WorkflowEvent:
        """Build a ``step.handler_failed`` diagnostic event."""
        return _build_event(
            self._run,
            "step.handler_failed",
            step_id=step_id,
            attempt_id=attempt_id,
            actor=actor,
            from_step=None,
            to_step=None,
            details={
                "step_id": step_id,
                "attempt_id": attempt_id,
                "error_code": error_code,
                "message": message,
                "idempotency_key": idempotency_key,
            },
            input_digest=input_digest or digest_value(step_id),
            output_digest=output_digest or digest_value(error_code),
            correlation_id=self._correlation_id,
        )

    def gate_decision(
        self,
        gate: _GateRef,
        decision: str,
        actor_id: str,
        *,
        reason: str | None = None,
        actor: dict[str, str] | None = None,
        input_digest: str | None = None,
        output_digest: str | None = None,
    ) -> WorkflowEvent:
        """Build a ``gate.approved`` or ``gate.rejected`` event."""
        event_type = f"gate.{decision}"
        details: dict[str, Any] = {
            "gate_id": gate.gate_id,
            "challenge_id": gate.challenge_id,
            "bound_digest": gate.bound_digest,
            "decision": decision,
        }
        if reason is not None:
            details["reason"] = reason
        resolved_actor = actor or {"kind": "human", "id": actor_id}
        return _build_event(
            self._run,
            event_type,
            step_id=gate.step_id,
            attempt_id=None,
            actor=resolved_actor,
            from_step=gate.step_id,
            to_step=None,
            details=details,
            input_digest=input_digest or digest_value(gate.bound_digest),
            output_digest=output_digest or digest_value(decision),
            correlation_id=self._correlation_id,
        )
