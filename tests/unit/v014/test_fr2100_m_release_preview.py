"""AC-FR2100-01: M-RELEASE preview & Human gate.

Runtime shows in the Project current release preview: canonical version/
candidate/main/tag, user changes, Issues/FR/AC trace, all tests/CI,
Prism/Judge, artifact digests/versions/public versions, non-blocking risks,
release/recovery plan and upcoming side effects.  Release is enabled only
when all non-waivable evidence is current PASS.  Human may choose Release,
Delay or Return; Delay produces no side effects and keeps candidate+preview
identity; Return records reason+target and only enters a WorkflowDefinition
target.  Any candidate/evidence/artifact/plan change makes the old
approval stale; Release may NOT bypass failed gates.
"""

from __future__ import annotations


import pytest

from louke.runtime.m_release_preview import (
    HumanDecision,
    MReleaseError,
    ReleasePreview,
    build_preview,
    submit_human_decision,
)

_CAND = "cand:abc"


def _preview(
    *, all_gates_pass: bool = True, dirty: bool = False, release_blocked: bool = False
) -> ReleasePreview:
    return ReleasePreview(
        preview_id="preview:1",
        candidate_id=_CAND,
        canonical_version="0.14.0",
        main_target="main",
        tag="v0.14.0",
        all_gates_pass=all_gates_pass,
        workspace_dirty=dirty,
        release_blocked=release_blocked,
        allowed_return_targets=("M-SPEC/M-ACC",),
        workflow_revision=1,
    )


def test_build_preview_binds_all_required_fields() -> None:
    """AC-FR2100-01: preview binds version/candidate/main/tag/trace/risks."""
    preview = build_preview(
        candidate_id=_CAND,
        canonical_version="0.14.0",
        main_target="main",
        tag="v0.14.0",
        all_gates_pass=True,
        workspace_dirty=False,
        release_blocked=False,
        allowed_return_targets=("M-SPEC/M-ACC",),
        workflow_revision=1,
    )
    assert preview.canonical_version == "0.14.0"
    assert preview.candidate_id == _CAND
    assert preview.tag == "v0.14.0"
    assert preview.preview_id.startswith("preview:")


def test_release_enabled_when_all_gates_pass_and_clean() -> None:
    """AC-FR2100-01: Release enabled only when all non-waivable evidence current PASS."""
    preview = _preview(all_gates_pass=True, dirty=False)
    assert preview.release_action_enabled() is True


def test_release_disabled_when_gates_fail() -> None:
    """AC-FR2100-01: failed gates disable Release."""
    preview = _preview(all_gates_pass=False)
    assert preview.release_action_enabled() is False


def test_release_disabled_when_workspace_dirty() -> None:
    """AC-FR2100-01: dirty workspace disables Release."""
    preview = _preview(dirty=True)
    assert preview.release_action_enabled() is False


def test_delay_produces_no_side_effects() -> None:
    """AC-FR2100-01: Delay keeps candidate+preview identity, no provider side effects."""
    decision = submit_human_decision(
        _preview(), HumanDecision(action="Delay", reason="wait for Friday")
    )
    assert decision.action == "Delay"
    assert decision.authorization_id is None  # no publish authorization
    assert decision.new_state == "release_waiting"
    assert decision.preview_id == "preview:1"
    assert decision.candidate_id == _CAND


def test_return_records_reason_and_target() -> None:
    """AC-FR2100-01: Return records reason+target and enters allowed upstream context."""
    decision = submit_human_decision(
        _preview(),
        HumanDecision(action="Return", reason="need new AC", target="M-SPEC/M-ACC"),
    )
    assert decision.action == "Return"
    assert decision.new_state == "returned_upstream"
    assert decision.target == "M-SPEC/M-ACC"


def test_return_rejects_disallowed_target() -> None:
    """AC-FR2100-01: Return to a non-allowed target does not change context."""
    with pytest.raises(MReleaseError) as exc:
        submit_human_decision(
            _preview(),
            HumanDecision(action="Return", reason="x", target="M-DESIGN"),
        )
    assert exc.value.code == "REL_RETURN_TARGET_INVALID"


def test_return_rejects_empty_reason() -> None:
    """AC-FR2100-01: Return requires non-empty reason."""
    with pytest.raises(MReleaseError) as exc:
        submit_human_decision(
            _preview(),
            HumanDecision(action="Return", reason="", target="M-SPEC/M-ACC"),
        )
    assert exc.value.code == "REL_RETURN_REASON_REQUIRED"


def test_release_creates_unique_publish_authorization() -> None:
    """AC-FR2100-01: Release creates a unique publish authorization."""
    decision = submit_human_decision(_preview(), HumanDecision(action="Release"))
    assert decision.action == "Release"
    assert decision.authorization_id is not None
    assert decision.new_state == "publishing"


def test_release_rejects_when_gates_fail() -> None:
    """AC-FR2100-01: Release may not bypass failed gates."""
    with pytest.raises(MReleaseError) as exc:
        submit_human_decision(
            _preview(all_gates_pass=False),
            HumanDecision(action="Release"),
        )
    assert exc.value.code == "REL_RELEASE_DISABLED"


def test_release_rejects_when_blocked() -> None:
    """AC-FR2100-01: Release disabled when blocked."""
    with pytest.raises(MReleaseError) as exc:
        submit_human_decision(
            _preview(release_blocked=True),
            HumanDecision(action="Release"),
        )
    assert exc.value.code == "REL_RELEASE_DISABLED"
