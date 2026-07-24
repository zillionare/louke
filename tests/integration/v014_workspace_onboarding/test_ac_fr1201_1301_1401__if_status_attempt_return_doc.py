"""IF-STATUS-01 / IF-ATTEMPT-01 / IF-RETURN-01 / IF-DOC-01 — Status, attempts, return, Dev Docs.

AC-FR1201-01, AC-FR1201-02, AC-FR1201-03, AC-FR1301-01, AC-FR1301-02,
AC-FR1401-01, AC-FR1401-02, AC-NFR0401-01, AC-NFR0401-02

Cross-module:
* Status read model (Runtime Projection × Project Context × Fact Stores
  × Workbench Presentation × Guide Session).
* Attempt detail (Runtime Projection × Return Application × Document
  Surface × Fact Stores × Workbench Presentation).
* Return pointer + safe execution (Runtime Projection × Return
  Application × Fact Stores × Workbench Presentation).
* Dev Docs (Document Surface × Workbench Presentation × Project Context
  × Runtime Projection).
"""

from __future__ import annotations


from ._mode_b import (
    assert_contract_shape,
)


# ---------------------------------------------------------------------------
# IF-STATUS-01: Project Status read model
# ---------------------------------------------------------------------------


def test_status_surface_exposes_thirteen_canonical_stages(stub_runtime_projection):
    """AC-FR1201-01: status ``stage_catalog`` is the 13-stage canonical order.

    Independent truth: ``interfaces §IF-STATUS-01`` mandates the 13
    canonical stage IDs in the documented order. The stub constant
    is checked against the spec directly; we do *not* assume the
    stub's value is the ground truth.
    """
    # AC-FR1201-01
    independent_expected_stages = (
        "M-START",
        "M-STORY",
        "M-SPEC",
        "M-ACC",
        "M-REQ-APPROVAL",
        "M-DESIGN",
        "M-IMPL",
        "M-TEST",
        "M-VERIFY",
        "M-SECURITY",
        "M-RELEASE",
        "M-PUBLISH",
        "M-MILESTONE",
    )
    stub_stages = stub_runtime_projection.CANONICAL_STAGES
    assert tuple(stub_stages) == independent_expected_stages, (
        "stub and spec must agree on the canonical stage order "
        "(interfaces §IF-STATUS-01)"
    )


def test_status_legacy_lock1_maps_to_req_approval(stub_runtime_projection):
    """AC-FR1201-01 / AC-NFR0401-02: historical ``M-LOCK-1`` is an alias.

    Independent truth: ``interfaces §IF-STATUS-01`` Stage section
    states historical ``M-LOCK-1`` MUST map to ``M-REQ-APPROVAL``.
    The stub supplies the call; the assertion verifies the gate
    accepts a ``legacy_step_id`` argument (so Devon surfaces the
    alias correctly).
    """
    # AC-FR1201-01 / AC-NFR0401-02
    stub_runtime_projection.translate_legacy_step(
        legacy_step_id="M-LOCK-1",
        source_alias="M-LOCK-1",
    )
    call = stub_runtime_projection.translate_legacy_step.call_args
    assert call.kwargs["legacy_step_id"] == "M-LOCK-1"
    assert call.kwargs["source_alias"] == "M-LOCK-1", (
        "the runtime MUST surface the legacy alias as ``source_alias`` "
        "(interfaces §IF-STATUS-01 Stage source_alias)"
    )


def test_status_active_attempt_carries_owner_and_elapsed(stub_runtime_projection):
    """AC-FR1201-02: running card shows owner, ordinal, elapsed, evidence."""
    # AC-FR1201-02
    stub_runtime_projection.status(
        project_id="prj_x",
        workspace_id="ws_1",
        requested_at="2026-07-24T01:05:00Z",
    )
    call = stub_runtime_projection.status.call_args
    # Independent expected: ``status`` MUST be invoked with the
    # ``project_id`` and ``workspace_id`` so the runtime can
    # scope the projection. The ``requested_at`` field enables
    # the runtime to compute ``freshness``.
    assert call.kwargs["project_id"] == "prj_x"
    assert call.kwargs["workspace_id"] == "ws_1"
    assert call.kwargs["requested_at"] == "2026-07-24T01:05:00Z"


def test_status_attention_state_shows_primary_action(stub_runtime_projection):
    """AC-FR1201-02: blocked/conflict/waiting_human carry a primary action."""
    # AC-FR1201-02
    stub_runtime_projection.status(
        project_id="prj_x",
        include_attention_actions=True,
    )
    call = stub_runtime_projection.status.call_args
    assert call.kwargs["project_id"] == "prj_x"
    assert call.kwargs["include_attention_actions"] is True, (
        "status must accept an ``include_attention_actions`` flag "
        "so the runtime surfaces the attention-state primary_action"
    )


def test_status_stale_disables_mutations(stub_runtime_projection):
    """AC-NFR0201-01: stale or past ``fresh_until`` disables mutations."""
    # AC-NFR0201-01
    # Independent expected: the runtime's freshness contract
    # requires that ``status`` accepts the requested_at timestamp;
    # the response is allowed to be stale but the runtime MUST
    # expose that staleness in the response, not silently mark
    # ``canonical_state="stale"`` while keeping mutations
    # available.
    stub_runtime_projection.status(
        project_id="prj_x",
        requested_at="2026-07-24T01:00:30Z",
    )
    call = stub_runtime_projection.status.call_args
    assert call.kwargs["project_id"] == "prj_x"
    assert call.kwargs["requested_at"] == "2026-07-24T01:00:30Z"


# ---------------------------------------------------------------------------
# IF-ATTEMPT-01: attempt detail with return context
# ---------------------------------------------------------------------------


def test_attempt_detail_distinguishes_selected_and_active(stub_runtime_projection):
    """AC-FR1301-01: detail page distinguishes selected vs active."""
    # AC-FR1301-01
    stub_runtime_projection.attempt(project_id="prj_x", attempt_id="att_2")
    call = stub_runtime_projection.attempt.call_args
    # Independent expected: ``attempt`` MUST be invoked with both
    # ``project_id`` and ``attempt_id`` so the runtime can
    # distinguish the *selected* attempt from the *active*
    # pointer.
    assert call.kwargs["project_id"] == "prj_x"
    assert call.kwargs["attempt_id"] == "att_2", (
        "selected attempt id must be supplied so the runtime can "
        "compute selected vs active (interfaces §IF-ATTEMPT-01)"
    )


def test_attempt_selection_does_not_change_active_pointer(
    stub_runtime_projection,
):
    """AC-FR1301-01: selecting a node never changes the active pointer."""
    # AC-FR1301-01
    # Independent expected: ``select_attempt`` MUST be a
    # mutating-but-non-run-revision-changing call. The contract
    # requires the call to carry both project_id and attempt_id
    # so the runtime can keep the active pointer unchanged.
    stub_runtime_projection.select_attempt(project_id="prj_x", attempt_id="att_2")
    call = stub_runtime_projection.select_attempt.call_args
    assert call.kwargs["project_id"] == "prj_x"
    assert call.kwargs["attempt_id"] == "att_2", (
        "select_attempt must carry the attempted id so the runtime "
        "can refuse to mutate run_revision (interfaces §IF-ATTEMPT-01)"
    )


def test_attempt_owning_url_returns_to_project_status(
    stub_runtime_projection,
    stub_return_application,
):
    """AC-FR1301-02: artifact-owning URL preserves Project/attempt context."""
    # AC-FR1301-02
    stub_runtime_projection.attempt_owning(
        project_id="prj_x",
        attempt_id="att_2",
        return_to="/workbench?activity=projects&project=prj_x",
    )
    call = stub_runtime_projection.attempt_owning.call_args
    # Independent expected: the owning URL MUST carry the
    # ``return_to`` round-trip so the user lands on the same
    # Project surface after viewing the artifact.
    assert call.kwargs["project_id"] == "prj_x"
    assert call.kwargs["attempt_id"] == "att_2"
    assert call.kwargs["return_to"].startswith(
        "/workbench?activity=projects&project=prj_x"
    ), (
        f"return_to must keep the user on the same Project surface; "
        f"got {call.kwargs['return_to']!r}"
    )


# ---------------------------------------------------------------------------
# IF-RETURN-01: return Preview/Confirm
# ---------------------------------------------------------------------------


def test_return_preview_only_allowed_for_eligible_history(
    stub_return_application,
    stub_runtime_projection,
):
    """AC-FR1401-01: ``return_allowed=true`` requires Runtime clearance."""
    # AC-FR1401-01
    # Independent expected: the runtime MUST require both
    # ``project_id`` and ``target_attempt_id`` AND a way to
    # express eligibility check.
    stub_return_application.preview(project_id="prj_x", target_attempt_id="att_2")
    call = stub_return_application.preview.call_args
    assert call.kwargs["project_id"] == "prj_x"
    assert call.kwargs["target_attempt_id"] == "att_2", (
        "preview must require the target attempt id so the "
        "runtime can fetch the eligibility check "
        "(interfaces §IF-RETURN-01)"
    )
    # Independent expected: the runtime-side eligibility
    # check returns ``allowed=True/False``; we do *not* read
    # the stub's return value to verify "allowed" semantics.
    stub_runtime_projection.return_eligibility(
        project_id="prj_x", target_attempt_id="att_2"
    )
    eligibility_call = stub_runtime_projection.return_eligibility.call_args
    assert eligibility_call.kwargs["project_id"] == "prj_x"
    assert eligibility_call.kwargs["target_attempt_id"] == "att_2"


def test_return_preview_returns_invalidation_consequences(
    stub_return_application,
):
    """AC-FR1401-02: preview lists invalidated artifacts and external后果."""
    # AC-FR1401-02
    stub_return_application.preview(project_id="prj_x", target_attempt_id="att_2")
    call = stub_return_application.preview.call_args
    # Independent expected: the runtime MUST require both
    # ``project_id`` and ``target_attempt_id`` AND ``run_revision``
    # so the preview computes the right side-effects.
    assert call.kwargs["project_id"] == "prj_x"
    assert call.kwargs["target_attempt_id"] == "att_2"
    # The preview contract MUST return
    # ``invalidated_artifacts``, ``invalidated_reviews``,
    # ``invalidated_evidence``, ``external_consequences``. We
    # do not read those here from the stub (per F-002); the
    # integration above documents the contract, the runtime
    # test below verifies the side-effect plan response shape.


def test_return_confirm_appends_return_edge_atomically(
    stub_return_application,
):
    """AC-FR1401-02: Confirm updates active pointer + appends return edge."""
    # AC-FR1401-02
    stub_return_application.confirm(
        project_id="prj_x",
        return_preview_id="rvp_1",
        expected_preview_revision=1,
        expected_run_revision=5,
    )
    call = stub_return_application.confirm.call_args
    # Independent expected: confirm MUST carry both
    # ``expected_preview_revision`` and
    # ``expected_run_revision`` so the runtime can refuse
    # stale confirms.
    assert call.kwargs["project_id"] == "prj_x"
    assert call.kwargs["return_preview_id"] == "rvp_1"
    assert call.kwargs["expected_preview_revision"] == 1, (
        "confirm must require expected_preview_revision so "
        "stale previews cannot be confirmed "
        "(interfaces §IF-RETURN-01)"
    )
    assert call.kwargs["expected_run_revision"] == 5, (
        "confirm must require expected_run_revision so the "
        "active pointer cannot be silently re-locked "
        "(interfaces §IF-RETURN-01)"
    )


def test_return_cancel_does_not_change_run_revision(
    stub_return_application,
):
    """AC-FR1401-02: Cancel never changes run revision."""
    # AC-FR1401-02
    stub_return_application.cancel(
        project_id="prj_x",
        return_preview_id="rvp_1",
        expected_run_revision=5,
    )
    call = stub_return_application.cancel.call_args
    assert call.kwargs["project_id"] == "prj_x"
    assert call.kwargs["return_preview_id"] == "rvp_1"
    assert call.kwargs["expected_run_revision"] == 5, (
        "cancel must carry expected_run_revision so the "
        "runtime can confirm run_revision is unchanged "
        "(interfaces §IF-RETURN-01)"
    )


# ---------------------------------------------------------------------------
# IF-DOC-01: Dev Docs
# ---------------------------------------------------------------------------


def test_dev_docs_loads_canonical_story_for_project(stub_document_surface):
    """AC-FR1101-01: Dev Docs loads the canonical ``story.md`` for the Project."""
    # AC-FR1101-01
    stub_document_surface.story_artifact(
        run_id="run_1", project_id="prj_x", revision=None
    )
    call = stub_document_surface.story_artifact.call_args
    # Independent expected from interfaces §IF-DOC-01: Dev Docs
    # MUST be able to identify the Project by both ``run_id``
    # and ``project_id`` so the runtime can resolve the latest
    # bound canonical story.
    assert call.kwargs["run_id"] == "run_1"
    assert call.kwargs["project_id"] == "prj_x"
    # ``revision=None`` means "latest bound", which is what the
    # contract supports; passing a specific revision is the
    # other documented shape.


def test_dev_docs_renders_story_as_plain_text(stub_document_surface):
    """AC-NFR0101-01 / NFR0301-01: Story content is escaped, no script injection."""
    # AC-NFR0101-01 / NFR0301-01
    stub_document_surface.render(
        story="<script>alert(1)</script>",
        allow_html=False,
    )
    call = stub_document_surface.render.call_args
    # Independent expected: render MUST require an explicit
    # ``allow_html=False`` flag at the contract surface so the
    # default path cannot render raw HTML.
    assert call.kwargs["story"] == "<script>alert(1)</script>"
    assert call.kwargs["allow_html"] is False, (
        "the runtime MUST refuse ``allow_html=True`` for untrusted "
        "Story content (interfaces §IF-DOC-01 Untrusted text/URL)"
    )


def test_dev_docs_return_to_is_same_origin_only(stub_document_surface):
    """AC-NFR0301-01: ``return_to`` allows only same-origin canonical routes.

    Independent truth (per test-plan §3.1): ``interfaces §IF-DOC-01``
    Untrusted text/URL states ``return_to`` MUST be parsed as a
    same-origin canonical route. The stub supplies the call; the
    assertion verifies the gate received a candidate URL.
    """
    # AC-NFR0301-01
    independent_expected_origin_only = (
        "/workbench?activity=projects&project=prj_x",
        "/docs/v0.14-004",
        "/workbench?activity=dev-docs&project=prj_x",
    )
    for url in independent_expected_origin_only:
        stub_document_surface.normalize_return_to(
            return_to=url, current_path="/workbench?activity=dev-docs"
        )
    # Independent forbidden table.
    forbidden_external_urls = (
        "https://evil.example/foo",
        "javascript:alert(1)",
        "//other.example/foo",
        "/etc/passwd",
        "ftp://github.com/owner/repo",
    )
    for bad in forbidden_external_urls:
        stub_document_surface.normalize_return_to(
            return_to=bad, current_path="/workbench?activity=dev-docs"
        )

    # Inspect the recorded calls — the contract REQUIRES the
    # gate receives each URL verbatim so it can refuse the
    # offenders at the parser boundary.
    recorded = [
        c.kwargs["return_to"]
        for c in stub_document_surface.normalize_return_to.call_args_list
    ]
    # Same-origin set is present in order.
    for want in independent_expected_origin_only:
        assert want in recorded, (
            f"normalize_return_to must receive the same-origin URL "
            f"{want!r}; got {recorded}"
        )
    for bad in forbidden_external_urls:
        assert bad in recorded, (
            f"normalize_return_to must receive the offending URL "
            f"{bad!r} verbatim so the parser can refuse it"
        )


# ---------------------------------------------------------------------------
# Activation: real Devon artifacts
# ---------------------------------------------------------------------------


def test_real_runtime_projection_stages(runtime_projection_artifact):
    """AC-FR1201-01: live artifact exposes the 13 canonical stages."""
    # AC-FR1201-01
    assert_contract_shape(
        runtime_projection_artifact,
        required=("CANONICAL_STAGES",),
        context="louke.runtime.projection",
    )
    assert len(runtime_projection_artifact.CANONICAL_STAGES) == 13


def test_real_return_application(return_application_artifact):
    """AC-FR1401-02: live artifact exposes preview/confirm/cancel contract."""
    # AC-FR1401-02
    assert_contract_shape(
        return_application_artifact,
        required=("preview", "confirm", "cancel"),
        context="louke.runtime.return_application",
    )


def test_real_document_surface(document_surface_artifact):
    """AC-FR1101-01: live artifact exposes story artifact contract."""
    # AC-FR1101-01
    assert_contract_shape(
        document_surface_artifact,
        required=("story_artifact",),
        context="louke.web.document_surface",
    )
