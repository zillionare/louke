"""Integration tests for FR-2100: M-RELEASE preview & Human gate.

AC-FR2100-01: The preview shows canonical version/candidate/main/tag,
user changes, trace, tests/CI/reviews/security, artifact identities/
versions, risks, operations & recovery. Release is enabled only when
all non-waivable evidence is current PASS. Human may choose Release,
Delay or Return; Delay produces no side effects and preserves candidate
+ preview identity; Return records reason+target and only enters a
WorkflowDefinition-allowed target. Any candidate/evidence/artifact/plan
change makes the old approval stale; Release may NOT bypass failed
gates.

Interfaces covered (per interfaces.md):
- IF-REL-02 (Primary ARC-14)
- IF-WFR-01 (workflow context, ARC-01)
- IF-CAND-01 (candidate context, ARC-09)
"""
# AC-FR2100-01

from __future__ import annotations

import pytest

from louke.runtime.m_release_preview import (
    ERROR_CODES,
    DecisionResult,
    HumanDecision,
    MReleaseError,
    ReleasePreview,
    build_preview,
    submit_human_decision,
)


def _valid_preview(
    *,
    all_gates_pass: bool = True,
    workspace_dirty: bool = False,
    release_blocked: bool = False,
    allowed_return_targets: tuple[str, ...] = ("M-DESIGN", "M-SPEC/M-ACC"),
) -> ReleasePreview:
    return build_preview(
        candidate_id="cand-1",
        canonical_version="0.14.0",
        main_target="main",
        tag="v0.14.0",
        all_gates_pass=all_gates_pass,
        workspace_dirty=workspace_dirty,
        release_blocked=release_blocked,
        allowed_return_targets=allowed_return_targets,
        workflow_revision=1,
    )


# ---------------------------------------------------------------------------
# build_preview
# ---------------------------------------------------------------------------


@pytest.mark.real_module
def test_build_preview_has_stable_identity_and_full_fields():
    """AC-FR2100-01: preview carries candidate/version/main/tag/gates/targets."""
    p = _valid_preview()
    assert isinstance(p, ReleasePreview)
    assert p.preview_id.startswith("preview:")
    assert p.canonical_version == "0.14.0"
    assert p.tag == "v0.14.0"
    assert p.main_target == "main"
    assert "M-DESIGN" in p.allowed_return_targets


@pytest.mark.real_module
def test_release_action_enabled_only_when_all_gates_pass_and_workspace_clean():
    """AC-FR2100-01: Release enabled only when gates PASS + clean workspace."""
    p = _valid_preview(
        all_gates_pass=True, workspace_dirty=False, release_blocked=False
    )
    assert p.release_action_enabled() is True

    p2 = _valid_preview(all_gates_pass=False)
    assert p2.release_action_enabled() is False

    p3 = _valid_preview(workspace_dirty=True)
    assert p3.release_action_enabled() is False

    p4 = _valid_preview(release_blocked=True)
    assert p4.release_action_enabled() is False


@pytest.mark.real_module
def test_delay_action_always_enabled():
    """AC-FR2100-01: Delay is always enabled (no side effects)."""
    p = _valid_preview(all_gates_pass=False, release_blocked=True)
    assert p.delay_action_enabled() is True


@pytest.mark.real_module
def test_return_action_enabled_only_when_targets_exist():
    """AC-FR2100-01: Return enabled only when WorkflowDefinition allows targets."""
    p = _valid_preview(allowed_return_targets=("M-DESIGN",))
    assert p.return_action_enabled() is True

    p2 = _valid_preview(allowed_return_targets=())
    assert p2.return_action_enabled() is False


# ---------------------------------------------------------------------------
# submit_human_decision - Release
# ---------------------------------------------------------------------------


@pytest.mark.real_module
def test_submit_release_creates_publish_authorization():
    """AC-FR2100-01: Release on gates-PASS preview -> publishing + authorization."""
    p = _valid_preview()
    result = submit_human_decision(p, HumanDecision(action="Release"))
    assert isinstance(result, DecisionResult)
    assert result.action == "Release"
    assert result.new_state == "publishing"
    assert result.authorization_id and result.authorization_id.startswith("auth:")
    assert result.preview_id == p.preview_id


@pytest.mark.real_module
def test_submit_release_rejected_when_gates_not_pass():
    """AC-FR2100-01: Release cannot bypass failed gates -> REL_RELEASE_DISABLED."""
    p = _valid_preview(all_gates_pass=False)
    with pytest.raises(MReleaseError) as exc:
        submit_human_decision(p, HumanDecision(action="Release"))
    assert exc.value.code == "REL_RELEASE_DISABLED"


@pytest.mark.real_module
def test_submit_release_rejected_when_workspace_dirty():
    """AC-FR2100-01: dirty workspace -> REL_RELEASE_DISABLED."""
    p = _valid_preview(workspace_dirty=True)
    with pytest.raises(MReleaseError) as exc:
        submit_human_decision(p, HumanDecision(action="Release"))
    assert exc.value.code == "REL_RELEASE_DISABLED"


@pytest.mark.real_module
def test_submit_release_rejected_when_release_blocked():
    """AC-FR2100-01: blocked release -> REL_RELEASE_DISABLED."""
    p = _valid_preview(release_blocked=True)
    with pytest.raises(MReleaseError) as exc:
        submit_human_decision(p, HumanDecision(action="Release"))
    assert exc.value.code == "REL_RELEASE_DISABLED"


# ---------------------------------------------------------------------------
# submit_human_decision - Delay
# ---------------------------------------------------------------------------


@pytest.mark.real_module
def test_submit_delay_produces_no_side_effects():
    """AC-FR2100-01: Delay -> release_waiting, no authorization, no provider intent."""
    p = _valid_preview()
    result = submit_human_decision(p, HumanDecision(action="Delay"))
    assert result.action == "Delay"
    assert result.new_state == "release_waiting"
    assert result.authorization_id is None  # no side effects
    assert result.preview_id == p.preview_id  # preview identity preserved
    assert result.candidate_id == p.candidate_id  # candidate preserved


# ---------------------------------------------------------------------------
# submit_human_decision - Return
# ---------------------------------------------------------------------------


@pytest.mark.real_module
def test_submit_return_to_allowed_target_with_reason():
    """AC-FR2100-01: Return to allowed target with reason -> returned_upstream."""
    p = _valid_preview(allowed_return_targets=("M-DESIGN", "M-SPEC/M-ACC"))
    result = submit_human_decision(
        p,
        HumanDecision(action="Return", reason="design gap", target="M-DESIGN"),
    )
    assert result.action == "Return"
    assert result.new_state == "returned_upstream"
    assert result.target == "M-DESIGN"


@pytest.mark.real_module
def test_submit_return_rejected_without_reason():
    """AC-FR2100-01: Return requires non-empty reason -> REL_RETURN_REASON_REQUIRED."""
    p = _valid_preview()
    with pytest.raises(MReleaseError) as exc:
        submit_human_decision(
            p,
            HumanDecision(action="Return", reason="", target="M-DESIGN"),
        )
    assert exc.value.code == "REL_RETURN_REASON_REQUIRED"


@pytest.mark.real_module
def test_submit_return_rejected_with_invalid_target():
    """AC-FR2100-01: Return target not in allowed -> REL_RETURN_TARGET_INVALID;
    only WorkflowDefinition-allowed targets may be entered."""
    p = _valid_preview(allowed_return_targets=("M-DESIGN",))
    with pytest.raises(MReleaseError) as exc:
        submit_human_decision(
            p,
            HumanDecision(action="Return", reason="x", target="M-TEST"),
        )
    assert exc.value.code == "REL_RETURN_TARGET_INVALID"


@pytest.mark.real_module
def test_submit_unknown_action_rejected():
    """AC-FR2100-01: unknown action -> REL_ACTION_NOT_ALLOWED."""
    p = _valid_preview()
    with pytest.raises(MReleaseError) as exc:
        submit_human_decision(p, HumanDecision(action="Mystery"))
    assert exc.value.code == "REL_ACTION_NOT_ALLOWED"


@pytest.mark.real_module
def test_error_codes_set_covers_all_documented_codes():
    """AC-FR2100-01: ERROR_CODES includes all codes from interfaces.md §12."""
    expected = {
        "REL_PREVIEW_NOT_READY",
        "REL_PREVIEW_STALE",
        "REL_REVISION_CONFLICT",
        "REL_RELEASE_DISABLED",
        "REL_GATE_NOT_CURRENT",
        "REL_RETURN_REASON_REQUIRED",
        "REL_RETURN_TARGET_INVALID",
        "REL_ACTION_NOT_ALLOWED",
        "REL_DECISION_CONFLICT",
        "REL_ALREADY_PUBLISHING",
    }
    actual = set(ERROR_CODES)
    missing = expected - actual
    assert not missing, f"ERROR_CODES missing: {missing}"
