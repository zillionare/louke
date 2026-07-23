"""AC-FR2600-01: Return upstream & stale propagation.

Agents may only return gap advisories that carry evidence + artifact
anchors; Runtime validates the target per WorkflowDefinition.  Technical
gaps confirmed by Archer+Prism return to M-DESIGN (no Human); product/
Acceptance gaps require Human approval to return to M-SPEC/M-ACC and
re-do M-REQ-APPROVAL.  After return, downstream graph/baseline/RGR/
commits/reviews/candidate/CI/artifact/security/release approval are
marked stale/superseded; history and unarchived Red refs are preserved.
Client/Agent-supplied arbitrary stage names are rejected.
"""

from __future__ import annotations

import pytest

from louke.runtime.return_upstream_stale import (
    GapAdvisory,
    ReturnUpstreamError,
    validate_return_target,
)

_RUN = "run-1"
_CAND = "cand:abc"
_R = "r" * 40


def _advisory(
    *,
    kind: str = "design",
    target: str = "M-DESIGN",
    evidence: tuple[str, ...] = ("ev-1",),
    anchors: tuple[str, ...] = ("anchor-1",),
) -> GapAdvisory:
    return GapAdvisory(
        kind=kind,
        target=target,
        evidence=evidence,
        anchors=anchors,
        actor="archer:1",
    )


def test_validate_return_accepts_technical_gap_to_m_design() -> None:
    """AC-FR2600-01: technical gap with Archer+Prism evidence returns to M-DESIGN."""
    decision = validate_return_target(
        _advisory(kind="design", target="M-DESIGN"),
        workflow_definition_targets=("M-DESIGN",),
        archer_confirmed=True,
        prism_confirmed=True,
    )
    assert decision.allowed is True
    assert decision.requires_human is False


def test_validate_return_rejects_technical_gap_without_prism_confirmation() -> None:
    """AC-FR2600-01: technical gap requires Archer+Prism confirmation."""
    with pytest.raises(ReturnUpstreamError) as exc:
        validate_return_target(
            _advisory(kind="design", target="M-DESIGN"),
            workflow_definition_targets=("M-DESIGN",),
            archer_confirmed=True,
            prism_confirmed=False,
        )
    assert exc.value.code == "RETURN_TECHNICAL_NOT_CONFIRMED"


def test_validate_return_rejects_product_gap_without_human_approval() -> None:
    """AC-FR2600-01: product gap requires Human approval to return to M-SPEC/M-ACC."""
    with pytest.raises(ReturnUpstreamError) as exc:
        validate_return_target(
            _advisory(kind="product", target="M-SPEC/M-ACC"),
            workflow_definition_targets=("M-SPEC/M-ACC",),
            human_approved=False,
        )
    assert exc.value.code == "RETURN_PRODUCT_REQUIRES_HUMAN"


def test_validate_return_accepts_product_gap_with_human_approval() -> None:
    """AC-FR2600-01: product gap with Human approval returns to M-SPEC/M-ACC."""
    decision = validate_return_target(
        _advisory(kind="product", target="M-SPEC/M-ACC"),
        workflow_definition_targets=("M-SPEC/M-ACC",),
        human_approved=True,
    )
    assert decision.allowed is True
    assert decision.requires_human is True


def test_validate_return_rejects_unknown_target() -> None:
    """AC-FR2600-01: target not in WorkflowDefinition is rejected."""
    with pytest.raises(ReturnUpstreamError) as exc:
        validate_return_target(
            _advisory(target="M-FOO"),
            workflow_definition_targets=("M-DESIGN",),
            archer_confirmed=True,
            prism_confirmed=True,
        )
    assert exc.value.code == "RETURN_TARGET_INVALID"


def test_validate_return_rejects_advisory_without_evidence() -> None:
    """AC-FR2600-01: advisory must carry evidence + artifact anchors."""
    with pytest.raises(ReturnUpstreamError) as exc:
        validate_return_target(
            _advisory(evidence=(), anchors=()),
            workflow_definition_targets=("M-DESIGN",),
            archer_confirmed=True,
            prism_confirmed=True,
        )
    assert exc.value.code == "RETURN_ADVISORY_INCOMPLETE"


def test_validate_return_rejects_arbitrary_stage_name_from_client() -> None:
    """AC-FR2600-01: client/Agent-supplied arbitrary stage name is rejected."""
    with pytest.raises(ReturnUpstreamError) as exc:
        validate_return_target(
            _advisory(target="M-RANDOM-STAGE"),
            workflow_definition_targets=("M-DESIGN", "M-SPEC/M-ACC"),
            archer_confirmed=True,
            prism_confirmed=True,
        )
    assert exc.value.code == "RETURN_TARGET_INVALID"


def test_return_propagates_stale_set_downstream() -> None:
    """AC-FR2600-01: return marks downstream graph/baseline/RGR/reviews/CI/etc stale."""
    decision = validate_return_target(
        _advisory(kind="design", target="M-DESIGN"),
        workflow_definition_targets=("M-DESIGN",),
        archer_confirmed=True,
        prism_confirmed=True,
    )
    assert "graph" in decision.stale_set
    assert "baseline" in decision.stale_set
    assert "rgr" in decision.stale_set
    assert "candidate" in decision.stale_set
    assert "ci" in decision.stale_set
    assert "artifact" in decision.stale_set
    assert "security" in decision.stale_set
    assert "release-approval" in decision.stale_set


def test_return_preserves_history_and_unarchived_red_refs() -> None:
    """AC-FR2600-01: return preserves history and unarchived Red refs."""
    decision = validate_return_target(
        _advisory(kind="design", target="M-DESIGN"),
        workflow_definition_targets=("M-DESIGN",),
        archer_confirmed=True,
        prism_confirmed=True,
    )
    assert decision.preserves_history is True
    assert decision.preserves_unarchived_red_refs is True
