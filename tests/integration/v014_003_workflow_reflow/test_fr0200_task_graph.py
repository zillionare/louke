"""Integration tests for FR-0200: Implementation task graph.

AC-FR0200-01: Archer outputs a parseable DAG; each task has Issue/FR/AC,
objective, dependencies, write/forbidden scopes, Devon/Shield
responsibilities, contracts and completion outlets. All effective
requirements have a destination. The task graph is persisted with a
Runtime internal identity and maps to requirement Issues; the system
does NOT duplicate GitHub Issues for internal tasks or treat Project as
an execution DAG.

Interfaces covered (per interfaces.md):
- IF-TASK-01 (Primary ARC-03, ARC-04)
"""
# AC-FR0200-01

from __future__ import annotations

import pytest

from louke.v014.fr0200_task_graph import (
    TaskGraphError,
    TaskGraphRecord,
    TaskNode,
    build_task_graph,
)


def _valid_baseline() -> dict:
    return {
        "baseline_id": "impl-baseline:abc",
        "base_commit": "a" * 40,
        "design_revision": "prism-r3",
        "design_digest": "sha256:design",
    }


def _valid_requirements() -> dict:
    return {
        "fr_ids": ["FR-0100", "FR-0200", "FR-0300"],
        "nfr_ids": ["NFR-0100"],
        "ac_ids": ["AC-FR0100-01", "AC-FR0200-01", "AC-FR0300-01", "AC-NFR0100-01"],
        "digests": {
            "spec": "sha256:spec",
            "acceptance": "sha256:acc",
        },
    }


def _valid_archer_proposal() -> dict:
    return {
        "tasks": [
            {
                "task_id": "T-001",
                "issue_id": 284,
                "fr_ids": ["FR-0100"],
                "nfr_ids": [],
                "ac_ids": ["AC-FR0100-01"],
                "objective": "M-IMPL entry & pre-commit reconcile",
                "depends_on": [],
                "write_scopes": ["louke/v014/fr0100_*.py"],
                "forbidden_scopes": ["tests/"],
                "devon_responsibility": "implement enter_m_impl",
                "shield_responsibility": "integration tests",
                "contracts": ["IF-PC-01"],
                "commands": {
                    "unit": "pytest -q",
                    "integration": "pytest -q tests/integration",
                },
                "completion_outlets": ["unit", "integration"],
            },
            {
                "task_id": "T-002",
                "issue_id": 285,
                "fr_ids": ["FR-0200"],
                "nfr_ids": [],
                "ac_ids": ["AC-FR0200-01"],
                "objective": "Implementation task graph",
                "depends_on": ["T-001"],
                "write_scopes": ["louke/v014/fr0200_*.py"],
                "forbidden_scopes": ["tests/"],
                "devon_responsibility": "implement build_task_graph",
                "shield_responsibility": "integration tests",
                "contracts": ["IF-TASK-01"],
                "commands": {
                    "unit": "pytest -q",
                    "integration": "pytest -q tests/integration",
                },
                "completion_outlets": ["unit", "integration"],
            },
            {
                "task_id": "T-003",
                "issue_id": 286,
                "fr_ids": ["FR-0300"],
                "nfr_ids": ["NFR-0100"],
                "ac_ids": ["AC-FR0300-01", "AC-NFR0100-01"],
                "objective": "Task graph validator + determinism",
                "depends_on": [],
                "write_scopes": ["louke/v014/fr0300_*.py", "louke/v014/nfr0100_*.py"],
                "forbidden_scopes": ["tests/"],
                "devon_responsibility": "implement validator + atomicity",
                "shield_responsibility": "integration tests",
                "contracts": ["IF-TASK-01"],
                "commands": {
                    "unit": "pytest -q",
                    "integration": "pytest -q tests/integration",
                },
                "completion_outlets": ["unit", "integration"],
            },
        ]
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.real_module
def test_build_task_graph_returns_record_with_revision():
    """AC-FR0200-01: valid proposal -> TaskGraphRecord with graph_revision."""
    record = build_task_graph(
        run_id="run-001",
        baseline=_valid_baseline(),
        requirements=_valid_requirements(),
        archer_proposal=_valid_archer_proposal(),
    )
    assert isinstance(record, TaskGraphRecord)
    assert record.graph_revision
    assert record.run_id == "run-001"
    assert len(record.tasks) == 3
    for task in record.tasks:
        assert isinstance(task, TaskNode)
        # Every task must carry Issue/FR/AC/scope/responsibility/outlets
        # (IF-TASK-01 graph input schema).
        assert task.task_id
        assert task.issue_id
        assert task.objective
        assert isinstance(task.write_scopes, tuple)
        assert isinstance(task.forbidden_scopes, tuple)
        assert task.devon_responsibility
        assert task.shield_responsibility


@pytest.mark.real_module
def test_build_task_graph_rejects_duplicate_task_ids():
    """AC-FR0200-01: duplicate task_id -> TASK_DUPLICATE_ID."""
    proposal = _valid_archer_proposal()
    proposal["tasks"][1]["task_id"] = "T-001"  # duplicate
    with pytest.raises(TaskGraphError) as exc:
        build_task_graph(
            run_id="run-001",
            baseline=_valid_baseline(),
            requirements=_valid_requirements(),
            archer_proposal=proposal,
        )
    assert (
        "DUPLICATE" in exc.value.code.upper() or "duplicate" in str(exc.value).lower()
    )


@pytest.mark.real_module
def test_build_task_graph_rejects_missing_dependency():
    """AC-FR0200-01: depends_on non-existent task -> TASK_DEPENDENCY_MISSING."""
    proposal = _valid_archer_proposal()
    proposal["tasks"][0]["depends_on"] = ["T-DOES-NOT-EXIST"]
    with pytest.raises(TaskGraphError) as exc:
        build_task_graph(
            run_id="run-001",
            baseline=_valid_baseline(),
            requirements=_valid_requirements(),
            archer_proposal=proposal,
        )
    assert (
        "DEPENDENCY" in exc.value.code.upper() or "dependency" in str(exc.value).lower()
    )


@pytest.mark.real_module
def test_build_task_graph_rejects_cycle():
    """AC-FR0200-01: cycle in DAG -> TASK_GRAPH_CYCLE."""
    proposal = _valid_archer_proposal()
    # T-001 -> T-002 -> T-001 cycle
    proposal["tasks"][0]["depends_on"] = ["T-002"]
    proposal["tasks"][1]["depends_on"] = ["T-001"]
    with pytest.raises(TaskGraphError) as exc:
        build_task_graph(
            run_id="run-001",
            baseline=_valid_baseline(),
            requirements=_valid_requirements(),
            archer_proposal=proposal,
        )
    assert "CYCLE" in exc.value.code.upper() or "cycle" in str(exc.value).lower()


@pytest.mark.real_module
def test_build_task_graph_rejects_scope_conflict():
    """AC-FR0200-01: two tasks writing same path -> TASK_SCOPE_CONFLICT."""
    proposal = _valid_archer_proposal()
    proposal["tasks"][2]["write_scopes"] = ["louke/v014/fr0200_*.py"]
    with pytest.raises(TaskGraphError) as exc:
        build_task_graph(
            run_id="run-001",
            baseline=_valid_baseline(),
            requirements=_valid_requirements(),
            archer_proposal=proposal,
        )
    assert "SCOPE" in exc.value.code.upper() or "scope" in str(exc.value).lower()


@pytest.mark.real_module
def test_build_task_graph_rejects_orphan_ac():
    """AC-FR0200-01: AC in requirements but not in any task -> TASK_AC_ORPHAN."""
    requirements = _valid_requirements()
    requirements["ac_ids"].append("AC-FR9999-99")  # not covered
    with pytest.raises(TaskGraphError) as exc:
        build_task_graph(
            run_id="run-001",
            baseline=_valid_baseline(),
            requirements=requirements,
            archer_proposal=_valid_archer_proposal(),
        )
    assert "ORPHAN" in exc.value.code.upper() or "orphan" in str(exc.value).lower()


@pytest.mark.real_module
def test_build_task_graph_revision_is_deterministic():
    """AC-FR0200-01: same canonical graph bytes -> same graph_revision
    (IF-TASK-01 idempotency contract)."""
    r1 = build_task_graph(
        run_id="run-001",
        baseline=_valid_baseline(),
        requirements=_valid_requirements(),
        archer_proposal=_valid_archer_proposal(),
    )
    r2 = build_task_graph(
        run_id="run-001",
        baseline=_valid_baseline(),
        requirements=_valid_requirements(),
        archer_proposal=_valid_archer_proposal(),
    )
    assert r1.graph_revision == r2.graph_revision


@pytest.mark.real_module
def test_build_task_graph_revision_changes_on_task_mutation():
    """AC-FR0200-01: graph content change -> new revision (stale propagation
    per IF-TASK-01 idempotency/concurrency contract)."""
    r1 = build_task_graph(
        run_id="run-001",
        baseline=_valid_baseline(),
        requirements=_valid_requirements(),
        archer_proposal=_valid_archer_proposal(),
    )
    proposal = _valid_archer_proposal()
    proposal["tasks"][0]["objective"] = "modified objective"
    r2 = build_task_graph(
        run_id="run-001",
        baseline=_valid_baseline(),
        requirements=_valid_requirements(),
        archer_proposal=proposal,
    )
    assert r1.graph_revision != r2.graph_revision


@pytest.mark.real_module
def test_build_task_graph_does_not_create_github_issues():
    """AC-FR0200-01: internal task_id is Runtime-internal; Issue is a
    requirement identity pointer, not an execution DAG (IF-TASK-01
    persistence contract)."""
    record = build_task_graph(
        run_id="run-001",
        baseline=_valid_baseline(),
        requirements=_valid_requirements(),
        archer_proposal=_valid_archer_proposal(),
    )
    for task in record.tasks:
        # task_id is Runtime-internal (T-XXX), NOT a GitHub Issue number.
        assert task.task_id.startswith("T-")
        # issue_id maps to requirement Issue (int) but is NOT the same identity.
        assert isinstance(task.issue_id, int)
        assert task.task_id != str(task.issue_id)
