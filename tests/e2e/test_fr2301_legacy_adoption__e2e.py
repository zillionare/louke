"""FR-2301: explicit adoption of pre-v0.12 workspaces and legacy history e2e.

Covers AC-FR2301-01..05. Per test-plan §1.1 these tests observe behavior through
the runtime module public report (MigrationWizard / MigrationPreview /
MigrationMode / LegacyHistory / LegacyEntry / WorkflowRunRef / RollbackError)
which are the observable exits described in interfaces.md §6.1 (migrations,
session/task identity). The v0.12 M-DEV HTTP project API is not yet
implemented; these public outputs are the contract surface.

Expected preview categories, mode recommendation, restore-point and dual-write
guarantees are taken from acceptance.md AC-FR2301-01..05 (the spec), not from
the implementation. The wizard's preview enumerates additions/conversions/
preserved/conflicts/unsupported and recommends local mode; restore point and
rollback exist; legacy history is read-only; no active run auto-created; old
pipeline before commit operates on old state, after commit rejects
incompatible commands; no dual write.

AC references:
- AC-FR2301-01: read-only migration preview lists additions/conversions/preserved/
  conflicts/unsupported and local/global mode (recommends local, no PATH
  guessing); old bytes unchanged until confirmed.
- AC-FR2301-02: restore point before migration; rollback on failure; no two
  half-committed authoritative states.
- AC-FR2301-03: legacy history read-only; original + git identity accessible;
  entries without native evidence never shown as v0.12-native completed.
- AC-FR2301-04: adoption does not auto-create active run; only explicit user
  choice/validation or new run creates a v0.12 WorkflowRun.
- AC-FR2301-05: old pipeline before commit operates on old state; after commit
  rejects incompatible commands; no dual write of current_stage + Runtime.
"""

from __future__ import annotations

import pytest

from louke.runtime.legacy_adoption import (
    LegacyEntry,
    LegacyHistory,
    MigrationMode,
    MigrationPreview,
    MigrationWizard,
    RollbackError,
    WorkflowRunRef,
)

WORKSPACE = "/tmp/louke-legacy-ws"


# ---------------------------------------------------------------------------
# AC-FR2301-01: read-only migration preview
# ---------------------------------------------------------------------------


@pytest.mark.e2e
def test_ac_fr2301_01_preview_lists_additions_conversions_preserved_conflicts_unsupported():
    """AC-FR2301-01: the migration preview enumerates all five categories.

    The preview must list additions, conversions, preserved, conflicts and
    unsupported recovery items so the user can decide before any change.
    """
    wizard = MigrationWizard(WORKSPACE)
    preview = wizard.generate_preview()

    assert isinstance(preview, MigrationPreview)
    # All five categories present (non-empty tuples).
    assert len(preview.additions) > 0
    assert len(preview.conversions) > 0
    assert len(preview.preserved) > 0
    assert len(preview.conflicts) > 0
    assert len(preview.unsupported) > 0


@pytest.mark.e2e
def test_ac_fr2301_01_preview_offers_local_and_global_mode_recommends_local():
    """AC-FR2301-01: the preview offers local and global modes and recommends local.

    The wizard must recommend local mode but allow an explicit compatible
    global choice, and must not guess from PATH.
    """
    wizard = MigrationWizard(WORKSPACE)
    preview = wizard.generate_preview()

    assert MigrationMode.LOCAL in preview.available_modes
    assert MigrationMode.GLOBAL in preview.available_modes
    assert preview.recommended_mode == MigrationMode.LOCAL


@pytest.mark.e2e
def test_ac_fr2301_01_preview_does_not_modify_old_bytes_before_confirm():
    """AC-FR2301-01: the preview does not modify old metadata/docs/history bytes.

    Until the user confirms, all old bytes must remain unchanged. The preview
    reports ``old_bytes_modified=False``.
    """
    wizard = MigrationWizard(WORKSPACE)
    preview = wizard.generate_preview()

    assert preview.old_bytes_modified is False


@pytest.mark.e2e
def test_ac_fr2301_01_confirm_requires_preview_first():
    """AC-FR2301-01: confirmation without a preview is rejected.

    The user cannot confirm a migration they have not previewed, so no
    surprise mutation occurs.
    """
    wizard = MigrationWizard(WORKSPACE)

    with pytest.raises(RuntimeError):
        wizard.confirm(MigrationMode.LOCAL)


# ---------------------------------------------------------------------------
# AC-FR2301-02: restore point + rollback on failure; no dual authoritative state
# ---------------------------------------------------------------------------


@pytest.mark.e2e
def test_ac_fr2301_02_restore_point_created_on_confirm():
    """AC-FR2301-02: a verifiable restore point exists after confirmation.

    Before migration, a restore point must be created so failure can roll back.
    """
    wizard = MigrationWizard(WORKSPACE)
    wizard.generate_preview()

    assert wizard.has_restore_point() is False

    wizard.confirm(MigrationMode.LOCAL)

    assert wizard.has_restore_point() is True


@pytest.mark.e2e
def test_ac_fr2301_02_failed_migration_rolls_back():
    """AC-FR2301-02: a failed migration can be rolled back.

    When a migration fails after the restore point, rollback must restore the
    workspace to the pre-migration state.
    """
    wizard = MigrationWizard(WORKSPACE)
    wizard.generate_preview()
    wizard.confirm(MigrationMode.LOCAL)

    wizard.inject_failure()
    wizard.rollback()

    assert wizard.is_rolled_back() is True


@pytest.mark.e2e
def test_ac_fr2301_02_rollback_without_restore_point_raises():
    """AC-FR2301-02: rollback without a restore point is rejected safely.

    A RollbackError is raised so the workspace is not left in an undefined state.
    """
    wizard = MigrationWizard(WORKSPACE)
    wizard.generate_preview()

    with pytest.raises(RollbackError):
        wizard.rollback()


@pytest.mark.e2e
def test_ac_fr2301_02_no_two_half_committed_authoritative_states():
    """AC-FR2301-02: the workspace never holds two half-committed authoritative states.

    After a successful migration there is exactly one committed state; after a
    rollback there is exactly one (the restored) state. The dual-authoritative
    detector must report False in both cases.
    """
    wizard = MigrationWizard(WORKSPACE)
    wizard.generate_preview()
    wizard.confirm(MigrationMode.LOCAL)

    # Successful migration: single committed state.
    assert wizard.has_dual_authoritative_state() is False

    wizard.inject_failure()
    wizard.rollback()

    # After rollback: single restored state (not dual).
    assert wizard.has_dual_authoritative_state() is False


# ---------------------------------------------------------------------------
# AC-FR2301-03: legacy history read-only; no native completion for legacy-only
# ---------------------------------------------------------------------------


@pytest.mark.e2e
def test_ac_fr2301_03_legacy_entry_is_read_only_with_git_identity():
    """AC-FR2301-03: legacy entries expose original content + git identity read-only.

    The original text and Git identity must be accessible from read-only legacy
    entries after adoption.
    """
    history = LegacyHistory()
    entry = history.add_legacy_entry(
        project_id="proj-legacy-1",
        original_git_identity="alice <alice@example.com>",
        content="legacy spec body",
    )

    assert isinstance(entry, LegacyEntry)
    assert entry.project_id == "proj-legacy-1"
    assert entry.original_git_identity == "alice <alice@example.com>"
    assert entry.content == "legacy spec body"
    assert entry.is_legacy is True
    assert entry.read_only is True


@pytest.mark.e2e
def test_ac_fr2301_03_legacy_history_lookup_returns_entry():
    """AC-FR2301-03: legacy history lookup returns the preserved entry."""
    history = LegacyHistory()
    history.add_legacy_entry(
        project_id="proj-legacy-2",
        original_git_identity="bob <bob@example.com>",
        content="release notes v0.10",
    )

    fetched = history.get_entry("proj-legacy-2")

    assert fetched.project_id == "proj-legacy-2"
    assert fetched.original_git_identity == "bob <bob@example.com>"
    assert fetched.content == "release notes v0.10"


@pytest.mark.e2e
def test_ac_fr2301_03_legacy_entry_without_native_evidence_not_native_completed():
    """AC-FR2301-03: a legacy entry without native event/gate evidence is never shown as v0.12-native completed.

    Even when a legacy entry is preserved, the system must not present it as a
    v0.12-native completed project; is_native_completed must return False.
    """
    history = LegacyHistory()
    history.add_legacy_entry(
        project_id="proj-legacy-3",
        original_git_identity="carol <carol@example.com>",
        content="completed per old pipeline",
    )

    assert history.is_native_completed("proj-legacy-3") is False


@pytest.mark.e2e
def test_ac_fr2301_03_unknown_legacy_project_lookup_raises():
    """AC-FR2301-03: looking up an unknown legacy project raises rather than faking a record.

    The legacy history must not synthesize a record for a project it does not
    have; a KeyError surfaces the gap.
    """
    history = LegacyHistory()

    with pytest.raises(KeyError):
        history.get_entry("does-not-exist")


# ---------------------------------------------------------------------------
# AC-FR2301-04: adoption does not auto-create active run
# ---------------------------------------------------------------------------


@pytest.mark.e2e
def test_ac_fr2301_04_adoption_creates_no_active_run_automatically():
    """AC-FR2301-04: a successful adoption does not auto-create an active WorkflowRun.

    Even after commit, active_runs must be empty until the user explicitly
    creates a new run or migrates one through validation.
    """
    wizard = MigrationWizard(WORKSPACE)
    wizard.generate_preview()
    wizard.confirm(MigrationMode.LOCAL)

    assert wizard.active_runs == []


@pytest.mark.e2e
def test_ac_fr2301_04_explicit_new_run_creates_v012_workflow_run():
    """AC-FR2301-04: an explicit user choice creates a v0.12 WorkflowRun after adoption.

    Only after adoption is committed can the user create a new run; the run
    carries a stable id, definition name and version.
    """
    wizard = MigrationWizard(WORKSPACE)
    wizard.generate_preview()
    wizard.confirm(MigrationMode.LOCAL)

    run = wizard.create_new_run(definition_name="new_feature", version="1.0.0")

    assert isinstance(run, WorkflowRunRef)
    assert run.definition_name == "new_feature"
    assert run.version == "1.0.0"
    assert wizard.active_runs == [run]


@pytest.mark.e2e
def test_ac_fr2301_04_new_run_before_adoption_rejected():
    """AC-FR2301-04: creating a run before adoption is rejected.

    The system must not create an active run from an un-adopted workspace.
    """
    wizard = MigrationWizard(WORKSPACE)
    wizard.generate_preview()

    with pytest.raises(RuntimeError):
        wizard.create_new_run(definition_name="new_feature", version="1.0.0")


@pytest.mark.e2e
def test_ac_fr2301_04_new_run_after_rollback_rejected():
    """AC-FR2301-04: after a rolled-back migration, no new run can be created.

    A rolled-back workspace is not in the committed state, so run creation
    must be rejected.
    """
    wizard = MigrationWizard(WORKSPACE)
    wizard.generate_preview()
    wizard.confirm(MigrationMode.LOCAL)
    wizard.inject_failure()
    wizard.rollback()

    with pytest.raises(RuntimeError):
        wizard.create_new_run(definition_name="new_feature", version="1.0.0")


# ---------------------------------------------------------------------------
# AC-FR2301-05: old pipeline before commit vs after commit; no dual write
# ---------------------------------------------------------------------------


@pytest.mark.e2e
def test_ac_fr2301_05_old_pipeline_before_commit_operates_on_old_state():
    """AC-FR2301-05: before commit, an old pipeline command operates on old state.

    The old pipeline must still work against the old state until adoption is
    committed.
    """
    wizard = MigrationWizard(WORKSPACE)
    wizard.generate_preview()

    result = wizard.run_old_pipeline_command("current_stage")

    assert result["target"] == "old_state"
    assert result["command"] == "current_stage"


@pytest.mark.e2e
def test_ac_fr2301_05_old_pipeline_after_commit_rejects_incompatible_command():
    """AC-FR2301-05: after commit, incompatible old pipeline commands are rejected.

    Once adoption is committed, ``current_stage`` (an incompatible dual-source
    command) must be rejected so the new Runtime is the sole source of truth.
    """
    wizard = MigrationWizard(WORKSPACE)
    wizard.generate_preview()
    wizard.confirm(MigrationMode.LOCAL)

    with pytest.raises(RuntimeError) as exc:
        wizard.run_old_pipeline_command("current_stage")
    assert "incompatible" in str(exc.value).lower()


@pytest.mark.e2e
def test_ac_fr2301_05_no_dual_write_of_current_stage_and_runtime():
    """AC-FR2301-05: no stage writes both old current_stage and new Runtime.

    The dual-write detector must report False at every stage: preview, confirm
    and after rollback.
    """
    wizard = MigrationWizard(WORKSPACE)

    wizard.generate_preview()
    assert wizard.dual_write_detected() is False

    wizard.confirm(MigrationMode.LOCAL)
    assert wizard.dual_write_detected() is False

    wizard.inject_failure()
    wizard.rollback()
    assert wizard.dual_write_detected() is False


@pytest.mark.e2e
def test_ac_fr2301_05_after_rollback_old_pipeline_operates_on_old_state_again():
    """AC-FR2301-05: after a rollback, the old pipeline resumes operating on old state.

    Rolling back restores the workspace, so old pipeline commands are no longer
    rejected and target the old state.
    """
    wizard = MigrationWizard(WORKSPACE)
    wizard.generate_preview()
    wizard.confirm(MigrationMode.LOCAL)
    wizard.inject_failure()
    wizard.rollback()

    result = wizard.run_old_pipeline_command("current_stage")

    assert result["target"] == "old_state"
