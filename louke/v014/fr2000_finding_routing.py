"""FR-2000: Security finding routing & policy skip.

Implementation vulnerabilities return to Devon; security test gaps return
to Shield; architecture boundary errors return to M-DESIGN; permission/
data consequence requirement gaps return via Human to M-SPEC/M-ACC.
Technical fixes are NOT punted to Human.  After fixes, affected
implementation/tests, full M-VERIFY and Judge are re-run.  Only current
policy-explicitly-allowed non-blocking findings may record residual risk;
critical/high or policy-forbidden items cannot be waived.  Legitimate
deep-audit skip must bind policy digest + scope; sensitive boundary
changes may NOT be silently skipped by ordinary rules (AC-FR2000-01).
"""

from __future__ import annotations

from dataclasses import dataclass

ERROR_CODES = (
    "SEC_FINDING_ROUTE_INVALID",
    "SEC_WAIVER_FORBIDDEN",
    "SEC_WAIVER_INVALID",
    "SEC_SKIP_FORBIDDEN",
    "SEC_SKIP_INVALID",
)

_ROUTE_TARGETS: dict[str, tuple[str, bool]] = {
    "implementation": ("Devon", False),
    "security_test": ("Shield", False),
    "design": ("M-DESIGN", False),
    "requirement": ("M-SPEC/M-ACC", True),
}

_NON_WAIVABLE_SEVERITIES: frozenset[str] = frozenset({"critical", "high"})

_SENSITIVE_BOUNDARY_PREFIXES: tuple[str, ...] = (
    "louke/auth/",
    "louke/credentials/",
    "louke/secrets/",
    "louke/billing/",
    "louke/permissions/",
)


class FindingRouteError(Exception):
    """A fail-closed finding routing rejection carrying a stable code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


@dataclass(frozen=True)
class SecurityFinding:
    """A single security finding (AC-FR2000-01).

    Attributes:
        finding_id: Stable finding id.
        candidate_id: Bound candidate id.
        location: File path + line/anchor.
        severity: ``critical|high|medium|low``.
        impact: Free-text impact description.
        required_fix: Free-text required fix.
        category: ``implementation|security_test|design|requirement``.
        route: Same as category; the route target.
    """

    finding_id: str
    candidate_id: str
    location: str
    severity: str
    impact: str
    required_fix: str
    category: str
    route: str


@dataclass(frozen=True)
class RouteDecision:
    """The routing decision for a finding (AC-FR2000-01).

    Attributes:
        target: ``Devon|Shield|M-DESIGN|M-SPEC/M-ACC``.
        requires_human: ``True`` only for requirement gaps.
        requires_full_rerun: ``True`` always (M-VERIFY + Judge must be re-run).
    """

    target: str
    requires_human: bool
    requires_full_rerun: bool = True


def route_finding(finding: SecurityFinding) -> RouteDecision:
    """Route a security finding to its owner (AC-FR2000-01).

    Args:
        finding: :class:`SecurityFinding` to route.

    Returns:
        A :class:`RouteDecision` with the target owner.

    Raises:
        FindingRouteError: With ``SEC_FINDING_ROUTE_INVALID`` if the route is
            not one of the four known categories.
    """
    if finding.route not in _ROUTE_TARGETS:
        raise FindingRouteError(
            "SEC_FINDING_ROUTE_INVALID",
            f"unknown route {finding.route!r}; must be one of {sorted(_ROUTE_TARGETS)}",
        )
    target, requires_human = _ROUTE_TARGETS[finding.route]
    return RouteDecision(target=target, requires_human=requires_human)


@dataclass(frozen=True)
class WaiverDecision:
    """A waiver request for a finding (AC-FR2000-01).

    Attributes:
        finding_id: Bound finding id.
        candidate_id: Bound candidate id.
        actor: Actor identity.
        reason: Free-text waiver reason.
        scope: Scope of the waiver.
        issue_id: Issue id backing the waiver.
        expires_at: Expiry of the waiver.
        policy_digest: ``sha256:<hex>`` of the policy bytes.
    """

    finding_id: str
    candidate_id: str
    actor: str
    reason: str
    scope: str
    issue_id: int
    expires_at: str
    policy_digest: str


@dataclass(frozen=True)
class WaiverEvaluation:
    """Result of :func:`evaluate_waiver` (AC-FR2000-01).

    Attributes:
        allowed: ``True`` if the waiver is allowed.
        reason_code: Stable reason code explaining a denial.
    """

    allowed: bool
    reason_code: str = ""


def evaluate_waiver(
    finding: SecurityFinding, *, waiver: WaiverDecision | None = None
) -> WaiverEvaluation:
    """Evaluate whether a finding may be waived (AC-FR2000-01).

    Args:
        finding: :class:`SecurityFinding`.
        waiver: Optional :class:`WaiverDecision` with policy-bound metadata.

    Returns:
        A :class:`WaiverEvaluation` with ``allowed=True`` only when:
        - severity is medium/low (not critical/high), AND
        - waiver metadata is fully populated with policy_digest+issue+owner+
          scope+expiry.
    """
    if finding.severity in _NON_WAIVABLE_SEVERITIES:
        return WaiverEvaluation(allowed=False, reason_code="SEC_WAIVER_FORBIDDEN")
    if waiver is None or not (
        waiver.policy_digest
        and waiver.issue_id
        and waiver.scope
        and waiver.expires_at
        and waiver.actor
    ):
        return WaiverEvaluation(allowed=False, reason_code="SEC_WAIVER_INVALID")
    return WaiverEvaluation(allowed=True)


@dataclass(frozen=True)
class PolicySkip:
    """A policy-declared scanner skip (AC-FR2000-01).

    Attributes:
        scanner: Scanner id being skipped.
        reason: Free-text skip reason.
        scope: Scope of the skip.
        issue_id: Issue id backing the skip.
        owner: Owner of the skip.
        expires_at: Expiry of the skip.
        policy_digest: ``sha256:<hex>`` of the policy bytes.
    """

    scanner: str
    reason: str
    scope: str
    issue_id: int
    owner: str
    expires_at: str
    policy_digest: str


def validate_skip(skip: PolicySkip, *, sensitive_boundary: bool) -> None:
    """Validate a policy skip (AC-FR2000-01).

    Args:
        skip: :class:`PolicySkip` to validate.
        sensitive_boundary: ``True`` if the skip affects a sensitive boundary
            (auth/credentials/secrets/billing/permissions).

    Raises:
        FindingRouteError: With ``SEC_SKIP_FORBIDDEN`` if the skip affects a
            sensitive boundary; ``SEC_SKIP_INVALID`` if any required metadata
            is missing.
    """
    if sensitive_boundary:
        raise FindingRouteError(
            "SEC_SKIP_FORBIDDEN",
            f"skip on scanner {skip.scanner!r} affects a sensitive boundary; "
            "ordinary rules cannot silently skip",
        )
    if not (
        skip.policy_digest
        and skip.issue_id
        and skip.owner
        and skip.scope
        and skip.expires_at
    ):
        raise FindingRouteError(
            "SEC_SKIP_INVALID",
            f"skip on scanner {skip.scanner!r} lacks required policy metadata",
        )
