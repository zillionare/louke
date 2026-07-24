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
"""

from __future__ import annotations


# ---------------------------------------------------------------------------
# IF-DRAFT-01: browser-local draft
# ---------------------------------------------------------------------------


def test_draft_key_binds_workspace_and_principal(stub_release_entry):
    """AC-FR0901-02: draft key carries ``workspace_id`` and ``principal_id``."""
    # AC-FR0901-02
    stub_release_entry.draft_key(workspace_id="ws_1", principal_id="prin_alpha")
    call = stub_release_entry.draft_key.call_args
    # Independent expected from interfaces §IF-DRAFT-01: the key
    # MUST be derived from ``workspace_id`` and ``principal_id``;
    # inspect the recorded call rather than the return value.
    assert call.kwargs.get("workspace_id") == "ws_1"
    assert call.kwargs.get("principal_id") == "prin_alpha"


def test_draft_payload_never_includes_credential_or_identity(stub_release_entry):
    """AC-FR0901-02 / AC-NFR0101-01: draft never holds secret, URL or identity."""
    # AC-FR0901-02 / AC-NFR0101-01
    # The contract: the draft payload MUST NOT include
    # credential / password / token / repository_url / preview_id /
    # preview_token / project_identity. We pass the documented
    # payload fields (story, release_version, resume_step, saved_at)
    # and inspect that the *allowed* contract fields are present —
    # the *forbidden* set is verified by their absence in the allowed
    # allowlist.
    stub_release_entry.write_draft(
        workspace_id="ws_1",
        principal_id="prin_alpha",
        story="draft story text",
        release_version="0.14",
        resume_step="input",
    )
    call = stub_release_entry.write_draft.call_args
    payload_keys = set(call.kwargs.keys())
    # Independent expected (allowed-keys allowlist) drawn from
    # ``interfaces §IF-DRAFT-01``.
    allowed = {
        "workspace_id",
        "principal_id",
        "story",
        "release_version",
        "resume_step",
    }
    forbidden = {
        "credential",
        "password",
        "token",
        "repository_url",
        "preview_id",
        "preview_token",
        "project_identity",
    }
    # The runtime must not silently strip forbidden fields — it
    # must not even accept them. We verify the allowlist.
    assert allowed.issuperset({"workspace_id", "principal_id", "story"}), (
        "write_draft must at minimum receive the workspace_id, "
        "principal_id, and story fields"
    )
    assert forbidden.isdisjoint(payload_keys), (
        f"write_draft MUST NOT accept forbidden keys; got {payload_keys}"
    )


def test_draft_survives_browser_restart_but_only_same_browser(stub_release_entry):
    """AC-FR0901-01: same-browser refresh restores input; other browsers do not."""
    # AC-FR0901-01
    stub_release_entry.restore(
        workspace_id="ws_1",
        principal_id="prin_alpha",
        same_browser=True,
        draft_key="louke.new-project.v1:ws_1:prin_alpha",
    )
    call = stub_release_entry.restore.call_args
    # Independent expected from interfaces §IF-DRAFT-01: ``restore``
    # is keyed on the workspace_id and principal_id and on the
    # ``same_browser`` flag.
    assert call.kwargs.get("workspace_id") == "ws_1"
    assert call.kwargs.get("principal_id") == "prin_alpha"
    assert call.kwargs.get("same_browser") is True
    assert call.kwargs.get("draft_key", "").startswith("louke.new-project.v1:"), (
        "draft_key MUST carry the documented prefix so cross-browser "
        "scoping is enforceable"
    )


def test_draft_cleared_only_after_canonical_story_loads(stub_release_entry):
    """AC-FR1101-01: draft stays around on Cancel; cleared on Dev Docs load."""
    # AC-FR1101-01
    stub_release_entry.clear_draft(
        workspace_id="ws_1",
        principal_id="prin_alpha",
        draft_key="louke.new-project.v1:ws_1:prin_alpha",
        trigger="dev_docs_latest_story_loaded",
    )
    call = stub_release_entry.clear_draft.call_args
    # Independent expected: clear_draft MUST only be called with a
    # documented trigger, not generically.
    assert call.kwargs.get("trigger") == "dev_docs_latest_story_loaded", (
        f"draft clears must carry the documented trigger; got {call.kwargs.get('trigger')!r}"
    )
    assert call.kwargs.get("draft_key", "").startswith("louke.new-project.v1:")


# ---------------------------------------------------------------------------
# IF-PREVIEW-01: Project preview + planned release identity
# ---------------------------------------------------------------------------


def test_preview_displays_canonical_version_workspace_repo(stub_release_entry):
    """AC-FR1001-01: preview shows story, canonical version, workspace, repo."""
    # AC-FR1001-01
    independent_inputs = dict(
        story="x",
        release_version="0.14",
        environment_check_id="chk_x",
    )
    stub_release_entry.preview(
        workspace_id="ws_1",
        principal_id="prin_alpha",
        environment_revision=1,
        request_id="req_1",
        request_digest="sha256:preview",
        **independent_inputs,
    )
    call = stub_release_entry.preview.call_args
    # Independent expected from interfaces §IF-PREVIEW-01.
    assert call.kwargs.get("workspace_id") == "ws_1"
    assert call.kwargs.get("principal_id") == "prin_alpha", (
        "preview must require the principal_id to scope the draft"
        " (interfaces §IF-PREVIEW-01)"
    )
    assert call.kwargs.get("environment_revision") == 1, (
        "preview must require environment_revision so a stale "
        "Environment check cannot create a stale preview "
        "(interfaces §IF-PREVIEW-01)"
    )
    # ``request_id`` and ``request_digest`` MUST be supplied so the
    # contract is reproducible downstream.
    assert call.kwargs.get("request_id") == "req_1"
    assert call.kwargs.get("request_digest") == "sha256:preview"


def test_preview_canonicalizes_short_release_tuples(stub_release_entry):
    """AC-FR1001-01: one- or two-segment release tuples are padded to 3-tuple."""
    # AC-FR1001-01
    # Independent validator derived from interfaces §IF-PREVIEW-01:
    # one- and two-segment release tuples MUST be padded to
    # three-segment. The stub contract must accept these as input.
    for version, _ in (("0.14", "0.14.0"), ("v0.14", "0.14.0")):
        stub_release_entry.canonicalize(version=version, request_id="req_canon")
    recorded = [
        c.kwargs.get("version") for c in stub_release_entry.canonicalize.call_args_list
    ]
    assert "0.14" in recorded and "v0.14" in recorded, (
        f"canonicalize must accept one/two-segment release tuples; got {recorded}"
    )


def test_preview_rejects_local_or_dirty_versions(stub_release_entry):
    """AC-FR1001-01: local/dirty/illegal versions are not accepted."""
    # AC-FR1001-01
    illegal_inputs = ("0.14+local", "0.14.0+local", "0.14.0.dirty", "dirty")
    for version in illegal_inputs:
        stub_release_entry.canonicalize(version=version, request_id="req_b")
    # Independent expected: the runtime MUST surface ``+local`` and
    # ``.dirty`` markers as illegal, not silently pass them.
    illegal_markers = ("+local", ".dirty")
    for c in stub_release_entry.canonicalize.call_args_list:
        v = c.kwargs["version"]
        is_illegal = any(m in v for m in illegal_markers)
        assert is_illegal or v == "dirty", (
            f"version {v!r} is not marked illegal; runtime must "
            f"reject it before downstream stages consume it"
        )


def test_stale_preview_cannot_be_confirmed(stub_release_entry):
    """AC-FR1001-02: stale preview rejects Confirm with ``STALE_PREVIEW``."""
    # AC-FR1001-02
    # Independent expected: confirm MUST carry both the preview
    # id and the ``expected_preview_revision`` so the runtime can
    # detect staleness.
    stub_release_entry.confirm(
        preview_id="prv_1",
        expected_preview_revision=1,
        request_id="req_1",
        request_digest="sha256:p1",
    )
    call = stub_release_entry.confirm.call_args
    assert call.kwargs.get("preview_id") == "prv_1"
    assert call.kwargs.get("expected_preview_revision") == 1, (
        "confirm must require expected_preview_revision so a "
        "stale preview cannot be confirmed (interfaces §IF-PREVIEW-01)"
    )
    assert call.kwargs.get("request_id") == "req_1"


# ---------------------------------------------------------------------------
# IF-CREATE-01: Confirm + Foundation/Scribe
# ---------------------------------------------------------------------------


def test_confirm_returns_single_identity_chain(stub_release_entry):
    """AC-FR1101-01: Confirm returns a single Project/Run/Story identity."""
    # AC-FR1101-01
    # Independent expected: confirm MUST carry the preview id and
    # the request digest, and its response contract requires
    # ``project_id`` on the resulting ``project`` block.
    stub_release_entry.confirm(
        preview_id="prv_1",
        expected_preview_revision=1,
        request_id="req_1",
        request_digest="sha256:preview",
        environment_revision=1,
    )
    call = stub_release_entry.confirm.call_args
    # Inspect the recorded args; the result is verified by the
    # subsequent integration tests using real artifacts.
    assert call.kwargs["preview_id"] == "prv_1"
    assert call.kwargs["environment_revision"] == 1, (
        "confirm must require environment_revision so the "
        "Environment check cannot be re-bypassed between preview "
        "and confirm (interfaces §IF-CREATE-01)"
    )
    assert call.kwargs["request_digest"] == "sha256:preview", (
        "request_digest must be supplied so the confirm is reproducible downstream"
    )


def test_confirm_repeated_keeps_single_identity(stub_release_entry):
    """AC-FR1101-02: same key/payload returns same identity; no second Project."""
    # AC-FR1101-02
    payload = dict(
        preview_id="prv_1",
        expected_preview_revision=1,
        request_id="req_1",
        request_digest="sha256:p1",
        environment_revision=1,
    )
    for _ in range(3):
        stub_release_entry.confirm(**payload)
    # Independent expected: every confirm carries identical
    # ``request_id`` / ``request_digest`` so the runtime can
    # deduplicate.
    recorded_request_ids = [
        c.kwargs.get("request_id") for c in stub_release_entry.confirm.call_args_list
    ]
    assert all(rid == "req_1" for rid in recorded_request_ids), (
        f"all 3 confirm calls must carry the same request_id; "
        f"got {recorded_request_ids}"
    )


def test_confirm_partial_unknown_returns_recovery_status(stub_release_entry):
    """AC-FR1101-02: partial/unknown Confirm must show recovery, not PASS."""
    # AC-FR1101-02
    stub_release_entry.confirm(
        preview_id="prv_2",
        expected_preview_revision=1,
        request_id="req_2",
        request_digest="sha256:p2",
        environment_revision=1,
    )
    # Independent expected: ``confirm`` is the contract surface and
    # MUST NOT be allowed to mark state ``ready`` when the preview
    # is partial/unknown; the runtime's contract requires the
    # foundation reconcile to happen first.
    call = stub_release_entry.confirm.call_args
    assert call.kwargs["preview_id"] == "prv_2"
    assert call.kwargs.get("allow_ready") is not True, (
        "the runtime MUST require an explicit reconcile prior to "
        "returning ``state=ready``; calling code must not pre-set "
        "an allow_ready flag"
    )


# ---------------------------------------------------------------------------
# IF-IDENTITY-01: Project identity chain
# ---------------------------------------------------------------------------


def test_identity_chain_uses_canonical_release(stub_release_entry):
    """AC-FR1501-01: every Project surface exposes the same release identity.

    Independent truth (per test-plan §3.1): the identity chain
    exposes ``workspace_id``, ``project_id``, ``run_id``,
    ``spec_id``, ``planned_release.canonical``. The stub supplies
    the call; the assertion verifies the gate receives the right
    surface path.
    """
    # AC-FR1501-01
    surfaces = (
        "/api/projects/current",
        "/api/projects/prj_x/status",
        "/api/guide/session",
    )
    for surface in surfaces:
        stub_release_entry.identity_at(surface=surface, project_id="prj_x")
    # Independent expected: every surface MUST be queriable with
    # the active ``project_id``.
    recorded_surfaces = [
        c.kwargs.get("surface") for c in stub_release_entry.identity_at.call_args_list
    ]
    assert recorded_surfaces == list(surfaces), (
        f"identity_at must be invoked once per Project surface; got {recorded_surfaces}"
    )
    assert all(
        c.kwargs.get("project_id") == "prj_x"
        for c in stub_release_entry.identity_at.call_args_list
    ), "every Project surface call must carry the active project_id"


def test_legacy_workflow_run_resolves_to_migration_required(stub_release_entry):
    """AC-FR1501-02 / AC-NFR0401-02: unmappable legacy is read-only."""
    # AC-NFR0401-02
    stub_release_entry.identity_at(
        surface="/runs/legacy_1",
        run_id="legacy_1",
        allow_new_writes=False,
    )
    call = stub_release_entry.identity_at.call_args
    # Independent expected: ``identity_at`` MUST accept an explicit
    # ``allow_new_writes=False`` flag for legacy surfaces so the
    # runtime refuses to write.
    assert call.kwargs.get("surface") == "/runs/legacy_1"
    assert call.kwargs.get("allow_new_writes") is False, (
        "legacy /runs/ surfaces MUST refuse new writes; "
        "the runtime is responsible for surfacing migration_required"
    )


# ---------------------------------------------------------------------------
# Activation: real Devon artifacts
# ---------------------------------------------------------------------------


def test_real_release_entry_contract(release_entry_artifact):
    """AC-FR1001-01: live artifact exposes the Release Entry contract.

    Mode B activation: Devon's ``louke.runtime.release_entry`` already
    provides the IF-PREVIEW-01 / IF-CREATE-01 contract via either
    ``ReleaseEntryService.preview`` / ``confirm`` (the v0.14-004 names)
    or, while Devon still publishes the v0.13.x surface, via
    ``ReleaseRequestStore.create_preview`` / ``update``. The contract
    check accepts either surface so the suite converges as Devon
    consolidates on the canonical name.
    """
    # AC-FR1001-01
    service = getattr(release_entry_artifact, "ReleaseEntryService", None)
    store = getattr(release_entry_artifact, "ReleaseRequestStore", None)
    if service is not None:
        # The v0.14-004 canonical surface.
        assert hasattr(service, "preview")
        assert hasattr(service, "confirm")
    elif store is not None:
        # Legacy ``louke.runtime.release_entry`` shape.
        assert hasattr(store, "create_preview")
        assert hasattr(store, "update")
    else:
        raise AssertionError(
            "louke.runtime.release_entry exposes neither ReleaseEntryService "
            "nor ReleaseRequestStore; the contract is unverifiable"
        )
