"""FR-0600: Runtime 权威工作流与 Web 当前状态.

Implements the deterministic contract slice of FR-0600:

* :class:`WorkflowAuthority` is the single stateless authority for legal
  phase transitions. Each transition is validated against
  :data:`LEGAL_TRANSITIONS`; disallowed targets raise
  :class:`WorkflowStateConflict` with code ``WORKFLOW_STATE_CONFLICT`` and
  expose the current phase, revision and a continue URL (AC-FR0600-01,
  AC-FR0600-03). Transitions that require a Human principal (every legal
  transition in this spec) raise :class:`ActionForbidden` with code
  ``HUMAN_AUTHORITY_REQUIRED`` when the caller is not a Human
  (IF-COMMON-01 trust boundary).

* :func:`build_read_model` produces the public read model from the
  persisted state. It is a pure function: identical persisted state always
  yields byte-equal read-model fields (AC-FR0600-02). The
  ``allowed_actions`` field is server-computed; UI clients only render
  actions in the list and cannot introduce new ones (AC-FR0600-03).

* :meth:`WorkflowAuthority.assert_revision_current` and
  :meth:`assert_action_allowed` enforce stale-revision and
  not-in-allowed-list rejection; both leave the run, artifact and external
  resources unchanged.

The module does not persist state; it operates on immutable
:class:`RunState` snapshots that the Driver/Store adapters persist.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
from typing import Optional


class Phase(str, Enum):
    """Workflow phases defined by v0.14-001 spec §3.1.

    Members:
        M_STORY: Story authoring and Human/Sage review.
        M_SPEC: Spec authoring and Human/Lex review.
        M_ACC: Acceptance authoring and Human/Lex review.
        M_LOCK_1: Three-document approval gate.
        ISSUES: Post-approval Issue/Project reconciliation.
        REQUIREMENTS_READY: Terminal state after Issue linking.
        PARKED: Terminal state for Park decision (FR-0800).
        NO_GO: Terminal state for No-Go decision (FR-0800).
    """

    M_STORY = "M-STORY"
    M_SPEC = "M-SPEC"
    M_ACC = "M-ACC"
    M_LOCK_1 = "M-LOCK-1"
    ISSUES = "ISSUES"
    REQUIREMENTS_READY = "REQUIREMENTS_READY"
    PARKED = "PARKED"
    NO_GO = "NO_GO"


class PhaseAction(str, Enum):
    """Server-computed actions a phase may expose to clients.

    Members:
        HUMAN_REVIEW: Human submits ``comment``/``no comment`` for the current
            artifact revision.
        AGENT_REPLY: Human sends a reply to the active author/reviewer Agent.
        STORY_DECISION: Human submits ``Go``/``Park``/``No-Go`` for the
            current Story revision (FR-0700).
        RETURN_UPSTREAM: Human returns to a legal upstream phase (FR-1500).
        APPROVE_M_LOCK_1: Human approves the M-LOCK-1 gate (FR-1700).
        RECONCILE_ISSUES: Human triggers Issue/Project reconcile (FR-1800).
        CANCEL_DIRTY: Human discards un saved browser edits (FR-1000).
        RETRY: Retry the read-model's currently retriable operation.
    """

    HUMAN_REVIEW = "human_review"
    AGENT_REPLY = "agent_reply"
    STORY_DECISION = "story_decision"
    RETURN_UPSTREAM = "return_upstream"
    APPROVE_M_LOCK_1 = "approve_m_lock_1"
    RECONCILE_ISSUES = "reconcile_issues"
    CANCEL_DIRTY = "cancel_dirty"
    RETRY = "retry"


LEGAL_TRANSITIONS: dict[Phase, frozenset[Phase]] = {
    Phase.M_STORY: frozenset({Phase.M_SPEC, Phase.PARKED, Phase.NO_GO}),
    Phase.M_SPEC: frozenset({Phase.M_STORY, Phase.M_ACC}),
    Phase.M_ACC: frozenset({Phase.M_SPEC, Phase.M_STORY, Phase.M_LOCK_1}),
    Phase.M_LOCK_1: frozenset({Phase.ISSUES}),
    Phase.ISSUES: frozenset({Phase.REQUIREMENTS_READY}),
    Phase.REQUIREMENTS_READY: frozenset(),
    Phase.PARKED: frozenset(),
    Phase.NO_GO: frozenset(),
}


HUMAN_ONLY_TRANSITIONS: frozenset[tuple[Phase, Phase]] = frozenset(
    (src, dst) for src, targets in LEGAL_TRANSITIONS.items() for dst in targets
)


@dataclass(frozen=True)
class RunState:
    """Immutable persisted state of a single run.

    Attributes:
        run_id: Opaque run identifier.
        phase: Current :class:`Phase`.
        revision: Monotonic run revision.
        artifact_revision: Current artifact revision (per document).
        writer: Current write-lease holder identity, or ``None``.
        review_round: Current review round number (0 when not in review).
        task_id: Active Agent task id, or ``None``.
        attempt_id: Active Agent attempt id, or ``None``.
        session_id: Active Agent session id, or ``None``.
        last_error: Non-secret last error message, or ``None``.
        allowed_actions: Server-computed allowed actions for the current
            phase. Defaults to empty.
    """

    run_id: str
    phase: Phase
    revision: int
    artifact_revision: int = 0
    writer: Optional[str] = None
    review_round: int = 0
    task_id: Optional[str] = None
    attempt_id: Optional[str] = None
    session_id: Optional[str] = None
    last_error: Optional[str] = None
    allowed_actions: tuple[PhaseAction, ...] = ()


class WorkflowStateConflict(Exception):
    """Raised when a phase transition or save violates workflow authority.

    Attributes:
        code: Always ``WORKFLOW_STATE_CONFLICT``.
        current_phase: The phase the run is currently in.
        current_revision: The current run revision.
        continue_url: URL the client can follow to recover.
    """

    def __init__(
        self,
        *,
        current_phase: Phase,
        current_revision: int,
        continue_url: str,
        message: Optional[str] = None,
    ) -> None:
        super().__init__(
            message
            or f"WORKFLOW_STATE_CONFLICT: current phase={current_phase.value} revision={current_revision}"
        )
        self.code = "WORKFLOW_STATE_CONFLICT"
        self.current_phase = current_phase
        self.current_revision = current_revision
        self.continue_url = continue_url


class ActionForbidden(Exception):
    """Raised when an action is not allowed in the current state.

    Attributes:
        code: ``HUMAN_AUTHORITY_REQUIRED`` when the caller lacks Human
            principal authority; ``WORKFLOW_STATE_CONFLICT`` when the action
            is not in the server-computed allowed list.
        current_phase: The phase the run is currently in.
        current_revision: The current run revision.
    """

    def __init__(
        self,
        *,
        code: str,
        current_phase: Phase,
        current_revision: int,
        message: str,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.current_phase = current_phase
        self.current_revision = current_revision


@dataclass(frozen=True)
class ReadModel:
    """Public read model for a run (IF-API-04).

    Attributes:
        run_id: Opaque run identifier.
        phase: Current :class:`Phase`.
        revision: Current run revision.
        artifact_revision: Current artifact revision.
        writer: Current write-lease holder, or ``None``.
        review_round: Current review round number.
        task_id: Active Agent task id, or ``None``.
        attempt_id: Active Agent attempt id, or ``None``.
        session_id: Active Agent session id, or ``None``.
        last_error: Non-secret last error, or ``None``.
        allowed_actions: Server-computed actions the UI may render.
        continue_url: URL the client can navigate to for the current state.
    """

    run_id: str
    phase: Phase
    revision: int
    artifact_revision: int
    writer: Optional[str]
    review_round: int
    task_id: Optional[str]
    attempt_id: Optional[str]
    session_id: Optional[str]
    last_error: Optional[str]
    allowed_actions: tuple[PhaseAction, ...]
    continue_url: str


def _continue_url(run_id: str) -> str:
    return f"/projects/{run_id}/current"


def build_read_model(
    state: RunState,
    *,
    allowed_actions: tuple[PhaseAction, ...] = (),
) -> ReadModel:
    """Build the public read model for ``state``.

    Args:
        state: The persisted :class:`RunState`.
        allowed_actions: Server-computed actions for the current phase.

    Returns:
        A :class:`ReadModel`. The function is pure: identical
        ``state`` and ``allowed_actions`` always return byte-equal fields.
    """
    return ReadModel(
        run_id=state.run_id,
        phase=state.phase,
        revision=state.revision,
        artifact_revision=state.artifact_revision,
        writer=state.writer,
        review_round=state.review_round,
        task_id=state.task_id,
        attempt_id=state.attempt_id,
        session_id=state.session_id,
        last_error=state.last_error,
        allowed_actions=allowed_actions,
        continue_url=_continue_url(state.run_id),
    )


class WorkflowAuthority:
    """Stateless authority for phase transitions and action validation."""

    def begin(
        self,
        *,
        run_id: str,
        phase: Phase,
        revision: int,
        artifact_revision: int = 0,
        writer: Optional[str] = None,
        review_round: int = 0,
        task_id: Optional[str] = None,
        attempt_id: Optional[str] = None,
        session_id: Optional[str] = None,
        last_error: Optional[str] = None,
        allowed_actions: tuple[PhaseAction, ...] = (),
    ) -> RunState:
        """Return a fresh :class:`RunState` snapshot.

        This does not persist the state; the Driver/Store adapter persists it.
        """
        return RunState(
            run_id=run_id,
            phase=phase,
            revision=revision,
            artifact_revision=artifact_revision,
            writer=writer,
            review_round=review_round,
            task_id=task_id,
            attempt_id=attempt_id,
            session_id=session_id,
            last_error=last_error,
            allowed_actions=allowed_actions,
        )

    def transition(
        self,
        *,
        state: RunState,
        target: Phase,
        expected_revision: int,
        actor_kind: str,
    ) -> RunState:
        """Validate and apply a phase transition.

        Args:
            state: The current :class:`RunState`.
            target: The desired target phase.
            expected_revision: The revision the caller last observed.
            actor_kind: ``human`` or ``agent``; only Human principals may
                transition phases.

        Returns:
            A new :class:`RunState` with ``phase == target`` and
            ``revision == expected_revision + 1``.

        Raises:
            WorkflowStateConflict: If ``target`` is not in
                :data:`LEGAL_TRANSITIONS` for ``state.phase``, or if
                ``expected_revision`` does not match ``state.revision``.
            ActionForbidden: If ``actor_kind != 'human'`` (IF-COMMON-01).
        """
        self.assert_revision_current(state, expected_revision)
        if target not in LEGAL_TRANSITIONS.get(state.phase, frozenset()):
            raise WorkflowStateConflict(
                current_phase=state.phase,
                current_revision=state.revision,
                continue_url=_continue_url(state.run_id),
                message=(
                    f"WORKFLOW_STATE_CONFLICT: transition {state.phase.value} "
                    f"-> {target.value} is not legal; legal targets: "
                    f"{sorted(p.value for p in LEGAL_TRANSITIONS[state.phase])}"
                ),
            )
        if actor_kind != "human":
            raise ActionForbidden(
                code="HUMAN_AUTHORITY_REQUIRED",
                current_phase=state.phase,
                current_revision=state.revision,
                message=(
                    "HUMAN_AUTHORITY_REQUIRED: phase transitions require a "
                    "Human principal; Agent/anonymous actors cannot move the "
                    "workflow pointer"
                ),
            )
        return replace(
            state,
            phase=target,
            revision=expected_revision + 1,
        )

    def assert_revision_current(
        self,
        state: RunState,
        expected_revision: int,
    ) -> None:
        """Assert ``expected_revision`` is the current run revision.

        Args:
            state: The current :class:`RunState`.
            expected_revision: The revision the caller last observed.

        Raises:
            WorkflowStateConflict: If ``expected_revision != state.revision``.
                The exception exposes the current revision/phase/continue_url
                so the client can refresh and retry.
        """
        if expected_revision != state.revision:
            raise WorkflowStateConflict(
                current_phase=state.phase,
                current_revision=state.revision,
                continue_url=_continue_url(state.run_id),
                message=(
                    f"WORKFLOW_STATE_CONFLICT: expected revision "
                    f"{expected_revision} but current is {state.revision}"
                ),
            )

    def assert_action_allowed(
        self,
        state: RunState,
        action: PhaseAction,
    ) -> None:
        """Assert ``action`` is in the server-computed allowed list.

        Args:
            state: The current :class:`RunState`.
            action: The action the client is requesting.

        Raises:
            ActionForbidden: If ``action`` is not in
                ``state.allowed_actions``. Code is
                ``WORKFLOW_STATE_CONFLICT`` and the current phase/revision are
                exposed; the run, artifact and external resources are
                unchanged.
        """
        if action not in state.allowed_actions:
            raise ActionForbidden(
                code="WORKFLOW_STATE_CONFLICT",
                current_phase=state.phase,
                current_revision=state.revision,
                message=(
                    f"WORKFLOW_STATE_CONFLICT: action {action.value} is not "
                    f"allowed in phase {state.phase.value}; allowed: "
                    f"{sorted(a.value for a in state.allowed_actions)}"
                ),
            )
