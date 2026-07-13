"""FR-0701 AC-2: legacy maestro advance is isolated from new WorkflowRuns."""

from types import SimpleNamespace

import louke.maestro
from louke.runtime.catalog import DefinitionRegistry, Edge, Step, WorkflowDefinition
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
    )
    end = Step(step_id="end", kind="program")
    return WorkflowDefinition(
        definition_id="ac_fr0701",
        version="1",
        start_step="start",
        steps=(start, end),
    )


def test_ac_fr0701_02_old_maestro_advance_does_not_touch_new_run(tmp_path, monkeypatch):
    """AC-FR0701-02: legacy maestro advance cannot mutate a v0.12 WorkflowRun."""
    project_dir = tmp_path / ".louke" / "project"
    project_dir.mkdir(parents=True)
    project_toml_file = project_dir / "project.toml"
    project_toml_file.write_text(_project_toml("M-DEV"), encoding="utf-8")

    registry = DefinitionRegistry()
    definition = registry.register(_simple_program_definition())

    db_path = tmp_path / ".louke" / "runtime" / "state.sqlite3"
    store = WorkflowRunStore(db_path=str(db_path), catalog=registry)
    run = store.create_run(definition)
    initial_revision = run.revision
    initial_events = store.get_events(run.run_id)

    monkeypatch.chdir(tmp_path)
    args = SimpleNamespace(
        stage="M-MILESTONE",
        spec_id="",
        commit_range="",
        release="",
        confirm=False,
        force=False,
    )
    result = louke.maestro.cmd_advance(args)

    # Legacy advance must be rejected when a v0.12 runtime store is present.
    assert result != 0
    assert _read_current_stage(project_toml_file) == "M-DEV"

    reloaded = WorkflowRunStore(db_path=str(db_path), catalog=registry)
    rerun = reloaded.get_run(run.run_id)
    assert rerun.revision == initial_revision
    assert rerun.current_step == run.current_step
    assert reloaded.get_events(run.run_id) == initial_events


def _read_current_stage(path) -> str:
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("current_stage"):
            return line.split("=", 1)[1].strip().strip('"')
    return ""
