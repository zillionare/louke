"""Integration tests for FR-2000: Security finding routing & policy skip.

AC-FR2000-01: Implementation, test, design and product-contract
security findings route to their defined paths; after fixes, a new
candidate's affected implementation/tests + full M-VERIFY + Judge are
re-run. Critical/high or policy-forbidden findings cannot be waived;
legitimate skips must record current policy digest/rationale/scope, and
sensitive-boundary (auth/permission/secret/payment/data) changes may
NOT be silently skipped by ordinary rules.

Interfaces covered (per interfaces.md):
- IF-SEC-01 (Primary ARC-13)
- IF-WFR-01 (workflow context, ARC-01)
- IF-CAND-01 (candidate stale, ARC-09)
"""
# AC-FR2000-01

from __future__ import annotations

import pytest

from louke.v014.fr2000_finding_routing import (
    ERROR_CODES,
    FindingRouteError,
    PolicySkip,
    RouteDecision,
    SecurityFinding,
    WaiverDecision,
    WaiverEvaluation,
    evaluate_waiver,
    route_finding,
    validate_skip,
)


def _finding(
    route: str = "implementation", severity: str = "medium"
) -> SecurityFinding:
    return SecurityFinding(
        finding_id="F-001",
        candidate_id="cand-1",
        location="louke/v014/x.py:10",
        severity=severity,
        impact="test impact",
        required_fix="fix it",
        category=route,
        route=route,
    )


def _valid_waiver() -> WaiverDecision:
    return WaiverDecision(
        finding_id="F-001",
        candidate_id="cand-1",
        actor="security-officer",
        reason="residual risk accepted",
        scope="louke/v014/x.py",
        issue_id=42,
        expires_at="2026-12-31",
        policy_digest="sha256:policy",
    )


def _valid_skip() -> PolicySkip:
    return PolicySkip(
        scanner="sast",
        reason="not applicable",
        scope="docs/",
        issue_id=42,
        owner="keeper",
        expires_at="2026-12-31",
        policy_digest="sha256:policy",
    )


# ---------------------------------------------------------------------------
# route_finding
# ---------------------------------------------------------------------------


@pytest.mark.real_module
def test_route_finding_implementation_to_devon():
    """AC-FR2000-01: implementation vulnerability -> Devon (not Human)."""
    decision = route_finding(_finding("implementation"))
    assert isinstance(decision, RouteDecision)
    assert decision.target == "Devon"
    assert decision.requires_human is False
    assert decision.requires_full_rerun is True


@pytest.mark.real_module
def test_route_finding_security_test_to_shield():
    """AC-FR2000-01: security test gap -> Shield."""
    decision = route_finding(_finding("security_test"))
    assert decision.target == "Shield"


@pytest.mark.real_module
def test_route_finding_design_to_m_design():
    """AC-FR2000-01: architecture boundary error -> M-DESIGN (no Human)."""
    decision = route_finding(_finding("design"))
    assert decision.target == "M-DESIGN"
    assert decision.requires_human is False


@pytest.mark.real_module
def test_route_finding_requirement_to_m_spec_acc_via_human():
    """AC-FR2000-01: permission/data requirement gap -> M-SPEC/M-ACC via Human."""
    decision = route_finding(_finding("requirement"))
    assert decision.target == "M-SPEC/M-ACC"
    assert decision.requires_human is True


@pytest.mark.real_module
def test_route_finding_rejects_unknown_route():
    """AC-FR2000-01: unknown route -> SEC_FINDING_ROUTE_INVALID."""
    with pytest.raises(FindingRouteError) as exc:
        route_finding(_finding("mystery"))
    assert exc.value.code == "SEC_FINDING_ROUTE_INVALID"


# ---------------------------------------------------------------------------
# evaluate_waiver
# ---------------------------------------------------------------------------


@pytest.mark.real_module
def test_waiver_allowed_for_medium_severity_with_full_metadata():
    """AC-FR2000-01: medium severity + full policy metadata -> allowed."""
    result = evaluate_waiver(
        _finding("implementation", "medium"), waiver=_valid_waiver()
    )
    assert isinstance(result, WaiverEvaluation)
    assert result.allowed is True


@pytest.mark.real_module
def test_waiver_forbidden_for_critical_severity():
    """AC-FR2000-01: critical severity -> SEC_WAIVER_FORBIDDEN (no waiver)."""
    result = evaluate_waiver(
        _finding("implementation", "critical"), waiver=_valid_waiver()
    )
    assert result.allowed is False
    assert result.reason_code == "SEC_WAIVER_FORBIDDEN"


@pytest.mark.real_module
def test_waiver_forbidden_for_high_severity():
    """AC-FR2000-01: high severity -> SEC_WAIVER_FORBIDDEN."""
    result = evaluate_waiver(_finding("implementation", "high"), waiver=_valid_waiver())
    assert result.allowed is False
    assert result.reason_code == "SEC_WAIVER_FORBIDDEN"


@pytest.mark.real_module
def test_waiver_invalid_when_metadata_missing():
    """AC-FR2000-01: missing policy metadata -> SEC_WAIVER_INVALID."""
    result = evaluate_waiver(_finding("implementation", "low"), waiver=None)
    assert result.allowed is False
    assert result.reason_code == "SEC_WAIVER_INVALID"

    # Missing policy_digest
    bad_waiver = WaiverDecision(
        finding_id="F-001",
        candidate_id="cand-1",
        actor="x",
        reason="x",
        scope="x",
        issue_id=42,
        expires_at="2026-12-31",
        policy_digest="",  # missing
    )
    result2 = evaluate_waiver(_finding("implementation", "low"), waiver=bad_waiver)
    assert result2.allowed is False
    assert result2.reason_code == "SEC_WAIVER_INVALID"


# ---------------------------------------------------------------------------
# validate_skip
# ---------------------------------------------------------------------------


@pytest.mark.real_module
def test_validate_skip_accepts_non_sensitive_boundary_with_full_metadata():
    """AC-FR2000-01: non-sensitive boundary + full policy metadata -> OK."""
    validate_skip(_valid_skip(), sensitive_boundary=False)  # no raise


@pytest.mark.real_module
def test_validate_skip_rejects_sensitive_boundary():
    """AC-FR2000-01: sensitive boundary change -> SEC_SKIP_FORBIDDEN;
    ordinary rules cannot silently skip."""
    with pytest.raises(FindingRouteError) as exc:
        validate_skip(_valid_skip(), sensitive_boundary=True)
    assert exc.value.code == "SEC_SKIP_FORBIDDEN"


@pytest.mark.real_module
def test_validate_skip_rejects_missing_policy_metadata():
    """AC-FR2000-01: skip without policy metadata -> SEC_SKIP_INVALID."""
    bad_skip = PolicySkip(
        scanner="sast",
        reason="x",
        scope="x",
        issue_id=0,  # missing
        owner="x",
        expires_at="2026-12-31",
        policy_digest="sha256:p",
    )
    with pytest.raises(FindingRouteError) as exc:
        validate_skip(bad_skip, sensitive_boundary=False)
    assert exc.value.code == "SEC_SKIP_INVALID"


@pytest.mark.real_module
def test_error_codes_set_covers_all_documented_codes():
    """AC-FR2000-01: ERROR_CODES includes all codes from interfaces.md §11."""
    expected = {
        "SEC_FINDING_ROUTE_INVALID",
        "SEC_WAIVER_FORBIDDEN",
        "SEC_WAIVER_INVALID",
        "SEC_SKIP_FORBIDDEN",
        "SEC_SKIP_INVALID",
    }
    actual = set(ERROR_CODES)
    missing = expected - actual
    assert not missing, f"ERROR_CODES missing: {missing}"
