"""FR-2101: completable new_feature and bug_fix workflows.

AC references:
- AC-FR2101-01: new_feature workflow covers requirements author/review,
  requirements approval, test-plan, architecture/interfaces, M-LOCK,
  traceable implementation, code/authoritative tests, E2E, policy release,
  human milestone close and history.
- AC-FR2101-02: bug_fix workflow validates linked spec/AC, skips new
  requirements, covers issue/source-contract validation, reproduction,
  M-LOCK, Devon R-G-R, review/regression, policy release and history.
- AC-FR2101-03: hotfix with no public/data/security/cross-module impact uses
  quick_rgr and marks design skipped; high-impact conditions require design.
- AC-FR2101-04: when impact cannot be determined by rules, Maestro only sees
  quick_rgr/design_required candidates with reasoning; Maestro output does not
  change run state.
- AC-FR2101-05: force/waiver/resume/agent-skip cannot bypass applicable gates;
  hotfix inherits old requirements approval only via source-contract validation;
  M-LOCK still requires human approve matching current artifacts.
- AC-FR2101-06: completion is rejected until all required artifacts, reviews,
  gates, implementation evidence, authoritative tests, policy and milestone
  close are satisfied; only then run becomes completed/history.
"""

from __future__ import annotations

import pytest

from louke.runtime.workflow_templates import (
    CompletionBlockedError,
    HotfixImpact,
    SourceContractValidation,
    WorkflowTemplateRegistry,
    WorkflowType,
)


# -- AC-FR2101-01 -------------------------------------------------------------


def test_ac_fr2101_01_new_feature_workflow_includes_required_nodes():
    """AC-FR2101-01: new_feature workflow includes all required phases."""
    registry = WorkflowTemplateRegistry()
    wf = registry.get(WorkflowType.NEW_FEATURE)

    required = {
        "requirements_author",
        "requirements_review",
        "requirements_approval",
        "test_plan_author",
        "test_plan_review",
        "architecture_author",
        "interfaces_author",
        "architecture_review",
        "interfaces_review",
        "m_lock",
        "traceable_implementation",
        "code",
        "authoritative_tests",
        "e2e",
        "policy_release",
        "human_milestone_close",
        "history",
    }
    assert required.issubset(wf.nodes)


def test_ac_fr2101_01_preflight_outside_business_graph():
    """AC-FR2101-01: programmatic foundation preflight is outside business graph."""
    registry = WorkflowTemplateRegistry()
    wf = registry.get(WorkflowType.NEW_FEATURE)

    assert "foundation_preflight" in wf.preflight_steps
    assert "scout_warden" not in wf.nodes


# -- AC-FR2101-02 -------------------------------------------------------------


def test_ac_fr2101_02_bug_fix_workflow_includes_required_nodes():
    """AC-FR2101-02: bug_fix workflow covers issue validation, reproduction,
    M-LOCK, R-G-R, regression and release."""
    registry = WorkflowTemplateRegistry()
    wf = registry.get(WorkflowType.BUG_FIX)

    required = {
        "issue_source_contract_validation",
        "failure_reproduction",
        "m_lock",
        "devon_rgr",
        "review",
        "authoritative_regression",
        "policy_release_confirmation",
        "history",
    }
    assert required.issubset(wf.nodes)
    assert "requirements_author" not in wf.nodes


def test_ac_fr2101_02_bug_fix_requires_approved_spec():
    """AC-FR2101-02: bug_fix creation requires linked approved spec/AC."""
    validator = SourceContractValidation()
    assert validator.validate(spec_status="approved", has_issue_link=True) is True
    assert validator.validate(spec_status="draft", has_issue_link=True) is False


# -- AC-FR2101-03 -------------------------------------------------------------


def test_ac_fr2101_03_low_impact_hotfix_uses_quick_rgr():
    """AC-FR2101-03: low-impact hotfix enters quick_rgr and skips design."""
    registry = WorkflowTemplateRegistry()
    impact = HotfixImpact(
        public_interface=False,
        data_migration=False,
        security_boundary=False,
        cross_module_design=False,
    )
    wf = registry.resolve_hotfix(impact)

    assert "quick_rgr" in wf.nodes
    assert "design_skipped" in wf.nodes
    assert "architecture_author" not in wf.nodes


def test_ac_fr2101_03_high_impact_hotfix_requires_design():
    """AC-FR2101-03: high-impact hotfix requires test-plan/architecture/ reviews."""
    registry = WorkflowTemplateRegistry()
    impact = HotfixImpact(
        public_interface=True,
        data_migration=False,
        security_boundary=False,
        cross_module_design=False,
    )
    wf = registry.resolve_hotfix(impact)

    assert "test_plan_author" in wf.nodes
    assert "architecture_author" in wf.nodes
    assert "m_lock" in wf.nodes


# -- AC-FR2101-04 -------------------------------------------------------------


def test_ac_fr2101_04_maestro_only_sees_allowed_candidates():
    """AC-FR2101-04: Maestro only sees quick_rgr/design_required candidates."""
    registry = WorkflowTemplateRegistry()
    candidates = registry.hotfix_decision_candidates()

    assert set(candidates) == {"quick_rgr", "design_required"}


# -- AC-FR2101-05 -------------------------------------------------------------


def test_ac_fr2101_05_force_waiver_cannot_bypass_gate():
    """AC-FR2101-05: force/waiver/resume cannot bypass applicable gates."""
    registry = WorkflowTemplateRegistry()
    wf = registry.get(WorkflowType.NEW_FEATURE)

    with pytest.raises(PermissionError):
        wf.bypass_gate("m_lock", actor="agent", reason="just do it")


def test_ac_fr2101_05_hotfix_inherits_approval_via_source_contract():
    """AC-FR2101-05: hotfix inherits old requirements approval only after
    source-contract validation."""
    validator = SourceContractValidation()
    assert (
        validator.can_inherit_requirements_approval(
            spec_status="approved",
            source_contract_digest_matches=True,
        )
        is True
    )
    assert (
        validator.can_inherit_requirements_approval(
            spec_status="approved",
            source_contract_digest_matches=False,
        )
        is False
    )


# -- AC-FR2101-06 -------------------------------------------------------------


def test_ac_fr2101_06_completion_blocked_until_all_evidence_present():
    """AC-FR2101-06: completion rejected until all required evidence present."""
    registry = WorkflowTemplateRegistry()
    wf = registry.get(WorkflowType.NEW_FEATURE)

    incomplete = {"requirements_approval": False, "m_lock": False}
    with pytest.raises(CompletionBlockedError):
        wf.complete(evidence=incomplete)

    complete = {node: True for node in wf.required_completion_nodes}
    result = wf.complete(evidence=complete)
    assert result.terminal_state == "completed"
    assert result.archived_to_history is True
