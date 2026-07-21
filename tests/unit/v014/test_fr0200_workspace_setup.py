"""FR-0200: Workspace Setup Preview、确认与 Manifest.

AC references:
- AC-FR0200-01: Setup preview shows each workspace-level field's value and
  provenance; before Human confirms, no workspace-level external configuration
  is created or modified; before the release request is confirmed, the
  counts of release Project/WorkflowRun/release GitHub Project/branch/Spec
  directory remain zero.
- AC-FR0200-02: when two authoritative sources conflict on the owner,
  restarting ``lk serve`` without Human decision keeps setup in
  ``waiting_human`` and preserves both candidates and their provenance
  byte-equal; WorkflowRun count and external configuration are unchanged.
- AC-FR0200-03: Human's confirmation of setup revision R records the
  revision, actor, selections, all candidate provenance, workspace/
  repository/provider namespace identity, auth/model/OpenCode readiness,
  namespace/create capability and operation evidence; repeating the same
  confirmation does not re-modify workspace-level configuration and the
  release-level resource counts/identity remain unchanged.
- AC-FR0200-04: a namespace/create-capability read check that returns
  missing/multiple/conflict/insufficient-permission keeps setup in
  ``waiting_human`` with the precise check details; no fuzzy-name selection;
  setup manifest not complete; no release Project creation to probe
  capability.
- AC-FR0200-05: after a partial setup with subsequent network/permission/
  restart interruption, reopening Setup from the same workspace recovers
  the same setup revision and per-item status (done/failed/uncertain);
  retry first reconciles completed operations and only continues unfinished
  items; release-level resource creation count stays zero and existing
  counts/identity are unchanged.
"""

from __future__ import annotations

import pytest

from louke.v014.fr0200_workspace_setup import (
    NAMESPACE_AMBIGUOUS,
    NAMESPACE_MISSING,
    NAMESPACE_PERMISSION_DENIED,
    SetupCandidate,
    SetupField,
    SetupManifest,
    SetupPreview,
    SetupProvenance,
    apply_setup_confirmation,
    build_setup_preview,
    check_namespace_capability,
    recover_setup_after_interruption,
)


def _candidate(value: str, source: str = "git_remote") -> SetupCandidate:
    return SetupCandidate(
        value=value,
        provenance=SetupProvenance(source=source, evidence="non-secret"),
    )


# AC-FR0200-01 ---------------------------------------------------------------
def test_setup_preview_shows_value_and_provenance_for_each_field() -> None:
    """AC-FR0200-01: each workspace-level field shows value and provenance."""
    preview = build_setup_preview(
        fields=(
            SetupField(
                name="owner",
                required=True,
                candidates=(_candidate("alice", "git_remote"),),
                selected=None,
                status="pending",
            ),
        ),
        revision=1,
    )
    assert isinstance(preview, SetupPreview)
    assert preview.fields[0].candidates[0].value == "alice"
    assert preview.fields[0].candidates[0].provenance.source == "git_remote"
    # No workspace-level modifications before confirm.
    assert preview.workspace_config_modification_count == 0
    # No release-level resources.
    assert preview.release_resource_creation_count == 0


# AC-FR0200-02 ---------------------------------------------------------------
def test_setup_conflict_preserved_byte_equal_across_restart() -> None:
    """AC-FR0200-02: conflicting candidates are preserved byte-equal after
    restart; setup stays ``waiting_human``; no WorkflowRun or external
    config changes."""
    field = SetupField(
        name="owner",
        required=True,
        candidates=(
            _candidate("alice", "git_remote"),
            _candidate("bob", "pyproject_toml"),
        ),
        selected=None,
        status="conflict",
    )
    preview1 = build_setup_preview(fields=(field,), revision=2)
    preview2 = build_setup_preview(fields=(field,), revision=2)
    assert preview1.status == "waiting_human"
    assert preview2.status == "waiting_human"
    # Byte-equal candidates and provenance.
    assert preview1.fields[0].candidates == preview2.fields[0].candidates
    assert preview1.workflow_run_count == 0
    assert preview2.workflow_run_count == 0
    assert preview1.workspace_config_modification_count == 0
    assert preview2.workspace_config_modification_count == 0


# AC-FR0200-03 ---------------------------------------------------------------
def test_setup_confirmation_records_manifest_and_is_idempotent() -> None:
    """AC-FR0200-03: confirmation records the manifest with revision, actor,
    selections, provenance, readiness, operations; repeating the same
    confirmation does not re-modify workspace configuration and release
    resource counts stay zero."""
    field = SetupField(
        name="owner",
        required=True,
        candidates=(_candidate("alice", "git_remote"),),
        selected=None,
        status="pending",
    )
    preview = build_setup_preview(fields=(field,), revision=1)
    manifest = apply_setup_confirmation(
        preview=preview,
        actor="human:alice",
        selections={"owner": "alice"},
        authorized_operation_ids=("op_1",),
    )
    assert isinstance(manifest, SetupManifest)
    assert manifest.setup_revision == 1
    assert manifest.actor == "human:alice"
    assert manifest.selections == {"owner": "alice"}
    assert manifest.workspace_config_modification_count == 1  # applied once
    assert manifest.release_resource_creation_count == 0
    # Repeat the same confirmation.
    manifest2 = apply_setup_confirmation(
        preview=preview,
        actor="human:alice",
        selections={"owner": "alice"},
        authorized_operation_ids=("op_1",),
        idempotency_key="confirm_1",
    )
    # Idempotent: no re-modification.
    assert manifest2.workspace_config_modification_count == 0
    assert manifest2.release_resource_creation_count == 0


# AC-FR0200-04 ---------------------------------------------------------------
@pytest.mark.parametrize(
    "namespace_result, expected_code",
    [
        ("missing", NAMESPACE_MISSING),
        ("multiple", NAMESPACE_AMBIGUOUS),
        ("conflict", NAMESPACE_AMBIGUOUS),
        ("permission_denied", NAMESPACE_PERMISSION_DENIED),
    ],
)
def test_namespace_capability_check_failure_keeps_waiting_human(
    namespace_result: str, expected_code: str
) -> None:
    """AC-FR0200-04: missing/multiple/conflict/permission-denied namespace
    keeps setup in ``waiting_human``; no fuzzy selection; no release Project
    creation to probe capability."""
    decision = check_namespace_capability(namespace_result=namespace_result)
    assert decision.setup_status == "waiting_human"
    assert decision.code == expected_code
    assert decision.manifest_complete is False
    # No release Project creation to probe.
    assert decision.release_project_probed is False


def test_namespace_capability_check_success_completes_manifest() -> None:
    """AC-FR0200-04: a single exact namespace completes the manifest's
    namespace capability field."""
    decision = check_namespace_capability(namespace_result="single")
    assert decision.setup_status == "ok"
    assert decision.manifest_complete is True
    assert decision.release_project_probed is False


# AC-FR0200-05 ---------------------------------------------------------------
def test_setup_recovery_after_interruption_preserves_revision_and_per_item_status() -> (
    None
):
    """AC-FR0200-05: after interruption, reopening Setup recovers the same
    revision and per-item status; retry only continues unfinished items;
    release-level resource creation count stays zero."""
    field = SetupField(
        name="owner",
        required=True,
        candidates=(_candidate("alice", "git_remote"),),
        selected="alice",
        status="done",
    )
    interrupted_field = SetupField(
        name="opencode",
        required=True,
        candidates=(_candidate("https://opencode.local", "env_var"),),
        selected=None,
        status="uncertain",
    )
    preview = build_setup_preview(fields=(field, interrupted_field), revision=3)
    recovery = recover_setup_after_interruption(preview)
    assert recovery.recovered_revision == 3
    # Per-item status preserved.
    statuses = {f.name: f.status for f in recovery.fields}
    assert statuses["owner"] == "done"
    assert statuses["opencode"] == "uncertain"
    # Retry only continues unfinished items.
    assert "opencode" in recovery.unfinished_field_names
    assert "owner" not in recovery.unfinished_field_names
    # Release-level resource creation count stays zero.
    assert recovery.release_resource_creation_count == 0
    # Existing counts/identity unchanged.
    assert recovery.existing_release_resource_count == 0
