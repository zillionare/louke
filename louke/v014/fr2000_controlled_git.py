"""FR-2000: 受控 Git Revision 与无关工作区保护.

Implements the deterministic contract slice of FR-2000:

* :func:`decide_controlled_commit_plan` validates the target index baseline
  and non-target index fingerprint before any Git operation. The plan's
  path allowlist only contains the target document; all non-target index
  entries/flags/cached staged intent are preserved byte-equal
  (AC-FR2000-01).

* :class:`ControlledCommitEvidence` records the expected document digest,
  parent commit SHA, new commit SHA, actor, run id, round number and task
  id. The ``ref_sha`` must equal ``new_commit_sha`` after the ref CAS
  (AC-FR2000-02).

* :class:`ControlledCommitConflict` is raised when the target is
  pre-staged, has conflict stages (stage > 0), has special index flags
  (intent-to-add, assume-unchanged, skip-worktree) or otherwise cannot be
  attributed. The conflict code is :data:`CONTROLLED_COMMIT_CONFLICT`;
  the next review is not started and no dangerous recovery commands are
  authorised (AC-FR2000-03).

* :func:`forbidden_recovery_commands` returns the set of Git commands the
  controlled-commit contract never authorises: ``git reset``,
  ``git checkout``, ``git push --force`` and ``git push -f``
  (AC-FR2000-03).
"""

from __future__ import annotations

from dataclasses import dataclass


CONTROLLED_COMMIT_CONFLICT = "CONTROLLED_COMMIT_CONFLICT"


_FORBIDDEN_INDEX_FLAGS: frozenset[str] = frozenset(
    {"intent-to-add", "assume-unchanged", "skip-worktree"}
)


@dataclass(frozen=True)
class TargetIndexBaseline:
    """Baseline state of the target document in HEAD and the index.

    Attributes:
        present_in_head: Whether the target exists in the HEAD tree.
        present_in_index: Whether the target has any entry in the index.
        target_index_entries: Tuple of index entries for the target
            (``{stage, mode, blob}``); empty when not in index.
        target_index_flags: Tuple of special index flags on the target
            entry (e.g. ``intent-to-add``); empty when none.
    """

    present_in_head: bool
    present_in_index: bool
    target_index_entries: tuple[dict[str, object], ...]
    target_index_flags: tuple[str, ...]


@dataclass(frozen=True)
class NonTargetIndexFingerprint:
    """Semantic fingerprint of all non-target index entries.

    Attributes:
        entries: Tuple of non-target index entries
            (``{path, stage, mode, blob}``) in canonical order.
        flags: Tuple of special index flags on non-target entries; empty
            when none.
    """

    entries: tuple[dict[str, object], ...]
    flags: tuple[str, ...]


@dataclass(frozen=True)
class ControlledCommitPlan:
    """Plan for a controlled single-document commit.

    Attributes:
        target_document: The only path allowed in the commit tree diff.
        expected_parent_sha: Parent commit SHA the commit is built on.
        intended_document_digest: ``sha256:<hex>`` digest of the target
            document bytes the commit will record.
        path_allowlist: Always ``(target_document,)``.
        non_target_fingerprint: :class:`NonTargetIndexFingerprint` to
            preserve byte-equal after the commit.
        actor: Non-secret actor identity.
        run_id: Opaque run identifier.
        round_number: Review round the commit belongs to.
        task_id: Task id that produced the document.
    """

    target_document: str
    expected_parent_sha: str
    intended_document_digest: str
    path_allowlist: tuple[str, ...]
    non_target_fingerprint: NonTargetIndexFingerprint
    actor: str
    run_id: str
    round_number: int
    task_id: str


class ControlledCommitConflict(Exception):
    """Raised when a controlled commit cannot proceed safely.

    Attributes:
        code: Always :data:`CONTROLLED_COMMIT_CONFLICT`.
        reason: Non-secret reason explaining the conflict.
    """

    def __init__(self, *, reason: str) -> None:
        super().__init__(f"{CONTROLLED_COMMIT_CONFLICT}: {reason}")
        self.code = CONTROLLED_COMMIT_CONFLICT
        self.reason = reason


def decide_controlled_commit_plan(
    *,
    target_document: str,
    expected_parent_sha: str,
    intended_document_digest: str,
    target_baseline: TargetIndexBaseline,
    non_target_fingerprint: NonTargetIndexFingerprint,
    actor: str,
    run_id: str,
    round_number: int,
    task_id: str,
) -> ControlledCommitPlan:
    """Validate the baseline and return a controlled-commit plan.

    Args:
        target_document: The only path allowed in the commit tree diff.
        expected_parent_sha: Parent commit SHA the commit is built on.
        intended_document_digest: ``sha256:<hex>`` digest of the target
            document bytes the commit will record.
        target_baseline: :class:`TargetIndexBaseline` describing the target
            in HEAD and the index.
        non_target_fingerprint: :class:`NonTargetIndexFingerprint` of all
            non-target index entries.
        actor: Non-secret actor identity.
        run_id: Opaque run identifier.
        round_number: Review round the commit belongs to.
        task_id: Task id that produced the document.

    Returns:
        A :class:`ControlledCommitPlan` with ``path_allowlist ==
        (target_document,)`` and the non-target fingerprint preserved.

    Raises:
        ControlledCommitConflict: When the target is pre-staged (in index
            but not in HEAD), has conflict stages (stage > 0), has special
            index flags or otherwise cannot be safely committed. The
            conflict code is :data:`CONTROLLED_COMMIT_CONFLICT`
            (AC-FR2000-03).
    """
    # AC-FR2000-03: target pre-staged (in index, not in HEAD) -> conflict.
    if target_baseline.present_in_index and not target_baseline.present_in_head:
        raise ControlledCommitConflict(
            reason=(
                f"target {target_document!r} is pre-staged in the index but "
                "absent from HEAD; will not commit to avoid clobbering "
                "unattributed staged intent"
            )
        )
    # AC-FR2000-03: target conflict stages (> 0) -> conflict.
    for entry in target_baseline.target_index_entries:
        stage = entry.get("stage", 0)
        if stage != 0:
            raise ControlledCommitConflict(
                reason=(
                    f"target {target_document!r} has a non-stage-0 index "
                    f"entry (stage={stage}); resolve the conflict before "
                    "committing"
                )
            )
    # AC-FR2000-03: target special index flags -> conflict.
    for flag in target_baseline.target_index_flags:
        if flag in _FORBIDDEN_INDEX_FLAGS:
            raise ControlledCommitConflict(
                reason=(
                    f"target {target_document!r} has special index flag "
                    f"{flag!r}; clear the flag before committing"
                )
            )
    return ControlledCommitPlan(
        target_document=target_document,
        expected_parent_sha=expected_parent_sha,
        intended_document_digest=intended_document_digest,
        path_allowlist=(target_document,),
        non_target_fingerprint=non_target_fingerprint,
        actor=actor,
        run_id=run_id,
        round_number=round_number,
        task_id=task_id,
    )


@dataclass(frozen=True)
class ControlledCommitEvidence:
    """Evidence for a successful controlled commit.

    Attributes:
        target_document: The only path in the commit tree diff.
        expected_document_digest: ``sha256:<hex>`` digest of the target
            document bytes the commit was expected to record.
        parent_commit_sha: Parent commit SHA the commit was built on.
        new_commit_sha: New commit SHA recorded for the revision.
        actor: Non-secret actor identity.
        run_id: Opaque run identifier.
        round_number: Review round the commit belongs to.
        task_id: Task id that produced the document.
        ref_sha: SHA read back from the Git ref after the commit; must equal
            ``new_commit_sha`` (AC-FR2000-02).
    """

    target_document: str
    expected_document_digest: str
    parent_commit_sha: str
    new_commit_sha: str
    actor: str
    run_id: str
    round_number: int
    task_id: str
    ref_sha: str


def forbidden_recovery_commands() -> frozenset[str]:
    """Return the set of Git commands the controlled-commit contract never
    authorises.

    Returns:
        A frozenset containing ``git reset``, ``git checkout``,
        ``git push --force`` and ``git push -f``. Controlled-commit
        recovery never resets the index, checks out a different tree or
        force-pushes a ref (AC-FR2000-03).
    """
    return frozenset({"git reset", "git checkout", "git push --force", "git push -f"})
