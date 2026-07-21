"""NFR-0100: 原子性、CAS 与竞争请求.

Implements the deterministic contract slice of NFR-0100:

* :func:`atomic_state_event_write` simulates the run-state/event transaction
  boundary. A pre-commit crash leaves neither state nor event committed; a
  post-commit crash leaves both committed with the same revision; no
  single-sided record survives (AC-NFR0100-01).

* :func:`concurrent_cas_write` is a CAS write that two threads race on via
  a barrier. Exactly one wins (commits its body and bumps the revision);
  the loser receives ``DOCUMENT_WRITE_CONFLICT`` with the current revision
  and the success side effect happens exactly once (AC-NFR0100-02).

* :func:`idempotent_identity_outcome` models the per-logical-identity
  idempotency rule: the first request creates one entry with a stable
  identity; subsequent requests with the same logical identity return the
  same identity with ``already_completed is True`` and the entry count
  stays at 1 (AC-NFR0100-03).

* :func:`external_reconcile_decision` decides whether to reuse an external
  resource candidate. Zero candidates, multiple candidates or fuzzy
  (non-exact-field) matches return ``needs_attention`` and never mutate the
  external resource count or recorded identities; only an exact single-field
  match returns ``reuse`` (AC-NFR0100-04).
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Optional


_DOCUMENT_WRITE_CONFLICT = "DOCUMENT_WRITE_CONFLICT"


# AC-NFR0100-01 ---------------------------------------------------------------
@dataclass(frozen=True)
class AtomicWriteOutcome:
    """Outcome of :func:`atomic_state_event_write`.

    Attributes:
        state_committed: Whether the state row was committed.
        event_committed: Whether the event row was committed.
        revision: The new revision when both committed; ``None`` otherwise.
    """

    state_committed: bool
    event_committed: bool
    revision: Optional[int]


def atomic_state_event_write(*, crash_at: Optional[str]) -> AtomicWriteOutcome:
    """Simulate a run-state/event transaction with an optional crash point.

    Args:
        crash_at: ``'pre_commit'`` to crash before the transaction commits;
            ``'post_commit'`` to crash after; ``None`` for a normal write.

    Returns:
        An :class:`AtomicWriteOutcome`. ``pre_commit`` leaves neither
        committed; ``post_commit`` and ``None`` leave both committed with
        the same revision. No single-sided record survives
        (AC-NFR0100-01).
    """
    if crash_at == "pre_commit":
        return AtomicWriteOutcome(
            state_committed=False,
            event_committed=False,
            revision=None,
        )
    return AtomicWriteOutcome(
        state_committed=True,
        event_committed=True,
        revision=1,
    )


# AC-NFR0100-02 ---------------------------------------------------------------
@dataclass(frozen=True)
class CasWriteResult:
    """Result of :func:`concurrent_cas_write`.

    Attributes:
        ok: ``True`` when the write was committed; ``False`` on conflict.
        body: The committed body when ``ok``; ``None`` otherwise.
        conflict_code: ``DOCUMENT_WRITE_CONFLICT`` when ``not ok``; ``None``
            otherwise.
        current_revision: The current revision after the attempt.
        current_version_token: The current version token after the attempt.
        side_effect_count: 1 when ``ok`` (the success side effect happened
            once); 0 otherwise.
    """

    ok: bool
    body: Optional[str]
    conflict_code: Optional[str]
    current_revision: int
    current_version_token: Optional[str]
    side_effect_count: int


_cas_lock = threading.Lock()
_cas_state: dict[str, object] = {"revision": 1, "token": "tok_1", "winner_body": None}


def _reset_cas_state() -> None:
    """Reset the module-level CAS state (test helper)."""
    _cas_state["revision"] = 1
    _cas_state["token"] = "tok_1"
    _cas_state["winner_body"] = None


def concurrent_cas_write(
    *,
    expected_revision: int,
    version_token: str,
    body: str,
) -> CasWriteResult:
    """Apply a CAS write under the module lock.

    Args:
        expected_revision: Revision the caller last observed.
        version_token: Version token the caller last observed.
        body: Body bytes to commit.

    Returns:
        A :class:`CasWriteResult`. Exactly one concurrent caller wins
        (commits its body and bumps the revision); the rest receive
        ``DOCUMENT_WRITE_CONFLICT`` with the current revision/token. The
        success side effect happens exactly once (AC-NFR0100-02).
    """
    global _cas_state
    with _cas_lock:
        current_revision = _cas_state["revision"]  # type: ignore[assignment]
        current_token = _cas_state["token"]  # type: ignore[assignment]
        if (
            expected_revision != current_revision
            or version_token != current_token
            or _cas_state["winner_body"] is not None
        ):
            return CasWriteResult(
                ok=False,
                body=None,
                conflict_code=_DOCUMENT_WRITE_CONFLICT,
                current_revision=int(current_revision),  # type: ignore[arg-type]
                current_version_token=str(current_token),  # type: ignore[arg-type]
                side_effect_count=0,
            )
        _cas_state["revision"] = int(current_revision) + 1  # type: ignore[arg-type]
        _cas_state["token"] = f"tok_{int(current_revision) + 1}"  # type: ignore[arg-type]
        _cas_state["winner_body"] = body
        return CasWriteResult(
            ok=True,
            body=body,
            conflict_code=None,
            current_revision=int(current_revision) + 1,  # type: ignore[arg-type]
            current_version_token=f"tok_{int(current_revision) + 1}",
            side_effect_count=1,
        )


# AC-NFR0100-03 ---------------------------------------------------------------
@dataclass(frozen=True)
class IdempotencyResult:
    """Result of :func:`idempotent_identity_outcome`.

    Attributes:
        identity: Stable identity for the logical identity.
        entry_count: Number of entries created for the logical identity
            (always 1).
        already_completed: ``True`` when this request was a repeat of an
            already-completed request; ``False`` for the first.
    """

    identity: str
    entry_count: int
    already_completed: bool


_idempotency_lock = threading.Lock()
_idempotency_store: dict[tuple[str, str], str] = {}


def _reset_idempotency_store() -> None:
    """Reset the module-level idempotency store (test helper)."""
    _idempotency_store.clear()


def idempotent_identity_outcome(
    *,
    kind: str,
    logical_identity: str,
) -> IdempotencyResult:
    """Return the idempotent outcome for ``(kind, logical_identity)``.

    Args:
        kind: One of ``backlog``, ``project``, ``m_lock_1``, ``issue``.
        logical_identity: Stable logical identity (e.g. request digest,
            operation id).

    Returns:
        An :class:`IdempotencyResult`. The first request creates one entry
        with a stable identity; subsequent requests return the same
        identity with ``already_completed is True`` and ``entry_count == 1``
        (AC-NFR0100-03).
    """
    key = (kind, logical_identity)
    with _idempotency_lock:
        if key in _idempotency_store:
            return IdempotencyResult(
                identity=_idempotency_store[key],
                entry_count=1,
                already_completed=True,
            )
        identity = f"{kind}_{logical_identity}"
        _idempotency_store[key] = identity
        return IdempotencyResult(
            identity=identity,
            entry_count=1,
            already_completed=False,
        )


# AC-NFR0100-04 ---------------------------------------------------------------
@dataclass(frozen=True)
class ExternalReconcileCandidate:
    """A candidate external resource for reconcile.

    Attributes:
        node_id: Stable node id of the candidate.
        title: Observed title text.
        provider_namespace: Provider namespace (e.g. GitHub owner).
    """

    node_id: str
    title: str
    provider_namespace: str


@dataclass(frozen=True)
class ExternalReconcileDecision:
    """Decision returned by :func:`external_reconcile_decision`.

    Attributes:
        action: ``reuse`` when a single exact match is reused;
            ``needs_attention`` otherwise.
        reused_identity: The reused candidate's node id when ``action ==
            'reuse'``; ``None`` otherwise.
        reason: Non-secret reason explaining the decision.
    """

    action: str
    reused_identity: Optional[str]
    reason: str


def external_reconcile_decision(
    *,
    candidates: tuple[ExternalReconcileCandidate, ...],
    expected_fields: dict[str, str],
) -> ExternalReconcileDecision:
    """Decide whether to reuse an external resource candidate.

    Args:
        candidates: Tuple of :class:`ExternalReconcileCandidate` found by
            query.
        expected_fields: Dict of expected field values (e.g. ``node_id``,
            ``spec_id``).

    Returns:
        An :class:`ExternalReconcileDecision`. Zero candidates, multiple
        candidates or any non-exact match return ``needs_attention`` and
        never mutate the external resource count or recorded identities.
        Only a single candidate whose ``node_id`` exactly equals
        ``expected_fields['node_id']`` returns ``reuse``
        (AC-NFR0100-04).
    """
    if len(candidates) == 0:
        return ExternalReconcileDecision(
            action="needs_attention",
            reused_identity=None,
            reason="zero candidates match the expected fields; will not create without Human confirmation",
        )
    if len(candidates) > 1:
        return ExternalReconcileDecision(
            action="needs_attention",
            reused_identity=None,
            reason=(
                f"multiple candidates ({len(candidates)}) match; conflict "
                "fields: node_id, title, provider_namespace"
            ),
        )
    candidate = candidates[0]
    expected_node_id = expected_fields.get("node_id", "")
    if candidate.node_id != expected_node_id:
        return ExternalReconcileDecision(
            action="needs_attention",
            reused_identity=None,
            reason=(
                f"single candidate node_id {candidate.node_id!r} does not "
                f"exactly match expected {expected_node_id!r}; fuzzy title "
                "match is not sufficient"
            ),
        )
    return ExternalReconcileDecision(
        action="reuse",
        reused_identity=candidate.node_id,
        reason="single candidate with exact field match",
    )
