"""FR-0200: Implementation task graph.

Runtime dispatches Archer to produce an internal implementation task DAG
based on the current requirements/design baseline.  Each task carries
``task_id``, ``issue_id``, ``fr_ids``, ``nfr_ids``, ``ac_ids``,
``objective``, ``depends_on``, ``write_scopes``, ``forbidden_scopes``,
``devon_responsibility``, ``shield_responsibility``, ``contracts``,
``commands`` and ``completion_outlets``.  Tasks are independently
verifiable vertical slices.  The DAG is persisted with an internal
``graph_revision`` identity; GitHub Project/Issues keep requirement
identity and are NOT duplicated per internal task (AC-FR0200-01).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

ERROR_CODES = (
    "TASK_DUPLICATE_ID",
    "TASK_DEPENDENCY_MISSING",
    "TASK_GRAPH_CYCLE",
    "TASK_SCOPE_CONFLICT",
    "TASK_AC_ORPHAN",
    "TASK_MANIFEST_INCOMPLETE",
)

_REQUIRED_TASK_KEYS = (
    "task_id",
    "issue_id",
    "fr_ids",
    "ac_ids",
    "objective",
    "depends_on",
    "write_scopes",
    "forbidden_scopes",
    "devon_responsibility",
    "shield_responsibility",
    "contracts",
    "commands",
    "completion_outlets",
)


class TaskGraphError(Exception):
    """A fail-closed task-graph rejection carrying a stable code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


@dataclass(frozen=True)
class TaskNode:
    """A single implementation task in the DAG (AC-FR0200-01).

    Attributes:
        task_id: Internal unique task id (Runtime-allocated).
        issue_id: GitHub Issue id used for requirement traceability; the
            system does NOT create a duplicate Issue per internal task.
        fr_ids: Tuple of FR ids this task implements.
        nfr_ids: Tuple of NFR ids this task implements.
        ac_ids: Tuple of AC anchors this task is responsible for.
        objective: Free-text objective describing the task closure.
        depends_on: Tuple of upstream task_ids that must complete first.
        write_scopes: Tuple of authorised write paths/globs.
        forbidden_scopes: Tuple of explicitly forbidden paths/globs.
        devon_responsibility: Devon's unit/contract/impl responsibility.
        shield_responsibility: Shield's integration/e2e responsibility.
        contracts: Tuple of IF-* contracts the task consumes.
        commands: Mapping of phase->command for the task.
        completion_outlets: Tuple of evidence outlet names produced.
    """

    task_id: str
    issue_id: int
    fr_ids: tuple[str, ...]
    nfr_ids: tuple[str, ...]
    ac_ids: tuple[str, ...]
    objective: str
    depends_on: tuple[str, ...]
    write_scopes: tuple[str, ...]
    forbidden_scopes: tuple[str, ...]
    devon_responsibility: str
    shield_responsibility: str
    contracts: tuple[str, ...]
    commands: dict[str, str]
    completion_outlets: tuple[str, ...]


def _json_canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def _check_task_complete(task: dict[str, Any]) -> None:
    missing = [k for k in _REQUIRED_TASK_KEYS if k not in task or task[k] in (None, "")]
    # ``nfr_ids`` and ``depends_on`` may legitimately be empty for FR-only
    # or root tasks.
    for optional in ("nfr_ids", "depends_on"):
        if optional in missing:
            missing.remove(optional)
    # Empty tuples for list-like fields are still invalid for required ones.
    for k in _REQUIRED_TASK_KEYS:
        if k in task and isinstance(task[k], tuple | list) and len(task[k]) == 0:
            if k in ("nfr_ids", "depends_on"):
                continue
            if k not in missing:
                missing.append(k)
    if missing:
        raise TaskGraphError(
            "TASK_MANIFEST_INCOMPLETE",
            f"task {task.get('task_id', '?')} missing fields: {missing}",
        )


def _check_no_duplicates(tasks: list[dict[str, Any]]) -> None:
    seen: set[str] = set()
    for task in tasks:
        tid = task["task_id"]
        if tid in seen:
            raise TaskGraphError("TASK_DUPLICATE_ID", f"duplicate task_id: {tid}")
        seen.add(tid)


def _check_dependencies(tasks: list[dict[str, Any]]) -> None:
    ids = {task["task_id"] for task in tasks}
    for task in tasks:
        for dep in task.get("depends_on", ()) or ():
            if dep not in ids:
                raise TaskGraphError(
                    "TASK_DEPENDENCY_MISSING",
                    f"task {task['task_id']} depends on unknown {dep}",
                )


def _check_no_cycle(tasks: list[dict[str, Any]]) -> None:
    by_id = {task["task_id"]: task for task in tasks}
    visited: dict[str, int] = {}  # 0=visiting, 1=done

    def dfs(node: str, path: list[str]) -> None:
        state = visited.get(node)
        if state == 0:
            cycle = " -> ".join(path + [node])
            raise TaskGraphError("TASK_GRAPH_CYCLE", f"cycle detected: {cycle}")
        if state == 1:
            return
        visited[node] = 0
        for dep in by_id[node].get("depends_on", ()) or ():
            dfs(dep, path + [node])
        visited[node] = 1

    for task in tasks:
        dfs(task["task_id"], [])


def _check_scope_conflict(tasks: list[dict[str, Any]]) -> None:
    """Two independent tasks (no dep relation) cannot share a write scope.

    Tasks linked by ``depends_on`` may legitimately share scopes (one
    extends the other); unrelated parallel tasks cannot.
    """
    by_id = {task["task_id"]: task for task in tasks}
    scopes_by_task = {
        task["task_id"]: set(task.get("write_scopes", ()) or ()) for task in tasks
    }

    def is_ancestor(a: str, b: str) -> bool:
        """Return True if ``a`` is an ancestor of ``b`` in depends_on."""
        stack = list(by_id[b].get("depends_on", ()) or ())
        seen: set[str] = set()
        while stack:
            current = stack.pop()
            if current in seen:
                continue
            seen.add(current)
            if current == a:
                return True
            stack.extend(by_id[current].get("depends_on", ()) or ())
        return False

    for i, t1 in enumerate(tasks):
        for t2 in tasks[i + 1 :]:
            if is_ancestor(t1["task_id"], t2["task_id"]) or is_ancestor(
                t2["task_id"], t1["task_id"]
            ):
                continue
            overlap = scopes_by_task[t1["task_id"]] & scopes_by_task[t2["task_id"]]
            if overlap:
                raise TaskGraphError(
                    "TASK_SCOPE_CONFLICT",
                    f"tasks {t1['task_id']} and {t2['task_id']} share scopes {sorted(overlap)}",
                )


def _check_ac_closure(
    tasks: list[dict[str, Any]], requirements: dict[str, Any]
) -> None:
    covered: set[str] = set()
    for task in tasks:
        for ac in task.get("ac_ids", ()) or ():
            covered.add(ac)
    required = set(requirements.get("ac_ids", ()) or ())
    orphan = sorted(required - covered)
    if orphan:
        raise TaskGraphError(
            "TASK_AC_ORPHAN",
            f"required AC ids without owning task: {orphan}",
        )


def _to_node(task: dict[str, Any]) -> TaskNode:
    return TaskNode(
        task_id=str(task["task_id"]),
        issue_id=int(task["issue_id"]),
        fr_ids=tuple(task.get("fr_ids", ()) or ()),
        nfr_ids=tuple(task.get("nfr_ids", ()) or ()),
        ac_ids=tuple(task.get("ac_ids", ()) or ()),
        objective=str(task["objective"]),
        depends_on=tuple(task.get("depends_on", ()) or ()),
        write_scopes=tuple(task.get("write_scopes", ()) or ()),
        forbidden_scopes=tuple(task.get("forbidden_scopes", ()) or ()),
        devon_responsibility=str(task["devon_responsibility"]),
        shield_responsibility=str(task["shield_responsibility"]),
        contracts=tuple(task.get("contracts", ()) or ()),
        commands=dict(task.get("commands", {}) or {}),
        completion_outlets=tuple(task.get("completion_outlets", ()) or ()),
    )


def _graph_revision(
    run_id: str,
    baseline: dict[str, Any],
    requirements: dict[str, Any],
    tasks: list[TaskNode],
) -> str:
    payload = _json_canonical(
        {
            "run_id": run_id,
            "baseline": {
                "baseline_id": baseline.get("baseline_id"),
                "base_commit": baseline.get("base_commit"),
                "design_revision": baseline.get("design_revision"),
                "design_digest": baseline.get("design_digest"),
            },
            "requirements": {
                "fr_ids": sorted(requirements.get("fr_ids", ()) or ()),
                "nfr_ids": sorted(requirements.get("nfr_ids", ()) or ()),
                "ac_ids": sorted(requirements.get("ac_ids", ()) or ()),
                "digests": requirements.get("digests", {}) or {},
            },
            "tasks": [
                {
                    "task_id": n.task_id,
                    "issue_id": n.issue_id,
                    "fr_ids": list(n.fr_ids),
                    "nfr_ids": list(n.nfr_ids),
                    "ac_ids": list(n.ac_ids),
                    "objective": n.objective,
                    "depends_on": list(n.depends_on),
                    "write_scopes": list(n.write_scopes),
                    "forbidden_scopes": list(n.forbidden_scopes),
                    "devon_responsibility": n.devon_responsibility,
                    "shield_responsibility": n.shield_responsibility,
                    "contracts": list(n.contracts),
                    "commands": n.commands,
                    "completion_outlets": list(n.completion_outlets),
                }
                for n in tasks
            ],
        }
    )
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
    return f"graph-rev:{digest}"


@dataclass(frozen=True)
class TaskGraphRecord:
    """Persisted implementation task graph (AC-FR0200-01).

    Attributes:
        run_id: Runtime-issued run id.
        baseline_id: Implementation baseline the graph is bound to.
        graph_revision: Deterministic graph revision id.
        tasks: Tuple of :class:`TaskNode`.
        issue_ids: Tuple of GitHub Issue ids referenced by tasks (no duplicates).
    """

    run_id: str
    baseline_id: str
    graph_revision: str
    tasks: tuple[TaskNode, ...]
    issue_ids: tuple[int, ...] = ()
    side_effects_emitted: tuple[str, ...] = field(default_factory=tuple)


def build_task_graph(
    run_id: str,
    baseline: dict[str, Any],
    requirements: dict[str, Any],
    archer_proposal: dict[str, Any],
) -> TaskGraphRecord:
    """Build and validate the implementation task DAG (AC-FR0200-01).

    Args:
        run_id: Runtime-issued run id.
        baseline: Implementation baseline identity (``baseline_id``,
            ``base_commit``, ``design_revision``, ``design_digest``).
        requirements: Mapping with ``fr_ids``, ``nfr_ids``, ``ac_ids`` and
            ``digests``.
        archer_proposal: Archer's proposed DAG with a ``tasks`` list.

    Returns:
        A :class:`TaskGraphRecord` with parsed :class:`TaskNode` tuple and
        a deterministic ``graph_revision``.

    Raises:
        TaskGraphError: With a stable code from :data:`ERROR_CODES` for any
            duplicate id, missing dependency, cycle, scope conflict, orphan
            AC or incomplete task manifest.
    """
    tasks = list(archer_proposal.get("tasks", []) or [])
    if not tasks:
        raise TaskGraphError("TASK_MANIFEST_INCOMPLETE", "no tasks in proposal")
    for task in tasks:
        _check_task_complete(task)
    _check_no_duplicates(tasks)
    _check_dependencies(tasks)
    _check_no_cycle(tasks)
    _check_scope_conflict(tasks)
    _check_ac_closure(tasks, requirements)
    nodes = tuple(_to_node(t) for t in tasks)
    issue_ids = tuple(sorted({n.issue_id for n in nodes}))
    return TaskGraphRecord(
        run_id=run_id,
        baseline_id=str(baseline.get("baseline_id", "")),
        graph_revision=_graph_revision(run_id, baseline, requirements, list(nodes)),
        tasks=nodes,
        issue_ids=issue_ids,
        side_effects_emitted=(),
    )
