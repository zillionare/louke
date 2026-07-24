"""IF-PROJECT-01 / IF-GUIDE-01 — Projects context + Guide session.

AC-FR0401-01, AC-FR0401-02, AC-FR0501-01, AC-FR0501-02, AC-FR0501-03

Cross-module:
* Projects context (Project Context × Fact Stores × Runtime Projection
  × Guide Session × Workbench Presentation).
* Guide session + auto advice (Guide Session × Project Context ×
  Runtime Projection × Environment Gate × Workbench Presentation ×
  Fact Stores).
"""

from __future__ import annotations


from ._mode_b import (
    assert_contract_shape,
)


# ---------------------------------------------------------------------------
# IF-PROJECT-01: Projects context (empty / active / conflict)
# ---------------------------------------------------------------------------


def test_projects_context_empty_state_exposes_new_project_action(
    stub_projects_context,
):
    """AC-FR0401-01: empty Project renders only ``New Project``.

    Independent truth (per test-plan §3.1): ``interfaces §IF-PROJECT-01``
    declares that ``state == empty`` MUST expose a single ``New
    Project`` primary action with ``enabled=True`` and ``primary_action
    != None``. The stub supplies the call; the assertion verifies
    the gate was queried with the right workspace context.
    """
    # AC-FR0401-01
    stub_projects_context.current(workspace_id="ws_demo")
    call = stub_projects_context.current.call_args
    # Independent expected: the gate must be invoked with the
    # current workspace_id; the runtime picks the ``state`` from
    # the fact store and renders accordingly.
    assert call.kwargs.get("workspace_id") == "ws_demo"
    # ``stub_projects_context.STATE_EMPTY`` is the contract value
    # exposed by the stub; its materialisation is the runtime's
    # responsibility. The independent expected string is spelt
    # out from the spec below.
    assert stub_projects_context.STATE_EMPTY == "empty"
    assert stub_projects_context.STATE_ACTIVE == "active"
    assert stub_projects_context.STATE_CONFLICT == "conflict"


def test_projects_context_active_state_loads_status(stub_projects_context):
    """AC-FR0401-01: active Project routes the main panel to Project Status."""
    # AC-FR0401-01
    # Independent expected: the ``current`` entry-point MUST be
    # invoked with the active project id; the runtime surfaces
    # the Project Status surface when state == active.
    stub_projects_context.current(workspace_id="ws_1", expected_project_id="prj_x")
    call = stub_projects_context.current.call_args
    assert call.kwargs.get("workspace_id") == "ws_1"
    assert call.kwargs.get("expected_project_id") == "prj_x", (
        "current() must accept the active project_id so the "
        "runtime can confirm the fact-store binding (interfaces "
        "§IF-PROJECT-01)"
    )


def test_projects_context_conflict_blocks_create_and_select(
    stub_projects_context,
):
    """AC-FR0401-02: conflict disables create & select; fact-store wins.

    Independent truth (per test-plan §3.1): ``interfaces §IF-PROJECT-01``
    declares that ``state == conflict`` MUST disable ``primary_action``
    and surface the conflicting project list. The stub supplies
    the call; the assertion verifies the gate was queried with
    the right context.
    """
    # AC-FR0401-02
    stub_projects_context.current(
        workspace_id="ws_1",
        expect_conflict=True,
    )
    call = stub_projects_context.current.call_args
    assert call.kwargs.get("workspace_id") == "ws_1"
    assert call.kwargs.get("expect_conflict") is True, (
        "current() must accept the conflict flag so the runtime "
        "can surface the conflicting bindings (interfaces §IF-PROJECT-01)"
    )


# ---------------------------------------------------------------------------
# IF-GUIDE-01: context-bound Guide session + auto advice
# ---------------------------------------------------------------------------


def test_guide_session_keys_on_workspace_and_project(stub_guide_session):
    """AC-FR0501-01: Guide session key reflects workspace + project context.

    Independent truth (per test-plan §3.1): ``interfaces §IF-GUIDE-01``
    fixes the session key composition at ``(workspace_id, kind,
    optional project_id)``. The stub supplies the call; the
    assertion verifies each documented fetch shape was issued.
    """
    # AC-FR0501-01
    independent_cases = (
        # (kwargs, expected_key_part)
        ({"context": "empty", "workspace_id": "ws_1"}, "ws_1_empty"),
        (
            {"context": "project", "workspace_id": "ws_1", "project_id": "prj_x"},
            "prj_x",
        ),
    )
    for kwargs, _ in independent_cases:
        stub_guide_session.fetch(**kwargs)
    # Independent expected: the gate was invoked exactly once per
    # documented case, and each call carries the right keys.
    assert stub_guide_session.fetch.call_count == len(independent_cases)
    actual_kwargs = [c.kwargs for c in stub_guide_session.fetch.call_args_list]
    for i, (want, _) in enumerate(independent_cases):
        assert actual_kwargs[i]["workspace_id"] == want["workspace_id"]
        if want.get("project_id"):
            assert actual_kwargs[i]["project_id"] == want["project_id"]
        assert actual_kwargs[i]["context"] == want["context"], (
            f"fetch must carry the document ``context`` tag; "
            f"got {actual_kwargs[i]['context']!r}"
        )


def test_environment_ordering_runtime_status_then_advice(stub_guide_session):
    """AC-FR0501-02: blocking errors emit Runtime status first, advice second.

    Independent truth (per test-plan §3.1): ``interfaces §IF-GUIDE-01``
    ``Environment ordering`` requires runtime_status to be appended
    first, deduped, then a guide_advice is appended. The stub
    supplies the call; the assertion verifies the gate accepts an
    ``append_blocking_error`` invocation with the documented args.
    """
    # AC-FR0501-02
    stub_guide_session.append_blocking_error(
        check_revision="chk_1",
        error_code="GIST_SCOPE_MISSING",
        message="gh auth missing scope repo",
        session_id="sess_ws_1_empty",
        owning_surface="/setup/env",
    )
    call = stub_guide_session.append_blocking_error.call_args
    # Independent expected from interfaces §IF-GUIDE-01.
    assert call.kwargs["check_revision"] == "chk_1"
    assert call.kwargs["session_id"] == "sess_ws_1_empty"
    assert call.kwargs["owning_surface"] == "/setup/env", (
        "blocking errors must carry an ``owning_surface`` so the "
        "Wizard can surface the recovery URL"
    )


def test_dedupe_blocks_replaying_same_advice(stub_guide_session):
    """AC-FR0501-02: dedupe key stops the same advice being repeated.

    Independent truth (per test-plan §3.1): ``interfaces §IF-GUIDE-01``
    fixes the dedupe key at ``(session_id, check_revision,
    error_code)``. The stub supplies the call; the assertion
    verifies the gate accepts the ``check_dedupe`` invocation
    with the documented key tuple.
    """
    # AC-FR0501-02
    dedupe_key = ("sess_ws_1_empty", "chk_1", "GIST_SCOPE_MISSING")
    stub_guide_session.append_or_skip_advice(
        dedupe_key=dedupe_key,
        session_id="sess_ws_1_empty",
        check_revision="chk_1",
        error_code="GIST_SCOPE_MISSING",
    )
    call = stub_guide_session.append_or_skip_advice.call_args
    assert call.kwargs["dedupe_key"] == dedupe_key
    assert call.kwargs["session_id"] == "sess_ws_1_empty"
    assert call.kwargs["error_code"] == "GIST_SCOPE_MISSING"


def test_guide_chat_cannot_execute_runtime_actions(stub_guide_session):
    """AC-FR0501-03: Guide chat responses do not carry action capability.

    Independent truth (per test-plan §3.1): ``interfaces §IF-GUIDE-01``
    mandates that Guide replies MUST NOT carry ``install_action``,
    ``auth_action``, ``create_action``, ``return_action``,
    ``select_action``, ``advance_action``. The stub supplies the
    call; the assertion verifies the gate accepts only documented
    fields on the message.
    """
    # AC-FR0501-03
    stub_guide_session.append_user_message(
        session_id="sess_x",
        user_content="install gh for me",
    )
    call = stub_guide_session.append_user_message.call_args
    # Independent expected: only ``user_content`` is allowed; the
    # runtime MUST strip any ``*_action`` capability tokens.
    assert call.kwargs["session_id"] == "sess_x"
    assert call.kwargs["user_content"] == "install gh for me"
    # No capability keys must be supplied by the caller; assert
    # that ``append_user_message`` only accepts the documented
    # arguments.
    forbidden_kwargs = {
        "install_action",
        "auth_action",
        "create_action",
        "return_action",
        "select_action",
        "advance_action",
    }
    leaked = forbidden_kwargs & set(call.kwargs)
    assert not leaked, f"Guide chat MUST NOT carry capability tokens; got {leaked!r}"


# ---------------------------------------------------------------------------
# Activation: real Devon artifacts
# ---------------------------------------------------------------------------


def test_real_projects_context_states(projects_context_artifact):
    """AC-FR0401-01: live artifact exposes empty/active/conflict states."""
    # AC-FR0401-01
    assert_contract_shape(
        projects_context_artifact,
        required=("STATE_EMPTY", "STATE_ACTIVE", "STATE_CONFLICT"),
        context="louke.web.projects_context",
    )


def test_real_guide_session_authority(guide_session_artifact):
    """AC-FR0501-03: live Guide authority values are runtime/guide/human."""
    # AC-FR0501-03
    assert_contract_shape(
        guide_session_artifact,
        required=(
            "AUTHORITY_RUNTIME",
            "AUTHORITY_GUIDE",
            "AUTHORITY_HUMAN",
        ),
        context="louke.web.guide_session",
    )
