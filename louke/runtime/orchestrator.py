"""Workflow orchestrator: the only component that writes run state and transitions."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from dataclasses import dataclass
from typing import TYPE_CHECKING

from louke.runtime.catalog import Edge, Step, WorkflowDefinition, derive_status
from louke.runtime.domain import (
    IllegalTransitionError,
    RevisionConflictError,
    RuntimeCommand,
    RuntimeStateError,
    UndeclaredResultError,
    WorkflowEvent,
)
from louke.runtime.store import WorkflowRun, WorkflowRunStore

if TYPE_CHECKING:
    from louke.runtime.gates import GateService


@dataclass(frozen=True, slots=True)
class TransitionOutcome:
    """Result of a successful state transition."""

    run: WorkflowRun
    event: WorkflowEvent


class WorkflowOrchestrator:
    """Enforce definition-bound state transitions with revision CAS."""

    def __init__(
        self,
        store: WorkflowRunStore,
        gate_service: "GateService | None" = None,
    ) -> None:
        self._store = store
        self._gate_service = gate_service

    def apply_command(
        self,
        command: RuntimeCommand,
        actor: dict[str, str] | None = None,
    ) -> TransitionOutcome:
        """Apply ``command`` to the identified run.

        The orchestrator validates the command against the bound definition,
        performs an atomic revision CAS, and appends a transition event on
        success.

        Args:
            command: The transition request.
            actor: Optional actor metadata for the resulting event.

        Returns:
            The updated run and the committed event.

        Raises:
            RevisionConflictError: If the run has moved past
                ``command.expected_revision``.
            IllegalTransitionError: If the command requests an undeclared
                transition or tries to choose a target step without a result.
            UndeclaredResultError: If the step result does not match any
                declared transition.
        """
        run = self._store.get_run(command.run_id)
        if command.idempotency_key:
            existing_attempt = self._store.get_step_attempt_by_key(
                command.run_id, command.idempotency_key
            )
            if existing_attempt is not None and existing_attempt.event_id is not None:
                existing_event = self._store.get_event(existing_attempt.event_id)
                return TransitionOutcome(run=run, event=existing_event)

        if run.revision != command.expected_revision:
            raise RevisionConflictError(
                f"revision conflict: expected {command.expected_revision}, "
                f"found {run.revision}",
                current_revision=run.revision,
            )

        definition = self._store.get_definition(command.run_id)
        current_step = _step_by_id(definition, run.current_step)

        if current_step.kind == "human_gate":
            raise self._gate_blocked_error(run, current_step)

        if command.requested_next_step is not None and command.result is None:
            raise IllegalTransitionError(
                "client cannot select next_step without a step result"
            )

        if command.result is None:
            raise IllegalTransitionError("no step result provided")

        matching = _transitions_for_result(current_step, command.result)
        if not matching:
            self._record_diagnostic(run, current_step, command.result, actor)
            raise UndeclaredResultError(
                f"step '{current_step.step_id}' has no transition for result "
                f"{command.result!r}"
            )

        edge = matching[0]
        new_status = derive_status(edge.to_step, definition)
        new_run = self._store.update_run(
            run.with_step(current_step=edge.to_step, status=new_status),
            command.expected_revision,
        )

        event = self._append_transition_event(
            new_run,
            current_step.step_id,
            edge,
            command.result,
            actor,
        )
        if command.idempotency_key:
            self._store.record_step_attempt(
                run_id=run.run_id,
                step_id=current_step.step_id,
                idempotency_key=command.idempotency_key,
                status="completed",
                result=command.result,
                event_id=event.event_id,
            )
        return TransitionOutcome(run=new_run, event=event)

    def _record_diagnostic(
        self,
        run: WorkflowRun,
        step: Step,
        result: str,
        actor: dict[str, str] | None,
    ) -> None:
        event = _build_event(
            run=run,
            event_type="step.result_undeclared",
            from_step=step.step_id,
            to_step=None,
            details={"result": result, "step_id": step.step_id},
            actor=actor,
        )
        self._store.append_event(event)

    def _append_transition_event(
        self,
        run: WorkflowRun,
        from_step: str,
        edge: Edge,
        result: str,
        actor: dict[str, str] | None,
    ) -> WorkflowEvent:
        event = _build_event(
            run=run,
            event_type="step.transition",
            from_step=from_step,
            to_step=edge.to_step,
            details={"result": result, "edge_id": edge.edge_id},
            actor=actor,
        )
        return self._store.append_event(event)

    def _gate_blocked_error(
        self, run: WorkflowRun, step: Step
    ) -> IllegalTransitionError:
        """Return an error indicating the current human gate blocks progress."""
        from louke.runtime.gates import GateNotApprovedError

        return GateNotApprovedError(
            f"step '{step.step_id}' is a human gate awaiting a host-authenticated decision"
        )

    def _append_gate_event(
        self,
        run_id: str,
        event_type: str,
        step_id: str,
        details: dict,
        actor: dict[str, str] | None = None,
    ) -> WorkflowEvent:
        """Append a gate-related event to the run's event stream."""
        run = self._store.get_run(run_id)
        event = _build_event(
            run=run,
            event_type=event_type,
            from_step=step_id,
            to_step=None,
            details=details,
            actor=actor,
        )
        return self._store.append_event(event)


def _step_by_id(definition: WorkflowDefinition, step_id: str) -> Step:
    for step in definition.steps:
        if step.step_id == step_id:
            return step
    raise RuntimeStateError(f"step {step_id!r} not found in bound definition")


def _transitions_for_result(step: Step, result: str) -> list[Edge]:
    return [edge for edge in step.transitions if edge.condition == result]


def _build_event(
    run: WorkflowRun,
    event_type: str,
    from_step: str | None,
    to_step: str | None,
    details: dict,
    actor: dict[str, str] | None,
) -> WorkflowEvent:
    return WorkflowEvent(
        event_id=f"evt_{uuid.uuid4().hex[:12]}",
        run_id=run.run_id,
        sequence=0,
        type=event_type,
        at=datetime.now(timezone.utc).isoformat(),
        actor=actor or {"kind": "runtime", "id": "runtime"},
        from_step=from_step,
        to_step=to_step,
        revision=run.revision,
        details=details,
    )
