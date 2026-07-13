"""FR-0001 AC-3: definition versioning and run pinning.

AC reference:
- AC-FR0001-03: given a run already created from definition v1, when a
different definition with the same name and version v2 is registered, the
old run still advances according to v1 steps/transitions and only new runs
use v2.
"""

from louke.runtime.catalog import DefinitionRegistry, Edge, Step, WorkflowDefinition
from louke.runtime.store import WorkflowRunStore


def _definition(version: str, start_step: str) -> WorkflowDefinition:
    return WorkflowDefinition(
        definition_id="evolving_flow",
        version=version,
        start_step=start_step,
        steps=(
            Step(
                step_id=start_step,
                kind="program",
                transitions=(Edge(edge_id="e1", from_step=start_step, to_step="end"),),
            ),
            Step(step_id="end", kind="program"),
        ),
    )


def test_ac_fr0001_03_old_run_pins_v1_after_v2_registered():
    """A run created before a definition upgrade stays bound to v1."""
    registry = DefinitionRegistry()
    v1 = _definition("1", "v1_start")
    registry.register(v1)

    store = WorkflowRunStore(catalog=registry)
    run_v1 = store.create_run(v1)

    v2 = _definition("2", "v2_start")
    registry.register(v2)

    run_v2 = store.create_run(v2)

    assert run_v1.definition_version == "1"
    assert run_v2.definition_version == "2"

    resolved_v1 = store.get_definition(run_v1.run_id)
    resolved_v2 = store.get_definition(run_v2.run_id)

    assert resolved_v1.version == "1"
    assert resolved_v1.start_step == "v1_start"
    assert resolved_v2.version == "2"
    assert resolved_v2.start_step == "v2_start"
