"""AC-FR2500-01: Bug fix / hotfix variant.

``bug_fix`` applies only to implementation deviation of an already-released
product against the existing approved Spec/AC; new behaviour must go through
backlog/new feature.  Runtime verifies source contract/Issue/version/
reproduction, picks ``quick_rgr`` or ``design_required`` by impact, and
executes in isolated ``fix/{issue-number}`` branch + worktree.  Both
variants reuse RGR, M-TEST, full historical M-VERIFY, required CI,
independent review, release/publish/milestone.  After release, main and
affected active releases are synced per policy.  Parallel active
releases must NOT cross-write; sync conflicts enter ``needs_attention``.
"""

from __future__ import annotations

import pytest

from louke.v014.fr2500_bug_fix_variant import (
    BugFixVariantError,
    HotfixPlan,
    HotfixVariant,
    classify_hotfix,
    plan_hotfix,
)

_ISSUE = 999
_VERSION = "0.14.1"
_REPRO = "sha256:" + "r" * 64
_CONTRACT = "sha256:" + "c" * 64


def test_classify_rejects_new_behaviour_as_hotfix() -> None:
    """AC-FR2500-01: actual new behaviour does not qualify as bug_fix."""
    with pytest.raises(BugFixVariantError) as exc:
        classify_hotfix(
            deviation_kind="new-behaviour",
            source_contract=_CONTRACT,
            issue_id=_ISSUE,
            source_version=_VERSION,
            reproduction_digest=_REPRO,
        )
    assert exc.value.code == "BUGFIX_NEW_BEHAVIOUR"


def test_classify_accepts_implementation_deviation() -> None:
    """AC-FR2500-01: implementation deviation qualifies for bug_fix."""
    decision = classify_hotfix(
        deviation_kind="implementation-deviation",
        source_contract=_CONTRACT,
        issue_id=_ISSUE,
        source_version=_VERSION,
        reproduction_digest=_REPRO,
    )
    assert decision.variant in ("quick_rgr", "design_required")


def test_classify_rejects_missing_reproduction() -> None:
    """AC-FR2500-01: missing reproduction blocks hotfix."""
    with pytest.raises(BugFixVariantError) as exc:
        classify_hotfix(
            deviation_kind="implementation-deviation",
            source_contract=_CONTRACT,
            issue_id=_ISSUE,
            source_version=_VERSION,
            reproduction_digest="",
        )
    assert exc.value.code == "BUGFIX_REPRODUCTION_MISSING"


def test_plan_hotfix_creates_isolated_branch_and_worktree() -> None:
    """AC-FR2500-01: hotfix runs in fix/{issue} branch + isolated worktree."""
    plan = plan_hotfix(
        deviation_kind="implementation-deviation",
        source_contract=_CONTRACT,
        issue_id=_ISSUE,
        source_version=_VERSION,
        reproduction_digest=_REPRO,
        impact="low",
    )
    assert isinstance(plan, HotfixPlan)
    assert plan.branch == f"fix/{_ISSUE}"
    assert plan.worktree_namespace.startswith(f"fix-{_ISSUE}-")


def test_plan_hotfix_chooses_quick_rgr_for_low_impact() -> None:
    """AC-FR2500-01: low impact + impl deviation -> quick_rgr."""
    plan = plan_hotfix(
        deviation_kind="implementation-deviation",
        source_contract=_CONTRACT,
        issue_id=_ISSUE,
        source_version=_VERSION,
        reproduction_digest=_REPRO,
        impact="low",
    )
    assert plan.variant == HotfixVariant.QUICK_RGR


def test_plan_hotfix_chooses_design_required_for_design_impact() -> None:
    """AC-FR2500-01: design/architecture impact -> design_required."""
    plan = plan_hotfix(
        deviation_kind="implementation-deviation",
        source_contract=_CONTRACT,
        issue_id=_ISSUE,
        source_version=_VERSION,
        reproduction_digest=_REPRO,
        impact="design",
    )
    assert plan.variant == HotfixVariant.DESIGN_REQUIRED


def test_plan_hotfix_reuses_full_rgr_test_verify_ci_release_pipeline() -> None:
    """AC-FR2500-01: hotfix reuses RGR/M-TEST/full M-VERIFY/required CI/release/milestone."""
    plan = plan_hotfix(
        deviation_kind="implementation-deviation",
        source_contract=_CONTRACT,
        issue_id=_ISSUE,
        source_version=_VERSION,
        reproduction_digest=_REPRO,
        impact="low",
    )
    required = set(plan.required_phases)
    assert {
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
    } <= required


def test_plan_hotfix_rejects_missing_source_contract() -> None:
    """AC-FR2500-01: missing source contract blocks hotfix."""
    with pytest.raises(BugFixVariantError) as exc:
        plan_hotfix(
            deviation_kind="implementation-deviation",
            source_contract="",
            issue_id=_ISSUE,
            source_version=_VERSION,
            reproduction_digest=_REPRO,
            impact="low",
        )
    assert exc.value.code == "BUGFIX_SOURCE_CONTRACT_MISSING"


def test_plan_hotfix_syncs_main_and_active_releases_after_release() -> None:
    """AC-FR2500-01: after release, sync main + affected active releases per policy."""
    plan = plan_hotfix(
        deviation_kind="implementation-deviation",
        source_contract=_CONTRACT,
        issue_id=_ISSUE,
        source_version=_VERSION,
        reproduction_digest=_REPRO,
        impact="low",
        active_releases=("0.14.x", "0.15.x"),
    )
    assert "main" in plan.sync_targets
    assert "0.14.x" in plan.sync_targets
    assert "0.15.x" in plan.sync_targets


def test_plan_hotfix_sync_conflict_enters_needs_attention() -> None:
    """AC-FR2500-01: parallel active releases must not cross-write; conflicts -> needs_attention."""
    plan = plan_hotfix(
        deviation_kind="implementation-deviation",
        source_contract=_CONTRACT,
        issue_id=_ISSUE,
        source_version=_VERSION,
        reproduction_digest=_REPRO,
        impact="low",
        active_releases=("0.14.x", "0.14.x"),  # duplicate -> conflict
    )
    assert plan.sync_conflict is True
