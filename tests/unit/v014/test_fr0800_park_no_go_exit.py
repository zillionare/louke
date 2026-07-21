"""FR-0800: Park/No-Go 的 Backlog 与安全退出.

AC references:
- AC-FR0800-01: Human selects Park or No-Go with a reason; Runtime exits the
  run idempotently. The canonical Backlog contains exactly one entry with
  Story identity/digest, decision, reason, actor and source run; the Project
  is in the corresponding terminal state and the M-SPEC task count is 0.
- AC-FR0800-02: when the local release branch only contains the initial
  Story commit and no other modifications, Park/No-Go cleanup deletes the
  local ref on the first call and is a no-op on the second; the Backlog
  entry count stays at one.
- AC-FR0800-03: when the release branch contains unattributed commits,
  dirty files or a remote ref, Park/No-Go cleanup puts the run into
  ``needs_attention``, lists the blocking identities, preserves the relevant
  refs and user file bytes, and performs no force/reset calls.
"""

from __future__ import annotations

import pytest

from louke.v014.fr0800_park_no_go_exit import (
    BranchCleanupDecision,
    ParkNoGoRecord,
    apply_park_no_go_exit,
    evaluate_branch_cleanup_safety,
)


def _record(decision: str = "Park") -> ParkNoGoRecord:
    return ParkNoGoRecord(
        workspace_id="ws_1",
        run_id="run_1",
        story_revision=3,
        story_digest="sha256:" + "a" * 64,
        decision=decision,
        reason="Out of scope this release.",
        actor="human:alice",
        source_run="run_1",
    )


# AC-FR0800-01 ---------------------------------------------------------------
def test_park_no_go_produces_single_backlog_entry_in_terminal_state() -> None:
    """AC-FR0800-01: a Park/No-Go decision produces exactly one canonical
    Backlog entry with full identity; the Project is in the corresponding
    terminal state and no M-SPEC task is dispatched."""
    record = _record(decision="Park")
    result = apply_park_no_go_exit(record)
    assert result.backlog_entry_count == 1
    assert result.project_status == "parked"
    assert result.m_spec_task_count == 0
    assert result.entry.story_digest == record.story_digest
    assert result.entry.decision == "Park"
    assert result.entry.reason == record.reason
    assert result.entry.actor == "human:alice"
    assert result.entry.source_run == "run_1"


def test_no_go_produces_terminal_no_go_state() -> None:
    """AC-FR0800-01: No-Go routes to the ``no_go`` terminal Project state."""
    record = _record(decision="No-Go")
    result = apply_park_no_go_exit(record)
    assert result.project_status == "no_go"
    assert result.entry.decision == "No-Go"


def test_park_no_go_idempotent_under_repeated_calls() -> None:
    """AC-FR0800-01: repeated Park/No-Go exits with the same identity produce
    exactly one Backlog entry."""
    record = _record()
    first = apply_park_no_go_exit(record)
    second = apply_park_no_go_exit(record)
    assert first.backlog_entry_count == 1
    assert second.backlog_entry_count == 1
    assert first.entry.entry_id == second.entry.entry_id


# AC-FR0800-02 ---------------------------------------------------------------
def test_safe_branch_cleanup_deletes_local_ref_then_no_op() -> None:
    """AC-FR0800-02: when the local release branch only has the initial
    Story commit and no dirty/remote, the first cleanup deletes the local
    ref and the second is a no-op."""
    decision = evaluate_branch_cleanup_safety(
        local_ref_exists=True,
        remote_ref_exists=False,
        local_commits_beyond_initial=False,
        dirty_paths=(),
    )
    assert isinstance(decision, BranchCleanupDecision)
    assert decision.can_delete is True
    # Second call (ref no longer exists) is a no-op.
    second = evaluate_branch_cleanup_safety(
        local_ref_exists=False,
        remote_ref_exists=False,
        local_commits_beyond_initial=False,
        dirty_paths=(),
    )
    assert second.can_delete is False
    assert second.already_absent is True


# AC-FR0800-03 ---------------------------------------------------------------
@pytest.mark.parametrize(
    "remote_ref_exists, local_commits_beyond_initial, dirty_paths",
    [
        (True, False, ()),  # remote ref exists
        (False, True, ()),  # unattributed local commit
        (False, False, ("notes.md", "scratch.py")),  # dirty workspace files
    ],
)
def test_unsafe_branch_cleanup_preserves_bytes_and_blocks(
    remote_ref_exists: bool,
    local_commits_beyond_initial: bool,
    dirty_paths: tuple[str, ...],
) -> None:
    """AC-FR0800-03: unattributed commits, dirty files or a remote ref put
    the run into ``needs_attention`` and forbid deletion; no force/reset
    calls are issued."""
    decision = evaluate_branch_cleanup_safety(
        local_ref_exists=True,
        remote_ref_exists=remote_ref_exists,
        local_commits_beyond_initial=local_commits_beyond_initial,
        dirty_paths=dirty_paths,
    )
    assert isinstance(decision, BranchCleanupDecision)
    assert decision.can_delete is False
    assert decision.run_status == "needs_attention"
    assert decision.blocking_reasons  # non-empty
    # Force/reset are never permitted by the decision contract.
    assert decision.permitted_commands == ()


def test_branch_cleanup_forbidden_includes_blocking_identities() -> None:
    """AC-FR0800-03: the cleanup forbidden result lists the blocking
    identities (refs and dirty paths) so the page can surface them."""
    decision = evaluate_branch_cleanup_safety(
        local_ref_exists=True,
        remote_ref_exists=True,
        local_commits_beyond_initial=True,
        dirty_paths=("notes.md",),
    )
    assert decision.can_delete is False
    assert any(
        "refs/remotes/origin/releases/0.14.0" in r for r in decision.blocking_reasons
    )
    assert any("unattributed" in r for r in decision.blocking_reasons)
    assert any("notes.md" in r for r in decision.blocking_reasons)


def test_branch_cleanup_decision_never_authorises_force_or_reset() -> None:
    """AC-FR0800-03: the decision contract never authorises ``git reset`` or
    ``git push --force``; only ``git branch -d`` (delete merged) is permitted
    and only on the safe path."""
    safe = evaluate_branch_cleanup_safety(
        local_ref_exists=True,
        remote_ref_exists=False,
        local_commits_beyond_initial=False,
        dirty_paths=(),
    )
    assert safe.can_delete is True
    assert safe.permitted_commands == ("git branch -d releases/0.14.0",)
    unsafe = evaluate_branch_cleanup_safety(
        local_ref_exists=True,
        remote_ref_exists=True,
        local_commits_beyond_initial=False,
        dirty_paths=(),
    )
    assert unsafe.permitted_commands == ()
