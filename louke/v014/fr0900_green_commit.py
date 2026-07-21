"""FR-0900: Formal Green commit & lineage.

After Green checks pass, Runtime creates formal commit ``G`` on the
release branch with ``parent=B`` and tree containing the reviewed tests
+ minimal implementation.  Trailers/evidence associate task and ``R``.
``G`` runs the ordinary pre-commit; ``--no-verify`` is forbidden.  If
hooks rewrite files, Runtime re-validates scope/lineage/checks.  Runtime
proves ``B->R`` test-only, ``R->G`` default implementation-only; ``R``
is NOT a parent of ``G`` (AC-FR0900-01).
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

ERROR_CODES = (
    "RGR_PRECOMMIT_FAILED",
    "RGR_LINEAGE_INVALID",
    "RGR_BRANCH_CONFLICT",
)


class GreenCommitError(Exception):
    """A fail-closed Green commit rejection carrying a stable code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


@dataclass(frozen=True)
class LineageCheck:
    """Diff direction classification for sibling lineage (AC-FR0900-01).

    Attributes:
        test_only: ``True`` if the diff only adds/modifies tests.
        implementation_only: ``True`` if the diff only adds implementation.
    """

    test_only: bool
    implementation_only: bool


@dataclass(frozen=True)
class GreenLineage:
    """The ``B/R/G`` sibling lineage evidence (AC-FR0900-01).

    Attributes:
        baseline_oid: ``B`` commit OID.
        red_oid: ``R`` commit OID (private, sibling of G).
        green_oid: ``G`` commit OID (formal release-branch commit).
        b_r_diff: :class:`LineageCheck` for ``B->R`` (must be test-only).
        r_g_diff: :class:`LineageCheck` for ``R->G`` (default impl-only).
        r_is_g_parent: ``True`` only if R is a parent of G (forbidden).
    """

    baseline_oid: str
    red_oid: str
    green_oid: str
    b_r_diff: LineageCheck
    r_g_diff: LineageCheck
    r_is_g_parent: bool = False


@dataclass(frozen=True)
class LineageReport:
    """Result of :func:`verify_lineage`.

    Attributes:
        status: ``pass`` or ``fail``.
        reason: Stable reason explaining a failure.
    """

    status: str
    reason: str = ""


def verify_lineage(lineage: GreenLineage) -> LineageReport:
    """Verify the ``B/R/G`` sibling lineage (AC-FR0900-01).

    Args:
        lineage: :class:`GreenLineage` evidence to verify.

    Returns:
        A :class:`LineageReport` with ``status=pass`` only when:
        - ``B->R`` is test-only,
        - ``R->G`` is implementation-only (default),
        - ``R`` is NOT a parent of ``G``.
    """
    if lineage.r_is_g_parent:
        return LineageReport(
            status="fail",
            reason="RGR_LINEAGE_INVALID: R must NOT be a parent of G (sibling lineage)",
        )
    if not lineage.b_r_diff.test_only:
        return LineageReport(
            status="fail",
            reason="RGR_LINEAGE_INVALID: B->R diff must be test-only",
        )
    if lineage.r_g_diff.test_only:
        return LineageReport(
            status="fail",
            reason="RGR_LINEAGE_INVALID: R->G diff must be implementation-only by default",
        )
    return LineageReport(status="pass", reason="lineage valid")


@dataclass(frozen=True)
class GreenCommitRecord:
    """Persisted formal Green commit evidence (AC-FR0900-01).

    Attributes:
        commit_id: Stable commit identity.
        run_id: Runtime-issued run id.
        task_id: Bound task id.
        attempt_no: Bound attempt number.
        baseline_oid: ``B`` commit OID (parent of G).
        red_oid: ``R`` commit OID referenced by trailers.
        green_oid: ``G`` commit OID.
        parent: ``B`` (parent of G).
        branch_oid: ``G`` (release branch tip advances to G).
        trailer_refs: Mapping of trailer refs (task_id, red_oid).
        precommit_passed: ``True`` if ordinary pre-commit ran and passed.
        hook_rewrote_files: ``True`` if hooks rewrote files (re-validated).
    """

    commit_id: str
    run_id: str
    task_id: str
    attempt_no: int
    baseline_oid: str
    red_oid: str
    green_oid: str
    parent: str
    branch_oid: str
    trailer_refs: dict[str, str]
    precommit_passed: bool
    hook_rewrote_files: bool


def _commit_id(kwargs: dict[str, Any]) -> str:
    payload = "|".join(
        str(kwargs[k])
        for k in (
            "run_id",
            "task_id",
            "attempt_no",
            "baseline_oid",
            "red_oid",
            "green_oid",
        )
    )
    return "green:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def commit_green(
    *,
    run_id: str,
    task_id: str,
    attempt_no: int,
    baseline_oid: str,
    red_oid: str,
    green_oid: str,
    precommit_passed: bool,
    used_no_verify: bool,
    hook_rewrote_files: bool,
    b_r_diff: dict[str, bool],
    r_g_diff: dict[str, bool],
    revalidated_after_rewrite: bool = True,
) -> GreenCommitRecord:
    """Create the formal ``G`` commit on the release branch (AC-FR0900-01).

    Args:
        run_id: Runtime-issued run id.
        task_id: Bound task id.
        attempt_no: Bound attempt number.
        baseline_oid: ``B`` commit OID (parent of G).
        red_oid: ``R`` commit OID referenced by trailers.
        green_oid: ``G`` commit OID.
        precommit_passed: ``True`` if ordinary pre-commit ran and passed.
        used_no_verify: ``True`` if ``--no-verify`` was used (forbidden).
        hook_rewrote_files: ``True`` if hooks rewrote files.
        b_r_diff: Diff classification for ``B->R`` (``{test_only, implementation_only}``).
        r_g_diff: Diff classification for ``R->G``.
        revalidated_after_rewrite: ``True`` if scope/lineage/checks were
            re-validated after a hook rewrite.

    Returns:
        An immutable :class:`GreenCommitRecord` with ``parent=B`` and
        ``branch_oid=G`` (release branch advances to G).

    Raises:
        GreenCommitError: With ``RGR_PRECOMMIT_FAILED`` if pre-commit did
            not pass, ``--no-verify`` was used, or a hook rewrite was not
            re-validated; ``RGR_LINEAGE_INVALID`` if the sibling lineage is
            broken.
    """
    if used_no_verify:
        raise GreenCommitError(
            "RGR_PRECOMMIT_FAILED",
            "blanket --no-verify is forbidden; pre-commit must run",
        )
    if not precommit_passed:
        raise GreenCommitError(
            "RGR_PRECOMMIT_FAILED",
            "pre-commit did not pass; cannot create G",
        )
    if hook_rewrote_files and not revalidated_after_rewrite:
        raise GreenCommitError(
            "RGR_PRECOMMIT_FAILED",
            "hook rewrote files; scope/lineage/checks must be re-validated",
        )
    lineage = GreenLineage(
        baseline_oid=baseline_oid,
        red_oid=red_oid,
        green_oid=green_oid,
        b_r_diff=LineageCheck(
            test_only=bool(b_r_diff.get("test_only", False)),
            implementation_only=bool(b_r_diff.get("implementation_only", False)),
        ),
        r_g_diff=LineageCheck(
            test_only=bool(r_g_diff.get("test_only", False)),
            implementation_only=bool(r_g_diff.get("implementation_only", False)),
        ),
    )
    lineage_report = verify_lineage(lineage)
    if lineage_report.status != "pass":
        raise GreenCommitError("RGR_LINEAGE_INVALID", lineage_report.reason)
    kwargs: dict[str, Any] = {
        "run_id": run_id,
        "task_id": task_id,
        "attempt_no": attempt_no,
        "baseline_oid": baseline_oid,
        "red_oid": red_oid,
        "green_oid": green_oid,
    }
    return GreenCommitRecord(
        commit_id=_commit_id(kwargs),
        run_id=run_id,
        task_id=task_id,
        attempt_no=attempt_no,
        baseline_oid=baseline_oid,
        red_oid=red_oid,
        green_oid=green_oid,
        parent=baseline_oid,  # G.parent = B
        branch_oid=green_oid,  # release branch advances to G
        trailer_refs={"task_id": task_id, "red_oid": red_oid},
        precommit_passed=precommit_passed,
        hook_rewrote_files=hook_rewrote_files,
    )
