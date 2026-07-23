"""AC-FR0700-01: Red independent review & correction.

Runtime dispatches Prism to review the precise ``B..R`` range, current
requirements/Acceptance, test-layer contract and Red evidence.  The
verdict binds the same ``R`` and evidence digest.  Only when program
gate AND Prism are both PASS may Green start.  REVISE, unexpected test
PASS, wrong failure category or diff out-of-scope must produce a new
Red correction attempt.  Any test tree change creates a new ``R`` and
makes the old review stale.
"""

from __future__ import annotations

import pytest

from louke.runtime.red_review import (
    PrismRedVerdict,
    RedReviewError,
    RedReviewStore,
    attach_red_review,
    can_start_green,
)

_B = "b" * 40
_R1 = "r" * 40
_R2 = "s" * 40


def _verdict(
    *,
    red_oid: str = _R1,
    verdict: str = "PASS",
    evidence_digest: str = "sha256:" + "e" * 64,
    review_id: str = "rev-1",
) -> PrismRedVerdict:
    return PrismRedVerdict(
        review_id=review_id,
        baseline_oid=_B,
        red_oid=red_oid,
        evidence_digest=evidence_digest,
        verdict=verdict,
        status="current",
    )


def test_attach_red_review_binds_red_oid_and_evidence() -> None:
    """AC-FR0700-01: a Prism review binds the same R and evidence digest."""
    store = RedReviewStore()
    v = _verdict()
    attach_red_review(store, v)
    assert store.current(_R1).verdict == "PASS"
    assert store.current(_R1).evidence_digest == v.evidence_digest


def test_can_start_green_requires_program_and_prism_pass() -> None:
    """AC-FR0700-01: Green starts only with both program gate and Prism PASS."""
    store = RedReviewStore()
    attach_red_review(store, _verdict(verdict="PASS"))
    assert can_start_green(store, red_oid=_R1, program_passed=True) is True
    assert can_start_green(store, red_oid=_R1, program_passed=False) is False
    store2 = RedReviewStore()
    attach_red_review(store2, _verdict(verdict="REVISE"))
    assert can_start_green(store2, red_oid=_R1, program_passed=True) is False


def test_revise_creates_new_correction_attempt() -> None:
    """AC-FR0700-01: REVISE verdict triggers a new Red correction attempt."""
    store = RedReviewStore()
    attach_red_review(store, _verdict(verdict="REVISE"))
    # The R1 verdict is current REVISE; cannot start Green.
    assert can_start_green(store, red_oid=_R1, program_passed=True) is False
    # The correction produces a new R2 and a new review.
    attach_red_review(store, _verdict(red_oid=_R2, verdict="PASS", review_id="rev-2"))
    assert can_start_green(store, red_oid=_R2, program_passed=True) is True


def test_test_tree_change_makes_old_review_stale() -> None:
    """AC-FR0700-01: any test tree change creates a new R and supersedes the old review."""
    store = RedReviewStore()
    attach_red_review(store, _verdict(verdict="PASS"))
    attach_red_review(store, _verdict(red_oid=_R2, verdict="PASS", review_id="rev-2"))
    assert store.current(_R1).status == "stale"
    assert store.current(_R2).status == "current"


def test_unexpected_pass_makes_review_invalid() -> None:
    """AC-FR0700-01: an unexpected test PASS invalidates the review."""
    store = RedReviewStore()
    attach_red_review(store, _verdict(verdict="PASS"))
    # If the tests unexpectedly passed during review, Runtime marks the verdict invalid.
    with pytest.raises(RedReviewError) as exc:
        attach_red_review(store, _verdict(verdict="UNEXPECTED_PASS"))
    assert exc.value.code == "RGR_RED_UNEXPECTED_PASS"


def test_review_rejects_mismatched_baseline() -> None:
    """AC-FR0700-01: a verdict bound to a different baseline is rejected."""
    store = RedReviewStore()
    bad = PrismRedVerdict(
        review_id="rev-x",
        baseline_oid="x" * 40,  # mismatched baseline
        red_oid=_R1,
        evidence_digest="sha256:" + "e" * 64,
        verdict="PASS",
        status="current",
    )
    with pytest.raises(RedReviewError) as exc:
        attach_red_review(store, bad, expected_baseline_oid=_B)
    assert exc.value.code == "RGR_RED_REVIEW_NOT_CURRENT"


def test_no_current_review_blocks_green() -> None:
    """AC-FR0700-01: no current review for R blocks Green."""
    store = RedReviewStore()
    assert can_start_green(store, red_oid=_R1, program_passed=True) is False
