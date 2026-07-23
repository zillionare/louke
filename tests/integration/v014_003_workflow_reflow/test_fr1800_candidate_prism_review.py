"""Integration tests for FR-1800: Candidate overall Prism review.

AC-FR1800-01: After local+GitHub gates PASS for the same candidate,
Prism receives the complete candidate, design/contracts, task reviews
and trace snapshot; its PASS binds to the same commit as all program
evidence. REVISE routes to the responsible Agent/upstream and creates
a new candidate; the old overall review cannot be reused to enter
M-SECURITY.

Interfaces covered (per interfaces.md):
- IF-CAND-01 (candidate context, ARC-09)
- IF-REV-02 (Prism review, ARC-07)
- IF-TRACE-01 (trace snapshot, ARC-16)
"""
# AC-FR1800-01

from __future__ import annotations

import pytest

from louke.runtime.candidate_prism_review import (
    ERROR_CODES,
    CandidatePrismReviewError,
    CandidatePrismVerdict,
    CandidateReviewStore,
    attach_candidate_review,
    can_enter_m_security,
)


def _valid_verdict(
    candidate_id: str = "cand-1", verdict: str = "PASS"
) -> CandidatePrismVerdict:
    return CandidatePrismVerdict(
        review_id="rev-cand-001",
        candidate_id=candidate_id,
        evidence_snapshot_digest="sha256:snapshot",
        verdict=verdict,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.real_module
def test_can_enter_m_security_true_when_local_ci_prism_pass_current():
    """AC-FR1800-01: local+CI PASS + Prism PASS current -> can enter M-SECURITY."""
    store = CandidateReviewStore()
    attach_candidate_review(store, _valid_verdict("cand-1", "PASS"))
    assert (
        can_enter_m_security(
            store,
            "cand-1",
            local_passed=True,
            ci_passed=True,
        )
        is True
    )


@pytest.mark.real_module
def test_can_enter_m_security_false_when_local_failed():
    """AC-FR1800-01: local gate fail -> cannot enter M-SECURITY."""
    store = CandidateReviewStore()
    attach_candidate_review(store, _valid_verdict("cand-1", "PASS"))
    assert (
        can_enter_m_security(
            store,
            "cand-1",
            local_passed=False,
            ci_passed=True,
        )
        is False
    )


@pytest.mark.real_module
def test_can_enter_m_security_false_when_ci_failed():
    """AC-FR1800-01: CI gate fail -> cannot enter M-SECURITY."""
    store = CandidateReviewStore()
    attach_candidate_review(store, _valid_verdict("cand-1", "PASS"))
    assert (
        can_enter_m_security(
            store,
            "cand-1",
            local_passed=True,
            ci_passed=False,
        )
        is False
    )


@pytest.mark.real_module
def test_can_enter_m_security_false_when_prism_revise():
    """AC-FR1800-01: REVISE verdict -> cannot enter M-SECURITY."""
    store = CandidateReviewStore()
    attach_candidate_review(store, _valid_verdict("cand-1", "REVISE"))
    assert (
        can_enter_m_security(
            store,
            "cand-1",
            local_passed=True,
            ci_passed=True,
        )
        is False
    )


@pytest.mark.real_module
def test_can_enter_m_security_false_when_no_review():
    """AC-FR1800-01: no Prism review -> cannot enter M-SECURITY."""
    store = CandidateReviewStore()
    assert (
        can_enter_m_security(
            store,
            "cand-1",
            local_passed=True,
            ci_passed=True,
        )
        is False
    )


@pytest.mark.real_module
def test_new_candidate_makes_old_review_stale():
    """AC-FR1800-01: new candidate -> old review stale; cannot enter M-SECURITY."""
    store = CandidateReviewStore()
    attach_candidate_review(store, _valid_verdict("cand-1", "PASS"))
    # New candidate arrives.
    attach_candidate_review(store, _valid_verdict("cand-2", "PASS"))
    assert store.current("cand-1").status == "stale"
    # Old candidate cannot enter M-SECURITY.
    assert (
        can_enter_m_security(
            store,
            "cand-1",
            local_passed=True,
            ci_passed=True,
        )
        is False
    )
    # New candidate can.
    assert (
        can_enter_m_security(
            store,
            "cand-2",
            local_passed=True,
            ci_passed=True,
        )
        is True
    )


@pytest.mark.real_module
def test_attach_review_rejects_invalid_verdict():
    """AC-FR1800-01: verdict not PASS|REVISE -> REV_SCHEMA_INVALID."""
    store = CandidateReviewStore()
    bad = CandidatePrismVerdict(
        review_id="rev-x",
        candidate_id="cand-1",
        evidence_snapshot_digest="sha256:x",
        verdict="MAYBE",  # invalid
    )
    with pytest.raises(CandidatePrismReviewError) as exc:
        attach_candidate_review(store, bad)
    assert exc.value.code == "REV_SCHEMA_INVALID"


@pytest.mark.real_module
def test_error_codes_set_covers_all_documented_codes():
    """AC-FR1800-01: ERROR_CODES includes all codes from interfaces.md §5."""
    expected = {
        "REV_KIND_UNSUPPORTED",
        "REV_INPUT_INCOMPLETE",
        "REV_PROGRAM_EVIDENCE_NOT_CURRENT",
        "REV_SUBJECT_MISMATCH",
        "REV_SCHEMA_INVALID",
        "REV_ACTOR_INVALID",
        "REV_BUNDLE_UNTRUSTED",
        "REV_OUTPUT_SECRET",
        "REV_TIMEOUT",
        "REV_STALE",
        "REV_ROUTE_INVALID",
    }
    actual = set(ERROR_CODES)
    missing = expected - actual
    assert not missing, f"ERROR_CODES missing: {missing}"
