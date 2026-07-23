"""FR-0800: Park/No-Go 的 Backlog 与安全退出.

Implements the deterministic contract slice of FR-0800:

* :func:`apply_park_no_go_exit` records the Park/No-Go decision as a single
  canonical Backlog entry with Story identity/digest, decision, reason,
  actor and source run; the Project enters the corresponding terminal state
  (``parked`` or ``no_go``) and the M-SPEC task count is 0 (AC-FR0800-01).
  Repeated calls with the same identity return the same entry id (idempotent
  per ``(workspace_id, run_id, decision)``).

* :func:`evaluate_branch_cleanup_safety` decides whether the local release
  branch may be deleted. Deletion is only permitted when the local ref
  exists, no remote ref exists, the local branch has no commits beyond the
  initial Story commit and no dirty workspace paths are present. The
  permitted command is exactly ``git branch -d releases/0.14.0``; force-push
  and reset are never authorised (AC-FR0800-02, AC-FR0800-03).

* When deletion is unsafe the decision puts the run into ``needs_attention``
  and lists the blocking identities (remote ref, unattributed commits, dirty
  paths) so the page can surface them (AC-FR0800-03).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass


_TERMINAL_PROJECT_STATUS: dict[str, str] = {
    "Park": "parked",
    "No-Go": "no_go",
}


@dataclass(frozen=True)
class ParkNoGoRecord:
    """Input record for a Park/No-Go decision.

    Attributes:
        workspace_id: Workspace the run belongs to.
        run_id: Opaque run identifier the decision is bound to.
        story_revision: Story revision the decision was made on.
        story_digest: ``sha256:<hex>`` digest of the Story bytes.
        decision: ``Park`` or ``No-Go``.
        reason: Non-empty human-supplied reason.
        actor: Non-secret Human principal identity.
        source_run: Opaque run identifier that produced the Backlog entry;
            equal to ``run_id`` for direct Park/No-Go exits.
    """

    workspace_id: str
    run_id: str
    story_revision: int
    story_digest: str
    decision: str
    reason: str
    actor: str
    source_run: str


@dataclass(frozen=True)
class ParkNoGoBacklogEntry:
    """Canonical Backlog entry produced by Park/No-Go exit.

    Attributes:
        entry_id: Stable id derived from
            ``(workspace_id, run_id, decision)``.
        workspace_id: Workspace the entry belongs to.
        run_id: Source run id.
        story_revision: Story revision the decision was made on.
        story_digest: ``sha256:<hex>`` digest of the Story bytes.
        decision: ``Park`` or ``No-Go``.
        reason: Non-empty reason.
        actor: Non-secret Human principal identity.
        source_run: Opaque run identifier that produced the entry.
    """

    entry_id: str
    workspace_id: str
    run_id: str
    story_revision: int
    story_digest: str
    decision: str
    reason: str
    actor: str
    source_run: str


@dataclass(frozen=True)
class ParkNoGoExitResult:
    """Result of :func:`apply_park_no_go_exit`.

    Attributes:
        entry: The canonical Backlog entry.
        backlog_entry_count: Always ``1`` (idempotent).
        project_status: ``parked`` for Park, ``no_go`` for No-Go.
        m_spec_task_count: Always ``0``; Park/No-Go does not dispatch M-SPEC.
    """

    entry: ParkNoGoBacklogEntry
    backlog_entry_count: int
    project_status: str
    m_spec_task_count: int


def _entry_id_for(record: ParkNoGoRecord) -> str:
    payload = f"{record.workspace_id}|{record.run_id}|{record.decision}"
    return f"bl_{hashlib.sha256(payload.encode('utf-8')).hexdigest()[:24]}"


def apply_park_no_go_exit(record: ParkNoGoRecord) -> ParkNoGoExitResult:
    """Apply a Park/No-Go exit and return the canonical Backlog entry.

    Args:
        record: The :class:`ParkNoGoRecord` describing the decision.

    Returns:
        A :class:`ParkNoGoExitResult` with a single Backlog entry, the
        terminal Project status and ``m_spec_task_count == 0``.

    Raises:
        ValueError: If ``record.decision`` is not ``Park`` or ``No-Go``, or
            if ``record.reason`` is empty.

    Side effects:
        None. The function is pure; the Driver/Store adapter persists the
        returned entry.
    """
    if record.decision not in _TERMINAL_PROJECT_STATUS:
        raise ValueError(
            f"decision must be one of {sorted(_TERMINAL_PROJECT_STATUS)}; "
            f"got {record.decision!r}"
        )
    if not record.reason.strip():
        raise ValueError("reason must be non-empty")
    entry = ParkNoGoBacklogEntry(
        entry_id=_entry_id_for(record),
        workspace_id=record.workspace_id,
        run_id=record.run_id,
        story_revision=record.story_revision,
        story_digest=record.story_digest,
        decision=record.decision,
        reason=record.reason,
        actor=record.actor,
        source_run=record.source_run,
    )
    return ParkNoGoExitResult(
        entry=entry,
        backlog_entry_count=1,
        project_status=_TERMINAL_PROJECT_STATUS[record.decision],
        m_spec_task_count=0,
    )


@dataclass(frozen=True)
class BranchCleanupDecision:
    """Decision returned by :func:`evaluate_branch_cleanup_safety`.

    Attributes:
        can_delete: ``True`` only when the local release branch may be
            safely deleted.
        run_status: ``needs_attention`` when deletion is forbidden; ``ok``
            when deletion is permitted; ``ok`` when the ref is already
            absent.
        blocking_reasons: Non-empty list of blocking identities when
            ``can_delete is False``; empty otherwise.
        permitted_commands: ``('git branch -d releases/0.14.0',)`` when
            ``can_delete is True``; ``()`` otherwise. Never contains
            ``reset`` or ``push --force``.
        already_absent: ``True`` when the local ref does not exist (idempotent
            no-op on retry).
    """

    can_delete: bool
    run_status: str
    blocking_reasons: tuple[str, ...]
    permitted_commands: tuple[str, ...]
    already_absent: bool = False


_REMOTE_REF = "refs/remotes/origin/releases/0.14.0"
_LOCAL_REF = "refs/heads/releases/0.14.0"


def evaluate_branch_cleanup_safety(
    *,
    local_ref_exists: bool,
    remote_ref_exists: bool,
    local_commits_beyond_initial: bool,
    dirty_paths: tuple[str, ...] = (),
) -> BranchCleanupDecision:
    """Decide whether the local release branch may be safely deleted.

    Args:
        local_ref_exists: Whether the local ``refs/heads/releases/0.14.0``
            ref exists.
        remote_ref_exists: Whether the remote ``refs/remotes/origin/
            releases/0.14.0`` ref exists.
        local_commits_beyond_initial: Whether the local branch has commits
            beyond the initial Story commit.
        dirty_paths: Workspace paths with unattributed dirty bytes.

    Returns:
        A :class:`BranchCleanupDecision`. Deletion is only permitted when
        ``local_ref_exists and not remote_ref_exists and not
        local_commits_beyond_initial and not dirty_paths``. The decision
        never authorises ``git reset`` or ``git push --force``.
    """
    if not local_ref_exists:
        return BranchCleanupDecision(
            can_delete=False,
            run_status="ok",
            blocking_reasons=(),
            permitted_commands=(),
            already_absent=True,
        )
    blockers: list[str] = []
    if remote_ref_exists:
        blockers.append(
            f"remote ref {_REMOTE_REF} exists; cannot delete local ref "
            "until remote is reconciled or removed by Human"
        )
    if local_commits_beyond_initial:
        blockers.append(
            "local branch contains unattributed commits beyond the initial "
            "Story commit; will not delete"
        )
    for path in dirty_paths:
        blockers.append(
            f"dirty workspace path {path!r} has unattributed bytes; "
            "will not delete local ref"
        )
    if blockers:
        return BranchCleanupDecision(
            can_delete=False,
            run_status="needs_attention",
            blocking_reasons=tuple(blockers),
            permitted_commands=(),
            already_absent=False,
        )
    return BranchCleanupDecision(
        can_delete=True,
        run_status="ok",
        blocking_reasons=(),
        permitted_commands=("git branch -d releases/0.14.0",),
        already_absent=False,
    )


class BranchCleanupForbidden(Exception):
    """Raised by adapters when a cleanup decision forbids deletion.

    Attributes:
        decision: The :class:`BranchCleanupDecision` that forbade deletion.
    """

    def __init__(self, decision: BranchCleanupDecision) -> None:
        super().__init__(
            "branch cleanup forbidden: " + "; ".join(decision.blocking_reasons)
        )
        self.decision = decision
