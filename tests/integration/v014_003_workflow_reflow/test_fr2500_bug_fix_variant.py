"""Integration tests for FR-2500: Bug fix / hotfix variant.

AC-FR2500-01: ``bug_fix`` applies only to implementation deviation of
an already-released product against the existing approved Spec/AC; new
behaviour must go through backlog/new feature. Runtime verifies source
contract/Issue/version/reproduction, picks ``quick_rgr`` or
``design_required`` by impact, and executes in an isolated
``fix/{issue-number}`` branch + worktree. Both variants reuse RGR,
M-TEST, full historical M-VERIFY, required CI, independent review,
release/publish/milestone. After release, main and affected active
releases are synced per policy; parallel active releases must NOT
cross-write; sync conflicts enter needs_attention.

Interfaces covered (per interfaces.md):
- IF-WFR-01 (Primary ARC-01)
- IF-RGR-01 (RGR reuse, ARC-05)
- IF-CI-02 (required CI, ARC-11)
- IF-TRACE-01 (trace, ARC-16)
"""
# AC-FR2500-01

from __future__ import annotations

import pytest

from louke.runtime.bug_fix_variant import (
    ERROR_CODES,
    BugFixVariantError,
    HotfixDecision,
    HotfixPlan,
    HotfixVariant,
    classify_hotfix,
    plan_hotfix,
)


def _valid_kwargs() -> dict:
    return dict(
        deviation_kind="implementation-deviation",
        source_contract="sha256:spec-v0.14.0",
        issue_id=42,
        source_version="0.14.0",
        reproduction_digest="sha256:repro",
    )


# ---------------------------------------------------------------------------
# classify_hotfix
# ---------------------------------------------------------------------------


@pytest.mark.real_module
def test_classify_hotfix_returns_quick_rgr_for_implementation_deviation():
    """AC-FR2500-01: implementation deviation -> quick_rgr variant."""
    decision = classify_hotfix(**_valid_kwargs())
    assert isinstance(decision, HotfixDecision)
    assert decision.variant == HotfixVariant.QUICK_RGR


@pytest.mark.real_module
def test_classify_hotfix_rejects_new_behaviour():
    """AC-FR2500-01: new behaviour must go through backlog, not hotfix."""
    kw = _valid_kwargs()
    kw["deviation_kind"] = "new-behaviour"
    with pytest.raises(BugFixVariantError) as exc:
        classify_hotfix(**kw)
    assert exc.value.code == "BUGFIX_NEW_BEHAVIOUR"


@pytest.mark.real_module
def test_classify_hotfix_rejects_missing_source_contract():
    """AC-FR2500-01: missing source contract -> BUGFIX_SOURCE_CONTRACT_MISSING."""
    kw = _valid_kwargs()
    kw["source_contract"] = ""
    with pytest.raises(BugFixVariantError) as exc:
        classify_hotfix(**kw)
    assert exc.value.code == "BUGFIX_SOURCE_CONTRACT_MISSING"


@pytest.mark.real_module
def test_classify_hotfix_rejects_missing_reproduction():
    """AC-FR2500-01: missing reproduction -> BUGFIX_REPRODUCTION_MISSING."""
    kw = _valid_kwargs()
    kw["reproduction_digest"] = ""
    with pytest.raises(BugFixVariantError) as exc:
        classify_hotfix(**kw)
    assert exc.value.code == "BUGFIX_REPRODUCTION_MISSING"


# ---------------------------------------------------------------------------
# plan_hotfix
# ---------------------------------------------------------------------------


@pytest.mark.real_module
def test_plan_hotfix_creates_isolated_branch_and_worktree():
    """AC-FR2500-01: branch=fix/{issue}; worktree namespace isolated."""
    plan = plan_hotfix(impact="low", **_valid_kwargs())
    assert isinstance(plan, HotfixPlan)
    assert plan.branch == "fix/42"
    assert plan.worktree_namespace == "fix-42-0.14.0"
    assert plan.variant == HotfixVariant.QUICK_RGR


@pytest.mark.real_module
def test_plan_hotfix_design_required_for_design_impact():
    """AC-FR2500-01: design impact -> design_required variant."""
    plan = plan_hotfix(impact="design", **_valid_kwargs())
    assert plan.variant == HotfixVariant.DESIGN_REQUIRED


@pytest.mark.real_module
def test_plan_hotfix_reuses_all_required_phases():
    """AC-FR2500-01: hotfix reuses RGR, M-TEST, full M-VERIFY, required CI,
    independent review, release/publish/milestone - no shortcuts."""
    plan = plan_hotfix(impact="low", **_valid_kwargs())
    expected = {
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
    assert set(plan.required_phases) == expected


@pytest.mark.real_module
def test_plan_hotfix_includes_main_and_active_releases_as_sync_targets():
    """AC-FR2500-01: sync targets = main + active releases."""
    plan = plan_hotfix(
        impact="low",
        active_releases=("releases/0.13.0", "releases/0.14.0"),
        **_valid_kwargs(),
    )
    assert "main" in plan.sync_targets
    assert "releases/0.13.0" in plan.sync_targets
    assert "releases/0.14.0" in plan.sync_targets


@pytest.mark.real_module
def test_plan_hotfix_detects_sync_conflict_on_duplicate_active_releases():
    """AC-FR2500-01: duplicate active releases -> sync_conflict; needs_attention."""
    plan = plan_hotfix(
        impact="low",
        active_releases=("releases/0.14.0", "releases/0.14.0"),  # duplicate
        **_valid_kwargs(),
    )
    assert plan.sync_conflict is True


@pytest.mark.real_module
def test_plan_hotfix_no_conflict_with_distinct_active_releases():
    """AC-FR2500-01: distinct active releases -> no sync_conflict."""
    plan = plan_hotfix(
        impact="low",
        active_releases=("releases/0.13.0", "releases/0.14.0"),
        **_valid_kwargs(),
    )
    assert plan.sync_conflict is False


@pytest.mark.real_module
def test_error_codes_set_covers_all_documented_codes():
    """AC-FR2500-01: ERROR_CODES includes all codes from interfaces.md (§4 row)."""
    expected = {
        "BUGFIX_NEW_BEHAVIOUR",
        "BUGFIX_SOURCE_CONTRACT_MISSING",
        "BUGFIX_REPRODUCTION_MISSING",
        "BUGFIX_SYNC_CONFLICT",
    }
    actual = set(ERROR_CODES)
    missing = expected - actual
    assert not missing, f"ERROR_CODES missing: {missing}"
