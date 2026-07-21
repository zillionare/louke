"""FR-2500: Bug fix / hotfix variant.

``bug_fix`` applies only to implementation deviation of an already-released
product against the existing approved Spec/AC; new behaviour must go through
backlog/new feature.  Runtime verifies source contract/Issue/version/
reproduction, picks ``quick_rgr`` or ``design_required`` by impact, and
executes in isolated ``fix/{issue-number}`` branch + worktree.  Both
variants reuse RGR, M-TEST, full historical M-VERIFY, required CI,
independent review, release/publish/milestone.  After release, main and
affected active releases are synced per policy.  Parallel active
releases must NOT cross-write; sync conflicts enter ``needs_attention``
(AC-FR2500-01).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

ERROR_CODES = (
    "BUGFIX_NEW_BEHAVIOUR",
    "BUGFIX_SOURCE_CONTRACT_MISSING",
    "BUGFIX_REPRODUCTION_MISSING",
    "BUGFIX_SYNC_CONFLICT",
)

_REQUIRED_PHASES: tuple[str, ...] = (
    "red",
    "green",
    "refactor",
    "m-test",
    "m-verify",
    "required-ci",
    "independent-review",
    "release",
    "publish",
    "milestone",
)


class BugFixVariantError(Exception):
    """A fail-closed bug fix variant rejection carrying a stable code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


class HotfixVariant(str, Enum):
    """Stable hotfix variant values (AC-FR2500-01)."""

    QUICK_RGR = "quick_rgr"
    DESIGN_REQUIRED = "design_required"


@dataclass(frozen=True)
class HotfixDecision:
    """A bug_fix classification decision (AC-FR2500-01).

    Attributes:
        variant: ``quick_rgr|design_required``.
    """

    variant: HotfixVariant


def classify_hotfix(
    *,
    deviation_kind: str,
    source_contract: str,
    issue_id: int,
    source_version: str,
    reproduction_digest: str,
) -> HotfixDecision:
    """Classify a bug_fix deviation (AC-FR2500-01).

    Args:
        deviation_kind: ``implementation-deviation`` (valid) or
            ``new-behaviour`` (rejected; must go through backlog).
        source_contract: ``sha256:<hex>`` of the source approved Spec/AC.
        issue_id: GitHub Issue id for the bug.
        source_version: Released version containing the bug.
        reproduction_digest: ``sha256:<hex>`` of the reproduction case bytes.

    Returns:
        A :class:`HotfixDecision` with the chosen variant.

    Raises:
        BugFixVariantError: With ``BUGFIX_NEW_BEHAVIOUR`` if the deviation is
            new behaviour; ``BUGFIX_REPRODUCTION_MISSING`` if reproduction is
            missing; ``BUGFIX_SOURCE_CONTRACT_MISSING`` if source contract is
            missing.
    """
    if deviation_kind == "new-behaviour":
        raise BugFixVariantError(
            "BUGFIX_NEW_BEHAVIOUR",
            "new behaviour must go through backlog/new feature, not hotfix",
        )
    if not source_contract:
        raise BugFixVariantError(
            "BUGFIX_SOURCE_CONTRACT_MISSING",
            "source contract digest is required for hotfix",
        )
    if not reproduction_digest:
        raise BugFixVariantError(
            "BUGFIX_REPRODUCTION_MISSING",
            "reproduction digest is required for hotfix",
        )
    return HotfixDecision(variant=HotfixVariant.QUICK_RGR)


@dataclass(frozen=True)
class HotfixPlan:
    """A hotfix execution plan (AC-FR2500-01).

    Attributes:
        variant: ``quick_rgr|design_required``.
        branch: ``fix/{issue-number}``.
        worktree_namespace: Isolated worktree namespace.
        required_phases: Tuple of phases reused from the main workflow.
        sync_targets: Tuple of release targets to sync after release.
        sync_conflict: ``True`` if parallel active releases cross-write.
    """

    variant: HotfixVariant
    branch: str
    worktree_namespace: str
    required_phases: tuple[str, ...]
    sync_targets: tuple[str, ...]
    sync_conflict: bool


def plan_hotfix(
    *,
    deviation_kind: str,
    source_contract: str,
    issue_id: int,
    source_version: str,
    reproduction_digest: str,
    impact: str,
    active_releases: tuple[str, ...] = (),
) -> HotfixPlan:
    """Plan a hotfix in an isolated branch + worktree (AC-FR2500-01).

    Args:
        deviation_kind: ``implementation-deviation`` (valid) or
            ``new-behaviour`` (rejected).
        source_contract: ``sha256:<hex>`` of the source approved Spec/AC.
        issue_id: GitHub Issue id for the bug.
        source_version: Released version containing the bug.
        reproduction_digest: ``sha256:<hex>`` of the reproduction case bytes.
        impact: ``low|medium|high|design``.
        active_releases: Tuple of active release branch names to sync after release.

    Returns:
        A :class:`HotfixPlan` with the chosen variant, isolated branch,
        worktree namespace, required phases and sync targets.

    Raises:
        BugFixVariantError: With a stable code from :data:`ERROR_CODES` for any
            invalid input.
    """
    decision = classify_hotfix(
        deviation_kind=deviation_kind,
        source_contract=source_contract,
        issue_id=issue_id,
        source_version=source_version,
        reproduction_digest=reproduction_digest,
    )
    variant = decision.variant
    if impact == "design":
        variant = HotfixVariant.DESIGN_REQUIRED
    sync_targets: list[str] = ["main"] + list(active_releases)
    sync_conflict = len(set(active_releases)) != len(active_releases)
    return HotfixPlan(
        variant=variant,
        branch=f"fix/{issue_id}",
        worktree_namespace=f"fix-{issue_id}-{source_version}",
        required_phases=_REQUIRED_PHASES,
        sync_targets=tuple(sync_targets),
        sync_conflict=sync_conflict,
    )
