"""AC-FR1300-01: M-TEST execution & defect triage.

After Prism approves the test contract, Runtime independently executes
integration/e2e and records runner, environment/fixture, commit, command,
result and covered AC.  Test/fixture errors return to Shield;
implementation defects keep tests and return to Devon; design gaps
return to M-DESIGN; requirements/Acceptance gaps return via Human to
M-SPEC/M-ACC; semantic ambiguity may be diagnosed by Prism, never
punted to Human for technical attribution.  After fixes, affected
layers are re-run and re-reviewed; success creates a controlled test
commit.
"""

from __future__ import annotations


import pytest

from louke.runtime.m_test_executor import (
    MTestExecutionError,
    MTestExecutor,
    SuiteResult,
)

_AC = "AC-FR1300-01"


def _result(
    *,
    suite_id: str = "ie-001",
    layer: str = "integration",
    passed: bool = True,
    defect_category: str | None = None,
    ac_ids: tuple[str, ...] = (_AC,),
) -> SuiteResult:
    return SuiteResult(
        suite_id=suite_id,
        layer=layer,
        passed=passed,
        runner="project-venv",
        environment="py-3.12",
        fixture="fixture-x",
        commit_oid="g" * 40,
        command=".venv/bin/python3 -m pytest -q tests/integration/v014/test_x.py",
        result_digest="sha256:" + "r" * 64,
        ac_ids=ac_ids,
        defect_category=defect_category,
    )


def test_executor_records_full_evidence_for_passing_suite() -> None:
    """AC-FR1300-01: a passing suite records runner/env/fixture/commit/cmd/result/AC."""
    executor = MTestExecutor()
    record = executor.execute(_result())
    assert record.suite_id == "ie-001"
    assert record.passed is True
    assert record.runner == "project-venv"
    assert record.environment == "py-3.12"
    assert record.commit_oid == "g" * 40
    assert "pytest" in record.command
    assert record.result_digest.startswith("sha256:")
    assert _AC in record.ac_ids


def test_executor_routes_test_defect_to_shield() -> None:
    """AC-FR1300-01: test/fixture defect returns to Shield."""
    executor = MTestExecutor()
    route = executor.route_defect(
        _result(passed=False, defect_category="test_or_fixture")
    )
    assert route.target == "Shield"
    assert route.requires_human is False


def test_executor_routes_implementation_defect_to_devon() -> None:
    """AC-FR1300-01: implementation defect returns to Devon with tests preserved."""
    executor = MTestExecutor()
    route = executor.route_defect(
        _result(passed=False, defect_category="implementation")
    )
    assert route.target == "Devon"
    assert route.requires_human is False
    assert route.preserve_tests is True


def test_executor_routes_design_gap_to_m_design() -> None:
    """AC-FR1300-01: design gap returns to M-DESIGN without Human."""
    executor = MTestExecutor()
    route = executor.route_defect(_result(passed=False, defect_category="design"))
    assert route.target == "M-DESIGN"
    assert route.requires_human is False


def test_executor_routes_requirement_gap_via_human() -> None:
    """AC-FR1300-01: requirement gap returns to M-SPEC/M-ACC via Human."""
    executor = MTestExecutor()
    route = executor.route_defect(_result(passed=False, defect_category="requirement"))
    assert route.target == "M-SPEC/M-ACC"
    assert route.requires_human is True


def test_executor_rejects_unknown_defect_category() -> None:
    """AC-FR1300-01: unknown defect category is rejected; Human not asked for tech attribution."""
    executor = MTestExecutor()
    with pytest.raises(MTestExecutionError) as exc:
        executor.route_defect(_result(passed=False, defect_category="unknown"))
    assert exc.value.code == "TEST_DEFECT_ROUTE_INVALID"


def test_executor_rejects_passing_suite_with_defect() -> None:
    """AC-FR1300-01: a passing suite cannot have a defect category."""
    executor = MTestExecutor()
    with pytest.raises(MTestExecutionError) as exc:
        executor.route_defect(_result(passed=True, defect_category="implementation"))
    assert exc.value.code == "TEST_DEFECT_ROUTE_INVALID"


def test_executor_creates_controlled_test_commit_after_all_pass() -> None:
    """AC-FR1300-01: after all required suites pass, Runtime creates a controlled test commit."""
    executor = MTestExecutor()
    executor.execute(_result(suite_id="ie-001"))
    executor.execute(_result(suite_id="ie-002", ac_ids=("AC-FR1300-01",)))
    commit = executor.create_controlled_test_commit(
        branch_oid="g" * 40,
        required_suite_ids=("ie-001", "ie-002"),
    )
    assert commit.branch_oid == "g" * 40
    assert commit.suite_ids == ("ie-001", "ie-002")


def test_executor_rejects_controlled_commit_with_missing_suite() -> None:
    """AC-FR1300-01: controlled test commit requires all required suites to have passed."""
    executor = MTestExecutor()
    executor.execute(_result(suite_id="ie-001"))
    with pytest.raises(MTestExecutionError) as exc:
        executor.create_controlled_test_commit(
            branch_oid="g" * 40,
            required_suite_ids=("ie-001", "ie-002"),
        )
    assert exc.value.code == "TEST_SUITE_REQUIRED_MISSING"


def test_executor_rejects_controlled_commit_with_failed_suite() -> None:
    """AC-FR1300-01: failed required suite blocks controlled commit."""
    executor = MTestExecutor()
    executor.execute(
        _result(suite_id="ie-001", passed=False, defect_category="implementation")
    )
    with pytest.raises(MTestExecutionError) as exc:
        executor.create_controlled_test_commit(
            branch_oid="g" * 40,
            required_suite_ids=("ie-001",),
        )
    assert exc.value.code == "TEST_RUNNER_FAILED"
