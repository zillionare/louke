"""Requirements approval and M-LOCK gate coordination.

This module implements the artifact-bound gates required by FR-0801 and
FR-0901. It computes deterministic digests over named artifact sets and uses
the generic gate service to create, rebind and challenge human gates.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import TYPE_CHECKING

from louke.runtime.events import EventBuilder
from louke.runtime.gates import GateNotApprovedError

if TYPE_CHECKING:
    from louke.runtime.gates import Gate, GateService
    from louke.runtime.store import WorkflowRun, WorkflowRunStore

#: Step id of the requirements approval human gate (FR-0801).
REQUIREMENTS_APPROVAL_STEP_ID: str = "requirements_approval"

#: Step id of the M-LOCK human gate (FR-0901).
M_LOCK_STEP_ID: str = "m_lock"


def contract_digest(artifacts: dict[str, str]) -> str:
    """Return a deterministic digest of an ordered artifact map.

    Args:
        artifacts: Mapping from artifact role to artifact digest. Roles are
            sorted alphabetically before hashing so the digest is stable.

    Returns:
        A ``sha256:`` prefixed digest string.
    """
    payload = {role: artifacts[role] for role in sorted(artifacts)}
    content = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return f"sha256:{hashlib.sha256(content.encode()).hexdigest()}"


@dataclass(frozen=True, slots=True)
class RequirementArtifacts:
    """Digest bundle for the three requirements documents."""

    story: str
    spec: str
    acceptance: str

    def digest(self) -> str:
        """Return the combined digest of the three requirement artifacts."""
        return contract_digest(
            {"story": self.story, "spec": self.spec, "acceptance": self.acceptance}
        )


class RequirementGateCoordinator:
    """Coordinate the requirements approval gate for a workflow run.

    The coordinator binds the gate to the combined digest of story, spec and
    acceptance. When the bound digest changes, the existing decision is
    invalidated and a new pending gate is created.

    Args:
        store: The workflow run store used for persistence and event logging.
        gate_service: The generic gate service.
    """

    _STEP_ID: str = REQUIREMENTS_APPROVAL_STEP_ID

    def __init__(
        self,
        store: "WorkflowRunStore",
        gate_service: "GateService",
    ) -> None:
        self._store = store
        self._gate_service = gate_service

    def ensure_gate(
        self,
        run_id: str,
        story_digest: str,
        spec_digest: str,
        acceptance_digest: str,
    ) -> "Gate":
        """Ensure a requirements approval gate bound to the current digest.

        When the bound documents change after a prior approval, the old approval
        is recorded as stale before the gate is rebound to the new digest, so
        the design flow cannot continue on the old approval (FR-0801 AC-4).

        Args:
            run_id: The run to ensure the gate for.
            story_digest: Digest of the story document.
            spec_digest: Digest of the spec document.
            acceptance_digest: Digest of the acceptance document.

        Returns:
            The active requirements gate record.
        """
        artifacts = RequirementArtifacts(
            story=story_digest,
            spec=spec_digest,
            acceptance=acceptance_digest,
        )
        new_digest = artifacts.digest()
        run = self._store.get_run(run_id)
        existing = self._store.get_gate_for_run_step(run_id, self._STEP_ID)
        if self._is_stale_approval(existing, new_digest):
            self._append_stale_event(run, existing)
        gate = self._gate_service.ensure_gate(
            run_id=run_id,
            step_id=self._STEP_ID,
            bound_digest=new_digest,
        )
        event = EventBuilder(run).build(
            event_type="gate.created",
            step_id=self._STEP_ID,
            details={
                "gate_id": gate.gate_id,
                "step_id": self._STEP_ID,
                "bound_digest": gate.bound_digest,
            },
            input_digest=new_digest,
            output_digest=gate.bound_digest,
        )
        self._store.append_event(event)
        return gate

    @staticmethod
    def _is_stale_approval(existing: "Gate | None", new_digest: str) -> bool:
        """Return True if ``existing`` is an approved gate whose digest changed."""
        return (
            existing is not None
            and existing.status == "approved"
            and existing.bound_digest != new_digest
        )

    def _append_stale_event(self, run: "WorkflowRun", gate: "Gate") -> None:
        """Append a ``gate.stale`` event recording the invalidated approval.

        Args:
            run: The run the gate belongs to.
            gate: The previously approved gate whose digest has changed.
        """
        event = EventBuilder(run).build(
            event_type="gate.stale",
            step_id=self._STEP_ID,
            details={
                "gate_id": gate.gate_id,
                "step_id": self._STEP_ID,
                "bound_digest": gate.bound_digest,
                "actor_id": gate.actor_id,
                "reason": gate.reason,
            },
            input_digest=gate.bound_digest,
            output_digest=gate.bound_digest,
        )
        self._store.append_event(event)

    def check_approval(self, run_id: str) -> "Gate":
        """Return the requirements gate only if it is approved.

        Args:
            run_id: The run to check.

        Returns:
            The approved requirements gate.

        Raises:
            GateNotApprovedError: If no requirements gate exists or its status
                is not ``approved``.
        """
        gate = self._store.get_gate_for_run_step(run_id, self._STEP_ID)
        if gate is None or gate.status != "approved":
            raise GateNotApprovedError(
                "requirements approval is required before design tasks"
            )
        return gate


class MLockGateCoordinator:
    """Coordinate the M-LOCK gate that gates implementation steps (FR-0901).

    A run may only enter implementation steps (``semantic_task`` or
    ``decision``) after the M-LOCK human gate has been approved. This
    coordinator exposes the read-side check used by the orchestrator to block
    implementation transitions before M-LOCK approval.

    Args:
        store: The workflow run store used for persistence and event logging.
        gate_service: The generic gate service.
    """

    _STEP_ID: str = M_LOCK_STEP_ID

    def __init__(
        self,
        store: "WorkflowRunStore",
        gate_service: "GateService",
    ) -> None:
        self._store = store
        self._gate_service = gate_service

    def check_approval(self, run_id: str) -> "Gate":
        """Return the M-LOCK gate only if it is approved.

        Args:
            run_id: The run to check.

        Returns:
            The approved M-LOCK gate.

        Raises:
            GateNotApprovedError: If no M-LOCK gate exists or its status is
                not ``approved``.
        """
        gate = self._store.get_gate_for_run_step(run_id, self._STEP_ID)
        if gate is None or gate.status != "approved":
            raise GateNotApprovedError(
                "M-LOCK approval is required before implementation steps"
            )
        return gate
