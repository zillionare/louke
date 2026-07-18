"""Deterministic pre-Lex scope gate for M-SPEC.

Runtime executes this gate after persisting a Sage draft or revision and before
dispatching Lex. It limits one Spec to 30 active FR units. NFR units are not
part of this product-scope limit. Deprecated FR units remain traceable but do
not count toward the limit.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from louke._tools.quote_parser import (
    COLUMN_ALIASES,
    RE_FENCE,
    RE_TABLE_ROW,
    RE_TABLE_SEP,
    RE_TOP_HEADING,
    RE_UNIT_HEADING,
)
from louke.runtime.program_steps import HandlerResult, StepContext

MAX_ACTIVE_REQUIREMENTS = 30
WITHIN_LIMIT = "within_limit"
NEEDS_STORY_SPLIT = "needs_story_split"
SCOPE_TOO_LARGE = "SPEC_SCOPE_TOO_LARGE"


@dataclass(frozen=True, slots=True)
class SpecScopeEvaluation:
    """Result of counting active requirements in one Spec."""

    active_count: int
    deprecated_count: int
    max_active: int = MAX_ACTIVE_REQUIREMENTS

    @property
    def within_limit(self) -> bool:
        return self.active_count <= self.max_active


@dataclass(slots=True)
class _RequirementUnit:
    requirement_id: str
    valid: str = ""


def evaluate_spec_scope(
    spec_text: str,
    max_active: int = MAX_ACTIVE_REQUIREMENTS,
) -> SpecScopeEvaluation:
    """Count active FR units in ``spec_text``.

    NFR units do not count. An FR is deprecated only when its metadata
    explicitly says ``Valid=❌``. Missing or undecided metadata remains active.
    """

    units = _parse_requirement_units(spec_text)
    deprecated_count = sum(1 for unit in units if unit.valid == "❌")
    return SpecScopeEvaluation(
        active_count=len(units) - deprecated_count,
        deprecated_count=deprecated_count,
        max_active=max_active,
    )


def spec_scope_check_handler(
    load_spec: Callable[[StepContext], str],
    max_active: int = MAX_ACTIVE_REQUIREMENTS,
) -> Callable[[StepContext], HandlerResult]:
    """Return the Runtime handler for the pre-Lex Spec scope check."""

    def handler(context: StepContext) -> HandlerResult:
        evaluation = evaluate_spec_scope(load_spec(context), max_active=max_active)
        output = {
            "active_requirements": evaluation.active_count,
            "deprecated_requirements": evaluation.deprecated_count,
            "max_active_requirements": evaluation.max_active,
            "waivable": False,
        }
        if evaluation.within_limit:
            return HandlerResult(result=WITHIN_LIMIT, output=output)
        return HandlerResult(
            result=NEEDS_STORY_SPLIT,
            output={
                **output,
                "error_code": SCOPE_TOO_LARGE,
                "return_target": "M-STORY",
                "reason": (
                    "Split the Story into smaller independently deliverable "
                    "Stories; each Story/Spec should target its own release."
                ),
            },
        )

    return handler


def _parse_requirement_units(spec_text: str) -> list[_RequirementUnit]:
    units: list[_RequirementUnit] = []
    current_unit: _RequirementUnit | None = None
    in_code_block = False
    table_rows: list[list[str]] = []
    in_table = False
    valid_column: int | None = None

    def reset_table() -> None:
        nonlocal table_rows, in_table, valid_column
        table_rows = []
        in_table = False
        valid_column = None

    for line in spec_text.splitlines():
        if RE_FENCE.match(line):
            in_code_block = not in_code_block
            reset_table()
            continue
        if in_code_block:
            continue

        heading = RE_UNIT_HEADING.match(line)
        if heading:
            kind, number = heading.groups()
            current_unit = None
            reset_table()
            if kind == "FR":
                current_unit = _RequirementUnit(f"{kind}-{number}")
                units.append(current_unit)
            continue

        if RE_TOP_HEADING.match(line):
            current_unit = None
            reset_table()
            continue
        if current_unit is None:
            continue

        row = RE_TABLE_ROW.match(line)
        if row is None:
            if table_rows:
                reset_table()
            continue

        cells = [cell.strip() for cell in row.group(1).split("|")]
        table_rows.append(cells)
        if len(table_rows) == 2 and RE_TABLE_SEP.match(line):
            in_table = True
            for index, column in enumerate(table_rows[0]):
                if COLUMN_ALIASES.get(column) == "valid":
                    valid_column = index
                    break
            continue
        if in_table and len(table_rows) >= 3 and valid_column is not None:
            if valid_column < len(cells) and not current_unit.valid:
                current_unit.valid = cells[valid_column]

    return units
