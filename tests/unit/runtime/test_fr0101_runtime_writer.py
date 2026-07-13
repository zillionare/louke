"""FR-0101: Runtime is the sole writer of state and transitions."""

from louke.runtime.catalog import DefinitionRegistry, Edge, Step, WorkflowDefinition
from louke.runtime.domain import IllegalTransitionError, RuntimeCommand
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

    try:
        orchestrator.apply_command(command)
    except IllegalTransitionError:
        pass
    else:
        raise AssertionError("expected IllegalTransitionError")

    fetched = store.get_run(run.run_id)
    assert fetched.current_step == "lock"
    assert fetched.revision == run.revision
    assert fetched.status == run.status
