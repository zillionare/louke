"""FR-0400: 新 Release 的 ``main`` 前置检查与 Foundation.

AC references:
- AC-FR0400-01: declared remote refresh failure or previous-branch not merged
  into authoritative main -> status non-PASS, no release-level resources and
  no M-STORY task created.
- AC-FR0400-02: remote main SHA = M and preflight passes -> each Foundation
  resource (Project, WorkflowRun, release GitHub Project, release branch, Spec
  directory) exists exactly once; release branch start bytes equal M; the
  Foundation evidence records each stable identity.
- AC-FR0400-03: release Project already created but local ack lost -> on
  reconcile, query and reuse the same Project node ID; resource count does
  not increase; M-STORY is not started early.
- AC-FR0400-04: no release resources exist, declared remote refresh succeeds,
  but local main != remote main OR previous branch relation is
  ahead/behind/diverged/unknown -> foundation status non-PASS; no resources
  created; remediation is non-empty.
- AC-FR0400-05: reconcile finds existing release branch start != M, or some
  resource identity conflicts with Foundation evidence -> Foundation stays
  ``conflict`` or ``needs_attention``; not ``complete``; no candidate branch
  or other resource is created; no silent overwrite of existing resources.
"""

from __future__ import annotations

import pytest

from louke.v014.fr0400_foundation import (
    FoundationOperationKind,
    FoundationReconciler,
    GitRefRelation,
    RemoteMain,
    evaluate_main_preflight,
)


def _remote_main(
    sha: str = "M" * 40, full_ref: str = "refs/remotes/origin/main"
) -> RemoteMain:
    return RemoteMain(full_ref=full_ref, sha=sha)


# AC-FR0400-01 ---------------------------------------------------------------
def test_preflight_fails_when_declared_remote_refresh_failed() -> None:
    """AC-FR0400-01: refresh error produces non-PASS with the refresh error
    message; no resources are claimed as created."""
    result = evaluate_main_preflight(
        declared_remote_refresh_error="fetch timeout",
        remote_main=None,
        previous_branch_relation=None,
        local_main_sha=None,
    )
    assert result.status == "blocked"
    assert "fetch timeout" in result.remediation
    assert result.can_create_foundation_resources is False


def test_preflight_fails_when_previous_branch_not_merged() -> None:
    """AC-FR0400-01: previous branch not merged (any non-merged relation)
    blocks Foundation and lists the ref/SHA/relation."""
    for relation in ("ahead", "behind", "diverged", "unknown"):
        result = evaluate_main_preflight(
            declared_remote_refresh_error=None,
            remote_main=_remote_main(sha="R" * 40),
            previous_branch_relation=GitRefRelation(relation),  # type: ignore[arg-type]
            previous_branch_full_ref="refs/heads/releases/0.13.1",
            previous_branch_sha="P" * 40,
            local_main_sha="R" * 40,
        )
        assert result.status == "blocked", relation
        assert "refs/heads/releases/0.13.1" in result.remediation, relation
        assert relation in result.remediation, relation
        assert result.can_create_foundation_resources is False


# AC-FR0400-02 ---------------------------------------------------------------
def test_preflight_passes_only_when_relation_merged_and_local_main_equals_remote() -> (
    None
):
    """AC-FR0400-02 + AC-FR0400-04: PASS requires relation=merged AND
    local_main_sha == remote_main.sha. Any other combination is non-PASS."""
    ok = evaluate_main_preflight(
        declared_remote_refresh_error=None,
        remote_main=_remote_main(sha="M" * 40),
        previous_branch_relation=GitRefRelation.MERGED,
        previous_branch_full_ref="refs/heads/releases/0.13.1",
        previous_branch_sha="P" * 40,
        local_main_sha="M" * 40,
    )
    assert ok.status == "pass"
    assert ok.can_create_foundation_resources is True
    assert ok.remote_main_sha == "M" * 40

    mismatched_local = evaluate_main_preflight(
        declared_remote_refresh_error=None,
        remote_main=_remote_main(sha="M" * 40),
        previous_branch_relation=GitRefRelation.MERGED,
        previous_branch_full_ref="refs/heads/releases/0.13.1",
        previous_branch_sha="P" * 40,
        local_main_sha="X" * 40,
    )
    assert mismatched_local.status == "blocked"
    assert mismatched_local.can_create_foundation_resources is False
    assert "local" in mismatched_local.remediation.lower()


def test_foundation_completes_when_all_resources_confirmed_and_branch_start_matches_m() -> (
    None
):
    """AC-FR0400-02: each Foundation resource exists exactly once and the
    release branch start byte-equals M when Foundation is complete."""
    reconciler = FoundationReconciler()
    manifest = reconciler.begin(
        workspace_id="ws_1",
        release_version="0.14.0",
        remote_main=_remote_main(sha="M" * 40),
    )
    # All five required kinds must be confirmed for completion.
    for kind in (
        FoundationOperationKind.LOCAL_PROJECT,
        FoundationOperationKind.WORKFLOW_RUN,
        FoundationOperationKind.GITHUB_PROJECT,
        FoundationOperationKind.RELEASE_BRANCH,
        FoundationOperationKind.SPEC_DIRECTORY,
    ):
        op = manifest.operation_for(kind)
        assert op is not None  # AC-FR0400-02: one operation per required kind
        manifest = reconciler.confirm(
            manifest, op.operation_id, actual_identity=f"id:{kind.value}"
        )

    branch_op = manifest.operation_for(FoundationOperationKind.RELEASE_BRANCH)
    assert branch_op is not None  # AC-FR0400-02: release branch operation exists
    manifest = reconciler.record_release_branch_start(
        manifest, branch_op.operation_id, start_sha="M" * 40
    )

    assert manifest.is_complete
    assert manifest.release_branch_start_sha == "M" * 40
    # AC-FR0400-02: each kind has exactly one operation.
    seen_kinds = [op.kind for op in manifest.operations]
    for kind in FoundationOperationKind:
        assert seen_kinds.count(kind) == 1


# AC-FR0400-03 ---------------------------------------------------------------
def test_foundation_reconcile_reuses_existing_project_node_id_after_ack_loss() -> None:
    """AC-FR0400-03: after a network ack loss, the reconciler queries and
    reuses the same Project node ID; resource count does not increase and
    M-STORY (Foundation completion) is not claimed early."""
    reconciler = FoundationReconciler()
    manifest = reconciler.begin(
        workspace_id="ws_1",
        release_version="0.14.0",
        remote_main=_remote_main(sha="M" * 40),
    )
    project_op = manifest.operation_for(FoundationOperationKind.LOCAL_PROJECT)
    assert project_op is not None  # AC-FR0400-03: pending LOCAL_PROJECT op

    # Simulate remote success but local ack loss: query returns the existing
    # node ID; the reconciler must reuse it instead of creating a second one.
    manifest = reconciler.reconcile_existing(
        manifest,
        project_op.operation_id,
        existing_identity="node_id:abc",
    )
    project_op_after = manifest.operation_for(FoundationOperationKind.LOCAL_PROJECT)
    assert project_op_after is not None  # AC-FR0400-03: reused LOCAL_PROJECT op
    assert project_op_after.status == "confirmed"
    assert project_op_after.actual_identity == "node_id:abc"
    # Still only one operation per kind.
    assert (
        sum(
            1
            for op in manifest.operations
            if op.kind == FoundationOperationKind.LOCAL_PROJECT
        )
        == 1
    )
    # Foundation not complete because the other resources are not confirmed.
    assert manifest.is_complete is False


# AC-FR0400-04 ---------------------------------------------------------------
@pytest.mark.parametrize(
    "relation, local_main_sha",
    [
        ("ahead", "M" * 40),
        ("behind", "M" * 40),
        ("diverged", "M" * 40),
        ("unknown", "M" * 40),
        ("merged", "X" * 40),
    ],
)
def test_preflight_blocked_relations_and_local_mismatch_produce_no_resources(
    relation: str, local_main_sha: str
) -> None:
    """AC-FR0400-04: blocked preflight (non-merged relation OR local main
    mismatch) never allows Foundation resources to be created."""
    result = evaluate_main_preflight(
        declared_remote_refresh_error=None,
        remote_main=_remote_main(sha="M" * 40),
        previous_branch_relation=GitRefRelation(relation),  # type: ignore[arg-type]
        previous_branch_full_ref="refs/heads/releases/0.13.1",
        previous_branch_sha="P" * 40,
        local_main_sha=local_main_sha,
    )
    assert result.status == "blocked"
    assert result.can_create_foundation_resources is False
    assert result.remediation  # non-empty


# AC-FR0400-05 ---------------------------------------------------------------
def test_foundation_conflict_when_release_branch_start_does_not_match_m() -> None:
    """AC-FR0400-05: an existing release branch whose start != M puts the
    Foundation into ``conflict``; no completion, no candidate branch."""
    reconciler = FoundationReconciler()
    manifest = reconciler.begin(
        workspace_id="ws_1",
        release_version="0.14.0",
        remote_main=_remote_main(sha="M" * 40),
    )
    branch_op = manifest.operation_for(FoundationOperationKind.RELEASE_BRANCH)
    assert branch_op is not None  # AC-FR0400-05: branch op exists pre-record
    # Existing branch starts at a different SHA.
    manifest = reconciler.record_release_branch_start(
        manifest, branch_op.operation_id, start_sha="X" * 40
    )
    assert manifest.is_complete is False
    branch_op_after = manifest.operation_for(FoundationOperationKind.RELEASE_BRANCH)
    assert branch_op_after is not None  # AC-FR0400-05: branch op exists post-record
    assert branch_op_after.status == "conflict"
    # No second RELEASE_BRANCH operation is created.
    assert (
        sum(
            1
            for op in manifest.operations
            if op.kind == FoundationOperationKind.RELEASE_BRANCH
        )
        == 1
    )


def test_foundation_conflict_when_resource_identity_conflicts_with_evidence() -> None:
    """AC-FR0400-05: when reconcile finds a resource whose identity conflicts
    with Foundation evidence, the operation enters ``conflict`` and no new
    candidate is created."""
    reconciler = FoundationReconciler()
    manifest = reconciler.begin(
        workspace_id="ws_1",
        release_version="0.14.0",
        remote_main=_remote_main(sha="M" * 40),
    )
    project_op = manifest.operation_for(FoundationOperationKind.LOCAL_PROJECT)
    assert project_op is not None  # AC-FR0400-05: pending project op
    # First confirm with one identity.
    manifest = reconciler.confirm(
        manifest, project_op.operation_id, actual_identity="node:A"
    )
    # Reconcile sees a *different* existing identity -> conflict, no overwrite.
    manifest = reconciler.reconcile_existing(
        manifest,
        project_op.operation_id,
        existing_identity="node:B",
    )
    project_op_after = manifest.operation_for(FoundationOperationKind.LOCAL_PROJECT)
    assert project_op_after is not None  # AC-FR0400-05: project op after conflict
    assert project_op_after.status == "conflict"
    assert project_op_after.actual_identity == "node:A"  # original preserved
    assert manifest.is_complete is False
    assert (
        sum(
            1
            for op in manifest.operations
            if op.kind == FoundationOperationKind.LOCAL_PROJECT
        )
        == 1
    )
