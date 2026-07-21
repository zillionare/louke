"""AC-FR0600-01: Private Red git checkpoint.

After a valid Red, Runtime uses a temporary Git index to create a real
commit ``R`` with ``parent=B`` and ``tree=B + test-only diff``.  The
private ref ``refs/louke/rgr/{run}/{task}/{attempt}/red`` is created via
compare-and-set; it does NOT move the release branch, does NOT enter
formal history, does NOT push, does NOT trigger ordinary pre-commit/CI,
and is bound to task/attempt/baseline/test command/failure fingerprint/
output digest/creator.  Before archive the ref must not be deleted or
overwritten.  The same attempt with a different commit OID fails the
compare-and-set.
"""

from __future__ import annotations

from typing import Any

import pytest

from louke.v014.fr0600_red_git_checkpoint import (
    PrivateRefError,
    PrivateRefStore,
    RedCheckpoint,
    RedCheckpointError,
    create_red_checkpoint,
)

_BASELINE_OID = "b" * 40
_RED_OID = "r" * 40
_REF = "refs/louke/rgr/run-1/t-001/att-1/red"


def _kwargs(**overrides: Any) -> dict[str, Any]:
    base = {
        "run_id": "run-1",
        "task_id": "t-001",
        "attempt_no": 1,
        "baseline_oid": _BASELINE_OID,
        "red_oid": _RED_OID,
        "test_command": ".venv/bin/python3 -m pytest -q",
        "failure_fingerprint": "fp:abc",
        "output_digest": "sha256:" + "o" * 64,
        "creator": "runtime:program",
    }
    base.update(overrides)
    return base


def test_create_red_checkpoint_returns_record() -> None:
    """AC-FR0600-01: a valid Red produces an R record bound to task/attempt/baseline."""
    store = PrivateRefStore()
    record = create_red_checkpoint(store=store, **_kwargs())
    assert isinstance(record, RedCheckpoint)
    assert record.baseline_oid == _BASELINE_OID
    assert record.red_oid == _RED_OID
    assert record.ref == _REF
    assert record.parent == _BASELINE_OID
    assert record.creator == "runtime:program"
    assert record.failure_fingerprint == "fp:abc"


def test_create_red_checkpoint_uses_private_ref_only() -> None:
    """AC-FR0600-01: the ref is under refs/louke/rgr/... and is private."""
    store = PrivateRefStore()
    record = create_red_checkpoint(store=store, **_kwargs())
    assert record.ref.startswith("refs/louke/rgr/")
    # The release branch must NOT be moved.
    assert store.branch_oid == _BASELINE_OID
    assert len(store.remote_pushes) == 0


def test_create_red_checkpoint_does_not_run_precommit_or_ci() -> None:
    """AC-FR0600-01: private R does not trigger ordinary pre-commit/CI."""
    store = PrivateRefStore()
    create_red_checkpoint(store=store, **_kwargs())
    assert store.precommit_invocations == 0
    assert store.ci_invocations == 0


def test_same_attempt_same_oid_is_idempotent() -> None:
    """AC-FR0600-01: replaying the same attempt+OID is idempotent (CAS succeeds)."""
    store = PrivateRefStore()
    a = create_red_checkpoint(store=store, **_kwargs())
    b = create_red_checkpoint(store=store, **_kwargs())
    assert a.red_oid == b.red_oid
    assert a.checkpoint_id == b.checkpoint_id


def test_same_attempt_different_oid_fails_cas() -> None:
    """AC-FR0600-01: same attempt with a different OID fails the compare-and-set."""
    store = PrivateRefStore()
    create_red_checkpoint(store=store, **_kwargs())
    with pytest.raises(PrivateRefError) as exc:
        create_red_checkpoint(store=store, **_kwargs(red_oid="x" * 40))
    assert exc.value.code == "RGR_RED_REF_CONFLICT"


def test_ref_is_not_deleted_or_overwritten_before_archive() -> None:
    """AC-FR0600-01: the ref must not be deleted or overwritten before archive."""
    store = PrivateRefStore()
    create_red_checkpoint(store=store, **_kwargs())
    assert len(store.deleted_refs) == 0  # no deletion attempted


def test_checkpoint_metadata_binds_command_and_fingerprint() -> None:
    """AC-FR0600-01: metadata/evidence contains the command and failure fingerprint."""
    store = PrivateRefStore()
    record = create_red_checkpoint(store=store, **_kwargs())
    assert record.test_command == ".venv/bin/python3 -m pytest -q"
    assert record.failure_fingerprint == "fp:abc"
    assert record.output_digest.startswith("sha256:")
    assert record.creator == "runtime:program"


def test_checkpoint_rejects_missing_required_field() -> None:
    """AC-FR0600-01: missing required field blocks the checkpoint."""
    store = PrivateRefStore()
    kwargs = _kwargs()
    del kwargs["failure_fingerprint"]
    with pytest.raises((RedCheckpointError, TypeError)) as exc:
        create_red_checkpoint(store=store, **kwargs)
    # Either TypeError (missing kw arg) or RedCheckpointError with stable code.
    if isinstance(exc.value, RedCheckpointError):
        assert exc.value.code == "RGR_RED_FAILURE_INVALID"


def test_checkpoint_id_deterministic_for_same_inputs() -> None:
    """AC-FR0600-01: same inputs produce same checkpoint identity."""
    store = PrivateRefStore()
    a = create_red_checkpoint(store=store, **_kwargs())
    store2 = PrivateRefStore()
    b = create_red_checkpoint(store=store2, **_kwargs())
    assert a.checkpoint_id == b.checkpoint_id


def test_ref_path_format() -> None:
    """AC-FR0600-01: ref path follows refs/louke/rgr/{run}/{task}/{attempt}/red."""
    store = PrivateRefStore()
    record = create_red_checkpoint(store=store, **_kwargs())
    assert record.ref == "refs/louke/rgr/run-1/t-001/att-1/red"


def test_red_checkpoint_immutable() -> None:
    """AC-FR0600-01: the checkpoint record is immutable."""
    store = PrivateRefStore()
    record = create_red_checkpoint(store=store, **_kwargs())
    with pytest.raises(Exception):
        record.red_oid = "tampered"  # type: ignore[misc]
