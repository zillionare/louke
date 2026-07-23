"""Integration tests for FR-0300: Task graph program validation & Prism review.

AC-FR0300-01: For duplicate ID / missing dependency / cycle / scope
conflict / orphan AC-or-task fixtures, the program gate fails
independently; a valid DAG gets a baseline-bound Prism PASS. Modifying
the DAG after review makes the old review stale. Design gaps return to
M-DESIGN; product gaps require Human before returning to M-SPEC/M-ACC.

Interfaces covered (per interfaces.md):
- IF-TASK-01 (Primary ARC-03)
- IF-REV-02 (Prism review freshness, ARC-07)
- IF-WFR-01 (downstream workflow current, ARC-01)
"""
# AC-FR0300-01

from __future__ import annotations

import pytest

from louke.runtime.task_graph_validator import (
    ERROR_CODES,
    GapRoute,
    PrismVerdict,
    TaskGraphValidationError,
    TaskGraphValidator,
    ValidationReport,
    route_gap,
)


def _valid_graph() -> dict:
    return {
        "run_id": "run-001",
        "baseline_id": "impl-baseline:abc",
        "graph_revision": "rev-1",
        "requirements": {
            "fr_ids": ["FR-0100"],
            "nfr_ids": [],
            "ac_ids": ["AC-FR0100-01"],
        },
        "tasks": [
            {
                "task_id": "T-001",
                "issue_id": 284,
                "fr_ids": ["FR-0100"],
                "nfr_ids": [],
                "ac_ids": ["AC-FR0100-01"],
                "objective": "M-IMPL entry",
                "depends_on": [],
                "write_scopes": ["louke/v014/fr0100_*.py"],
                "forbidden_scopes": ["tests/"],
                "devon_responsibility": "implement",
                "shield_responsibility": "tests",
                "contracts": ["IF-PC-01"],
                "commands": {"unit": "pytest -q"},
                "completion_outlets": ["unit"],
            }
        ],
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.real_module
def test_validate_passes_on_valid_dag():
    """AC-FR0300-01: valid DAG -> status=pass with no diagnostics."""
    validator = TaskGraphValidator()
    report = validator.validate(_valid_graph())
    assert isinstance(report, ValidationReport)
    assert report.status == "pass"
    assert report.diagnostics == ()
    assert report.graph_revision == "rev-1"


@pytest.mark.real_module
def test_validate_fails_on_duplicate_task_id():
    """AC-FR0300-01: duplicate task_id -> TASK_DUPLICATE_ID diagnostic."""
    graph = _valid_graph()
    graph["tasks"].append(dict(graph["tasks"][0]))  # same task_id
    report = TaskGraphValidator().validate(graph)
    assert report.status == "fail"
    codes = {d.code for d in report.diagnostics}
    assert "TASK_DUPLICATE_ID" in codes


@pytest.mark.real_module
def test_validate_fails_on_missing_dependency():
    """AC-FR0300-01: depends_on unknown task -> TASK_DEPENDENCY_MISSING."""
    graph = _valid_graph()
    graph["tasks"][0]["depends_on"] = ["T-DOES-NOT-EXIST"]
    report = TaskGraphValidator().validate(graph)
    assert report.status == "fail"
    codes = {d.code for d in report.diagnostics}
    assert "TASK_DEPENDENCY_MISSING" in codes


@pytest.mark.real_module
def test_validate_fails_on_cycle():
    """AC-FR0300-01: cycle in DAG -> TASK_GRAPH_CYCLE diagnostic."""
    graph = _valid_graph()
    graph["tasks"].append(
        {
            "task_id": "T-002",
            "issue_id": 285,
            "fr_ids": ["FR-0200"],
            "nfr_ids": [],
            "ac_ids": ["AC-FR0200-01"],
            "objective": "x",
            "depends_on": ["T-001"],
            "write_scopes": ["louke/v014/fr0200_*.py"],
            "forbidden_scopes": ["tests/"],
            "devon_responsibility": "x",
            "shield_responsibility": "x",
            "contracts": ["IF-TASK-01"],
            "commands": {"unit": "pytest -q"},
            "completion_outlets": ["unit"],
        }
    )
    # T-001 -> T-002 -> T-001 cycle
    graph["tasks"][0]["depends_on"] = ["T-002"]
    graph["requirements"]["fr_ids"].append("FR-0200")
    graph["requirements"]["ac_ids"].append("AC-FR0200-01")
    report = TaskGraphValidator().validate(graph)
    assert report.status == "fail"
    codes = {d.code for d in report.diagnostics}
    assert "TASK_GRAPH_CYCLE" in codes


@pytest.mark.real_module
def test_validate_fails_on_scope_conflict():
    """AC-FR0300-01: two non-ancestor tasks write same path -> TASK_SCOPE_CONFLICT."""
    graph = _valid_graph()
    graph["tasks"].append(
        {
            "task_id": "T-002",
            "issue_id": 285,
            "fr_ids": ["FR-0200"],
            "nfr_ids": [],
            "ac_ids": ["AC-FR0200-01"],
            "objective": "x",
            "depends_on": [],
            "write_scopes": ["louke/v014/fr0100_*.py"],  # conflict!
            "forbidden_scopes": ["tests/"],
            "devon_responsibility": "x",
            "shield_responsibility": "x",
            "contracts": ["IF-TASK-01"],
            "commands": {"unit": "pytest -q"},
            "completion_outlets": ["unit"],
        }
    )
    graph["requirements"]["fr_ids"].append("FR-0200")
    graph["requirements"]["ac_ids"].append("AC-FR0200-01")
    report = TaskGraphValidator().validate(graph)
    assert report.status == "fail"
    codes = {d.code for d in report.diagnostics}
    assert "TASK_SCOPE_CONFLICT" in codes


@pytest.mark.real_module
def test_validate_fails_on_orphan_ac():
    """AC-FR0300-01: AC declared but no task covers it -> TASK_AC_ORPHAN."""
    graph = _valid_graph()
    graph["requirements"]["ac_ids"].append("AC-FR9999-99")
    report = TaskGraphValidator().validate(graph)
    assert report.status == "fail"
    codes = {d.code for d in report.diagnostics}
    assert "TASK_AC_ORPHAN" in codes


@pytest.mark.real_module
def test_validate_fails_on_orphan_task_no_ownership():
    """AC-FR0300-01: task with no FR/NFR/AC ownership -> TASK_ORPHAN."""
    graph = _valid_graph()
    graph["tasks"][0]["fr_ids"] = []
    graph["tasks"][0]["nfr_ids"] = []
    graph["tasks"][0]["ac_ids"] = []
    # remove orphan AC requirement so only TASK_ORPHAN fires
    graph["requirements"]["ac_ids"] = []
    graph["requirements"]["fr_ids"] = []
    report = TaskGraphValidator().validate(graph)
    assert report.status == "fail"
    codes = {d.code for d in report.diagnostics}
    assert "TASK_ORPHAN" in codes


@pytest.mark.real_module
def test_validate_fails_on_missing_devon_shield_responsibility():
    """AC-FR0300-01: missing devon/shield responsibility -> TASK_MANIFEST_INCOMPLETE."""
    graph = _valid_graph()
    graph["tasks"][0]["devon_responsibility"] = ""
    report = TaskGraphValidator().validate(graph)
    assert report.status == "fail"
    codes = {d.code for d in report.diagnostics}
    assert "TASK_MANIFEST_INCOMPLETE" in codes


@pytest.mark.real_module
def test_route_gap_design_returns_m_design_no_human():
    """AC-FR0300-01: design gap -> M-DESIGN without Human (Devon cannot improvise)."""
    route = route_gap("design", evidence=("review-1", "finding-2"))
    assert isinstance(route, GapRoute)
    assert route.target == "M-DESIGN"
    assert route.requires_human is False
    assert "review-1" in route.evidence


@pytest.mark.real_module
def test_route_gap_product_returns_m_spec_acc_with_human():
    """AC-FR0300-01: product gap -> M-SPEC/M-ACC requires Human approval."""
    route = route_gap("product")
    assert route.target == "M-SPEC/M-ACC"
    assert route.requires_human is True


@pytest.mark.real_module
def test_route_gap_rejects_unknown_kind():
    """AC-FR0300-01: unknown gap kind -> TASK_ROUTE_INVALID; no improvisation."""
    with pytest.raises(TaskGraphValidationError) as exc:
        route_gap("arbitrary")
    assert exc.value.code == "TASK_ROUTE_INVALID"


@pytest.mark.real_module
def test_prism_review_pass_unblocks_advance():
    """AC-FR0300-01: program+Prism PASS current -> can_advance True."""
    validator = TaskGraphValidator()
    graph = _valid_graph()
    verdict = PrismVerdict(
        verdict="PASS",
        review_id="rev-001",
        subject_digest="sha256:graph-bytes",
    )
    validator.attach_prism_review(graph, verdict)
    assert validator.can_advance(graph) is True


@pytest.mark.real_module
def test_prism_review_revise_blocks_advance():
    """AC-FR0300-01: REVISE verdict blocks advance."""
    validator = TaskGraphValidator()
    graph = _valid_graph()
    verdict = PrismVerdict(
        verdict="REVISE",
        review_id="rev-001",
        subject_digest="sha256:graph-bytes",
    )
    validator.attach_prism_review(graph, verdict)
    assert validator.can_advance(graph) is False


@pytest.mark.real_module
def test_graph_mutation_makes_old_prism_review_stale():
    """AC-FR0300-01: graph revision change -> old review stale; can_advance False."""
    validator = TaskGraphValidator()
    graph_v1 = _valid_graph()
    verdict_v1 = PrismVerdict(
        verdict="PASS", review_id="rev-001", subject_digest="sha256:v1"
    )
    validator.attach_prism_review(graph_v1, verdict_v1)
    assert validator.can_advance(graph_v1) is True

    # New revision -> old review stale.
    graph_v2 = dict(graph_v1)
    graph_v2["graph_revision"] = "rev-2"
    verdict_v2 = PrismVerdict(
        verdict="PASS", review_id="rev-002", subject_digest="sha256:v2"
    )
    validator.attach_prism_review(graph_v2, verdict_v2)
    # Old review for rev-1 is now stale (AC-FR0300-01).
    old = validator.current_prism_review("rev-1")
    assert old and old.status == "stale"
    # can_advance for v1 graph now False (review stale).
    assert validator.can_advance(graph_v1) is False
    # can_advance for v2 graph is True (current review).
    assert validator.can_advance(graph_v2) is True


@pytest.mark.real_module
def test_error_codes_set_covers_all_documented_codes():
    """AC-FR0300-01: ERROR_CODES tuple includes all codes from interfaces.md §3."""
    expected = {
        "TASK_DUPLICATE_ID",
        "TASK_DEPENDENCY_MISSING",
        "TASK_GRAPH_CYCLE",
        "TASK_SCOPE_CONFLICT",
        "TASK_AC_ORPHAN",
        "TASK_ORPHAN",
        "TASK_MANIFEST_INCOMPLETE",
        "TASK_ROUTE_INVALID",
    }
    actual = set(ERROR_CODES)
    missing = expected - actual
    assert not missing, f"ERROR_CODES missing: {missing}"
