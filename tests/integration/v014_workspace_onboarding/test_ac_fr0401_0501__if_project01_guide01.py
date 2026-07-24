"""IF-PROJECT-01 / IF-GUIDE-01 — Projects context + Guide session.

AC-FR0401-01, AC-FR0401-02, AC-FR0501-01, AC-FR0501-02, AC-FR0501-03

Cross-module:
* Projects context (Project Context × Fact Stores × Runtime Projection
  × Guide Session × Workbench Presentation).
* Guide session + auto advice (Guide Session × Project Context ×
  Runtime Projection × Environment Gate × Workbench Presentation ×
  Fact Stores).

Tests drive the real ``louke.web.projects_context`` and
``louke.web.guide_session`` modules. External bindings come from
explicit inputs; no fixture stubs the modules under test.
"""

from __future__ import annotations

from louke.web.guide_session import (
    AUTHORITY_GUIDE,
    AUTHORITY_HUMAN,
    AUTHORITY_RUNTIME,
    KIND_GUIDE_ADVICE,
    KIND_GUIDE_ERROR,
    KIND_GUIDE_REPLY,
    KIND_RUNTIME_STATUS,
    KIND_USER,
    create_session,
)
from louke.web.projects_context import (
    STATE_ACTIVE,
    STATE_CONFLICT,
    STATE_EMPTY,
    resolve,
)


# ---------------------------------------------------------------------------
# IF-PROJECT-01: Projects context (empty / active / conflict)
# ---------------------------------------------------------------------------


def test_projects_context_empty_disables_secondary_actions() -> None:
    """AC-FR0401-01: empty context exposes only the New Project primary action."""
    # AC-FR0401-01
    body = resolve(workspace_id="ws_1", bindings=[])
    assert body["state"] == STATE_EMPTY
    assert body["project"] is None
    assert body["conflicts"] == []
    # AC-FR0401-01: empty Project exposes a New Project primary action
    assert body["primary_action"] is not None
    assert body["primary_action"]["kind"] == "new_project"
    assert body["primary_action"]["enabled"] is True


def test_projects_context_active_loads_the_single_project() -> None:
    """AC-FR0401-01: one binding → ``active`` with that project as the surface."""
    # AC-FR0401-01
    binding = {
        "project_id": "prj_x",
        "spec_id": "spec_1",
        "run_id": "run_1",
    }
    body = resolve(workspace_id="ws_1", bindings=[binding])
    assert body["state"] == STATE_ACTIVE
    assert body["project"] == binding
    assert body["conflicts"] == []
    assert body["primary_action"] is None


def test_projects_context_conflict_disables_create_and_select() -> None:
    """AC-FR0401-02: conflict surfaces all bindings and disables actions."""
    # AC-FR0401-02
    bindings = [
        {"project_id": "prj_a", "spec_id": "spec_1"},
        {"project_id": "prj_b", "spec_id": "spec_2"},
    ]
    body = resolve(workspace_id="ws_1", bindings=bindings)
    assert body["state"] == STATE_CONFLICT
    assert body["project"] is None
    assert body["conflicts"] == bindings
    # AC-FR0401-02: conflict disables the New Project primary action
    assert body["primary_action"] is not None
    assert body["primary_action"]["enabled"] is False
    assert body["primary_action"]["kind"] == "new_project"


def test_projects_context_does_not_depend_on_list_order_or_recent() -> None:
    """AC-FR0401-02: resolution is based purely on binding count, not order.

    Reversing the order of the same bindings must yield the same state.
    No 'most recent' or 'first in list' shortcut is allowed.
    """
    # AC-FR0401-02
    bindings = [
        {"project_id": "prj_a", "spec_id": "spec_1"},
        {"project_id": "prj_b", "spec_id": "spec_2"},
    ]
    forward = resolve(workspace_id="ws_1", bindings=bindings)
    backward = resolve(workspace_id="ws_1", bindings=list(reversed(bindings)))
    assert forward["state"] == STATE_CONFLICT
    assert backward["state"] == STATE_CONFLICT
    assert set(c["project_id"] for c in forward["conflicts"]) == set(
        c["project_id"] for c in backward["conflicts"]
    )


def test_projects_context_does_not_start_environment_check_on_empty() -> None:
    """AC-FR0401-01: empty context exposes no Environment side-effect."""
    # AC-FR0401-01
    body = resolve(workspace_id="ws_1", bindings=[])
    # ``primary_action`` is the only exposed action; there is no
    # hidden ``start_environment_check`` flag in the response.
    assert "start_environment_check" not in body
    assert "environment_check" not in body


# ---------------------------------------------------------------------------
# IF-GUIDE-01: context-bound Guide session
# ---------------------------------------------------------------------------


def test_guide_session_authority_values_match_contract() -> None:
    """AC-FR0501-03: authority values are runtime / guide / human."""
    # AC-FR0501-03
    assert AUTHORITY_RUNTIME == "runtime"
    assert AUTHORITY_GUIDE == "guide"
    assert AUTHORITY_HUMAN == "human"


def test_guide_session_kind_values_match_contract() -> None:
    """AC-FR0501-02: message kinds are the documented five."""
    # AC-FR0501-02
    assert KIND_RUNTIME_STATUS == "runtime_status"
    assert KIND_GUIDE_ADVICE == "guide_advice"
    assert KIND_GUIDE_ERROR == "guide_error"
    assert KIND_USER == "user"
    assert KIND_GUIDE_REPLY == "guide_reply"


def test_guide_session_create_empty_context() -> None:
    """AC-FR0501-01: empty-context session is bound to the workspace."""
    # AC-FR0501-01
    session = create_session(workspace_id="ws_1", kind="empty")
    assert session["context"]["workspace_id"] == "ws_1"
    assert session["context"]["kind"] == "empty"
    assert session["context"]["project_id"] is None
    assert session["context"]["runtime_revision"] is None
    assert session["messages"] == []
    assert session["composer_enabled"] is True
    assert session["owning_links"] == []


def test_guide_session_create_project_context() -> None:
    """AC-FR0501-01: project-context session carries project_id."""
    # AC-FR0501-01
    session = create_session(workspace_id="ws_1", project_id="prj_x", kind="project")
    assert session["context"]["project_id"] == "prj_x"
    assert session["context"]["kind"] == "project"


def test_guide_session_keys_on_workspace_and_optional_project() -> None:
    """AC-FR0501-01: a session id depends on workspace + project context."""
    # AC-FR0501-01
    empty = create_session(workspace_id="ws_1", kind="empty")
    project = create_session(workspace_id="ws_1", project_id="prj_x", kind="project")
    other_workspace = create_session(workspace_id="ws_2", kind="empty")
    assert empty["session_id"] != other_workspace["session_id"]
    # The empty context and the project context within the same
    # workspace must produce distinct sessions.
    assert empty["session_id"] != project["session_id"]


# ---------------------------------------------------------------------------
# Activation: real artifact surface
# ---------------------------------------------------------------------------


def test_real_projects_context_states() -> None:
    """AC-FR0401-01: real ``projects_context`` exposes empty/active/conflict."""
    # AC-FR0401-01
    import louke.web.projects_context as mod

    assert mod.STATE_EMPTY == "empty"
    assert mod.STATE_ACTIVE == "active"
    assert mod.STATE_CONFLICT == "conflict"
    assert callable(mod.resolve)


def test_real_guide_session_authority() -> None:
    """AC-FR0501-03: real ``guide_session`` exposes the authority values."""
    # AC-FR0501-03
    import louke.web.guide_session as mod

    assert mod.AUTHORITY_RUNTIME == "runtime"
    assert mod.AUTHORITY_GUIDE == "guide"
    assert mod.AUTHORITY_HUMAN == "human"
    assert callable(mod.create_session)
