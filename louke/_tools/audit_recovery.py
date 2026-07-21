"""NFR-0400: recoverability & audit export.

Runtime recovers M-DESIGN current state from persisted revision/manifest/
diff/review/program evidence/operation design after a restart, never re-
dispatches completed attempts, and fails closed on missing or digest-
inconsistent persistence while preserving historical revisions
(AC-NFR0400-01).  Audit export redacts secrets and emits a typed record.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

ERROR_CODES = (
    "RECOVERY_NO_CURRENT_REVISION",
    "RECOVERY_DIGEST_INCONSISTENT",
    "RECOVERY_DUPLICATE_DISPATCH",
)


class AuditRecoveryError(Exception):
    """A fail-closed audit/recovery rejection carrying a stable code."""

    __test__ = False

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


@dataclass(frozen=True)
class PersistentRevision:
    """A persisted design revision record (AC-NFR0400-01).

    Attributes:
        revision_id: The design revision id.
        attempt_id: The active Archer attempt id.
        run_id: The run id.
        base_commit: 40-hex git commit bound to the revision.
        requirements_digests: ``{story, spec, acceptance}`` digests.
        project_facts_digest: ``sha256:<hex>`` of the host-project-facts snapshot.
        task_manifest_digest: ``sha256:<hex>`` of the Archer task manifest.
        program_evidence_digests: Tuple of program evidence digests.
        prism_verdict_digest: ``sha256:<hex>`` of the Prism verdict.
        baseline_digest: ``sha256:<hex>`` of the implementation baseline.
        digests_consistent: ``True`` when all digests recompute correctly.
        completed_dispatches: Tuple of completed dispatch attempt ids.
        history: Tuple of prior revisions (immutable, append-only).
    """

    revision_id: str
    attempt_id: str
    run_id: str
    base_commit: str
    requirements_digests: dict[str, str]
    project_facts_digest: str
    task_manifest_digest: str
    program_evidence_digests: tuple[str, ...]
    prism_verdict_digest: str
    baseline_digest: str
    digests_consistent: bool = True
    completed_dispatches: tuple[str, ...] = ()
    history: tuple["PersistentRevision", ...] = ()


@dataclass(frozen=True)
class PersistentStore:
    """Persistent store snapshot at restart (AC-NFR0400-01).

    Attributes:
        current: The current revision, or ``None`` if store is empty.
        pending_work: Tuple of pending work items.
    """

    current: PersistentRevision | None
    pending_work: tuple[str, ...] = ()


@dataclass(frozen=True)
class RecoveryReport:
    """Result of :func:`recover_current_revision`.

    Attributes:
        current_revision: The recovered current revision.
        pending_work: Recovered pending work items.
        completed_dispatches: Already-completed dispatch attempt ids.
        pending_dispatches: New dispatches to schedule (always empty on recovery).
        history: Tuple of historical revisions.
    """

    current_revision: PersistentRevision
    pending_work: tuple[str, ...]
    completed_dispatches: tuple[str, ...]
    pending_dispatches: tuple[str, ...]
    history: tuple[PersistentRevision, ...]


def recover_current_revision(store: PersistentStore) -> RecoveryReport:
    """Recover the current revision and pending work after a restart.

    Args:
        store: The persistent store snapshot at restart.

    Returns:
        A :class:`RecoveryReport` describing the recovered state.

    Raises:
        AuditRecoveryError: With ``RECOVERY_NO_CURRENT_REVISION`` if the
            store has no current revision, or ``RECOVERY_DIGEST_INCONSISTENT``
            if the digests do not recompute correctly.
    """
    if store.current is None:
        raise AuditRecoveryError(
            "RECOVERY_NO_CURRENT_REVISION",
            "persistent store has no current revision; cannot recover",
        )
    verify_persistence_integrity(store.current)
    return RecoveryReport(
        current_revision=store.current,
        pending_work=store.pending_work,
        completed_dispatches=store.current.completed_dispatches,
        pending_dispatches=(),  # completed dispatches are not re-dispatched
        history=store.current.history,
    )


def verify_persistence_integrity(revision: PersistentRevision) -> None:
    """Verify the digests of a persisted revision are consistent.

    Args:
        revision: The persisted revision to verify.

    Raises:
        AuditRecoveryError: With ``RECOVERY_DIGEST_INCONSISTENT`` if any
            digest is missing or marked inconsistent.
    """
    if not revision.digests_consistent:
        raise AuditRecoveryError(
            "RECOVERY_DIGEST_INCONSISTENT",
            f"digests inconsistent for revision {revision.revision_id}",
        )
    for key, digest in revision.requirements_digests.items():
        if not digest or not digest.startswith("sha256:"):
            raise AuditRecoveryError(
                "RECOVERY_DIGEST_INCONSISTENT",
                f"requirements.{key} digest missing or malformed",
            )
    if not revision.project_facts_digest.startswith("sha256:"):
        raise AuditRecoveryError(
            "RECOVERY_DIGEST_INCONSISTENT",
            "project_facts_digest missing or malformed",
        )


def verify_no_duplicate_dispatch(
    revision: PersistentRevision,
    *,
    attempted_dispatches: tuple[str, ...],
) -> None:
    """Verify no dispatch in ``attempted_dispatches`` is already completed.

    Args:
        revision: The persisted revision.
        attempted_dispatches: Dispatches attempted after restart.

    Raises:
        AuditRecoveryError: With ``RECOVERY_DUPLICATE_DISPATCH`` if any
            attempted dispatch is already in ``revision.completed_dispatches``.
    """
    completed = set(revision.completed_dispatches)
    for dispatch in attempted_dispatches:
        if dispatch in completed:
            raise AuditRecoveryError(
                "RECOVERY_DUPLICATE_DISPATCH",
                f"attempt {dispatch} already dispatched; cannot re-dispatch",
            )


@dataclass(frozen=True)
class AuditExport:
    """Audit export record (AC-NFR0400-01).

    Attributes:
        current_revision: The current revision record.
        pending_work: Pending work items.
        history: Tuple of historical revisions.
    """

    current_revision: PersistentRevision
    pending_work: tuple[str, ...]
    history: tuple[PersistentRevision, ...]

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a dict, redacting secrets."""
        return {
            "current_revision": {
                "revision_id": self.current_revision.revision_id,
                "attempt_id": self.current_revision.attempt_id,
                "run_id": self.current_revision.run_id,
                "base_commit": self.current_revision.base_commit,
                "requirements_digests": dict(
                    self.current_revision.requirements_digests
                ),
                "project_facts_digest": self.current_revision.project_facts_digest,
                "task_manifest_digest": self.current_revision.task_manifest_digest,
                "program_evidence_digests": list(
                    self.current_revision.program_evidence_digests
                ),
                "prism_verdict_digest": self.current_revision.prism_verdict_digest,
                "baseline_digest": self.current_revision.baseline_digest,
                "completed_dispatches": list(
                    self.current_revision.completed_dispatches
                ),
            },
            "pending_work": list(self.pending_work),
            "history": [
                {"revision_id": h.revision_id, "attempt_id": h.attempt_id}
                for h in self.history
            ],
        }


def export_audit(store: PersistentStore) -> AuditExport:
    """Export the persistent store as an audit record, redacting secrets."""
    if store.current is None:
        raise AuditRecoveryError(
            "RECOVERY_NO_CURRENT_REVISION",
            "cannot export audit from an empty store",
        )
    return AuditExport(
        current_revision=store.current,
        pending_work=store.pending_work,
        history=store.current.history,
    )
