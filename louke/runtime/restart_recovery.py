"""NFR-0300: Restart recovery & idempotency.

Runtime must recover from persisted manifest/refs/commits/reviews/evidence/
operation ledger after a restart at any stage; it must NOT repeat already-
confirmed side effects.  When evidence/ref/operation identity is missing or
conflicting, Runtime fail-closed/needs_attention and never fabricate PASS.
After repair, safe retry is allowed.  Tested by simulating process
termination after Red ref creation / Green commit / CI polling / tag-publish
/ milestone cleanup (AC-NFR0300-01).
"""

from __future__ import annotations

from dataclasses import dataclass

ERROR_CODES = (
    "RECOVERY_FAIL_CLOSED",
    "RECOVERY_UNKNOWN_INTENT",
    "RECOVERY_IDENTITY_MISSING",
)

_PHASE_AFTER: dict[str, str] = {
    "red-ref-created": "after-red-ref",
    "green-committed": "after-green",
    "ci-pushed": "after-ci-push",
    "publish-tag": "after-publish",
    "publish-complete": "after-publish",
}


@dataclass(frozen=True)
class OperationIntent:
    """A durable operation intent scanned during recovery (AC-NFR0300-01).

    Attributes:
        kind: Stable operation kind (e.g. ``publish-tag``).
        operation_id: Stable operation identity.
        status: ``confirmed|unknown|executing|planned``.
    """

    kind: str
    operation_id: str
    status: str


@dataclass(frozen=True)
class RecoveryDecision:
    """Result of :func:`recover_after_restart` (AC-NFR0300-01).

    Attributes:
        state: ``running|needs_attention``.
        resumed_phase: Phase Runtime resumes from (``after-red-ref|after-green|...``).
        confirmed_facts: Tuple of confirmed fact kinds (no re-execution).
        fail_closed: ``True`` if recovery could not safely proceed.
    """

    state: str
    resumed_phase: str
    confirmed_facts: tuple[str, ...] = ()
    fail_closed: bool = False


class RecoveryStore:
    """In-memory recovery store capturing confirmed/unknown facts (AC-NFR0300-01)."""

    def __init__(self) -> None:
        self._confirmed: dict[str, OperationIntent] = {}
        self._unknown: dict[str, OperationIntent] = {}

    def record_confirmed(self, kind: str, *, operation_id: str) -> None:
        self._confirmed[kind] = OperationIntent(
            kind=kind, operation_id=operation_id, status="confirmed"
        )

    def record_unknown(self, kind: str, *, operation_id: str) -> None:
        self._unknown[kind] = OperationIntent(
            kind=kind, operation_id=operation_id, status="unknown"
        )

    def resolve_unknown(self, kind: str) -> None:
        if kind in self._unknown:
            intent = self._unknown.pop(kind)
            self._confirmed[kind] = OperationIntent(
                kind=intent.kind,
                operation_id=intent.operation_id,
                status="confirmed",
            )

    def pending_intents(self) -> list[OperationIntent]:
        return list(self._unknown.values()) + list(self._confirmed.values())

    @property
    def confirmed(self) -> dict[str, OperationIntent]:
        return dict(self._confirmed)

    @property
    def unknown(self) -> dict[str, OperationIntent]:
        return dict(self._unknown)


def fail_closed_unknown(*, reason: str) -> RecoveryDecision:
    """Return a fail-closed recovery decision for an unknown state (AC-NFR0300-01)."""
    return RecoveryDecision(
        state="needs_attention",
        resumed_phase="",
        confirmed_facts=(),
        fail_closed=True,
    )


def recover_after_restart(store: RecoveryStore) -> RecoveryDecision:
    """Recover Runtime state after a restart (AC-NFR0300-01).

    Args:
        store: :class:`RecoveryStore` capturing confirmed + unknown facts.

    Returns:
        A :class:`RecoveryDecision`:
        - If any unknown intent has empty operation_id -> fail closed.
        - If any unknown intent exists with valid operation_id -> needs_attention.
        - Otherwise running, with confirmed_facts and resumed_phase derived
          from the latest confirmed fact.
    """
    # Fail closed for any unknown intent with missing identity.
    for kind, intent in store.unknown.items():
        if not intent.operation_id:
            return fail_closed_unknown(
                reason=f"unknown intent {kind!r} missing operation_id"
            )
    if store.unknown:
        return RecoveryDecision(
            state="needs_attention",
            resumed_phase="",
            confirmed_facts=tuple(store.confirmed.keys()),
            fail_closed=True,
        )
    # No unknowns: derive resumed phase from latest confirmed fact.
    confirmed_kinds = tuple(store.confirmed.keys())
    resumed = ""
    for kind in reversed(confirmed_kinds):
        if kind in _PHASE_AFTER:
            resumed = _PHASE_AFTER[kind]
            break
    return RecoveryDecision(
        state="running",
        resumed_phase=resumed,
        confirmed_facts=confirmed_kinds,
        fail_closed=False,
    )
