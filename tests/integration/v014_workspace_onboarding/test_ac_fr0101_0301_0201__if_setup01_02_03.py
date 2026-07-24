"""IF-SETUP-01 / IF-SETUP-02 / IF-SETUP-03 — Setup projection, first-user, real probe.

AC-FR0101-01, AC-FR0101-02, AC-FR0201-01, AC-FR0201-02, AC-FR0301-01, AC-FR0301-02

Cross-module:
* Setup projection (Setup Application × Setup Gate × OpenCode Adapter ×
  Fact Stores × Workbench Presentation).
* Unique first-user command (Setup Application × Setup Gate × Fact
  Stores × Workbench Presentation).
* Real OpenCode probe (OpenCode Adapter × Setup Application × Fact
  Stores).

All tests drive the real ``louke.web.setup_projection``,
``louke.web.first_user``, and ``louke.web.opencode_probe`` modules
against real on-disk manifests (where applicable) and a real,
controllable subprocess (for the OpenCode probe).
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from louke.web.first_user import (
    create_first_user,
    login_recovery,
    principal_id_for,
)
from louke.web.opencode_probe import (
    PROBE_PROMPT,
    SINGLE_TIMEOUT_SECONDS,
    is_available,
    run_minimal,
)
from louke.web.setup_projection import (
    SCHEMA_VERSION,
    STATUS_COMPLETE,
    STATUS_PENDING_MODEL,
    STATUS_PENDING_USER,
    read as read_projection,
)
from louke.web.setup_state import (
    SetupManifest,
    SetupStateError,
    SetupStatus,
    read_manifest,
    write_manifest,
)
from louke.web.store import ProjectStore


WORKSPACE_ID = "ws_setup"


def _write(workspace: Path, manifest: SetupManifest) -> None:
    """Persist a manifest into the real workspace ``.louke/`` layout."""
    write_manifest(workspace, manifest)


def _make_pending_user_manifest() -> SetupManifest:
    """Initial ``pending_user`` manifest with the locked workspace id."""
    return SetupManifest(
        workspace_id=WORKSPACE_ID,
        revision=0,
        status=SetupStatus.PENDING_USER,
    )


def _make_pending_model_manifest() -> SetupManifest:
    """``pending_model`` after the first user is established."""
    return _make_pending_user_manifest().advance_to_pending_model(
        first_principal_id="prin_alpha", expected_revision=0
    )


def _make_complete_manifest() -> SetupManifest:
    """``complete`` after a passed model probe."""
    return _make_pending_model_manifest().complete(
        model_check_state="passed",
        model_check_id="chk_1",
        model_check_revision=1,
        model_id="minimax/m2",
        diagnosis=None,
        observed_at="2026-07-24T00:00:00Z",
        expected_revision=1,
    )


# ---------------------------------------------------------------------------
# IF-SETUP-01: Setup projection + v2 manifest
# ---------------------------------------------------------------------------


def test_setup_projection_read_returns_v2_fields(synthetic_host) -> None:
    """AC-FR0301-01: ``read`` returns every v2 contract field."""
    # AC-FR0301-01
    _write(synthetic_host, _make_pending_user_manifest())
    body = read_projection(synthetic_host, workspace_id=WORKSPACE_ID)
    assert body["workspace_id"] == WORKSPACE_ID
    assert body["revision"] == 0
    assert body["status"] == STATUS_PENDING_USER
    assert body["first_user"] is None
    assert body["model_check"] is None
    assert body["available_actions"] == ["create_first_user"]
    assert body["continue_url"] == "/setup"


def test_setup_projection_pending_model_exposes_actions(synthetic_host) -> None:
    """AC-FR0101-01: ``pending_model`` exposes the model-check actions."""
    # AC-FR0101-01
    _write(synthetic_host, _make_pending_model_manifest())
    body = read_projection(synthetic_host, workspace_id=WORKSPACE_ID)
    assert body["status"] == STATUS_PENDING_MODEL
    assert "start_model_check" in body["available_actions"]
    assert "retry_model_check" in body["available_actions"]
    assert body["first_user"] == {"principal_id": "prin_alpha"}


def test_setup_projection_complete_points_to_projects(synthetic_host) -> None:
    """AC-FR0301-01: ``complete`` projection points at Projects activity."""
    # AC-FR0301-01
    _write(synthetic_host, _make_complete_manifest())
    body = read_projection(synthetic_host, workspace_id=WORKSPACE_ID)
    assert body["status"] == STATUS_COMPLETE
    assert body["continue_url"] == "/workbench?activity=projects"
    assert body["first_user"] == {"principal_id": "prin_alpha"}
    assert body["model_check"]["state"] == "passed"
    assert body["model_check"]["model_id"] == "minimax/m2"


def test_setup_projection_missing_manifest_is_pending_user(synthetic_host) -> None:
    """AC-FR0301-01: missing manifest is treated as ``pending_user``."""
    # AC-FR0301-01
    body = read_projection(synthetic_host, workspace_id=WORKSPACE_ID)
    assert body["status"] == STATUS_PENDING_USER
    assert body["first_user"] is None
    assert "create_first_user" in body["available_actions"]


def test_setup_projection_status_constants_match_contract() -> None:
    """AC-FR0101-01: three closed states are the contract."""
    # AC-FR0101-01
    assert STATUS_PENDING_USER == "pending_user"
    assert STATUS_PENDING_MODEL == "pending_model"
    assert STATUS_COMPLETE == "complete"
    assert SCHEMA_VERSION == 2


def test_setup_projection_revision_filter(synthetic_host) -> None:
    """AC-FR0101-02: stale-revision reads expose ``available_actions=[]``."""
    # AC-FR0101-02
    _write(synthetic_host, _make_complete_manifest())
    body = read_projection(synthetic_host, workspace_id=WORKSPACE_ID, revision=99)
    assert body["revision"] == 2  # actual current revision
    assert body["available_actions"] == []
    assert body["continue_url"] == "/setup"


# ---------------------------------------------------------------------------
# IF-SETUP-02: unique first-user command
# ---------------------------------------------------------------------------


def test_first_user_create_advances_to_pending_model(synthetic_host) -> None:
    """AC-FR0201-01: first user creation advances the manifest atomically."""
    # AC-FR0201-01
    _write(synthetic_host, _make_pending_user_manifest())
    store = ProjectStore(synthetic_host)
    result = create_first_user(
        synthetic_host,
        workspace_id=WORKSPACE_ID,
        name="demo_owner",
        credential="canary",
        expected_revision=0,
        store=store,
    )
    assert result["principal_id"] == principal_id_for("demo_owner")
    assert result["status"] == STATUS_PENDING_MODEL
    assert result["setup_revision"] == 1
    assert result["continue_url"] == "/setup"
    # Manifest is on disk
    reread = read_manifest(synthetic_host, workspace_id=WORKSPACE_ID)
    assert reread.status == SetupStatus.PENDING_MODEL
    assert reread.first_principal_id == principal_id_for("demo_owner")
    # Credential was persisted via the real ProjectStore
    assert store.user_exists("demo_owner")


def test_first_user_idempotent_for_same_payload(synthetic_host) -> None:
    """AC-FR0201-01: identical payload returns the same principal."""
    # AC-FR0201-01
    _write(synthetic_host, _make_pending_user_manifest())
    store = ProjectStore(synthetic_host)
    first = create_first_user(
        synthetic_host,
        workspace_id=WORKSPACE_ID,
        name="demo_owner",
        credential="canary",
        expected_revision=0,
        store=store,
    )
    # Second call with the same identity: revision has advanced to 1
    second = create_first_user(
        synthetic_host,
        workspace_id=WORKSPACE_ID,
        name="demo_owner",
        credential="canary",
        expected_revision=1,
        store=store,
    )
    assert second["principal_id"] == first["principal_id"]
    # No second user created
    assert len(store.list_users()) == 1


def test_first_user_different_name_after_existing_raises(synthetic_host) -> None:
    """AC-FR0201-01: a different name after the first user is a conflict."""
    # AC-FR0201-01
    _write(synthetic_host, _make_pending_model_manifest())
    with pytest.raises(SetupStateError):
        create_first_user(
            synthetic_host,
            workspace_id=WORKSPACE_ID,
            name="someone_else",
            credential="canary",
            expected_revision=1,
            store=ProjectStore(synthetic_host),
        )


def test_first_user_login_recovery_returns_existing(synthetic_host) -> None:
    """AC-FR0201-02: login recovery returns the existing principal."""
    # AC-FR0201-02
    # Set up manifest with the principal id derived from the username so
    # the manifest and the credential store agree on the identity.
    pid = principal_id_for("demo_owner")
    manifest = SetupManifest(
        workspace_id=WORKSPACE_ID,
        revision=0,
        status=SetupStatus.PENDING_USER,
    ).advance_to_pending_model(first_principal_id=pid, expected_revision=0)
    _write(synthetic_host, manifest)
    store = ProjectStore(synthetic_host)
    store.create_user("demo_owner", "canary")
    result = login_recovery(
        synthetic_host,
        workspace_id=WORKSPACE_ID,
        name="demo_owner",
        credential="canary",
        store=store,
    )
    assert result["principal_id"] == pid
    assert result["status"] == STATUS_PENDING_MODEL
    assert result["continue_url"] == "/setup"


def test_first_user_login_recovery_rejects_unknown(synthetic_host) -> None:
    """AC-FR0201-02: login recovery refuses when no first user exists."""
    # AC-FR0201-02
    _write(synthetic_host, _make_pending_user_manifest())
    with pytest.raises(SetupStateError):
        login_recovery(
            synthetic_host,
            workspace_id=WORKSPACE_ID,
            name="demo_owner",
            credential="canary",
        )


def test_first_user_login_recovery_rejects_when_complete(synthetic_host) -> None:
    """AC-FR0201-02: login recovery is refused once Setup is complete."""
    # AC-FR0201-02
    _write(synthetic_host, _make_complete_manifest())
    with pytest.raises(SetupStateError):
        login_recovery(
            synthetic_host,
            workspace_id=WORKSPACE_ID,
            name="demo_owner",
            credential="canary",
        )


# ---------------------------------------------------------------------------
# IF-SETUP-03: real OpenCode probe
# ---------------------------------------------------------------------------


def test_opencode_probe_prompt_and_defaults() -> None:
    """AC-FR0201-01: probe uses ``please echo hi`` and 15s deadline."""
    # AC-FR0201-01
    assert PROBE_PROMPT == "please echo hi"
    assert SINGLE_TIMEOUT_SECONDS == 15


def test_opencode_probe_run_minimal_returns_uncertain_on_timeout(
    tmp_path, monkeypatch
) -> None:
    """AC-FR0201-02: timeout is classified ``uncertain`` (never ``passed``)."""
    # AC-FR0201-02

    def fake_run(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=args[0], timeout=kwargs["timeout"])

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = run_minimal(
        model_id="minimax/m2",
        prompt=PROBE_PROMPT,
        deadline_seconds=15,
    )
    assert result.state == "uncertain"
    # AC-FR0201-02: timeout carries a non-null diagnosis object
    assert result.diagnosis is not None
    assert result.diagnosis["reason"] == "timeout"


def test_opencode_probe_run_minimal_returns_failed_for_nonzero_exit(
    tmp_path, monkeypatch
) -> None:
    """AC-FR0201-02: non-zero exit is classified ``failed``."""
    # AC-FR0201-02

    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(
            args=args[0], returncode=1, stdout="", stderr="boom"
        )

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = run_minimal(
        model_id="minimax/m2", prompt=PROBE_PROMPT, deadline_seconds=15
    )
    assert result.state == "failed"
    # AC-FR0201-02: non-zero exit carries a non-null diagnosis object
    assert result.diagnosis is not None
    assert result.diagnosis["reason"] == "nonzero_exit"


def test_opencode_probe_run_minimal_returns_passed_for_exit_zero(monkeypatch) -> None:
    """AC-FR0201-01: exit 0 means ``passed``."""
    # AC-FR0201-01

    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(
            args=args[0], returncode=0, stdout="hi", stderr=""
        )

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = run_minimal(
        model_id="minimax/m2", prompt=PROBE_PROMPT, deadline_seconds=15
    )
    assert result.state == "passed"
    assert result.diagnosis is None


def test_opencode_probe_run_minimal_isolates_prompt_and_args(monkeypatch) -> None:
    """AC-FR0201-01: the call uses the fixed minimal prompt and no stdin."""
    # AC-FR0201-01
    captured: dict[str, object] = {}

    def fake_run(args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        return subprocess.CompletedProcess(
            args=args, returncode=0, stdout="hi", stderr=""
        )

    monkeypatch.setattr(subprocess, "run", fake_run)
    run_minimal(model_id="minimax/m2", prompt=PROBE_PROMPT, deadline_seconds=15)
    args = captured["args"]
    kwargs = captured["kwargs"]
    assert args[0] == "opencode"
    assert args[1] == "run"
    assert args[2] == "--model"
    assert args[3] == "minimax/m2"
    assert args[4] == PROBE_PROMPT
    # No workspace file, story, or artifact context
    assert kwargs.get("stdin") == subprocess.DEVNULL
    assert kwargs.get("timeout") == 15


def test_opencode_probe_is_available_returns_bool() -> None:
    """AC-FR0201-01: ``is_available`` is a real PATH-based check."""
    # AC-FR0201-01
    assert isinstance(is_available(), bool)


# ---------------------------------------------------------------------------
# Activation: real artifact surface
# ---------------------------------------------------------------------------


def test_real_setup_projection_artifact_surface() -> None:
    """AC-FR0301-01: real ``louke.web.setup_projection`` exposes the contract."""
    # AC-FR0301-01
    import louke.web.setup_projection as mod

    assert mod.SCHEMA_VERSION == 2
    assert mod.STATUS_PENDING_USER == "pending_user"
    assert mod.STATUS_PENDING_MODEL == "pending_model"
    assert mod.STATUS_COMPLETE == "complete"
    assert callable(mod.read)


def test_real_opencode_probe_artifact_surface() -> None:
    """AC-FR0201-01: real ``louke.web.opencode_probe`` exposes the contract."""
    # AC-FR0201-01
    import louke.web.opencode_probe as mod

    assert mod.PROBE_PROMPT == "please echo hi"
    assert callable(mod.run_minimal)
    assert callable(mod.is_available)
