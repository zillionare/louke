"""Integration tests for FR-2600: Return upstream & stale propagation.

AC-FR2600-01: Agents may only return gap advisories carrying evidence
+ artifact anchors; Runtime validates the target per WorkflowDefinition.
Technical gaps confirmed by Archer+Prism return to M-DESIGN (no Human);
product/Acceptance gaps require Human approval to return to M-SPEC/
M-ACC and re-do M-REQ-APPROVAL. After return, downstream graph/
baseline/RGR/commits/reviews/candidate/CI/artifact/security/release
approval are marked stale/superseded; history and unarchived Red refs
are preserved. Client/Agent-supplied arbitrary stage names are rejected.

Interfaces covered (per interfaces.md):
- IF-WFR-01 (Primary ARC-01)
- IF-TRACE-01 (trace stale, ARC-16)
- IF-RGR-01 (Red ref preservation, ARC-05)
"""
# AC-FR2600-01

from __future__ import annotations

import pytest

from louke.v014.fr2600_return_upstream import (
    ERROR_CODES,
    GapAdvisory,
    ReturnTarget,
    ReturnUpstreamError,
    validate_return_target,
)


def _valid_advisory(kind: str = "design", target: str = "M-DESIGN") -> GapAdvisory:
    return GapAdvisory(
        kind=kind,
        target=target,
        evidence=("review-1", "finding-2"),
        anchors=("louke/v014/x.py:42",),
        actor="archer:1",
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.real_module
def test_validate_return_target_design_with_archer_prism_confirmed():
    """AC-FR2600-01: technical gap with Archer+Prism -> M-DESIGN allowed,
    no Human required."""
    target = validate_return_target(
        _valid_advisory("design", "M-DESIGN"),
        workflow_definition_targets=("M-DESIGN", "M-SPEC/M-ACC"),
        archer_confirmed=True,
        prism_confirmed=True,
    )
    assert isinstance(target, ReturnTarget)
    assert target.allowed is True
    assert target.requires_human is False
    # Stale set covers all downstream fields.
    for field in (
        "graph",
        "baseline",
        "rgr",
        "commits",
        "reviews",
        "candidate",
        "ci",
        "artifact",
        "security",
        "release-approval",
    ):
        assert field in target.stale_set


@pytest.mark.real_module
def test_validate_return_target_product_requires_human_approval():
    """AC-FR2600-01: product gap without Human -> RETURN_PRODUCT_REQUIRES_HUMAN."""
    with pytest.raises(ReturnUpstreamError) as exc:
        validate_return_target(
            _valid_advisory("product", "M-SPEC/M-ACC"),
            workflow_definition_targets=("M-DESIGN", "M-SPEC/M-ACC"),
            human_approved=False,
        )
    assert exc.value.code == "RETURN_PRODUCT_REQUIRES_HUMAN"


@pytest.mark.real_module
def test_validate_return_target_product_allowed_with_human_approval():
    """AC-FR2600-01: product gap with Human approval -> M-SPEC/M-ACC allowed."""
    target = validate_return_target(
        _valid_advisory("product", "M-SPEC/M-ACC"),
        workflow_definition_targets=("M-DESIGN", "M-SPEC/M-ACC"),
        human_approved=True,
    )
    assert target.allowed is True
    assert target.requires_human is True


@pytest.mark.real_module
def test_validate_return_target_rejects_advisory_without_evidence():
    """AC-FR2600-01: advisory must carry evidence + anchors."""
    advisory = GapAdvisory(
        kind="design",
        target="M-DESIGN",
        evidence=(),  # missing
        anchors=("x",),
        actor="archer:1",
    )
    with pytest.raises(ReturnUpstreamError) as exc:
        validate_return_target(
            advisory,
            workflow_definition_targets=("M-DESIGN",),
            archer_confirmed=True,
            prism_confirmed=True,
        )
    assert exc.value.code == "RETURN_ADVISORY_INCOMPLETE"


@pytest.mark.real_module
def test_validate_return_target_rejects_advisory_without_anchors():
    """AC-FR2600-01: advisory must carry artifact anchors."""
    advisory = GapAdvisory(
        kind="design",
        target="M-DESIGN",
        evidence=("review-1",),
        anchors=(),  # missing
        actor="archer:1",
    )
    with pytest.raises(ReturnUpstreamError) as exc:
        validate_return_target(
            advisory,
            workflow_definition_targets=("M-DESIGN",),
            archer_confirmed=True,
            prism_confirmed=True,
        )
    assert exc.value.code == "RETURN_ADVISORY_INCOMPLETE"


@pytest.mark.real_module
def test_validate_return_target_rejects_target_not_in_workflow_definition():
    """AC-FR2600-01: target not in WorkflowDefinition -> RETURN_TARGET_INVALID;
    arbitrary stage names rejected."""
    with pytest.raises(ReturnUpstreamError) as exc:
        validate_return_target(
            _valid_advisory("design", "M-MYSTERY"),
            workflow_definition_targets=("M-DESIGN", "M-SPEC/M-ACC"),
            archer_confirmed=True,
            prism_confirmed=True,
        )
    assert exc.value.code == "RETURN_TARGET_INVALID"


@pytest.mark.real_module
def test_validate_return_target_rejects_technical_gap_without_archer_prism():
    """AC-FR2600-01: technical gap requires Archer+Prism confirmation."""
    with pytest.raises(ReturnUpstreamError) as exc:
        validate_return_target(
            _valid_advisory("design", "M-DESIGN"),
            workflow_definition_targets=("M-DESIGN",),
            archer_confirmed=False,
            prism_confirmed=True,
        )
    assert exc.value.code == "RETURN_TECHNICAL_NOT_CONFIRMED"


@pytest.mark.real_module
def test_validate_return_target_preserves_history_and_unarchived_red_refs():
    """AC-FR2600-01: history preserved; unarchived Red refs preserved."""
    target = validate_return_target(
        _valid_advisory("design", "M-DESIGN"),
        workflow_definition_targets=("M-DESIGN",),
        archer_confirmed=True,
        prism_confirmed=True,
    )
    assert target.preserves_history is True
    assert target.preserves_unarchived_red_refs is True


@pytest.mark.real_module
def test_validate_return_target_rejects_unknown_kind():
    """AC-FR2600-01: unknown advisory kind -> RETURN_TARGET_INVALID."""
    with pytest.raises(ReturnUpstreamError) as exc:
        validate_return_target(
            _valid_advisory("mystery", "M-DESIGN"),
            workflow_definition_targets=("M-DESIGN",),
            archer_confirmed=True,
            prism_confirmed=True,
        )
    assert exc.value.code == "RETURN_TARGET_INVALID"


@pytest.mark.real_module
def test_error_codes_set_covers_all_documented_codes():
    """AC-FR2600-01: ERROR_CODES includes all codes from interfaces.md (§4 row)."""
    expected = {
        "RETURN_TARGET_INVALID",
        "RETURN_ADVISORY_INCOMPLETE",
        "RETURN_TECHNICAL_NOT_CONFIRMED",
        "RETURN_PRODUCT_REQUIRES_HUMAN",
    }
    actual = set(ERROR_CODES)
    missing = expected - actual
    assert not missing, f"ERROR_CODES missing: {missing}"
