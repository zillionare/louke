"""FR-0301: registered program steps and idempotent execution.

AC references:
- AC-FR0301-01: definitions referencing unregistered handlers or containing
  shell command fields are rejected during validation.
- AC-FR0301-02: registered handlers receive a read-only StepContext and return
  schema-valid results.
- AC-FR0301-03: handler exceptions, timeouts or schema-invalid outputs do not
  mark the attempt successful and expose stable error codes plus diagnostic
  events.
- AC-FR0301-04: replaying a step with an already-completed idempotency key
  does not repeat external side effects.
"""

from louke.runtime.catalog import Edge, Step, WorkflowDefinition, validate_definition


def _step(step_id: str, kind: str, **kwargs) -> Step:
    return Step(step_id=step_id, kind=kind, **kwargs)


def _edge(edge_id: str, from_step: str, to_step: str, condition: str = "") -> Edge:
    return Edge(
        edge_id=edge_id, from_step=from_step, to_step=to_step, condition=condition
    )


def test_ac_fr0301_01_reject_unregistered_handler_and_shell_command():
    """AC-FR0301-01: unregistered handler or shell command fields are rejected."""
    # This import is inside the test so the test file can be collected before
    # the module exists; the failure still points to the missing rule.
    from louke.runtime.program_steps import HandlerRegistry

    registry = HandlerRegistry()
    registry.register("known_handler", lambda _ctx: None)

    unregistered_definition = WorkflowDefinition(
        definition_id="ac_fr0301_01",
        version="1",
        start_step="start",
        steps=(
            _step(
                "start",
                "program",
                handler="unknown_handler",
                transitions=(_edge("e1", "start", "end", condition="done"),),
            ),
            _step("end", "program"),
        ),
    )

    shell_definition = WorkflowDefinition(
        definition_id="ac_fr0301_01_shell",
        version="1",
        start_step="start",
        steps=(
            _step(
                "start",
                "program",
                handler="known_handler",
                shell="echo forbidden",
                transitions=(_edge("e1", "start", "end", condition="done"),),
            ),
            _step("end", "program"),
        ),
    )

    unregistered_errors = validate_definition(
        unregistered_definition, handler_registry=registry
    )
    shell_errors = validate_definition(shell_definition, handler_registry=registry)

    assert any(error.code == "unregistered_handler" for error in unregistered_errors), (
        f"expected unregistered_handler error, got {unregistered_errors}"
    )

    assert any(error.code == "shell_command_forbidden" for error in shell_errors), (
        f"expected shell_command_forbidden error, got {shell_errors}"
    )
