"""FR-2400: M-MILESTONE trace, archive & resource cleanup.

After publish verification, Runtime closes the bidirectional trace
(FR/NFR->AC->Test Plan->task/Issue->R/review->code/test/CI->artifact/
release), updates requirement Issues/Project, archives run/tasks/
reviews/gates/events/diffs/RGR/CI/artifact/security/publish evidence,
and turns the project into read-only history.  Only after publish facts
verified AND all required archives closed may Project/WorkflowRun
``complete`` and release the next main release eligibility.  ``closing``
or ``needs_attention`` may NOT release that eligibility.  Only after
Red commit/tree + evidence enter recoverable archive may Runtime
precisely delete the run-manifest-listed ``refs/louke/rgr/{run}/...``;
close failure keeps ``closing`` idempotent retry, no re-publish
(AC-FR2400-01).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

ERROR_CODES = (
    "TRACE_EDGE_INVALID",
    "TRACE_FORWARD_MISSING",
    "TRACE_REVERSE_ORPHAN",
    "TRACE_AMBIGUOUS",
    "ARCHIVE_PUBLISH_UNCONFIRMED",
    "ARCHIVE_MEMBER_MISSING",
    "ARCHIVE_DIGEST_MISMATCH",
    "ARCHIVE_READBACK_FAILED",
    "CLEANUP_REF_CONFLICT",
    "CLEANUP_FOREIGN_REF",
    "CLEANUP_INCOMPLETE",
    "HISTORY_PROJECTION_FAILED",
    "NEXT_RELEASE_NOT_ELIGIBLE",
)


class MilestoneError(Exception):
    """A fail-closed milestone rejection carrying a stable code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


class MilestoneState(str, Enum):
    """Stable milestone state values (AC-FR2400-01)."""

    CLOSING = "closing"
    COMPLETE = "complete"
    NEEDS_ATTENTION = "needs_attention"


@dataclass(frozen=True)
class ArchiveManifest:
    """Archive manifest listing evidence + Red refs to clean up (AC-FR2400-01).

    Attributes:
        archive_id: Stable archive identity.
        run_id: Bound run id.
        candidate_id: Bound candidate id.
        trace_root: Trace root identity.
        evidence_ids: Tuple of evidence ids included in the archive.
        red_refs: Tuple of ``(refname, expected_oid)`` pairs to clean up.
    """

    archive_id: str
    run_id: str
    candidate_id: str
    trace_root: str
    evidence_ids: tuple[str, ...]
    red_refs: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class CleanupDecision:
    """A single Red ref cleanup decision (AC-FR2400-01).

    Attributes:
        refname: ``refs/louke/rgr/{run}/{task}/{attempt}/red``.
        expected_oid: Expected R OID from the manifest.
        actual_oid: Actual OID read back, or ``""`` if ref is absent.
        status: ``success|idempotent-success|conflict|foreign``.
    """

    refname: str
    expected_oid: str
    actual_oid: str
    status: str


def plan_cleanup(
    manifest: ArchiveManifest,
    *,
    existing_refs: dict[str, str],
) -> list[CleanupDecision]:
    """Plan precise Red ref cleanup based on the archive manifest (AC-FR2400-01).

    Args:
        manifest: :class:`ArchiveManifest` listing refs to clean up.
        existing_refs: Map of existing ref name -> OID on disk.

    Returns:
        A list of :class:`CleanupDecision` for each manifest-listed ref:
        - ``success`` if ref exists with matching OID (will be deleted),
        - ``idempotent-success`` if ref is already absent,
        - ``conflict`` if actual OID != expected OID (no delete).
    """
    out: list[CleanupDecision] = []
    for refname, expected_oid in manifest.red_refs:
        actual = existing_refs.get(refname, "")
        if not actual:
            out.append(
                CleanupDecision(
                    refname=refname,
                    expected_oid=expected_oid,
                    actual_oid="",
                    status="idempotent-success",
                )
            )
        elif actual == expected_oid:
            out.append(
                CleanupDecision(
                    refname=refname,
                    expected_oid=expected_oid,
                    actual_oid=actual,
                    status="success",
                )
            )
        else:
            out.append(
                CleanupDecision(
                    refname=refname,
                    expected_oid=expected_oid,
                    actual_oid=actual,
                    status="conflict",
                )
            )
    return out


class ArchiveStore:
    """In-memory archive store tracking milestone state (AC-FR2400-01)."""

    def __init__(self) -> None:
        self._state: MilestoneState = MilestoneState.CLOSING
        self._completed = False

    @property
    def state(self) -> MilestoneState:
        return self._state

    def set_state(self, state: MilestoneState) -> None:
        self._state = state
        if state == MilestoneState.COMPLETE:
            self._completed = True

    def next_release_eligible(self) -> bool:
        """Return ``True`` only if milestone has reached COMPLETE."""
        return self._completed


def close_milestone(
    *,
    store: ArchiveStore,
    run_id: str,
    candidate_id: str,
    publish_facts_verified: bool,
    trace_closed: bool,
    archive_manifest: ArchiveManifest,
    cleanup_results: tuple[CleanupDecision, ...],
) -> MilestoneState:
    """Close the milestone after publish verification (AC-FR2400-01).

    Args:
        store: :class:`ArchiveStore` for state tracking.
        run_id: Bound run id.
        candidate_id: Bound candidate id.
        publish_facts_verified: ``True`` if all publish facts are verified.
        trace_closed: ``True`` if bidirectional trace is closed.
        archive_manifest: :class:`ArchiveManifest` for the run.
        cleanup_results: Tuple of :class:`CleanupDecision` from ``plan_cleanup``.

    Returns:
        A :class:`MilestoneState`: ``complete`` only when publish facts
        verified + trace closed + no cleanup conflict; otherwise
        ``closing`` or ``needs_attention``.
    """
    if not publish_facts_verified or not trace_closed:
        store.set_state(MilestoneState.CLOSING)
        return MilestoneState.CLOSING
    if any(c.status == "conflict" for c in cleanup_results):
        store.set_state(MilestoneState.NEEDS_ATTENTION)
        return MilestoneState.NEEDS_ATTENTION
    store.set_state(MilestoneState.COMPLETE)
    return MilestoneState.COMPLETE
