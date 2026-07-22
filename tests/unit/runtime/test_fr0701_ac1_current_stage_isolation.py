"""FR-0701 AC-1: runtime state is independent of project.toml current_stage."""

from louke.runtime.catalog import DefinitionRegistry, Edge, Step, WorkflowDefinition
from louke.runtime.recovery import recover_run
from louke.runtime.store import WorkflowRunStore


def _project_toml(current_stage: str) -> str:
    return f'[meta]\ncurrent_stage = "{current_stage}"\n'


def _simple_program_definition() -> WorkflowDefinition:
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
        definition_id="ac_fr0701",
        version="1",
        start_step="start",
        steps=(start, end),
    )


def test_ac_fr0701_01_runtime_state_ignores_project_toml_current_stage(
    tmp_path, monkeypatch
):
    """AC-FR0701-01: new run state is independent of project.toml current_stage."""
    project_dir = tmp_path / ".louke" / "project"
    project_dir.mkdir(parents=True)
    project_toml_file = project_dir / "project.toml"
    project_toml_file.write_text(_project_toml("M-ARCH"), encoding="utf-8")
    monkeypatch.chdir(tmp_path)

    registry = DefinitionRegistry()
    definition = registry.register(_simple_program_definition())

    db_path = tmp_path / ".louke" / "runtime" / "state.sqlite3"
    store = WorkflowRunStore(db_path=str(db_path), catalog=registry)
    run = store.create_run(definition)

    assert run.current_step == "start"
    assert run.status == "in_progress"
    assert run.revision == 0

    # The runtime schema must not contain legacy project metadata fields.
    assert "current_stage" not in store.schema_columns

    # Change the legacy current_stage field and reload/recover the run.
    project_toml_file.write_text(_project_toml("M-DEV"), encoding="utf-8")
    reloaded_store = WorkflowRunStore(db_path=str(db_path), catalog=registry)
    recovered = recover_run(reloaded_store, run.run_id)

    assert recovered.current_step == "start"
    assert recovered.status == "in_progress"
    assert recovered.revision == run.revision
    assert recovered.contract_digest == run.contract_digest
    assert "current_stage" not in reloaded_store.schema_columns
