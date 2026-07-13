"""FR-0001 AC-2: WorkflowRun creation and retrieval.

AC reference:
- AC-FR0001-02: given a valid definition, creating a WorkflowRun yields a
  query result containing the fixed definition id, version, start step and
  revision 0 (initial revision).
"""

from louke.runtime.catalog import Edge, Step, WorkflowDefinition
from louke.runtime.store import WorkflowRunStore


def _valid_definition() -> WorkflowDefinition:
    start = Step(
        step_id="start",
        kind="program",
        transitions=(Edge(edge_id="e1", from_step="start", to_step="end"),),
    )
    end = Step(step_id="end", kind="program")
    return WorkflowDefinition(
        definition_id="test_flow",
        version="1",
        start_step="start",
        steps=(start, end),
    )


def test_ac_fr0001_02_created_run_has_fixed_definition_and_revision_zero():
    """Creating a WorkflowRun pins the definition and starts at revision 0."""
    store = WorkflowRunStore()
    definition = _valid_definition()

    run = store.create_run(definition)

    assert run.definition_id == definition.definition_id
    assert run.definition_version == definition.version
    assert run.current_step == definition.start_step
    assert run.revision == 0

    fetched = store.get_run(run.run_id)
    assert fetched == run
