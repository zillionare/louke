"""E2E journey: security audit (program gates + Judge review).

Covers AC IDs:
- AC-FR1900-01 (Security program gates & Judge review)
- AC-FR2000-01 (Security finding routing & policy skip)

NORMAL PATH: all required scanners PASS + Judge PASS -> security gate
PASS -> enter M-RELEASE.
"""
# AC-FR1900-01, AC-FR2000-01

from __future__ import annotations

import pytest

pytestmark = pytest.mark.v014_003_e2e


def test_security_audit_normal_path():
    """J-SECURITY: 4 scanners PASS + Judge PASS -> security gate PASS."""
    from louke.runtime.security_gates import (
        JudgeVerdict,
        ProgramScanResult,
        evaluate_security_gate,
    )

    scans = [
        ProgramScanResult(
            scanner_id=s,
            status="pass",
            evidence_id=f"ev-{s}",
            tool_digest=f"sha256:{s}",
        )
        for s in ("secret-scan", "dependency-sca", "sast", "project-checks")
    ]
    judge = JudgeVerdict(
        review_id="rev-judge-001",
        candidate_id="cand-1",
        verdict="PASS",
    )
    report = evaluate_security_gate("cand-1", scans, judge)
    assert report.status == "pass"


def test_security_finding_routes_to_correct_owner():
    """J-SECURITY: 4 finding categories route to 4 owners."""
    from louke.runtime.finding_routing import (
        RouteDecision,
        SecurityFinding,
        route_finding,
    )

    routes = {
        "implementation": "Devon",
        "security_test": "Shield",
        "design": "M-DESIGN",
        "requirement": "M-SPEC/M-ACC",
    }
    for category, expected_target in routes.items():
        finding = SecurityFinding(
            finding_id=f"F-{category}",
            candidate_id="cand-1",
            location="x.py:1",
            severity="medium",
            impact="x",
            required_fix="fix",
            category=category,
            route=category,
        )
        decision = route_finding(finding)
        assert isinstance(decision, RouteDecision)
        assert decision.target == expected_target
        assert decision.requires_full_rerun is True
