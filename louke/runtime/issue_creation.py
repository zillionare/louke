"""FR-1800: M-LOCK-1 后的 GitHub Issue 创建与 Project 关联.

Implements the deterministic contract slice of FR-1800:

* :func:`is_gate_approved_for_issue_creation` enforces the M-LOCK-1 gate
  before any Issue creation. When the gate is not approved, the request is
  rejected with :data:`GATE_NOT_APPROVED` and the Issue search/Project item
  counts do not increase (AC-FR1800-01).

* :func:`compute_issue_targets` enumerates the Valid (non-❌) requirements
  from the locked Spec. For the current spec (21 FR + 3 NFR all ✅) the
  target count is 24 (AC-FR1800-02).

* :func:`format_issue_title` and :func:`parse_first_requirement_token`
  enforce the exact single ``[{ID}]`` token at the start of the title
  (AC-FR1800-02, AC-FR1800-05).

* :class:`IssueBodyIdentity` captures the body identity (requirement id +
  locked Spec section URL + Acceptance section URL) used for reconcile
  (AC-FR1800-02, AC-FR1800-03).

* :class:`IssueReconciler.reconcile` and :func:`reconcile_existing_issue`
  implement the reconcile contract: exact identity match -> ``REUSED``;
  no candidate -> ``CREATED``; imprecise title token / mismatched body /
  link / Project -> ``CONFLICT`` with the mismatched fields listed and no
  second candidate created (AC-FR1800-03, AC-FR1800-05). Partial failures
  preserve successful Issue numbers and only retry failed items
  (AC-FR1800-04).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional


GATE_NOT_APPROVED = "GATE_NOT_APPROVED"


@dataclass(frozen=True)
class IssueTarget:
    """A single requirement target for Issue creation.

    Attributes:
        requirement_id: The exact requirement ID (e.g. ``FR-0100``).
        valid: The Valid field from the locked Spec (``✅`` or ``❌``);
            targets are only emitted for non-❌ requirements.
    """

    requirement_id: str
    valid: str


def compute_issue_targets(
    locked_requirements: list[dict[str, str]],
) -> tuple[IssueTarget, ...]:
    """Enumerate the Issue creation targets from the locked Spec.

    Args:
        locked_requirements: List of ``{"id": ..., "valid": ...}`` dicts
            parsed from the locked Spec.

    Returns:
        A tuple of :class:`IssueTarget` for every requirement whose
        ``valid`` field is not ``❌``. The order matches the input order.
    """
    return tuple(
        IssueTarget(requirement_id=r["id"], valid=r["valid"])
        for r in locked_requirements
        if r.get("valid") != "❌"
    )


def compute_project_item_count(
    *,
    targets: tuple[IssueTarget, ...],
    per_target_item_count: int,
) -> int:
    """Return the total Project item count for ``targets``.

    Args:
        targets: The :class:`IssueTarget` tuple.
        per_target_item_count: Project items per target (always 1 in this
            spec).

    Returns:
        ``len(targets) * per_target_item_count``.
    """
    return len(targets) * per_target_item_count


_TITLE_TOKEN_RE = re.compile(r"^\[(FR-\d{4}|NFR-\d{4})\]")


def format_issue_title(requirement_id: str, summary: str) -> str:
    """Format an Issue title with the exact single ``[{ID}]`` token prefix.

    Args:
        requirement_id: The exact requirement ID.
        summary: Human-readable summary appended after the token.

    Returns:
        ``f"[{requirement_id}] {summary}"``.
    """
    return f"[{requirement_id}] {summary}"


def parse_first_requirement_token(title: str) -> Optional[str]:
    """Return the first ``[{ID}]`` token in ``title`` or ``None``.

    Args:
        title: The Issue title to parse.

    Returns:
        The requirement ID (e.g. ``FR-0100``) when the title starts with
        ``[{ID}]``; ``None`` otherwise.
    """
    m = _TITLE_TOKEN_RE.match(title)
    return m.group(1) if m else None


@dataclass(frozen=True)
class IssueBodyIdentity:
    """Identity of an Issue body for reconcile.

    Attributes:
        requirement_id: The exact requirement ID the body must contain.
        spec_section_url: URL of the locked Spec section for the requirement.
        acceptance_section_url: URL of the Acceptance section for the
            requirement.
    """

    requirement_id: str
    spec_section_url: str
    acceptance_section_url: str


@dataclass(frozen=True)
class IssueIdentity:
    """Stable identity of an Issue/Project item for reconcile.

    Attributes:
        repository_node_id: Repository node ID.
        spec_id: Canonical spec identifier.
        requirement_id: Exact requirement ID.
        joint_digest: ``sha256:<hex>`` joint digest of the locked three-doc
            set.
        body: :class:`IssueBodyIdentity` the Issue must match.
        project_node_id: Foundation release GitHub Project node ID.
        observed_title: When reconciling an existing Issue, the observed
            title text; ``None`` when the identity is purely expected.
    """

    repository_node_id: str
    spec_id: str
    requirement_id: str
    joint_digest: str
    body: IssueBodyIdentity
    project_node_id: str
    observed_title: Optional[str] = None


class IssueOperationStatus(str, Enum):
    """Status of an Issue operation.

    Members:
        PENDING: Operation has not yet been processed.
        CREATED: Issue and Project item were created.
        LINKED: Existing Issue was linked to a new Project item.
        REUSED: Existing Issue and Project item were reused as-is.
        FAILED: Operation failed (provider error); Issue number preserved
            when already created.
        UNCERTAIN: Operation result is unknown (ack loss); reconcile later.
        CONFLICT: Existing candidate does not match; no second candidate
            created.
    """

    PENDING = "pending"
    CREATED = "created"
    LINKED = "linked"
    REUSED = "reused"
    FAILED = "failed"
    UNCERTAIN = "uncertain"
    CONFLICT = "conflict"


@dataclass(frozen=True)
class IssueOperation:
    """A single Issue creation/reconcile operation.

    Attributes:
        operation_id: Stable opaque operation identifier.
        target: The :class:`IssueTarget` for this operation.
        expected_identity: The :class:`IssueIdentity` the operation expects
            to create or reuse.
        status: Current :class:`IssueOperationStatus`.
        issue_number: Issue number once created/reused; ``None`` otherwise.
        provider_error: Non-secret provider error message when ``FAILED``.
    """

    operation_id: str
    target: IssueTarget
    expected_identity: IssueIdentity
    status: IssueOperationStatus = IssueOperationStatus.PENDING
    issue_number: Optional[int] = None
    provider_error: Optional[str] = None


@dataclass(frozen=True)
class IssueReconcileResult:
    """Result of :meth:`IssueReconciler.reconcile` or
    :func:`reconcile_existing_issue`.

    Attributes:
        operation_id: The operation id.
        status: Final :class:`IssueOperationStatus`.
        actual_identity: The actual :class:`IssueIdentity` when reused or
            created; ``None`` when conflict.
        created_issue: ``True`` when a new Issue was created; ``False``
            otherwise.
        created_project_item: ``True`` when a new Project item was created;
            ``False`` otherwise.
        issue_number: Issue number when known; ``None`` otherwise.
        provider_error: Non-secret provider error when ``FAILED``.
        conflict_fields: Non-empty list of mismatched fields when
            ``CONFLICT``; empty otherwise.
    """

    operation_id: str
    status: IssueOperationStatus
    actual_identity: Optional[IssueIdentity]
    created_issue: bool
    created_project_item: bool
    issue_number: Optional[int] = None
    provider_error: Optional[str] = None
    conflict_fields: tuple[str, ...] = ()


@dataclass(frozen=True)
class GateDecision:
    """Decision returned by :func:`is_gate_approved_for_issue_creation`.

    Attributes:
        allowed: ``True`` when Issue creation may proceed.
        code: ``GATE_NOT_APPROVED`` when ``not allowed``; ``None`` otherwise.
        issue_search_count_delta: Always ``0`` when ``not allowed``.
        project_item_count_delta: Always ``0`` when ``not allowed``.
    """

    allowed: bool
    code: Optional[str]
    issue_search_count_delta: int
    project_item_count_delta: int


def is_gate_approved_for_issue_creation(
    *,
    m_lock_1_approved: bool,
) -> GateDecision:
    """Decide whether Issue creation may proceed.

    Args:
        m_lock_1_approved: Whether M-LOCK-1 has been approved.

    Returns:
        A :class:`GateDecision`. When ``m_lock_1_approved is False``,
        ``allowed is False`` with code :data:`GATE_NOT_APPROVED` and zero
        count deltas (AC-FR1800-01).
    """
    if not m_lock_1_approved:
        return GateDecision(
            allowed=False,
            code=GATE_NOT_APPROVED,
            issue_search_count_delta=0,
            project_item_count_delta=0,
        )
    return GateDecision(
        allowed=True,
        code=None,
        issue_search_count_delta=0,
        project_item_count_delta=0,
    )


class IssueReconciler:
    """Stateless helper that decides Issue operation outcomes."""

    def reconcile(
        self,
        operation: IssueOperation,
        *,
        existing: Optional[IssueIdentity],
    ) -> IssueReconcileResult:
        """Reconcile ``operation`` against an optional ``existing`` Issue.

        Args:
            operation: The :class:`IssueOperation` to reconcile.
            existing: The existing :class:`IssueIdentity` found by query, or
                ``None`` when no candidate exists.

        Returns:
            An :class:`IssueReconcileResult`. ``REUSED`` when ``existing``
            exactly matches ``operation.expected_identity``; ``CREATED``
            when ``existing is None``; ``CONFLICT`` with mismatched fields
            when ``existing`` is present but does not match.
        """
        if existing is None:
            return IssueReconcileResult(
                operation_id=operation.operation_id,
                status=IssueOperationStatus.CREATED,
                actual_identity=operation.expected_identity,
                created_issue=True,
                created_project_item=True,
                issue_number=operation.issue_number,
            )
        return reconcile_existing_issue(operation, existing=existing)

    def mark_link_failure(
        self,
        operation: IssueOperation,
        *,
        provider_error: str,
    ) -> IssueReconcileResult:
        """Mark a link failure on ``operation``; preserve any Issue number.

        Args:
            operation: The operation that failed at the link step.
            provider_error: Non-secret provider error message.

        Returns:
            An :class:`IssueReconcileResult` with status ``FAILED``, the
            Issue number preserved when already created, ``created_issue is
            False`` (retry only the link, not the Issue) and the provider
            error message recorded (AC-FR1800-04).
        """
        return IssueReconcileResult(
            operation_id=operation.operation_id,
            status=IssueOperationStatus.FAILED,
            actual_identity=operation.expected_identity,
            created_issue=False,
            created_project_item=False,
            issue_number=operation.issue_number,
            provider_error=provider_error,
        )


def _conflict_fields(expected: IssueIdentity, existing: IssueIdentity) -> list[str]:
    """Return the list of mismatched fields between ``expected`` and
    ``existing``."""
    fields: list[str] = []
    if existing.repository_node_id != expected.repository_node_id:
        fields.append("repository_node_id")
    if existing.spec_id != expected.spec_id:
        fields.append("spec_id")
    if existing.requirement_id != expected.requirement_id:
        fields.append("requirement_id")
    if existing.joint_digest != expected.joint_digest:
        fields.append("joint_digest")
    if existing.project_node_id != expected.project_node_id:
        fields.append("project_node_id")
    if existing.body.requirement_id != expected.body.requirement_id:
        fields.append("body.requirement_id")
    if existing.body.spec_section_url != expected.body.spec_section_url:
        fields.append("body.spec_section_url")
    if existing.body.acceptance_section_url != expected.body.acceptance_section_url:
        fields.append("body.acceptance_section_url")
    # Title token check.
    if existing.observed_title is not None:
        token = parse_first_requirement_token(existing.observed_title)
        if token != expected.requirement_id:
            fields.append("title")
        elif existing.observed_title.count(f"[{expected.requirement_id}]") > 1:
            fields.append("title")
    return fields


def reconcile_existing_issue(
    operation: IssueOperation,
    *,
    existing: IssueIdentity,
) -> IssueReconcileResult:
    """Reconcile ``operation`` against an existing Issue identity.

    Args:
        operation: The :class:`IssueOperation` to reconcile.
        existing: The existing :class:`IssueIdentity` found by query.

    Returns:
        An :class:`IssueReconcileResult`. ``REUSED`` when ``existing``
        exactly matches ``operation.expected_identity`` (including the
        title token check); ``CONFLICT`` with the mismatched fields
        listed and no second candidate created otherwise (AC-FR1800-03,
        AC-FR1800-05).
    """
    conflicts = _conflict_fields(operation.expected_identity, existing)
    if conflicts:
        return IssueReconcileResult(
            operation_id=operation.operation_id,
            status=IssueOperationStatus.CONFLICT,
            actual_identity=None,
            created_issue=False,
            created_project_item=False,
            issue_number=None,
            conflict_fields=tuple(conflicts),
        )
    return IssueReconcileResult(
        operation_id=operation.operation_id,
        status=IssueOperationStatus.REUSED,
        actual_identity=existing,
        created_issue=False,
        created_project_item=False,
        issue_number=operation.issue_number,
    )
