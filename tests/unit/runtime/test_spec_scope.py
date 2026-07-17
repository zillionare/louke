"""Tests for the Runtime pre-Lex Spec scope gate."""

from __future__ import annotations

from louke.runtime.program_steps import StepContext
from louke.runtime.spec_scope import (
    NEEDS_STORY_SPLIT,
    SCOPE_TOO_LARGE,
    WITHIN_LIMIT,
    evaluate_spec_scope,
    spec_scope_check_handler,
)


def _spec(active: int, deprecated: int = 0, nfr: int = 0) -> str:
    lines = ["# Spec", "", "## Functional Requirements", ""]
    for index in range(1, active + 1):
        lines.extend(_unit("FR", index, "✅"))
    for index in range(active + 1, active + deprecated + 1):
        lines.extend(_unit("FR", index, "❌"))
    if nfr:
        lines.extend(["## Non-Functional Requirements", ""])
    for index in range(1, nfr + 1):
        lines.extend(_unit("NFR", index, "✅"))
    return "\n".join(lines)


def _unit(kind: str, number: int, valid: str) -> list[str]:
    return [
        f"### {kind}-{number:04d} Requirement {number}",
        "| Valid | Testable | Decided |",
        "|---|---|---|",
        f"| {valid} | ✅ | ✅ |",
        "",
    ]


def _context() -> StepContext:
    return StepContext(
        run_id="run-1",
        step_id="spec-scope-check",
        attempt_id="attempt-1",
        workspace="/workspace",
        idempotency_key="scope-1",
    )


def test_exactly_30_active_requirements_pass() -> None:
    evaluation = evaluate_spec_scope(_spec(30))
    assert evaluation.within_limit
    assert evaluation.active_count == 30


def test_fr_and_nfr_share_one_spec_limit() -> None:
    evaluation = evaluate_spec_scope(_spec(20, nfr=11))
    assert not evaluation.within_limit
    assert evaluation.active_count == 31


def test_deprecated_requirements_do_not_count() -> None:
    evaluation = evaluate_spec_scope(_spec(30, deprecated=5))
    assert evaluation.within_limit
    assert evaluation.active_count == 30
    assert evaluation.deprecated_count == 5


def test_missing_metadata_remains_active() -> None:
    text = "# Spec\n\n## Functional Requirements\n\n### FR-0001 No metadata\n"
    evaluation = evaluate_spec_scope(text)
    assert evaluation.active_count == 1


def test_chinese_valid_column_is_supported() -> None:
    text = "\n".join(
        [
            "# Spec",
            "## Functional Requirements",
            "### FR-0001 Deprecated",
            "| 有效需求 | 可测性 | 是否已决定 |",
            "|---|---|---|",
            "| ❌ | ✅ | ✅ |",
        ]
    )
    evaluation = evaluate_spec_scope(text)
    assert evaluation.active_count == 0
    assert evaluation.deprecated_count == 1


def test_handler_returns_pre_lex_story_split_result() -> None:
    handler = spec_scope_check_handler(lambda _context: _spec(31))
    result = handler(_context())
    assert result.result == NEEDS_STORY_SPLIT
    assert result.output["error_code"] == SCOPE_TOO_LARGE
    assert result.output["return_target"] == "M-STORY"
    assert result.output["waivable"] is False


def test_handler_allows_lex_dispatch_at_limit() -> None:
    handler = spec_scope_check_handler(lambda _context: _spec(30))
    result = handler(_context())
    assert result.result == WITHIN_LIMIT
    assert result.output["active_requirements"] == 30
