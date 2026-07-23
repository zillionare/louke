"""AC-FR0300-01: Task graph program validation & review.

Runtime validates that the task graph has no duplicate id, no missing
dependency, no cycle, no write-scope conflict, no orphan AC/task, and that
every effective FR/AC has an implementation + verification responsibility.
Prism independently reviews the graph for implementability, testability
and design consistency.  Any graph change creates a new revision and
makes the old review stale.  Design gaps return to M-DESIGN; product gaps
return to M-SPEC/M-ACC only via Human; Devon does not improvise design.
"""

from __future__ import annotations

from typing import Any

import pytest

from louke.runtime.task_graph_validator import (
    PrismVerdict,
    TaskGraphValidationError,
    TaskGraphValidator,
    ValidationReport,
    route_gap,
)

_PRISM_PASS = PrismVerdict(
    verdict="PASS", review_id="rev-1", subject_digest="sha256:" + "p" * 64
)
_PRISM_REVISE = PrismVerdict(
    verdict="REVISE", review_id="rev-1", subject_digest="sha256:" + "p" * 64
)


def _graph(
    *,
    tasks: list[dict[str, Any]] | None = None,
    requirements: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if tasks is None:
        tasks = [
            {
                "task_id": "t-001",
                "issue_id": 284,
                "fr_ids": ["FR-0100"],
                "nfr_ids": [],
                "ac_ids": ["AC-FR0100-01"],
                "objective": "x",
                "depends_on": [],
                "write_scopes": ["a.py"],
                "forbidden_scopes": [],
                "devon_responsibility": "unit+impl",
                "shield_responsibility": "integration",
                "contracts": ["IF-IMPL-01"],
                "commands": {"unit": "x"},
                "completion_outlets": ["baseline"],
            },
            {
                "task_id": "t-002",
                "issue_id": 285,
                "fr_ids": ["FR-0200"],
                "nfr_ids": [],
                "ac_ids": ["AC-FR0200-01"],
                "objective": "y",
                "depends_on": ["t-001"],
                "write_scopes": ["b.py"],
                "forbidden_scopes": [],
                "devon_responsibility": "unit+impl",
                "shield_responsibility": "integration",
                "contracts": ["IF-TASK-01"],
                "commands": {"unit": "y"},
                "completion_outlets": ["graph"],
            },
        ]
    if requirements is None:
        requirements = {
            "fr_ids": ["FR-0100", "FR-0200"],
            "nfr_ids": [],
            "ac_ids": ["AC-FR0100-01", "AC-FR0200-01"],
        }
    return {
        "run_id": "run-1",
        "baseline_id": "impl-baseline:abc",
        "graph_revision": "graph-rev:abc",
        "requirements": requirements,
        "tasks": tasks,
    }


def test_validator_passes_for_valid_graph() -> None:
    """AC-FR0300-01: a valid graph passes program validation."""
    validator = TaskGraphValidator()
    report = validator.validate(_graph())
    assert isinstance(report, ValidationReport)
    assert report.status == "pass"
    assert len(report.diagnostics) == 0


def test_validator_fails_for_duplicate_id() -> None:
    """AC-FR0300-01: duplicate task_id fails validation."""
    graph = _graph()
    graph["tasks"][1]["task_id"] = "t-001"
    validator = TaskGraphValidator()
    report = validator.validate(graph)
    assert report.status == "fail"
    codes = {d.code for d in report.diagnostics}
    assert "TASK_DUPLICATE_ID" in codes


def test_validator_fails_for_missing_dependency() -> None:
    """AC-FR0300-01: missing dependency fails validation."""
    graph = _graph()
    graph["tasks"][0]["depends_on"] = ["t-999"]
    validator = TaskGraphValidator()
    report = validator.validate(graph)
    assert report.status == "fail"
    assert any(d.code == "TASK_DEPENDENCY_MISSING" for d in report.diagnostics)


def test_validator_fails_for_cycle() -> None:
    """AC-FR0300-01: cycle fails validation."""
    graph = _graph()
    # t-001 -> t-002 -> t-001 cycle
    graph["tasks"][0]["depends_on"] = ["t-002"]
    validator = TaskGraphValidator()
    report = validator.validate(graph)
    assert report.status == "fail"
    assert any(d.code == "TASK_GRAPH_CYCLE" for d in report.diagnostics)


def test_validator_fails_for_scope_conflict() -> None:
    """AC-FR0300-01: independent tasks sharing a write scope fail validation."""
    graph = _graph()
    graph["tasks"][1]["depends_on"] = []  # make t-002 independent of t-001
    graph["tasks"][1]["write_scopes"] = ["a.py"]  # same as t-001
    validator = TaskGraphValidator()
    report = validator.validate(graph)
    assert report.status == "fail"
    assert any(d.code == "TASK_SCOPE_CONFLICT" for d in report.diagnostics)


def test_validator_fails_for_orphan_ac() -> None:
    """AC-FR0300-01: a required AC with no owning task fails validation."""
    graph = _graph()
    graph["requirements"]["ac_ids"] = ["AC-FR0100-01", "AC-FR0200-01", "AC-FR0300-01"]
    validator = TaskGraphValidator()
    report = validator.validate(graph)
    assert report.status == "fail"
    assert any(d.code == "TASK_AC_ORPHAN" for d in report.diagnostics)


def test_validator_fails_for_orphan_task() -> None:
    """AC-FR0300-01: a task with no FR/NFR/AC ownership fails validation."""
    graph = _graph()
    graph["tasks"][1]["fr_ids"] = []
    graph["tasks"][1]["ac_ids"] = []
    validator = TaskGraphValidator()
    report = validator.validate(graph)
    assert report.status == "fail"
    assert any(d.code == "TASK_ORPHAN" for d in report.diagnostics)


def test_validator_fails_when_devon_or_shield_missing() -> None:
    """AC-FR0300-01: every AC must have implementation + verification owner."""
    graph = _graph()
    graph["tasks"][1]["shield_responsibility"] = ""
    validator = TaskGraphValidator()
    report = validator.validate(graph)
    assert report.status == "fail"
    assert any(d.code == "TASK_MANIFEST_INCOMPLETE" for d in report.diagnostics)


def test_graph_revision_change_makes_old_review_stale() -> None:
    """AC-FR0300-01: a graph revision change supersedes the prior Prism review."""
    validator = TaskGraphValidator()
    validator.attach_prism_review(_graph(), _PRISM_PASS)
    assert validator.current_prism_review("graph-rev:abc").verdict == "PASS"
    new_graph = _graph()
    new_graph["graph_revision"] = "graph-rev:def"
    # Attaching a verdict for the new revision makes the prior stale.
    validator.attach_prism_review(new_graph, _PRISM_PASS)
    assert validator.current_prism_review("graph-rev:def").verdict == "PASS"
    assert validator.current_prism_review("graph-rev:abc").status == "stale"


def test_only_prism_pass_unblocks_next_phase() -> None:
    """AC-FR0300-01: only a current Prism PASS combined with program PASS unblocks."""
    validator = TaskGraphValidator()
    validator.attach_prism_review(_graph(), _PRISM_REVISE)
    blocked = validator.can_advance(_graph())
    assert blocked is False
    validator.attach_prism_review(_graph(), _PRISM_PASS)
    assert validator.can_advance(_graph()) is True


def test_design_gap_routes_to_m_design() -> None:
    """AC-FR0300-01: design gap returns to M-DESIGN without Human."""
    route = route_gap("design", evidence=("rev-1", "anchor-1"))
    assert route.target == "M-DESIGN"
    assert route.requires_human is False


def test_product_gap_routes_to_m_spec_via_human() -> None:
    """AC-FR0300-01: product gap requires Human before returning to M-SPEC/M-ACC."""
    route = route_gap("product", evidence=("rev-1", "anchor-1"))
    assert route.target == "M-SPEC/M-ACC"
    assert route.requires_human is True


def test_unknown_gap_type_rejected() -> None:
    """AC-FR0300-01: an unknown gap type is rejected (no improvisation)."""
    with pytest.raises(TaskGraphValidationError) as exc:
        route_gap("technical-decision", evidence=("rev-1",))
    assert exc.value.code == "TASK_ROUTE_INVALID"
