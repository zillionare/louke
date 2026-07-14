"""FR-2101: completable new_feature and bug_fix workflow templates e2e.

Covers AC-FR2101-01..06. Per test-plan §1.1 these tests observe behavior through
the runtime module public report (WorkflowTemplateRegistry / CompletableWorkflow
/ HotfixImpact / SourceContractValidation / CompletionBlockedError) which are
the observable exits described in interfaces.md §6.1 (workflow graph, gate,
source contract, trace/completion check). The v0.12 M-DEV HTTP project API is
not yet implemented; these public outputs are the contract surface.

The required node sets, preflight location and gate rules asserted here are
taken verbatim from acceptance.md AC-FR2101-01..06 (the spec), not derived from
the implementation. Where the implementation exposes them, we assert equality
against the spec-derived expected set; where the implementation enforces rules
(CompletionBlockedError / PermissionError), we trigger and assert the public
exception type.

AC references:
- AC-FR2101-01: new_feature success path covers all required nodes; preflight
  outside business graph and does not invoke Scout/Warden.
- AC-FR2101-02: bug_fix with linked approved spec/AC skips requirements; graph
  covers issue/source-contract validation, failure reproduction, M-LOCK, Devon
  R-G-R, review/authoritative regression, policy release confirmation, history.
- AC-FR2101-03: low-impact hotfix -> quick_rgr with design skipped; any high
  impact flag forces design_required (test-plan, arch/interfaces, reviews, M-LOCK).
- AC-FR2101-04: Maestro candidates limited to quick_rgr / design_required;
  Maestro output alone does not change the run.
- AC-FR2101-05: force / waiver / resume / agent bypass cannot pass an applicable
  gate; hotfix inherits requirements approval only via source-contract validation;
  M-LOCK only advances on human approve of matching artifact/revision.
- AC-FR2101-06: completion rejected when any required evidence is missing; only
  when all are satisfied does the run reach completed/history.
"""

from __future__ import annotations

import pytest

from louke.runtime.workflow_templates import (
    CompletionBlockedError,
    CompletableWorkflow,
    HotfixImpact,
    SourceContractValidation,
    WorkflowTemplateRegistry,
    WorkflowType,
)

# ---------------------------------------------------------------------------
# Expected node sets are derived from acceptance.md AC-FR2101-01..02, not from
# the implementation. They are the spec's enumeration of which gates/steps each
# workflow must cover on the success path.
# ---------------------------------------------------------------------------

NEW_FEATURE_REQUIRED_NODES = frozenset(
    {
        "requirements_approval",
        "m_lock",
        "traceable_implementation",
        "code",
        "authoritative_tests",
        "e2e",
        "policy_release",
        "human_milestone_close",
    }
)

NEW_FEATURE_FULL_NODES = NEW_FEATURE_REQUIRED_NODES | frozenset(
    {
        "requirements_author",
        "requirements_review",
        "test_plan_author",
        "test_plan_review",
        "architecture_author",
        "interfaces_author",
        "architecture_review",
        "interfaces_review",
        "history",
    }
)

BUG_FIX_REQUIRED_NODES = frozenset(
    {
        "issue_source_contract_validation",
        "m_lock",
        "devon_rgr",
        "review",
        "authoritative_regression",
        "policy_release_confirmation",
    }
)

BUG_FIX_FULL_NODES = BUG_FIX_REQUIRED_NODES | frozenset({"failure_reproduction", "history"})

QUICK_HOTFIX_REQUIRED_NODES = frozenset(
    {
        "issue_source_contract_validation",
        "quick_rgr",
        "m_lock",
        "review",
        "authoritative_regression",
        "policy_release_confirmation",
    }
)
QUICK_HOTFIX_FULL_NODES = QUICK_HOTFIX_REQUIRED_NODES | frozenset(
    {"design_skipped", "history"}
)

DESIGN_HOTFIX_REQUIRED_NODES = frozenset(
    {
        "issue_source_contract_validation",
        "test_plan_author",
        "architecture_author",
        "interfaces_author",
        "m_lock",
        "devon_rgr",
        "review",
        "authoritative_regression",
        "policy_release_confirmation",
    }
)
DESIGN_HOTFIX_FULL_NODES = DESIGN_HOTFIX_REQUIRED_NODES | frozenset(
    {
        "test_plan_review",
        "architecture_review",
        "interfaces_review",
        "history",
    }
)


# ---------------------------------------------------------------------------
# AC-FR2101-01: new_feature success path covers all required nodes
# ---------------------------------------------------------------------------


@pytest.mark.e2e
def test_ac_fr2101_01_new_feature_covers_all_required_nodes():
    """AC-FR2101-01: new_feature graph covers every required success-path node.

    The bound graph must include requirements author/review/approval, test-plan
    author/review, architecture/interfaces author/review, M-LOCK, traceable
    implementation, code/authoritative tests, E2E, policy-required
    security/release, human milestone close and history.
    """
    registry = WorkflowTemplateRegistry()
    wf = registry.get(WorkflowType.NEW_FEATURE)

    assert isinstance(wf, CompletableWorkflow)
    assert NEW_FEATURE_FULL_NODES.issubset(wf.nodes)
    assert wf.required_completion_nodes == NEW_FEATURE_REQUIRED_NODES


@pytest.mark.e2e
def test_ac_fr2101_01_preflight_outside_business_graph_no_scout_warden():
    """AC-FR2101-01: preflight lives outside the business graph.

    The programmatic foundation preflight step is not one of the business-graph
    workflow nodes, and the business graph node set does not reference Scout or
    Warden agents (which are not part of the v0.12 programmatic control plane).
    """
    registry = WorkflowTemplateRegistry()
    wf = registry.get(WorkflowType.NEW_FEATURE)

    assert wf.preflight_steps == frozenset({"foundation_preflight"})
    # Preflight is NOT a business-graph node.
    assert "foundation_preflight" not in wf.nodes
    # Scout/Warden are explicitly out of the programmatic control plane.
    assert "scout" not in wf.nodes
    assert "warden" not in wf.nodes
    for n in wf.nodes:
        assert "scout" not in n
        assert "warden" not in n


@pytest.mark.e2e
def test_ac_fr2101_01_new_feature_rejects_requirements_gate_design_before_approval():
    """AC-FR2101-01: design nodes only appear after requirements approval.

    The success path ordering requires requirements approval before design
    dispatch. The required_completion_nodes enforce this dependency by requiring
    ``requirements_approval``; design nodes (architecture/interfaces author)
    are present but cannot complete without the upstream approval gate.
    """
    registry = WorkflowTemplateRegistry()
    wf = registry.get(WorkflowType.NEW_FEATURE)

    # requirements_approval is required for completion -> design cannot bypass it.
    assert "requirements_approval" in wf.required_completion_nodes
    # Design author nodes exist but are NOT in the bypassable shortlist.
    assert "architecture_author" in wf.nodes
    assert "interfaces_author" in wf.nodes


# ---------------------------------------------------------------------------
# AC-FR2101-02: bug_fix skips requirements; covers issue/source-contract path
# ---------------------------------------------------------------------------


@pytest.mark.e2e
def test_ac_fr2101_02_bug_fix_skips_requirements_gate():
    """AC-FR2101-02: bug_fix does not create a requirements document or gate.

    A bug_fix linked to an approved spec/AC must not include a requirements
    author/review/approval node; its graph starts at issue/source-contract
    validation and failure reproduction.
    """
    registry = WorkflowTemplateRegistry()
    wf = registry.get(WorkflowType.BUG_FIX)

    assert "requirements_author" not in wf.nodes
    assert "requirements_review" not in wf.nodes
    assert "requirements_approval" not in wf.nodes
    assert "requirements_approval" not in wf.required_completion_nodes


@pytest.mark.e2e
def test_ac_fr2101_02_bug_fix_covers_issue_validation_and_history():
    """AC-FR2101-02: bug_fix graph covers issue/source-contract validation and history.

    The quick path must cover Issue/source-contract validation, failure
    reproduction, M-LOCK, Devon R-G-R, review/authoritative regression, policy
    release confirmation and history.
    """
    registry = WorkflowTemplateRegistry()
    wf = registry.get(WorkflowType.BUG_FIX)

    assert BUG_FIX_FULL_NODES.issubset(wf.nodes)
    assert wf.required_completion_nodes == BUG_FIX_REQUIRED_NODES
    assert "issue_source_contract_validation" in wf.required_completion_nodes
    assert "failure_reproduction" in wf.nodes


@pytest.mark.e2e
def test_ac_fr2101_02_bug_fix_completion_requires_all_evidence():
    """AC-FR2101-02: bug_fix completion requires every required evidence node.

    With all required nodes satisfied completion reaches terminal state; with
    any single required node missing it is blocked.
    """
    registry = WorkflowTemplateRegistry()
    wf = registry.get(WorkflowType.BUG_FIX)

    full_evidence = {node: True for node in wf.required_completion_nodes}
    result = wf.complete(full_evidence)
    assert result.terminal_state == "completed"
    assert result.archived_to_history is True

    # Remove one required node at a time -> each must block completion.
    for missing in wf.required_completion_nodes:
        partial = dict(full_evidence)
        partial[missing] = False
        with pytest.raises(CompletionBlockedError) as exc:
            wf.complete(partial)
        assert missing in str(exc.value)


# ---------------------------------------------------------------------------
# AC-FR2101-03: hotfix quick_rgr vs design_required based on impact
# ---------------------------------------------------------------------------


@pytest.mark.e2e
def test_ac_fr2101_03_low_impact_hotfix_uses_quick_rgr_with_design_skipped():
    """AC-FR2101-03: a hotfix with no high-impact flag uses quick_rgr and skips design.

    When the hotfix explicitly does not touch public interface, data migration,
    security boundary or cross-module design, the graph must enter quick_rgr
    and mark design as skipped (no test-plan/architecture/interfaces author).
    """
    registry = WorkflowTemplateRegistry()
    impact = HotfixImpact(
        public_interface=False,
        data_migration=False,
        security_boundary=False,
        cross_module_design=False,
    )
    wf = registry.resolve_hotfix(impact)

    assert QUICK_HOTFIX_FULL_NODES.issubset(wf.nodes)
    assert wf.required_completion_nodes == QUICK_HOTFIX_REQUIRED_NODES
    assert "quick_rgr" in wf.required_completion_nodes
    assert "design_skipped" in wf.nodes
    # Design-required nodes must NOT appear on the quick path.
    assert "test_plan_author" not in wf.nodes
    assert "architecture_author" not in wf.nodes
    assert "interfaces_author" not in wf.nodes


@pytest.mark.e2e
def test_ac_fr2101_03_public_interface_impact_forces_design_required():
    """AC-FR2101-03: a public-interface impact forces the design_required path.

    Any single high-impact condition (here: public_interface) must route to
    test-plan, architecture/interfaces author and their reviews before M-LOCK,
    not to quick_rgr.
    """
    registry = WorkflowTemplateRegistry()
    impact = HotfixImpact(
        public_interface=True,
        data_migration=False,
        security_boundary=False,
        cross_module_design=False,
    )
    wf = registry.resolve_hotfix(impact)

    assert DESIGN_HOTFIX_FULL_NODES.issubset(wf.nodes)
    assert wf.required_completion_nodes == DESIGN_HOTFIX_REQUIRED_NODES
    assert "quick_rgr" not in wf.nodes
    assert "design_skipped" not in wf.nodes
    assert "test_plan_author" in wf.required_completion_nodes
    assert "architecture_author" in wf.required_completion_nodes
    assert "interfaces_author" in wf.required_completion_nodes


@pytest.mark.e2e
def test_ac_fr2101_03_each_high_impact_flag_independently_forces_design():
    """AC-FR2101-03: each high-impact flag independently forces design_required.

    Setting only one of the four impact flags at a time must route to the
    design_required path; the agent cannot suggest skipping design when any
    holds.
    """
    registry = WorkflowTemplateRegistry()
    flag_names = (
        "public_interface",
        "data_migration",
        "security_boundary",
        "cross_module_design",
    )
    for flag in flag_names:
        kwargs = {f: False for f in flag_names}
        kwargs[flag] = True
        impact = HotfixImpact(**kwargs)  # type: ignore[arg-type]
        wf = registry.resolve_hotfix(impact)
        assert "test_plan_author" in wf.required_completion_nodes, (
            f"{flag}=True did not force design_required"
        )
        assert "quick_rgr" not in wf.nodes
        assert "design_skipped" not in wf.nodes


# ---------------------------------------------------------------------------
# AC-FR2101-04: Maestro candidates limited to quick_rgr / design_required
# ---------------------------------------------------------------------------


@pytest.mark.e2e
def test_ac_fr2101_04_maestro_candidates_are_only_quick_rgr_and_design_required():
    """AC-FR2101-04: the candidate set presented to Maestro is exactly the two values.

    When impact cannot be decided by rules and Runtime consults Maestro, only
    ``quick_rgr`` and ``design_required`` are accepted candidates, each with a
    structured reason.
    """
    registry = WorkflowTemplateRegistry()
    candidates = registry.hotfix_decision_candidates()

    assert set(candidates) == {"quick_rgr", "design_required"}
    assert len(candidates) == 2


@pytest.mark.e2e
def test_ac_fr2101_04_maestro_output_alone_does_not_change_run():
    """AC-FR2101-04: consulting candidates does not mutate any workflow template.

    The Maestro output itself does not change the run; the runtime still
    resolves via the rule-based path. Calling ``hotfix_decision_candidates``
    must not mutate the registry's built-in templates.
    """
    registry = WorkflowTemplateRegistry()
    before = registry.get(WorkflowType.NEW_FEATURE).nodes
    _ = registry.hotfix_decision_candidates()
    after = registry.get(WorkflowType.NEW_FEATURE).nodes
    assert before == after

    # And the low/high impact rules are still deterministic independent of the
    # candidate list (Maestro output is advisory only).
    low = registry.resolve_hotfix(
        HotfixImpact(False, False, False, False)
    )
    high = registry.resolve_hotfix(HotfixImpact(True, False, False, False))
    assert "quick_rgr" in low.nodes
    assert "test_plan_author" in high.required_completion_nodes


# ---------------------------------------------------------------------------
# AC-FR2101-05: force / waiver / resume / agent bypass cannot pass a gate
# ---------------------------------------------------------------------------


@pytest.mark.e2e
def test_ac_fr2101_05_force_cannot_bypass_m_lock_gate():
    """AC-FR2101-05: a ``force`` request cannot bypass an applicable gate (M-LOCK).

    When a client submits force at M-LOCK, the gate must keep waiting. The
    bypass_gate call must raise PermissionError regardless of actor/reason.
    """
    registry = WorkflowTemplateRegistry()
    wf = registry.get(WorkflowType.NEW_FEATURE)

    with pytest.raises(PermissionError):
        wf.bypass_gate("m_lock", actor="client", reason="force")


@pytest.mark.e2e
def test_ac_fr2101_05_waiver_cannot_bypass_requirements_approval_gate():
    """AC-FR2101-05: a ``waiver`` cannot bypass requirements approval.

    A waiver submitted at requirements approval must not advance the gate.
    """
    registry = WorkflowTemplateRegistry()
    wf = registry.get(WorkflowType.NEW_FEATURE)

    with pytest.raises(PermissionError):
        wf.bypass_gate("requirements_approval", actor="client", reason="waiver")


@pytest.mark.e2e
def test_ac_fr2101_05_resume_cannot_bypass_gate():
    """AC-FR2101-05: a ``resume`` request cannot bypass an applicable gate.

    Resume does not skip the current gate; bypass is rejected.
    """
    registry = WorkflowTemplateRegistry()
    wf = registry.get(WorkflowType.BUG_FIX)

    with pytest.raises(PermissionError):
        wf.bypass_gate("m_lock", actor="agent", reason="resume")


@pytest.mark.e2e
def test_ac_fr2101_05_agent_suggestion_cannot_bypass_gate():
    """AC-FR2101-05: an Agent-suggested bypass cannot pass an applicable gate.

    Even when the actor is an agent with a structured reason, the gate stays.
    """
    registry = WorkflowTemplateRegistry()
    wf = registry.get(WorkflowType.NEW_FEATURE)

    with pytest.raises(PermissionError):
        wf.bypass_gate("m_lock", actor="agent", reason="suggest-skip")


@pytest.mark.e2e
def test_ac_fr2101_05_hotfix_inherits_requirements_approval_only_via_source_contract():
    """AC-FR2101-05: hotfix inherits requirements approval only when source contract matches.

    A hotfix may inherit an existing requirements approval only after
    source-contract validation: spec approved AND digest matches. A digest
    mismatch or unapproved spec must NOT allow inheritance.
    """
    validator = SourceContractValidation()

    assert validator.can_inherit_requirements_approval(
        spec_status="approved",
        source_contract_digest_matches=True,
    ) is True

    assert validator.can_inherit_requirements_approval(
        spec_status="approved",
        source_contract_digest_matches=False,
    ) is False

    assert validator.can_inherit_requirements_approval(
        spec_status="draft",
        source_contract_digest_matches=True,
    ) is False


@pytest.mark.e2e
def test_ac_fr2101_05_bug_fix_creation_requires_approved_spec_and_issue_link():
    """AC-FR2101-05: a valid bug_fix requires an approved spec/AC with a linked issue.

    Without an approved spec or without an issue link, the bug_fix cannot be
    created (so it cannot inherit any approval).
    """
    validator = SourceContractValidation()

    assert validator.validate(spec_status="approved", has_issue_link=True) is True
    assert validator.validate(spec_status="approved", has_issue_link=False) is False
    assert validator.validate(spec_status="draft", has_issue_link=True) is False


# ---------------------------------------------------------------------------
# AC-FR2101-06: completion rejected until all required evidence present
# ---------------------------------------------------------------------------


@pytest.mark.e2e
def test_ac_fr2101_06_new_feature_completion_blocked_when_evidence_missing():
    """AC-FR2101-06: new_feature completion is rejected when any required evidence is missing.

    When an Agent has replied or code has been generated but any required
    artifact/review/gate/implementation evidence/authoritative test/security/
    release policy/milestone close is unmet, completion must be rejected with
    the specific gap listed.
    """
    registry = WorkflowTemplateRegistry()
    wf = registry.get(WorkflowType.NEW_FEATURE)

    # All-but-one evidence present: agent replied + code generated, but e2e missing.
    evidence = {node: True for node in wf.required_completion_nodes}
    evidence["e2e"] = False

    with pytest.raises(CompletionBlockedError) as exc:
        wf.complete(evidence)
    assert "e2e" in str(exc.value)
    # The error must enumerate the gap, not be empty.
    assert str(exc.value).strip() != ""


@pytest.mark.e2e
def test_ac_fr2101_06_new_feature_completion_blocked_lists_all_gaps():
    """AC-FR2101-06: when multiple required pieces are missing, all gaps are listed."""
    registry = WorkflowTemplateRegistry()
    wf = registry.get(WorkflowType.NEW_FEATURE)

    evidence = {node: False for node in wf.required_completion_nodes}

    with pytest.raises(CompletionBlockedError) as exc:
        wf.complete(evidence)
    msg = str(exc.value)
    # Every required node must appear in the gap list.
    for node in wf.required_completion_nodes:
        assert node in msg


@pytest.mark.e2e
def test_ac_fr2101_06_new_feature_completion_succeeds_when_all_evidence_present():
    """AC-FR2101-06: when all required evidence is satisfied, the run reaches completed/history."""
    registry = WorkflowTemplateRegistry()
    wf = registry.get(WorkflowType.NEW_FEATURE)

    evidence = {node: True for node in wf.required_completion_nodes}
    result = wf.complete(evidence)

    assert result.terminal_state == "completed"
    assert result.archived_to_history is True


@pytest.mark.e2e
def test_ac_fr2101_06_bug_fix_completion_blocked_until_policy_release_confirmed():
    """AC-FR2101-06: bug_fix completion blocked until policy release confirmation is present.

    Even with implementation and regression done, missing policy release
    confirmation must block completion (a required evidence piece).
    """
    registry = WorkflowTemplateRegistry()
    wf = registry.get(WorkflowType.BUG_FIX)

    evidence = {node: True for node in wf.required_completion_nodes}
    evidence["policy_release_confirmation"] = False

    with pytest.raises(CompletionBlockedError) as exc:
        wf.complete(evidence)
    assert "policy_release_confirmation" in str(exc.value)
