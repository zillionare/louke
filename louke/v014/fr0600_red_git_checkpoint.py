"""FR-0600: Private Red git checkpoint.

After a valid Red, Runtime uses a temporary Git index to create a real
commit ``R`` with ``parent=B`` and ``tree=B + test-only diff``.  The
private ref ``refs/louke/rgr/{run}/{task}/{attempt}/red`` is created via
compare-and-set; it does NOT move the release branch, does NOT enter
formal history, does NOT push, does NOT trigger ordinary pre-commit/CI,
and is bound to task/attempt/baseline/test command/failure fingerprint/
output digest/creator.  Before archive the ref must not be deleted or
overwritten.  The same attempt with a different commit OID fails the
compare-and-set (AC-FR0600-01).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any

ERROR_CODES = (
    "RGR_RED_REF_CONFLICT",
    "RGR_RED_FAILURE_INVALID",
    "RGR_LINEAGE_INVALID",
)

_REQUIRED_FIELDS = (
    "run_id",
    "task_id",
    "attempt_no",
    "baseline_oid",
    "red_oid",
    "test_command",
    "failure_fingerprint",
    "output_digest",
    "creator",
)


class RedCheckpointError(Exception):
    """A fail-closed Red checkpoint rejection carrying a stable code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


class PrivateRefError(Exception):
    """A fail-closed private ref CAS rejection carrying a stable code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


@dataclass
class PrivateRefStore:
    """In-memory stand-in for the Git private ref store (AC-FR0600-01).

    Real Runtime uses ``git update-ref <ref> <new> <old>`` and a temporary
    index.  This stand-in captures the same observable contract: branch
    never moves, ref is CAS-created, no remote push, no pre-commit/CI.
    """

    refs: dict[str, str] = field(default_factory=dict)
    branch_oid: str | None = None
    remote_pushes: list[str] = field(default_factory=list)
    precommit_invocations: int = 0
    ci_invocations: int = 0
    deleted_refs: list[str] = field(default_factory=list)

    def compare_and_set_ref(
        self,
        ref: str,
        new_oid: str,
        expected_old_oid: str | None,
    ) -> None:
        if expected_old_oid is None:
            if ref in self.refs:
                raise PrivateRefError(
                    "RGR_RED_REF_CONFLICT",
                    f"ref {ref} already exists with OID {self.refs[ref]}",
                )
            self.refs[ref] = new_oid
            return
        current = self.refs.get(ref)
        if current is None:
            raise PrivateRefError(
                "RGR_RED_REF_CONFLICT",
                f"ref {ref} missing; expected {expected_old_oid}",
            )
        if current != expected_old_oid:
            raise PrivateRefError(
                "RGR_RED_REF_CONFLICT",
                f"ref {ref} OID {current} != expected {expected_old_oid}",
            )
        if current != new_oid:
            raise PrivateRefError(
                "RGR_RED_REF_CONFLICT",
                f"ref {ref} OID {current} != new {new_oid}; same attempt must reuse same OID",
            )
        # idempotent: same OID, no change.


@dataclass(frozen=True)
class RedCheckpoint:
    """Persisted Red checkpoint evidence (AC-FR0600-01).

    Attributes:
        checkpoint_id: Stable checkpoint identity.
        run_id: Runtime-issued run id.
        task_id: Bound task id.
        attempt_no: Bound attempt number.
        baseline_oid: ``B`` commit OID.
        red_oid: ``R`` commit OID.
        parent: ``B`` (parent of R).
        ref: ``refs/louke/rgr/{run}/{task}/{attempt}/red``.
        test_command: Exact test command that produced the Red failure.
        failure_fingerprint: Failure fingerprint from the Red gate.
        output_digest: ``sha256:<hex>`` of the test runner output bytes.
        creator: Actor that created the checkpoint.
    """

    checkpoint_id: str
    run_id: str
    task_id: str
    attempt_no: int
    baseline_oid: str
    red_oid: str
    parent: str
    ref: str
    test_command: str
    failure_fingerprint: str
    output_digest: str
    creator: str


def _ref(run_id: str, task_id: str, attempt_no: int) -> str:
    return f"refs/louke/rgr/{run_id}/{task_id}/att-{attempt_no}/red"


def _checkpoint_id(kwargs: dict[str, Any]) -> str:
    payload = "|".join(str(kwargs[k]) for k in _REQUIRED_FIELDS)
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
    return f"red-cp:{digest}"


def create_red_checkpoint(
    *,
    store: PrivateRefStore,
    run_id: str,
    task_id: str,
    attempt_no: int,
    baseline_oid: str,
    red_oid: str,
    test_command: str,
    failure_fingerprint: str,
    output_digest: str,
    creator: str,
) -> RedCheckpoint:
    """Create a private Red checkpoint ``R`` bound to ``B`` (AC-FR0600-01).

    Args:
        store: :class:`PrivateRefStore` capturing the Git contract.
        run_id: Runtime-issued run id.
        task_id: Bound task id.
        attempt_no: Bound attempt number.
        baseline_oid: ``B`` commit OID.
        red_oid: ``R`` commit OID.
        test_command: Exact test command that produced the Red failure.
        failure_fingerprint: Failure fingerprint from the Red gate.
        output_digest: ``sha256:<hex>`` of the test runner output bytes.
        creator: Actor that created the checkpoint.

    Returns:
        An immutable :class:`RedCheckpoint` bound to the CAS-created ref.

    Raises:
        RedCheckpointError: With ``RGR_RED_FAILURE_INVALID`` if any required
            field is missing or empty.
        PrivateRefError: With ``RGR_RED_REF_CONFLICT`` if the same attempt
            already has a different OID (compare-and-set failure).
    """
    kwargs = {
        "run_id": run_id,
        "task_id": task_id,
        "attempt_no": attempt_no,
        "baseline_oid": baseline_oid,
        "red_oid": red_oid,
        "test_command": test_command,
        "failure_fingerprint": failure_fingerprint,
        "output_digest": output_digest,
        "creator": creator,
    }
    missing = [k for k in _REQUIRED_FIELDS if not kwargs[k]]
    if missing:
        raise RedCheckpointError(
            "RGR_RED_FAILURE_INVALID",
            f"missing required fields: {missing}",
        )
    ref = _ref(run_id, task_id, attempt_no)
    existing = store.refs.get(ref)
    if existing is None:
        store.compare_and_set_ref(ref, red_oid, expected_old_oid=None)
    else:
        # Idempotent if same OID; conflict if different OID.
        store.compare_and_set_ref(ref, red_oid, expected_old_oid=existing)
    # The release branch is NOT moved and remote is NOT pushed.
    store.branch_oid = baseline_oid
    return RedCheckpoint(
        checkpoint_id=_checkpoint_id(kwargs),
        run_id=run_id,
        task_id=task_id,
        attempt_no=attempt_no,
        baseline_oid=baseline_oid,
        red_oid=red_oid,
        parent=baseline_oid,
        ref=ref,
        test_command=test_command,
        failure_fingerprint=failure_fingerprint,
        output_digest=output_digest,
        creator=creator,
    )
