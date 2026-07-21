"""E2E journey: hotfix flow (bug_fix variant).

Covers AC IDs:
- AC-FR2500-01 (Bug fix / hotfix variant)

NORMAL PATH: approved deviation -> quick_rgr -> isolated fix branch ->
reuse full RGR/M-TEST/M-VERIFY/release closure.
"""
# AC-FR2500-01

from __future__ import annotations

import pytest

pytestmark = pytest.mark.v014_003_e2e


def test_hotfix_quick_rgr_normal_path():
    """J-HOTFIX: implementation-deviation -> quick_rgr plan in isolated branch."""
    from louke.v014.fr2500_bug_fix_variant import (
        HotfixVariant,
        classify_hotfix,
        plan_hotfix,
    )

    # 1. Classify: implementation deviation -> quick_rgr
    decision = classify_hotfix(
        deviation_kind="implementation-deviation",
        source_contract="sha256:spec-v0.14.0",
        issue_id=999,
        source_version="0.14.0",
        reproduction_digest="sha256:repro",
    )
    assert decision.variant == HotfixVariant.QUICK_RGR

    # 2. Plan: isolated branch + worktree, reuses all required phases
    plan = plan_hotfix(
        deviation_kind="implementation-deviation",
        source_contract="sha256:spec-v0.14.0",
        issue_id=999,
        source_version="0.14.0",
        reproduction_digest="sha256:repro",
        impact="low",
        active_releases=("releases/0.13.0",),
    )
    assert plan.variant == HotfixVariant.QUICK_RGR
    assert plan.branch == "fix/999"
    assert "fix-999-0.14.0" in plan.worktree_namespace
    # Reuses all required phases (RGR + M-TEST + M-VERIFY + CI + review + release)
    expected_phases = {
        "red",
        "green",
        "refactor",
        "m-test",
        "m-verify",
        "required-ci",
        "independent-review",
        "release",
        "publish",
        "milestone",
    }
    assert set(plan.required_phases) == expected_phases
    # Sync targets include main + active releases
    assert "main" in plan.sync_targets
    assert "releases/0.13.0" in plan.sync_targets
    assert plan.sync_conflict is False  # no duplicate releases


def test_hotfix_design_required_for_design_impact():
    """J-HOTFIX variant: design impact -> design_required variant."""
    from louke.v014.fr2500_bug_fix_variant import (
        HotfixVariant,
        plan_hotfix,
    )

    plan = plan_hotfix(
        deviation_kind="implementation-deviation",
        source_contract="sha256:spec-v0.14.0",
        issue_id=999,
        source_version="0.14.0",
        reproduction_digest="sha256:repro",
        impact="design",
    )
    assert plan.variant == HotfixVariant.DESIGN_REQUIRED
