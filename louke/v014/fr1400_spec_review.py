"""FR-1400: M-SPEC Human/Lex 语义 Review 与格式验收.

Implements the deterministic contract slice of FR-1400:

* :func:`start_first_spec_review_round` opens the first Spec review round
  bound to commit R and digest D. The Lex session id must differ from the
  Sage session id (AC-FR1400-01).

* :func:`lex_can_write_without_lease` enforces that Lex cannot change the
  document or discussions without a write lease; with a lease, Lex's
  threads are queryable (AC-FR1400-01).

* :func:`build_lex_review_input` builds the Lex input for the case where
  Human modifies R first (R2). The input binds to R2 and includes the
  Human diff (AC-FR1400-02).

* :func:`verdict_is_stale` returns ``True`` when a verdict's digest does
  not match the current round's digest (AC-FR1400-02).

* :func:`decide_m_spec_semantic_gate` decides whether the semantic gate
  passes. Human ``no_comment`` + Lex ``PASS`` + zero open threads + digest
  match is required to enter format check; any other combination requires
  rework with round increment (AC-FR1400-03).

* :func:`decide_m_spec_format_gate` decides whether the format gate passes.
  A failure shows the specific file/line/rule and keeps the current step at
  M-SPEC with M-ACC task count 0; a pass enters M-ACC (AC-FR1400-04).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


FORMAT_CHECK_REQUIRED = "FORMAT_CHECK_REQUIRED"


@dataclass(frozen=True)
class SpecReviewRound:
    """A Spec review round.

    Attributes:
        round_number: 1 for the first round, incremented on each rework.
        spec_commit_sha: Commit SHA of the Spec revision under review.
        spec_digest: ``sha256:<hex>`` digest of the Spec revision.
        sage_session_id: Sage OpenCode session id (continues across
            rounds).
        lex_session_id: Lex reviewer OpenCode session id; must differ from
            ``sage_session_id``.
    """

    round_number: int
    spec_commit_sha: str
    spec_digest: str
    sage_session_id: str
    lex_session_id: str


def start_first_spec_review_round(
    *,
    spec_commit_sha: str,
    spec_digest: str,
    sage_session_id: str,
    lex_session_id: str,
) -> SpecReviewRound:
    """Open the first Spec review round.

    Args:
        spec_commit_sha: Commit SHA of the Spec revision under review.
        spec_digest: ``sha256:<hex>`` digest of the Spec revision.
        sage_session_id: Sage OpenCode session id.
        lex_session_id: Lex reviewer OpenCode session id; must differ from
            ``sage_session_id``.

    Returns:
        A :class:`SpecReviewRound` with ``round_number == 1``.

    Raises:
        ValueError: If ``lex_session_id == sage_session_id`` (AC-FR1400-01
            requires independent sessions).
    """
    if lex_session_id == sage_session_id:
        raise ValueError(
            "Lex reviewer session must differ from Sage author session (AC-FR1400-01)"
        )
    return SpecReviewRound(
        round_number=1,
        spec_commit_sha=spec_commit_sha,
        spec_digest=spec_digest,
        sage_session_id=sage_session_id,
        lex_session_id=lex_session_id,
    )


@dataclass(frozen=True)
class LexWriteDecision:
    """Decision returned by :func:`lex_can_write_without_lease`.

    Attributes:
        can_write: ``True`` when Lex has a lease and may write; ``False``
            otherwise.
        code: ``WRITE_SCOPE_DENIED`` when ``can_write is False``; ``None``
            otherwise.
        threads_queryable: ``True`` when Lex's threads are queryable from
            the review page and the persistent discussion outlet; only when
            ``can_write is True``.
    """

    can_write: bool
    code: Optional[str] = None
    threads_queryable: bool = False


def lex_can_write_without_lease(*, has_lease: bool) -> LexWriteDecision:
    """Decide whether Lex may write without a lease.

    Args:
        has_lease: Whether Lex currently holds a write lease.

    Returns:
        A :class:`LexWriteDecision}. Without a lease Lex cannot write
        (``WRITE_SCOPE_DENIED``); with a lease Lex's threads are queryable
        (AC-FR1400-01).
    """
    if has_lease:
        return LexWriteDecision(
            can_write=True,
            code=None,
            threads_queryable=True,
        )
    return LexWriteDecision(
        can_write=False,
        code="WRITE_SCOPE_DENIED",
        threads_queryable=False,
    )


@dataclass(frozen=True)
class LexReviewInput:
    """Lex reviewer input for a round where Human modified first.

    Attributes:
        bound_digest: ``sha256:<hex>`` digest of the Human-modified Spec
            revision (R2).
        human_diff: Diff bytes between the previous Spec revision and the
            Human-modified revision.
        human_commit_sha: Commit SHA of the Human-modified Spec revision.
        lex_session_id: Lex reviewer OpenCode session id.
    """

    bound_digest: str
    human_diff: bytes
    human_commit_sha: str
    lex_session_id: str


def build_lex_review_input(
    *,
    round_: SpecReviewRound,
    human_commit_sha: str,
    human_digest: str,
    human_diff: bytes,
) -> LexReviewInput:
    """Build the Lex reviewer input when Human modifies first.

    Args:
        round_: The current :class:`SpecReviewRound`.
        human_commit_sha: Commit SHA of the Human-modified Spec revision
            (R2).
        human_digest: ``sha256:<hex>`` digest of the Human-modified Spec
            revision.
        human_diff: Diff bytes between the previous Spec revision and the
            Human-modified revision.

    Returns:
        A :class:`LexReviewInput` bound to ``human_digest`` and including
        the Human diff (AC-FR1400-02).
    """
    return LexReviewInput(
        bound_digest=human_digest,
        human_diff=human_diff,
        human_commit_sha=human_commit_sha,
        lex_session_id=round_.lex_session_id,
    )


def verdict_is_stale(verdict: object, round_: SpecReviewRound) -> bool:
    """Return ``True`` when ``verdict.digest`` does not match the current
    round's digest.

    Args:
        verdict: Any object with a ``digest`` attribute.
        round_: The current :class:`SpecReviewRound`.

    Returns:
        ``True`` when the verdict's digest differs from
        ``round_.spec_digest``; ``False`` otherwise (AC-FR1400-02).
    """
    return getattr(verdict, "digest", None) != round_.spec_digest


@dataclass(frozen=True)
class MSpecSemanticGateDecision:
    """Decision returned by :func:`decide_m_spec_semantic_gate`.

    Attributes:
        can_enter_format_check: ``True`` only when Human ``no_comment`` +
            Lex ``PASS`` + zero open threads + digest match.
        requires_rework: ``True`` when the round must rework; ``False``
            otherwise.
        round_increment: 1 when ``requires_rework``; 0 otherwise.
        next_action: ``format_check`` when ``can_enter_format_check``;
            ``rework`` otherwise.
    """

    can_enter_format_check: bool
    requires_rework: bool
    round_increment: int
    next_action: str


def decide_m_spec_semantic_gate(
    *,
    round_: SpecReviewRound,
    human_signal: str,
    lex_verdict: str,
    open_threads: int,
    digest_matches: bool,
) -> MSpecSemanticGateDecision:
    """Decide whether the M-SPEC semantic gate passes.

    Args:
        round_: The current :class:`SpecReviewRound`.
        human_signal: ``comment`` or ``no_comment``.
        lex_verdict: ``PASS`` or ``REJECT``.
        open_threads: Number of OPEN/REOPEN discussions on the current
            Spec revision.
        digest_matches: Whether the Spec digest still matches the round's
            binding.

    Returns:
        An :class:`MSpecSemanticGateDecision}. ``can_enter_format_check is
        True`` only when ``human_signal == 'no_comment'`` AND
        ``lex_verdict == 'PASS'`` AND ``open_threads == 0`` AND
        ``digest_matches is True``. Any other combination requires rework
        with ``round_increment == 1`` (AC-FR1400-03).
    """
    if (
        human_signal == "no_comment"
        and lex_verdict == "PASS"
        and open_threads == 0
        and digest_matches
    ):
        return MSpecSemanticGateDecision(
            can_enter_format_check=True,
            requires_rework=False,
            round_increment=0,
            next_action="format_check",
        )
    return MSpecSemanticGateDecision(
        can_enter_format_check=False,
        requires_rework=True,
        round_increment=1,
        next_action="rework",
    )


@dataclass(frozen=True)
class MSpecFormatCheckResult:
    """Result of a canonical format check on the Spec.

    Attributes:
        passed: ``True`` when the format check passed; ``False`` otherwise.
        errors: Tuple of error descriptors (``{file, line, rule, message}``)
            when ``passed is False``; empty otherwise.
    """

    passed: bool
    errors: tuple[dict[str, object], ...]


@dataclass(frozen=True)
class MSpecFormatGateDecision:
    """Decision returned by :func:`decide_m_spec_format_gate`.

    Attributes:
        can_enter_m_acc: ``True`` only when the format check passed.
        current_step: ``M-ACC`` when ``can_enter_m_acc``; ``M-SPEC``
            otherwise.
        m_acc_task_count: ``1`` when ``can_enter_m_acc``; ``0`` otherwise.
        format_errors: Tuple of format error descriptors when
            ``not can_enter_m_acc``; empty otherwise.
    """

    can_enter_m_acc: bool
    current_step: str
    m_acc_task_count: int
    format_errors: tuple[dict[str, object], ...]


def decide_m_spec_format_gate(
    result: MSpecFormatCheckResult,
) -> MSpecFormatGateDecision:
    """Decide whether the M-SPEC format gate passes.

    Args:
        result: The :class:`MSpecFormatCheckResult` of the canonical format
            check.

    Returns:
        An :class:`MSpecFormatGateDecision}. A failure shows the specific
        file/line/rule and keeps the current step at M-SPEC with M-ACC task
        count 0; a pass enters M-ACC with at least one M-ACC task
        (AC-FR1400-04).
    """
    if result.passed:
        return MSpecFormatGateDecision(
            can_enter_m_acc=True,
            current_step="M-ACC",
            m_acc_task_count=1,
            format_errors=(),
        )
    return MSpecFormatGateDecision(
        can_enter_m_acc=False,
        current_step="M-SPEC",
        m_acc_task_count=0,
        format_errors=result.errors,
    )
