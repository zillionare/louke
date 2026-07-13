"""Project detail, artifact review and approval UI state (FR-1901).

This module provides runtime data structures and validation for the project
detail page, gate panels, artifact reviews, task controls and inline
discussions. Gate approval is blocked until bound artifacts have no open
discussions, no stale digest and all required checks pass.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any


class RunStatus(Enum):
    """High-level run status displayed in the project detail page."""

    RUNNING = auto()
    WAITING_FOR_HUMAN = auto()
    BLOCKED = auto()
    FAILED = auto()
    TERMINATED = auto()


class GateBlockedError(RuntimeError):
    """Raised when a gate approval is blocked by unresolved conditions."""


class DiscussionStatus(Enum):
    """Lifecycle status of an inline discussion thread."""

    OPEN = "open"
    RESOLVED = "resolved"
    REOPENED = "reopened"


@dataclass(frozen=True, slots=True)
class ArtifactReview:
    """Review snapshot of a bound artifact.

    Attributes:
        artifact_id: Artifact identifier.
        revision: Bound revision string.
        digest: Bound digest.
        required_reviewer: Principal required to review.
        verdict: Current verdict (pending/approved/rejected).
        open_discussions: Number of open discussion threads.
        check_results: Map of check name to result.
    """

    artifact_id: str
    revision: str = ""
    digest: str = ""
    required_reviewer: str = ""
    verdict: str = "pending"
    open_discussions: int = 0
    check_results: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class DecisionRecord:
    """Human decision on a gate.

    Attributes:
        actor: Principal id that made the decision.
        verdict: ``approve`` or ``reject``.
        reason: Optional human-readable reason.
    """

    actor: str
    verdict: str
    reason: str = ""


@dataclass
class GatePanel:
    """Gate panel state and approval validation.

    Attributes:
        gate_id: Gate identifier.
        gate_type: ``requirements_approval`` or ``m_lock``.
        artifacts: Bound artifact reviews.
        baseline_digest: Digest used as the gate baseline.
        changes_since_baseline: Files changed since the baseline.
        is_stale: Whether the gate is stale.
        approve_scope: Human-readable scope of approval.
        decision: Recorded decision, if any.
    """

    gate_id: str
    gate_type: str
    artifacts: list[ArtifactReview]
    baseline_digest: str
    changes_since_baseline: list[str]
    is_stale: bool
    approve_scope: str = ""
    decision: DecisionRecord | None = None

    def approve(self, decision: DecisionRecord) -> None:
        """Record an approval decision after validating gate conditions.

        Args:
            decision: The decision to record.

        Raises:
            GateBlockedError: If open discussions, stale digest, failed checks
                or digest mismatch exist.
        """
        blockers: list[str] = []
        for artifact in self.artifacts:
            if artifact.open_discussions > 0:
                blockers.append(
                    f"{artifact.artifact_id} has {artifact.open_discussions} open discussions"
                )
            for check, result in artifact.check_results.items():
                if result != "passed":
                    blockers.append(f"{artifact.artifact_id} check {check} is {result}")
        if self.is_stale:
            blockers.append("gate is stale")
        if blockers:
            raise GateBlockedError(f"gate {self.gate_id!r} blocked: {', '.join(blockers)}")
        self.decision = decision


@dataclass
class TaskControl:
    """Control surface for an active agent task/session.

    Attributes:
        agent_role: Agent role.
        pinned_model: Model pinned for the task.
        task_status: Task status.
        session_status: OpenCode session status.
        allowed_actions: Actions currently allowed.
    """

    agent_role: str
    pinned_model: str
    task_status: str
    session_status: str
    allowed_actions: list[str]


@dataclass
class ProjectDetail:
    """Reconstructible project detail state.

    Attributes:
        run_id: Run identifier.
        status: Current run status.
        current_step: Current workflow step.
        entry_reason: Reason for entering the current status/step.
        allowed_actions: Actions currently allowed by the definition.
    """

    run_id: str
    status: RunStatus = RunStatus.RUNNING
    current_step: str = ""
    entry_reason: str = ""
    allowed_actions: list[str] = field(default_factory=list)

    def apply_event(self, event: dict[str, Any]) -> None:
        """Update detail state from a runtime event.

        Args:
            event: Runtime event dict with ``type`` and payload.
        """
        event_type = event.get("type")
        if event_type == "status_changed":
            self.status = RunStatus[event.get("status", "RUNNING").upper()]
        elif event_type == "step_changed":
            self.current_step = event.get("step", "")


@dataclass(frozen=True, slots=True)
class DiscussionThread:
    """Canonical inline discussion thread.

    Attributes:
        thread_id: Stable opaque identifier.
        doc_id: Document the thread belongs to.
        anchor: Anchor within the document.
        speaker: Speaker principal.
        body: Text body.
        depth: Nesting depth (1 = top-level).
        status: Thread status.
    """

    thread_id: str
    doc_id: str
    anchor: str
    speaker: str
    body: str
    depth: int
    status: DiscussionStatus


class InlineDiscussionStore:
    """Store for inline discussions with canonical serialization.

    Threads are persisted in a canonical ``speaker/depth/status`` form that the
gate parser can round-trip.
    """

    def __init__(self) -> None:
        self._threads: dict[str, DiscussionThread] = {}

    def add(
        self,
        doc_id: str,
        anchor: str,
        speaker: str,
        body: str,
        status: DiscussionStatus = DiscussionStatus.OPEN,
        depth: int = 1,
    ) -> DiscussionThread:
        """Add a new inline discussion thread.

        Args:
            doc_id: Document identifier.
            anchor: Document anchor.
            speaker: Speaker principal.
            body: Thread body.
            status: Initial status.
            depth: Nesting depth.

        Returns:
            The created :class:`DiscussionThread`.
        """
        thread = DiscussionThread(
            thread_id=f"thread_{uuid.uuid4().hex[:12]}",
            doc_id=doc_id,
            anchor=anchor,
            speaker=speaker,
            body=body,
            depth=depth,
            status=status,
        )
        self._threads[thread.thread_id] = thread
        return thread

    def to_canonical(self, thread_id: str) -> str:
        """Serialize a thread to canonical form.

        Args:
            thread_id: Thread identifier.

        Returns:
            Canonical string representation.

        Raises:
            KeyError: If the thread does not exist.
        """
        thread = self._threads[thread_id]
        payload = {
            "speaker": thread.speaker,
            "depth": thread.depth,
            "status": thread.status.value,
            "body": thread.body,
            "anchor": thread.anchor,
            "doc_id": thread.doc_id,
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":"))

    def parse_canonical(self, canonical: str) -> dict[str, Any]:
        """Parse a canonical thread representation.

        Args:
            canonical: Canonical string.

        Returns:
            Parsed dict.

        Raises:
            ValueError: If the canonical form is invalid.
        """
        try:
            parsed = json.loads(canonical)
        except json.JSONDecodeError as exc:
            raise ValueError("invalid canonical discussion form") from exc
        required = {"speaker", "depth", "status"}
        if not required.issubset(parsed.keys()):
            raise ValueError("canonical discussion missing required fields")
        return parsed
