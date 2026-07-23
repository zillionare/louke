"""AC-FR1500-01: Local authoritative quality chain.

Runtime executes against the same candidate the full chain of project-local
format/lint/static/type, pre-commit config/installation drift + all-files,
RGR lineage, all historical host unit tests, all required integration/e2e/
regression, AC bidirectional trace, skip/quarantine policy, anti-pattern,
docs/migration/compat and a real build.  Local selectors are diagnostic
only; historical tests may only be excluded via formal policy-bound
quarantine/deprecation.  No selector, skip or missing policy identity may
PASS.
"""

from __future__ import annotations


import pytest

from louke.runtime.local_quality_chain import (
    LocalQualityError,
    LocalQualityReport,
    QualityChainGate,
    QualityGateResult,
)

_CAND = "cand:abc"


def _gates(
    *, all_pass: bool = True, failing: tuple[str, ...] = ()
) -> list[QualityGateResult]:
    names = [
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
    ]
    return [
        QualityGateResult(
            name=n,
            status="pass"
            if (all_pass and n not in failing)
            else ("fail" if n in failing else "pass"),
        )
        for n in names
    ]


def test_quality_chain_passes_when_all_required_gates_pass() -> None:
    """AC-FR1500-01: full chain passes when every required gate passes."""
    gate = QualityChainGate()
    report = gate.evaluate(_CAND, _gates())
    assert isinstance(report, LocalQualityReport)
    assert report.status == "pass"
    assert len(report.failed) == 0


def test_quality_chain_fails_when_history_unit_excluded_by_selector() -> None:
    """AC-FR1500-01: excluding history unit tests by selector is diagnostic-only, not PASS."""
    gate = QualityChainGate()
    report = gate.evaluate(_CAND, _gates(all_pass=True), selector_only=True)
    assert report.status == "fail"
    assert "selector-partial" in report.failed


def test_quality_chain_fails_when_history_unit_fails() -> None:
    """AC-FR1500-01: failing history unit cannot be excluded without policy quarantine."""
    gate = QualityChainGate()
    report = gate.evaluate(_CAND, _gates(failing=("history-unit",)))
    assert report.status == "fail"
    assert "history-unit" in report.failed


def test_quality_chain_fails_when_required_integration_skipped() -> None:
    """AC-FR1500-01: required integration suite skip blocks PASS."""
    gate = QualityChainGate()
    report = gate.evaluate(_CAND, _gates(failing=("integration",)))
    assert report.status == "fail"
    assert "integration" in report.failed


def test_quality_chain_fails_when_build_fails() -> None:
    """AC-FR1500-01: real build failure blocks PASS."""
    gate = QualityChainGate()
    report = gate.evaluate(_CAND, _gates(failing=("build",)))
    assert report.status == "fail"
    assert "build" in report.failed


def test_quality_chain_fails_when_ac_trace_incomplete() -> None:
    """AC-FR1500-01: AC bidirectional trace failure blocks PASS."""
    gate = QualityChainGate()
    report = gate.evaluate(_CAND, _gates(failing=("ac-trace",)))
    assert report.status == "fail"
    assert "ac-trace" in report.failed


def test_quality_chain_fails_when_precommit_drift() -> None:
    """AC-FR1500-01: pre-commit config/installation drift blocks PASS."""
    gate = QualityChainGate()
    report = gate.evaluate(_CAND, _gates(failing=("precommit-drift",)))
    assert report.status == "fail"
    assert "precommit-drift" in report.failed


def test_quality_chain_rejects_invalid_quarantine_without_policy_identity() -> None:
    """AC-FR1500-01: skip/quarantine requires formal policy identity."""
    gate = QualityChainGate()
    # Replace history-unit gate with a SKIP without policy identity.
    gates = _gates()
    gates = [
        g
        if g.name != "history-unit"
        else QualityGateResult(name="history-unit", status="skip")  # no policy_digest
        for g in gates
    ]
    with pytest.raises(LocalQualityError) as exc:
        gate.evaluate(_CAND, gates)
    assert exc.value.code == "QUAL_QUARANTINE_INVALID"


def test_quality_chain_accepts_policy_bound_quarantine() -> None:
    """AC-FR1500-01: policy-bound quarantine with policy_digest is acceptable."""
    gate = QualityChainGate()
    # Replace history-unit gate with a policy-bound SKIP.
    gates = _gates()
    gates = [
        g
        if g.name != "history-unit"
        else QualityGateResult(
            name="history-unit",
            status="skip",
            policy_digest="sha256:" + "p" * 64,
            issue_id=999,
            owner="Devon",
            scope="tests/legacy/",
            expiry="2026-12-31",
        )
        for g in gates
    ]
    report = gate.evaluate(_CAND, gates)
    assert report.status == "pass"
