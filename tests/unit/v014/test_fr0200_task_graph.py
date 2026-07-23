"""AC-FR0200-01: Implementation task graph.

Runtime must dispatch Archer to generate an internal implementation task
DAG based on the current requirements/design baseline.  Each task carries
``task_id``, ``issue_id``, ``fr_ids``, ``nfr_ids``, ``ac_ids``,
``objective``, ``depends_on``, ``write_scopes``, ``forbidden_scopes``,
``devon_responsibility``, ``shield_responsibility``, ``contracts``,
``commands`` and ``completion_outlets``.  Tasks are independently
verifiable vertical slices.  GitHub Project/Issues keep requirement
identity; the system does NOT create a duplicate GitHub Issue per
internal task or treat the Project board as the execution DAG.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from louke.runtime.task_graph import (
    TaskGraphError,
    TaskGraphRecord,
    TaskNode,
    build_task_graph,
)

_ROOT = Path(__file__).resolve().parents[3]


def _task(
    *,
    task_id: str = "t-001",
    issue_id: int = 284,
    fr_ids: tuple[str, ...] = ("FR-0100",),
    ac_ids: tuple[str, ...] = ("AC-FR0100-01",),
    depends_on: tuple[str, ...] = (),
    write_scopes: tuple[str, ...] = ("louke/v014/fr0100_m_impl_entry.py",),
    objective: str = "Implement M-IMPL entry",
    devon_responsibility: str = "unit + impl",
    shield_responsibility: str = "integration",
    contracts: tuple[str, ...] = ("IF-IMPL-01",),
    completion_outlets: tuple[str, ...] = ("baseline-id",),
) -> dict[str, Any]:
    return {
        "task_id": task_id,
        "issue_id": issue_id,
        "fr_ids": fr_ids,
        "nfr_ids": (),
        "ac_ids": ac_ids,
        "objective": objective,
        "depends_on": depends_on,
        "write_scopes": write_scopes,
        "forbidden_scopes": ("louke/_tools/",),
        "devon_responsibility": devon_responsibility,
        "shield_responsibility": shield_responsibility,
        "contracts": contracts,
        "commands": {"unit": ".venv/bin/python3 -m pytest -q"},
        "completion_outlets": completion_outlets,
    }


def _baseline() -> dict[str, Any]:
    return {
        "baseline_id": "impl-baseline:abc",
        "base_commit": "2734177ef5398e4c10a1f68039ec469ccc21f2b8",
        "design_revision": "design-rev:abc",
        "design_digest": "sha256:" + "a" * 64,
    }


def _requirements() -> dict[str, Any]:
    return {
        "fr_ids": ("FR-0100", "FR-0200"),
        "nfr_ids": (),
        "ac_ids": ("AC-FR0100-01", "AC-FR0200-01"),
        "digests": {
            "spec": "sha256:" + "s" * 64,
            "acceptance": "sha256:" + "a" * 64,
        },
    }


def test_build_task_graph_returns_dag_with_full_closure() -> None:
    """AC-FR0200-01: build_task_graph returns a parsed DAG covering all FR/AC."""
    record = build_task_graph(
        run_id="run-1",
        baseline=_baseline(),
        requirements=_requirements(),
        archer_proposal={
            "tasks": [
                _task(),
                _task(
                    task_id="t-002",
                    issue_id=285,
                    fr_ids=("FR-0200",),
                    ac_ids=("AC-FR0200-01",),
                    write_scopes=("louke/v014/fr0200_task_graph.py",),
                ),
            ]
        },
    )
    assert isinstance(record, TaskGraphRecord)
    assert record.graph_revision.startswith("graph-rev:")
    assert len(record.tasks) == 2
    for node in record.tasks:
        assert isinstance(node, TaskNode)
        assert node.task_id
        assert node.issue_id
        assert node.fr_ids
        assert node.ac_ids
        assert node.objective
        assert node.write_scopes
        assert node.devon_responsibility
        assert node.shield_responsibility
        assert node.contracts
        assert node.completion_outlets


def test_build_task_graph_rejects_missing_required_field() -> None:
    """AC-FR0200-01: missing required field on a task blocks graph build."""
    bad_task = _task()
    del bad_task["devon_responsibility"]
    with pytest.raises(TaskGraphError) as exc:
        build_task_graph(
            run_id="run-1",
            baseline=_baseline(),
            requirements=_requirements(),
            archer_proposal={"tasks": [bad_task]},
        )
    assert exc.value.code == "TASK_MANIFEST_INCOMPLETE"


def test_build_task_graph_rejects_orphan_ac() -> None:
    """AC-FR0200-01: an AC in requirements without any owning task is rejected."""
    requirements = _requirements()
    requirements["ac_ids"] = ("AC-FR0100-01", "AC-FR0200-01", "AC-FR0300-01")
    with pytest.raises(TaskGraphError) as exc:
        build_task_graph(
            run_id="run-1",
            baseline=_baseline(),
            requirements=requirements,
            archer_proposal={"tasks": [_task()]},
        )
    assert exc.value.code == "TASK_AC_ORPHAN"


def test_build_task_graph_rejects_duplicate_task_id() -> None:
    """AC-FR0200-01: duplicate task ids are rejected."""
    with pytest.raises(TaskGraphError) as exc:
        build_task_graph(
            run_id="run-1",
            baseline=_baseline(),
            requirements=_requirements(),
            archer_proposal={
                "tasks": [
                    _task(),
                    _task(
                        task_id="t-001",
                        issue_id=285,
                        fr_ids=("FR-0200",),
                        ac_ids=("AC-FR0200-01",),
                    ),
                ]
            },
        )
    assert exc.value.code == "TASK_DUPLICATE_ID"


def test_build_task_graph_rejects_missing_dependency() -> None:
    """AC-FR0200-01: depends_on referencing an unknown task is rejected."""
    with pytest.raises(TaskGraphError) as exc:
        build_task_graph(
            run_id="run-1",
            baseline=_baseline(),
            requirements=_requirements(),
            archer_proposal={
                "tasks": [
                    _task(task_id="t-001", depends_on=("t-999",)),
                ]
            },
        )
    assert exc.value.code == "TASK_DEPENDENCY_MISSING"


def test_build_task_graph_rejects_cycle() -> None:
    """AC-FR0200-01: cycles in depends_on are rejected."""
    with pytest.raises(TaskGraphError) as exc:
        build_task_graph(
            run_id="run-1",
            baseline=_baseline(),
            requirements=_requirements(),
            archer_proposal={
                "tasks": [
                    _task(
                        task_id="t-001",
                        depends_on=("t-002",),
                        issue_id=284,
                        fr_ids=("FR-0100",),
                        ac_ids=("AC-FR0100-01",),
                    ),
                    _task(
                        task_id="t-002",
                        depends_on=("t-001",),
                        issue_id=285,
                        fr_ids=("FR-0200",),
                        ac_ids=("AC-FR0200-01",),
                    ),
                ]
            },
        )
    assert exc.value.code == "TASK_GRAPH_CYCLE"


def test_build_task_graph_rejects_write_scope_conflict() -> None:
    """AC-FR0200-01: two independent tasks writing the same scope conflict."""
    with pytest.raises(TaskGraphError) as exc:
        build_task_graph(
            run_id="run-1",
            baseline=_baseline(),
            requirements=_requirements(),
            archer_proposal={
                "tasks": [
                    _task(
                        task_id="t-001",
                        write_scopes=("louke/v014/x.py",),
                        issue_id=284,
                        fr_ids=("FR-0100",),
                        ac_ids=("AC-FR0100-01",),
                    ),
                    _task(
                        task_id="t-002",
                        write_scopes=("louke/v014/x.py",),
                        issue_id=285,
                        fr_ids=("FR-0200",),
                        ac_ids=("AC-FR0200-01",),
                    ),
                ]
            },
        )
    assert exc.value.code == "TASK_SCOPE_CONFLICT"


def test_build_task_graph_does_not_create_github_issue_per_task() -> None:
    """AC-FR0200-01: internal task graph maps to existing Issue ids, no duplicates."""
    record = build_task_graph(
        run_id="run-1",
        baseline=_baseline(),
        requirements=_requirements(),
        archer_proposal={
            "tasks": [
                _task(task_id="t-001", issue_id=284),
                _task(
                    task_id="t-002",
                    issue_id=285,
                    fr_ids=("FR-0200",),
                    ac_ids=("AC-FR0200-01",),
                    write_scopes=("louke/v014/fr0200_task_graph.py",),
                ),
            ]
        },
    )
    issue_ids = {n.issue_id for n in record.tasks}
    assert issue_ids == {284, 285}
    # Graph is persisted with internal identity; issues are not duplicated.
    assert record.graph_revision.startswith("graph-rev:")


def test_build_task_graph_deterministic_revision() -> None:
    """AC-FR0200-01: identical inputs produce identical graph_revision."""
    proposal = {
        "tasks": [
            _task(),
            _task(
                task_id="t-002",
                issue_id=285,
                fr_ids=("FR-0200",),
                ac_ids=("AC-FR0200-01",),
                write_scopes=("louke/v014/fr0200_task_graph.py",),
            ),
        ]
    }
    a = build_task_graph("run-1", _baseline(), _requirements(), proposal)
    b = build_task_graph("run-1", _baseline(), _requirements(), proposal)
    assert a.graph_revision == b.graph_revision
