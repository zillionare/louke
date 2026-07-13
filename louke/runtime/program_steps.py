"""Registered program step handlers and executor.

This module provides the handler registry used by catalog validation and the
executor that invokes handlers with a read-only StepContext.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Callable

from louke.runtime.catalog import derive_status
from louke.runtime.domain import WorkflowEvent
from louke.runtime.events import EventBuilder

if TYPE_CHECKING:
    from louke.runtime.store import WorkflowRun, WorkflowRunStore


@dataclass(frozen=True, slots=True)
class StepContext:
    """Read-only context supplied to a program step handler.

    Attributes:
        run_id: Opaque identifier of the workflow run.
        step_id: Identifier of the step being executed.
        attempt_id: Opaque identifier of this attempt.
        workspace: Absolute path to the workspace root.
        idempotency_key: Stable key used to deduplicate the attempt.
    """

    run_id: str
    step_id: str
    attempt_id: str
    workspace: str
    idempotency_key: str


@dataclass(frozen=True, slots=True)
class HandlerResult:
    """Structured result returned by a program step handler.

    Attributes:
        result: The transition condition produced by the handler.
        output: Additional structured output validated against the step schema.
    """

    result: str
    output: dict[str, Any] = field(default_factory=dict)


Handler = Callable[[StepContext], HandlerResult]


class HandlerNotFoundError(KeyError):
    """Raised when a requested handler name is not registered."""


class HandlerRegistry:
    """Registry of named program step handlers.

    Handlers are keyed by name.  Once registered a name cannot be replaced
    without first unregistering it, keeping catalog validation deterministic.
    """

    def __init__(self) -> None:
        self._handlers: dict[str, Handler] = {}

    def register(self, name: str, handler: Handler) -> None:
        """Register ``handler`` under ``name``.

        Args:
            name: Stable handler identifier referenced by program steps.
            handler: Callable accepting a :class:`StepContext` and returning a
                :class:`HandlerResult`.
        """
        self._handlers[name] = handler

    def get(self, name: str) -> Handler:
        """Return the handler registered under ``name``.

        Args:
            name: The stable handler identifier.

        Returns:
            The registered handler callable.

        Raises:
            HandlerNotFoundError: If no handler with that name is registered.
        """
        handler = self._handlers.get(name)
        if handler is None:
            raise HandlerNotFoundError(f"handler {name!r} not registered")
        return handler

    def __contains__(self, name: str) -> bool:
        return name in self._handlers


@dataclass(frozen=True, slots=True)
class ExecutionOutcome:
    """Result of a program step execution attempt.

    Attributes:
        run: The workflow run after the attempt.
        event: The committed event, if any.
        error_code: Stable error code when the attempt did not succeed.
    """

    run: WorkflowRun
    event: WorkflowEvent | None = None
    error_code: str | None = None


class ProgramStepExecutor:
    """Invoke registered program step handlers and advance workflow state.

    The executor is responsible for idempotency: a completed idempotency key
    is never executed again, and failed attempts produce diagnostic events
    without advancing the run.
    """

    def __init__(self, handler_registry: HandlerRegistry) -> None:
        self._handler_registry = handler_registry

    def execute(
        self,
        store: WorkflowRunStore,
        run_id: str,
        workspace: str,
        idempotency_key: str,
    ) -> ExecutionOutcome:
        """Execute the current program step for ``run_id``.

        Args:
            store: The workflow run store.
            run_id: The run to advance.
            workspace: Absolute workspace path passed to the handler.
            idempotency_key: Stable key for this attempt.

        Returns:
            An :class:`ExecutionOutcome` describing the run state after the
            attempt.  Successful attempts advance the run; failed attempts keep
            the run at the current step and expose a stable ``error_code``.
        """
        cached = self._cached_outcome(store, run_id, idempotency_key)
        if cached is not None:
            return cached

        run = store.get_run(run_id)
        definition = store.get_definition(run_id)
        current_step = self._step_by_id(definition, run.current_step)
        handler = self._handler_registry.get(current_step.handler)

        attempt = self._ensure_started_attempt(
            store,
            run_id=run_id,
            step_id=current_step.step_id,
            idempotency_key=idempotency_key,
        )

        started_event = EventBuilder(run).step_started(
            step_id=current_step.step_id,
            attempt_id=attempt.attempt_id,
        )
        store.append_event(started_event)

        try:
            context = StepContext(
                run_id=run.run_id,
                step_id=current_step.step_id,
                attempt_id=attempt.attempt_id,
                workspace=workspace,
                idempotency_key=idempotency_key,
            )
            handler_result = handler(context)
        except Exception as exc:
            return self._record_failure(
                store,
                run=run,
                attempt=attempt,
                error_code="handler_exception",
                message=str(exc),
            )

        matching = self._transitions_for_result(current_step, handler_result.result)
        if not matching:
            return self._record_failure(
                store,
                run=run,
                attempt=attempt,
                error_code="schema_invalid_result",
                message=(
                    f"handler returned result {handler_result.result!r} with no "
                    f"matching transition"
                ),
            )

        edge = matching[0]
        new_status = derive_status(edge.to_step, definition)
        new_run = store.update_run(
            run.with_step(current_step=edge.to_step, status=new_status),
            run.revision,
        )
        event = store.append_event(
            EventBuilder(new_run).step_transition(
                from_step=current_step.step_id,
                to_step=edge.to_step,
                result=handler_result.result,
                edge_id=edge.edge_id,
                attempt_id=attempt.attempt_id,
            )
        )
        store.append_event(
            EventBuilder(new_run).step_completed(
                step_id=current_step.step_id,
                attempt_id=attempt.attempt_id,
                result=handler_result.result,
            )
        )
        store.update_step_attempt(
            attempt.with_status(
                status="completed",
                result=handler_result.result,
                event_id=event.event_id,
            )
        )
        return ExecutionOutcome(run=new_run, event=event)

    def _cached_outcome(
        self,
        store: WorkflowRunStore,
        run_id: str,
        idempotency_key: str,
    ) -> ExecutionOutcome | None:
        """Return a previously completed outcome for the same key, if any."""
        existing = store.get_step_attempt_by_key(run_id, idempotency_key)
        if existing is None or existing.event_id is None:
            return None
        run = store.get_run(run_id)
        event = store.get_event(existing.event_id)
        return ExecutionOutcome(run=run, event=event)

    def _ensure_started_attempt(
        self,
        store: WorkflowRunStore,
        run_id: str,
        step_id: str,
        idempotency_key: str,
    ):
        """Return a started attempt, creating or updating an existing record."""
        for attempt in store.get_step_attempts(run_id):
            if attempt.idempotency_key == idempotency_key:
                if attempt.status == "completed":
                    continue
                return store.update_step_attempt(attempt.with_status(status="started"))
        return store.record_step_attempt(
            run_id=run_id,
            step_id=step_id,
            idempotency_key=idempotency_key,
            status="started",
        )

    def _record_failure(
        self,
        store: WorkflowRunStore,
        run,
        attempt,
        error_code: str,
        message: str,
    ) -> ExecutionOutcome:
        """Record a failed attempt and a diagnostic event."""
        event = EventBuilder(run).step_handler_failed(
            step_id=attempt.step_id,
            attempt_id=attempt.attempt_id,
            error_code=error_code,
            message=message,
            idempotency_key=attempt.idempotency_key,
        )
        store.append_event(event)
        store.update_step_attempt(attempt.with_status(status="failed"))
        return ExecutionOutcome(run=run, event=event, error_code=error_code)

    @staticmethod
    def _step_by_id(definition, step_id: str):
        for step in definition.steps:
            if step.step_id == step_id:
                return step
        raise RuntimeError(f"step {step_id!r} not found in bound definition")

    @staticmethod
    def _transitions_for_result(step, result: str):
        return [edge for edge in step.transitions if edge.condition == result]
