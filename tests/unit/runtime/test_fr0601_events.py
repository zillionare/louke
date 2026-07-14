"""FR-0601: workflow events and evidence."""

from __future__ import annotations

import json

import pytest

from louke.runtime.catalog import DefinitionRegistry, Edge, Step, WorkflowDefinition
from louke.runtime.domain import RuntimeCommand
from louke.runtime.domain import WorkflowEvent
from louke.runtime.events import EventBuilder, EventValidationError
from louke.runtime.gates import GateNotApprovedError, GateService
from louke.runtime.orchestrator import WorkflowOrchestrator
from louke.runtime.program_steps import (
    HandlerRegistry,
    HandlerResult,
    ProgramStepExecutor,
    StepContext,
)
from louke.runtime.store import WorkflowRunStore


def _lifecycle_definition() -> WorkflowDefinition:
    """Return a definition that exercises all FR-0601 event types."""
    start = Step(
        step_id="start",
        kind="program",
        handler="demo",
        transitions=(
            Edge(
                edge_id="e_to_gate",
                from_step="start",
                to_step="gate",
                condition="done",
            ),
        ),
    )
    gate = Step(
        step_id="gate",
        kind="human_gate",
        transitions=(
            Edge(
                edge_id="e_approved",
                from_step="gate",
                to_step="end",
                condition="approved",
            ),
        ),
    )
    end = Step(step_id="end", kind="program")
    return WorkflowDefinition(
        definition_id="fr0601_lifecycle",
        version="1",
        start_step="start",
        steps=(start, gate, end),
    )


def test_ac_fr0601_01_event_stream_covers_lifecycle_and_schema(tmp_path):
    """AC-FR0601-01: append-only ordered events cover the lifecycle schema."""
    registry = DefinitionRegistry()
    definition = registry.register(_lifecycle_definition())
    store = WorkflowRunStore(catalog=registry)

    handler_registry = HandlerRegistry()

    def demo_handler(_ctx: StepContext) -> HandlerResult:
        return HandlerResult(result="done", output={"answer": 42})

    handler_registry.register("demo", demo_handler)
    executor = ProgramStepExecutor(handler_registry)
    orchestrator = WorkflowOrchestrator(store, gate_service=GateService(store))

    run = store.create_run(definition)

    # Step start / end / transition to the human gate.
    outcome = executor.execute(
        store=store,
        run_id=run.run_id,
        workspace=str(tmp_path),
        idempotency_key="attempt-1",
    )
    assert outcome.run.current_step == "gate"

    # Blocked: trying to drive through a human gate without a decision.
    with pytest.raises(GateNotApprovedError):
        orchestrator.apply_command(
            RuntimeCommand(
                run_id=run.run_id,
                expected_revision=outcome.run.revision,
                result="approved",
            )
        )

    # Retry event emitted explicitly by the runtime consumer.
    retry_event = EventBuilder(store.get_run(run.run_id)).step_retry(
        step_id="gate",
        attempt_id="attempt-retry",
        reason="policy retry",
    )
    store.append_event(retry_event)

    # Gate decision (approved) produces a gate event and a transition.
    gate_service = GateService(store)
    gate = gate_service.ensure_gate(
        run_id=run.run_id,
        step_id="gate",
        bound_digest="sha256:gate-artifact",
    )
    orchestrator.apply_gate_decision(
        run_id=run.run_id,
        gate_id=gate.gate_id,
        decision="approve",
        bound_digest="sha256:gate-artifact",
        expected_revision=store.get_run(run.run_id).revision,
        principal={"kind": "human", "id": "alice"},
    )

    events = store.get_events(run.run_id)

    # Append-only and stable order.
    sequences = [event.sequence for event in events]
    assert sequences == sorted(sequences)
    assert len(set(sequences)) == len(sequences)

    # All required event types are present.
    event_types = {event.type for event in events}
    expected_types = {
        "run.created",
        "step.started",
        "step.completed",
        "step.blocked",
        "step.retry",
        "step.transition",
        "gate.approved",
    }
    assert expected_types <= event_types, (
        f"missing event types: {expected_types - event_types}"
    )

    # Every event carries the required schema fields.
    for event in events:
        assert event.run_id == run.run_id
        assert event.type
        assert event.at
        assert event.correlation_id
        assert isinstance(event.revision, int)
        assert event.input_digest.startswith("sha256:")
        assert event.output_digest.startswith("sha256:")
        assert event.step_id


def test_ac_fr0601_02_state_and_last_event_revision_consistent_and_atomic():
    """AC-FR0601-02: successful state changes leave state and last event aligned."""
    registry = DefinitionRegistry()
    definition = registry.register(
        WorkflowDefinition(
            definition_id="fr0601_consistency",
            version="1",
            start_step="start",
            steps=(
                Step(
                    step_id="start",
                    kind="program",
                    transitions=(
                        Edge(
                            edge_id="e1",
                            from_step="start",
                            to_step="end",
                            condition="done",
                        ),
                    ),
                ),
                Step(step_id="end", kind="program"),
            ),
        )
    )
    store = WorkflowRunStore(catalog=registry)
    orchestrator = WorkflowOrchestrator(store)

    run = store.create_run(definition)
    orchestrator.apply_command(
        RuntimeCommand(
            run_id=run.run_id,
            expected_revision=run.revision,
            result="done",
        )
    )

    current = store.get_run(run.run_id)
    events = store.get_events(run.run_id)
    last_event = events[-1]

    assert current.revision == last_event.revision
    assert last_event.type == "step.transition"

    # An invalid event must not produce a partially committed state change.
    bad_event = WorkflowEvent(
        event_id="evt_bad",
        run_id=current.run_id,
        sequence=0,
        type="step.transition",
        at="2026-01-01T00:00:00+00:00",
        step_id="end",
        from_step="end",
        to_step="nowhere",
        input_digest=None,
        output_digest="sha256:out",
    )

    with pytest.raises(EventValidationError):
        store.commit_transition(
            current.with_step(current_step="nowhere", status="in_progress"),
            current.revision,
            [bad_event],
        )

    after_rollback = store.get_run(run.run_id)
    assert after_rollback.revision == current.revision
    assert after_rollback.current_step == current.current_step


def test_ac_fr0601_03_event_redacts_secrets_and_credentials():
    """AC-FR0601-03: events keep identity identifiers but not secrets or credentials."""
    registry = DefinitionRegistry()
    definition = registry.register(
        WorkflowDefinition(
            definition_id="fr0601_redaction",
            version="1",
            start_step="start",
            steps=(
                Step(
                    step_id="start",
                    kind="program",
                    transitions=(
                        Edge(
                            edge_id="e1",
                            from_step="start",
                            to_step="end",
                            condition="done",
                        ),
                    ),
                ),
                Step(step_id="end", kind="program"),
            ),
        )
    )
    store = WorkflowRunStore(catalog=registry)
    run = store.create_run(definition)

    actor = {
        "kind": "human",
        "id": "alice",
        "token": "super-secret-token",
        "credential": "super-secret-credential",
    }
    details = {
        "step_id": "start",
        "idempotency_key": "attempt-secret",
        "input": {"password": "hunter2", "api_key": "AKIA..."},
    }

    event = EventBuilder(run).step_started(
        step_id="start",
        attempt_id="attempt-secret",
        actor=actor,
        details=details,
        input_digest="sha256:input",
        output_digest="sha256:output",
    )
    persisted = store.append_event(event)

    serialized = json.dumps(
        {
            "actor": persisted.actor,
            "details": persisted.details,
        },
        sort_keys=True,
    )
    assert "super-secret-token" not in serialized
    assert "super-secret-credential" not in serialized
    assert "hunter2" not in serialized
    assert "AKIA..." not in serialized

    # Allowed identity identifiers survive redaction.
    assert persisted.actor.get("kind") == "human"
    assert persisted.actor.get("id") == "alice"

    # Secrets are replaced by stable digests.
    assert persisted.actor.get("token", "").startswith("sha256:")
    assert persisted.actor.get("credential", "").startswith("sha256:")
    assert persisted.details["input"]["password"].startswith("sha256:")
    assert persisted.details["input"]["api_key"].startswith("sha256:")
