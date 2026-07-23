"""AC-NFR0100-01: Determinism, atomicity & concurrency safety.

State transitions, write lease, controlled commit, Red ref, candidate
freeze and publish operation must use atomic/compare-and-set semantics;
the same input retried must converge to the same fact, and concurrent
attempts must NOT overwrite or cross-write.  In concurrent fixtures for
lease/stage transition/controlled commit/Red ref/candidate/publish
operation, exactly one compare-and-set succeeds; the rest receive a
retryable conflict and do NOT overwrite the winner.
"""

from __future__ import annotations

import threading

import pytest

from louke.runtime.determinism import (
    DeterminismError,
    IdempotencyStore,
    acquire_lease_concurrent,
    cas_red_ref,
    freeze_candidate_concurrent,
    publish_operation_concurrent,
    transition_state_concurrent,
)

_RUN = "run-1"
_TASK = "t-001"


def test_cas_red_ref_only_one_succeeds_for_same_attempt_different_oid() -> None:
    """AC-NFR0100-01: same attempt with different OID -> exactly one CAS succeeds."""
    results = cas_red_ref(
        ref="refs/louke/rgr/run-1/t-001/att-1/red",
        attempts=[("r1" * 20, None), ("r2" * 20, None)],  # different OIDs
    )
    successes = [r for r in results if r.success]
    conflicts = [r for r in results if not r.success]
    assert len(successes) == 1
    assert len(conflicts) == 1
    assert conflicts[0].retryable is True


def test_cas_red_ref_idempotent_for_same_oid() -> None:
    """AC-NFR0100-01: same attempt + same OID -> idempotent success."""
    results = cas_red_ref(
        ref="refs/louke/rgr/run-1/t-001/att-1/red",
        attempts=[("r1" * 20, None), ("r1" * 20, "r1" * 20)],
    )
    assert all(r.success for r in results)


def test_acquire_lease_concurrent_single_winner() -> None:
    """AC-NFR0100-01: concurrent lease acquire yields exactly one winner."""
    barrier = threading.Barrier(5)
    results = acquire_lease_concurrent(
        task_id=_TASK,
        actors=("devon:1", "devon:2", "devon:3", "devon:4", "devon:5"),
        barrier=barrier,
    )
    successes = [r for r in results if r.success]
    conflicts = [r for r in results if not r.success]
    assert len(successes) == 1
    assert len(conflicts) == 4
    assert all(c.retryable for c in conflicts)


def test_transition_state_concurrent_single_winner() -> None:
    """AC-NFR0100-01: concurrent state transitions yield exactly one winner."""
    results = transition_state_concurrent(
        run_id=_RUN,
        from_revision=1,
        to_revision=2,
        actors=("runtime:1", "runtime:2", "runtime:3"),
    )
    successes = [r for r in results if r.success]
    assert len(successes) == 1
    assert all(not r.success for r in results if r not in successes)


def test_freeze_candidate_concurrent_single_winner() -> None:
    """AC-NFR0100-01: concurrent freeze attempts yield exactly one winner."""
    results = freeze_candidate_concurrent(
        run_id=_RUN,
        candidate_id="cand:abc",
        actors=("runtime:1", "runtime:2"),
    )
    successes = [r for r in results if r.success]
    assert len(successes) == 1


def test_publish_operation_concurrent_single_winner() -> None:
    """AC-NFR0100-01: concurrent publish operations yield exactly one winner."""
    results = publish_operation_concurrent(
        operation_id="op:1",
        actors=("runtime:1", "runtime:2"),
    )
    successes = [r for r in results if r.success]
    assert len(successes) == 1
    assert all(not r.success for r in results if r not in successes)


def test_idempotency_store_replay_returns_same_result() -> None:
    """AC-NFR0100-01: same idempotency key + bytes replay returns same result."""
    store = IdempotencyStore()
    record1 = store.execute("key-1", b"payload-1", lambda: "result-A")
    record2 = store.execute("key-1", b"payload-1", lambda: "result-B")  # replay
    assert record1.result == "result-A"
    assert record2.result == "result-A"  # original result preserved
    assert record1.idempotency_id == record2.idempotency_id


def test_idempotency_store_rejects_same_key_different_bytes() -> None:
    """AC-NFR0100-01: same key with different bytes is an integrity conflict."""
    store = IdempotencyStore()
    store.execute("key-1", b"payload-1", lambda: "result-A")
    with pytest.raises(DeterminismError) as exc:
        store.execute("key-1", b"payload-2", lambda: "result-B")
    assert exc.value.code == "IDEMPOTENCY_CONFLICT"


def test_different_attempts_keep_independent_history() -> None:
    """AC-NFR0100-01: different attempts each keep their own history."""
    store = IdempotencyStore()
    r1 = store.execute("key-1", b"p1", lambda: "r1")
    r2 = store.execute("key-2", b"p2", lambda: "r2")
    assert r1.result == "r1"
    assert r2.result == "r2"
    assert r1.idempotency_id != r2.idempotency_id
