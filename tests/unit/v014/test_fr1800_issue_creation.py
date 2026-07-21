"""FR-1800: M-LOCK-1 后的 GitHub Issue 创建与 Project 关联.

AC references:
- AC-FR1800-01: before M-LOCK-1 is approved, any Issue split/create request
  is rejected and the target repository's Issue search result count and
  release Project item count do not increase.
- AC-FR1800-02: when the locked Spec has 21 FRs + 3 NFRs all Valid=✅, the
  target count is 24; each Valid (non-❌) requirement has exactly one Issue
  whose title starts with the exact single ``[{ID}]`` token and whose body
  contains the ID, locked Spec section URL and Acceptance section URL; all
  24 Issues appear as single Project items in the Foundation release GitHub
  Project.
- AC-FR1800-03: reconcile of the same repository/spec/requirement/joint-
  digest operation (repeated/concurrent/restart) produces at most one
  matching Issue and one Project item per requirement; a reused Issue's
  first requirement token must exactly equal the ID and its body ID, links
  and Project association must match; remote-success-local-ack-loss Issues
  are query-reused rather than recreated.
- AC-FR1800-04: partial Issue/Project failures show per-ID status
  (created/linked/failed/uncertain) and provider error; successful Issue
  numbers do not change; only failed items are retried; the step does not
  complete until all are linked.
- AC-FR1800-05: a search hit whose title starts with ``[FR-0100]`` but
  whose first requirement token is duplicated/imprecise, or whose body ID,
  links or Project association do not match, is not reused; the page shows
  conflict status and the mismatched fields; no second candidate Issue is
  created until Human resolves the ambiguity.
"""

from __future__ import annotations


from louke.v014.fr1800_issue_creation import (
    GATE_NOT_APPROVED,
    IssueBodyIdentity,
    IssueIdentity,
    IssueOperation,
    IssueOperationStatus,
    IssueReconciler,
    IssueTarget,
    compute_issue_targets,
    compute_project_item_count,
    format_issue_title,
    is_gate_approved_for_issue_creation,
    parse_first_requirement_token,
    reconcile_existing_issue,
)


# AC-FR1800-01 ---------------------------------------------------------------
def test_issue_creation_rejected_before_m_lock_1_approval() -> None:
    """AC-FR1800-01: before M-LOCK-1 is approved, Issue creation is rejected
    with GATE_NOT_APPROVED; Issue search and Project item counts do not
    increase."""
    decision = is_gate_approved_for_issue_creation(m_lock_1_approved=False)
    assert decision.allowed is False
    assert decision.code == GATE_NOT_APPROVED
    assert decision.issue_search_count_delta == 0
    assert decision.project_item_count_delta == 0


# AC-FR1800-02 ---------------------------------------------------------------
def test_compute_targets_for_locked_24_requirements() -> None:
    """AC-FR1800-02: 21 FR + 3 NFR all Valid=✅ produces 24 targets."""
    locked_requirements = [
        {"id": f"FR-{i:04d}", "valid": "✅"} for i in range(100, 100 + 21)
    ] + [{"id": f"NFR-{i:04d}", "valid": "✅"} for i in range(100, 100 + 3)]
    targets = compute_issue_targets(locked_requirements)
    assert len(targets) == 24
    # All targets are Valid (not ❌).
    assert all(t.valid != "❌" for t in targets)
    # IDs are unique.
    ids = {t.requirement_id for t in targets}
    assert len(ids) == 24


def test_invalid_requirements_excluded_from_targets() -> None:
    """AC-FR1800-02: requirements with Valid=❌ are excluded from targets."""
    locked_requirements = [
        {"id": "FR-0100", "valid": "✅"},
        {"id": "FR-0101", "valid": "❌"},  # excluded
        {"id": "NFR-0100", "valid": "✅"},
    ]
    targets = compute_issue_targets(locked_requirements)
    assert len(targets) == 2
    assert {t.requirement_id for t in targets} == {"FR-0100", "NFR-0100"}


def test_issue_title_starts_with_exact_single_requirement_token() -> None:
    """AC-FR1800-02: the Issue title starts with the exact single ``[{ID}]``
    token."""
    title = format_issue_title("FR-0100", "Add offline cache for project list.")
    assert title.startswith("[FR-0100] ")
    # Exactly one token at the start.
    assert parse_first_requirement_token(title) == "FR-0100"


def test_issue_body_identity_contains_id_and_section_links() -> None:
    """AC-FR1800-02: the Issue body contains the ID, locked Spec section URL
    and Acceptance section URL."""
    identity = IssueBodyIdentity(
        requirement_id="FR-0100",
        spec_section_url=(
            "https://github.com/zillionare/louke/blob/releases/0.14.0/"
            ".louke/project/specs/v0.14-001-workflow-reflow-spec/spec.md#fr-0100"
        ),
        acceptance_section_url=(
            "https://github.com/zillionare/louke/blob/releases/0.14.0/"
            ".louke/project/specs/v0.14-001-workflow-reflow-spec/acceptance.md#ac-fr-0100"
        ),
    )
    assert identity.requirement_id == "FR-0100"
    assert "spec.md#fr-0100" in identity.spec_section_url
    assert "acceptance.md#ac-fr-0100" in identity.acceptance_section_url


def test_project_item_count_per_target_is_one() -> None:
    """AC-FR1800-02: each target Issue is a single Project item in the
    Foundation release GitHub Project."""
    item_count = compute_project_item_count(
        targets=[
            IssueTarget(requirement_id="FR-0100", valid="✅"),
            IssueTarget(requirement_id="FR-0200", valid="✅"),
        ],
        per_target_item_count=1,
    )
    assert item_count == 2


# AC-FR1800-03 ---------------------------------------------------------------
def test_reconcile_reuses_issue_when_identity_exactly_matches() -> None:
    """AC-FR1800-03: an existing Issue whose identity exactly matches is
    reused; no second Issue or Project item is created."""
    reconciler = IssueReconciler()
    target = IssueTarget(requirement_id="FR-0100", valid="✅")
    expected = IssueIdentity(
        repository_node_id="R_1",
        spec_id="v0.14-001-workflow-reflow-spec",
        requirement_id="FR-0100",
        joint_digest="sha256:" + "j" * 64,
        body=IssueBodyIdentity(
            requirement_id="FR-0100",
            spec_section_url="https://example/spec.md#fr-0100",
            acceptance_section_url="https://example/acceptance.md#ac-fr-0100",
        ),
        project_node_id="P_1",
    )
    op = IssueOperation(
        operation_id="op_1",
        target=target,
        expected_identity=expected,
        status=IssueOperationStatus.PENDING,
    )
    result = reconciler.reconcile(op, existing=expected)
    assert result.status == IssueOperationStatus.REUSED
    assert result.actual_identity == expected
    # No new Issue or Project item created.
    assert result.created_issue is False
    assert result.created_project_item is False


def test_reconcile_creates_issue_when_no_existing_match() -> None:
    """AC-FR1800-03: when no existing Issue matches, the reconciler creates
    one and links exactly one Project item."""
    reconciler = IssueReconciler()
    target = IssueTarget(requirement_id="FR-0100", valid="✅")
    expected = IssueIdentity(
        repository_node_id="R_1",
        spec_id="v0.14-001-workflow-reflow-spec",
        requirement_id="FR-0100",
        joint_digest="sha256:" + "j" * 64,
        body=IssueBodyIdentity(
            requirement_id="FR-0100",
            spec_section_url="https://example/spec.md#fr-0100",
            acceptance_section_url="https://example/acceptance.md#ac-fr-0100",
        ),
        project_node_id="P_1",
    )
    op = IssueOperation(
        operation_id="op_1",
        target=target,
        expected_identity=expected,
        status=IssueOperationStatus.PENDING,
    )
    result = reconciler.reconcile(op, existing=None)
    assert result.status == IssueOperationStatus.CREATED
    assert result.created_issue is True
    assert result.created_project_item is True


# AC-FR1800-04 ---------------------------------------------------------------
def test_partial_failure_keeps_successful_issue_numbers() -> None:
    """AC-FR1800-04: when some Issue/Project operations fail, successful
    Issue numbers do not change; only failed items are retried."""
    reconciler = IssueReconciler()
    target = IssueTarget(requirement_id="FR-0100", valid="✅")
    expected = IssueIdentity(
        repository_node_id="R_1",
        spec_id="v0.14-001-workflow-reflow-spec",
        requirement_id="FR-0100",
        joint_digest="sha256:" + "j" * 64,
        body=IssueBodyIdentity(
            requirement_id="FR-0100",
            spec_section_url="https://example/spec.md#fr-0100",
            acceptance_section_url="https://example/acceptance.md#ac-fr-0100",
        ),
        project_node_id="P_1",
    )
    op = IssueOperation(
        operation_id="op_1",
        target=target,
        expected_identity=expected,
        status=IssueOperationStatus.PENDING,
        issue_number=42,  # already created
    )
    # Project link fails.
    result = reconciler.mark_link_failure(op, provider_error="Projects API 502")
    assert result.status == IssueOperationStatus.FAILED
    assert result.issue_number == 42  # preserved
    assert "Projects API 502" in result.provider_error
    # Retry only the link, not the Issue creation.
    assert result.created_issue is False


# AC-FR1800-05 ---------------------------------------------------------------
def test_reconcile_conflict_when_title_token_is_imprecise() -> None:
    """AC-FR1800-05: an Issue whose title starts with ``[FR-0100]`` but
    whose first requirement token is duplicated/imprecise is not reused; the
    operation enters conflict and no second candidate is created."""
    target = IssueTarget(requirement_id="FR-0100", valid="✅")
    expected = IssueIdentity(
        repository_node_id="R_1",
        spec_id="v0.14-001-workflow-reflow-spec",
        requirement_id="FR-0100",
        joint_digest="sha256:" + "j" * 64,
        body=IssueBodyIdentity(
            requirement_id="FR-0100",
            spec_section_url="https://example/spec.md#fr-0100",
            acceptance_section_url="https://example/acceptance.md#ac-fr-0100",
        ),
        project_node_id="P_1",
    )
    # Existing Issue title has duplicate token: "[FR-0100][FR-0100] ..."
    mismatched = IssueIdentity(
        repository_node_id="R_1",
        spec_id="v0.14-001-workflow-reflow-spec",
        requirement_id="FR-0100",
        joint_digest="sha256:" + "j" * 64,
        body=IssueBodyIdentity(
            requirement_id="FR-0100",
            spec_section_url="https://example/spec.md#fr-0100",
            acceptance_section_url="https://example/acceptance.md#ac-fr-0100",
        ),
        project_node_id="P_1",
        observed_title="[FR-0100][FR-0100] duplicated token",
    )
    op = IssueOperation(
        operation_id="op_1",
        target=target,
        expected_identity=expected,
        status=IssueOperationStatus.PENDING,
    )
    result = reconcile_existing_issue(op, existing=mismatched)
    assert result.status == IssueOperationStatus.CONFLICT
    assert result.created_issue is False
    assert "title" in result.conflict_fields


def test_reconcile_conflict_when_body_link_or_project_mismatches() -> None:
    """AC-FR1800-05: an Issue whose body ID, links or Project association do
    not match is not reused; the operation enters conflict with the
    mismatched fields listed."""
    target = IssueTarget(requirement_id="FR-0100", valid="✅")
    expected = IssueIdentity(
        repository_node_id="R_1",
        spec_id="v0.14-001-workflow-reflow-spec",
        requirement_id="FR-0100",
        joint_digest="sha256:" + "j" * 64,
        body=IssueBodyIdentity(
            requirement_id="FR-0100",
            spec_section_url="https://example/spec.md#fr-0100",
            acceptance_section_url="https://example/acceptance.md#ac-fr-0100",
        ),
        project_node_id="P_1",
    )
    mismatched_body = IssueIdentity(
        repository_node_id="R_1",
        spec_id="v0.14-001-workflow-reflow-spec",
        requirement_id="FR-0100",
        joint_digest="sha256:" + "j" * 64,
        body=IssueBodyIdentity(
            requirement_id="FR-0200",  # wrong ID in body
            spec_section_url="https://example/spec.md#fr-0100",
            acceptance_section_url="https://example/acceptance.md#ac-fr-0100",
        ),
        project_node_id="P_1",
        observed_title="[FR-0100] some title",
    )
    op = IssueOperation(
        operation_id="op_1",
        target=target,
        expected_identity=expected,
        status=IssueOperationStatus.PENDING,
    )
    result = reconcile_existing_issue(op, existing=mismatched_body)
    assert result.status == IssueOperationStatus.CONFLICT
    assert "body.requirement_id" in result.conflict_fields
