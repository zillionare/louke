"""FR-0800: Green minimal implementation & Red test protection.

Entering Green, Runtime restores the precise reviewed ``R`` tree; the
release branch remains ``B``.  Devon may only add the minimal code that
makes the Red tests pass, following current design/CI contracts.  The
``R`` tests must not be deleted, weakened or rewritten; corrections must
return to Red.  Runtime independently runs target tests, all historical
host unit tests, applicable lint/format/type/static and task contract
checks; historical failures may not be skipped (AC-FR0800-01).
"""

from __future__ import annotations

from dataclasses import dataclass, field

ERROR_CODES = (
    "RGR_TEST_MUTATED",
    "RGR_GREEN_SCOPE_DENIED",
    "RGR_HISTORY_TEST_FAILED",
    "RGR_REFACTOR_CONTRACT_CHANGED",
)


class GreenChecksError(Exception):
    """A fail-closed Green rejection carrying a stable code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


@dataclass(frozen=True)
class GreenPatch:
    """A Green-phase patch observed by Runtime (AC-FR0800-01).

    Attributes:
        diff_paths: Tuple of paths the patch touches.
        test_deleted: ``True`` if any reviewed R test was deleted.
        test_weakened: ``True`` if any reviewed R test was weakened.
        implementation_added: ``True`` if the patch adds implementation code.
        design_contract_change: ``True`` if the patch changes design/contract
            (must return upstream, not Green).
    """

    diff_paths: tuple[str, ...]
    test_deleted: bool
    test_weakened: bool
    implementation_added: bool
    design_contract_change: bool


@dataclass(frozen=True)
class GreenCheck:
    """A single Green check result.

    Attributes:
        name: Stable check name (``target|history-unit|static|contract|lint|format``).
        passed: ``True`` if the check passed.
        detail: Optional diagnostic detail.
    """

    name: str
    passed: bool
    detail: str = ""


@dataclass(frozen=True)
class GreenChecksReport:
    """Result of :func:`evaluate_green_checks`.

    Attributes:
        status: ``pass`` or ``fail``.
        failed_checks: Tuple of :class:`GreenCheck` that failed.
    """

    status: str
    failed_checks: tuple[GreenCheck, ...] = ()


def evaluate_green_checks(checks: list[GreenCheck]) -> GreenChecksReport:
    """Evaluate Green checks; fail on any non-PASS (AC-FR0800-01).

    Args:
        checks: List of :class:`GreenCheck` for target tests, history unit,
            static, contract, lint and format.

    Returns:
        A :class:`GreenChecksReport` with ``status=pass`` only when every
        required check passed.
    """
    failed = tuple(c for c in checks if not c.passed)
    return GreenChecksReport(
        status="fail" if failed else "pass",
        failed_checks=failed,
    )


@dataclass(frozen=True)
class GreenAttempt:
    """A Green attempt bound to a reviewed ``R`` (AC-FR0800-01).

    Attributes:
        run_id: Runtime-issued run id.
        task_id: Bound task id.
        attempt_no: Bound attempt number.
        baseline_oid: ``B`` commit OID (release branch tip).
        reviewed_red_oid: ``R`` commit OID whose tree was restored.
        workspace_tree_oid: ``R`` (workspace tree restored from R).
        branch_oid: ``B`` (release branch unchanged).
        patch: The :class:`GreenPatch` Devon produced.
        checks: The :class:`GreenChecksReport` from Runtime.
    """

    run_id: str
    task_id: str
    attempt_no: int
    baseline_oid: str
    reviewed_red_oid: str
    workspace_tree_oid: str
    branch_oid: str
    patch: GreenPatch
    checks: GreenChecksReport = field(
        default_factory=lambda: GreenChecksReport(status="pass")
    )


def _check_patch(patch: GreenPatch) -> None:
    if patch.test_deleted or patch.test_weakened:
        raise GreenChecksError(
            "RGR_TEST_MUTATED",
            "Green must not delete, weaken or rewrite R tests; return to Red",
        )
    if patch.design_contract_change:
        raise GreenChecksError(
            "RGR_REFACTOR_CONTRACT_CHANGED",
            "Green must not change design/contract; return upstream",
        )
    if not patch.implementation_added:
        raise GreenChecksError(
            "RGR_GREEN_SCOPE_DENIED",
            "Green must add minimal implementation to pass R tests",
        )


def build_green_attempt(
    *,
    run_id: str,
    task_id: str,
    attempt_no: int,
    baseline_oid: str,
    reviewed_red_oid: str,
    patch: GreenPatch,
) -> GreenAttempt:
    """Build a Green attempt restoring the reviewed ``R`` tree (AC-FR0800-01).

    Args:
        run_id: Runtime-issued run id.
        task_id: Bound task id.
        attempt_no: Bound attempt number.
        baseline_oid: ``B`` commit OID (release branch tip).
        reviewed_red_oid: ``R`` commit OID whose tree was restored.
        patch: The :class:`GreenPatch` Devon produced.

    Returns:
        A :class:`GreenAttempt` with ``workspace_tree_oid=R`` and
        ``branch_oid=B`` (release branch unchanged).

    Raises:
        GreenChecksError: With a stable code from :data:`ERROR_CODES` for any
            invalid Green patch (deleted/weakened tests, design/contract
            change, or no implementation added).
    """
    _check_patch(patch)
    return GreenAttempt(
        run_id=run_id,
        task_id=task_id,
        attempt_no=attempt_no,
        baseline_oid=baseline_oid,
        reviewed_red_oid=reviewed_red_oid,
        workspace_tree_oid=reviewed_red_oid,  # restore reviewed R tree
        branch_oid=baseline_oid,  # release branch unchanged
        patch=patch,
    )
