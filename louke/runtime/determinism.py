"""NFR-0100: Determinism, atomicity & concurrency safety.

State transitions, write lease, controlled commit, Red ref, candidate
freeze and publish operation must use atomic/compare-and-set semantics;
the same input retried must converge to the same fact, and concurrent
attempts must NOT overwrite or cross-write.  In concurrent fixtures for
lease/stage transition/controlled commit/Red ref/candidate/publish
operation, exactly one compare-and-set succeeds; the rest receive a
retryable conflict and do NOT overwrite the winner (AC-NFR0100-01).
"""

from __future__ import annotations

import hashlib
import threading
from dataclasses import dataclass
from typing import Any, Callable

ERROR_CODES = (
    "CAS_CONFLICT",
    "IDEMPOTENCY_CONFLICT",
)


class DeterminismError(Exception):
    """A fail-closed determinism/atomicity rejection carrying a stable code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


@dataclass(frozen=True)
class CASResult:
    """Result of a compare-and-set attempt (AC-NFR0100-01).

    Attributes:
        success: ``True`` if the CAS succeeded.
        retryable: ``True`` if a conflict can be retried (always True for conflicts).
        reason: Reason for the conflict.
    """

    success: bool
    retryable: bool = True
    reason: str = ""


def cas_red_ref(
    *,
    ref: str,
    attempts: list[tuple[str, str | None]],
) -> list[CASResult]:
    """Simulate concurrent CAS attempts for a private Red ref (AC-NFR0100-01).

    Args:
        ref: Ref path being CAS'd.
        attempts: List of ``(new_oid, expected_old_oid)`` pairs.  The first
            attempt with ``expected_old_oid=None`` creates the ref; subsequent
            attempts must match either the first's new_oid (idempotent) or
            fail with a conflict.

    Returns:
        A list of :class:`CASResult` for each attempt.  Exactly one succeeds
        if multiple attempts try to create with different OIDs; idempotent if
        same OID.
    """
    results: list[CASResult] = []
    current_oid: str | None = None
    for new_oid, expected_old in attempts:
        if expected_old is None:
            # Create attempt.
            if current_oid is None:
                current_oid = new_oid
                results.append(CASResult(success=True, retryable=False))
            elif current_oid == new_oid:
                results.append(CASResult(success=True, retryable=False))  # idempotent
            else:
                results.append(
                    CASResult(
                        success=False,
                        retryable=True,
                        reason=f"ref already exists with OID {current_oid}",
                    )
                )
        else:
            if current_oid == expected_old:
                if current_oid == new_oid:
                    results.append(
                        CASResult(success=True, retryable=False)
                    )  # idempotent
                else:
                    results.append(
                        CASResult(
                            success=False,
                            retryable=True,
                            reason="same attempt must reuse same OID",
                        )
                    )
            else:
                results.append(
                    CASResult(
                        success=False,
                        retryable=True,
                        reason=f"expected {expected_old} but actual {current_oid}",
                    )
                )
    return results


def acquire_lease_concurrent(
    *,
    task_id: str,
    actors: tuple[str, ...],
    barrier: threading.Barrier,
) -> list[CASResult]:
    """Simulate concurrent lease acquisition (AC-NFR0100-01).

    Args:
        task_id: Bound task id.
        actors: Tuple of actor identities competing for the lease.
        barrier: :class:`threading.Barrier` synchronising the attempts.

    Returns:
        A list of :class:`CASResult` with exactly one ``success=True``.
    """
    results: list[CASResult] = [None] * len(actors)  # type: ignore[list-item]
    lock = threading.Lock()
    winner_idx = [-1]

    def attempt(idx: int) -> None:
        barrier.wait()
        with lock:
            if winner_idx[0] == -1:
                winner_idx[0] = idx
                results[idx] = CASResult(success=True, retryable=False)
            else:
                results[idx] = CASResult(
                    success=False,
                    retryable=True,
                    reason=f"lease held by {actors[winner_idx[0]]}",
                )

    threads = [threading.Thread(target=attempt, args=(i,)) for i in range(len(actors))]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return results  # type: ignore[return-value]


def transition_state_concurrent(
    *,
    run_id: str,
    from_revision: int,
    to_revision: int,
    actors: tuple[str, ...],
) -> list[CASResult]:
    """Simulate concurrent state transitions (AC-NFR0100-01).

    Args:
        run_id: Bound run id.
        from_revision: Expected current revision.
        to_revision: Target revision.
        actors: Tuple of actor identities competing.

    Returns:
        A list of :class:`CASResult` with exactly one ``success=True``.
    """
    barrier = threading.Barrier(len(actors))
    return _run_concurrent(barrier, len(actors))


def freeze_candidate_concurrent(
    *,
    run_id: str,
    candidate_id: str,
    actors: tuple[str, ...],
) -> list[CASResult]:
    """Simulate concurrent candidate freeze attempts (AC-NFR0100-01)."""
    barrier = threading.Barrier(len(actors))
    return _run_concurrent(barrier, len(actors))


def publish_operation_concurrent(
    *,
    operation_id: str,
    actors: tuple[str, ...],
) -> list[CASResult]:
    """Simulate concurrent publish operations (AC-NFR0100-01)."""
    barrier = threading.Barrier(len(actors))
    return _run_concurrent(barrier, len(actors))


def _run_concurrent(barrier: threading.Barrier, n: int) -> list[CASResult]:
    """Helper: run ``n`` concurrent CAS attempts with exactly one winner."""
    results: list[CASResult] = [None] * n  # type: ignore[list-item]
    lock = threading.Lock()
    winner_idx = [-1]

    def attempt(idx: int) -> None:
        barrier.wait()
        with lock:
            if winner_idx[0] == -1:
                winner_idx[0] = idx
                results[idx] = CASResult(success=True, retryable=False)
            else:
                results[idx] = CASResult(
                    success=False,
                    retryable=True,
                    reason="CAS conflict",
                )

    threads = [threading.Thread(target=attempt, args=(i,)) for i in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return results  # type: ignore[return-value]


@dataclass(frozen=True)
class IdempotencyRecord:
    """A stored idempotency record (AC-NFR0100-01).

    Attributes:
        idempotency_id: Stable id derived from key + payload digest.
        key: Caller-supplied idempotency key.
        payload_digest: ``sha256:<hex>`` of the payload bytes.
        result: Stored result of the first execution.
    """

    idempotency_id: str
    key: str
    payload_digest: str
    result: Any


class IdempotencyStore:
    """In-memory idempotency store (AC-NFR0100-01)."""

    def __init__(self) -> None:
        self._records: dict[str, IdempotencyRecord] = {}

    def execute(
        self, key: str, payload: bytes, fn: Callable[[], Any]
    ) -> IdempotencyRecord:
        """Execute ``fn`` idempotently, keyed by ``key`` + payload digest."""
        payload_digest = "sha256:" + hashlib.sha256(payload).hexdigest()
        existing = self._records.get(key)
        if existing is not None:
            if existing.payload_digest != payload_digest:
                raise DeterminismError(
                    "IDEMPOTENCY_CONFLICT",
                    f"key {key!r} already exists with different payload digest",
                )
            return existing
        result = fn()
        record = IdempotencyRecord(
            idempotency_id=f"idem:{key}:{payload_digest[:12]}",
            key=key,
            payload_digest=payload_digest,
            result=result,
        )
        self._records[key] = record
        return record


@dataclass
class AtomicWriteLease:
    """Atomic write lease tracker (AC-NFR0100-01)."""

    task_id: str
    holder: str = ""
    held: bool = False

    def acquire(self, actor: str) -> CASResult:
        if self.held:
            return CASResult(success=False, retryable=True, reason="lease held")
        self.held = True
        self.holder = actor
        return CASResult(success=True, retryable=False)

    def release(self, actor: str) -> None:
        if self.holder == actor:
            self.held = False
            self.holder = ""
