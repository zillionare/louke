"""Requirements approval and M-LOCK gate coordination.

This module implements the artifact-bound gates required by FR-0801 and
FR-0901. It computes deterministic digests over named artifact sets and uses
the generic gate service to create, rebind and challenge human gates. It also
provides the bug_fix source-contract inheritance verifier required by
FR-0801 AC-6.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from louke.runtime.domain import RuntimeStateError
from louke.runtime.events import EventBuilder
from louke.runtime.gates import GATE_INHERITED, GateNotApprovedError

if TYPE_CHECKING:
    from louke.runtime.gates import Gate, GateService
    from louke.runtime.store import WorkflowRun, WorkflowRunStore

#: Step id of the requirements approval human gate (FR-0801).
REQUIREMENTS_APPROVAL_STEP_ID: str = "requirements_approval"

#: Step id of the M-LOCK human gate (FR-0901).
M_LOCK_STEP_ID: str = "m_lock"

#: Behavior change claim that allows a bug_fix to inherit source approval.
BEHAVIOR_DEVIATION_ONLY: str = "implementation_deviation_only"

#: Behavior change claim that disqualifies a bug_fix from inheritance.
BEHAVIOR_CHANGE: str = "behavior_change"


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
        """Return the requirements gate only if it is approved or inherited.

        A gate whose status is ``approved`` was authorised by a human
        principal against the current digest. A gate whose status is
        ``inherited`` was carried over from an approved source contract by a
        ``bug_fix`` run (FR-0801 AC-6) without a new human decision. Both
        satisfy the requirements approval precondition for design tasks.

        Args:
            run_id: The run to check.

        Returns:
            The approved or inherited requirements gate.

        Raises:
            GateNotApprovedError: If no requirements gate exists or its status
                is neither ``approved`` nor ``inherited``.
        """
        gate = self._store.get_gate_for_run_step(run_id, self._STEP_ID)
        if gate is None or gate.status not in ("approved", GATE_INHERITED):
            raise GateNotApprovedError(
                "requirements approval is required before design tasks"
            )
        return gate

    def apply_inherited_approval(
        self,
        run_id: str,
        inherited: InheritedApproval,
    ) -> "Gate":
        """Record an inherited requirements approval on a bug_fix run.

        Creates a requirements approval gate for ``run_id`` whose status is
        ``inherited`` and whose ``bound_digest`` is the source approval's bound
        digest, without ever entering ``waiting_for_human``. Appends a
        ``requirements.approval.inherited`` event recording the source gate
        id, GitHub Issue and bound digest so the inheritance is auditable
        (FR-0801 AC-6).

        Args:
            run_id: The bug_fix run inheriting the source approval.
            inherited: The inherited approval record returned by the verifier.

        Returns:
            The persisted inherited requirements gate.

        Raises:
            HotfixInheritanceError: If a requirements gate already exists for
                the run, since inheritance must not silently overwrite a gate
                that was created by another path.
        """
        existing = self._store.get_gate_for_run_step(run_id, self._STEP_ID)
        if existing is not None:
            raise HotfixInheritanceError(
                f"run {run_id!r} already has a requirements gate "
                f"(status {existing.status!r}); cannot apply inherited approval"
            )

        run = self._store.get_run(run_id)
        now = datetime.now(timezone.utc).isoformat()
        gate = _make_inherited_gate(
            run_id=run_id,
            step_id=self._STEP_ID,
            bound_digest=inherited.bound_digest,
            expected_revision=run.revision,
            created_at=now,
            decided_at=inherited.inherited_at,
        )
        self._store.create_gate(gate)

        event = EventBuilder(run).build(
            event_type="requirements.approval.inherited",
            step_id=self._STEP_ID,
            details={
                "gate_id": gate.gate_id,
                "step_id": self._STEP_ID,
                "source_approval_gate_id": inherited.source_approval_gate_id,
                "github_issue": inherited.github_issue,
                "bound_digest": inherited.bound_digest,
            },
            input_digest=inherited.bound_digest,
            output_digest=inherited.bound_digest,
        )
        self._store.append_event(event)
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


@dataclass(frozen=True, slots=True)
class SourceContract:
    """A bug_fix source contract referencing an approved source spec/AC.

    A ``bug_fix`` run references the existing GitHub Issue it targets and the
    already approved source spec/acceptance it inherits its requirements
    approval from. The ``behavior_change`` claim records whether the fix only
    corrects an implementation deviation or actually changes expected
    behavior; only the former is eligible for inheritance (FR-0801 AC-6).

    Attributes:
        github_issue: The GitHub Issue the bug_fix targets (e.g.
            ``owner/repo#42``). Must be non-empty.
        source_spec_digest: Digest of the source spec the bug_fix references.
        source_acceptance_digest: Digest of the source acceptance the
            bug_fix references.
        source_approval_gate_id: Id of the source run's approved requirements
            gate whose approval is being inherited.
        source_approval_bound_digest: The bound digest of the source approval
            gate at the time it was approved. Must match the persisted
            source gate's ``bound_digest``.
        behavior_change: ``implementation_deviation_only`` for inheritance
            eligibility, or ``behavior_change`` to force the run into a new
            requirements flow.
    """

    github_issue: str
    source_spec_digest: str
    source_acceptance_digest: str
    source_approval_gate_id: str
    source_approval_bound_digest: str
    behavior_change: str


@dataclass(frozen=True, slots=True)
class InheritedApproval:
    """Record that a bug_fix run inherited an existing source approval.

    Attributes:
        run_id: The bug_fix run that inherited the approval.
        source_approval_gate_id: Id of the source run's approved requirements
            gate whose approval was inherited.
        github_issue: The GitHub Issue the bug_fix targets.
        bound_digest: The bound digest of the source approval gate, carried
            over so the bug_fix run's inherited approval is bound to the same
            artifact digest.
        inherited_at: ISO 8601 UTC timestamp of the inheritance.
    """

    run_id: str
    source_approval_gate_id: str
    github_issue: str
    bound_digest: str
    inherited_at: str


class HotfixInheritanceError(RuntimeStateError):
    """Raised when a bug_fix cannot prove source contract inheritance.

    The hotfix quick path is rejected when the source contract is missing a
    GitHub Issue mapping, claims a behavior change, or references a source
    approval that is not actually approved or whose bound digest does not
    match. The caller must fall back to a new requirements flow.
    """


class BugFixInheritanceVerifier:
    """Verify a bug_fix source contract inherits an existing approval.

    The verifier is the program-side of the ``source_contract.verify`` step
    in a ``bug_fix`` workflow definition (FR-0801 AC-6). It checks that:

    - The source contract references a non-empty GitHub Issue.
    - The behavior change claim is ``implementation_deviation_only``; a
      behavior change disqualifies the run from inheritance.
    - The referenced source approval gate exists and is approved.
    - The contract's ``source_approval_bound_digest`` matches the persisted
      source gate's ``bound_digest`` so the inheritance cannot be claimed
      against a stale or rewritten source.

    When all checks pass, the verifier returns an :class:`InheritedApproval`
    record. The orchestrator records this approval on the bug_fix run
    without creating a new ``waiting_for_human`` requirements gate.

    Args:
        store: The workflow run store used to look up the source approval gate.
    """

    def __init__(self, store: "WorkflowRunStore") -> None:
        self._store = store

    def verify(
        self,
        run_id: str,
        source_contract: SourceContract,
    ) -> InheritedApproval:
        """Verify ``source_contract`` and return the inherited approval.

        Args:
            run_id: The bug_fix run inheriting the source approval.
            source_contract: The source contract referencing the approved
                source spec/AC.

        Returns:
            The :class:`InheritedApproval` record carrying the source gate id,
            GitHub Issue and bound digest.

        Raises:
            HotfixInheritanceError: If the GitHub Issue mapping is missing,
                the behavior change claim disqualifies inheritance, or the
                referenced source approval gate is not approved or its bound
                digest does not match.
        """
        if not source_contract.github_issue:
            raise HotfixInheritanceError(
                "bug_fix source contract requires a GitHub Issue mapping"
            )
        if source_contract.behavior_change != BEHAVIOR_DEVIATION_ONLY:
            raise HotfixInheritanceError(
                "bug_fix claims a behavior change; a new requirements flow is "
                "required instead of inheriting source approval"
            )

        source_gate = self._store.get_gate(source_contract.source_approval_gate_id)
        if source_gate.status != "approved":
            raise HotfixInheritanceError(
                f"source approval gate {source_gate.gate_id!r} is not approved "
                f"(status {source_gate.status!r})"
            )
        if source_gate.bound_digest != source_contract.source_approval_bound_digest:
            raise HotfixInheritanceError(
                "source approval bound digest does not match the persisted "
                "source gate digest"
            )

        return InheritedApproval(
            run_id=run_id,
            source_approval_gate_id=source_gate.gate_id,
            github_issue=source_contract.github_issue,
            bound_digest=source_gate.bound_digest,
            inherited_at=datetime.now(timezone.utc).isoformat(),
        )


def _make_inherited_gate(
    run_id: str,
    step_id: str,
    bound_digest: str,
    expected_revision: int,
    created_at: str,
    decided_at: str,
) -> "Gate":
    """Build a requirements gate whose approval was inherited (FR-0801 AC-6).

    The gate is created directly in the ``inherited`` status with no human
    principal and no challenge, since no new human decision was made on the
    inheriting run. ``decided_at`` is set to the inheritance timestamp so the
    audit trail records when the source approval was carried over.

    Args:
        run_id: The bug_fix run inheriting the approval.
        step_id: The requirements approval step id.
        bound_digest: The source approval's bound digest, carried over.
        expected_revision: The bug_fix run's current revision.
        created_at: ISO 8601 timestamp of gate creation.
        decided_at: ISO 8601 timestamp of the inherited decision.

    Returns:
        A :class:`~louke.runtime.gates.Gate` with status ``inherited``.
    """
    from louke.runtime.gates import Gate

    return Gate(
        gate_id=f"gate_{uuid.uuid4().hex[:12]}",
        challenge_id=f"chal_inherited_{uuid.uuid4().hex[:8]}",
        run_id=run_id,
        step_id=step_id,
        expected_revision=expected_revision,
        bound_digest=bound_digest,
        status=GATE_INHERITED,
        actor_id=None,
        reason="inherited from source approval",
        decided_at=decided_at,
        created_at=created_at,
    )
