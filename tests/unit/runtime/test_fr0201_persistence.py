"""FR-0201: persist WorkflowRun and resume across process restarts."""

from louke.runtime.catalog import DefinitionRegistry, Edge, Step, WorkflowDefinition
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
    )
    design = Step(step_id="design", kind="program")
    return WorkflowDefinition(
        definition_id="ac_fr0201",
        version="1",
        start_step="requirements_approval",
        steps=(requirements, design),
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
