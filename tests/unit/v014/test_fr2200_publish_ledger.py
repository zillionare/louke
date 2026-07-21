"""AC-FR2200-01: M-PUBLISH operation ledger & idempotent execution.

After Human Release binds the current preview, Runtime establishes a
stable identity for each applicable external operation (merge/main,
canonical tag, registry/artifact publish, GitHub Release/notes, deploy
and smoke) and persists intent + result.  Agents do NOT execute or
simulate these side effects.  After restart, already-confirmed
operations are NOT repeated; unknown results enter ``needs_attention``.
Runtime may NOT create a different tag, re-upload or overwrite an
immutable artifact.
"""

from __future__ import annotations

import pytest

from louke.v014.fr2200_publish_ledger import (
    Operation,
    OperationKind,
    OperationLedger,
    OperationLedgerError,
    OperationStatus,
)

_CAND = "cand:abc"


def _op(
    *,
    operation_id: str = "op:1",
    kind: OperationKind = "tag",
    target: str = "v0.14.0",
    payload_digest: str = "sha256:" + "p" * 64,
) -> Operation:
    return Operation(
        operation_id=operation_id,
        kind=kind,
        target=target,
        payload_digest=payload_digest,
        status=OperationStatus.PLANNED,
        attempts=(),
    )


def test_ledger_records_intent_before_effect() -> None:
    """AC-FR2200-01: every operation has stable identity + intent persisted before effect."""
    ledger = OperationLedger()
    op = ledger.plan_operation(
        release_identity="0.14.0",
        kind="tag",
        target="v0.14.0",
        payload_digest="sha256:" + "p" * 64,
    )
    assert op.operation_id.startswith("op:")
    assert op.status == OperationStatus.PLANNED


def test_ledger_confirms_operation_after_query_and_effect() -> None:
    """AC-FR2200-01: intent -> query -> effect -> result -> confirmed."""
    ledger = OperationLedger()
    op = ledger.plan_operation(
        release_identity="0.14.0",
        kind="tag",
        target="v0.14.0",
        payload_digest="sha256:" + "p" * 64,
    )
    ledger.query(op.operation_id, query_digest="sha256:" + "q" * 64, cardinality=0)
    ledger.effect(op.operation_id, effect_digest="sha256:" + "e" * 64)
    ledger.confirm(
        op.operation_id, provider_ids=("v0.14.0",), response_digest="sha256:" + "r" * 64
    )
    confirmed = ledger.get(op.operation_id)
    assert confirmed.status == OperationStatus.CONFIRMED


def test_ledger_does_not_repeat_confirmed_operation() -> None:
    """AC-FR2200-01: after restart, already-confirmed operations are NOT repeated."""
    ledger = OperationLedger()
    op = ledger.plan_operation(
        release_identity="0.14.0",
        kind="tag",
        target="v0.14.0",
        payload_digest="sha256:" + "p" * 64,
    )
    ledger.confirm(
        op.operation_id, provider_ids=("v0.14.0",), response_digest="sha256:" + "r" * 64
    )
    # Restart simulation: try to plan the same operation -> idempotent.
    op2 = ledger.plan_operation(
        release_identity="0.14.0",
        kind="tag",
        target="v0.14.0",
        payload_digest="sha256:" + "p" * 64,
    )
    assert op2.operation_id == op.operation_id
    assert op2.status == OperationStatus.CONFIRMED  # stays confirmed, no new effect


def test_ledger_unknown_status_enters_needs_attention() -> None:
    """AC-FR2200-01: unknown result enters needs_attention, not a new tag/upload."""
    ledger = OperationLedger()
    op = ledger.plan_operation(
        release_identity="0.14.0",
        kind="tag",
        target="v0.14.0",
        payload_digest="sha256:" + "p" * 64,
    )
    ledger.mark_unknown(op.operation_id, reason="ack loss")
    assert ledger.get(op.operation_id).status == OperationStatus.UNKNOWN


def test_ledger_rejects_duplicate_operation_id_with_different_payload() -> None:
    """AC-FR2200-01: same operation_id with different payload is an integrity conflict."""
    ledger = OperationLedger()
    op = ledger.plan_operation(
        release_identity="0.14.0",
        kind="tag",
        target="v0.14.0",
        payload_digest="sha256:" + "p" * 64,
    )
    with pytest.raises(OperationLedgerError) as exc:
        # Forcing a different payload through internal _add would conflict; here
        # we simulate by trying to plan with the same op id but a different
        # payload via direct insert.
        ledger._add_operation(
            Operation(
                operation_id=op.operation_id,
                kind="tag",
                target="v0.14.0",
                payload_digest="sha256:" + "X" * 64,
                status=OperationStatus.PLANNED,
                attempts=(),
            )
        )
    assert exc.value.code == "PUB_OPERATION_CONFLICT"


def test_ledger_query_one_with_matching_identity_confirms_without_new_effect() -> None:
    """AC-FR2200-01: query=1 with matching identity confirms; no new effect."""
    ledger = OperationLedger()
    op = ledger.plan_operation(
        release_identity="0.14.0",
        kind="tag",
        target="v0.14.0",
        payload_digest="sha256:" + "p" * 64,
    )
    ledger.query(
        op.operation_id,
        query_digest="sha256:" + "q" * 64,
        cardinality=1,
        existing_digest="sha256:" + "p" * 64,
    )  # matches
    assert ledger.get(op.operation_id).status == OperationStatus.CONFIRMED
    # Subsequent effect attempt is rejected: already confirmed.
    with pytest.raises(OperationLedgerError) as exc:
        ledger.effect(op.operation_id, effect_digest="sha256:" + "e" * 64)
    assert exc.value.code == "PUB_PROVIDER_AMBIGUOUS"


def test_ledger_rejects_overwrite_immutable_artifact() -> None:
    """AC-FR2200-01: cannot overwrite an immutable artifact (e.g. existing tag)."""
    ledger = OperationLedger()
    op = ledger.plan_operation(
        release_identity="0.14.0",
        kind="tag",
        target="v0.14.0",
        payload_digest="sha256:" + "p" * 64,
    )
    with pytest.raises(OperationLedgerError) as exc:
        ledger.query(
            op.operation_id,
            query_digest="sha256:" + "q" * 64,
            cardinality=1,
            existing_digest="sha256:" + "OTHER" * 13,
        )  # different
    assert exc.value.code == "PUB_IMMUTABLE_CONFLICT"


def test_ledger_query_zero_allows_effect_when_contract_create_safe() -> None:
    """AC-FR2200-01: query=0 with contract create-safe allows effect."""
    ledger = OperationLedger()
    op = ledger.plan_operation(
        release_identity="0.14.0",
        kind="tag",
        target="v0.14.0",
        payload_digest="sha256:" + "p" * 64,
    )
    ledger.query(op.operation_id, query_digest="sha256:" + "q" * 64, cardinality=0)
    ledger.effect(op.operation_id, effect_digest="sha256:" + "e" * 64)
    ledger.confirm(
        op.operation_id, provider_ids=("v0.14.0",), response_digest="sha256:" + "r" * 64
    )
    assert ledger.get(op.operation_id).status == OperationStatus.CONFIRMED
