"""FR-0500: Red program gate.

In ``phase=red`` Devon may only add unit/contract tests proving the
current task's missing behaviour.  Runtime validates test-only diff,
format, test syntax, secret absence, AC trace, anti-pattern scan, and
applicable static checks.  The gate requires a precise behaviour-assertion
failure matching the current requirement/interface, OR a precise
compile/type failure caused by an already-designed-but-unimplemented
symbol/interface.  Environment/fixture/permission/dependency/unrelated
failures are invalid Red and are rejected with stable codes
(AC-FR0500-01).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ERROR_CODES = (
    "RGR_RED_NOT_TEST_ONLY",
    "RGR_RED_UNEXPECTED_PASS",
    "RGR_RED_FAILURE_INVALID",
    "RGR_RED_TRACE_MISSING",
    "RGR_TEST_MUTATED",
)

FailureCategory = Literal[
    "assertion",
    "missing-symbol",
    "environment",
    "fixture",
    "permission",
    "dependency",
    "unrelated",
]

_VALID_FAILURE_CATEGORIES: frozenset[str] = frozenset({"assertion", "missing-symbol"})


class RedGateError(Exception):
    """A fail-closed Red gate rejection carrying a stable code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


@dataclass(frozen=True)
class RedPatch:
    """A Red-phase patch observed by Runtime (AC-FR0500-01).

    Attributes:
        diff_paths: Tuple of paths the patch touches.
        product_code_changed: ``True`` if any non-test path was modified.
        test_weakened: ``True`` if the patch removes assertions, lowers
            expectations or skips existing tests.
        ac_refs: Tuple of AC anchors present in the diff.
        has_anti_pattern: ``True`` if any FAKE-* anti-pattern was detected.
        syntax_valid: ``True`` if the test files parse.
        secret_detected: ``True`` if a secret pattern was detected.
        static_check_passed: ``True`` if applicable static checks passed.
        format_passed: ``True`` if the diff passes project format checks.
    """

    diff_paths: tuple[str, ...]
    product_code_changed: bool
    test_weakened: bool
    ac_refs: tuple[str, ...]
    has_anti_pattern: bool
    syntax_valid: bool
    secret_detected: bool
    static_check_passed: bool
    format_passed: bool


@dataclass(frozen=True)
class FailureFingerprint:
    """A precise failure fingerprint for a Red attempt (AC-FR0500-01).

    Attributes:
        category: ``assertion|missing-symbol`` for valid Red; other values
            are invalid Red.
        command: The exact test command that produced the failure.
        ac_refs: AC anchors the failing assertion references.
        assertion_identity: ``module::test_name`` of the failing assertion.
        output_digest: ``sha256:<hex>`` of the test runner output bytes.
    """

    category: FailureCategory
    command: str
    ac_refs: tuple[str, ...]
    assertion_identity: str
    output_digest: str


@dataclass(frozen=True)
class RedGateResult:
    """The result of :func:`evaluate_red_gate` for a passing Red attempt.

    Attributes:
        status: ``pass`` for a valid Red; ``fail`` otherwise.
        failure_fingerprint: The validated :class:`FailureFingerprint`.
        command: The exact test command that was run.
        ac_refs: Tuple of AC anchors covered by the Red.
    """

    status: str
    failure_fingerprint: FailureFingerprint | None
    command: str
    ac_refs: tuple[str, ...]


def _check_patch(patch: RedPatch) -> None:
    if patch.product_code_changed:
        raise RedGateError(
            "RGR_RED_NOT_TEST_ONLY",
            "Red diff must only contain test files; product code changed",
        )
    if patch.test_weakened:
        raise RedGateError(
            "RGR_TEST_MUTATED",
            "Red diff must not weaken or remove existing assertions",
        )
    if not patch.ac_refs:
        raise RedGateError(
            "RGR_RED_TRACE_MISSING",
            "Red diff must reference at least one AC anchor",
        )
    if (
        not patch.syntax_valid
        or patch.has_anti_pattern
        or patch.secret_detected
        or not patch.static_check_passed
        or not patch.format_passed
    ):
        raise RedGateError(
            "RGR_RED_FAILURE_INVALID",
            "Red diff failed syntax/anti-pattern/secret/static/format checks",
        )


def _check_failure(
    failure: FailureFingerprint | None, patch: RedPatch, command: str
) -> FailureFingerprint:
    if failure is None:
        raise RedGateError(
            "RGR_RED_UNEXPECTED_PASS",
            "Red gate requires a precise failure; the tests unexpectedly passed",
        )
    if failure.category not in _VALID_FAILURE_CATEGORIES:
        raise RedGateError(
            "RGR_RED_FAILURE_INVALID",
            f"failure category {failure.category!r} is not a valid Red failure",
        )
    if failure.command != command:
        raise RedGateError(
            "RGR_RED_FAILURE_INVALID",
            f"failure command {failure.command!r} != run command {command!r}",
        )
    if not set(failure.ac_refs) & set(patch.ac_refs):
        raise RedGateError(
            "RGR_RED_TRACE_MISSING",
            f"failure AC refs {failure.ac_refs} do not match patch AC refs {patch.ac_refs}",
        )
    return failure


def evaluate_red_gate(
    *,
    patch: RedPatch,
    failure: FailureFingerprint | None,
    command: str,
) -> RedGateResult:
    """Evaluate the Red program gate (AC-FR0500-01).

    Args:
        patch: The :class:`RedPatch` observed by Runtime.
        failure: The :class:`FailureFingerprint` from running the test
            command, or ``None`` if the tests unexpectedly passed.
        command: The exact test command that was run.

    Returns:
        A :class:`RedGateResult` with ``status=pass`` and the validated
        fingerprint on success.

    Raises:
        RedGateError: With a stable code from :data:`ERROR_CODES` for any
            invalid Red diff or failure category.
    """
    _check_patch(patch)
    fingerprint = _check_failure(failure, patch, command)
    return RedGateResult(
        status="pass",
        failure_fingerprint=fingerprint,
        command=command,
        ac_refs=patch.ac_refs,
    )
