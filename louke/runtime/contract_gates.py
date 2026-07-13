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

if TYPE_CHECKING:
    from louke.runtime.gates import Gate, GateService
    from louke.runtime.store import WorkflowRunStore


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

    _STEP_ID: str = "requirements_approval"

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
        gate = self._gate_service.ensure_gate(
            run_id=run_id,
            step_id=self._STEP_ID,
            bound_digest=artifacts.digest(),
        )
        event = EventBuilder(self._store.get_run(run_id)).build(
            event_type="gate.created",
            step_id=self._STEP_ID,
            details={
                "gate_id": gate.gate_id,
                "step_id": self._STEP_ID,
                "bound_digest": gate.bound_digest,
            },
            input_digest=artifacts.digest(),
            output_digest=gate.bound_digest,
        )
        self._store.append_event(event)
        return gate
