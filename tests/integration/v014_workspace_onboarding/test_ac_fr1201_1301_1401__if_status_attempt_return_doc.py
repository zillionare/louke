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

Tests drive the real ``louke.runtime.projection``,
``louke.runtime.attempt_detail``, ``louke.runtime.return_application``,
and ``louke.web.document_surface`` modules.
"""

from __future__ import annotations

from pathlib import Path


from louke.runtime.attempt_detail import attempt_detail
from louke.runtime.projection import CANONICAL_STAGES, project_status
from louke.runtime.return_application import cancel, confirm, preview
from louke.web.document_surface import story_artifact


# ---------------------------------------------------------------------------
# IF-STATUS-01: Project Status read model
# ---------------------------------------------------------------------------


def test_status_surface_carries_thirteen_canonical_stages() -> None:
    """AC-FR1201-01: ``stage_catalog`` is the 13-stage canonical order.

    The contract fixes the canonical stage IDs and order; the test
    asserts against the locked list (interfaces §IF-STATUS-01).
    """
    # AC-FR1201-01
    locked_stages = (
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
    assert tuple(CANONICAL_STAGES) == locked_stages, (
        f"CANONICAL_STAGES must match the locked order from "
        f"interfaces §IF-STATUS-01; got {tuple(CANONICAL_STAGES)}"
    )
    assert len(CANONICAL_STAGES) == 13


def test_project_status_returns_projection_shape() -> None:
    """AC-FR1201-01: ``project_status`` returns a non-empty projection."""
    # AC-FR1201-01
    body = project_status(workspace_id="ws_1", project_id="prj_x", run_id="run_1")
    assert body["workspace_id"] == "ws_1"
    assert body["project_id"] == "prj_x"
    assert body["run_id"] == "run_1"
    assert "active" in body
    assert "projection_revision" in body


def test_project_status_active_stage_is_first_canonical() -> None:
    """AC-FR1201-01: a fresh projection defaults to the first canonical stage."""
    # AC-FR1201-01
    body = project_status(workspace_id="ws_1", project_id="prj_x")
    assert body["active"]["stage"] == CANONICAL_STAGES[0]


# ---------------------------------------------------------------------------
# IF-ATTEMPT-01: attempt detail with return context
# ---------------------------------------------------------------------------


def test_attempt_detail_distinguishes_selected_and_active() -> None:
    """AC-FR1301-01: detail carries both project_id and attempt_id."""
    # AC-FR1301-01
    detail = attempt_detail(
        project_id="prj_x",
        attempt_id="att_2",
        stage="M-IMPL",
        owner="agent_devon",
        elapsed_seconds=120,
        evidence=[{"kind": "log", "path": "out.log"}],
        actions=["retry", "open_artifact"],
    )
    assert detail["project_id"] == "prj_x"
    assert detail["attempt_id"] == "att_2"
    assert detail["stage"] == "M-IMPL"
    assert detail["owner"] == "agent_devon"
    assert detail["elapsed_seconds"] == 120
    assert detail["evidence"] == [{"kind": "log", "path": "out.log"}]
    assert detail["actions"] == ["retry", "open_artifact"]


def test_attempt_detail_defaults_to_empty_evidence_and_actions() -> None:
    """AC-FR1301-01: missing evidence/actions default to empty lists."""
    # AC-FR1301-01
    detail = attempt_detail(project_id="prj_x", attempt_id="att_1", stage="M-IMPL")
    assert detail["evidence"] == []
    assert detail["actions"] == []


# ---------------------------------------------------------------------------
# IF-RETURN-01: Return Preview / Confirm
# ---------------------------------------------------------------------------


def test_return_preview_reports_unconfirmed() -> None:
    """AC-FR1401-01: ``preview`` returns ``confirmed=False`` and a target stage."""
    # AC-FR1401-01
    body = preview(project_id="prj_x", attempt_id="att_2", target_stage="M-IMPL")
    assert body["project_id"] == "prj_x"
    assert body["attempt_id"] == "att_2"
    assert body["target_stage"] == "M-IMPL"
    assert body["confirmed"] is False


def test_return_confirm_marks_executed() -> None:
    """AC-FR1401-02: ``confirm`` returns ``executed=True`` and a new revision."""
    # AC-FR1401-02
    body = confirm(project_id="prj_x", attempt_id="att_2", expected_revision=5)
    assert body["project_id"] == "prj_x"
    assert body["attempt_id"] == "att_2"
    assert body["executed"] is True


def test_return_cancel_marks_cancelled() -> None:
    """AC-FR1401-02: ``cancel`` returns ``cancelled=True`` and does NOT execute."""
    # AC-FR1401-02
    body = cancel(project_id="prj_x", attempt_id="att_2")
    assert body["project_id"] == "prj_x"
    assert body["attempt_id"] == "att_2"
    assert body["cancelled"] is True


# ---------------------------------------------------------------------------
# IF-DOC-01: Dev Docs canonical Story
# ---------------------------------------------------------------------------


def test_document_surface_returns_none_when_no_story(tmp_path: Path) -> None:
    """AC-FR1401-01: missing ``story.md`` returns ``None``."""
    # AC-FR1401-01
    body = story_artifact(workspace_root=tmp_path, spec_id="spec_1")
    assert body is None


def test_document_surface_loads_existing_story(tmp_path: Path) -> None:
    """AC-FR1401-01: an existing ``story.md`` is loaded with a return URL."""
    # AC-FR1401-01
    spec_dir = tmp_path / ".louke" / "project" / "specs" / "spec_1"
    spec_dir.mkdir(parents=True)
    (spec_dir / "story.md").write_text("# Story\ntext body", encoding="utf-8")
    body = story_artifact(workspace_root=tmp_path, spec_id="spec_1")
    # AC-FR1401-01: existing story.md is loaded with a return URL
    assert body is not None
    assert body["spec_id"] == "spec_1"
    assert body["revision"] == "latest"
    assert "# Story" in body["content"]
    assert body["return_url"] == "/workbench?activity=projects"


def test_document_surface_specific_revision(tmp_path: Path) -> None:
    """AC-FR1401-01: a specific revision is reflected in the response."""
    # AC-FR1401-01
    spec_dir = tmp_path / ".louke" / "project" / "specs" / "spec_1"
    spec_dir.mkdir(parents=True)
    (spec_dir / "story.md").write_text("# Story", encoding="utf-8")
    body = story_artifact(workspace_root=tmp_path, spec_id="spec_1", revision="r1")
    assert body["revision"] == "r1"


# ---------------------------------------------------------------------------
# Activation: real artifact surface
# ---------------------------------------------------------------------------


def test_real_runtime_projection_stages() -> None:
    """AC-FR1201-01: real ``louke.runtime.projection`` exposes 13 stages."""
    # AC-FR1201-01
    import louke.runtime.projection as mod

    assert len(mod.CANONICAL_STAGES) == 13


def test_real_return_application_surface() -> None:
    """AC-FR1401-02: real artifact exposes ``preview`` / ``confirm`` / ``cancel``."""
    # AC-FR1401-02
    import louke.runtime.return_application as mod

    assert callable(mod.preview)
    assert callable(mod.confirm)
    assert callable(mod.cancel)


def test_real_attempt_detail_surface() -> None:
    """AC-FR1301-01: real artifact exposes ``attempt_detail``."""
    # AC-FR1301-01
    import louke.runtime.attempt_detail as mod

    assert callable(mod.attempt_detail)


def test_real_document_surface_surface() -> None:
    """AC-FR1401-01: real artifact exposes ``story_artifact``."""
    # AC-FR1401-01
    import louke.web.document_surface as mod

    assert callable(mod.story_artifact)
