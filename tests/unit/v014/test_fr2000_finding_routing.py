"""AC-FR2000-01: Security finding routing & policy skip.

Implementation vulnerabilities return to Devon; security test gaps return
to Shield; architecture boundary errors return to M-DESIGN; permission/
data consequence requirement gaps return via Human to M-SPEC/M-ACC.
Technical fixes are NOT punted to Human.  After fixes, affected
implementation/tests, full M-VERIFY and Judge are re-run.  Only current
policy-explicitly-allowed non-blocking findings may record residual risk;
critical/high or policy-forbidden items cannot be waived.  Legitimate
deep-audit skip must bind policy digest + scope; sensitive boundary
changes may NOT be silently skipped by ordinary rules.
"""

from __future__ import annotations

import pytest

from louke.v014.fr2000_finding_routing import (
    FindingRouteError,
    PolicySkip,
    SecurityFinding,
    WaiverDecision,
    evaluate_waiver,
    route_finding,
    validate_skip,
)

_CAND = "cand:abc"
_POLICY = "sha256:" + "p" * 64


def _finding(
    *,
    severity: str = "medium",
    route: str = "implementation",
    category: str = "implementation",
) -> SecurityFinding:
    return SecurityFinding(
        finding_id="f-1",
        candidate_id=_CAND,
        location="louke/v014/x.py:42",
        severity=severity,
        impact="X",
        required_fix="Y",
        category=category,
        route=route,
    )


def test_route_finding_returns_to_devon_for_implementation() -> None:
    """AC-FR2000-01: implementation vuln routes to Devon."""
    decision = route_finding(_finding(route="implementation"))
    assert decision.target == "Devon"
    assert decision.requires_human is False


def test_route_finding_returns_to_shield_for_security_test() -> None:
    """AC-FR2000-01: security test gap routes to Shield."""
    decision = route_finding(_finding(route="security_test"))
    assert decision.target == "Shield"


def test_route_finding_returns_to_m_design_for_design() -> None:
    """AC-FR2000-01: design gap returns to M-DESIGN (no Human)."""
    decision = route_finding(_finding(route="design"))
    assert decision.target == "M-DESIGN"
    assert decision.requires_human is False


def test_route_finding_returns_to_m_spec_via_human_for_requirement() -> None:
    """AC-FR2000-01: requirement gap returns to M-SPEC/M-ACC via Human."""
    decision = route_finding(_finding(route="requirement"))
    assert decision.target == "M-SPEC/M-ACC"
    assert decision.requires_human is True


def test_route_finding_rejects_unknown_route() -> None:
    """AC-FR2000-01: unknown route is rejected (no Human for tech attribution)."""
    with pytest.raises(FindingRouteError) as exc:
        route_finding(_finding(route="unknown"))
    assert exc.value.code == "SEC_FINDING_ROUTE_INVALID"


def test_waiver_rejects_critical_severity() -> None:
    """AC-FR2000-01: critical findings cannot be waived."""
    decision = evaluate_waiver(_finding(severity="critical"))
    assert decision.allowed is False
    assert decision.reason_code == "SEC_WAIVER_FORBIDDEN"


def test_waiver_rejects_high_severity() -> None:
    """AC-FR2000-01: high findings cannot be waived."""
    decision = evaluate_waiver(_finding(severity="high"))
    assert decision.allowed is False
    assert decision.reason_code == "SEC_WAIVER_FORBIDDEN"


def test_waiver_allows_medium_with_policy_bound_metadata() -> None:
    """AC-FR2000-01: medium finding may be waived with policy-bound metadata."""
    waiver = WaiverDecision(
        finding_id="f-1",
        candidate_id=_CAND,
        actor="human:bob",
        reason="acceptable risk",
        scope="tests/legacy/",
        issue_id=999,
        expires_at="2026-12-31",
        policy_digest=_POLICY,
    )
    decision = evaluate_waiver(_finding(severity="medium"), waiver=waiver)
    assert decision.allowed is True


def test_waiver_rejects_medium_without_policy_metadata() -> None:
    """AC-FR2000-01: medium waiver without policy metadata is rejected."""
    decision = evaluate_waiver(_finding(severity="medium"))  # no waiver metadata
    assert decision.allowed is False
    assert decision.reason_code == "SEC_WAIVER_INVALID"


def test_skip_rejects_sensitive_boundary_change() -> None:
    """AC-FR2000-01: sensitive boundary changes may not be skipped by ordinary rules."""
    skip = PolicySkip(
        scanner="secret-scan",
        reason="routine",
        scope="louke/auth/",
        issue_id=1,
        owner="Devon",
        expires_at="2026-12-31",
        policy_digest=_POLICY,
    )
    with pytest.raises(FindingRouteError) as exc:
        validate_skip(skip, sensitive_boundary=True)
    assert exc.value.code == "SEC_SKIP_FORBIDDEN"


def test_skip_accepts_policy_bound_routine() -> None:
    """AC-FR2000-01: legitimate deep-audit skip binds policy digest + scope."""
    skip = PolicySkip(
        scanner="sast",
        reason="deep-audit",
        scope="tests/fixtures/",
        issue_id=1,
        owner="Devon",
        expires_at="2026-12-31",
        policy_digest=_POLICY,
    )
    validate_skip(skip, sensitive_boundary=False)  # does not raise


def test_skip_rejects_missing_policy_metadata() -> None:
    """AC-FR2000-01: skip without policy_digest/issue/owner/scope/expiry is rejected."""
    skip = PolicySkip(
        scanner="sast",
        reason="x",
        scope="",
        issue_id=0,
        owner="",
        expires_at="",
        policy_digest="",
    )
    with pytest.raises(FindingRouteError) as exc:
        validate_skip(skip, sensitive_boundary=False)
    assert exc.value.code == "SEC_SKIP_INVALID"
