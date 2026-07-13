"""Workflow orchestrator: the only component that writes run state and transitions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from louke.runtime.catalog import Edge, Step, WorkflowDefinition, derive_status
from louke.runtime.contract_gates import (
    InheritedApproval,
    MLockGateCoordinator,
    RequirementGateCoordinator,
)
from louke.runtime.domain import (
    IllegalTransitionError,
    RevisionConflictError,
    RuntimeCommand,
    RuntimeStateError,
    UndeclaredResultError,
    WorkflowEvent,
)
from louke.runtime.events import EventBuilder, digest_value
from louke.runtime.store import WorkflowRun, WorkflowRunStore

if TYPE_CHECKING:
    from louke.runtime.gates import Gate, GateService


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
        self._requirements_coordinator: RequirementGateCoordinator | None = None
        self._m_lock_coordinator: MLockGateCoordinator | None = None
        if gate_service is not None:
            self._requirements_coordinator = RequirementGateCoordinator(
                store, gate_service
            )
            self._m_lock_coordinator = MLockGateCoordinator(store, gate_service)

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
            blocked_event = EventBuilder(run).step_blocked(
                step_id=current_step.step_id,
                reason="human_gate awaits host-authenticated decision",
                actor=actor,
            )
            self._store.append_event(blocked_event)
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
        target_step = _step_by_id(definition, edge.to_step)
        self._check_implementation_gate(run, target_step, actor)
        new_status = derive_status(edge.to_step, definition)
        new_run = run.with_step(current_step=edge.to_step, status=new_status)
        transition_event = EventBuilder(run).step_transition(
            from_step=current_step.step_id,
            to_step=edge.to_step,
            result=command.result,
            edge_id=edge.edge_id,
            attempt_id=command.idempotency_key,
            actor=actor,
        )
        committed_run, committed_events = self._store.commit_transition(
            new_run,
            command.expected_revision,
            (transition_event,),
        )
        event = committed_events[0]
        if command.idempotency_key:
            self._store.record_step_attempt(
                run_id=run.run_id,
                step_id=current_step.step_id,
                idempotency_key=command.idempotency_key,
                status="completed",
                result=command.result,
                event_id=event.event_id,
            )
        return TransitionOutcome(run=committed_run, event=event)

    def ensure_requirements_gate(
        self,
        run_id: str,
        story_digest: str,
        spec_digest: str,
        acceptance_digest: str,
    ) -> "Gate":
        """Ensure the requirements approval gate is bound to the current digest.

        Args:
            run_id: The run to ensure the gate for.
            story_digest: Digest of the story document.
            spec_digest: Digest of the spec document.
            acceptance_digest: Digest of the acceptance document.

        Returns:
            The active requirements gate record.

        Raises:
            RuntimeError: If the orchestrator was created without a gate
                service.
        """
        if self._requirements_coordinator is None:
            raise RuntimeError("orchestrator has no gate service")
        return self._requirements_coordinator.ensure_gate(
            run_id=run_id,
            story_digest=story_digest,
            spec_digest=spec_digest,
            acceptance_digest=acceptance_digest,
        )

    def check_requirements_approval(self, run_id: str) -> "Gate":
        """Verify that the requirements approval gate is approved for ``run_id``.

        Args:
            run_id: The run to check.

        Returns:
            The approved requirements gate.

        Raises:
            RuntimeError: If the orchestrator was created without a gate
                service.
            GateNotApprovedError: If the requirements gate is missing or not
                approved.
        """
        if self._requirements_coordinator is None:
            raise RuntimeError("orchestrator has no gate service")
        return self._requirements_coordinator.check_approval(run_id)

    def apply_inherited_requirements_approval(
        self,
        run_id: str,
        inherited: InheritedApproval,
    ) -> "Gate":
        """Record an inherited requirements approval on a bug_fix run.

        Used by the ``source_contract.verify`` step of a ``bug_fix`` workflow
        definition after the :class:`~louke.runtime.contract_gates.BugFixInheritanceVerifier`
        has accepted the source contract. Records the inherited approval on
        the run without creating a new ``waiting_for_human`` requirements
        gate, so the run can advance to design/implementation without a new
        human approval (FR-0801 AC-6).

        Args:
            run_id: The bug_fix run inheriting the source approval.
            inherited: The inherited approval record returned by the verifier.

        Returns:
            The persisted inherited requirements gate.

        Raises:
            RuntimeError: If the orchestrator was created without a gate
                service.
            HotfixInheritanceError: If a requirements gate already exists for
                the run.
        """
        if self._requirements_coordinator is None:
            raise RuntimeError("orchestrator has no gate service")
        return self._requirements_coordinator.apply_inherited_approval(
            run_id=run_id,
            inherited=inherited,
        )

    def check_m_lock_approval(self, run_id: str) -> "Gate":
        """Verify that the M-LOCK gate is approved for ``run_id``.

        Args:
            run_id: The run to check.

        Returns:
            The approved M-LOCK gate.

        Raises:
            RuntimeError: If the orchestrator was created without a gate
                service.
            GateNotApprovedError: If the M-LOCK gate is missing or not
                approved.
        """
        if self._m_lock_coordinator is None:
            raise RuntimeError("orchestrator has no gate service")
        return self._m_lock_coordinator.check_approval(run_id)

    def apply_gate_decision(
        self,
        run_id: str,
        gate_id: str,
        decision: str,
        bound_digest: str,
        expected_revision: int,
        principal: dict[str, str] | None,
        reason: str | None = None,
    ) -> TransitionOutcome:
        """Apply a host-authenticated human decision to a gate.

        The orchestrator delegates validation to the gate service, then advances
        the run through the ``approved`` transition if the decision is valid.

        Args:
            run_id: The run the gate belongs to.
            gate_id: The gate identifier.
            decision: ``approve`` or ``reject``.
            bound_digest: The artifact digest the principal is deciding on.
            expected_revision: The run revision the caller last observed.
            principal: Host-authenticated principal metadata.
            reason: Required when ``decision`` is ``reject``.

        Returns:
            The updated run and the committed transition event, if any.

        Raises:
            GateNotApprovedError: If the gate service rejects the decision.
        """
        from louke.runtime.gates import GateNotApprovedError

        if self._gate_service is None:
            raise RuntimeError("orchestrator has no gate service")

        gate = self._gate_service.submit_decision(
            run_id=run_id,
            gate_id=gate_id,
            decision=decision,
            bound_digest=bound_digest,
            expected_revision=expected_revision,
            principal=principal,
            reason=reason,
        )

        run = self._store.get_run(run_id)
        definition = self._store.get_definition(run_id)
        current_step = _step_by_id(definition, run.current_step)

        if current_step.kind != "human_gate":
            raise GateNotApprovedError(
                f"run is no longer at a human gate (step {run.current_step!r})"
            )

        transition_result = "approved" if gate.status == "approved" else "rejected"
        matching = _transitions_for_result(current_step, transition_result)
        if not matching:
            raise GateNotApprovedError(
                f"step {current_step.step_id!r} has no {transition_result} transition"
            )

        edge = matching[0]
        new_status = derive_status(edge.to_step, definition)
        new_run = run.with_step(current_step=edge.to_step, status=new_status)
        transition_event = EventBuilder(run).step_transition(
            from_step=current_step.step_id,
            to_step=edge.to_step,
            result=transition_result,
            edge_id=edge.edge_id,
            actor=principal,
            reason=reason if gate.status == "rejected" else None,
            bound_digest=gate.bound_digest if gate.status == "rejected" else None,
        )
        committed_run, committed_events = self._store.commit_transition(
            new_run,
            run.revision,
            (transition_event,),
        )
        return TransitionOutcome(run=committed_run, event=committed_events[0])

    def _record_diagnostic(
        self,
        run: WorkflowRun,
        step: Step,
        result: str,
        actor: dict[str, str] | None,
    ) -> None:
        event = EventBuilder(run).build(
            event_type="step.result_undeclared",
            step_id=step.step_id,
            from_step=step.step_id,
            to_step=None,
            details={"result": result, "step_id": step.step_id},
            actor=actor,
            input_digest=digest_value(step.step_id),
            output_digest=digest_value(result),
        )
        self._store.append_event(event)

    def _gate_blocked_error(
        self, run: WorkflowRun, step: Step
    ) -> IllegalTransitionError:
        """Return an error indicating the current human gate blocks progress."""
        from louke.runtime.gates import GateNotApprovedError

        return GateNotApprovedError(
            f"step '{step.step_id}' is a human gate awaiting a host-authenticated decision"
        )

    def _check_implementation_gate(
        self,
        run: WorkflowRun,
        target_step: Step,
        actor: dict[str, str] | None,
    ) -> None:
        """Block transitions into implementation steps before M-LOCK approval.

        Implementation steps (``semantic_task`` and ``decision``) must not
        start until the M-LOCK human gate has a current approved decision. The
        check is skipped when the orchestrator has no gate service, since gate
        enforcement is only meaningful for runs that carry artifact-bound
        gates.

        Args:
            run: The run attempting the transition.
            target_step: The step the run is trying to enter.
            actor: Optional actor metadata for the blocked event.

        Raises:
            GateNotApprovedError: If the target step is an implementation step
                and the M-LOCK gate is missing or not approved.
        """
        from louke.runtime.gates import GateNotApprovedError

        if target_step.kind not in {"semantic_task", "decision"}:
            return

        if self._m_lock_coordinator is None:
            return

        try:
            self._m_lock_coordinator.check_approval(run.run_id)
        except GateNotApprovedError:
            blocked_event = EventBuilder(run).step_blocked(
                step_id=target_step.step_id,
                reason="implementation steps require M-LOCK approval",
                actor=actor,
            )
            self._store.append_event(blocked_event)
            raise


def _step_by_id(definition: WorkflowDefinition, step_id: str) -> Step:
    for step in definition.steps:
        if step.step_id == step_id:
            return step
    raise RuntimeStateError(f"step {step_id!r} not found in bound definition")


def _transitions_for_result(step: Step, result: str) -> list[Edge]:
    return [edge for edge in step.transitions if edge.condition == result]
