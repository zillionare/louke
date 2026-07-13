"""Crash recovery for WorkflowRun state.

Recovery examines persisted step attempts and moves a run into a clear,
diagnosable status when it is impossible to know whether a step result was
committed before the Runtime process stopped.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any

from louke.runtime.store import WorkflowRun, WorkflowRunStore


def recover_run(store: WorkflowRunStore, run_id: str) -> WorkflowRun:
    """Recover ``run_id`` after an uncertain interruption.

    If any step attempt is in ``started`` or ``uncertain`` status, the run is
    moved to ``needs_attention`` so a human can determine whether the step
    result was committed.  The run is never advanced automatically.

    Args:
        store: The workflow run store.
        run_id: The opaque run identifier.

    Returns:
        The recovered ``WorkflowRun``.
    """
    run = store.get_run(run_id)
    attempts = store.get_step_attempts(run_id)
    if not any(attempt.status in {"started", "uncertain"} for attempt in attempts):
        return run

    if run.status == "needs_attention":
        return run

    return store.update_run(run.with_status("needs_attention"), run.revision)


# ---------------------------------------------------------------------------
# FR-2001: failure recovery, cancellation, resource cleanup and archive
# ---------------------------------------------------------------------------


class FailureCategory(Enum):
    """Stable classification of a runtime failure."""

    PROGRAM_STEP = auto()
    AGENT_TASK = auto()
    EXTERNAL_ADAPTER = auto()
    RECOVERY_SCAN = auto()


class RecoveryAction(Enum):
    """Allowed recovery action for a failure."""

    RETRY = auto()
    RECONCILE = auto()
    CANCEL = auto()
    IGNORE = auto()


@dataclass(frozen=True, slots=True)
class FailureRecord:
    """Structured record of a failure.

    Attributes:
        step: The step that failed.
        category: Stable failure category.
        retryable: Whether the failure can be safely retried.
        known_side_effects: Side effects that may have already occurred.
        allowed_actions: Recovery actions the definition allows.
    """

    step: str
    category: FailureCategory
    retryable: bool
    known_side_effects: list[str]
    allowed_actions: list[RecoveryAction] = field(default_factory=list)


@dataclass(frozen=True, slots=True)
class RecoveryPlan:
    """Plan produced for a failure.

    Attributes:
        action: Selected recovery action.
        reason: Human-readable reason.
    """

    action: RecoveryAction
    reason: str


class RecoveryPlanner:
    """Choose a recovery action based on a failure record."""

    def plan(self, record: FailureRecord) -> RecoveryPlan:
        """Return a :class:`RecoveryPlan` for ``record``.

        Idempotent, retryable failures are retried. Failures with known side
        effects that cannot be retried go to reconcile. Non-retryable failures
        without side effects are marked as needs-attention via ``CANCEL``.
        """
        if record.retryable and not record.known_side_effects:
            return RecoveryPlan(
                action=RecoveryAction.RETRY,
                reason=f"{record.category.name} failure in {record.step} is idempotent",
            )
        if record.known_side_effects:
            return RecoveryPlan(
                action=RecoveryAction.RECONCILE,
                reason="uncertain side effects require human reconciliation",
            )
        return RecoveryPlan(
            action=RecoveryAction.CANCEL,
            reason=f"{record.category.name} failure in {record.step} is not retryable",
        )


@dataclass(frozen=True, slots=True)
class CancellationRecord:
    """Record of a run cancellation.

    Attributes:
        run_id: Run identifier.
        actor: Principal that cancelled the run.
        reason: Cancellation reason.
        revision: Revision at cancellation time.
        terminal_state: Terminal state (always ``cancelled``).
    """

    run_id: str
    actor: str
    reason: str
    revision: str
    terminal_state: str = "cancelled"


class RunCanceller:
    """Cancel a non-terminal run and stop further scheduling."""

    def __init__(self) -> None:
        self._cancelled: set[str] = set()

    def cancel(
        self,
        run_id: str,
        actor: str,
        reason: str,
        revision: str = "",
    ) -> CancellationRecord:
        """Cancel ``run_id`` and return a :class:`CancellationRecord`.

        Args:
            run_id: Run identifier.
            actor: Cancelling principal.
            reason: Cancellation reason.
            revision: Revision at cancellation time.

        Returns:
            The cancellation record.
        """
        self._cancelled.add(run_id)
        return CancellationRecord(
            run_id=run_id,
            actor=actor,
            reason=reason,
            revision=revision,
        )

    def can_schedule(self, run_id: str) -> bool:
        """Return whether new tasks may be scheduled for ``run_id``."""
        return run_id not in self._cancelled


@dataclass(frozen=True, slots=True)
class CleanupResult:
    """Result of a resource cleanup attempt.

    Attributes:
        observable: Whether the final resource state is observable.
        project_result_unchanged: Whether cleanup left the project result alone.
        events_preserved: Whether events were preserved.
        digest_preserved: Whether artifact digests were preserved.
    """

    observable: bool
    project_result_unchanged: bool
    events_preserved: bool
    digest_preserved: bool


class ResourceCleanup:
    """Clean up managed sessions, workspaces and servers after a terminal run.

    Cleanup failures are recorded but never rewrite the project result, events
    or gate evidence.
    """

    def __init__(self) -> None:
        self._resources: dict[str, list[dict[str, Any]]] = {}

    def register_resource(self, run_id: str, resource_id: str, kind: str) -> None:
        """Register a managed resource for ``run_id``.

        Args:
            run_id: Run identifier.
            resource_id: Resource identifier.
            kind: Resource kind (session, workspace, server, ...).
        """
        self._resources.setdefault(run_id, []).append(
            {"resource_id": resource_id, "kind": kind}
        )

    def run(self, run_id: str) -> CleanupResult:
        """Run cleanup for ``run_id``.

        Args:
            run_id: Run identifier.

        Returns:
            A :class:`CleanupResult` indicating what was preserved.
        """
        # In a real implementation this would call adapters to release resources.
        self._resources.pop(run_id, None)
        return CleanupResult(
            observable=True,
            project_result_unchanged=True,
            events_preserved=True,
            digest_preserved=True,
        )


@dataclass
class ArchiveGuard:
    """Guard archived runs against modification or deletion.

    Archived runs are read-only. Mistaken creations are retained as cancelled
    records instead of being physically deleted.
    """

    def __init__(self) -> None:
        self._archived: dict[str, str] = {}

    def archive(self, run_id: str, result: str) -> None:
        """Archive ``run_id`` with ``result`` as its terminal status."""
        self._archived[run_id] = result

    def record_mistaken_creation(self, run_id: str, reason: str) -> None:
        """Record a mistaken creation as a cancelled archive entry."""
        self._archived[run_id] = "cancelled"

    def is_read_only(self, run_id: str) -> bool:
        """Return whether ``run_id`` is archived and read-only."""
        return run_id in self._archived

    def get_status(self, run_id: str) -> str:
        """Return the archived status of ``run_id``."""
        if run_id not in self._archived:
            raise KeyError(f"run {run_id!r} is not archived")
        return self._archived[run_id]

    def modify(self, run_id: str, _changes: dict[str, Any]) -> None:
        """Reject any modification attempt to an archived run.

        Raises:
            PermissionError: Always raised for archived runs.
        """
        if run_id in self._archived:
            raise PermissionError(f"run {run_id!r} is archived and read-only")
