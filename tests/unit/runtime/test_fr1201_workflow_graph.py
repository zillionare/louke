"""FR-1201: workflow graph and current position.

AC references:
- AC-FR1201-01: graph displays the run's bound definition id/version; later
  definition upgrades do not change the historical graph.
- AC-FR1201-02: graph distinguishes completed, current, waiting_for_human,
  blocked, failed, pending and skipped_by_definition nodes.
- AC-FR1201-03: graph updates to the same revision after refresh; operating
  the graph alone cannot change Runtime state.
- AC-FR1201-04: historical runs are read-only; write requests cannot change
  their revision, status or events.
"""

from __future__ import annotations

import pytest

from louke.runtime.catalog import (
    DefinitionRegistry,
    Edge,
    Step,
    WorkflowDefinition,
)
from louke.runtime.domain import RuntimeCommand
from louke.runtime.gates import GateService
from louke.runtime.orchestrator import WorkflowOrchestrator
from louke.runtime.projects import ProjectStore
from louke.runtime.store import WorkflowRunStore
from louke.runtime.workflow_graph import (
    GraphNodeState,
    WorkflowGraphBuilder,
)


# -- Definition helpers -------------------------------------------------------


def _graph_definition() -> WorkflowDefinition:
    """Return a definition with multiple steps and branches.

    start -> requirements_approval(human_gate) -> design -> m_lock(human_gate) -> implementation -> archive
                                        |                          |
                                        +-> skipped_step(required=False) -> archive
    """
    start = Step(
        "start",
        "program",
        transitions=(Edge("e1", "start", "requirements_approval", "done"),),
        implemented=True,
    )
    req = Step(
        "requirements_approval",
        "human_gate",
        transitions=(
            Edge("e2", "requirements_approval", "design", "approved"),
            Edge("e2b", "requirements_approval", "skipped_step", "rejected"),
        ),
        implemented=True,
    )
    design = Step(
        "design",
        "program",
        transitions=(Edge("e3", "design", "m_lock", "done"),),
        implemented=True,
    )
    m_lock = Step(
        "m_lock",
        "human_gate",
        transitions=(Edge("e4", "m_lock", "implementation", "approved"),),
        implemented=True,
    )
    impl = Step(
        "implementation",
        "semantic_task",
        capability="agent_task",
        transitions=(Edge("e5", "implementation", "archive", "done"),),
        implemented=True,
    )
    skipped = Step(
        "skipped_step",
        "program",
        required=False,
        transitions=(Edge("e6", "skipped_step", "archive", "done"),),
        implemented=True,
    )
    archive = Step("archive", "program", implemented=True)
    return WorkflowDefinition(
        "graph_test", "1", "start", (start, req, design, m_lock, impl, skipped, archive)
    )


def _create_fixtures() -> tuple[
    DefinitionRegistry, WorkflowRunStore, WorkflowOrchestrator, ProjectStore, object
]:
    registry = DefinitionRegistry()
    definition = registry.register(_graph_definition())
    store = WorkflowRunStore(catalog=registry)
    gate_service = GateService(store)
    orchestrator = WorkflowOrchestrator(store, gate_service=gate_service)
    project_store = ProjectStore(run_store=store)
    run = store.create_run(definition)
    return registry, store, orchestrator, project_store, run


# -- AC-FR1201-01 -------------------------------------------------------------


def test_ac_fr1201_01_graph_shows_bound_definition_version():
    """AC-FR1201-01: graph displays the run's bound definition id/version.

    After the run is created, the graph must show the definition id and
    version the run was bound to at creation time. If the definition is
    later upgraded to v2, the run's graph still shows v1.
    """
    registry, store, _orch, _ps, run = _create_fixtures()

    graph = WorkflowGraphBuilder(store).build(run.run_id)

    assert graph.definition_id == "graph_test"
    assert graph.definition_version == "1"
    assert len(graph.nodes) == 7
    assert graph.run_id == run.run_id

    # Register a v2 of the same definition
    v2_def = WorkflowDefinition("graph_test", "2", "start", (Step("start", "program"),))
    registry.register(v2_def)

    # The existing run's graph still shows v1
    graph_after = WorkflowGraphBuilder(store).build(run.run_id)
    assert graph_after.definition_version == "1"


# -- AC-FR1201-02 -------------------------------------------------------------


def test_ac_fr1201_02_node_states_distinguishable():
    """AC-FR1201-02: graph distinguishes completed, current, pending, skipped.

    After advancing the run past ``start``, the start node is ``completed``,
    the current node is highlighted, not-yet-reached nodes are ``pending``,
    and ``skipped_step`` (required=False, not on the taken path) is
    ``skipped_by_definition`` or ``pending``.
    """
    _reg, store, orchestrator, _ps, run = _create_fixtures()

    # Advance start -> requirements_approval
    orchestrator.apply_command(
        RuntimeCommand(run_id=run.run_id, expected_revision=run.revision, result="done")
    )

    graph = WorkflowGraphBuilder(store).build(run.run_id)

    start_node = next(n for n in graph.nodes if n.step_id == "start")
    assert start_node.state == GraphNodeState.COMPLETED

    req_node = next(n for n in graph.nodes if n.step_id == "requirements_approval")
    assert req_node.state == GraphNodeState.WAITING_FOR_HUMAN
    assert graph.current_node_id == "requirements_approval"

    design_node = next(n for n in graph.nodes if n.step_id == "design")
    assert design_node.state == GraphNodeState.PENDING

    skipped_node = next(n for n in graph.nodes if n.step_id == "skipped_step")
    assert skipped_node.state in (
        GraphNodeState.PENDING,
        GraphNodeState.SKIPPED,
    )


# -- AC-FR1201-03 -------------------------------------------------------------


def test_ac_fr1201_03_graph_refreshes_to_same_revision():
    """AC-FR1201-03: graph updates after revision change.

    After the run advances, the graph must reflect the new revision and
    current position. Building the graph alone must not change the run
    state.
    """
    _reg, store, orchestrator, _ps, run = _create_fixtures()

    graph_before = WorkflowGraphBuilder(store).build(run.run_id)
    assert graph_before.revision == run.revision

    orchestrator.apply_command(
        RuntimeCommand(run_id=run.run_id, expected_revision=run.revision, result="done")
    )

    updated_run = store.get_run(run.run_id)
    graph_after = WorkflowGraphBuilder(store).build(run.run_id)
    assert graph_after.revision == updated_run.revision
    assert graph_after.current_node_id == "requirements_approval"

    # Building the graph did not change state
    same_run = store.get_run(run.run_id)
    assert same_run.revision == updated_run.revision


# -- AC-FR1201-04 -------------------------------------------------------------


def test_ac_fr1201_04_historical_run_read_only():
    """AC-FR1201-04: archived/historical runs are read-only.

    After a project is archived, its run cannot be advanced. Any write
    request must be rejected, and the revision, status and events must
    remain unchanged.
    """
    from louke.runtime.projects import ProjectStore

    registry = DefinitionRegistry()
    registry.register(_graph_definition())
    store = WorkflowRunStore(catalog=registry)
    gate_service = GateService(store)
    orchestrator = WorkflowOrchestrator(store, gate_service=gate_service)
    project_store = ProjectStore(run_store=store)

    project = project_store.create_project(
        story="Archived project",
        release_version="v0.12.0",
        definition_id="graph_test",
        definition_version="1",
    )
    project_store.archive_project(project.project_id)

    archived_run = store.get_run(project.run_id)
    with pytest.raises(Exception):
        orchestrator.apply_command(
            RuntimeCommand(
                run_id=project.run_id,
                expected_revision=archived_run.revision,
                result="done",
            )
        )

    same_run = store.get_run(project.run_id)
    assert same_run.revision == archived_run.revision
