"""AC-FR1800-01: Candidate overall Prism review.

After local + GitHub gates PASS for the same candidate, Runtime dispatches
Prism to do an independent consistency re-review of the whole candidate:
Architecture/Interfaces/Test Plan, cross-task drift, duplicate work,
regression risks and machine-contract implementation.  REVISE routes to
the responsible Devon/Shield/upstream and creates a new candidate.  Old
overall review cannot be reused to enter M-SECURITY.  Exit M-VERIFY
requires a complete evidence snapshot of the same candidate + current
Prism PASS.
"""

from __future__ import annotations

import pytest

from louke.runtime.candidate_prism_review import (
    CandidatePrismReviewError,
    CandidatePrismVerdict,
    CandidateReviewStore,
    attach_candidate_review,
    can_enter_m_security,
)

_CAND = "cand:abc"


def _verdict(
    verdict: str = "PASS", review_id: str = "rev-cand-1", candidate_id: str = _CAND
) -> CandidatePrismVerdict:
    return CandidatePrismVerdict(
        review_id=review_id,
        candidate_id=candidate_id,
        evidence_snapshot_digest="sha256:" + "e" * 64,
        verdict=verdict,
        status="current",
    )


def test_attach_candidate_review_binds_evidence_snapshot() -> None:
    """AC-FR1800-01: a candidate Prism verdict binds the same candidate + evidence."""
    store = CandidateReviewStore()
    attach_candidate_review(store, _verdict())
    v = store.current(_CAND)
    assert v.verdict == "PASS"
    assert v.evidence_snapshot_digest.startswith("sha256:")


def test_can_enter_m_security_requires_prism_pass() -> None:
    """AC-FR1800-01: entering M-SECURITY requires current Prism PASS."""
    store = CandidateReviewStore()
    attach_candidate_review(store, _verdict("PASS"))
    assert can_enter_m_security(store, _CAND, local_passed=True, ci_passed=True) is True


def test_revise_routes_to_responsible_and_creates_new_candidate() -> None:
    """AC-FR1800-01: REVISE routes to owner; old review cannot be reused."""
    store = CandidateReviewStore()
    attach_candidate_review(store, _verdict("REVISE"))
    assert (
        can_enter_m_security(store, _CAND, local_passed=True, ci_passed=True) is False
    )


def test_old_review_cannot_be_reused_after_candidate_change() -> None:
    """AC-FR1800-01: candidate change makes old overall review stale."""
    store = CandidateReviewStore()
    attach_candidate_review(store, _verdict("PASS", candidate_id="cand:1"))
    # New candidate id -> old review stale.
    attach_candidate_review(
        store, _verdict("PASS", candidate_id="cand:2", review_id="rev-2")
    )
    assert (
        can_enter_m_security(store, "cand:1", local_passed=True, ci_passed=True)
        is False
    )
    assert (
        can_enter_m_security(store, "cand:2", local_passed=True, ci_passed=True) is True
    )


def test_enter_m_security_requires_local_and_ci_pass_too() -> None:
    """AC-FR1800-01: local + CI gates must also be current PASS."""
    store = CandidateReviewStore()
    attach_candidate_review(store, _verdict("PASS"))
    assert (
        can_enter_m_security(store, _CAND, local_passed=False, ci_passed=True) is False
    )
    assert (
        can_enter_m_security(store, _CAND, local_passed=True, ci_passed=False) is False
    )


def test_missing_review_blocks_m_security() -> None:
    """AC-FR1800-01: missing candidate Prism verdict blocks M-SECURITY."""
    store = CandidateReviewStore()
    assert (
        can_enter_m_security(store, _CAND, local_passed=True, ci_passed=True) is False
    )


def test_attach_rejects_unknown_verdict() -> None:
    """AC-FR1800-01: unknown verdict value is rejected."""
    store = CandidateReviewStore()
    with pytest.raises(CandidatePrismReviewError) as exc:
        attach_candidate_review(store, _verdict("UNKNOWN"))
    assert exc.value.code == "REV_SCHEMA_INVALID"
