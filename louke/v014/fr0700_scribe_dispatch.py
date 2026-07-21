"""FR-0700: Scribe 调查、分流建议与 Human 裁决.

Implements the deterministic contract slice of FR-0700:

* :func:`dispatch_scribe_investigation` builds the public Scribe task
  manifest for M-STORY. The manifest carries run/step/attempt, spec id,
  Story revision and digest, Story template path and digest, the human's
  original request, Foundation manifest identity, and (in non-first rounds)
  the digests of previous feedback. The write scope is fixed to
  ``("story.md",)``; Scribe cannot write Spec, Acceptance or any other file
  during M-STORY.

* :class:`ScribeSuggestion` captures a Go/Park/No-Go suggestion with
  reasoning. Applying a suggestion to a run state keeps the run in
  ``waiting_human`` at ``M-STORY`` and produces zero M-SPEC tasks; the
  suggestion alone never moves the workflow pointer (FR-0700 AC-02).

* :func:`record_story_decision` is the only authority that records a Human
  story decision. It rejects stale revisions
  (``WORKFLOW_STATE_CONFLICT``), Agent-transport callers
  (``HUMAN_AUTHORITY_REQUIRED``) and values outside {Go, Park, No-Go}
  (``VALIDATION_FAILED``). A valid Human decision on the current revision
  records actor, revision, value and a UTC RFC 3339 timestamp (FR-0700
  AC-03).

The module does not persist state; it produces deterministic records that
the Driver/Store adapters persist.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from enum import Enum
from typing import Optional


FOUNDATION_MANIFEST_REQUIRED = "FOUNDATION_MANIFEST_REQUIRED"


class StoryDecisionValue(str, Enum):
    """Legal Human story-decision values.

    Members:
        GO: Proceed with M-STORY interview and handoff.
        PARK: Park the request in Backlog (FR-0800).
        NO_GO: Reject the request (FR-0800).
    """

    GO = "Go"
    PARK = "Park"
    NO_GO = "No-Go"


_LEGAL_DECISION_VALUES: frozenset[str] = frozenset(v.value for v in StoryDecisionValue)


@dataclass(frozen=True)
class ScribeTaskManifest:
    """Public Scribe task manifest for M-STORY.

    Attributes:
        run_id: Opaque run identifier.
        phase: Always ``M-STORY`` for this manifest.
        attempt_id: Stable attempt identifier bound to the Scribe session.
        spec_id: Canonical spec identifier.
        story_revision: Current Story revision the Scribe reads.
        story_digest: ``sha256:<hex>`` digest of the current Story bytes.
        story_template_path: Canonical Story template path.
        story_template_digest: ``sha256:<hex>`` digest of the template bytes.
        human_request: The human's original one-sentence设想.
        foundation_manifest_identity: Stable identity of the Foundation
            manifest the run is bound to.
        round_number: Review round (1 for the first investigation).
        previous_feedback_digests: Digests of previous-round feedback; empty
            in round 1.
        write_scope: Always ``("story.md",)`` for M-STORY Scribe.
    """

    run_id: str
    phase: str
    attempt_id: str
    spec_id: str
    story_revision: int
    story_digest: str
    story_template_path: str
    story_template_digest: str
    human_request: str
    foundation_manifest_identity: str
    round_number: int
    previous_feedback_digests: tuple[str, ...]
    write_scope: tuple[str, ...] = ("story.md",)


def dispatch_scribe_investigation(
    *,
    run_id: str,
    story_revision: int,
    story_digest: str,
    story_template_path: str,
    story_template_digest: str,
    human_request: str,
    foundation_manifest_identity: str,
    spec_id: str = "v0.14-001-workflow-reflow-spec",
    round_number: int = 1,
    previous_feedback_digests: tuple[str, ...] = (),
    attempt_id: str = "att_scribe_1",
) -> ScribeTaskManifest:
    """Build the Scribe task manifest for an M-STORY investigation.

    Args:
        run_id: Opaque run identifier.
        story_revision: Current Story revision the Scribe must read.
        story_digest: ``sha256:<hex>`` digest of the current Story bytes.
        story_template_path: Canonical Story template path.
        story_template_digest: ``sha256:<hex>`` digest of the template bytes.
        human_request: The human's original one-sentence设想.
        foundation_manifest_identity: Stable Foundation manifest identity;
            must be non-empty.
        spec_id: Canonical spec identifier.
        round_number: Review round (1 for the first investigation).
        previous_feedback_digests: Digests of previous-round feedback; must
            be empty when ``round_number == 1``.
        attempt_id: Stable attempt identifier bound to the Scribe session.

    Returns:
        A :class:`ScribeTaskManifest` with ``write_scope == ('story.md',)``.

    Raises:
        ValueError: If ``foundation_manifest_identity`` is empty or
            ``previous_feedback_digests`` is non-empty in round 1.

    Side effects:
        None.
    """
    if not foundation_manifest_identity:
        raise ValueError(
            f"{FOUNDATION_MANIFEST_REQUIRED}: Scribe task requires a Foundation manifest identity"
        )
    if round_number == 1 and previous_feedback_digests:
        raise ValueError(
            "previous_feedback_digests must be empty in round 1 (no prior feedback yet)"
        )
    return ScribeTaskManifest(
        run_id=run_id,
        phase="M-STORY",
        attempt_id=attempt_id,
        spec_id=spec_id,
        story_revision=story_revision,
        story_digest=story_digest,
        story_template_path=story_template_path,
        story_template_digest=story_template_digest,
        human_request=human_request,
        foundation_manifest_identity=foundation_manifest_identity,
        round_number=round_number,
        previous_feedback_digests=previous_feedback_digests,
        write_scope=("story.md",),
    )


@dataclass(frozen=True)
class ScribeSuggestion:
    """Scribe's Go/Park/No-Go suggestion with reasoning.

    Attributes:
        suggestion: One of ``Go``, ``Park``, ``No-Go``.
        reasoning: Non-empty reasoning text.
    """

    suggestion: str
    reasoning: str

    def apply_to_run_state(self) -> "SuggestionRunState":
        """Return the run state that results from a Scribe suggestion.

        The run stays ``waiting_human`` at ``M-STORY`` with zero M-SPEC
        tasks; the suggestion alone never moves the workflow pointer.

        Returns:
            A :class:`SuggestionRunState` capturing the deterministic
            post-suggestion state.
        """
        if self.suggestion not in _LEGAL_DECISION_VALUES:
            raise ValueError(
                f"ScribeSuggestion.suggestion must be one of "
                f"{sorted(_LEGAL_DECISION_VALUES)}; got {self.suggestion!r}"
            )
        if not self.reasoning.strip():
            raise ValueError("ScribeSuggestion.reasoning must be non-empty")
        return SuggestionRunState(
            status="waiting_human",
            current_step="M-STORY",
            m_spec_task_count=0,
            suggestion=self,
        )


@dataclass(frozen=True)
class SuggestionRunState:
    """Run state after a Scribe suggestion has been received.

    Attributes:
        status: Always ``waiting_human``.
        current_step: Always ``M-STORY``.
        m_spec_task_count: Always ``0``; the suggestion alone does not
            dispatch an M-SPEC task.
        suggestion: The :class:`ScribeSuggestion` that produced this state.
    """

    status: str
    current_step: str
    m_spec_task_count: int
    suggestion: ScribeSuggestion


@dataclass(frozen=True)
class StoryDecisionRecord:
    """Recorded Human story decision (FR-0700 AC-03).

    Attributes:
        actor: Non-secret Human principal identity (e.g. ``human:alice``).
        story_revision: The Story revision the decision was made on.
        value: The :class:`StoryDecisionValue` chosen by the Human.
        decided_at: UTC RFC 3339 timestamp.
    """

    actor: str
    story_revision: int
    value: StoryDecisionValue
    decided_at: str


class DecisionRejected(Exception):
    """Raised when a story decision is rejected.

    Attributes:
        code: ``WORKFLOW_STATE_CONFLICT`` (stale revision),
            ``HUMAN_AUTHORITY_REQUIRED`` (Agent/anonymous caller) or
            ``VALIDATION_FAILED`` (value outside {Go, Park, No-Go}).
        recorded: Always ``None``; no decision is recorded on rejection.
    """

    def __init__(self, *, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.recorded: Optional[StoryDecisionRecord] = None


def _now_iso_utc() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def record_story_decision(
    *,
    story_revision: int,
    expected_revision: int,
    value: StoryDecisionValue,
    actor: str,
    actor_kind: str,
) -> StoryDecisionRecord:
    """Validate and record a Human story decision.

    Args:
        story_revision: The Story revision the decision is made on.
        expected_revision: The revision the caller last observed; must equal
            ``story_revision``.
        value: The :class:`StoryDecisionValue` chosen by the Human.
        actor: Non-secret Human principal identity.
        actor_kind: ``human`` or ``agent``; only ``human`` is accepted.

    Returns:
        A :class:`StoryDecisionRecord` with actor, revision, value and a
        UTC RFC 3339 timestamp.

    Raises:
        DecisionRejected: If the revision is stale, the caller is not a
            Human principal or the value is outside {Go, Park, No-Go}. In
            every rejection case ``recorded is None``.

    Side effects:
        None. The function is pure; the Driver/Store adapter persists the
        returned record.
    """
    if expected_revision != story_revision:
        raise DecisionRejected(
            code="WORKFLOW_STATE_CONFLICT",
            message=(
                f"expected revision {expected_revision} does not match "
                f"current Story revision {story_revision}"
            ),
        )
    if actor_kind != "human":
        raise DecisionRejected(
            code="HUMAN_AUTHORITY_REQUIRED",
            message=(
                "story decisions require a Human principal; "
                "Agent/anonymous actors cannot decide Go/Park/No-Go"
            ),
        )
    if (
        not isinstance(value, StoryDecisionValue)
        or value.value not in _LEGAL_DECISION_VALUES
    ):
        raise DecisionRejected(
            code="VALIDATION_FAILED",
            message=(
                f"story decision value must be one of "
                f"{sorted(_LEGAL_DECISION_VALUES)}; got {value!r}"
            ),
        )
    return StoryDecisionRecord(
        actor=actor,
        story_revision=story_revision,
        value=value,
        decided_at=_now_iso_utc(),
    )
