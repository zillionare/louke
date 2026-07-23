"""Unit contracts for revision and idempotency command guards."""

from __future__ import annotations

import pytest

from louke.web.command_guard import CommandGuard


def test_same_key_same_payload_is_idempotent_and_stale_revision_is_rejected() -> None:
    """AC-NFR0001-01: one matching revision may commit at most once."""
    guard = CommandGuard("rev-1")
    assert guard.accept("key-1", {"mode": "init"})
    assert not guard.accept("key-1", {"mode": "init"})

    with pytest.raises(ValueError, match="stale"):
        guard.check_revision("rev-2")


def test_same_key_different_payload_is_conflict() -> None:
    """AC-NFR0001-02: idempotency-key reuse with another body fails closed."""
    guard = CommandGuard("rev-1")
    guard.accept("key-1", {"mode": "init"})

    with pytest.raises(ValueError, match="idempotency"):
        guard.accept("key-1", {"mode": "clone"})
