"""FR-2600: Return upstream & stale propagation.

Agents may only return gap advisories that carry evidence + artifact
anchors; Runtime validates the target per WorkflowDefinition.  Technical
gaps confirmed by Archer+Prism return to M-DESIGN (no Human); product/
Acceptance gaps require Human approval to return to M-SPEC/M-ACC and
re-do M-REQ-APPROVAL.  After return, downstream graph/baseline/RGR/
commits/reviews/candidate/CI/artifact/security/release approval are
marked stale/superseded; history and unarchived Red refs are preserved.
Client/Agent-supplied arbitrary stage names are rejected (AC-FR2600-01).
"""

from __future__ import annotations

from dataclasses import dataclass

ERROR_CODES = (
    "RETURN_TARGET_INVALID",
    "RETURN_ADVISORY_INCOMPLETE",
    "RETURN_TECHNICAL_NOT_CONFIRMED",
    "RETURN_PRODUCT_REQUIRES_HUMAN",
)

_STALE_FIELDS: tuple[str, ...] = (
    "graph",
    "baseline",
    "rgr",
    "commits",
    "reviews",
    "candidate",
    "ci",
    "artifact",
    "security",
    "release-approval",
)


class ReturnUpstreamError(Exception):
    """A fail-closed return-upstream rejection carrying a stable code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


@dataclass(frozen=True)
class GapAdvisory:
    """A gap advisory returned by an Agent (AC-FR2600-01).

    Attributes:
        kind: ``design|product``.
        target: ``M-DESIGN|M-SPEC/M-ACC``.
        evidence: Tuple of evidence ids supporting the advisory.
        anchors: Tuple of artifact anchors (file/path/anchor).
        actor: Actor identity returning the advisory.
    """

    kind: str
    target: str
    evidence: tuple[str, ...]
    anchors: tuple[str, ...]
    actor: str


@dataclass(frozen=True)
class ReturnTarget:
    """The decision result for a return-upstream request (AC-FR2600-01).

    Attributes:
        allowed: ``True`` if the return is allowed.
        requires_human: ``True`` for product gaps.
        stale_set: Tuple of downstream fields marked stale/superseded.
        preserves_history: ``True`` always; history is never deleted.
        preserves_unarchived_red_refs: ``True`` always; unarchived Red refs preserved.
    """

    allowed: bool
    requires_human: bool
    stale_set: tuple[str, ...] = ()
    preserves_history: bool = True
    preserves_unarchived_red_refs: bool = True


def validate_return_target(
    advisory: GapAdvisory,
    *,
    workflow_definition_targets: tuple[str, ...],
    archer_confirmed: bool = False,
    prism_confirmed: bool = False,
    human_approved: bool = False,
) -> ReturnTarget:
    """Validate a return-upstream target per WorkflowDefinition (AC-FR2600-01).

    Args:
        advisory: :class:`GapAdvisory` to validate.
        workflow_definition_targets: Tuple of allowed return targets from the
            current WorkflowDefinition.
        archer_confirmed: ``True`` if Archer confirmed the technical gap.
        prism_confirmed: ``True`` if Prism confirmed the technical gap.
        human_approved: ``True`` if Human approved the product gap return.

    Returns:
        A :class:`ReturnTarget` with ``allowed=True`` and the stale set if the
        return is valid.

    Raises:
        ReturnUpstreamError: With ``RETURN_ADVISORY_INCOMPLETE`` if the advisory
            lacks evidence/anchors; ``RETURN_TARGET_INVALID`` if target is not
            in WorkflowDefinition; ``RETURN_TECHNICAL_NOT_CONFIRMED`` for
            unconfirmed technical gaps; ``RETURN_PRODUCT_REQUIRES_HUMAN`` for
            product gaps without Human approval.
    """
    if not advisory.evidence or not advisory.anchors:
        raise ReturnUpstreamError(
            "RETURN_ADVISORY_INCOMPLETE",
            "advisory must carry evidence and artifact anchors",
        )
    if advisory.target not in workflow_definition_targets:
        raise ReturnUpstreamError(
            "RETURN_TARGET_INVALID",
            f"target {advisory.target!r} not in WorkflowDefinition {workflow_definition_targets}",
        )
    if advisory.kind == "design":
        if not (archer_confirmed and prism_confirmed):
            raise ReturnUpstreamError(
                "RETURN_TECHNICAL_NOT_CONFIRMED",
                "technical gap requires Archer+Prism confirmation",
            )
        return ReturnTarget(
            allowed=True,
            requires_human=False,
            stale_set=_STALE_FIELDS,
        )
    if advisory.kind == "product":
        if not human_approved:
            raise ReturnUpstreamError(
                "RETURN_PRODUCT_REQUIRES_HUMAN",
                "product gap requires Human approval to return to M-SPEC/M-ACC",
            )
        return ReturnTarget(
            allowed=True,
            requires_human=True,
            stale_set=_STALE_FIELDS,
        )
    raise ReturnUpstreamError(
        "RETURN_TARGET_INVALID",
        f"unknown advisory kind {advisory.kind!r}",
    )
