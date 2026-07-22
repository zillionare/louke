"""FR-0001: versioned workflow definition validation.

AC references:
- AC-FR0001-01: invalid definitions return stable, locatable validation errors
  for unknown step, dangling transition, duplicate step/edge ID,
  unreachable required step and unsupported step type.
"""

from louke.runtime.catalog import (
    Edge,
    Step,
    WorkflowDefinition,
    DefinitionValidationError,
    derive_status,
    validate_definition,
)


def _edge(edge_id: str, from_step: str, to_step: str, condition: str = "") -> Edge:
    return Edge(
        edge_id=edge_id, from_step=from_step, to_step=to_step, condition=condition
    )


def _step(
    step_id: str,
    kind: str,
    required: bool = True,
    transitions: tuple[Edge, ...] = (),
) -> Step:
    return Step(
        step_id=step_id,
        kind=kind,
        required=required,
        transitions=transitions,
    )


def test_ac_fr0001_01_definition_validation_returns_locatable_error():
    """AC-FR0001-01: each invalid definition yields a stable, locatable validation error."""
    cases = [
        (
            "unknown_step",
            WorkflowDefinition(
                definition_id="test",
                version="1",
                start_step="missing",
                steps=(_step("start", "program"),),
            ),
            "unknown_step",
            {"step_id": "missing"},
        ),
        (
            "dangling_transition",
            WorkflowDefinition(
                definition_id="test",
                version="1",
                start_step="start",
                steps=(
                    _step(
                        "start",
                        "program",
                        transitions=(_edge("e1", "start", "missing"),),
                    ),
                ),
            ),
            "dangling_transition",
            {"step_id": "missing", "edge_id": "e1"},
        ),
        (
            "duplicate_step_id",
            WorkflowDefinition(
                definition_id="test",
                version="1",
                start_step="a",
                steps=(
                    _step("a", "program"),
                    _step("a", "human_gate"),
                ),
            ),
            "duplicate_step_id",
            {"step_id": "a"},
        ),
        (
            "duplicate_edge_id",
            WorkflowDefinition(
                definition_id="test",
                version="1",
                start_step="start",
                steps=(
                    _step(
                        "start",
                        "decision",
                        transitions=(
                            _edge("same", "start", "a", condition="x"),
                            _edge("same", "start", "b", condition="y"),
                        ),
                    ),
                    _step("a", "program"),
                    _step("b", "program"),
                ),
            ),
            "duplicate_edge_id",
            {"edge_id": "same"},
        ),
        (
            "unreachable_required_step",
            WorkflowDefinition(
                definition_id="test",
                version="1",
                start_step="start",
                steps=(
                    _step(
                        "start",
                        "program",
                        transitions=(_edge("e1", "start", "a"),),
                    ),
                    _step("a", "program"),
                    _step("b", "program", required=True),
                ),
            ),
            "unreachable_required_step",
            {"step_id": "b"},
        ),
        (
            "unsupported_step_type",
            WorkflowDefinition(
                definition_id="test",
                version="1",
                start_step="start",
                steps=(_step("start", "shell"),),
            ),
            "unsupported_step_type",
            {"step_id": "start"},
        ),
    ]

    for name, definition, expected_code, expected_locator in cases:
        errors = validate_definition(definition)
        matching = [error for error in errors if error.code == expected_code]
        assert len(matching) == 1, (
            f"{name}: expected exactly one {expected_code} error, got {errors}"
        )
        error = matching[0]
        assert isinstance(error, DefinitionValidationError)
        for attr, expected_value in expected_locator.items():
            assert getattr(error, attr) == expected_value, (
                f"{name}: expected {attr}={expected_value}, got {getattr(error, attr)}"
            )


def test_step_without_implemented_field_is_blocked_fail_closed() -> None:
    """An omitted implementation declaration must not expose an executable step."""
    definition = WorkflowDefinition(
        definition_id="unimplemented",
        version="1",
        start_step="start",
        steps=(Step(step_id="start", kind="program"),),
    )

    assert Step(step_id="start", kind="program").implemented is False
    assert derive_status("start", definition) == "blocked"
