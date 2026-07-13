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

from louke.runtime.catalog import (
    DefinitionRegistry,
    Edge,
    Step,
    WorkflowDefinition,
    validate_definition,
)


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


def test_ac_fr0301_02_handler_receives_read_only_context_and_returns_valid_result(
    tmp_path,
):
    """AC-FR0301-02: registered handlers receive a StepContext and advance the run."""
    from louke.runtime.program_steps import (
        HandlerRegistry,
        HandlerResult,
        ProgramStepExecutor,
        StepContext,
    )
    from louke.runtime.store import WorkflowRunStore

    captured_contexts: list[StepContext] = []

    def sample_handler(ctx: StepContext) -> HandlerResult:
        captured_contexts.append(ctx)
        return HandlerResult(result="done", output={"greeting": "hello"})

    handler_registry = HandlerRegistry()
    handler_registry.register("sample_handler", sample_handler)

    definition_registry = DefinitionRegistry()
    definition = definition_registry.register(
        WorkflowDefinition(
            definition_id="ac_fr0301_02",
            version="1",
            start_step="start",
            steps=(
                _step(
                    "start",
                    "program",
                    handler="sample_handler",
                    transitions=(_edge("e1", "start", "end", condition="done"),),
                ),
                _step("end", "program", handler="sample_handler"),
            ),
        )
    )

    store = WorkflowRunStore(catalog=definition_registry)
    run = store.create_run(definition)

    executor = ProgramStepExecutor(handler_registry)
    workspace = str(tmp_path)
    outcome = executor.execute(
        store=store,
        run_id=run.run_id,
        workspace=workspace,
        idempotency_key="exec-1",
    )

    assert outcome.run.current_step == "end"
    assert outcome.run.status == "completed"
    assert outcome.run.revision == 1

    assert len(captured_contexts) == 1
    ctx = captured_contexts[0]
    assert ctx.run_id == run.run_id
    assert ctx.step_id == "start"
    assert ctx.workspace == workspace
    assert ctx.idempotency_key == "exec-1"
    assert ctx.attempt_id

    attempts = store.get_step_attempts(run.run_id)
    assert len(attempts) == 1
    assert attempts[0].status == "completed"
    assert attempts[0].result == "done"
    assert attempts[0].idempotency_key == "exec-1"

    events = store.get_events(run.run_id)
    transition_events = [event for event in events if event.type == "step.transition"]
    assert len(transition_events) == 1
    assert transition_events[0].to_step == "end"


def test_ac_fr0301_03_handler_exception_records_failure_without_advancing(tmp_path):
    """AC-FR0301-03: handler exceptions do not mark the attempt successful."""
    from louke.runtime.program_steps import (
        HandlerRegistry,
        HandlerResult,
        ProgramStepExecutor,
        StepContext,
    )
    from louke.runtime.store import WorkflowRunStore

    def failing_handler(_ctx: StepContext) -> HandlerResult:
        raise ValueError("something went wrong")

    handler_registry = HandlerRegistry()
    handler_registry.register("failing_handler", failing_handler)

    definition_registry = DefinitionRegistry()
    definition = definition_registry.register(
        WorkflowDefinition(
            definition_id="ac_fr0301_03",
            version="1",
            start_step="start",
            steps=(
                _step(
                    "start",
                    "program",
                    handler="failing_handler",
                    transitions=(_edge("e1", "start", "end", condition="done"),),
                ),
                _step("end", "program", handler="failing_handler"),
            ),
        )
    )

    store = WorkflowRunStore(catalog=definition_registry)
    run = store.create_run(definition)

    executor = ProgramStepExecutor(handler_registry)
    outcome = executor.execute(
        store=store,
        run_id=run.run_id,
        workspace=str(tmp_path),
        idempotency_key="exec-fail",
    )

    assert outcome.run.current_step == "start"
    assert outcome.run.revision == run.revision
    assert outcome.error_code == "handler_exception"

    attempts = store.get_step_attempts(run.run_id)
    assert len(attempts) == 1
    assert attempts[0].status == "failed"
    assert attempts[0].result is None

    events = store.get_events(run.run_id)
    failure_events = [event for event in events if event.type == "step.handler_failed"]
    assert len(failure_events) == 1
    assert failure_events[0].details["error_code"] == "handler_exception"
    assert failure_events[0].details["step_id"] == "start"
    assert failure_events[0].details["idempotency_key"] == "exec-fail"
