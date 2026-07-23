"""Recovery decisions for interrupted Setup and Story delivery requests."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DeliveryRecovery:
    """Persisted delivery identity and last known external result."""

    request_id: str
    status: str
    release_id: str
    start_count: int


def recover_delivery(state: DeliveryRecovery) -> DeliveryRecovery:
    """Reconcile an interrupted delivery without replaying its request.

    Unknown or uncertain results remain attention and preserve the original
    request/release identity for a later owning-surface reconciliation.
    """
    status = "attention" if state.status in {"unknown", "uncertain"} else state.status
    return DeliveryRecovery(
        request_id=state.request_id,
        status=status,
        release_id=state.release_id,
        start_count=state.start_count,
    )
