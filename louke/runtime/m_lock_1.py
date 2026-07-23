"""FR-1700: M-LOCK-1 三文档批准与只读锁定.

Implements the deterministic contract slice of FR-1700:

* :func:`compute_m_lock_1_blockers` enumerates the unclosed reviews/formats/
  discussions that block approval. When the list is non-empty, approve is
  rejected and the GitHub Issue count does not change (AC-FR1700-01).

* :func:`build_joint_digest` deterministically combines the Story, Spec and
  Acceptance digests into a single ``sha256:<hex>`` joint digest that the
  challenge is bound to (AC-FR1700-02).

* :func:`issue_new_m_lock_1_challenge` issues a fresh one-time challenge id
  bound to the joint digest and the expected run revision (AC-FR1700-02).

* :func:`approve_m_lock_1` is the only authority for an M-LOCK-1 approval.
  It requires a Human principal, a non-consumed challenge whose id matches
  the gate's current challenge, an expected_revision that matches the gate
  and a joint_digest that matches the gate's joint digest. On success the
  approval decision records actor/time/challenge/revision/digests and the
  gate becomes ``APPROVED``. Failures leave the gate ``PENDING`` with one
  of: ``HUMAN_AUTHORITY_REQUIRED``, ``GATE_CHALLENGE_REPLAYED``,
  ``WORKFLOW_STATE_CONFLICT`` (stale revision) or ``AUTH_CHALLENGE_INVALID``
  (wrong joint digest) (AC-FR1700-02, AC-FR1700-03).

* :func:`is_write_allowed_after_lock` returns ``REQUIREMENTS_LOCKED`` for
  any write to a locked document; the file bytes do not change
  (AC-FR1700-03).
"""

from __future__ import annotations

import datetime
import hashlib
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Optional


HUMAN_AUTHORITY_REQUIRED = "HUMAN_AUTHORITY_REQUIRED"
GATE_CHALLENGE_REPLAYED = "GATE_CHALLENGE_REPLAYED"
REQUIREMENTS_LOCKED = "REQUIREMENTS_LOCKED"
AUTH_CHALLENGE_INVALID = "AUTH_CHALLENGE_INVALID"


class MLock1GateState(str, Enum):
    """Lifecycle state of an M-LOCK-1 gate.

    Members:
        PENDING: Gate is awaiting Human approval.
        APPROVED: Gate has been approved by an authenticated Human.
        STALE: Upstream digest change has made the gate stale.
    """

    PENDING = "pending"
    APPROVED = "approved"
    STALE = "stale"


def build_joint_digest(
    story_digest: str,
    spec_digest: str,
    acceptance_digest: str,
) -> str:
    """Return the deterministic joint digest of the three documents.

    Args:
        story_digest: ``sha256:<hex>`` Story digest.
        spec_digest: ``sha256:<hex>`` Spec digest.
        acceptance_digest: ``sha256:<hex>`` Acceptance digest.

    Returns:
        ``sha256:<hex>`` joint digest covering all three input digests in
        fixed order. Identical inputs always produce the same joint digest.
    """
    payload = f"{story_digest}|{spec_digest}|{acceptance_digest}"
    return f"sha256:{hashlib.sha256(payload.encode('utf-8')).hexdigest()}"


@dataclass(frozen=True)
class MLock1Challenge:
    """A fresh one-time M-LOCK-1 challenge.

    Attributes:
        challenge_id: Fresh opaque challenge identifier.
        gate_id: Gate the challenge belongs to.
        expected_run_revision: Run revision the challenge is bound to.
        joint_digest: ``sha256:<hex>`` joint digest the challenge is bound
            to.
        issued_at: UTC RFC 3339 timestamp.
    """

    challenge_id: str
    gate_id: str
    expected_run_revision: int
    joint_digest: str
    issued_at: str


def _now_iso_utc() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def issue_new_m_lock_1_challenge(
    *,
    gate_id: str,
    expected_run_revision: int,
    story_digest: str,
    spec_digest: str,
    acceptance_digest: str,
) -> MLock1Challenge:
    """Issue a fresh one-time M-LOCK-1 challenge.

    Args:
        gate_id: Gate the challenge belongs to.
        expected_run_revision: Run revision the challenge is bound to.
        story_digest: ``sha256:<hex>`` Story digest.
        spec_digest: ``sha256:<hex>`` Spec digest.
        acceptance_digest: ``sha256:<hex>`` Acceptance digest.

    Returns:
        An :class:`MLock1Challenge` with a fresh ``challenge_id`` and the
        computed ``joint_digest``.
    """
    return MLock1Challenge(
        challenge_id=f"ch_{uuid.uuid4().hex[:16]}",
        gate_id=gate_id,
        expected_run_revision=expected_run_revision,
        joint_digest=build_joint_digest(story_digest, spec_digest, acceptance_digest),
        issued_at=_now_iso_utc(),
    )


@dataclass(frozen=True)
class MLock1Gate:
    """M-LOCK-1 gate state.

    Attributes:
        gate_id: Opaque gate identifier.
        status: :class:`MLock1GateState`.
        expected_run_revision: Run revision the gate is bound to.
        story_digest: ``sha256:<hex>`` Story digest the gate is bound to.
        spec_digest: ``sha256:<hex>`` Spec digest the gate is bound to.
        acceptance_digest: ``sha256:<hex>`` Acceptance digest the gate is
            bound to.
        challenge_id: Current challenge id; ``None`` when no challenge has
            been issued.
        consumed_challenge_ids: Frozen set of challenge ids that have
            already been consumed.
    """

    gate_id: str
    status: MLock1GateState
    expected_run_revision: int
    story_digest: str
    spec_digest: str
    acceptance_digest: str
    challenge_id: Optional[str] = None
    consumed_challenge_ids: frozenset[str] = frozenset()

    @property
    def joint_digest(self) -> str:
        """Return the joint digest bound to this gate."""
        return build_joint_digest(
            self.story_digest, self.spec_digest, self.acceptance_digest
        )


def compute_m_lock_1_blockers(
    *,
    story_review_open: bool,
    spec_format_pending: bool,
    acceptance_open_threads: int,
) -> tuple[str, ...]:
    """Enumerate the blockers that prevent M-LOCK-1 approval.

    Args:
        story_review_open: Whether the Story review is still open.
        spec_format_pending: Whether the Spec format check is still pending.
        acceptance_open_threads: Number of OPEN/REOPEN Acceptance threads.

    Returns:
        A tuple of blocker codes. Empty when no blockers remain
        (AC-FR1700-01).
    """
    blockers: list[str] = []
    if story_review_open:
        blockers.append("story_review_open")
    if spec_format_pending:
        blockers.append("spec_format_pending")
    if acceptance_open_threads > 0:
        blockers.append(f"acceptance_open_threads:{acceptance_open_threads}")
    return tuple(blockers)


@dataclass(frozen=True)
class MLock1ApprovalDecision:
    """A recorded M-LOCK-1 approval decision.

    Attributes:
        actor: Non-secret Human principal identity.
        approved_at: UTC RFC 3339 timestamp.
        challenge_id: The consumed challenge id.
        run_revision: The run revision at approval time.
        story_digest: Story digest at approval time.
        spec_digest: Spec digest at approval time.
        acceptance_digest: Acceptance digest at approval time.
        joint_digest: Joint digest at approval time.
    """

    actor: str
    approved_at: str
    challenge_id: str
    run_revision: int
    story_digest: str
    spec_digest: str
    acceptance_digest: str
    joint_digest: str


class MLock1ApprovalRejected(Exception):
    """Raised when an M-LOCK-1 approval is rejected.

    Attributes:
        code: ``HUMAN_AUTHORITY_REQUIRED``, ``GATE_CHALLENGE_REPLAYED``,
            ``AUTH_CHALLENGE_INVALID``, ``WORKFLOW_STATE_CONFLICT`` or
            :data:`REQUIREMENTS_LOCKED`.
    """

    def __init__(self, *, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code


@dataclass(frozen=True)
class MLock1ApprovalOutcome:
    """Outcome of :func:`approve_m_lock_1`.

    Attributes:
        decision: The recorded :class:`MLock1ApprovalDecision`.
        new_gate: The updated :class:`MLock1Gate` with status ``APPROVED``
            and the consumed challenge id added to
            ``consumed_challenge_ids``.
    """

    decision: "MLock1ApprovalDecision"
    new_gate: "MLock1Gate"


def approve_m_lock_1(
    *,
    gate: MLock1Gate,
    challenge_id: str,
    expected_run_revision: int,
    joint_digest: str,
    actor_kind: str,
    actor: str,
) -> MLock1ApprovalOutcome:
    """Validate and apply a Human M-LOCK-1 approval.

    Args:
        gate: The current :class:`MLock1Gate`.
        challenge_id: The challenge id the caller is consuming.
        expected_run_revision: The run revision the caller last observed.
        joint_digest: The joint digest the caller is bound to.
        actor_kind: ``human`` or ``agent``; only Human principals may
            approve.
        actor: Non-secret Human principal identity.

    Returns:
        An :class:`MLock1ApprovalOutcome` containing the recorded decision
        and the updated gate (status ``APPROVED``, challenge id consumed).
        The three documents become read-only.

    Raises:
        MLock1ApprovalRejected: When the caller is not a Human principal
            (``HUMAN_AUTHORITY_REQUIRED``), the challenge has already been
            consumed (``GATE_CHALLENGE_REPLAYED``), the gate is already
            approved (``REQUIREMENTS_LOCKED``), the challenge id does not
            match the gate's current challenge (``AUTH_CHALLENGE_INVALID``),
            the expected_revision is stale
            (``WORKFLOW_STATE_CONFLICT``) or the joint digest does not match
            (``AUTH_CHALLENGE_INVALID``).

    Side effects:
        None. The function is pure; the returned ``new_gate`` is the
        caller's responsibility to persist.
    """
    if gate.status == MLock1GateState.APPROVED:
        raise MLock1ApprovalRejected(
            code=REQUIREMENTS_LOCKED,
            message="gate already approved; three documents are read-only",
        )
    if actor_kind != "human":
        raise MLock1ApprovalRejected(
            code=HUMAN_AUTHORITY_REQUIRED,
            message=(
                "M-LOCK-1 approval requires a Human principal; Agent/anonymous "
                "actors cannot approve"
            ),
        )
    if challenge_id in gate.consumed_challenge_ids:
        raise MLock1ApprovalRejected(
            code=GATE_CHALLENGE_REPLAYED,
            message=f"challenge {challenge_id!r} has already been consumed",
        )
    if gate.challenge_id is None or challenge_id != gate.challenge_id:
        # A challenge id that is not the gate's current challenge is either
        # a replay of a previously-consumed challenge (handled above) or an
        # invalid challenge from another gate/instance. Either way the
        # contract treats a non-current challenge on a pending gate as a
        # replay attempt (AC-FR1700-02).
        raise MLock1ApprovalRejected(
            code=GATE_CHALLENGE_REPLAYED,
            message=(
                f"challenge {challenge_id!r} does not match the gate's "
                f"current challenge {gate.challenge_id!r}; treated as a "
                "replay of a stale challenge"
            ),
        )
    if expected_run_revision != gate.expected_run_revision:
        raise MLock1ApprovalRejected(
            code="WORKFLOW_STATE_CONFLICT",
            message=(
                f"expected revision {expected_run_revision} does not match "
                f"gate revision {gate.expected_run_revision}"
            ),
        )
    if joint_digest != gate.joint_digest:
        raise MLock1ApprovalRejected(
            code=AUTH_CHALLENGE_INVALID,
            message="joint digest does not match the gate's joint digest",
        )
    decision = MLock1ApprovalDecision(
        actor=actor,
        approved_at=_now_iso_utc(),
        challenge_id=challenge_id,
        run_revision=expected_run_revision,
        story_digest=gate.story_digest,
        spec_digest=gate.spec_digest,
        acceptance_digest=gate.acceptance_digest,
        joint_digest=gate.joint_digest,
    )
    new_gate = MLock1Gate(
        gate_id=gate.gate_id,
        status=MLock1GateState.APPROVED,
        expected_run_revision=gate.expected_run_revision,
        story_digest=gate.story_digest,
        spec_digest=gate.spec_digest,
        acceptance_digest=gate.acceptance_digest,
        challenge_id=gate.challenge_id,
        consumed_challenge_ids=gate.consumed_challenge_ids | {challenge_id},
    )
    return MLock1ApprovalOutcome(decision=decision, new_gate=new_gate)


@dataclass(frozen=True)
class WriteAfterLockDecision:
    """Decision returned by :func:`is_write_allowed_after_lock`.

    Attributes:
        allowed: ``True`` when the write is allowed; ``False`` otherwise.
        code: ``REQUIREMENTS_LOCKED`` when ``not allowed``; ``None``
            otherwise.
    """

    allowed: bool
    code: Optional[str]


def is_write_allowed_after_lock(
    *,
    is_locked: bool,
    document: str,
) -> WriteAfterLockDecision:
    """Decide whether a write to ``document`` is allowed after M-LOCK-1.

    Args:
        is_locked: Whether the document is locked (M-LOCK-1 approved).
        document: Document path being written.

    Returns:
        A :class:`WriteAfterLockDecision`. ``allowed is False`` with code
        :data:`REQUIREMENTS_LOCKED` when ``is_locked is True``; otherwise
        ``allowed is True``. The file bytes do not change on rejection
        (AC-FR1700-03).
    """
    if is_locked:
        return WriteAfterLockDecision(allowed=False, code=REQUIREMENTS_LOCKED)
    return WriteAfterLockDecision(allowed=True, code=None)
