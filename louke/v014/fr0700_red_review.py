"""FR-0700: Red independent review & correction.

Runtime dispatches Prism to review the precise ``B..R`` range, current
requirements/Acceptance, test-layer contract and Red evidence.  The
verdict binds the same ``R`` and evidence digest.  Only when program
gate AND Prism are both PASS may Green start.  REVISE, unexpected test
PASS, wrong failure category or diff out-of-scope must produce a new
Red correction attempt.  Any test tree change creates a new ``R`` and
makes the old review stale (AC-FR0700-01).
"""

from __future__ import annotations

from dataclasses import dataclass

ERROR_CODES = (
    "RGR_RED_UNEXPECTED_PASS",
    "RGR_RED_REVIEW_NOT_CURRENT",
    "RGR_RED_FAILURE_INVALID",
)


class RedReviewError(Exception):
    """A fail-closed Red review rejection carrying a stable code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


@dataclass(frozen=True)
class PrismRedVerdict:
    """A Prism review verdict for a Red checkpoint (AC-FR0700-01).

    Attributes:
        review_id: Stable review identity.
        baseline_oid: ``B`` commit OID the review is bound to.
        red_oid: ``R`` commit OID the review is bound to.
        evidence_digest: ``sha256:<hex>`` of the evidence snapshot.
        verdict: ``PASS|REVISE|UNEXPECTED_PASS``.
        status: ``current`` (default) or ``stale`` once a newer R arrives.
    """

    review_id: str
    baseline_oid: str
    red_oid: str
    evidence_digest: str
    verdict: str
    status: str = "current"


class RedReviewStore:
    """In-memory store of Prism Red verdicts keyed by ``R`` OID (AC-FR0700-01)."""

    def __init__(self) -> None:
        self._by_red: dict[str, PrismRedVerdict] = {}
        self._order: list[str] = []  # red OIDs in attach order

    def current(self, red_oid: str) -> PrismRedVerdict:
        """Return the verdict bound to ``red_oid`` (raises KeyError if absent)."""
        return self._by_red[red_oid]

    def latest_red_oid(self) -> str | None:
        """Return the most recently attached R OID, or ``None`` if empty."""
        return self._order[-1] if self._order else None

    def _attach(self, verdict: PrismRedVerdict) -> None:
        # Mark all prior current verdicts as stale when a new R arrives.
        if verdict.red_oid not in self._by_red:
            for existing_oid in list(self._by_red.keys()):
                existing = self._by_red[existing_oid]
                if existing.status == "current":
                    self._by_red[existing_oid] = PrismRedVerdict(
                        review_id=existing.review_id,
                        baseline_oid=existing.baseline_oid,
                        red_oid=existing.red_oid,
                        evidence_digest=existing.evidence_digest,
                        verdict=existing.verdict,
                        status="stale",
                    )
        self._by_red[verdict.red_oid] = verdict
        if verdict.red_oid not in self._order:
            self._order.append(verdict.red_oid)


def attach_red_review(
    store: RedReviewStore,
    verdict: PrismRedVerdict,
    *,
    expected_baseline_oid: str | None = None,
) -> None:
    """Attach a Prism Red verdict to the review store (AC-FR0700-01).

    Args:
        store: :class:`RedReviewStore` for the run/task/attempt.
        verdict: The :class:`PrismRedVerdict` to attach.
        expected_baseline_oid: Optional ``B`` OID the verdict must bind to;
            mismatch raises ``RGR_RED_REVIEW_NOT_CURRENT``.

    Raises:
        RedReviewError: With ``RGR_RED_UNEXPECTED_PASS`` if verdict is
            ``UNEXPECTED_PASS`` (the tests unexpectedly passed during
            review), or with ``RGR_RED_REVIEW_NOT_CURRENT`` if the bound
            baseline does not match ``expected_baseline_oid``.
    """
    if verdict.verdict == "UNEXPECTED_PASS":
        raise RedReviewError(
            "RGR_RED_UNEXPECTED_PASS",
            f"Prism review {verdict.review_id} reported unexpected test PASS",
        )
    if (
        expected_baseline_oid is not None
        and verdict.baseline_oid != expected_baseline_oid
    ):
        raise RedReviewError(
            "RGR_RED_REVIEW_NOT_CURRENT",
            f"verdict baseline {verdict.baseline_oid} != expected {expected_baseline_oid}",
        )
    store._attach(verdict)


def can_start_green(
    store: RedReviewStore,
    *,
    red_oid: str,
    program_passed: bool,
) -> bool:
    """Return ``True`` only when program gate AND Prism PASS are current (AC-FR0700-01)."""
    if not program_passed:
        return False
    try:
        verdict = store.current(red_oid)
    except KeyError:
        return False
    if verdict.status != "current":
        return False
    if verdict.verdict != "PASS":
        return False
    # If a newer R has been attached, the older one is stale and cannot
    # be used to start Green.
    latest = store.latest_red_oid()
    if latest is not None and latest != red_oid:
        return False
    return True
