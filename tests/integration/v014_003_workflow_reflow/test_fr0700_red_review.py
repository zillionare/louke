"""Integration tests for FR-0700: Red independent review & correction.

AC-FR0700-01: Prism receives the precise ``B..R`` range,
requirements/Acceptance, test-layer contract and Red evidence; Green
can only start when both the program gate and Prism PASS are current on
the same ``R``. Modifying the test tree, REVISE, unexpected PASS, or
wrong failure category creates a new attempt/ref and makes the old
verdict unable to advance Green.

Interfaces covered (per interfaces.md):
- IF-RGR-01 (Primary ARC-05)
- IF-REV-02 (Prism review snapshot, ARC-07)
"""
# AC-FR0700-01

from __future__ import annotations

import pytest

from louke.v014.fr0700_red_review import (
    ERROR_CODES,
    PrismRedVerdict,
    RedReviewError,
    RedReviewStore,
    attach_red_review,
    can_start_green,
)


def _valid_verdict(red_oid: str = "r" * 40, verdict: str = "PASS") -> PrismRedVerdict:
    return PrismRedVerdict(
        review_id="rev-001",
        baseline_oid="b" * 40,
        red_oid=red_oid,
        evidence_digest="sha256:evidence",
        verdict=verdict,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.real_module
def test_can_start_green_true_when_program_and_prism_pass_current():
    """AC-FR0700-01: program_passed=True + Prism PASS current -> can start Green."""
    store = RedReviewStore()
    attach_red_review(store, _valid_verdict("r" * 40, "PASS"))
    assert can_start_green(store, red_oid="r" * 40, program_passed=True) is True


@pytest.mark.real_module
def test_can_start_green_false_when_program_failed():
    """AC-FR0700-01: program_passed=False -> cannot start Green."""
    store = RedReviewStore()
    attach_red_review(store, _valid_verdict("r" * 40, "PASS"))
    assert can_start_green(store, red_oid="r" * 40, program_passed=False) is False


@pytest.mark.real_module
def test_can_start_green_false_when_prism_revise():
    """AC-FR0700-01: REVISE verdict -> cannot start Green."""
    store = RedReviewStore()
    attach_red_review(store, _valid_verdict("r" * 40, "REVISE"))
    assert can_start_green(store, red_oid="r" * 40, program_passed=True) is False


@pytest.mark.real_module
def test_can_start_green_false_when_no_review():
    """AC-FR0700-01: no Prism review -> cannot start Green."""
    store = RedReviewStore()
    assert can_start_green(store, red_oid="r" * 40, program_passed=True) is False


@pytest.mark.real_module
def test_attach_red_review_rejects_unexpected_pass_verdict():
    """AC-FR0700-01: unexpected test PASS during review -> error."""
    store = RedReviewStore()
    verdict = PrismRedVerdict(
        review_id="rev-001",
        baseline_oid="b" * 40,
        red_oid="r" * 40,
        evidence_digest="sha256:evidence",
        verdict="UNEXPECTED_PASS",
    )
    with pytest.raises(RedReviewError) as exc:
        attach_red_review(store, verdict)
    assert exc.value.code == "RGR_RED_UNEXPECTED_PASS"


@pytest.mark.real_module
def test_attach_red_review_rejects_baseline_mismatch():
    """AC-FR0700-01: verdict baseline != expected -> RGR_RED_REVIEW_NOT_CURRENT."""
    store = RedReviewStore()
    verdict = _valid_verdict("r" * 40, "PASS")
    # bind verdict to baseline B1 but expected baseline is different.
    verdict = PrismRedVerdict(
        review_id=verdict.review_id,
        baseline_oid="b1" + "b" * 38,
        red_oid=verdict.red_oid,
        evidence_digest=verdict.evidence_digest,
        verdict="PASS",
    )
    with pytest.raises(RedReviewError) as exc:
        attach_red_review(store, verdict, expected_baseline_oid="b2" + "b" * 38)
    assert exc.value.code == "RGR_RED_REVIEW_NOT_CURRENT"


@pytest.mark.real_module
def test_new_red_makes_old_review_stale():
    """AC-FR0700-01: test tree change -> new R; old verdict stale; cannot advance Green."""
    store = RedReviewStore()
    attach_red_review(store, _valid_verdict("r1" + "r" * 38, "PASS"))
    # Initial state: can advance.
    assert can_start_green(store, red_oid="r1" + "r" * 38, program_passed=True) is True

    # New R arrives: old verdict must become stale.
    attach_red_review(store, _valid_verdict("r2" + "r" * 38, "PASS"))
    # Old R's verdict is now stale.
    assert store.current("r1" + "r" * 38).status == "stale"
    # Cannot advance Green with old R.
    assert can_start_green(store, red_oid="r1" + "r" * 38, program_passed=True) is False
    # Can advance Green with the new R.
    assert can_start_green(store, red_oid="r2" + "r" * 38, program_passed=True) is True


@pytest.mark.real_module
def test_red_review_idempotent_when_same_red_oid():
    """AC-FR0700-01: re-attaching verdict for same R does not invalidate it."""
    store = RedReviewStore()
    v1 = _valid_verdict("r" * 40, "PASS")
    attach_red_review(store, v1)
    v2 = PrismRedVerdict(
        review_id="rev-002",
        baseline_oid="b" * 40,
        red_oid="r" * 40,
        evidence_digest="sha256:evidence-v2",
        verdict="PASS",
    )
    attach_red_review(store, v2)
    # Same R, current verdict updated.
    assert store.current("r" * 40).status == "current"
    assert can_start_green(store, red_oid="r" * 40, program_passed=True) is True


@pytest.mark.real_module
def test_error_codes_set_covers_all_documented_codes():
    """AC-FR0700-01: ERROR_CODES includes all codes from interfaces.md §4."""
    expected = {
        "RGR_RED_UNEXPECTED_PASS",
        "RGR_RED_REVIEW_NOT_CURRENT",
        "RGR_RED_FAILURE_INVALID",
    }
    actual = set(ERROR_CODES)
    missing = expected - actual
    assert not missing, f"ERROR_CODES missing: {missing}"
