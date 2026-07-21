"""FR-1800: Candidate overall Prism review.

After local + GitHub gates PASS for the same candidate, Runtime dispatches
Prism to do an independent consistency re-review of the whole candidate:
Architecture/Interfaces/Test Plan, cross-task drift, duplicate work,
regression risks and machine-contract implementation.  REVISE routes to
the responsible Devon/Shield/upstream and creates a new candidate.  Old
overall review cannot be reused to enter M-SECURITY.  Exit M-VERIFY
requires a complete evidence snapshot of the same candidate + current
Prism PASS (AC-FR1800-01).
"""

from __future__ import annotations

from dataclasses import dataclass

ERROR_CODES = (
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
)

_VALID_VERDICTS = frozenset({"PASS", "REVISE"})


class CandidatePrismReviewError(Exception):
    """A fail-closed candidate Prism review rejection carrying a stable code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


@dataclass(frozen=True)
class CandidatePrismVerdict:
    """A Prism whole-candidate review verdict (AC-FR1800-01).

    Attributes:
        review_id: Stable review identity.
        candidate_id: Bound candidate id.
        evidence_snapshot_digest: ``sha256:<hex>`` of the complete evidence
            snapshot.
        verdict: ``PASS|REVISE``.
        status: ``current`` (default) or ``stale`` once a newer candidate
            arrives.
    """

    review_id: str
    candidate_id: str
    evidence_snapshot_digest: str
    verdict: str
    status: str = "current"


class CandidateReviewStore:
    """In-memory store of candidate Prism verdicts (AC-FR1800-01)."""

    def __init__(self) -> None:
        self._by_candidate: dict[str, CandidatePrismVerdict] = {}
        self._latest: str | None = None

    def current(self, candidate_id: str) -> CandidatePrismVerdict:
        """Return the verdict bound to ``candidate_id`` (raises KeyError if absent)."""
        return self._by_candidate[candidate_id]

    def latest_candidate_id(self) -> str | None:
        """Return the most recently attached candidate id, or ``None``."""
        return self._latest

    def _attach(self, verdict: CandidatePrismVerdict) -> None:
        # Mark prior current verdicts as stale.
        for cid, existing in list(self._by_candidate.items()):
            if cid != verdict.candidate_id and existing.status == "current":
                self._by_candidate[cid] = CandidatePrismVerdict(
                    review_id=existing.review_id,
                    candidate_id=existing.candidate_id,
                    evidence_snapshot_digest=existing.evidence_snapshot_digest,
                    verdict=existing.verdict,
                    status="stale",
                )
        self._by_candidate[verdict.candidate_id] = verdict
        self._latest = verdict.candidate_id


def attach_candidate_review(
    store: CandidateReviewStore, verdict: CandidatePrismVerdict
) -> None:
    """Attach a candidate Prism verdict to the store (AC-FR1800-01).

    Args:
        store: :class:`CandidateReviewStore`.
        verdict: :class:`CandidatePrismVerdict`.

    Raises:
        CandidatePrismReviewError: With ``REV_SCHEMA_INVALID`` if the verdict
            value is not ``PASS`` or ``REVISE``.
    """
    if verdict.verdict not in _VALID_VERDICTS:
        raise CandidatePrismReviewError(
            "REV_SCHEMA_INVALID",
            f"verdict {verdict.verdict!r} not in {sorted(_VALID_VERDICTS)}",
        )
    store._attach(verdict)


def can_enter_m_security(
    store: CandidateReviewStore,
    candidate_id: str,
    *,
    local_passed: bool,
    ci_passed: bool,
) -> bool:
    """Return ``True`` only when local+CI PASS and current Prism PASS (AC-FR1800-01)."""
    if not local_passed or not ci_passed:
        return False
    try:
        verdict = store.current(candidate_id)
    except KeyError:
        return False
    if verdict.status != "current" or verdict.verdict != "PASS":
        return False
    # If a newer candidate exists, the older one is stale and cannot enter
    # M-SECURITY.
    latest = store.latest_candidate_id()
    if latest is not None and latest != candidate_id:
        return False
    return True
