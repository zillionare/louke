"""FR-2200: M-PUBLISH operation ledger & idempotent execution.

After Human Release binds the current preview, Runtime establishes a
stable identity for each applicable external operation (merge/main,
canonical tag, registry/artifact publish, GitHub Release/notes, deploy
and smoke) and persists intent + result.  Agents do NOT execute or
simulate these side effects.  After restart, already-confirmed
operations are NOT repeated; unknown results enter ``needs_attention``.
Runtime may NOT create a different tag, re-upload or overwrite an
immutable artifact (AC-FR2200-01).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import Enum
from typing import Literal

ERROR_CODES = (
    "PUB_AUTHORIZATION_MISSING",
    "PUB_AUTHORIZATION_STALE",
    "PUB_PRECONDITION_FAILED",
    "PUB_CONTRACT_NOT_CURRENT",
    "PUB_OPERATION_CONFLICT",
    "PUB_DEPENDENCY_UNCONFIRMED",
    "PUB_PROVIDER_ZERO_UNSAFE",
    "PUB_PROVIDER_AMBIGUOUS",
    "PUB_RESOURCE_IDENTITY_MISMATCH",
    "PUB_ACK_UNKNOWN",
    "PUB_IMMUTABLE_CONFLICT",
    "PUB_CREDENTIAL_UNAVAILABLE",
    "PUB_RECONCILE_REQUIRED",
)

OperationKind = Literal[
    "merge-main",
    "tag",
    "wheel-upload",
    "sdist-upload",
    "github-release",
    "deploy",
    "smoke",
]


class OperationLedgerError(Exception):
    """A fail-closed operation ledger rejection carrying a stable code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


class OperationStatus(str, Enum):
    """Stable operation status values (AC-FR2200-01)."""

    PLANNED = "planned"
    EXECUTING = "executing"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    UNKNOWN = "unknown"
    NEEDS_ATTENTION = "needs_attention"
    FORWARD_FIX_REQUIRED = "forward_fix_required"


@dataclass(frozen=True)
class OperationAttempt:
    """A single attempt within an operation (AC-FR2200-01).

    Attributes:
        attempt_no: Monotonic attempt number.
        intent_digest: ``sha256:<hex>`` of the persisted intent bytes.
        query_digest: ``sha256:<hex>`` of the query response, or ``""``.
        query_cardinality: Number of provider-observed matches (0, 1, many).
        effect_digest: ``sha256:<hex>`` of the effect response, or ``""``.
        result_digest: ``sha256:<hex>`` of the result/response, or ``""``.
        response_digest: ``sha256:<hex>`` of the final provider response.
        observed_at: RFC 3339 timestamp.
    """

    attempt_no: int
    intent_digest: str
    query_digest: str = ""
    query_cardinality: int = 0
    effect_digest: str = ""
    result_digest: str = ""
    response_digest: str = ""
    observed_at: str = ""


@dataclass
class Operation:
    """A publish operation in the ledger (AC-FR2200-01).

    Attributes:
        operation_id: Stable operation identity.
        kind: ``merge-main|tag|wheel-upload|sdist-upload|github-release|deploy|smoke``.
        target: Canonical target (e.g. tag name, registry namespace).
        payload_digest: ``sha256:<hex>`` of the operation payload.
        status: :class:`OperationStatus`.
        attempts: Tuple of :class:`OperationAttempt`.
    """

    operation_id: str
    kind: OperationKind
    target: str
    payload_digest: str
    status: OperationStatus
    attempts: tuple[OperationAttempt, ...] = ()


def _operation_id(
    release_identity: str, kind: OperationKind, target: str, payload_digest: str
) -> str:
    payload = f"{release_identity}|{kind}|{target}|{payload_digest}"
    return "op:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]


class OperationLedger:
    """Append-only operation ledger (AC-FR2200-01)."""

    def __init__(self) -> None:
        self._operations: dict[str, Operation] = {}

    def _add_operation(self, op: Operation) -> None:
        existing = self._operations.get(op.operation_id)
        if existing is not None and existing.payload_digest != op.payload_digest:
            raise OperationLedgerError(
                "PUB_OPERATION_CONFLICT",
                f"operation {op.operation_id} already exists with different payload",
            )
        self._operations[op.operation_id] = op

    def plan_operation(
        self,
        *,
        release_identity: str,
        kind: OperationKind,
        target: str,
        payload_digest: str,
    ) -> Operation:
        """Plan a new operation; idempotent if the same identity already exists."""
        operation_id = _operation_id(release_identity, kind, target, payload_digest)
        existing = self._operations.get(operation_id)
        if existing is not None:
            return existing
        op = Operation(
            operation_id=operation_id,
            kind=kind,
            target=target,
            payload_digest=payload_digest,
            status=OperationStatus.PLANNED,
            attempts=(OperationAttempt(attempt_no=1, intent_digest=payload_digest),),
        )
        self._operations[operation_id] = op
        return op

    def get(self, operation_id: str) -> Operation:
        return self._operations[operation_id]

    def query(
        self,
        operation_id: str,
        *,
        query_digest: str,
        cardinality: int,
        existing_digest: str = "",
    ) -> None:
        """Record a query result for an operation.

        Raises:
            OperationLedgerError: ``PUB_PROVIDER_AMBIGUOUS`` if cardinality > 1,
                ``PUB_IMMUTABLE_CONFLICT`` if cardinality==1 with a different
                existing digest.
        """
        op = self._operations[operation_id]
        if cardinality > 1:
            op.status = OperationStatus.NEEDS_ATTENTION
            raise OperationLedgerError(
                "PUB_PROVIDER_AMBIGUOUS",
                f"query for {operation_id} returned {cardinality} matches",
            )
        if cardinality == 1:
            if existing_digest and existing_digest != op.payload_digest:
                op.status = OperationStatus.NEEDS_ATTENTION
                raise OperationLedgerError(
                    "PUB_IMMUTABLE_CONFLICT",
                    "existing resource has different digest; cannot overwrite",
                )
            # cardinality==1 with matching identity -> operation already exists,
            # confirm without a new effect.
            op.status = OperationStatus.CONFIRMED
            return
        # cardinality == 0 -> safe to effect (if contract allows).
        op.status = OperationStatus.EXECUTING

    def effect(self, operation_id: str, *, effect_digest: str) -> None:
        """Record an effect for an operation.

        Raises:
            OperationLedgerError: ``PUB_PROVIDER_AMBIGUOUS`` if the operation
                is not in EXECUTING state.
        """
        op = self._operations[operation_id]
        if op.status != OperationStatus.EXECUTING:
            raise OperationLedgerError(
                "PUB_PROVIDER_AMBIGUOUS",
                f"cannot effect {operation_id} in status {op.status.value}",
            )

    def confirm(
        self, operation_id: str, *, provider_ids: tuple[str, ...], response_digest: str
    ) -> None:
        """Mark an operation as confirmed."""
        op = self._operations[operation_id]
        op.status = OperationStatus.CONFIRMED

    def mark_unknown(self, operation_id: str, *, reason: str) -> None:
        """Mark an operation as unknown (e.g. ack loss)."""
        op = self._operations[operation_id]
        op.status = OperationStatus.UNKNOWN
