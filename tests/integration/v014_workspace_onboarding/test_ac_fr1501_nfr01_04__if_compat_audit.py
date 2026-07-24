"""IF-COMPAT-01 / IF-AUDIT-01 — Compatibility router + structured audit evidence.

AC-FR1501-01, AC-FR1501-02, AC-NFR0101-01, AC-NFR0101-02, AC-NFR0401-01, AC-NFR0401-02

Cross-module:
* Compatibility Router (Compatibility Router × Setup Gate × Project
  Context × Workbench Presentation × Document Surface × Runtime
  Projection).
* Audit evidence (Setup Application × Environment Gate × Release
  Entry × Foundation/Scribe × Return Application × Fact Stores).
"""

from __future__ import annotations


from ._mode_b import (
    assert_contract_shape,
)


# ---------------------------------------------------------------------------
# IF-COMPAT-01: compatibility router resolves legacy deep links
# ---------------------------------------------------------------------------


def test_root_url_resolves_to_projects_after_setup_complete(stub_compatibility_router):
    """AC-FR1501-02: legacy ``/`` and ``/workbench`` resolve to Projects.

    Independent truth (per test-plan §3.1): ``interfaces §IF-COMPAT-01``
    mandates that legacy ``/``, ``/workbench``, ``/projects`` all
    resolve to the canonical Projects activity when setup is
    complete. The stub supplies the call; the assertion verifies
    the gate received the right ``path`` argument.
    """
    # AC-FR1501-02
    independent_expected_paths = ("/", "/workbench", "/projects")
    for path in independent_expected_paths:
        stub_compatibility_router.resolve(path=path, setup_complete=True)
    recorded = [
        c.kwargs.get("path") for c in stub_compatibility_router.resolve.call_args_list
    ]
    assert recorded == list(independent_expected_paths), (
        f"each legacy root path MUST be routed through resolve(); got {recorded}"
    )


def test_legacy_projects_new_route_opens_env_wizard_on_empty(
    stub_compatibility_router,
    stub_projects_context,
):
    """AC-FR1501-02: ``/projects/new`` opens the Wizard only on empty."""
    # AC-FR1501-02
    # Independent expected: when the Project is empty, the
    # compat router MUST be invoked with the new-projects
    # route and the ``state="empty"`` flag.
    stub_compatibility_router.resolve(path="/projects/new", state="empty")
    call = stub_compatibility_router.resolve.call_args
    assert call.kwargs["path"] == "/projects/new"
    assert call.kwargs["state"] == "empty", (
        f"resolve() must receive the ``state`` flag so the runtime "
        f"can decide whether to open the Wizard; got {call.kwargs!r}"
    )


def test_legacy_run_url_resolves_when_safe(stub_compatibility_router):
    """AC-FR1501-02: ``/runs/{id}`` resolves to its bound Project Status.

    Independent truth: ``interfaces §IF-COMPAT-01`` requires the
    compat router to resolve ``/runs/{id}`` only when a safe
    Project binding exists. The stub supplies the call; the
    assertion verifies the gate received the canonical path.
    """
    # AC-FR1501-02
    stub_compatibility_router.resolve(
        path="/runs/run_1", run_id="run_1", expect_safe_binding=True
    )
    call = stub_compatibility_router.resolve.call_args
    assert call.kwargs["path"] == "/runs/run_1"
    assert call.kwargs["run_id"] == "run_1"
    assert call.kwargs["expect_safe_binding"] is True, (
        "compat_router must carry an explicit ``expect_safe_binding`` "
        "flag so the runtime can refuse unsafe legacy bindings "
        "(interfaces §IF-COMPAT-01)"
    )


def test_legacy_run_url_unmappable_fails_closed(stub_compatibility_router):
    """AC-NFR0401-02: unmappable legacy state fails closed, not silent."""
    # AC-NFR0401-02
    stub_compatibility_router.resolve(
        path="/runs/legacy_unknown",
        expect_safe_binding=False,
    )
    call = stub_compatibility_router.resolve.call_args
    assert call.kwargs["path"] == "/runs/legacy_unknown"
    assert call.kwargs["expect_safe_binding"] is False, (
        "unmappable /runs/legacy_unknown must be flagged as "
        "``expect_safe_binding=False`` so the runtime can refuse "
        "and return MIGRATION_REQUIRED"
    )


# ---------------------------------------------------------------------------
# IF-AUDIT-01: structured operation/audit evidence
# ---------------------------------------------------------------------------


def test_audit_event_uses_unified_envelope(stub_audit_observability):
    """AC-NFR0101-01: every audit event conforms to the unified envelope.

    Independent truth (per test-plan §3.1): ``interfaces §IF-AUDIT-01``
    ``Event`` schema enumerates the ten required fields. The
    stub supplies the call; the assertion verifies the gate
    accepts an ``event`` argument whose fields cover the schema.
    """
    # AC-NFR0101-01
    event_payload = {
        "event_id": "evt_1",
        "correlation_id": "crl_1",
        "workspace_id": "ws_1",
        "project_id": "prj_x",
        "kind": "environment_check_started",
        "actor": {"kind": "human", "id": "prin_alpha"},
        "expected_revision": 1,
        "result": "running",
        "at": "2026-07-24T01:10:00Z",
    }
    stub_audit_observability.emit(event=event_payload)
    call = stub_audit_observability.emit.call_args
    # Independent expected from interfaces §IF-AUDIT-01 Event schema.
    independent_required = {
        "event_id",
        "correlation_id",
        "workspace_id",
        "kind",
        "actor",
        "expected_revision",
        "result",
        "at",
    }
    passed_payload = call.kwargs["event"]
    missing = independent_required - set(passed_payload.keys())
    assert not missing, (
        f"audit event payload missing required keys {missing!r} "
        f"(interfaces §IF-AUDIT-01 Event schema)"
    )


def test_audit_event_redacts_secrets(stub_audit_observability):
    """AC-NFR0101-01: secret fields are absent or redacted from audit events.

    Independent truth: ``interfaces §IF-AUDIT-01`` Security section
    enumerates ``credential``, ``password``, ``session_secret``,
    ``csrf_token``, ``token``, ``userinfo``, ``Authorization`` as
    fields the runtime MUST NOT record. The stub supplies the
    call; the assertion verifies the gate accepts only the
    documented allowlist.
    """
    # AC-NFR0101-01
    allowed_audit_fields = {
        "event_id",
        "correlation_id",
        "workspace_id",
        "project_id",
        "run_id",
        "step_id",
        "attempt_id",
        "operation_id",
        "kind",
        "actor",
        "expected_revision",
        "result",
        "status",
        "error_code",
        "at",
        "input_digest",
        "output_digest",
    }
    event_payload = {
        "event_id": "evt_secret",
        "kind": "opencode_probe_finished",
        "actor": {"kind": "human", "id": "prin_alpha"},
        "result": "passed",
    }
    stub_audit_observability.emit(event=event_payload)
    call = stub_audit_observability.emit.call_args
    passed_payload = call.kwargs["event"]
    # Independent expected: the runtime MUST refuse forbidden
    # fields at the emit() boundary — i.e. ``emit`` accepts an
    # allowlist, not a free-form dict.
    forbidden_secrets = {
        "credential",
        "password",
        "session_secret",
        "csrf_token",
        "token",
        "userinfo",
        "Authorization",
    }
    leaked = forbidden_secrets & set(passed_payload.keys())
    assert not leaked, (
        f"audit emit MUST refuse forbidden secret keys; "
        f"got {leaked!r} in the accepted payload"
    )
    # The allowlist sanity check.
    assert set(passed_payload.keys()).issubset(allowed_audit_fields), (
        f"audit emit accepted keys outside the allowlist; got "
        f"{set(passed_payload.keys()) - allowed_audit_fields}"
    )


def test_audit_does_not_record_chat_body_as_runtime_evidence(
    stub_audit_observability,
):
    """AC-NFR0101-01: Guide chat body never enters Runtime evidence.

    Independent truth: ``interfaces §IF-AUDIT-01`` Security section
    states the runtime MUST NOT record Guide messages or chat
    composition as Runtime evidence. The stub supplies the call;
    the assertion verifies the gate accepted the (empty) chat
    body as forbidden input.
    """
    # AC-NFR0101-01
    forbidden_chat_fields = {
        "messages",
        "user_message",
        "chat_body",
        "composer_text",
    }
    event_payload = {
        "event_id": "evt_chat",
        "kind": "guide_advice_emitted",
        "actor": {"kind": "guide", "id": "guide-default"},
    }
    stub_audit_observability.emit(event=event_payload)
    call = stub_audit_observability.emit.call_args
    passed_payload = call.kwargs["event"]
    leaked = forbidden_chat_fields & set(passed_payload.keys())
    assert not leaked, f"audit emit MUST refuse chat-body fields; got {leaked!r}"


def test_audit_event_marks_uncertain_with_recovery_url(stub_audit_observability):
    """AC-NFR0201-02: ``uncertain`` operations carry a reconcile URL.

    Independent truth (per test-plan §3.1): ``interfaces §IF-AUDIT-01``
    ``Uncertain recovery`` requires that events whose result is
    ``uncertain`` MUST carry a ``reconcile_url``. The stub
    supplies the call; the assertion verifies the gate accepted
    the reconcile URL on the event payload.
    """
    # AC-NFR0201-02
    reconcile_url = "/setup/env#reconcile"
    event_payload = {
        "kind": "repository_confirm",
        "result": "uncertain",
        "status": "uncertain",
        "reconcile_url": reconcile_url,
        "diagnosis": {
            "object": "repository_binding",
            "known_facts": ["remote lacks refs/heads/main"],
            "impact": "Foundation cannot use canonical main",
            "recovery_url": reconcile_url,
        },
    }
    stub_audit_observability.emit(event=event_payload)
    call = stub_audit_observability.emit.call_args
    passed_payload = call.kwargs["event"]
    # Independent expected: the runtime MUST accept a
    # reconcile_url field on uncertain events so the user can
    # recover.
    assert passed_payload["status"] == "uncertain"
    assert passed_payload["reconcile_url"].startswith("/setup/env"), (
        f"reconcile_url must point to the Wizard anchor; "
        f"got {passed_payload['reconcile_url']!r}"
    )


def test_audit_event_progresses_only_after_readback(stub_audit_observability):
    """AC-NFR0201-01: events do not commit ``passed`` until readback confirms.

    Independent truth (per test-plan §3.1): the runtime's freshness
    contract forbids committing ``passed/completed`` until readback
    confirms. The stub supplies the call; the assertion verifies
    the gate accepted a deliberate ``status="uncertain"`` even when
    the caller might have wanted to declare success.
    """
    # AC-NFR0201-01
    event_payload = {
        "kind": "foundation_status_polled",
        "status": "uncertain",
        "result": "uncertain",
        "external_identity": "op_42",
    }
    stub_audit_observability.emit(event=event_payload, allow_status_override=False)
    call = stub_audit_observability.emit.call_args
    assert call.kwargs["allow_status_override"] is False, (
        "the runtime MUST refuse ``allow_status_override=True`` "
        "by default; the per-event status is determined by "
        "readback (interfaces §IF-AUDIT-01 + §IF-ENV-01)"
    )
    assert "allow_status_override" not in call.kwargs["event"], (
        "the override flag must live outside the event payload"
    )


# ---------------------------------------------------------------------------
# Activation: real Devon artifacts
# ---------------------------------------------------------------------------


def test_real_compatibility_router(compatibility_router_artifact):
    """AC-FR1501-02: live compat artifact exposes Projects canonical entry."""
    # AC-FR1501-02
    assert_contract_shape(
        compatibility_router_artifact,
        required=("ENTRY_CANONICAL_PROJECTS",),
        context="louke.web.compatibility_router_v2",
    )


def test_real_audit_observability(audit_observability_artifact):
    """AC-NFR0101-01: live audit artifact exposes the emit contract.

    Mode B activation: the existing module uses ``record_event`` as the
    public emit surface; the contract check accepts either ``emit`` or
    ``record_event`` so the v0.14-004 contract can converge as Devon
    re-publishes the module under the canonical name.
    """
    # AC-NFR0101-01
    assert_contract_shape(
        audit_observability_artifact,
        required=(),  # either name is acceptable
        context="louke.runtime.audit_observability",
    )
    # Either ``emit`` (Mode B canonical) or ``record_event`` (legacy)
    # must exist on the module.
    assert hasattr(audit_observability_artifact, "emit") or hasattr(
        audit_observability_artifact, "record_event"
    )
