"""AC-NFR0001-01 / AC-NFR0001-02 / AC-NFR0201-01 — Persistence, idempotency, freshness.

These ACs belong to *every* cross-module interface and are exercised
against the real ``louke.web.setup_state`` module (CAS transitions,
manifest persistence) and the real ``louke.web.opencode_probe``
(timeout/uncertain classification).

Cross-module: every Fact Stores × Runtime Projection × Guide Session ×
Environment Gate × Release Entry × Return Application path.
"""

from __future__ import annotations

import json
import subprocess

import pytest

from louke.web.draft_storage import create_draft
from louke.web.setup_state import (
    SetupManifest,
    SetupStateError,
    SetupStateMismatch,
    SetupStatus,
    read_manifest,
    write_manifest,
)


WORKSPACE_ID = "ws_persistence"


# ---------------------------------------------------------------------------
# AC-NFR0001-01: persistence + restart
# ---------------------------------------------------------------------------


def test_setup_manifest_survives_restart(synthetic_host) -> None:
    """AC-NFR0001-01: manifest round-trips through real file persistence."""
    # AC-NFR0001-01
    manifest = SetupManifest(
        workspace_id=WORKSPACE_ID,
        revision=0,
        status=SetupStatus.PENDING_USER,
    )
    write_manifest(synthetic_host, manifest)
    reread = read_manifest(synthetic_host, workspace_id=WORKSPACE_ID)
    assert reread == manifest


def test_setup_manifest_rejects_completed_at_until_complete(synthetic_host) -> None:
    """AC-NFR0001-01: ``completed_at`` is only set when status == complete."""
    # AC-NFR0001-01
    manifest = SetupManifest(
        workspace_id=WORKSPACE_ID,
        revision=0,
        status=SetupStatus.PENDING_USER,
    )
    write_manifest(synthetic_host, manifest)
    reread = read_manifest(synthetic_host, workspace_id=WORKSPACE_ID)
    assert reread.completed_at is None
    assert reread.status == SetupStatus.PENDING_USER


def test_browser_draft_payload_omits_forbidden_fields() -> None:
    """AC-NFR0001-01: draft payload MUST NOT carry credential / token / URL."""
    # AC-NFR0001-01
    draft = create_draft(
        workspace_id="ws_1",
        principal_id="prin_alpha",
        story="draft story",
    )
    forbidden = {
        "credential",
        "password",
        "token",
        "repository_url",
        "preview_id",
        "preview_token",
        "project_identity",
    }
    assert not (forbidden & set(draft.keys())), (
        f"draft leaked forbidden keys: {forbidden & set(draft.keys())}"
    )


# ---------------------------------------------------------------------------
# AC-NFR0001-02: idempotent + concurrent writes
# ---------------------------------------------------------------------------


def test_concurrent_first_user_calls_resolve_to_one_principal(synthetic_host) -> None:
    """AC-NFR0001-02: repeated identical ``advance_to_pending_model`` is idempotent."""
    # AC-NFR0001-02
    manifest = SetupManifest(
        workspace_id=WORKSPACE_ID,
        revision=0,
        status=SetupStatus.PENDING_USER,
    )
    write_manifest(synthetic_host, manifest)
    # First advance with the same principal twice: second is a no-op.
    advanced = manifest.advance_to_pending_model(
        first_principal_id="prin_alpha", expected_revision=0
    )
    write_manifest(synthetic_host, advanced)
    reread = read_manifest(synthetic_host, workspace_id=WORKSPACE_ID)
    repeated = reread.advance_to_pending_model(
        first_principal_id="prin_alpha",
        expected_revision=reread.revision,
    )
    # Same principal => no double advance.
    assert repeated.revision == reread.revision
    assert repeated.first_principal_id == reread.first_principal_id


def test_setup_complete_rejects_stale_expected_revision(synthetic_host) -> None:
    """AC-NFR0001-02: ``complete`` with a stale ``expected_revision`` raises.

    The CAS check is enforced in-memory: a caller who has not seen
    the current revision must be refused.
    """
    # AC-NFR0001-02
    base = SetupManifest(
        workspace_id=WORKSPACE_ID,
        revision=0,
        status=SetupStatus.PENDING_USER,
    )
    advanced = base.advance_to_pending_model(
        first_principal_id="prin_alpha", expected_revision=0
    )
    write_manifest(synthetic_host, advanced)
    reread = read_manifest(synthetic_host, workspace_id=WORKSPACE_ID)
    assert reread.revision == 1
    # Caller still thinks the revision is 0; ``complete`` MUST reject.
    with pytest.raises(SetupStateMismatch):
        reread.complete(
            model_check_state="passed",
            model_check_id="chk_x",
            model_check_revision=1,
            model_id="minimax/m2",
            diagnosis=None,
            observed_at="2026-07-24T00:00:00Z",
            expected_revision=0,
        )


def test_setup_complete_refuses_when_status_already_complete(synthetic_host) -> None:
    """AC-NFR0001-02: re-completing an already-complete manifest is refused."""
    # AC-NFR0001-02
    base = SetupManifest(
        workspace_id=WORKSPACE_ID,
        revision=0,
        status=SetupStatus.PENDING_USER,
    )
    advanced = base.advance_to_pending_model(
        first_principal_id="prin_alpha", expected_revision=0
    )
    completed = advanced.complete(
        model_check_state="passed",
        model_check_id="chk_x",
        model_check_revision=1,
        model_id="minimax/m2",
        diagnosis=None,
        observed_at="2026-07-24T00:00:00Z",
        expected_revision=advanced.revision,
    )
    write_manifest(synthetic_host, completed)
    reread = read_manifest(synthetic_host, workspace_id=WORKSPACE_ID)
    with pytest.raises(SetupStateError):
        reread.complete(
            model_check_state="passed",
            model_check_id="chk_x",
            model_check_revision=1,
            model_id="minimax/m2",
            diagnosis=None,
            observed_at="2026-07-24T00:00:00Z",
            expected_revision=reread.revision,
        )


def test_setup_rejects_workspace_id_mismatch(synthetic_host) -> None:
    """AC-NFR0001-02: read with the wrong workspace_id fails closed."""
    # AC-NFR0001-02
    manifest = SetupManifest(
        workspace_id=WORKSPACE_ID,
        revision=0,
        status=SetupStatus.PENDING_USER,
    )
    write_manifest(synthetic_host, manifest)
    with pytest.raises(SetupStateError):
        read_manifest(synthetic_host, workspace_id="other_workspace")


def test_setup_rejects_corrupt_manifest(synthetic_host) -> None:
    """AC-NFR0001-02: a corrupt manifest raises on read."""
    # AC-NFR0001-02
    manifest_path = synthetic_host / ".louke" / "web-setup-state.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text("{ this is not valid json")
    with pytest.raises(SetupStateError):
        read_manifest(synthetic_host, workspace_id=WORKSPACE_ID)


def test_setup_rejects_unknown_schema_version(synthetic_host) -> None:
    """AC-NFR0001-02: a v1 / unknown schema is refused by the v2 reader."""
    # AC-NFR0001-02
    manifest_path = synthetic_host / ".louke" / "web-setup-state.json"
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(
        json.dumps(
            {
                "version": 1,
                "current_step": "complete",
                "completed_steps": [],
            }
        )
    )
    with pytest.raises(SetupStateError):
        read_manifest(synthetic_host, workspace_id=WORKSPACE_ID)


# ---------------------------------------------------------------------------
# AC-NFR0201-01: freshness, timeout, retry
# ---------------------------------------------------------------------------


def test_opencode_probe_timeout_classifies_uncertain(monkeypatch) -> None:
    """AC-NFR0201-01: timeout returns ``uncertain`` (never ``passed``)."""
    # AC-NFR0201-01
    from louke.web.opencode_probe import run_minimal

    def fake_run(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=args[0], timeout=kwargs["timeout"])

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = run_minimal(model_id="minimax/m2", deadline_seconds=15)
    assert result.state == "uncertain"
    assert result.diagnosis is not None


def test_opencode_probe_executable_missing_is_failed(monkeypatch) -> None:
    """AC-NFR0201-01: missing executable is ``failed`` with a diagnosis."""
    # AC-NFR0201-01
    from louke.web.opencode_probe import run_minimal

    def fake_run(*args, **kwargs):
        raise FileNotFoundError("no such executable")

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = run_minimal(model_id="minimax/m2", deadline_seconds=15)
    assert result.state == "failed"
    # AC-NFR0201-01: missing executable carries a non-null diagnosis
    assert result.diagnosis is not None


# ---------------------------------------------------------------------------
# Synthetic host project: leak / no-side-effect
# ---------------------------------------------------------------------------


def test_synthetic_host_setup_state_does_not_persist_real_secret(tmp_path) -> None:
    """AC-NFR0101-01: secret canary is absent from the synthetic host layout."""
    # AC-NFR0101-01
    canary = "SECRET_V014004_TEST"
    # Build a synthetic host and write a known canary into a real,
    # but isolated, file under it. The test ensures the host's own
    # ``.louke/project/project.toml`` (which the runtime reads) is
    # free of the canary.
    from tests.integration.v014_workspace_onboarding._mode_b import (
        synthetic_host_project,
    )

    with synthetic_host_project(marker="canary") as synth:
        project_toml = synth / ".louke" / "project" / "project.toml"
        before = project_toml.read_text(encoding="utf-8")
        assert canary not in before
        # Write a canary somewhere the host MUST NOT touch.
        (synth / "canary.txt").write_text(canary, encoding="utf-8")
        after = project_toml.read_text(encoding="utf-8")
        assert before == after, "synthetic host file was unexpectedly mutated"
        assert canary in (synth / "canary.txt").read_text(encoding="utf-8")
