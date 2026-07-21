"""FR-1000: Refactor subphase.

After ``G``, Runtime allows Devon to make behaviour-preserving structural
improvements under test protection, re-running all Green checks.  When
there are changes, an independent Refactor commit ``F`` (parent=G) is
created through ordinary pre-commit; when there are no changes, a
no-change evidence bound to ``G`` is recorded.  Changes to public
interface, data semantics, test layering or architecture are identified
as upstream gaps and may NOT be completed as Refactor (AC-FR1000-01).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

ERROR_CODES = (
    "RGR_REFACTOR_CONTRACT_CHANGED",
    "RGR_PRECOMMIT_FAILED",
    "RGR_FINAL_GATE_FAILED",
)


class RefactorError(Exception):
    """A fail-closed Refactor rejection carrying a stable code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


@dataclass(frozen=True)
class RefactorPatch:
    """A Refactor-phase patch observed by Runtime (AC-FR1000-01).

    Attributes:
        diff_paths: Tuple of paths the patch touches.
        public_interface_changed: ``True`` if the patch changes a public
            interface (must return upstream).
        data_semantics_changed: ``True`` if the patch changes data semantics.
        test_layering_changed: ``True`` if the patch changes test layering.
        architecture_changed: ``True`` if the patch changes architecture.
        has_changes: ``True`` if the patch contains any code change.
    """

    diff_paths: tuple[str, ...]
    public_interface_changed: bool
    data_semantics_changed: bool
    test_layering_changed: bool
    architecture_changed: bool
    has_changes: bool


@dataclass(frozen=True)
class RefactorRecord:
    """Persisted Refactor commit ``F`` evidence (AC-FR1000-01).

    Attributes:
        commit_id: Stable commit identity.
        run_id: Runtime-issued run id.
        task_id: Bound task id.
        attempt_no: Bound attempt number.
        green_oid: ``G`` commit OID (parent of F).
        refactor_oid: ``F`` commit OID.
        parent: ``G`` (parent of F).
        branch_oid: ``F`` (release branch tip advances to F).
        precommit_passed: ``True`` if ordinary pre-commit ran and passed.
        green_checks_passed: ``True`` if all Green checks were re-run and passed.
    """

    commit_id: str
    run_id: str
    task_id: str
    attempt_no: int
    green_oid: str
    refactor_oid: str
    parent: str
    branch_oid: str
    precommit_passed: bool
    green_checks_passed: bool


@dataclass(frozen=True)
class NoChangeEvidence:
    """Evidence recorded when Refactor produces no changes (AC-FR1000-01).

    Attributes:
        evidence_id: Stable evidence identity.
        run_id: Runtime-issued run id.
        task_id: Bound task id.
        attempt_no: Bound attempt number.
        green_oid: ``G`` commit OID the evidence is bound to.
        status: Always ``no-change``.
        green_checks_passed: ``True`` if Green checks were re-run and passed.
    """

    evidence_id: str
    run_id: str
    task_id: str
    attempt_no: int
    green_oid: str
    status: str
    green_checks_passed: bool


def _check_refactor_patch(patch: RefactorPatch) -> None:
    if (
        patch.public_interface_changed
        or patch.data_semantics_changed
        or patch.test_layering_changed
        or patch.architecture_changed
    ):
        raise RefactorError(
            "RGR_REFACTOR_CONTRACT_CHANGED",
            "Refactor must not change public interface, data semantics, test "
            "layering or architecture; return upstream",
        )


def _commit_id(
    *, run_id: str, task_id: str, attempt_no: int, green_oid: str, refactor_oid: str
) -> str:
    payload = f"{run_id}|{task_id}|{attempt_no}|{green_oid}|{refactor_oid}"
    return "refactor:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _evidence_id(*, run_id: str, task_id: str, attempt_no: int, green_oid: str) -> str:
    payload = f"{run_id}|{task_id}|{attempt_no}|{green_oid}|no-change"
    return (
        "refactor-nochange:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
    )


def commit_refactor(
    *,
    run_id: str,
    task_id: str,
    attempt_no: int,
    green_oid: str,
    refactor_oid: str,
    patch: RefactorPatch,
    precommit_passed: bool,
    green_checks_passed: bool,
) -> RefactorRecord:
    """Create the formal Refactor commit ``F`` (AC-FR1000-01).

    Args:
        run_id: Runtime-issued run id.
        task_id: Bound task id.
        attempt_no: Bound attempt number.
        green_oid: ``G`` commit OID (parent of F).
        refactor_oid: ``F`` commit OID.
        patch: The :class:`RefactorPatch` Devon produced.
        precommit_passed: ``True`` if ordinary pre-commit ran and passed.
        green_checks_passed: ``True`` if all Green checks were re-run and passed.

    Returns:
        An immutable :class:`RefactorRecord` with ``parent=G`` and
        ``branch_oid=F`` (release branch advances to F).

    Raises:
        RefactorError: With ``RGR_REFACTOR_CONTRACT_CHANGED`` if the patch
            changes public interface/data semantics/test layering/architecture;
            ``RGR_PRECOMMIT_FAILED`` if pre-commit failed; ``RGR_FINAL_GATE_
            FAILED`` if Green checks were not re-run or did not pass.
    """
    _check_refactor_patch(patch)
    if not green_checks_passed:
        raise RefactorError(
            "RGR_FINAL_GATE_FAILED",
            "Refactor must re-run all Green checks; they did not pass",
        )
    if not precommit_passed:
        raise RefactorError(
            "RGR_PRECOMMIT_FAILED",
            "pre-commit did not pass; cannot create F",
        )
    return RefactorRecord(
        commit_id=_commit_id(
            run_id=run_id,
            task_id=task_id,
            attempt_no=attempt_no,
            green_oid=green_oid,
            refactor_oid=refactor_oid,
        ),
        run_id=run_id,
        task_id=task_id,
        attempt_no=attempt_no,
        green_oid=green_oid,
        refactor_oid=refactor_oid,
        parent=green_oid,  # F.parent = G
        branch_oid=refactor_oid,  # release branch advances to F
        precommit_passed=precommit_passed,
        green_checks_passed=green_checks_passed,
    )


def build_no_change_evidence(
    *,
    run_id: str,
    task_id: str,
    attempt_no: int,
    green_oid: str,
    green_checks_passed: bool,
) -> NoChangeEvidence:
    """Record a no-change Refactor evidence bound to ``G`` (AC-FR1000-01).

    Args:
        run_id: Runtime-issued run id.
        task_id: Bound task id.
        attempt_no: Bound attempt number.
        green_oid: ``G`` commit OID the evidence is bound to.
        green_checks_passed: ``True`` if Green checks were re-run and passed.

    Returns:
        An immutable :class:`NoChangeEvidence` with ``status=no-change``.

    Raises:
        RefactorError: With ``RGR_FINAL_GATE_FAILED`` if Green checks were
            not re-run or did not pass.
    """
    if not green_checks_passed:
        raise RefactorError(
            "RGR_FINAL_GATE_FAILED",
            "No-change Refactor must still re-run Green checks; they did not pass",
        )
    return NoChangeEvidence(
        evidence_id=_evidence_id(
            run_id=run_id, task_id=task_id, attempt_no=attempt_no, green_oid=green_oid
        ),
        run_id=run_id,
        task_id=task_id,
        attempt_no=attempt_no,
        green_oid=green_oid,
        status="no-change",
        green_checks_passed=green_checks_passed,
    )
