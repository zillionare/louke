"""IF-ENV-01 / IF-ENV-02 — On-demand Environment Gate + repository binding.

AC-FR0601-01, AC-FR0601-02, AC-FR0701-01, AC-FR0701-02, AC-FR0801-01, AC-FR0801-02

Cross-module:
* Environment Gate (Environment Gate × Project Context × GitHub/Git
  Adapters × Workbench Presentation × Guide Session × Fact Stores).
* Repository binding preview/confirm/reconcile (Environment Gate ×
  GitHub/Git Adapters × Fact Stores × Workbench Presentation × Guide
  Session).

Tests drive the real ``louke.web.environment_gate`` module.
"""

from __future__ import annotations

from louke.web.environment_gate import (
    CANONICAL_STEPS,
    REQUIRED_SCOPES,
    STEP_CANONICAL_MAIN,
    STEP_GH_AUTH_SCOPES,
    STEP_GH_EXECUTABLE,
    STEP_REPOSITORY_BINDING,
    start_check,
)


# ---------------------------------------------------------------------------
# IF-ENV-01: scope contract + canonical step order
# ---------------------------------------------------------------------------


def test_environment_gate_required_scopes_match_contract() -> None:
    """AC-FR0701-01: the four required scopes are the locked set."""
    # AC-FR0701-01
    assert set(REQUIRED_SCOPES) == {"gist", "project", "repo", "workflow"}


def test_environment_gate_canonical_step_order_matches_contract() -> None:
    """AC-FR0601-01: steps run gh_executable → auth_scopes → binding → main."""
    # AC-FR0601-01
    assert CANONICAL_STEPS == (
        STEP_GH_EXECUTABLE,
        STEP_GH_AUTH_SCOPES,
        STEP_REPOSITORY_BINDING,
        STEP_CANONICAL_MAIN,
    )


def test_environment_gate_start_check_returns_running_default() -> None:
    """AC-FR0601-01: ``start_check`` returns a running 4-step check."""
    # AC-FR0601-01
    check = start_check(workspace_id="ws_1")
    assert check["state"] == "running"
    assert check["current_step"] == STEP_GH_EXECUTABLE
    assert len(check["steps"]) == 4
    # Each step starts pending; no automatic runner state.
    for step in check["steps"]:
        assert step["state"] == "pending"
        assert step["observed"] is None
        assert step["missing"] == []
        assert step["diagnosis"] is None
        assert step["actions"] == []


def test_environment_gate_step_ids_match_contract() -> None:
    """AC-FR0601-01: each ``EnvironmentStep.id`` is one of the four locked ids."""
    # AC-FR0601-01
    check = start_check(workspace_id="ws_1")
    seen_ids = {step["id"] for step in check["steps"]}
    assert seen_ids == set(CANONICAL_STEPS)
    assert seen_ids == {
        "gh_executable",
        "gh_auth_scopes",
        "repository_binding",
        "canonical_main",
    }


def test_environment_gate_booleans_start_disabled() -> None:
    """AC-FR0601-01: nothing is ``enabled`` until every step passes."""
    # AC-FR0601-01
    check = start_check(workspace_id="ws_1")
    assert check["story_input_enabled"] is False
    assert check["preview_enabled"] is False
    assert check["create_enabled"] is False


# ---------------------------------------------------------------------------
# Activation: real artifact surface
# ---------------------------------------------------------------------------


def test_real_environment_gate_required_scopes() -> None:
    """AC-FR0701-01: real ``louke.web.environment_gate`` exposes ``REQUIRED_SCOPES``."""
    # AC-FR0701-01
    import louke.web.environment_gate as mod

    scopes = set(mod.REQUIRED_SCOPES)
    assert scopes == {"gist", "project", "repo", "workflow"}


def test_real_environment_gate_canonical_steps() -> None:
    """AC-FR0601-01: real artifact exposes the canonical step order."""
    # AC-FR0601-01
    import louke.web.environment_gate as mod

    assert tuple(mod.CANONICAL_STEPS) == (
        "gh_executable",
        "gh_auth_scopes",
        "repository_binding",
        "canonical_main",
    )
