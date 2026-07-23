"""Integration tests for FR-0500: Red program gate.

AC-FR0500-01: A legitimate behaviour-assertion failure or a precise
"designed but missing symbol" compile/type failure fixture can both
pass the Red gate, and the diff contains only the current AC's tests.
Product code changes, test weakening, unrelated syntax errors,
dependency/fixture/env/permission failures, missing AC trace, or fake
test fixtures are all rejected with the baseline preserved.

Interfaces covered (per interfaces.md):
- IF-RGR-01 (Primary ARC-05)
- IF-TASK-01 (manifest scope alignment, ARC-04)
"""
# AC-FR0500-01

from __future__ import annotations

import pytest

from louke.runtime.red_program_gate import (
    ERROR_CODES,
    FailureFingerprint,
    RedGateError,
    RedGateResult,
    RedPatch,
    evaluate_red_gate,
)


def _valid_patch() -> RedPatch:
    return RedPatch(
        diff_paths=("tests/unit/test_fr0100.py",),
        product_code_changed=False,
        test_weakened=False,
        ac_refs=("AC-FR0100-01",),
        has_anti_pattern=False,
        syntax_valid=True,
        secret_detected=False,
        static_check_passed=True,
        format_passed=True,
    )


def _valid_failure(category: str = "assertion") -> FailureFingerprint:
    return FailureFingerprint(
        category=category,  # type: ignore[arg-type]
        command="pytest -q tests/unit/test_fr0100.py",
        ac_refs=("AC-FR0100-01",),
        assertion_identity="tests/unit/test_fr0100.py::test_x",
        output_digest="sha256:output",
    )


_VALID_COMMAND = "pytest -q tests/unit/test_fr0100.py"


# ---------------------------------------------------------------------------
# Valid Red: behaviour assertion failure & missing-symbol failure
# ---------------------------------------------------------------------------


@pytest.mark.real_module
def test_red_gate_passes_on_assertion_failure():
    """AC-FR0500-01: legitimate assertion failure passes Red gate."""
    result = evaluate_red_gate(
        patch=_valid_patch(),
        failure=_valid_failure("assertion"),
        command=_VALID_COMMAND,
    )
    assert isinstance(result, RedGateResult)
    assert result.status == "pass"
    assert result.failure_fingerprint is not None
    assert result.failure_fingerprint.category == "assertion"
    assert result.ac_refs == ("AC-FR0100-01",)
    assert result.command == _VALID_COMMAND


@pytest.mark.real_module
def test_red_gate_passes_on_missing_symbol_failure():
    """AC-FR0500-01: precise missing-symbol compile/type failure passes Red."""
    result = evaluate_red_gate(
        patch=_valid_patch(),
        failure=_valid_failure("missing-symbol"),
        command=_VALID_COMMAND,
    )
    assert result.status == "pass"
    # AC-FR0500-01: missing-symbol failure carries a valid fingerprint.
    assert result.failure_fingerprint
    assert result.failure_fingerprint.category == "missing-symbol"


# ---------------------------------------------------------------------------
# Invalid Red: each forbidden condition
# ---------------------------------------------------------------------------


@pytest.mark.real_module
def test_red_gate_rejects_product_code_change():
    """AC-FR0500-01: product code in diff -> RGR_RED_NOT_TEST_ONLY."""
    p = _valid_patch()
    p = RedPatch(
        diff_paths=p.diff_paths,
        product_code_changed=True,
        test_weakened=p.test_weakened,
        ac_refs=p.ac_refs,
        has_anti_pattern=p.has_anti_pattern,
        syntax_valid=p.syntax_valid,
        secret_detected=p.secret_detected,
        static_check_passed=p.static_check_passed,
        format_passed=p.format_passed,
    )
    with pytest.raises(RedGateError) as exc:
        evaluate_red_gate(patch=p, failure=_valid_failure(), command=_VALID_COMMAND)
    assert exc.value.code == "RGR_RED_NOT_TEST_ONLY"


@pytest.mark.real_module
def test_red_gate_rejects_test_weakening():
    """AC-FR0500-01: weakening existing assertions -> RGR_TEST_MUTATED."""
    p = _valid_patch()
    p = RedPatch(
        diff_paths=p.diff_paths,
        product_code_changed=False,
        test_weakened=True,
        ac_refs=p.ac_refs,
        has_anti_pattern=p.has_anti_pattern,
        syntax_valid=p.syntax_valid,
        secret_detected=p.secret_detected,
        static_check_passed=p.static_check_passed,
        format_passed=p.format_passed,
    )
    with pytest.raises(RedGateError) as exc:
        evaluate_red_gate(patch=p, failure=_valid_failure(), command=_VALID_COMMAND)
    assert exc.value.code == "RGR_TEST_MUTATED"


@pytest.mark.real_module
def test_red_gate_rejects_missing_ac_trace():
    """AC-FR0500-01: diff without AC anchor -> RGR_RED_TRACE_MISSING."""
    p = RedPatch(
        diff_paths=("tests/unit/test_fr0100.py",),
        product_code_changed=False,
        test_weakened=False,
        ac_refs=(),  # no AC trace
        has_anti_pattern=False,
        syntax_valid=True,
        secret_detected=False,
        static_check_passed=True,
        format_passed=True,
    )
    with pytest.raises(RedGateError) as exc:
        evaluate_red_gate(patch=p, failure=_valid_failure(), command=_VALID_COMMAND)
    assert exc.value.code == "RGR_RED_TRACE_MISSING"


@pytest.mark.real_module
def test_red_gate_rejects_unexpected_pass():
    """AC-FR0500-01: tests unexpectedly pass -> RGR_RED_UNEXPECTED_PASS."""
    with pytest.raises(RedGateError) as exc:
        evaluate_red_gate(
            patch=_valid_patch(),
            failure=None,
            command=_VALID_COMMAND,
        )
    assert exc.value.code == "RGR_RED_UNEXPECTED_PASS"


@pytest.mark.real_module
def test_red_gate_rejects_environment_failure_category():
    """AC-FR0500-01: environment failure -> RGR_RED_FAILURE_INVALID."""
    with pytest.raises(RedGateError) as exc:
        evaluate_red_gate(
            patch=_valid_patch(),
            failure=_valid_failure("environment"),
            command=_VALID_COMMAND,
        )
    assert exc.value.code == "RGR_RED_FAILURE_INVALID"


@pytest.mark.real_module
def test_red_gate_rejects_fixture_failure_category():
    """AC-FR0500-01: fixture failure -> RGR_RED_FAILURE_INVALID."""
    with pytest.raises(RedGateError) as exc:
        evaluate_red_gate(
            patch=_valid_patch(),
            failure=_valid_failure("fixture"),
            command=_VALID_COMMAND,
        )
    assert exc.value.code == "RGR_RED_FAILURE_INVALID"


@pytest.mark.real_module
def test_red_gate_rejects_permission_failure_category():
    """AC-FR0500-01: permission failure -> RGR_RED_FAILURE_INVALID."""
    with pytest.raises(RedGateError) as exc:
        evaluate_red_gate(
            patch=_valid_patch(),
            failure=_valid_failure("permission"),
            command=_VALID_COMMAND,
        )
    assert exc.value.code == "RGR_RED_FAILURE_INVALID"


@pytest.mark.real_module
def test_red_gate_rejects_dependency_failure_category():
    """AC-FR0500-01: dependency failure -> RGR_RED_FAILURE_INVALID."""
    with pytest.raises(RedGateError) as exc:
        evaluate_red_gate(
            patch=_valid_patch(),
            failure=_valid_failure("dependency"),
            command=_VALID_COMMAND,
        )
    assert exc.value.code == "RGR_RED_FAILURE_INVALID"


@pytest.mark.real_module
def test_red_gate_rejects_unrelated_failure_category():
    """AC-FR0500-01: unrelated failure -> RGR_RED_FAILURE_INVALID."""
    with pytest.raises(RedGateError) as exc:
        evaluate_red_gate(
            patch=_valid_patch(),
            failure=_valid_failure("unrelated"),
            command=_VALID_COMMAND,
        )
    assert exc.value.code == "RGR_RED_FAILURE_INVALID"


@pytest.mark.real_module
def test_red_gate_rejects_command_mismatch():
    """AC-FR0500-01: failure command must equal run command."""
    bad = FailureFingerprint(
        category="assertion",
        command="pytest -q something-else",
        ac_refs=("AC-FR0100-01",),
        assertion_identity="x",
        output_digest="sha256:x",
    )
    with pytest.raises(RedGateError) as exc:
        evaluate_red_gate(
            patch=_valid_patch(),
            failure=bad,
            command=_VALID_COMMAND,
        )
    assert exc.value.code == "RGR_RED_FAILURE_INVALID"


@pytest.mark.real_module
def test_red_gate_rejects_ac_mismatch_between_patch_and_failure():
    """AC-FR0500-01: failure AC refs must intersect patch AC refs."""
    bad = FailureFingerprint(
        category="assertion",
        command=_VALID_COMMAND,
        ac_refs=("AC-FR9999-99",),  # disjoint from patch AC refs
        assertion_identity="x",
        output_digest="sha256:x",
    )
    with pytest.raises(RedGateError) as exc:
        evaluate_red_gate(
            patch=_valid_patch(),
            failure=bad,
            command=_VALID_COMMAND,
        )
    assert exc.value.code == "RGR_RED_TRACE_MISSING"


@pytest.mark.real_module
def test_red_gate_rejects_anti_pattern_in_patch():
    """AC-FR0500-01: anti-pattern detected -> RGR_RED_FAILURE_INVALID."""
    p = RedPatch(
        diff_paths=("tests/unit/test_fr0100.py",),
        product_code_changed=False,
        test_weakened=False,
        ac_refs=("AC-FR0100-01",),
        has_anti_pattern=True,  # FAKE-* pattern
        syntax_valid=True,
        secret_detected=False,
        static_check_passed=True,
        format_passed=True,
    )
    with pytest.raises(RedGateError) as exc:
        evaluate_red_gate(patch=p, failure=_valid_failure(), command=_VALID_COMMAND)
    assert exc.value.code == "RGR_RED_FAILURE_INVALID"


@pytest.mark.real_module
def test_red_gate_rejects_secret_in_patch():
    """AC-FR0500-01: secret detected -> RGR_RED_FAILURE_INVALID."""
    p = RedPatch(
        diff_paths=("tests/unit/test_fr0100.py",),
        product_code_changed=False,
        test_weakened=False,
        ac_refs=("AC-FR0100-01",),
        has_anti_pattern=False,
        syntax_valid=True,
        secret_detected=True,  # secret canary
        static_check_passed=True,
        format_passed=True,
    )
    with pytest.raises(RedGateError) as exc:
        evaluate_red_gate(patch=p, failure=_valid_failure(), command=_VALID_COMMAND)
    assert exc.value.code == "RGR_RED_FAILURE_INVALID"


@pytest.mark.real_module
def test_error_codes_set_covers_all_documented_codes():
    """AC-FR0500-01: ERROR_CODES includes all codes from interfaces.md §4."""
    expected = {
        "RGR_RED_NOT_TEST_ONLY",
        "RGR_RED_UNEXPECTED_PASS",
        "RGR_RED_FAILURE_INVALID",
        "RGR_RED_TRACE_MISSING",
        "RGR_TEST_MUTATED",
    }
    actual = set(ERROR_CODES)
    missing = expected - actual
    assert not missing, f"ERROR_CODES missing: {missing}"
