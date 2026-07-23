"""At-most-once Setup operation ledger and fail-closed reconciliation."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class OperationResult:
    """Readback result for one authorized workspace operation."""

    state: str
    evidence: str

    @property
    def requires_human(self) -> bool:
        """Return whether the result must remain visible for reconciliation."""
        return self.state in {"uncertain", "conflict", "failed"}


class OperationLedger:
    """In-memory operation identity ledger used by application adapters."""

    def __init__(self) -> None:
        self._results: dict[str, OperationResult] = {}
        self.write_count = 0

    def record(self, operation_id: str, result: OperationResult) -> OperationResult:
        """Record once and return the canonical result for an operation id."""
        existing = self._results.get(operation_id)
        if existing is not None:
            return existing
        self._results[operation_id] = result
        self.write_count += 1
        return result

    def reconcile(self, operation_id: str) -> OperationResult:
        """Return readback or an explicit uncertain result for an unknown id."""
        return self._results.get(
            operation_id,
            OperationResult("uncertain", "operation result is not readable"),
        )
