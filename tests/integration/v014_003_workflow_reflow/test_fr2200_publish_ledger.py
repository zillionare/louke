"""Integration tests for FR-2200: M-PUBLISH operation ledger & idempotent
execution.

AC-FR2200-01: After Human Release binds the current preview, each
applicable merge/tag/publish/release/deploy/smoke operation has a
stable identity with intent+result persisted; actor is Runtime. After
simulated restart, confirmed operations are NOT repeated; unknown
results enter needs_attention; Runtime may NOT create a different tag,
re-upload or overwrite an immutable artifact, or let Agents
textually fill in success.

Interfaces covered (per interfaces.md):
- IF-PUB-02 (Primary ARC-15)
- IF-REL-02 (release preview, ARC-14)
- IF-PUB-01 (inherited, ARC-15)
"""
# AC-FR2200-01

from __future__ import annotations

import pytest

from louke.v014.fr2200_publish_ledger import (
    ERROR_CODES,
    Operation,
    OperationLedger,
    OperationLedgerError,
    OperationStatus,
)


# ---------------------------------------------------------------------------
# plan_operation
# ---------------------------------------------------------------------------


@pytest.mark.real_module
def test_plan_operation_creates_stable_identity_with_intent():
    """AC-FR2200-01: plan -> stable operation_id + intent persisted."""
    ledger = OperationLedger()
    op = ledger.plan_operation(
        release_identity="0.14.0",
        kind="tag",
        target="v0.14.0",
        payload_digest="sha256:payload",
    )
    assert isinstance(op, Operation)
    assert op.operation_id.startswith("op:")
    assert op.status == OperationStatus.PLANNED
    assert op.attempts[0].intent_digest == "sha256:payload"
    assert op.kind == "tag"
    assert op.target == "v0.14.0"


@pytest.mark.real_module
def test_plan_operation_is_idempotent_for_same_identity():
    """AC-FR2200-01: same release+kind+target+payload -> same operation_id."""
    ledger = OperationLedger()
    op1 = ledger.plan_operation(
        release_identity="0.14.0",
        kind="tag",
        target="v0.14.0",
        payload_digest="sha256:payload",
    )
    op2 = ledger.plan_operation(
        release_identity="0.14.0",
        kind="tag",
        target="v0.14.0",
        payload_digest="sha256:payload",
    )
    assert op1.operation_id == op2.operation_id


# ---------------------------------------------------------------------------
# query (provider fact lookup)
# ---------------------------------------------------------------------------


@pytest.mark.real_module
def test_query_zero_matches_advances_to_executing():
    """AC-FR2200-01: zero matches -> safe to effect (if contract allows)."""
    ledger = OperationLedger()
    op = ledger.plan_operation(
        release_identity="0.14.0",
        kind="tag",
        target="v0.14.0",
        payload_digest="sha256:payload",
    )
    ledger.query(op.operation_id, query_digest="sha256:q", cardinality=0)
    assert ledger.get(op.operation_id).status == OperationStatus.EXECUTING


@pytest.mark.real_module
def test_query_one_match_with_same_digest_confirms_without_effect():
    """AC-FR2200-01: one exact match -> CONFIRMED without re-effect (idempotent)."""
    ledger = OperationLedger()
    op = ledger.plan_operation(
        release_identity="0.14.0",
        kind="tag",
        target="v0.14.0",
        payload_digest="sha256:payload",
    )
    ledger.query(
        op.operation_id,
        query_digest="sha256:q",
        cardinality=1,
        existing_digest="sha256:payload",  # matches
    )
    assert ledger.get(op.operation_id).status == OperationStatus.CONFIRMED


@pytest.mark.real_module
def test_query_one_match_with_different_digest_rejects_overwrite():
    """AC-FR2200-01: existing resource has different digest -> PUB_IMMUTABLE_CONFLICT;
    cannot overwrite immutable artifact."""
    ledger = OperationLedger()
    op = ledger.plan_operation(
        release_identity="0.14.0",
        kind="tag",
        target="v0.14.0",
        payload_digest="sha256:payload",
    )
    with pytest.raises(OperationLedgerError) as exc:
        ledger.query(
            op.operation_id,
            query_digest="sha256:q",
            cardinality=1,
            existing_digest="sha256:different",
        )
    assert exc.value.code == "PUB_IMMUTABLE_CONFLICT"


@pytest.mark.real_module
def test_query_multiple_matches_needs_attention():
    """AC-FR2200-01: cardinality > 1 -> PUB_PROVIDER_AMBIGUOUS; needs_attention."""
    ledger = OperationLedger()
    op = ledger.plan_operation(
        release_identity="0.14.0",
        kind="tag",
        target="v0.14.0",
        payload_digest="sha256:payload",
    )
    with pytest.raises(OperationLedgerError) as exc:
        ledger.query(op.operation_id, query_digest="sha256:q", cardinality=3)
    assert exc.value.code == "PUB_PROVIDER_AMBIGUOUS"
    assert ledger.get(op.operation_id).status == OperationStatus.NEEDS_ATTENTION


# ---------------------------------------------------------------------------
# mark_unknown + restart recovery
# ---------------------------------------------------------------------------


@pytest.mark.real_module
def test_mark_unknown_after_ack_loss():
    """AC-FR2200-01: ack loss -> UNKNOWN; cannot infer success or failure."""
    ledger = OperationLedger()
    op = ledger.plan_operation(
        release_identity="0.14.0",
        kind="tag",
        target="v0.14.0",
        payload_digest="sha256:payload",
    )
    ledger.mark_unknown(op.operation_id, reason="ack loss")
    assert ledger.get(op.operation_id).status == OperationStatus.UNKNOWN


@pytest.mark.real_module
def test_restart_recovery_does_not_repeat_confirmed_operation():
    """AC-FR2200-01: confirmed operation is NOT re-effected after restart."""
    ledger = OperationLedger()
    op = ledger.plan_operation(
        release_identity="0.14.0",
        kind="tag",
        target="v0.14.0",
        payload_digest="sha256:payload",
    )
    # Simulate: query returns 1 match with same digest -> confirmed.
    ledger.query(
        op.operation_id,
        query_digest="sha256:q",
        cardinality=1,
        existing_digest="sha256:payload",
    )
    assert ledger.get(op.operation_id).status == OperationStatus.CONFIRMED
    # Simulated restart: re-planning the same operation returns the existing
    # confirmed operation (idempotent), NOT a new one.
    op_after_restart = ledger.plan_operation(
        release_identity="0.14.0",
        kind="tag",
        target="v0.14.0",
        payload_digest="sha256:payload",
    )
    assert op_after_restart.operation_id == op.operation_id
    assert op_after_restart.status == OperationStatus.CONFIRMED


@pytest.mark.real_module
def test_error_codes_set_covers_all_documented_codes():
    """AC-FR2200-01: ERROR_CODES includes all codes from interfaces.md §13."""
    expected = {
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
    }
    actual = set(ERROR_CODES)
    missing = expected - actual
    assert not missing, f"ERROR_CODES missing: {missing}"
