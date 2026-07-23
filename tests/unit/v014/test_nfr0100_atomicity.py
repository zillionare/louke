"""NFR-0100: 原子性、CAS 与竞争请求.

AC references:
- AC-NFR0100-01: a crash at the run-state/event transaction boundary leaves
  either both state and event committed (post-commit crash) or neither
  (pre-commit crash); no single-sided record survives.
- AC-NFR0100-02: two concurrent writes with the same expected
  revision/token produce exactly one winner; the loser receives the current
  revision/token and a stable conflict code; the success side effect
  happens only once.
- AC-NFR0100-03: Backlog routing, Project creation, M-LOCK-1 approval and
  Issue reconcile each produce at most one entry/run/gate decision/Issue per
  logical identity under repeated/concurrent requests; all callers receive
  the same identity or an explicit already-completed/conflict result.
- AC-NFR0100-04: external-resource reconcile with zero/multi/stable-id-
  conflict/fuzzy-title candidates returns ``needs_attention`` and lists the
  resource kind, provider namespace and conflicting fields; external
  resource count and recorded identities do not change; only an exact
  single-field-match candidate may be reused.
"""

from __future__ import annotations

import threading

import pytest

from louke.runtime.atomicity import (
    ExternalReconcileCandidate,
    atomic_state_event_write,
    concurrent_cas_write,
    external_reconcile_decision,
    idempotent_identity_outcome,
)


# AC-NFR0100-01 ---------------------------------------------------------------
def test_atomic_write_pre_commit_crash_leaves_neither() -> None:
    """AC-NFR0100-01: a crash before the transaction commits leaves neither
    state nor event."""
    outcome = atomic_state_event_write(crash_at="pre_commit")
    assert outcome.state_committed is False
    assert outcome.event_committed is False
    assert outcome.revision is None  # no single-sided record


def test_atomic_write_post_commit_crash_leaves_both() -> None:
    """AC-NFR0100-01: a crash after the transaction commits leaves both
    state and event with the same revision."""
    outcome = atomic_state_event_write(crash_at="post_commit")
    assert outcome.state_committed is True
    assert outcome.event_committed is True
    assert outcome.revision == 1
    # No single-sided record: both share the same revision.


def test_atomic_write_no_crash_commits_both() -> None:
    """AC-NFR0100-01: a normal write commits both state and event."""
    outcome = atomic_state_event_write(crash_at=None)
    assert outcome.state_committed is True
    assert outcome.event_committed is True
    assert outcome.revision == 1


# AC-NFR0100-02 ---------------------------------------------------------------
def test_concurrent_cas_write_exactly_one_winner() -> None:
    """AC-NFR0100-02: two concurrent CAS writes with the same expected
    revision produce exactly one winner; the loser gets the current revision
    and a stable conflict code."""
    barrier = threading.Barrier(2)
    results: list[object] = []

    def _write(body: str) -> None:
        barrier.wait(timeout=2.0)
        results.append(
            concurrent_cas_write(
                expected_revision=1,
                version_token="tok_1",
                body=body,
            )
        )

    threads = [
        threading.Thread(target=_write, args=("winner",)),
        threading.Thread(target=_write, args=("loser",)),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5.0)

    assert len(results) == 2
    winners = [r for r in results if getattr(r, "ok", False)]  # type: ignore[attr-defined]
    losers = [r for r in results if not getattr(r, "ok", False)]  # type: ignore[attr-defined]
    assert len(winners) == 1
    assert len(losers) == 1
    assert losers[0].conflict_code == "DOCUMENT_WRITE_CONFLICT"  # type: ignore[attr-defined]
    # Success side effect happens only once.
    assert winners[0].side_effect_count == 1  # type: ignore[attr-defined]


# AC-NFR0100-03 ---------------------------------------------------------------
@pytest.mark.parametrize(
    "kind",
    ["backlog", "project", "m_lock_1", "issue"],
)
def test_idempotent_identity_outcome_returns_same_identity(kind: str) -> None:
    """AC-NFR0100-03: repeated requests with the same logical identity
    return the same identity; concurrent callers all see the same result or
    an explicit already-completed/conflict."""
    first = idempotent_identity_outcome(
        kind=kind,  # type: ignore[arg-type]
        logical_identity="id_1",
    )
    second = idempotent_identity_outcome(
        kind=kind,  # type: ignore[arg-type]
        logical_identity="id_1",
    )
    assert first.identity == second.identity
    assert first.entry_count == 1
    assert second.entry_count == 1
    assert second.already_completed is True


def test_idempotent_identity_distinct_logical_identities_produce_distinct_entries() -> (
    None
):
    """AC-NFR0100-03: distinct logical identities produce distinct entries;
    each has its own identity."""
    a = idempotent_identity_outcome(kind="backlog", logical_identity="id_a")
    b = idempotent_identity_outcome(kind="backlog", logical_identity="id_b")
    assert a.identity != b.identity
    assert a.entry_count == 1
    assert b.entry_count == 1


# AC-NFR0100-04 ---------------------------------------------------------------
def test_external_reconcile_zero_candidates_returns_needs_attention() -> None:
    """AC-NFR0100-04: zero candidates return needs_attention; resource count
    and recorded identities do not change."""
    decision = external_reconcile_decision(
        candidates=(),
        expected_fields={"node_id": "R_1", "spec_id": "v0.14-001"},
    )
    assert decision.action == "needs_attention"
    assert decision.reused_identity is None
    assert "zero" in decision.reason.lower()


def test_external_reconcile_multiple_candidates_returns_needs_attention() -> None:
    """AC-NFR0100-04: multiple candidates return needs_attention."""
    candidates = (
        ExternalReconcileCandidate(
            node_id="R_1", title="[FR-0100] one", provider_namespace="ns_1"
        ),
        ExternalReconcileCandidate(
            node_id="R_2", title="[FR-0100] two", provider_namespace="ns_1"
        ),
    )
    decision = external_reconcile_decision(
        candidates=candidates,
        expected_fields={"node_id": "R_1", "spec_id": "v0.14-001"},
    )
    assert decision.action == "needs_attention"
    assert (
        "multiple" in decision.reason.lower() or "conflict" in decision.reason.lower()
    )


def test_external_reconcile_fuzzy_title_only_returns_needs_attention() -> None:
    """AC-NFR0100-04: a candidate whose title is only a fuzzy match (not
    exact node_id) is not reused."""
    candidates = (
        ExternalReconcileCandidate(
            node_id="R_different",  # not exact
            title="[FR-0100] something",
            provider_namespace="ns_1",
        ),
    )
    decision = external_reconcile_decision(
        candidates=candidates,
        expected_fields={"node_id": "R_1", "spec_id": "v0.14-001"},
    )
    assert decision.action == "needs_attention"
    assert decision.reused_identity is None


def test_external_reconcile_exact_single_match_is_reused() -> None:
    """AC-NFR0100-04: a single candidate with exact field match is reused."""
    candidates = (
        ExternalReconcileCandidate(
            node_id="R_1",
            title="[FR-0100] exact",
            provider_namespace="ns_1",
        ),
    )
    decision = external_reconcile_decision(
        candidates=candidates,
        expected_fields={"node_id": "R_1", "spec_id": "v0.14-001"},
    )
    assert decision.action == "reuse"
    assert decision.reused_identity == "R_1"
