"""Human gate service: challenge, principal binding and decision validation.

This module implements the unbypassable human gate required by FR-0501.
It persists gate records, validates host-authenticated principals and ensures
that any transition through a ``human_gate`` step is backed by an approved,
fresh gate decision bound to the current artifact digest.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from louke.runtime.domain import (
    IllegalTransitionError,
    RuntimeStateError,
)
from louke.runtime.events import EventBuilder

if TYPE_CHECKING:
    from louke.runtime.store import WorkflowRun, WorkflowRunStore

GATE_WAITING: str = "waiting_for_human"
GATE_APPROVED: str = "approved"
GATE_REJECTED: str = "rejected"

DECISION_APPROVE: str = "approve"
DECISION_REJECT: str = "reject"


class GateError(RuntimeStateError):
    """Base class for human gate errors."""


class GateNotApprovedError(GateError, IllegalTransitionError):
    """Raised when a run tries to advance through a gate without an approved decision."""


class GateNotFoundError(GateError):
    """Raised when a referenced gate does not exist."""


class StaleGateError(GateError):
    """Raised when a gate decision references an expired challenge/revision/digest."""

    def __init__(
        self,
        message: str,
        current_revision: int | None = None,
        current_digest: str | None = None,
    ) -> None:
        super().__init__(message)
        self.current_revision = current_revision
        self.current_digest = current_digest


class UnauthenticatedPrincipalError(GateError):
    """Raised when a gate decision lacks a host-authenticated human principal."""


class DuplicateDecisionError(GateError):
    """Raised when a decision is submitted for a gate that already has one."""


@dataclass(frozen=True, slots=True)
class Gate:
    """A persisted human gate record.

    Attributes:
        gate_id: Opaque stable identifier for the gate.
        challenge_id: Opaque challenge identifier bound to this gate decision.
        run_id: Opaque run identifier the gate belongs to.
        step_id: The human_gate step this gate controls.
        expected_revision: Run revision the gate was created at.
        bound_digest: Artifact digest the principal must approve.
        status: Gate lifecycle status (``waiting_for_human``, ``approved``,
            ``rejected`` or ``stale``).
        actor_id: Authenticated principal id for the recorded decision.
        reason: Human-readable reason when the gate was rejected.
        decided_at: ISO 8601 UTC timestamp of the decision, when recorded.
        created_at: ISO 8601 UTC timestamp of gate creation.
    """

    gate_id: str
    challenge_id: str
    run_id: str
    step_id: str
    expected_revision: int
    bound_digest: str
    status: str = GATE_WAITING
    actor_id: str | None = None
    reason: str | None = None
    decided_at: str | None = None
    created_at: str | None = None

    def with_decision(
        self,
        status: str,
        actor_id: str,
        reason: str | None = None,
    ) -> "Gate":
        """Return a new gate with a recorded decision."""
        now = datetime.now(timezone.utc).isoformat()
        return Gate(
            gate_id=self.gate_id,
            challenge_id=self.challenge_id,
            run_id=self.run_id,
            step_id=self.step_id,
            expected_revision=self.expected_revision,
            bound_digest=self.bound_digest,
            status=status,
            actor_id=actor_id,
            reason=reason,
            decided_at=now,
            created_at=self.created_at,
        )

    def with_digest(self, new_digest: str) -> "Gate":
        """Return a new gate rebound to ``new_digest`` and reset to pending."""
        return Gate(
            gate_id=self.gate_id,
            challenge_id=f"chal_{uuid.uuid4().hex[:12]}",
            run_id=self.run_id,
            step_id=self.step_id,
            expected_revision=self.expected_revision,
            bound_digest=new_digest,
            status=GATE_WAITING,
            actor_id=None,
            reason=None,
            decided_at=None,
            created_at=self.created_at,
        )


class GateService:
    """Validate and record human gate decisions.

    The service is the only authority that may declare a gate ``approved`` or
    ``rejected``. It relies on the caller to supply a host-authenticated
    principal; free-text ``approved_by`` fields are rejected.

    Args:
        store: The workflow run store used for persistence.
    """

    def __init__(self, store: "WorkflowRunStore") -> None:
        self._store = store

    def ensure_gate(
        self,
        run_id: str,
        step_id: str,
        bound_digest: str,
    ) -> Gate:
        """Return an existing active gate for ``run_id``/``step_id`` or create one.

        If a gate exists for the run/step and its digest matches ``bound_digest``,
        it is returned. If the digest differs, the existing decision is invalidated
        and a new pending gate bound to ``bound_digest`` is created.

        Args:
            run_id: The run to ensure a gate for.
            step_id: The human_gate step the gate controls.
            bound_digest: Artifact digest to bind the gate to.

        Returns:
            The active gate record.
        """
        existing = self._store.get_gate_for_run_step(run_id, step_id)
        if existing is not None:
            if existing.bound_digest == bound_digest:
                return existing
            new_gate = existing.with_digest(bound_digest)
            self._store.update_gate(new_gate)
            return new_gate

        now = datetime.now(timezone.utc).isoformat()
        gate = Gate(
            gate_id=f"gate_{uuid.uuid4().hex[:12]}",
            challenge_id=f"chal_{uuid.uuid4().hex[:12]}",
            run_id=run_id,
            step_id=step_id,
            expected_revision=self._store.get_run(run_id).revision,
            bound_digest=bound_digest,
            status=GATE_WAITING,
            created_at=now,
        )
        self._store.create_gate(gate)
        return gate

    def submit_decision(
        self,
        run_id: str,
        gate_id: str,
        decision: str,
        bound_digest: str,
        expected_revision: int,
        principal: dict[str, str] | None,
        reason: str | None = None,
    ) -> Gate:
        """Submit a human decision for ``gate_id``.

        Args:
            run_id: The run the gate belongs to.
            gate_id: The gate identifier.
            decision: ``approve`` or ``reject``.
            bound_digest: The artifact digest the principal is deciding on.
            expected_revision: The run revision the caller last observed.
            principal: Host-authenticated principal metadata. Must contain a
                ``kind`` of ``human`` and a non-empty ``id``.
            reason: Required when ``decision`` is ``reject``.

        Returns:
            The gate record after recording the decision.

        Raises:
            UnauthenticatedPrincipalError: If ``principal`` is missing or not a
                host-authenticated human principal.
            GateNotFoundError: If the gate does not exist or does not belong to
                the run/step.
            StaleGateError: If the challenge, revision, step or digest has
                changed since the gate was created.
            DuplicateDecisionError: If the gate already has a recorded decision.
        """
        gate = self._store.get_gate(gate_id)
        run = self._store.get_run(run_id)

        if gate.run_id != run_id:
            raise GateNotFoundError(
                f"gate {gate_id!r} does not belong to run {run_id!r}"
            )

        self._validate_principal(principal)
        actor_id = principal["id"]

        self._validate_freshness(gate, run, bound_digest, expected_revision)

        if gate.status in (GATE_APPROVED, GATE_REJECTED):
            raise DuplicateDecisionError(
                f"gate {gate_id!r} already has status {gate.status!r}"
            )

        if decision == DECISION_REJECT:
            if not reason:
                raise GateError("reject decision requires a reason")
            return self._persist_decision(
                gate=gate,
                run=run,
                status=GATE_REJECTED,
                actor_id=actor_id,
                reason=reason,
            )

        if decision == DECISION_APPROVE:
            return self._persist_decision(
                gate=gate,
                run=run,
                status=GATE_APPROVED,
                actor_id=actor_id,
            )

        raise GateError(f"unknown decision {decision!r}")

    def _persist_decision(
        self,
        gate: Gate,
        run: "WorkflowRun",
        status: str,
        actor_id: str,
        reason: str | None = None,
    ) -> Gate:
        """Persist a gate decision and emit an evidence event."""
        decided_gate = gate.with_decision(
            status=status,
            actor_id=actor_id,
            reason=reason,
        )
        self._store.update_gate(decided_gate)
        event = EventBuilder(run).gate_decision(
            gate=decided_gate,
            decision=status,
            actor_id=actor_id,
            reason=reason,
        )
        self._store.append_event(event)
        return decided_gate

    def _validate_principal(self, principal: dict[str, str] | None) -> None:
        """Ensure ``principal`` represents a host-authenticated human actor."""
        if principal is None:
            raise UnauthenticatedPrincipalError("missing authenticated principal")
        if principal.get("kind") != "human":
            raise UnauthenticatedPrincipalError(
                "principal must be a host-authenticated human"
            )
        if not principal.get("id"):
            raise UnauthenticatedPrincipalError("principal id is required")

    def _validate_freshness(
        self,
        gate: Gate,
        run: "WorkflowRun",
        bound_digest: str,
        expected_revision: int,
    ) -> None:
        """Validate that the gate decision matches the current challenge/revision/digest."""
        if run.revision != expected_revision:
            raise StaleGateError(
                "run revision has changed since the gate was created",
                current_revision=run.revision,
            )
        if run.current_step != gate.step_id:
            raise StaleGateError(f"run is no longer at step {gate.step_id!r}")
        if gate.bound_digest != bound_digest:
            raise StaleGateError(
                "artifact digest has changed since the gate was created",
                current_digest=gate.bound_digest,
            )
