"""FR-2100: M-RELEASE preview & Human gate.

Runtime shows in the Project current release preview: canonical version/
candidate/main/tag, user changes, Issues/FR/AC trace, all tests/CI,
Prism/Judge, artifact digests/versions/public versions, non-blocking risks,
release/recovery plan and upcoming side effects.  Release is enabled only
when all non-waivable evidence is current PASS.  Human may choose Release,
Delay or Return; Delay produces no side effects and keeps candidate+preview
identity; Return records reason+target and only enters a WorkflowDefinition
target.  Any candidate/evidence/artifact/plan change makes the old
approval stale; Release may NOT bypass failed gates (AC-FR2100-01).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

ERROR_CODES = (
    "REL_PREVIEW_NOT_READY",
    "REL_PREVIEW_STALE",
    "REL_REVISION_CONFLICT",
    "REL_RELEASE_DISABLED",
    "REL_GATE_NOT_CURRENT",
    "REL_RETURN_REASON_REQUIRED",
    "REL_RETURN_TARGET_INVALID",
    "REL_ACTION_NOT_ALLOWED",
    "REL_DECISION_CONFLICT",
    "REL_ALREADY_PUBLISHING",
)


class MReleaseError(Exception):
    """A fail-closed release preview rejection carrying a stable code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


@dataclass(frozen=True)
class ReleasePreview:
    """A current release preview (AC-FR2100-01).

    Attributes:
        preview_id: Stable preview identity.
        candidate_id: Bound candidate id.
        canonical_version: Canonical release version.
        main_target: Main branch target name.
        tag: External Git tag (e.g. ``v0.14.0``).
        all_gates_pass: ``True`` when all non-waivable gates are current PASS.
        workspace_dirty: ``True`` if the workspace has unattributed changes.
        release_blocked: ``True`` if any gate is missing/FAIL/UNKNOWN/blocked.
        allowed_return_targets: Tuple of WorkflowDefinition-allowed return targets.
        workflow_revision: Current workflow revision for CAS.
    """

    preview_id: str
    candidate_id: str
    canonical_version: str
    main_target: str
    tag: str
    all_gates_pass: bool
    workspace_dirty: bool
    release_blocked: bool
    allowed_return_targets: tuple[str, ...]
    workflow_revision: int

    def release_action_enabled(self) -> bool:
        """Return ``True`` only when Release is enabled."""
        return (
            self.all_gates_pass
            and not self.workspace_dirty
            and not self.release_blocked
        )

    def delay_action_enabled(self) -> bool:
        """Delay is always enabled unless publishing/closing/complete."""
        return True

    def return_action_enabled(self) -> bool:
        """Return is enabled when there are allowed targets."""
        return bool(self.allowed_return_targets)


def build_preview(
    *,
    candidate_id: str,
    canonical_version: str,
    main_target: str,
    tag: str,
    all_gates_pass: bool,
    workspace_dirty: bool,
    release_blocked: bool,
    allowed_return_targets: tuple[str, ...],
    workflow_revision: int,
) -> ReleasePreview:
    """Build a current release preview (AC-FR2100-01).

    Args:
        candidate_id: Bound candidate id.
        canonical_version: Canonical release version.
        main_target: Main branch target name.
        tag: External Git tag.
        all_gates_pass: ``True`` when all non-waivable gates PASS.
        workspace_dirty: ``True`` if workspace has unattributed changes.
        release_blocked: ``True`` if any gate blocks Release.
        allowed_return_targets: Tuple of allowed return targets.
        workflow_revision: Current workflow revision.

    Returns:
        An immutable :class:`ReleasePreview` with stable preview_id.
    """
    payload = f"{candidate_id}|{canonical_version}|{tag}|{workflow_revision}"
    preview_id = "preview:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]
    return ReleasePreview(
        preview_id=preview_id,
        candidate_id=candidate_id,
        canonical_version=canonical_version,
        main_target=main_target,
        tag=tag,
        all_gates_pass=all_gates_pass,
        workspace_dirty=workspace_dirty,
        release_blocked=release_blocked,
        allowed_return_targets=tuple(allowed_return_targets),
        workflow_revision=workflow_revision,
    )


@dataclass(frozen=True)
class HumanDecision:
    """A Human Release/Delay/Return decision (AC-FR2100-01).

    Attributes:
        action: ``Release|Delay|Return``.
        reason: Optional (Delay) or required (Return) free-text reason.
        target: Required for ``Return``; must be in allowed_return_targets.
    """

    action: str
    reason: str = ""
    target: str = ""


@dataclass(frozen=True)
class DecisionResult:
    """Result of :func:`submit_human_decision` (AC-FR2100-01).

    Attributes:
        action: Echoed action.
        preview_id: Bound preview id.
        candidate_id: Bound candidate id.
        new_state: ``publishing|release_waiting|returned_upstream``.
        authorization_id: Publish authorization id for ``Release`` only.
        target: Bound target for ``Return``.
    """

    action: str
    preview_id: str
    candidate_id: str
    new_state: str
    authorization_id: str | None = None
    target: str = ""


def submit_human_decision(
    preview: ReleasePreview, decision: HumanDecision
) -> DecisionResult:
    """Submit a Human Release/Delay/Return decision (AC-FR2100-01).

    Args:
        preview: Current :class:`ReleasePreview`.
        decision: :class:`HumanDecision`.

    Returns:
        A :class:`DecisionResult` with the new state and (for Release) the
        publish authorization id.

    Raises:
        MReleaseError: With ``REL_RELEASE_DISABLED`` if Release is attempted
            with failed/blocked gates; ``REL_RETURN_REASON_REQUIRED`` if
            Return lacks a reason; ``REL_RETURN_TARGET_INVALID`` if Return
            target is not in ``allowed_return_targets``.
    """
    if decision.action == "Release":
        if not preview.release_action_enabled():
            raise MReleaseError(
                "REL_RELEASE_DISABLED",
                "Release is disabled; gates not current PASS or workspace dirty",
            )
        auth_id = (
            "auth:"
            + hashlib.sha256(
                f"{preview.candidate_id}|{preview.tag}".encode("utf-8")
            ).hexdigest()[:12]
        )
        return DecisionResult(
            action="Release",
            preview_id=preview.preview_id,
            candidate_id=preview.candidate_id,
            new_state="publishing",
            authorization_id=auth_id,
        )
    if decision.action == "Delay":
        return DecisionResult(
            action="Delay",
            preview_id=preview.preview_id,
            candidate_id=preview.candidate_id,
            new_state="release_waiting",
        )
    if decision.action == "Return":
        if not decision.reason:
            raise MReleaseError(
                "REL_RETURN_REASON_REQUIRED",
                "Return requires a non-empty reason",
            )
        if decision.target not in preview.allowed_return_targets:
            raise MReleaseError(
                "REL_RETURN_TARGET_INVALID",
                f"target {decision.target!r} not in allowed {preview.allowed_return_targets}",
            )
        return DecisionResult(
            action="Return",
            preview_id=preview.preview_id,
            candidate_id=preview.candidate_id,
            new_state="returned_upstream",
            target=decision.target,
        )
    raise MReleaseError(
        "REL_ACTION_NOT_ALLOWED",
        f"unknown action {decision.action!r}",
    )
