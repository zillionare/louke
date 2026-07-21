"""FR-2300: Post-publish verification & recovery.

Runtime must confirm main/tag/release/artifacts point to the approved
candidate, and execute version + basic smoke from real install/deploy/
run outlets.  On failure, Runtime executes the current rollback/forward-
fix contract's automatic safe steps; credential/external-ownership/
irreversible-conflict issues request Human authorization; technical
fixes still return to the specialist Agent.  All facts must be verified
before the state leaves ``publishing``/``needs_attention``; ``completed``
is forbidden before verification (AC-FR2300-01).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ERROR_CODES = (
    "PUB_PRECONDITION_FAILED",
    "PUB_PROVIDER_AMBIGUOUS",
    "PUB_RESOURCE_IDENTITY_MISMATCH",
    "PUB_IMMUTABLE_CONFLICT",
    "PUB_CREDENTIAL_UNAVAILABLE",
    "PUB_RECONCILE_REQUIRED",
)


class PostPublishError(Exception):
    """A fail-closed post-publish rejection carrying a stable code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


@dataclass(frozen=True)
class PublishFact:
    """A single publish fact verification (AC-FR2300-01).

    Attributes:
        name: ``main|tag|release|artifacts``.
        target_oid: Expected target OID (candidate OID).
        actual_oid: Actual OID read back from the provider.
    """

    name: str
    target_oid: str
    actual_oid: str


@dataclass(frozen=True)
class OutletVerification:
    """A single install/runtime/smoke outlet verification (AC-FR2300-01).

    Attributes:
        name: ``install|runtime|smoke``.
        outlet: Outlet command (e.g. ``pip install louke==0.14.0``).
        value: Value read back from the outlet.
        passed: ``True`` if the outlet returned the expected value.
    """

    name: str
    outlet: str
    value: str
    passed: bool


RecoveryKind = Literal["rollback", "forward-fix", "human-authorization"]


@dataclass(frozen=True)
class RecoveryDecision:
    """A recovery decision for a post-publish failure (AC-FR2300-01).

    Attributes:
        kind: ``rollback|forward-fix|human-authorization``.
        target: Specialist Agent target for forward-fix (e.g. ``Devon``).
        reason: Free-text reason for audit.
    """

    kind: RecoveryKind
    target: str = ""
    reason: str = ""


@dataclass(frozen=True)
class PostPublishReport:
    """Result of :func:`verify_post_publish` (AC-FR2300-01).

    Attributes:
        candidate_oid: Bound candidate OID.
        status: ``pass`` or ``fail``.
        new_state: ``completed`` for pass, ``needs_attention`` for fail.
        recovery: :class:`RecoveryDecision` if status is ``fail``.
    """

    candidate_oid: str
    status: str
    new_state: str
    recovery: RecoveryDecision | None = None


def _recovery_for(issue_kind: str) -> RecoveryDecision:
    if issue_kind == "credential-conflict":
        return RecoveryDecision(
            kind="human-authorization",
            reason="credential or external-ownership conflict requires Human authorization",
        )
    if issue_kind == "irreversible-conflict":
        return RecoveryDecision(
            kind="human-authorization",
            reason="irreversible conflict requires Human authorization",
        )
    # Default: technical fix routes to specialist Agent.
    return RecoveryDecision(
        kind="forward-fix",
        target="Devon",
        reason="technical fix routes to specialist Agent",
    )


def verify_post_publish(
    candidate_oid: str,
    facts: list[PublishFact],
    outlets: list[OutletVerification],
    *,
    issue_kind: str = "technical",
) -> PostPublishReport:
    """Verify post-publish facts and outlets (AC-FR2300-01).

    Args:
        candidate_oid: Approved candidate OID.
        facts: List of :class:`PublishFact` for main/tag/release/artifacts.
        outlets: List of :class:`OutletVerification` for install/runtime/smoke.
        issue_kind: ``technical|credential-conflict|irreversible-conflict``;
            determines the recovery route on failure.

    Returns:
        A :class:`PostPublishReport` with ``status=pass`` and ``new_state=
        completed`` only when every fact matches and every outlet passed.
        Otherwise ``status=fail``, ``new_state=needs_attention`` and a
        :class:`RecoveryDecision` is attached.
    """
    failed = any(f.actual_oid != f.target_oid for f in facts)
    failed = failed or any(not o.passed for o in outlets)
    if not failed:
        return PostPublishReport(
            candidate_oid=candidate_oid,
            status="pass",
            new_state="completed",
        )
    recovery = _recovery_for(issue_kind)
    return PostPublishReport(
        candidate_oid=candidate_oid,
        status="fail",
        new_state="needs_attention",
        recovery=recovery,
    )
