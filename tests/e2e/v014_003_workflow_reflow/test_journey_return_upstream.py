"""E2E journey: return upstream & stale propagation.

Covers AC IDs:
- AC-FR2600-01 (Return upstream & stale propagation)

NORMAL PATH: technical gap with Archer+Prism confirmation -> M-DESIGN
allowed -> downstream evidence stale.
"""
# AC-FR2600-01

from __future__ import annotations

import pytest

pytestmark = pytest.mark.v014_003_e2e


def test_return_upstream_technical_gap_normal_path():
    """J-RETURN: technical gap -> Archer+Prism confirm -> M-DESIGN allowed."""
    from louke.v014.fr2600_return_upstream import (
        GapAdvisory,
        ReturnTarget,
        validate_return_target,
    )

    advisory = GapAdvisory(
        kind="design",
        target="M-DESIGN",
        evidence=("review-1", "finding-2"),
        anchors=("louke/v014/x.py:42",),
        actor="archer:1",
    )
    target = validate_return_target(
        advisory,
        workflow_definition_targets=("M-DESIGN", "M-SPEC/M-ACC"),
        archer_confirmed=True,
        prism_confirmed=True,
    )
    assert isinstance(target, ReturnTarget)
    assert target.allowed is True
    assert target.requires_human is False
    # Downstream evidence marked stale.
    expected_stale = {
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
    }
    assert set(target.stale_set) == expected_stale
    # History and unarchived Red refs preserved.
    assert target.preserves_history is True
    assert target.preserves_unarchived_red_refs is True


def test_return_upstream_product_gap_with_human_normal_path():
    """J-RETURN: product gap with Human approval -> M-SPEC/M-ACC allowed."""
    from louke.v014.fr2600_return_upstream import (
        GapAdvisory,
        validate_return_target,
    )

    advisory = GapAdvisory(
        kind="product",
        target="M-SPEC/M-ACC",
        evidence=("review-1",),
        anchors=("acceptance.md:42",),
        actor="human:1",
    )
    target = validate_return_target(
        advisory,
        workflow_definition_targets=("M-DESIGN", "M-SPEC/M-ACC"),
        human_approved=True,
    )
    assert target.allowed is True
    assert target.requires_human is True
