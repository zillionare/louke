"""Workflow graph builder for FR-1201.

This module produces a read-only graph view of a workflow run, based on the
definition the run was bound to at creation time. The graph distinguishes
completed, current, waiting-for-human, blocked, failed, pending and
skipped nodes, and exposes the run's current revision so consumers can
verify they are looking at the same state.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from louke.runtime.catalog import (
    Step,
    WorkflowDefinition,
)

if TYPE_CHECKING:
    from louke.runtime.store import WorkflowRun, WorkflowRunStore


class WorkflowGraphError(Exception):
    """Raised when a graph operation is attempted on a read-only run."""


class GraphNodeState:
    """Stable node state constants for the workflow graph view."""

    COMPLETED = "completed"
    CURRENT = "current"
    WAITING_FOR_HUMAN = "waiting_for_human"
    BLOCKED = "blocked"
    FAILED = "failed"
    PENDING = "pending"
    SKIPPED = "skipped_by_definition"


@dataclass(frozen=True, slots=True)
class GraphNode:
    """A node in the workflow graph view.

    Attributes:
        step_id: The step identifier from the bound definition.
        kind: The step kind (program, human_gate, semantic_task, decision).
        label: Human-readable label, defaults to the step id.
        state: The node's current state (see :class:`GraphNodeState`).
        required: Whether the step is required (affects skip display).
    """

    step_id: str
    kind: str
    label: str
    state: str
    required: bool = True


@dataclass(frozen=True, slots=True)
class GraphEdge:
    """An edge in the workflow graph view.

    Attributes:
        edge_id: The edge identifier from the bound definition.
        from_step: Source step id.
        to_step: Target step id.
        condition: The transition condition.
    """

    edge_id: str
    from_step: str
    to_step: str
    condition: str


@dataclass(frozen=True, slots=True)
class WorkflowGraph:
    """A read-only workflow graph view for a run.

    Attributes:
        run_id: The run the graph was built for.
        definition_id: The definition id the run is bound to.
        definition_version: The definition version the run is bound to.
        nodes: The graph nodes.
        edges: The graph edges.
        current_node_id: The step id of the current node.
        revision: The run revision the graph was built at.
    """

    run_id: str
    definition_id: str
    definition_version: str
    nodes: tuple[GraphNode, ...] = field(default_factory=tuple)
    edges: tuple[GraphEdge, ...] = field(default_factory=tuple)
    current_node_id: str | None = None
    revision: int = 0


class WorkflowGraphBuilder:
    """Build a :class:`WorkflowGraph` from a run's bound definition and state.

    The builder reads the run and its bound definition from the store, then
    computes each node's state based on the run's current step and the
    reachability of steps from the start step.

    Args:
        store: The workflow run store.
    """

    def __init__(self, store: "WorkflowRunStore") -> None:
        self._store = store

    def build(self, run_id: str) -> WorkflowGraph:
        """Build the workflow graph for ``run_id``.

        Args:
            run_id: The run to build the graph for.

        Returns:
            A :class:`WorkflowGraph` showing the run's current state.

        Raises:
            RunNotFoundError: If the run does not exist.
        """
        run = self._store.get_run(run_id)
        definition = self._store.get_definition(run_id)

        completed_steps = self._completed_steps(run_id, definition, run.current_step)
        nodes = tuple(
            self._build_node(step, run, definition, completed_steps)
            for step in definition.steps
        )
        edges = tuple(
            GraphEdge(
                edge_id=edge.edge_id,
                from_step=step.step_id,
                to_step=edge.to_step,
                condition=edge.condition,
            )
            for step in definition.steps
            for edge in step.transitions
        )

        return WorkflowGraph(
            run_id=run.run_id,
            definition_id=definition.definition_id,
            definition_version=definition.version,
            nodes=nodes,
            edges=edges,
            current_node_id=run.current_step,
            revision=run.revision,
        )

    def _completed_steps(
        self,
        run_id: str,
        definition: WorkflowDefinition,
        current_step: str,
    ) -> frozenset[str]:
        """Return the set of steps that have been completed before ``current_step``.

        A step is completed if it is on the path from ``start_step`` to
        ``current_step`` (exclusive) in the definition's transition graph.
        """
        start = definition.start_step
        if current_step == start:
            return frozenset()

        reachable_to_current = self._steps_reaching(definition, current_step)
        return frozenset(
            step_id
            for step_id in reachable_to_current
            if step_id != current_step and step_id != start
        ) | ({start} if start != current_step else set())

    def _steps_reaching(self, definition: WorkflowDefinition, target: str) -> set[str]:
        """Return all step ids that have a path to ``target`` (including target)."""
        reaching: set[str] = {target}
        changed = True
        while changed:
            changed = False
            for step in definition.steps:
                if step.step_id in reaching:
                    continue
                if any(edge.to_step in reaching for edge in step.transitions):
                    reaching.add(step.step_id)
                    changed = True
        return reaching

    def _build_node(
        self,
        step: Step,
        run: "WorkflowRun",
        definition: WorkflowDefinition,
        completed: frozenset[str],
    ) -> GraphNode:
        """Determine the state of ``step`` relative to the run's current position."""
        if step.step_id == run.current_step:
            if step.kind == "human_gate":
                state = GraphNodeState.WAITING_FOR_HUMAN
            elif run.status == "blocked":
                state = GraphNodeState.BLOCKED
            elif run.status == "failed":
                state = GraphNodeState.FAILED
            else:
                state = GraphNodeState.CURRENT
        elif step.step_id in completed:
            state = GraphNodeState.COMPLETED
        elif not step.required and not self._is_on_active_path(step, run, definition):
            state = GraphNodeState.SKIPPED
        else:
            state = GraphNodeState.PENDING

        return GraphNode(
            step_id=step.step_id,
            kind=step.kind,
            label=step.step_id.replace("_", " ").title(),
            state=state,
            required=step.required,
        )

    @staticmethod
    def _is_on_active_path(
        step: Step,
        run: "WorkflowRun",
        definition: WorkflowDefinition,
    ) -> bool:
        """Return True if ``step`` is reachable from the current step."""
        step_by_id = {s.step_id: s for s in definition.steps}
        reachable: set[str] = set()
        queue = [run.current_step]
        while queue:
            current = queue.pop()
            if current in reachable or current not in step_by_id:
                continue
            reachable.add(current)
            for edge in step_by_id[current].transitions:
                if edge.to_step not in reachable:
                    queue.append(edge.to_step)
        return step.step_id in reachable
