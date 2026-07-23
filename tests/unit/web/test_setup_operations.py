"""Unit contracts for idempotent Setup operation reconciliation."""

from __future__ import annotations

from louke.web.setup_operations import OperationLedger, OperationResult


def test_reconcile_reuses_completed_operation_without_repeating_side_effect() -> None:
    """AC-FR0701-01: readback makes repeated Apply at-most-once."""
    ledger = OperationLedger()
    first = ledger.record("op-1", OperationResult("completed", "head abc"))
    repeated = ledger.reconcile("op-1")

    assert first == repeated
    assert ledger.write_count == 1


def test_uncertain_operation_remains_attention() -> None:
    """AC-FR0701-02: unknown external result never becomes success."""
    ledger = OperationLedger()
    ledger.record("op-2", OperationResult("uncertain", "remote response lost"))

    result = ledger.reconcile("op-2")

    assert result.state == "uncertain"
    assert result.requires_human
