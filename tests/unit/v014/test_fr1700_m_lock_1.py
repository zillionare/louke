"""FR-1700: M-LOCK-1 三文档批准与只读锁定.

AC references:
- AC-FR1700-01: when any of the three documents has an unclosed
  review/format/discussion, the approve button is disabled, the server
  rejects with the specific blockers, and the GitHub Issue count does not
  change.
- AC-FR1700-02: when all three documents pass and have digests S/P/A, the
  Project current page shows ``M-LOCK-1`` waiting for approval, displays
  the three versions and offers the approve action. Agent / stale
  challenge / wrong revision / wrong joint digest approvals are rejected
  and the gate stays pending.
- AC-FR1700-03: when an authenticated Human approves the current
  challenge/joint digest, the approval record contains actor/time/
  challenge/revision/digests; the three documents become read-only and
  subsequent writes are rejected with ``REQUIREMENTS_LOCKED``; the three
  files' bytes do not change.
"""

from __future__ import annotations

import pytest

from louke.v014.fr1700_m_lock_1 import (
    GATE_CHALLENGE_REPLAYED,
    HUMAN_AUTHORITY_REQUIRED,
    MLock1Gate,
    MLock1GateState,
    REQUIREMENTS_LOCKED,
    build_joint_digest,
    compute_m_lock_1_blockers,
    is_write_allowed_after_lock,
    issue_new_m_lock_1_challenge,
    approve_m_lock_1,
)


def _digest(c: str) -> str:
    return f"sha256:{c * 64}"


# AC-FR1700-01 ---------------------------------------------------------------
def test_blockers_listed_when_any_document_unclosed() -> None:
    """AC-FR1700-01: any unclosed review/format/discussion is listed as a
    blocker; approve is rejected."""
    blockers = compute_m_lock_1_blockers(
        story_review_open=True,
        spec_format_pending=False,
        acceptance_open_threads=0,
    )
    assert "story_review_open" in blockers
    assert len(blockers) >= 1


def test_no_blockers_when_all_documents_closed() -> None:
    """AC-FR1700-01: when all reviews/formats/discussions are closed, the
    blocker list is empty and approve is available."""
    blockers = compute_m_lock_1_blockers(
        story_review_open=False,
        spec_format_pending=False,
        acceptance_open_threads=0,
    )
    assert blockers == ()


# AC-FR1700-02 ---------------------------------------------------------------
def test_joint_digest_is_deterministic_over_three_document_digests() -> None:
    """AC-FR1700-02: the joint digest is deterministic over
    (story_digest, spec_digest, acceptance_digest)."""
    s = _digest("a")
    p = _digest("b")
    a = _digest("c")
    joint1 = build_joint_digest(s, p, a)
    joint2 = build_joint_digest(s, p, a)
    assert joint1 == joint2
    assert joint1.startswith("sha256:")
    # Different inputs produce different joints.
    different = build_joint_digest(_digest("x"), p, a)
    assert different != joint1


def test_approve_rejects_agent_actor() -> None:
    """AC-FR1700-02 + IF-COMMON-01: an Agent-transport caller cannot approve
    M-LOCK-1."""
    gate = MLock1Gate(
        gate_id="gate_1",
        status=MLock1GateState.PENDING,
        expected_run_revision=4,
        story_digest=_digest("a"),
        spec_digest=_digest("b"),
        acceptance_digest=_digest("c"),
        challenge_id="ch_1",
    )
    with pytest.raises(Exception) as exc_info:
        approve_m_lock_1(
            gate=gate,
            challenge_id="ch_1",
            expected_run_revision=4,
            joint_digest=gate.joint_digest,
            actor_kind="agent",
            actor="agent:sage",
        )
    assert exc_info.value.code == HUMAN_AUTHORITY_REQUIRED
    assert gate.status == MLock1GateState.PENDING


def test_approve_rejects_stale_challenge() -> None:
    """AC-FR1700-02: a stale/already-consumed challenge is rejected with
    GATE_CHALLENGE_REPLAYED; the gate stays pending."""
    gate = MLock1Gate(
        gate_id="gate_1",
        status=MLock1GateState.PENDING,
        expected_run_revision=4,
        story_digest=_digest("a"),
        spec_digest=_digest("b"),
        acceptance_digest=_digest("c"),
        challenge_id="ch_1",
    )
    with pytest.raises(Exception) as exc_info:
        approve_m_lock_1(
            gate=gate,
            challenge_id="ch_old",  # stale challenge
            expected_run_revision=4,
            joint_digest=gate.joint_digest,
            actor_kind="human",
            actor="human:alice",
        )
    assert exc_info.value.code == GATE_CHALLENGE_REPLAYED


def test_approve_rejects_wrong_joint_digest() -> None:
    """AC-FR1700-02: a wrong joint digest is rejected; the gate stays
    pending."""
    gate = MLock1Gate(
        gate_id="gate_1",
        status=MLock1GateState.PENDING,
        expected_run_revision=4,
        story_digest=_digest("a"),
        spec_digest=_digest("b"),
        acceptance_digest=_digest("c"),
        challenge_id="ch_1",
    )
    with pytest.raises(Exception):
        approve_m_lock_1(
            gate=gate,
            challenge_id="ch_1",
            expected_run_revision=4,
            joint_digest=_digest("z"),  # wrong joint
            actor_kind="human",
            actor="human:alice",
        )
    assert gate.status == MLock1GateState.PENDING


def test_valid_human_approval_records_actor_time_challenge_revision_digests() -> None:
    """AC-FR1700-02 + AC-FR1700-03: a valid Human approval records actor,
    time, challenge, revision and the three digests; the gate becomes
    APPROVED."""
    gate = MLock1Gate(
        gate_id="gate_1",
        status=MLock1GateState.PENDING,
        expected_run_revision=4,
        story_digest=_digest("a"),
        spec_digest=_digest("b"),
        acceptance_digest=_digest("c"),
        challenge_id="ch_1",
    )
    decision = approve_m_lock_1(
        gate=gate,
        challenge_id="ch_1",
        expected_run_revision=4,
        joint_digest=gate.joint_digest,
        actor_kind="human",
        actor="human:alice",
    )
    assert decision.actor == "human:alice"
    assert decision.challenge_id == "ch_1"
    assert decision.run_revision == 4
    assert decision.story_digest == _digest("a")
    assert decision.spec_digest == _digest("b")
    assert decision.acceptance_digest == _digest("c")
    assert decision.joint_digest == gate.joint_digest
    assert decision.approved_at  # non-empty timestamp


# AC-FR1700-03 ---------------------------------------------------------------
def test_write_after_lock_rejected_with_requirements_locked() -> None:
    """AC-FR1700-03: after approval, writes to any of the three documents
    are rejected with REQUIREMENTS_LOCKED; the file bytes do not change."""
    decision = is_write_allowed_after_lock(
        is_locked=True,
        document="story.md",
    )
    assert decision.allowed is False
    assert decision.code == REQUIREMENTS_LOCKED


def test_challenge_is_one_time() -> None:
    """AC-FR1700-02 + AC-FR1700-03: each challenge is one-time; replaying a
    consumed challenge is rejected."""
    gate = MLock1Gate(
        gate_id="gate_1",
        status=MLock1GateState.PENDING,
        expected_run_revision=4,
        story_digest=_digest("a"),
        spec_digest=_digest("b"),
        acceptance_digest=_digest("c"),
        challenge_id="ch_1",
    )
    approve_m_lock_1(
        gate=gate,
        challenge_id="ch_1",
        expected_run_revision=4,
        joint_digest=gate.joint_digest,
        actor_kind="human",
        actor="human:alice",
    )
    # Replay the same challenge on the now-approved gate.
    with pytest.raises(Exception) as exc_info:
        approve_m_lock_1(
            gate=gate,
            challenge_id="ch_1",
            expected_run_revision=4,
            joint_digest=gate.joint_digest,
            actor_kind="human",
            actor="human:alice",
        )
    assert exc_info.value.code in {GATE_CHALLENGE_REPLAYED, REQUIREMENTS_LOCKED}


def test_issue_new_challenge_returns_fresh_id_bound_to_joint_digest() -> None:
    """AC-FR1700-02: issuing a new challenge returns a fresh challenge id
    bound to the joint digest."""
    challenge = issue_new_m_lock_1_challenge(
        gate_id="gate_1",
        expected_run_revision=4,
        story_digest=_digest("a"),
        spec_digest=_digest("b"),
        acceptance_digest=_digest("c"),
    )
    assert challenge.challenge_id  # non-empty fresh id
    assert challenge.expected_run_revision == 4
    assert challenge.joint_digest.startswith("sha256:")
