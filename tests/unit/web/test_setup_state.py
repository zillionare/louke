"""Unit tests for the v2 Setup manifest (AC-FR0001, AC-FR0101, AC-FR0301).

AC-FR0001-01, AC-FR0001-02, AC-FR0101-01, AC-FR0101-02,
AC-FR0301-01, AC-FR0301-02, AC-NFR0001-01

The v2 manifest replaces the old six-step SetupJourney. It has three
states (``pending_user``, ``pending_model``, ``complete``) and uses
compare-and-swap for atomic transitions.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from louke.web.setup_state import (
    SetupStateError,
    SetupStateMismatch,
    SetupStatus,
    migrate_v1_state,
    read_manifest,
    write_manifest,
)


# ---------------------------------------------------------------------------
# Constants & fixtures
# ---------------------------------------------------------------------------


WORKSPACE_ID = "ws_test_001"


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    """An empty workspace directory with a ``.louke/`` sub-tree."""
    louke = tmp_path / ".louke"
    louke.mkdir()
    return tmp_path


# ---------------------------------------------------------------------------
# AC-FR0001-01: blank workspace has no manifest → gate must redirect
# ---------------------------------------------------------------------------


def test_blank_workspace_returns_pending_user(workspace: Path):
    """AC-FR0001-01: a workspace with no manifest defaults to ``pending_user``."""
    # AC-FR0001-01
    manifest = read_manifest(workspace, workspace_id=WORKSPACE_ID)
    assert manifest.status == SetupStatus.PENDING_USER
    assert manifest.revision == 0
    assert manifest.first_principal_id is None
    assert manifest.model_check is None
    assert manifest.completed_at is None


# ---------------------------------------------------------------------------
# AC-FR0101-01: first user creation advances to ``pending_model``
# ---------------------------------------------------------------------------


def test_first_user_advances_to_pending_model(workspace: Path):
    """AC-FR0101-01: creating the first user advances status to ``pending_model``."""
    # AC-FR0101-01
    manifest = read_manifest(workspace, workspace_id=WORKSPACE_ID)
    updated = manifest.advance_to_pending_model(
        first_principal_id="prin_alpha",
        expected_revision=0,
    )
    write_manifest(workspace, updated)
    reread = read_manifest(workspace, workspace_id=WORKSPACE_ID)
    assert reread.status == SetupStatus.PENDING_MODEL
    assert reread.first_principal_id == "prin_alpha"
    assert reread.revision == 1


def test_first_user_cas_rejects_stale_revision(workspace: Path):
    """AC-FR0101-01: CAS rejects a stale ``expected_revision``."""
    # AC-FR0101-01
    manifest = read_manifest(workspace, workspace_id=WORKSPACE_ID)
    manifest = manifest.advance_to_pending_model(
        first_principal_id="prin_alpha",
        expected_revision=0,
    )
    write_manifest(workspace, manifest)
    reread = read_manifest(workspace, workspace_id=WORKSPACE_ID)
    with pytest.raises(SetupStateMismatch):
        reread.advance_to_pending_model(
            first_principal_id="prin_beta",
            expected_revision=0,
        )


# ---------------------------------------------------------------------------
# AC-FR0301-01: completion requires first user + passed model probe
# ---------------------------------------------------------------------------


def test_complete_requires_passed_model_check(workspace: Path):
    """AC-FR0301-01: completion requires ``model_check.state == passed``."""
    # AC-FR0301-01
    manifest = read_manifest(workspace, workspace_id=WORKSPACE_ID)
    manifest = manifest.advance_to_pending_model(
        first_principal_id="prin_alpha",
        expected_revision=0,
    )
    write_manifest(workspace, manifest)
    reread = read_manifest(workspace, workspace_id=WORKSPACE_ID)
    with pytest.raises(SetupStateError, match="model_check"):
        reread.complete(
            model_check_state="failed",
            model_check_id="chk_1",
            model_check_revision=1,
            model_id=None,
            diagnosis=None,
            observed_at="2026-07-24T00:00:00Z",
            expected_revision=1,
        )


def test_complete_succeeds_with_passed_model(workspace: Path):
    """AC-FR0301-01: completion succeeds when model probe passed."""
    # AC-FR0301-01
    manifest = read_manifest(workspace, workspace_id=WORKSPACE_ID)
    manifest = manifest.advance_to_pending_model(
        first_principal_id="prin_alpha",
        expected_revision=0,
    )
    write_manifest(workspace, manifest)
    reread = read_manifest(workspace, workspace_id=WORKSPACE_ID)
    completed = reread.complete(
        model_check_state="passed",
        model_check_id="chk_1",
        model_check_revision=1,
        model_id="minimax/m2",
        diagnosis=None,
        observed_at="2026-07-24T00:00:00Z",
        expected_revision=1,
    )
    write_manifest(workspace, completed)
    final = read_manifest(workspace, workspace_id=WORKSPACE_ID)
    assert final.status == SetupStatus.COMPLETE
    # AC-FR0301-01: completion stamps timestamp and model check
    assert final.completed_at is not None
    assert final.model_check is not None
    assert final.model_check.state == "passed"
    assert final.model_check.model_id == "minimax/m2"
    assert final.revision == 2


# ---------------------------------------------------------------------------
# AC-FR0301-02: restart recovery preserves manifest
# ---------------------------------------------------------------------------


def test_manifest_survives_restart(workspace: Path):
    """AC-FR0301-02: manifest persists across a simulated restart."""
    # AC-FR0301-02
    manifest = read_manifest(workspace, workspace_id=WORKSPACE_ID)
    manifest = manifest.advance_to_pending_model(
        first_principal_id="prin_alpha",
        expected_revision=0,
    )
    write_manifest(workspace, manifest)
    before = read_manifest(workspace, workspace_id=WORKSPACE_ID)
    # Simulate restart: re-read from disk.
    after = read_manifest(workspace, workspace_id=WORKSPACE_ID)
    assert before.status == after.status
    assert before.revision == after.revision
    assert before.first_principal_id == after.first_principal_id


# ---------------------------------------------------------------------------
# AC-FR0001-02: fail closed on corruption / unknown schema / workspace mismatch
# ---------------------------------------------------------------------------


def test_corrupt_manifest_fails_closed(workspace: Path):
    """AC-FR0001-02: a corrupt manifest file raises rather than faking complete."""
    # AC-FR0001-02
    state_path = workspace / ".louke" / "web-setup-state.json"
    state_path.write_text("{ broken json", encoding="utf-8")
    with pytest.raises(SetupStateError):
        read_manifest(workspace, workspace_id=WORKSPACE_ID)


def test_unknown_schema_version_fails_closed(workspace: Path):
    """AC-FR0001-02: a manifest with unknown schema version fails closed."""
    # AC-FR0001-02
    state_path = workspace / ".louke" / "web-setup-state.json"
    state_path.write_text(
        json.dumps({"version": 99, "workspace_id": WORKSPACE_ID, "status": "complete"}),
        encoding="utf-8",
    )
    with pytest.raises(SetupStateError, match="version"):
        read_manifest(workspace, workspace_id=WORKSPACE_ID)


def test_workspace_id_mismatch_fails_closed(workspace: Path):
    """AC-FR0001-02: manifest with wrong workspace_id fails closed."""
    # AC-FR0001-02
    state_path = workspace / ".louke" / "web-setup-state.json"
    state_path.write_text(
        json.dumps(
            {
                "version": 2,
                "workspace_id": "ws_other",
                "status": "pending_user",
                "revision": 0,
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(SetupStateError, match="workspace"):
        read_manifest(workspace, workspace_id=WORKSPACE_ID)


# ---------------------------------------------------------------------------
# AC-FR0101-02: idempotent first-user creation
# ---------------------------------------------------------------------------


def test_first_user_idempotent_same_principal(workspace: Path):
    """AC-FR0101-02: re-advancing with same principal returns same result."""
    # AC-FR0101-02
    manifest = read_manifest(workspace, workspace_id=WORKSPACE_ID)
    first = manifest.advance_to_pending_model(
        first_principal_id="prin_alpha",
        expected_revision=0,
    )
    write_manifest(workspace, first)
    reread = read_manifest(workspace, workspace_id=WORKSPACE_ID)
    # Re-advancing with the same principal at the same revision is a no-op.
    second = reread.advance_to_pending_model(
        first_principal_id="prin_alpha",
        expected_revision=1,
    )
    assert second.first_principal_id == first.first_principal_id
    assert second.revision == first.revision


def test_first_user_conflict_on_different_principal(workspace: Path):
    """AC-FR0101-02: advancing with a different principal raises conflict."""
    # AC-FR0101-02
    manifest = read_manifest(workspace, workspace_id=WORKSPACE_ID)
    manifest = manifest.advance_to_pending_model(
        first_principal_id="prin_alpha",
        expected_revision=0,
    )
    write_manifest(workspace, manifest)
    reread = read_manifest(workspace, workspace_id=WORKSPACE_ID)
    with pytest.raises(SetupStateError, match="principal"):
        reread.advance_to_pending_model(
            first_principal_id="prin_beta",
            expected_revision=1,
        )


# ---------------------------------------------------------------------------
# AC-NFR0001-01: v1 migration
# ---------------------------------------------------------------------------


def test_migrate_v1_with_user_but_no_model_probe_becomes_pending_model(
    workspace: Path,
):
    """AC-NFR0001-01: v1 state with user but no probe evidence → ``pending_model``."""
    # AC-NFR0001-01
    v1_state = {
        "version": 1,
        "current_step": "dependencies",
        "completed_steps": ["identity", "repository"],
        "selections": {},
        "blocking_items": [],
    }
    migrated = migrate_v1_state(v1_state, first_principal_id="prin_alpha")
    assert migrated["version"] == 2
    assert migrated["status"] == SetupStatus.PENDING_MODEL
    assert migrated["first_principal_id"] == "prin_alpha"
    assert migrated["model_check"] is None
    assert migrated["completed_at"] is None


def test_migrate_v1_no_user_becomes_pending_user(workspace: Path):
    """AC-NFR0001-01: v1 state with no user → ``pending_user``."""
    # AC-NFR0001-01
    v1_state = {
        "version": 1,
        "current_step": "identity",
        "completed_steps": [],
        "selections": {},
        "blocking_items": [],
    }
    migrated = migrate_v1_state(v1_state, first_principal_id=None)
    assert migrated["version"] == 2
    assert migrated["status"] == SetupStatus.PENDING_USER
    assert migrated["first_principal_id"] is None


# ---------------------------------------------------------------------------
# AC-FR0301-01: completion CAS fails closed on write failure
# ---------------------------------------------------------------------------


def test_complete_cas_rejects_stale_revision(workspace: Path):
    """AC-FR0301-02: completing with stale revision raises ``SetupStateMismatch``."""
    # AC-FR0301-02
    manifest = read_manifest(workspace, workspace_id=WORKSPACE_ID)
    manifest = manifest.advance_to_pending_model(
        first_principal_id="prin_alpha",
        expected_revision=0,
    )
    write_manifest(workspace, manifest)
    reread = read_manifest(workspace, workspace_id=WORKSPACE_ID)
    with pytest.raises(SetupStateMismatch):
        reread.complete(
            model_check_state="passed",
            model_check_id="chk_1",
            model_check_revision=1,
            model_id="minimax/m2",
            diagnosis=None,
            observed_at="2026-07-24T00:00:00Z",
            expected_revision=0,
        )


# ---------------------------------------------------------------------------
# SetupStatus enum contract
# ---------------------------------------------------------------------------


def test_setup_status_has_three_states():
    """AC-FR0101-01: manifest states are exactly three."""
    assert SetupStatus.PENDING_USER == "pending_user"
    assert SetupStatus.PENDING_MODEL == "pending_model"
    assert SetupStatus.COMPLETE == "complete"
    assert len(SetupStatus) == 3


def test_manifest_is_complete_only_when_status_complete(workspace: Path):
    """AC-FR0001-02: only ``complete`` status means setup is done."""
    # AC-FR0001-02
    manifest = read_manifest(workspace, workspace_id=WORKSPACE_ID)
    assert not manifest.is_complete
    manifest = manifest.advance_to_pending_model(
        first_principal_id="prin_alpha",
        expected_revision=0,
    )
    assert not manifest.is_complete
    manifest = manifest.complete(
        model_check_state="passed",
        model_check_id="chk_1",
        model_check_revision=1,
        model_id="minimax/m2",
        diagnosis=None,
        observed_at="2026-07-24T00:00:00Z",
        expected_revision=1,
    )
    assert manifest.is_complete
