"""FR-0701 AC-3: capability gating for semantic_task and decision steps."""

import pytest

from louke.runtime.capabilities import (
    CapabilityRegistry,
    UnsupportedCapabilityError,
)
from louke.runtime.catalog import (
    DefinitionInvalidError,
    Edge,
    Step,
    WorkflowDefinition,
    validate_definition,
)
from louke.runtime.store import WorkflowRunStore


def _agent_task_definition() -> WorkflowDefinition:
    start = Step(
        step_id="start",
        kind="semantic_task",
        capability="agent_task",
        transitions=(
            Edge(
                edge_id="e_done",
                from_step="start",
                to_step="end",
                condition="done",
            ),
        ),
    )
    end = Step(step_id="end", kind="program")
    return WorkflowDefinition(
        definition_id="ac_fr0701_agent_task",
        version="1",
        start_step="start",
        steps=(start, end),
    )


def test_ac_fr0701_03_capability_report_lists_agent_task_and_decision_as_supported():
    """AC-FR0701-03: capability report marks agent_task and decision supported."""
    registry = CapabilityRegistry()

    def mock_agent_task(**kwargs) -> dict:
        return {"result": "agent-output", "context": kwargs.get("context")}

    def mock_decision(candidates, **_kwargs) -> dict:
        return {"choice": candidates[0], "reason": "mock decision"}

    registry.register("agent_task", mock_agent_task)
    registry.register("decision", mock_decision)

    report = registry.report()
    assert report["agent_task"].supported is True
    assert report["decision"].supported is True

    agent_result = registry.invoke("agent_task", context={"task": "demo"})
    assert agent_result["result"] == "agent-output"

    decision_result = registry.invoke(
        "decision", candidates=["quick_rgr", "design_required"]
    )
    assert decision_result["choice"] == "quick_rgr"


def test_ac_fr0701_03_unsupported_capability_rejects_definition_without_fake_run(
    tmp_path,
):
    """AC-FR0701-03: unsupported capability is rejected and no run is created."""
    registry = CapabilityRegistry()
    definition = _agent_task_definition()

    errors = validate_definition(definition, capability_registry=registry)
    assert any(
        error.code == "unsupported_capability" and error.step_id == "start"
        for error in errors
    )

    db_path = tmp_path / ".louke" / "runtime" / "state.sqlite3"
    store = WorkflowRunStore(db_path=str(db_path), capabilities=registry)
    with pytest.raises(DefinitionInvalidError):
        store.create_run(definition)

    assert store.list_runs() == ()


def test_ac_fr0701_03_unregistered_capability_cannot_be_invoked():
    """AC-FR0701-03: invoking an unregistered capability raises a clear error."""
    registry = CapabilityRegistry()
    with pytest.raises(UnsupportedCapabilityError):
        registry.invoke("agent_task", context={})
