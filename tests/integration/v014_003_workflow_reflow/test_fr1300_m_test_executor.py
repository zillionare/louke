"""Integration tests for FR-1300: M-TEST execution & defect triage.

AC-FR1300-01: Runtime records runner/environment/fixture/commit/command/
result/covered AC for approved tests and, after all pass, creates a
controlled test commit + trace update. Fixture/test defects,
implementation defects, design gaps and requirements gaps route to
Shield, Devon, M-DESIGN and Human-controlled M-SPEC/M-ACC
respectively; technical attribution is never punted to Human.

Interfaces covered (per interfaces.md):
- IF-TEST-02 (Primary ARC-08)
- IF-WFR-01 (workflow context, ARC-01)
- IF-TRACE-01 (trace edges, ARC-16)
"""
# AC-FR1300-01

from __future__ import annotations

import pytest

from louke.v014.fr1300_m_test_executor import (
    ERROR_CODES,
    ControlledTestCommit,
    DefectRoute,
    MTestExecutionError,
    MTestExecutor,
    SuiteResult,
)


def _passing_suite(suite_id: str = "S-001") -> SuiteResult:
    return SuiteResult(
        suite_id=suite_id,
        layer="integration",
        passed=True,
        runner="project-venv",
        environment="py-3.12",
        fixture="fixture-v1",
        commit_oid="c" * 40,
        command="pytest -q tests/integration/v014_003_workflow_reflow",
        result_digest="sha256:ok",
        ac_ids=("AC-FR1300-01",),
    )


def _failing_suite(category: str, suite_id: str = "S-002") -> SuiteResult:
    return SuiteResult(
        suite_id=suite_id,
        layer="integration",
        passed=False,
        runner="project-venv",
        environment="py-3.12",
        fixture="fixture-v1",
        commit_oid="c" * 40,
        command="pytest -q tests/integration/v014_003_workflow_reflow",
        result_digest="sha256:fail",
        ac_ids=("AC-FR1300-01",),
        defect_category=category,
    )


# ---------------------------------------------------------------------------
# execute + route_defect
# ---------------------------------------------------------------------------


@pytest.mark.real_module
def test_execute_records_suite_result():
    """AC-FR1300-01: Runtime records runner/env/fixture/commit/cmd/result/AC."""
    executor = MTestExecutor()
    result = executor.execute(_passing_suite())
    assert isinstance(result, SuiteResult)
    assert result.runner == "project-venv"
    assert result.environment == "py-3.12"
    assert result.fixture == "fixture-v1"
    assert result.commit_oid == "c" * 40
    assert result.command.startswith("pytest")
    assert result.result_digest.startswith("sha256:")
    assert "AC-FR1300-01" in result.ac_ids


@pytest.mark.real_module
def test_route_defect_test_or_fixture_to_shield():
    """AC-FR1300-01: test/fixture defect -> Shield (not Human)."""
    executor = MTestExecutor()
    route = executor.route_defect(_failing_suite("test_or_fixture"))
    assert isinstance(route, DefectRoute)
    assert route.target == "Shield"
    assert route.requires_human is False
    assert route.preserve_tests is False  # tests may need fixing


@pytest.mark.real_module
def test_route_defect_implementation_to_devon_preserving_tests():
    """AC-FR1300-01: implementation defect -> Devon; tests preserved."""
    executor = MTestExecutor()
    route = executor.route_defect(_failing_suite("implementation"))
    assert route.target == "Devon"
    assert route.requires_human is False
    assert route.preserve_tests is True  # tests stay


@pytest.mark.real_module
def test_route_defect_design_to_m_design_no_human():
    """AC-FR1300-01: design gap -> M-DESIGN (Archer+Prism, no Human)."""
    executor = MTestExecutor()
    route = executor.route_defect(_failing_suite("design"))
    assert route.target == "M-DESIGN"
    assert route.requires_human is False


@pytest.mark.real_module
def test_route_defect_requirement_to_m_spec_acc_via_human():
    """AC-FR1300-01: requirement gap -> M-SPEC/M-ACC requires Human."""
    executor = MTestExecutor()
    route = executor.route_defect(_failing_suite("requirement"))
    assert route.target == "M-SPEC/M-ACC"
    assert route.requires_human is True


@pytest.mark.real_module
def test_route_defect_rejects_passing_suite():
    """AC-FR1300-01: passing suite has no defect -> TEST_DEFECT_ROUTE_INVALID."""
    executor = MTestExecutor()
    with pytest.raises(MTestExecutionError) as exc:
        executor.route_defect(_passing_suite())
    assert exc.value.code == "TEST_DEFECT_ROUTE_INVALID"


@pytest.mark.real_module
def test_route_defect_rejects_unknown_category():
    """AC-FR1300-01: unknown category -> TEST_DEFECT_ROUTE_INVALID; Human never
    asked to judge technical attribution."""
    executor = MTestExecutor()
    with pytest.raises(MTestExecutionError) as exc:
        executor.route_defect(_failing_suite("mystery-category"))
    assert exc.value.code == "TEST_DEFECT_ROUTE_INVALID"


# ---------------------------------------------------------------------------
# create_controlled_test_commit
# ---------------------------------------------------------------------------


@pytest.mark.real_module
def test_create_controlled_test_commit_when_all_required_pass():
    """AC-FR1300-01: all required suites pass -> controlled test commit."""
    executor = MTestExecutor()
    executor.execute(_passing_suite("S-001"))
    executor.execute(_passing_suite("S-002"))
    commit = executor.create_controlled_test_commit(
        branch_oid="c" * 40,
        required_suite_ids=("S-001", "S-002"),
    )
    assert isinstance(commit, ControlledTestCommit)
    assert commit.branch_oid == "c" * 40
    assert set(commit.suite_ids) == {"S-001", "S-002"}
    assert commit.commit_id.startswith("test-commit:")


@pytest.mark.real_module
def test_create_controlled_test_commit_rejects_missing_required_suite():
    """AC-FR1300-01: missing required suite -> TEST_SUITE_REQUIRED_MISSING."""
    executor = MTestExecutor()
    executor.execute(_passing_suite("S-001"))
    with pytest.raises(MTestExecutionError) as exc:
        executor.create_controlled_test_commit(
            branch_oid="c" * 40,
            required_suite_ids=("S-001", "S-002"),
        )
    assert exc.value.code == "TEST_SUITE_REQUIRED_MISSING"


@pytest.mark.real_module
def test_create_controlled_test_commit_rejects_failed_required_suite():
    """AC-FR1300-01: failed required suite -> TEST_RUNNER_FAILED."""
    executor = MTestExecutor()
    executor.execute(_passing_suite("S-001"))
    executor.execute(_failing_suite("implementation", "S-002"))
    with pytest.raises(MTestExecutionError) as exc:
        executor.create_controlled_test_commit(
            branch_oid="c" * 40,
            required_suite_ids=("S-001", "S-002"),
        )
    assert exc.value.code == "TEST_RUNNER_FAILED"


@pytest.mark.real_module
def test_error_codes_set_covers_all_documented_codes():
    """AC-FR1300-01: ERROR_CODES includes all codes from interfaces.md §6."""
    expected = {
        "TEST_RUNNER_FAILED",
        "TEST_DEFECT_ROUTE_INVALID",
        "TEST_SUITE_REQUIRED_MISSING",
        "TEST_COMMIT_CONFLICT",
    }
    actual = set(ERROR_CODES)
    missing = expected - actual
    assert not missing, f"ERROR_CODES missing: {missing}"
