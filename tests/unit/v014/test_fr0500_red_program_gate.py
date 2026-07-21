"""AC-FR0500-01: Red program gate.

In ``phase=red`` Devon may only add unit/contract tests proving the current
task's missing behaviour.  Runtime must validate test-only diff, format,
test syntax, secret absence, AC trace, anti-pattern scan, and applicable
static checks.  The gate requires a precise behaviour-assertion failure
matching the current requirement/interface, OR a precise compile/type
failure caused by an already-designed-but-unimplemented symbol/interface.
Environment/fixture/permission/dependency/unrelated failures are invalid
Red.
"""

from __future__ import annotations


import pytest

from louke.v014.fr0500_red_program_gate import (
    FailureCategory,
    FailureFingerprint,
    RedGateError,
    RedGateResult,
    RedPatch,
    evaluate_red_gate,
)

_AC = "AC-FR0500-01"
_CMD = ".venv/bin/python3 -m pytest -q tests/unit/v014/test_fr0500_red_program_gate.py"


def _patch(
    *,
    diff_paths: tuple[str, ...] = ("tests/unit/v014/test_x.py",),
    product_code_changed: bool = False,
    test_weakened: bool = False,
    ac_refs: tuple[str, ...] = (_AC,),
    has_anti_pattern: bool = False,
    syntax_valid: bool = True,
    secret_detected: bool = False,
    static_check_passed: bool = True,
    format_passed: bool = True,
) -> RedPatch:
    return RedPatch(
        diff_paths=diff_paths,
        product_code_changed=product_code_changed,
        test_weakened=test_weakened,
        ac_refs=ac_refs,
        has_anti_pattern=has_anti_pattern,
        syntax_valid=syntax_valid,
        secret_detected=secret_detected,
        static_check_passed=static_check_passed,
        format_passed=format_passed,
    )


def _behavior_failure(category: FailureCategory = "assertion") -> FailureFingerprint:
    return FailureFingerprint(
        category=category,
        command=_CMD,
        ac_refs=(_AC,),
        assertion_identity="tests.unit.test_x::test_x_passes",
        output_digest="sha256:" + "f" * 64,
    )


def test_red_gate_passes_for_precise_behavior_assertion_failure() -> None:
    """AC-FR0500-01: a precise behavior assertion failure passes the Red gate."""
    result = evaluate_red_gate(
        patch=_patch(),
        failure=_behavior_failure(category="assertion"),
        command=_CMD,
    )
    assert isinstance(result, RedGateResult)
    assert result.status == "pass"
    assert result.failure_fingerprint is not None
    assert result.failure_fingerprint.category == "assertion"


def test_red_gate_passes_for_designed_but_missing_symbol() -> None:
    """AC-FR0500-01: a precise compile/type failure for a designed-but-missing symbol passes."""
    result = evaluate_red_gate(
        patch=_patch(),
        failure=_behavior_failure(category="missing-symbol"),
        command=_CMD,
    )
    assert result.status == "pass"
    assert result.failure_fingerprint.category == "missing-symbol"


def test_red_gate_rejects_product_code_change() -> None:
    """AC-FR0500-01: Red with product code change is rejected."""
    with pytest.raises(RedGateError) as exc:
        evaluate_red_gate(
            patch=_patch(product_code_changed=True),
            failure=_behavior_failure(),
            command=_CMD,
        )
    assert exc.value.code == "RGR_RED_NOT_TEST_ONLY"


def test_red_gate_rejects_test_weakening() -> None:
    """AC-FR0500-01: weakening existing tests is rejected."""
    with pytest.raises(RedGateError) as exc:
        evaluate_red_gate(
            patch=_patch(test_weakened=True), failure=_behavior_failure(), command=_CMD
        )
    assert exc.value.code == "RGR_TEST_MUTATED"


def test_red_gate_rejects_missing_ac_trace() -> None:
    """AC-FR0500-01: missing AC trace in diff is rejected."""
    with pytest.raises(RedGateError) as exc:
        evaluate_red_gate(
            patch=_patch(ac_refs=()), failure=_behavior_failure(), command=_CMD
        )
    assert exc.value.code == "RGR_RED_TRACE_MISSING"


def test_red_gate_rejects_anti_pattern() -> None:
    """AC-FR0500-01: anti-pattern in test diff is rejected."""
    with pytest.raises(RedGateError) as exc:
        evaluate_red_gate(
            patch=_patch(has_anti_pattern=True),
            failure=_behavior_failure(),
            command=_CMD,
        )
    assert exc.value.code == "RGR_RED_FAILURE_INVALID"


def test_red_gate_rejects_syntax_error() -> None:
    """AC-FR0500-01: invalid syntax is rejected as invalid Red."""
    with pytest.raises(RedGateError) as exc:
        evaluate_red_gate(
            patch=_patch(syntax_valid=False), failure=_behavior_failure(), command=_CMD
        )
    assert exc.value.code == "RGR_RED_FAILURE_INVALID"


def test_red_gate_rejects_secret_in_diff() -> None:
    """AC-FR0500-01: secret in diff is rejected."""
    with pytest.raises(RedGateError) as exc:
        evaluate_red_gate(
            patch=_patch(secret_detected=True),
            failure=_behavior_failure(),
            command=_CMD,
        )
    assert exc.value.code == "RGR_RED_FAILURE_INVALID"


def test_red_gate_rejects_static_check_failure() -> None:
    """AC-FR0500-01: static check failure is rejected."""
    with pytest.raises(RedGateError) as exc:
        evaluate_red_gate(
            patch=_patch(static_check_passed=False),
            failure=_behavior_failure(),
            command=_CMD,
        )
    assert exc.value.code == "RGR_RED_FAILURE_INVALID"


def test_red_gate_rejects_format_failure() -> None:
    """AC-FR0500-01: format failure is rejected."""
    with pytest.raises(RedGateError) as exc:
        evaluate_red_gate(
            patch=_patch(format_passed=False), failure=_behavior_failure(), command=_CMD
        )
    assert exc.value.code == "RGR_RED_FAILURE_INVALID"


def test_red_gate_rejects_unexpected_pass() -> None:
    """AC-FR0500-01: an unexpected test PASS is rejected (no real failure)."""
    with pytest.raises(RedGateError) as exc:
        evaluate_red_gate(patch=_patch(), failure=None, command=_CMD)
    assert exc.value.code == "RGR_RED_UNEXPECTED_PASS"


def test_red_gate_rejects_environment_failure_category() -> None:
    """AC-FR0500-01: environment/fixture/permission failure category is invalid Red."""
    for category in ("environment", "fixture", "permission", "dependency", "unrelated"):
        with pytest.raises(RedGateError) as exc:
            evaluate_red_gate(
                patch=_patch(),
                failure=_behavior_failure(category=category),  # type: ignore[arg-type]
                command=_CMD,
            )
        assert exc.value.code == "RGR_RED_FAILURE_INVALID"


def test_red_gate_rejects_failure_with_no_ac_match() -> None:
    """AC-FR0500-01: a failure whose AC doesn't match the patch is invalid Red."""
    mismatch = FailureFingerprint(
        category="assertion",
        command=_CMD,
        ac_refs=("AC-FR9999-99",),
        assertion_identity="tests.unit.test_x::test_y",
        output_digest="sha256:" + "g" * 64,
    )
    with pytest.raises(RedGateError) as exc:
        evaluate_red_gate(patch=_patch(), failure=mismatch, command=_CMD)
    assert exc.value.code == "RGR_RED_TRACE_MISSING"
