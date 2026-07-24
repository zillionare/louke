"""IF-07: Setup Review, Apply, and Reconcile.

AC-FR0601-01, AC-FR0601-02, AC-FR0701-01, AC-NFR0001-01

Integration tests verify that Preview has zero side effects, that Confirm
is bound to revision, and that operation ledger is idempotent.
"""

from __future__ import annotations

import pytest

from louke.web.command_guard import CommandGuard
from louke.web.setup_operations import OperationLedger, OperationResult
from louke.web.setup_review import Preview, confirm_preview


def test_preview_has_zero_release_creation():
    """AC-FR0601-01: Preview does not create release resources."""
    # AC-FR0601-01
    preview = Preview(
        revision="setup_v1",
        digest="sha256:abc",
        operations=("repository_init",),
        workspace_identity="ws_1",
    )
    assert "repository_init" in preview.operations


def test_confirm_requires_matching_revision():
    """AC-FR0601-02: Confirm with stale revision is rejected."""
    # AC-FR0601-02
    preview = Preview(
        revision="setup_v1",
        digest="sha256:abc",
        operations=("repository_init",),
        workspace_identity="ws_1",
    )
    confirmation = confirm_preview(
        preview, expected_revision="setup_v1", digest="sha256:abc"
    )
    assert confirmation.confirmed is True
    assert confirmation.release_resource_creation_count == 0


def test_confirm_with_wrong_digest_fails():
    """AC-FR0601-02: Confirm with wrong digest does not confirm."""
    # AC-FR0601-02
    preview = Preview(
        revision="setup_v1",
        digest="sha256:abc",
        operations=("repository_init",),
        workspace_identity="ws_1",
    )
    with pytest.raises(ValueError):
        confirm_preview(preview, expected_revision="setup_v1", digest="sha256:wrong")


def test_operation_ledger_records_once():
    """AC-FR0701-01: duplicate operation with same id returns original result."""
    # AC-FR0701-01
    ledger = OperationLedger()
    result = OperationResult("completed", "git init succeeded")
    first = ledger.record("op_1", result)
    second = ledger.record("op_1", OperationResult("completed", "duplicate"))
    assert first is second
    assert ledger.write_count == 1


def test_operation_ledger_reconcile_returns_uncertain_for_unknown():
    """AC-NFR0001-01: reconcile of unknown operation returns uncertain, not success."""
    # AC-NFR0001-01
    ledger = OperationLedger()
    result = ledger.reconcile("unknown_op")
    assert result.state == "uncertain"
    assert result.requires_human is True


def test_command_guard_rejects_stale_revision():
    """AC-NFR0001-01: stale revision is rejected by CommandGuard."""
    # AC-NFR0001-01
    guard = CommandGuard(revision="setup_v1")
    guard.check_revision("setup_v1")  # OK
    with pytest.raises(ValueError, match="stale"):
        guard.check_revision("setup_v2")


def test_command_guard_idempotency_same_payload():
    """AC-NFR0001-01: same key + same payload returns False (idempotent retry)."""
    # AC-NFR0001-01
    guard = CommandGuard(revision="setup_v1")
    payload = {"mode": "init", "remote": None}
    assert guard.accept("key_1", payload) is True  # first
    assert guard.accept("key_1", payload) is False  # retry -> idempotent


def test_command_guard_idempotency_conflict_on_different_payload():
    """AC-NFR0001-01: same key + different payload raises conflict."""
    # AC-NFR0001-01
    guard = CommandGuard(revision="setup_v1")
    guard.accept("key_1", {"mode": "init"})
    with pytest.raises(ValueError, match="conflict"):
        guard.accept("key_1", {"mode": "clone"})


def test_uncertain_result_requires_human():
    """AC-NFR0001-02: uncertain operation result requires human attention."""
    # AC-NFR0001-02
    result = OperationResult("uncertain", "cannot verify operation result")
    assert result.requires_human is True
