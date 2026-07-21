"""Integration tests for FR-1500: Local authoritative quality chain.

AC-FR1500-01: The current candidate's gate evidence includes static
checks, pre-commit all-files/drift, RGR, all historical unit, required
integration/e2e/regression, AC trace, policy, docs/migration and a real
build. Running only the current Spec selector, excluding historical
failures as "unrelated", or having a policy-less skip/quarantine cannot
PASS.

Interfaces covered (per interfaces.md):
- IF-QUAL-01 (Primary ARC-10)
- IF-TEST-02 (suite inventory, ARC-08)
- IF-RGR-01 (RGR lineage, ARC-05)
"""
# AC-FR1500-01

from __future__ import annotations

import pytest

from louke.v014.fr1500_local_quality_chain import (
    ERROR_CODES,
    LocalQualityError,
    LocalQualityReport,
    QualityChainGate,
    QualityGateResult,
)


def _all_pass_gates() -> list[QualityGateResult]:
    names = (
        "format",
        "lint",
        "static",
        "type",
        "precommit-drift",
        "precommit-all-files",
        "rgr-lineage",
        "history-unit",
        "integration",
        "e2e",
        "regression",
        "ac-trace",
        "skip-policy",
        "anti-pattern",
        "docs",
        "migration",
        "compat",
        "build",
    )
    return [QualityGateResult(name=n, status="pass") for n in names]


def _one_pass_gate(name: str) -> QualityGateResult:
    return QualityGateResult(name=name, status="pass")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.real_module
def test_quality_chain_passes_when_all_required_gates_pass():
    """AC-FR1500-01: all 18 required gates pass -> status=pass."""
    gate = QualityChainGate()
    report = gate.evaluate("cand-1", _all_pass_gates())
    assert isinstance(report, LocalQualityReport)
    assert report.status == "pass"
    assert report.failed == ()


@pytest.mark.real_module
def test_quality_chain_fails_when_required_gate_missing():
    """AC-FR1500-01: missing required gate -> QUAL_GATE_MISSING."""
    gates = _all_pass_gates()
    # Remove 'build' gate.
    gates = [g for g in gates if g.name != "build"]
    report = QualityChainGate().evaluate("cand-1", gates)
    assert report.status == "fail"
    assert "build" in report.failed


@pytest.mark.real_module
def test_quality_chain_fails_when_history_unit_excluded():
    """AC-FR1500-01: historical unit failure excluded -> cannot PASS."""
    gates = _all_pass_gates()
    # Replace history-unit gate with fail.
    gates = [
        QualityGateResult(name=g.name, status="fail") if g.name == "history-unit" else g
        for g in gates
    ]
    report = QualityChainGate().evaluate("cand-1", gates)
    assert report.status == "fail"
    assert "history-unit" in report.failed


@pytest.mark.real_module
def test_quality_chain_fails_on_selector_only():
    """AC-FR1500-01: selector_only=True -> diagnostic-only, cannot PASS."""
    report = QualityChainGate().evaluate(
        "cand-1",
        _all_pass_gates(),
        selector_only=True,
    )
    assert report.status == "fail"
    assert "selector-partial" in report.failed


@pytest.mark.real_module
def test_quality_chain_rejects_policy_less_quarantine():
    """AC-FR1500-01: skip without formal policy identity -> QUAL_QUARANTINE_INVALID."""
    gates = _all_pass_gates()
    # Replace 'integration' with a skip without policy.
    gates = [
        QualityGateResult(name="integration", status="skip")
        if g.name == "integration"
        else g
        for g in gates
    ]
    with pytest.raises(LocalQualityError) as exc:
        QualityChainGate().evaluate("cand-1", gates)
    assert exc.value.code == "QUAL_QUARANTINE_INVALID"


@pytest.mark.real_module
def test_quality_chain_accepts_policy_bound_quarantine():
    """AC-FR1500-01: formal policy-bound quarantine is acceptable."""
    gates = _all_pass_gates()
    # Replace 'integration' with a proper policy-bound quarantine.
    gates = [
        QualityGateResult(
            name="integration",
            status="skip",
            policy_digest="sha256:policy",
            issue_id=999,
            owner="keeper",
            scope="tests/integration/x",
            expiry="2026-12-31",
        )
        if g.name == "integration"
        else g
        for g in gates
    ]
    report = QualityChainGate().evaluate("cand-1", gates)
    assert report.status == "pass"


@pytest.mark.real_module
def test_quality_chain_required_gate_set_includes_all_categories():
    """AC-FR1500-01: required gate set covers format/lint/static/type,
    pre-commit drift+all-files, RGR, history unit, integration/e2e/regression,
    AC trace, skip policy, anti-pattern, docs/migration/compat and build."""
    from louke.v014.fr1500_local_quality_chain import _REQUIRED_GATES

    required = set(_REQUIRED_GATES)
    expected_categories = {
        "format",
        "lint",
        "static",
        "type",
        "precommit-drift",
        "precommit-all-files",
        "rgr-lineage",
        "history-unit",
        "integration",
        "e2e",
        "regression",
        "ac-trace",
        "skip-policy",
        "anti-pattern",
        "docs",
        "migration",
        "compat",
        "build",
    }
    missing = expected_categories - required
    assert not missing, f"required gates missing: {missing}"


@pytest.mark.real_module
def test_error_codes_set_covers_all_documented_codes():
    """AC-FR1500-01: ERROR_CODES includes all codes from interfaces.md §8."""
    expected = {
        "QUAL_CONTRACT_NOT_CURRENT",
        "QUAL_GATE_MISSING",
        "QUAL_COMMAND_FAILED",
        "QUAL_TIMEOUT",
        "QUAL_REQUIRED_SUITE_MISSING",
        "QUAL_REQUIRED_SUITE_SKIPPED",
        "QUAL_HISTORY_EXCLUDED",
        "QUAL_SELECTOR_PARTIAL",
        "QUAL_QUARANTINE_INVALID",
        "QUAL_TRACE_INCOMPLETE",
        "QUAL_BUILD_FAILED",
        "QUAL_EVIDENCE_UNKNOWN",
        "QUAL_CANDIDATE_STALE",
    }
    actual = set(ERROR_CODES)
    missing = expected - actual
    assert not missing, f"ERROR_CODES missing: {missing}"
