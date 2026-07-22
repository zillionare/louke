"""FR-0201: persist WorkflowRun and resume across process restarts."""

from louke.runtime.catalog import DefinitionRegistry, Edge, Step, WorkflowDefinition
from louke.runtime.domain import RuntimeCommand
from louke.runtime.orchestrator import WorkflowOrchestrator
from louke.runtime.store import WorkflowRunStore


def _human_gate_definition() -> WorkflowDefinition:
    requirements = Step(
        step_id="requirements_approval",
        kind="human_gate",
        transitions=(
            Edge(
                edge_id="e_approved",
                from_step="requirements_approval",
                to_step="design",
                condition="approved",
            ),
        ),
        implemented=True,
    )
    design = Step(step_id="design", kind="program", implemented=True)
    return WorkflowDefinition(
        definition_id="ac_fr0201",
        version="1",
        start_step="requirements_approval",
        steps=(requirements, design),
    )


def _program_step_definition() -> WorkflowDefinition:
    start = Step(
        step_id="start",
        kind="program",
        transitions=(
            Edge(
                edge_id="e_done",
                from_step="start",
                to_step="end",
                condition="done",
            ),
        ),
        implemented=True,
    )
    end = Step(step_id="end", kind="program", implemented=True)
    return WorkflowDefinition(
        definition_id="ac_fr0201_idempotency",
        version="1",
        start_step="start",
        steps=(start, end),
    )


def test_ac_fr0201_01_persist_and_resume_waiting_for_human(tmp_path):
    """AC-FR0201-01: after process restart the same run/step/gate/revision/contract digest are visible."""
    registry = DefinitionRegistry()
    definition = registry.register(_human_gate_definition())

    db_path = tmp_path / ".louke" / "runtime" / "state.sqlite3"
    store = WorkflowRunStore(db_path=str(db_path), catalog=registry)
    run = store.create_run(definition)

    assert run.status == "waiting_for_human"
    assert run.current_step == "requirements_approval"
    assert run.revision == 0
    assert run.contract_digest

    store.close()

    reloaded_store = WorkflowRunStore(db_path=str(db_path), catalog=registry)
    runs = reloaded_store.list_runs()
    assert len(runs) == 1
    reloaded = reloaded_store.get_run(run.run_id)

    assert reloaded.run_id == run.run_id
    assert reloaded.current_step == run.current_step
    assert reloaded.revision == run.revision
    assert reloaded.status == run.status
    assert reloaded.definition_id == run.definition_id
    assert reloaded.definition_version == run.definition_version
    assert reloaded.contract_digest == run.contract_digest

    resolved = reloaded_store.get_definition(run.run_id)
    assert resolved.definition_id == definition.definition_id
    assert resolved.version == definition.version


def test_ac_fr0201_02_committed_step_is_idempotent_after_resume(tmp_path):
    """AC-FR0201-02: a committed step result is not re-applied after restart."""
    registry = DefinitionRegistry()
    definition = registry.register(_program_step_definition())

    db_path = tmp_path / ".louke" / "runtime" / "state.sqlite3"
    store = WorkflowRunStore(db_path=str(db_path), catalog=registry)
    run = store.create_run(definition)

    orchestrator = WorkflowOrchestrator(store)
    command = RuntimeCommand(
        run_id=run.run_id,
        expected_revision=run.revision,
        result="done",
        idempotency_key="exec-1",
    )
    outcome = orchestrator.apply_command(command)
    assert outcome.run.current_step == "end"
    assert outcome.run.revision == 1

    transition_events = [
        event
        for event in store.get_events(run.run_id)
        if event.type == "step.transition"
    ]
    assert len(transition_events) == 1

    store.close()

    reloaded_store = WorkflowRunStore(db_path=str(db_path), catalog=registry)
    reloaded_orchestrator = WorkflowOrchestrator(reloaded_store)
    retry = RuntimeCommand(
        run_id=run.run_id,
        expected_revision=run.revision,
        result="done",
        idempotency_key="exec-1",
    )
    retry_outcome = reloaded_orchestrator.apply_command(retry)

    assert retry_outcome.run.current_step == "end"
    assert retry_outcome.run.revision == 1
    reloaded_events = [
        event
        for event in reloaded_store.get_events(run.run_id)
        if event.type == "step.transition"
    ]
    assert len(reloaded_events) == 1


def test_ac_fr0201_03_uncertain_interruption_enters_needs_attention(tmp_path):
    """AC-FR0201-03: an uncertain crash position becomes needs_attention, not auto-success."""
    registry = DefinitionRegistry()
    definition = registry.register(_program_step_definition())

    db_path = tmp_path / ".louke" / "runtime" / "state.sqlite3"
    store = WorkflowRunStore(db_path=str(db_path), catalog=registry)
    run = store.create_run(definition)

    store.record_step_attempt(
        run_id=run.run_id,
        step_id=run.current_step,
        idempotency_key="exec-uncertain",
        status="started",
    )

    from louke.runtime.recovery import recover_run

    recovered = recover_run(store, run.run_id)

    assert recovered.status == "needs_attention"
    assert recovered.current_step == run.current_step
    assert recovered.revision == run.revision + 1
    assert recovered.contract_digest == run.contract_digest

    reloaded = store.get_run(run.run_id)
    assert reloaded.status == "needs_attention"
    assert reloaded.current_step == run.current_step
