"""IF-DRAFT-01 / IF-PREVIEW-01 / IF-CREATE-01 / IF-IDENTITY-01 — Draft, Preview, Create, Identity.

AC-FR0901-01, AC-FR0901-02, AC-FR1001-01, AC-FR1001-02, AC-FR1101-01, AC-FR1101-02,
AC-FR1501-01, AC-FR1501-02

Cross-module:
* Browser draft (Workbench Presentation × Environment Gate × Release
  Entry).
* Preview (Release Entry × Environment Gate × Project Context × Fact
  Stores × Workbench Presentation).
* Confirm + Foundation/Scribe (Release Entry × Environment Gate ×
  Project Context × Foundation/Scribe × Runtime Projection × Document
  Surface × Fact Stores × Workbench Presentation).
* Project identity chain (Project Context × Release Entry ×
  Foundation/Scribe × Runtime Projection × Document Surface ×
  Compatibility Router × Fact Stores).

Tests drive the real ``louke.web.draft_storage``,
``louke.runtime.release_entry``, ``louke.runtime.foundation_scribe``,
and ``louke.runtime.project_identity`` modules. The release_entry
``ReleaseEntryService`` is exercised against a real
``WorkflowRunStore`` so the contract side-effects (preview_id,
revision, request_digest) are observable.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from louke.runtime.foundation_scribe import dispatch_scribe, reconcile
from louke.runtime.project_identity import build_identity
from louke.runtime.release_entry import ReleaseEntryService
from louke.runtime.store import WorkflowRunStore
from louke.web.draft_storage import create_draft, draft_key


# ---------------------------------------------------------------------------
# IF-DRAFT-01: browser-local draft
# ---------------------------------------------------------------------------


def test_draft_key_is_browser_storage_shape() -> None:
    """AC-FR0901-02: draft key carries ``workspace_id`` and ``principal_id``."""
    # AC-FR0901-02
    key = draft_key(workspace_id="ws_1", principal_id="prin_alpha")
    # The contract fixes the key shape at
    # ``louke.new-project.v1:<workspace_id>:<principal_id>`` so
    # browser storage scoping is enforceable per-browser /
    # per-principal.
    assert key == "louke.new-project.v1:ws_1:prin_alpha", (
        f"draft key MUST match the contract shape "
        f"``louke.new-project.v1:<workspace>:<principal>``; got {key!r}"
    )


def test_draft_payload_matches_contract_shape() -> None:
    """AC-FR0901-02: draft payload exposes the contract fields, no secrets."""
    # AC-FR0901-02
    draft = create_draft(
        workspace_id="ws_1",
        principal_id="prin_alpha",
        story_input="draft story text",
    )
    # Required contract keys.
    assert draft["version"] == 1
    assert draft["story"] == "draft story text"
    assert draft["release_version"] == "" or "release_version" not in draft
    assert draft["resume_step"] in {"input", "preview"}
    assert "saved_at" in draft
    # Forbidden keys: the runtime MUST NOT store credential /
    # token / repository_url / preview_id / preview_token /
    # project_identity on the draft.
    forbidden = {
        "credential",
        "password",
        "token",
        "repository_url",
        "preview_id",
        "preview_token",
        "project_identity",
    }
    leaked = forbidden & set(draft.keys())
    assert not leaked, f"draft payload leaked forbidden keys: {leaked!r}"


def test_draft_key_distinguishes_workspace_and_principal() -> None:
    """AC-FR0901-02: two principals in the same workspace have distinct keys."""
    # AC-FR0901-02
    a = draft_key(workspace_id="ws_1", principal_id="prin_alpha")
    b = draft_key(workspace_id="ws_1", principal_id="prin_beta")
    c = draft_key(workspace_id="ws_2", principal_id="prin_alpha")
    assert a != b, "principal_id must affect the key"
    assert a != c, "workspace_id must affect the key"


# ---------------------------------------------------------------------------
# IF-PREVIEW-01: Project Preview + planned release identity
# ---------------------------------------------------------------------------


@pytest.fixture
def release_entry(tmp_path: Path) -> ReleaseEntryService:
    """A real ``ReleaseEntryService`` against an in-memory SQLite store."""
    store = WorkflowRunStore(tmp_path / "runtime.sqlite3")
    return ReleaseEntryService(
        store,
        foundation=None,  # type: ignore[arg-type]
        workspace_id="ws_1",
    )


def test_preview_returns_canonical_shape(release_entry) -> None:
    """AC-FR1001-01: ``preview`` returns preview_id + revision + request_digest."""
    # AC-FR1001-01
    body = release_entry.preview("draft story", "0.14")
    assert "preview_id" in body
    assert "preview_revision" in body
    assert "request_id" in body
    assert "request_digest" in body
    assert body["workspace_id"] == "ws_1"
    assert body["release"]["canonical"] is not None
    assert body["side_effects"] == []


def test_preview_canonicalizes_short_version(release_entry) -> None:
    """AC-FR1001-01: ``0.14`` becomes a valid 3-segment canonical version.

    The contract requires one- and two-segment release tuples to be
    padded to a 3-tuple canonical PEP440 version. Devon's preview
    currently echoes the input as-is; this test documents the
    expected behaviour so a regression surfaces immediately.
    """
    # AC-FR1001-01
    body = release_entry.preview("x", "0.14")
    canonical = body["release"]["canonical"]
    # Canonical form MUST be a valid 3-segment PEP440 version.
    parts = canonical.split(".")
    assert len(parts) == 3, f"canonical version must be 3 segments; got {canonical}"
    assert all(p.isdigit() for p in parts), (
        f"canonical version segments must be numeric; got {canonical}"
    )


def test_preview_idempotency_replays_same_request(release_entry) -> None:
    """AC-FR1001-01: identical inputs produce an idempotent preview.

    Two consecutive previews with the same story + version produce
    request_digests derived from the deterministic identity, so
    downstream layers can dedupe by digest.
    """
    # AC-FR1001-01
    first = release_entry.preview("same story", "0.14")
    second = release_entry.preview("same story", "0.14")
    assert first["request_digest"] == second["request_digest"]


# ---------------------------------------------------------------------------
# IF-CREATE-01: Foundation/Scribe reconcile
# ---------------------------------------------------------------------------


def test_foundation_scribe_reconcile_returns_status() -> None:
    """AC-FR1101-01: reconcile returns a non-empty foundation status."""
    # AC-FR1101-01
    body = reconcile(
        project_id="prj_x",
        release_identity={"spec_id": "spec_1"},
    )
    assert body["project_id"] == "prj_x"
    assert body["state"] in {"reconciled", "blocked", "uncertain"}


def test_foundation_scribe_dispatch_returns_revision() -> None:
    """AC-FR1101-01: dispatch returns a non-empty story revision."""
    # AC-FR1101-01
    body = dispatch_scribe(project_id="prj_x", spec_id="spec_1")
    assert body["project_id"] == "prj_x"
    assert body["spec_id"] == "spec_1"
    assert body["story_revision"]


# ---------------------------------------------------------------------------
# IF-IDENTITY-01: Project identity chain
# ---------------------------------------------------------------------------


def test_project_identity_carries_canonical_chain_fields() -> None:
    """AC-FR1501-01: identity chain carries every locked field from interfaces §IF-IDENTITY-01."""
    # AC-FR1501-01
    identity = build_identity(
        project_id="prj_x",
        release_identity="rel_1",
        github_project_node_id="ghpn_1",
        request_id="req_1",
        run_id="run_1",
        spec_id="spec_1",
        story_revision="latest",
    )
    # Top-level fields.
    for key in (
        "workspace_id",
        "project_id",
        "request_id",
        "run_id",
        "spec_id",
        "activity_state",
        "identity_revision",
    ):
        assert key in identity, f"identity missing {key!r}"
    # Nested objects (interfaces.md §IF-IDENTITY-01 row 1):
    # planned_release = {canonical, tag, branch}
    # github_project  = {node_id, url} | null
    # story           = {path, revision, digest} | null
    assert "planned_release" in identity
    assert isinstance(identity["planned_release"], dict)
    assert set(identity["planned_release"].keys()) >= {"canonical", "tag", "branch"}
    assert "github_project" in identity
    assert identity["github_project"] is None or set(
        identity["github_project"].keys()
    ) >= {"node_id", "url"}
    assert "story" in identity
    assert identity["story"] is None or set(identity["story"].keys()) >= {
        "path",
        "revision",
        "digest",
    }


def test_project_identity_activity_state_is_valid() -> None:
    """AC-FR1501-02: ``activity_state`` is one of the locked three values."""
    # AC-FR1501-02
    identity = build_identity(project_id="prj_x")
    assert identity["activity_state"] in {"active", "historical", "migration_required"}


# ---------------------------------------------------------------------------
# Activation: real artifact surface
# ---------------------------------------------------------------------------


def test_real_release_entry_service_contract() -> None:
    """AC-FR1001-01: real ``ReleaseEntryService`` exposes ``preview``/``confirm``."""
    # AC-FR1001-01
    import louke.runtime.release_entry as mod

    service_cls = mod.ReleaseEntryService
    assert callable(getattr(service_cls, "preview", None))
    assert callable(getattr(service_cls, "confirm", None))


def test_real_foundation_scribe_surface() -> None:
    """AC-FR1101-01: real ``foundation_scribe`` exposes ``reconcile``/``dispatch_scribe``."""
    # AC-FR1101-01
    import louke.runtime.foundation_scribe as mod

    assert callable(mod.reconcile)
    assert callable(mod.dispatch_scribe)


def test_real_project_identity_surface() -> None:
    """AC-FR1501-01: real ``project_identity`` exposes ``build_identity``."""
    # AC-FR1501-01
    import louke.runtime.project_identity as mod

    assert callable(mod.build_identity)
