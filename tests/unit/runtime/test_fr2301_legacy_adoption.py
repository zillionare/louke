"""FR-2301: explicit adoption of v0.10/v0.11 workspaces and legacy history.

AC references:
- AC-FR2301-01: adoption entry gives a read-only migration preview listing
  additions, conversions, preserved items, conflicts, unsupported items and
  the local/global mode choice; old bytes are unchanged until confirmed.
- AC-FR2301-02: migration has a verifiable restore point, failures can be
  rolled back or repaired, and no dual-authoritative half-committed state.
- AC-FR2301-03: after adoption, legacy specs/releases/history are accessible
  as read-only legacy entries; projects without native event/gate evidence are
  not shown as v0.12-native completed.
- AC-FR2301-04: adoption does not auto-create active runs; only explicit
  user choice + current definition/contract validation or a new run creates a
  v0.12 WorkflowRun.
- AC-FR2301-05: before commit, old pipeline commands still operate on old
  state; after commit, incompatible old commands are rejected; never dual-write
  old current_stage and new Runtime.
"""

from __future__ import annotations

import pytest

from louke.runtime.legacy_adoption import (
    LegacyHistory,
    MigrationMode,
    MigrationPreview,
    MigrationWizard,
)


# -- AC-FR2301-01 -------------------------------------------------------------


def test_ac_fr2301_01_preview_lists_categories_and_mode():
    """AC-FR2301-01: preview lists migration categories and mode choice."""
    wizard = MigrationWizard(workspace_path="/old_workspace")
    preview = wizard.generate_preview()

    assert isinstance(preview, MigrationPreview)
    assert "project.toml" in preview.additions
    assert "runtime_mode" in preview.conversions
    assert "legacy_history" in preview.preserved
    assert preview.recommended_mode == MigrationMode.LOCAL
    assert preview.available_modes == (MigrationMode.LOCAL, MigrationMode.GLOBAL)


def test_ac_fr2301_01_old_bytes_unchanged_before_confirm():
    """AC-FR2301-01: old metadata/docs/history bytes are unchanged before confirm."""
    wizard = MigrationWizard(workspace_path="/old_workspace")
    preview = wizard.generate_preview()

    assert preview.old_bytes_modified is False


# -- AC-FR2301-02 -------------------------------------------------------------


def test_ac_fr2301_02_restore_point_before_migration():
    """AC-FR2301-02: migration creates a verifiable restore point."""
    wizard = MigrationWizard(workspace_path="/old_workspace")
    wizard.generate_preview()
    wizard.confirm(mode=MigrationMode.LOCAL)

    assert wizard.has_restore_point() is True


def test_ac_fr2301_02_failed_migration_can_rollback():
    """AC-FR2301-02: failed migration can be rolled back."""
    wizard = MigrationWizard(workspace_path="/old_workspace")
    wizard.generate_preview()
    wizard.confirm(mode=MigrationMode.LOCAL)
    wizard.inject_failure()

    wizard.rollback()

    assert wizard.is_rolled_back() is True
    assert wizard.has_dual_authoritative_state() is False


# -- AC-FR2301-03 -------------------------------------------------------------


def test_ac_fr2301_03_legacy_history_read_only():
    """AC-FR2301-03: legacy history entries are read-only."""
    history = LegacyHistory()
    history.add_legacy_entry(
        project_id="proj_001",
        original_git_identity="abc123",
        content="legacy spec",
    )

    entry = history.get_entry("proj_001")
    assert entry.is_legacy is True
    assert entry.read_only is True


def test_ac_fr2301_03_legacy_without_native_evidence_not_completed():
    """AC-FR2301-03: legacy entries without native evidence are not native completed."""
    history = LegacyHistory()
    history.add_legacy_entry(project_id="proj_002")

    assert history.is_native_completed("proj_002") is False


# -- AC-FR2301-04 -------------------------------------------------------------


def test_ac_fr2301_04_no_auto_active_run_after_adoption():
    """AC-FR2301-04: adoption does not auto-create an active run."""
    wizard = MigrationWizard(workspace_path="/old_workspace")
    wizard.generate_preview()
    wizard.confirm(mode=MigrationMode.LOCAL)

    assert wizard.active_runs == []


def test_ac_fr2301_04_new_run_creates_workflow_run():
    """AC-FR2301-04: explicit new run after adoption creates a v0.12 WorkflowRun."""
    wizard = MigrationWizard(workspace_path="/old_workspace")
    wizard.generate_preview()
    wizard.confirm(mode=MigrationMode.LOCAL)

    run = wizard.create_new_run(definition_name="new_feature", version="1.0")

    assert run.run_id.startswith("run_")
    assert run.definition_name == "new_feature"


# -- AC-FR2301-05 -------------------------------------------------------------


def test_ac_fr2301_05_old_pipeline_before_commit_uses_old_state():
    """AC-FR2301-05: before commit, old pipeline commands operate on old state."""
    wizard = MigrationWizard(workspace_path="/old_workspace")
    wizard.generate_preview()

    result = wizard.run_old_pipeline_command("status")
    assert result["target"] == "old_state"


def test_ac_fr2301_05_after_commit_incompatible_old_command_rejected():
    """AC-FR2301-05: after commit, incompatible old commands are rejected."""
    wizard = MigrationWizard(workspace_path="/old_workspace")
    wizard.generate_preview()
    wizard.confirm(mode=MigrationMode.LOCAL)

    with pytest.raises(RuntimeError):
        wizard.run_old_pipeline_command("current_stage")


def test_ac_fr2301_05_no_dual_write():
    """AC-FR2301-05: no dual write to old current_stage and new Runtime."""
    wizard = MigrationWizard(workspace_path="/old_workspace")
    wizard.generate_preview()
    wizard.confirm(mode=MigrationMode.LOCAL)

    assert wizard.dual_write_detected() is False
