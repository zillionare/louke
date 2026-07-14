"""FR-0101: Runtime is the sole writer of state and transitions."""

import pytest

from louke.runtime.catalog import DefinitionRegistry, Edge, Step, WorkflowDefinition
from louke.runtime.domain import (
    IllegalTransitionError,
    RevisionConflictError,
    RuntimeCommand,
    UndeclaredResultError,
)
from louke.runtime.orchestrator import WorkflowOrchestrator
from louke.runtime.store import WorkflowRunStore


def _lock_definition() -> WorkflowDefinition:
    lock = Step(
        step_id="lock",
        kind="human_gate",
        transitions=(
            Edge(
                edge_id="e_approved",
                from_step="lock",
                to_step="design",
                condition="approved",
            ),
            Edge(
                edge_id="e_rejected",
                from_step="lock",
                to_step="cancel",
                condition="rejected",
            ),
        ),
    )
    design = Step(step_id="design", kind="program")
    cancel = Step(step_id="cancel", kind="program")
    return WorkflowDefinition(
        definition_id="ac_fr0101",
        version="1",
        start_step="lock",
        steps=(lock, design, cancel),
    )


def _program_step_definition() -> WorkflowDefinition:
    review = Step(
        step_id="review",
        kind="program",
        transitions=(
            Edge(
                edge_id="e_approved",
                from_step="review",
                to_step="next",
                condition="approved",
            ),
            Edge(
                edge_id="e_rejected",
                from_step="review",
                to_step="end",
                condition="rejected",
            ),
        ),
    )
    next_step = Step(step_id="next", kind="program")
    end = Step(step_id="end", kind="program")
    return WorkflowDefinition(
        definition_id="ac_fr0101",
        version="1",
        start_step="review",
        steps=(review, next_step, end),
    )


def test_ac_fr0101_01_reject_undeclared_next_step():
    """AC-FR0101-01: a request to jump to an undeclared step is rejected."""
    registry = DefinitionRegistry()
    definition = registry.register(_lock_definition())
    store = WorkflowRunStore(catalog=registry)
    run = store.create_run(definition)

    orchestrator = WorkflowOrchestrator(store)
    command = RuntimeCommand(
        run_id=run.run_id,
        expected_revision=run.revision,
        requested_next_step="development",
    )

    with pytest.raises(IllegalTransitionError):
        orchestrator.apply_command(command)

    fetched = store.get_run(run.run_id)
    assert fetched.current_step == "lock"
    assert fetched.revision == run.revision
    assert fetched.status == run.status


def test_ac_fr0101_02_record_diagnostic_on_undeclared_result():
    """AC-FR0101-02: an undeclared executor result is diagnosed but not transitioned."""
    registry = DefinitionRegistry()
    definition = registry.register(_program_step_definition())
    store = WorkflowRunStore(catalog=registry)
    run = store.create_run(definition)

    orchestrator = WorkflowOrchestrator(store)
    command = RuntimeCommand(
        run_id=run.run_id,
        expected_revision=run.revision,
        result="skipped",
    )

    with pytest.raises(UndeclaredResultError):
        orchestrator.apply_command(command)

    fetched = store.get_run(run.run_id)
    assert fetched.current_step == "review"
    assert fetched.revision == run.revision

    events = store.get_events(run.run_id)
    result_events = [
        event for event in events if event.type == "step.result_undeclared"
    ]
    assert len(result_events) == 1
    assert result_events[0].details["result"] == "skipped"
    assert result_events[0].details["step_id"] == "review"


def test_ac_fr0101_03_revision_cas_conflict_on_concurrent_submit():
    """AC-FR0101-03: the second client to submit on the same revision gets a conflict."""
    registry = DefinitionRegistry()
    definition = registry.register(_program_step_definition())
    store = WorkflowRunStore(catalog=registry)
    run = store.create_run(definition)

    orchestrator = WorkflowOrchestrator(store)
    first = RuntimeCommand(
        run_id=run.run_id,
        expected_revision=run.revision,
        result="approved",
    )
    outcome = orchestrator.apply_command(first)
    assert outcome.run.current_step == "next"
    assert outcome.run.revision == 1

    second = RuntimeCommand(
        run_id=run.run_id,
        expected_revision=run.revision,
        result="approved",
    )
    try:
        orchestrator.apply_command(second)
    except RevisionConflictError as exc:
        assert exc.current_revision == 1
    else:
        raise AssertionError("expected RevisionConflictError")

    latest = store.get_run(run.run_id)
    assert latest.revision == 1
    assert latest.current_step == "next"


def test_ac_fr0101_04_next_step_must_be_definition_target():
    """AC-FR0101-04: a valid result uses the definition target, not a client override."""
    registry = DefinitionRegistry()
    definition = registry.register(_program_step_definition())
    store = WorkflowRunStore(catalog=registry)
    run = store.create_run(definition)

    orchestrator = WorkflowOrchestrator(store)
    command = RuntimeCommand(
        run_id=run.run_id,
        expected_revision=run.revision,
        result="approved",
        requested_next_step="end",
    )
    outcome = orchestrator.apply_command(command)

    assert outcome.run.current_step == "next"
    assert outcome.run.revision == 1

    fetched = store.get_run(run.run_id)
    assert fetched.current_step == "next"
    assert fetched.revision == 1

    events = store.get_events(run.run_id)
    transition_events = [event for event in events if event.type == "step.transition"]
    assert len(transition_events) == 1
    assert transition_events[0].to_step == "next"
