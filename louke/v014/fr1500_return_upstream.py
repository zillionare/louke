"""FR-1500: Human 主导的合法返回上游.

Implements the deterministic contract slice of FR-1500:

* :func:`legal_return_targets` returns the legal upstream targets for a
  phase: M-SPEC -> ``('M-STORY',)``; M-ACC -> ``('M-SPEC', 'M-STORY')``;
  M-STORY/M-LOCK-1/ISSUES/REQUIREMENTS_READY -> ``()`` (AC-FR1500-01).

* :func:`apply_return_upstream` validates and applies a Human return. The
  target must be in :func:`legal_return_targets` for the current phase and
  the caller must be a Human principal. On success the current step moves
  to the target, the run revision bumps, Git history is preserved, and the
  target plus all downstream verdicts/format/approval evidence are marked
  ``stale``/``superseded`` (AC-FR1500-02). Illegal targets raise
  :class:`ReturnUpstreamForbidden` with ``UPSTREAM_RETURN_TARGET_INVALID``
  and Agent callers raise with ``HUMAN_AUTHORITY_REQUIRED``
  (AC-FR1500-01, IF-COMMON-01).

* :func:`record_agent_return_suggestion` records an Agent's suggestion to
  return upstream. The suggestion only produces a Human wait; the run's
  step and revision do not change until Human confirms (AC-FR1500-03).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


UPSTREAM_RETURN_TARGET_INVALID = "UPSTREAM_RETURN_TARGET_INVALID"


_LEGAL_TARGETS: dict[str, tuple[str, ...]] = {
    "M-STORY": (),
    "M-SPEC": ("M-STORY",),
    "M-ACC": ("M-SPEC", "M-STORY"),
    "M-LOCK-1": (),
    "ISSUES": (),
    "REQUIREMENTS_READY": (),
    "PARKED": (),
    "NO_GO": (),
}


def legal_return_targets(current_phase: str) -> tuple[str, ...]:
    """Return the legal upstream return targets for ``current_phase``.

    Args:
        current_phase: The current workflow phase.

    Returns:
        A tuple of legal target phase names. Empty for phases that do not
        allow return-upstream (M-STORY, M-LOCK-1, ISSUES, REQUIREMENTS_READY,
        terminal states).
    """
    return _LEGAL_TARGETS.get(current_phase, ())


_DOWNSTREAM_EVIDENCE: dict[str, tuple[str, ...]] = {
    "M-STORY": (
        "story_verdict",
        "spec_verdict",
        "spec_format",
        "acceptance_verdict",
        "acceptance_format",
        "m_lock_1_approval",
    ),
    "M-SPEC": (
        "spec_verdict",
        "spec_format",
        "acceptance_verdict",
        "acceptance_format",
        "m_lock_1_approval",
    ),
    "M-ACC": (
        "acceptance_verdict",
        "acceptance_format",
        "m_lock_1_approval",
    ),
}


@dataclass(frozen=True)
class ReturnUpstreamDecision:
    """Result of a successful :func:`apply_return_upstream`.

    Attributes:
        new_phase: The target phase the run moved to.
        new_revision: The bumped run revision (``expected_revision + 1``).
        stale_evidence: Frozen set of evidence categories marked
            ``stale``/``superseded``.
        git_history_deleted: Always ``False``; Git history is preserved.
    """

    new_phase: str
    new_revision: int
    stale_evidence: frozenset[str]
    git_history_deleted: bool = False


class ReturnUpstreamForbidden(Exception):
    """Raised when a return-upstream request is rejected.

    Attributes:
        code: ``UPSTREAM_RETURN_TARGET_INVALID`` for illegal targets;
            ``HUMAN_AUTHORITY_REQUIRED`` for Agent/anonymous callers;
            ``WORKFLOW_STATE_CONFLICT`` for stale revisions.
        current_phase: The phase the run is currently in.
        current_revision: The current run revision.
        legal_targets: Legal targets for ``current_phase``.
    """

    def __init__(
        self,
        *,
        code: str,
        current_phase: str,
        current_revision: int,
        legal_targets: tuple[str, ...],
        message: str,
    ) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.current_phase = current_phase
        self.current_revision = current_revision
        self.legal_targets = legal_targets


def apply_return_upstream(
    *,
    current_phase: str,
    target: str,
    expected_revision: int,
    actor_kind: str,
) -> ReturnUpstreamDecision:
    """Validate and apply a Human return-upstream request.

    Args:
        current_phase: The current workflow phase.
        target: The desired target phase.
        expected_revision: The revision the caller last observed.
        actor_kind: ``human`` or ``agent``; only Human principals may return
            upstream.

    Returns:
        A :class:`ReturnUpstreamDecision` with ``new_phase == target``,
        ``new_revision == expected_revision + 1``, the downstream evidence
        marked stale, and ``git_history_deleted is False``.

    Raises:
        ReturnUpstreamForbidden: If the target is not legal for
            ``current_phase`` (``UPSTREAM_RETURN_TARGET_INVALID``), the
            caller is not a Human principal (``HUMAN_AUTHORITY_REQUIRED``)
            or the revision is stale (``WORKFLOW_STATE_CONFLICT``).

    Side effects:
        None. The function is pure; the Driver/Store adapter persists the
        returned decision.
    """
    legal = legal_return_targets(current_phase)
    if actor_kind != "human":
        raise ReturnUpstreamForbidden(
            code="HUMAN_AUTHORITY_REQUIRED",
            current_phase=current_phase,
            current_revision=expected_revision,
            legal_targets=legal,
            message=(
                "return-upstream requires a Human principal; Agent/anonymous "
                "actors cannot move the workflow pointer"
            ),
        )
    if target not in legal:
        raise ReturnUpstreamForbidden(
            code=UPSTREAM_RETURN_TARGET_INVALID,
            current_phase=current_phase,
            current_revision=expected_revision,
            legal_targets=legal,
            message=(
                f"target {target!r} is not a legal return target from "
                f"{current_phase!r}; legal targets: {list(legal)}"
            ),
        )
    downstream = _DOWNSTREAM_EVIDENCE.get(target, ())
    return ReturnUpstreamDecision(
        new_phase=target,
        new_revision=expected_revision + 1,
        stale_evidence=frozenset(downstream),
        git_history_deleted=False,
    )


@dataclass(frozen=True)
class AgentReturnSuggestion:
    """An Agent's suggestion to return upstream (AC-FR1500-03).

    Attributes:
        current_phase: The phase the run is currently in (unchanged).
        current_revision: ``None``; the revision is not changed by an Agent
            suggestion.
        suggested_target: The target the Agent suggests.
        reasoning: Non-empty Agent reasoning.
        agent_identity: Non-secret Agent identity.
        run_status: Always ``waiting_human``.
        requires_human_confirmation: Always ``True``.
    """

    current_phase: str
    current_revision: Optional[int]
    suggested_target: str
    reasoning: str
    agent_identity: str
    run_status: str = "waiting_human"
    requires_human_confirmation: bool = True


def record_agent_return_suggestion(
    *,
    current_phase: str,
    suggested_target: str,
    reasoning: str,
    agent_identity: str,
) -> AgentReturnSuggestion:
    """Record an Agent's suggestion to return upstream.

    The suggestion only produces a Human wait; the run's step and revision
    do not change until Human confirms (AC-FR1500-03).

    Args:
        current_phase: The current workflow phase.
        suggested_target: The target the Agent suggests.
        reasoning: Non-empty Agent reasoning.
        agent_identity: Non-secret Agent identity.

    Returns:
        An :class:`AgentReturnSuggestion` with ``run_status ==
        'waiting_human'`` and ``current_revision is None``.
    """
    if not reasoning.strip():
        raise ValueError("reasoning must be non-empty")
    return AgentReturnSuggestion(
        current_phase=current_phase,
        current_revision=None,
        suggested_target=suggested_target,
        reasoning=reasoning,
        agent_identity=agent_identity,
    )
