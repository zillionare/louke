"""FR-2000: 受控 Git Revision 与无关工作区保护.

AC references:
- AC-FR2000-01: when the workspace has pre-staged, unstaged, untracked and
  other-document modifications, a controlled commit of the current
  ``spec.md`` revision only contains ``spec.md`` in its tree diff; all
  other file bytes and index states remain byte-equal to before the
  commit.
- AC-FR2000-02: a successful controlled commit records the expected
  document digest, parent SHA, commit SHA, actor, run, round and task in
  the revision evidence; the Git ref SHA read back equals the recorded
  commit SHA.
- AC-FR2000-03: when the index conflicts, the branch moved or the
  document source cannot be attributed, a controlled commit attempt
  returns ``CONTROLLED_COMMIT_CONFLICT``; the next review is not started
  and no reset/checkout/force-push or unrelated file changes occur.
"""

from __future__ import annotations

import pytest

from louke.v014.fr2000_controlled_git import (
    CONTROLLED_COMMIT_CONFLICT,
    ControlledCommitConflict,
    ControlledCommitEvidence,
    NonTargetIndexFingerprint,
    TargetIndexBaseline,
    decide_controlled_commit_plan,
    forbidden_recovery_commands,
)


# AC-FR2000-01 ---------------------------------------------------------------
def test_controlled_commit_plan_only_includes_target_document() -> None:
    """AC-FR2000-01: the controlled commit plan's path allowlist only
    contains the target document."""
    plan = decide_controlled_commit_plan(
        target_document="spec.md",
        expected_parent_sha="p" * 40,
        intended_document_digest="sha256:" + "d" * 64,
        target_baseline=TargetIndexBaseline(
            present_in_head=False,
            present_in_index=False,
            target_index_entries=(),
            target_index_flags=(),
        ),
        non_target_fingerprint=NonTargetIndexFingerprint(
            entries=(
                {"path": "notes.md", "stage": 0, "mode": "100644", "blob": "n" * 40},
                {"path": "scratch.py", "stage": 0, "mode": "100644", "blob": "s" * 40},
            ),
            flags=(),
        ),
        actor="human:alice",
        run_id="run_1",
        round_number=2,
        task_id="task_sage_1",
    )
    assert plan.path_allowlist == ("spec.md",)
    assert "notes.md" not in plan.path_allowlist
    assert "scratch.py" not in plan.path_allowlist


def test_controlled_commit_plan_preserves_non_target_index_entries() -> None:
    """AC-FR2000-01: the plan records the non-target index fingerprint so
    callers can verify other index entries remain byte-equal after the
    commit."""
    fingerprint = NonTargetIndexFingerprint(
        entries=({"path": "notes.md", "stage": 0, "mode": "100644", "blob": "n" * 40},),
        flags=(),
    )
    plan = decide_controlled_commit_plan(
        target_document="spec.md",
        expected_parent_sha="p" * 40,
        intended_document_digest="sha256:" + "d" * 64,
        target_baseline=TargetIndexBaseline(
            present_in_head=False,
            present_in_index=False,
            target_index_entries=(),
            target_index_flags=(),
        ),
        non_target_fingerprint=fingerprint,
        actor="human:alice",
        run_id="run_1",
        round_number=2,
        task_id="task_sage_1",
    )
    assert plan.non_target_fingerprint == fingerprint


# AC-FR2000-02 ---------------------------------------------------------------
def test_controlled_commit_evidence_records_all_required_fields() -> None:
    """AC-FR2000-02: the evidence records expected document digest, parent
    SHA, commit SHA, actor, run, round and task; the ref SHA equals the
    commit SHA."""
    evidence = ControlledCommitEvidence(
        target_document="spec.md",
        expected_document_digest="sha256:" + "d" * 64,
        parent_commit_sha="p" * 40,
        new_commit_sha="c" * 40,
        actor="human:alice",
        run_id="run_1",
        round_number=2,
        task_id="task_sage_1",
        ref_sha="c" * 40,
    )
    assert evidence.expected_document_digest == "sha256:" + "d" * 64
    assert evidence.parent_commit_sha == "p" * 40
    assert evidence.new_commit_sha == "c" * 40
    assert evidence.actor == "human:alice"
    assert evidence.run_id == "run_1"
    assert evidence.round_number == 2
    assert evidence.task_id == "task_sage_1"
    # AC-FR2000-02: ref SHA equals the recorded commit SHA.
    assert evidence.ref_sha == evidence.new_commit_sha


# AC-FR2000-03 ---------------------------------------------------------------
def test_target_pre_staged_conflict_raises_controlled_commit_conflict() -> None:
    """AC-FR2000-03: when the target document is pre-staged in the index,
    the plan raises CONTROLLED_COMMIT_CONFLICT."""
    with pytest.raises(ControlledCommitConflict) as exc_info:
        decide_controlled_commit_plan(
            target_document="spec.md",
            expected_parent_sha="p" * 40,
            intended_document_digest="sha256:" + "d" * 64,
            target_baseline=TargetIndexBaseline(
                present_in_head=False,
                present_in_index=True,
                target_index_entries=(
                    {"stage": 0, "mode": "100644", "blob": "x" * 40},
                ),
                target_index_flags=(),
            ),
            non_target_fingerprint=NonTargetIndexFingerprint(entries=(), flags=()),
            actor="human:alice",
            run_id="run_1",
            round_number=2,
            task_id="task_sage_1",
        )
    assert exc_info.value.code == CONTROLLED_COMMIT_CONFLICT
    assert (
        "pre-staged" in exc_info.value.reason.lower()
        or "index" in exc_info.value.reason.lower()
    )


def test_target_conflict_stage_raises_controlled_commit_conflict() -> None:
    """AC-FR2000-03: a target index entry in conflict stage (stage > 0)
    raises CONTROLLED_COMMIT_CONFLICT."""
    with pytest.raises(ControlledCommitConflict):
        decide_controlled_commit_plan(
            target_document="spec.md",
            expected_parent_sha="p" * 40,
            intended_document_digest="sha256:" + "d" * 64,
            target_baseline=TargetIndexBaseline(
                present_in_head=True,
                present_in_index=True,
                target_index_entries=(
                    {"stage": 1, "mode": "100644", "blob": "x" * 40},
                    {"stage": 2, "mode": "100644", "blob": "y" * 40},
                ),
                target_index_flags=(),
            ),
            non_target_fingerprint=NonTargetIndexFingerprint(entries=(), flags=()),
            actor="human:alice",
            run_id="run_1",
            round_number=2,
            task_id="task_sage_1",
        )


def test_target_special_index_flag_raises_controlled_commit_conflict() -> None:
    """AC-FR2000-03: a target index entry with a special flag
    (intent-to-add, assume-unchanged, skip-worktree) raises
    CONTROLLED_COMMIT_CONFLICT."""
    for flag in ("intent-to-add", "assume-unchanged", "skip-worktree"):
        with pytest.raises(ControlledCommitConflict):
            decide_controlled_commit_plan(
                target_document="spec.md",
                expected_parent_sha="p" * 40,
                intended_document_digest="sha256:" + "d" * 64,
                target_baseline=TargetIndexBaseline(
                    present_in_head=False,
                    present_in_index=True,
                    target_index_entries=(
                        {"stage": 0, "mode": "100644", "blob": "x" * 40},
                    ),
                    target_index_flags=(flag,),
                ),
                non_target_fingerprint=NonTargetIndexFingerprint(entries=(), flags=()),
                actor="human:alice",
                run_id="run_1",
                round_number=2,
                task_id="task_sage_1",
            )


def test_no_dangerous_recovery_commands_are_authorised() -> None:
    """AC-FR2000-03: the controlled-commit contract never authorises
    reset/checkout/force-push."""
    forbidden = forbidden_recovery_commands()
    assert "git reset" in forbidden
    assert "git checkout" in forbidden
    assert "git push --force" in forbidden
    assert "git push -f" in forbidden
