"""FR-1000: 文档 Write Ownership、CAS 与脏编辑保护.

AC references:
- AC-FR1000-01: Human and Agent holding the same stale version token or
  wrong lease save the same document; at most one succeeds, the loser sees
  the current revision/token and conflict reason, and the on-disk bytes
  equal the winner's content with no silent overwrite.
- AC-FR1000-02: when the Human browser has unsaved edits and an Agent
  requests a write lease, the lease is not granted and the page prompts
  save/discard; the Agent's write request cannot change the file until the
  Human saves or explicitly discards.
- AC-FR1000-03: when a non-holder modifies a controlled document and the
  patch is exactly isolatable, Runtime only removes the violating patch,
  preserves the other workspace/index bytes and notifies the Agent to
  re-read; when the baseline cannot be obtained or the source is not
  isolatable, the run is ``needs_attention`` and no repository-wide revert
  is performed.
"""

from __future__ import annotations

import threading

import pytest

from louke.v014.fr1000_write_ownership import (
    DOCUMENT_WRITE_CONFLICT,
    DirtyBlocksHandoff,
    HUMAN_DIRTY_BLOCKS_HANDOFF,
    LeaseHolder,
    LeaseStatus,
    NonHolderPatchDecision,
    WriteLease,
    WriteLeaseRegistry,
    acquire_write_lease,
    apply_concurrent_save,
    decide_non_holder_patch_handling,
    register_dirty,
    release_write_lease,
)


# AC-FR1000-01 ---------------------------------------------------------------
def test_concurrent_save_with_same_token_at_most_one_winner() -> None:
    """AC-FR1000-01: two concurrent saves with the same expected_revision and
    version token produce exactly one winner; the loser receives
    DOCUMENT_WRITE_CONFLICT with the current revision/token."""
    registry = WriteLeaseRegistry()
    lease = WriteLease(
        lease_id="lease_1",
        holder=LeaseHolder(kind="human", id="human:alice", role="author"),
        document="story.md",
        base_revision=2,
        version_token="tok_1",
        status=LeaseStatus.ACTIVE,
    )
    registry.grant(lease)
    barrier = threading.Barrier(2)
    results: list[object] = []

    def _save(body: str) -> None:
        barrier.wait(timeout=2.0)
        results.append(
            apply_concurrent_save(
                registry=registry,
                document="story.md",
                body_md=body,
                expected_revision=2,
                version_token="tok_1",
                lease_id="lease_1",
                actor="human:alice",
            )
        )

    threads = [
        threading.Thread(target=_save, args=("winner body",)),
        threading.Thread(target=_save, args=("loser body",)),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5.0)

    assert len(results) == 2
    winners = [r for r in results if getattr(r, "ok", False)]  # type: ignore[attr-defined]
    losers = [r for r in results if not getattr(r, "ok", False)]  # type: ignore[attr-defined]
    assert len(winners) == 1
    assert len(losers) == 1
    assert losers[0].conflict_code == DOCUMENT_WRITE_CONFLICT  # type: ignore[attr-defined]
    # On-disk bytes equal the winner's content.
    assert winners[0].committed_bytes == b"winner body"  # type: ignore[attr-defined]
    # Loser sees the current revision/token.
    assert losers[0].current_revision == 3  # type: ignore[attr-defined]
    assert losers[0].current_version_token  # type: ignore[attr-defined]


def test_save_with_wrong_lease_is_rejected() -> None:
    """AC-FR1000-01: a save with a wrong lease id is rejected; bytes are
    unchanged."""
    registry = WriteLeaseRegistry()
    lease = WriteLease(
        lease_id="lease_1",
        holder=LeaseHolder(kind="human", id="human:alice", role="author"),
        document="story.md",
        base_revision=1,
        version_token="tok_1",
        status=LeaseStatus.ACTIVE,
    )
    registry.grant(lease)
    result = apply_concurrent_save(
        registry=registry,
        document="story.md",
        body_md="some body",
        expected_revision=1,
        version_token="tok_1",
        lease_id="lease_other",  # wrong lease
        actor="human:alice",
    )
    assert result.ok is False
    assert result.conflict_code == DOCUMENT_WRITE_CONFLICT


# AC-FR1000-02 ---------------------------------------------------------------
def test_human_dirty_blocks_agent_lease_acquisition() -> None:
    """AC-FR1000-02: when the Human browser has unsaved edits registered on
    the document, an Agent acquire is blocked and returns
    HUMAN_DIRTY_BLOCKS_HANDOFF; the page must prompt save/discard."""
    registry = WriteLeaseRegistry()
    register_dirty(
        registry=registry,
        document="story.md",
        client_id="client_alice",
        expected_artifact_revision=2,
        dirty=True,
    )
    with pytest.raises(DirtyBlocksHandoff) as exc_info:
        acquire_write_lease(
            registry=registry,
            holder=LeaseHolder(kind="agent", id="agent:scribe", role="author"),
            document="story.md",
            base_revision=2,
            version_token="tok_1",
            task_id="task_1",
        )
    assert exc_info.value.code == HUMAN_DIRTY_BLOCKS_HANDOFF
    assert "save" in exc_info.value.remediation.lower()
    # No lease granted.
    assert registry.active_lease_for("story.md") is None


def test_human_dirty_cleared_allows_agent_lease() -> None:
    """AC-FR1000-02: once the Human clears the dirty flag (save or discard),
    an Agent lease can be acquired."""
    registry = WriteLeaseRegistry()
    register_dirty(
        registry=registry,
        document="story.md",
        client_id="client_alice",
        expected_artifact_revision=2,
        dirty=True,
    )
    register_dirty(
        registry=registry,
        document="story.md",
        client_id="client_alice",
        expected_artifact_revision=2,
        dirty=False,
    )
    lease = acquire_write_lease(
        registry=registry,
        holder=LeaseHolder(kind="agent", id="agent:scribe", role="author"),
        document="story.md",
        base_revision=2,
        version_token="tok_1",
        task_id="task_1",
    )
    assert lease.status == LeaseStatus.ACTIVE


def test_second_holder_for_same_document_is_rejected() -> None:
    """AC-FR1000-01: a second active lease for the same document is rejected
    with the current holder exposed."""
    registry = WriteLeaseRegistry()
    first = acquire_write_lease(
        registry=registry,
        holder=LeaseHolder(kind="human", id="human:alice", role="author"),
        document="story.md",
        base_revision=2,
        version_token="tok_1",
        task_id=None,
    )
    assert first.status == LeaseStatus.ACTIVE
    second = acquire_write_lease(
        registry=registry,
        holder=LeaseHolder(kind="agent", id="agent:scribe", role="reviewer"),
        document="story.md",
        base_revision=2,
        version_token="tok_1",
        task_id="task_1",
    )
    assert second.status == LeaseStatus.BLOCKED
    assert second.current_holder is not None
    assert second.current_holder.id == "human:alice"


# AC-FR1000-03 ---------------------------------------------------------------
def test_isolatable_non_holder_patch_is_removed_preserving_other_bytes() -> None:
    """AC-FR1000-03: when the baseline bytes are available and the violating
    patch is exactly isolatable, Runtime removes only the violating patch and
    preserves the other workspace/index bytes; the Agent is notified to
    re-read."""
    decision = decide_non_holder_patch_handling(
        baseline_bytes_available=True,
        patch_isolatable=True,
        source_identifiable=True,
    )
    assert isinstance(decision, NonHolderPatchDecision)
    assert decision.action == "remove_violating_patch"
    assert decision.run_status == "ok"
    assert decision.notify_agent_to_reread is True
    assert decision.repository_wide_revert is False


def test_non_isolatable_patch_or_unknown_baseline_is_needs_attention() -> None:
    """AC-FR1000-03: when the baseline bytes cannot be obtained or the
    violating patch is not isolatable, the run is ``needs_attention`` and no
    repository-wide revert is performed."""
    decision = decide_non_holder_patch_handling(
        baseline_bytes_available=False,
        patch_isolatable=True,
        source_identifiable=True,
    )
    assert decision.action == "needs_attention"
    assert decision.run_status == "needs_attention"
    assert decision.repository_wide_revert is False

    decision = decide_non_holder_patch_handling(
        baseline_bytes_available=True,
        patch_isolatable=False,
        source_identifiable=True,
    )
    assert decision.action == "needs_attention"
    assert decision.repository_wide_revert is False


def test_release_lease_is_idempotent() -> None:
    """AC-FR1000-02: releasing a lease is idempotent; releasing twice is a
    no-op."""
    registry = WriteLeaseRegistry()
    lease = acquire_write_lease(
        registry=registry,
        holder=LeaseHolder(kind="human", id="human:alice", role="author"),
        document="story.md",
        base_revision=2,
        version_token="tok_1",
        task_id=None,
    )
    release_write_lease(registry=registry, lease_id=lease.lease_id)
    # Second release is a no-op.
    release_write_lease(registry=registry, lease_id=lease.lease_id)
    assert registry.active_lease_for("story.md") is None
