"""FR-1301: agent-model binding graph and drag-drop override.

AC references:
- AC-FR1301-01: workflow detail shows each agent's effective model,
  distinguishing default binding from run-scoped override.
- AC-FR1301-02: dragging an available model to an agent creates an override
  effective for the next task; unavailable models are rejected.
- AC-FR1301-03: in-flight task keeps its model snapshot; only the next
  not-yet-started task uses the new binding.
- AC-FR1301-04: binding change persists across reload and records actor,
  agent, old/new model, effective boundary and timestamp.
- AC-FR1301-05: new tasks use run override or default model; historical runs
  do not allow new overrides.
"""

from __future__ import annotations

import pytest

from louke.runtime.agent_bindings import (
    BindingModelUnavailableError,
    BindingRevisionConflictError,
    BindingStore,
)
from louke.runtime.catalog import DefinitionRegistry, Edge, Step, WorkflowDefinition
from louke.runtime.store import WorkflowRunStore


# -- Fixtures -----------------------------------------------------------------

_DEFAULT_MODELS: dict[str, str] = {
    "devon": "provider/default-devon",
    "sage": "provider/default-sage",
    "archer": "provider/default-archer",
}

_AVAILABLE_MODELS: frozenset[str] = frozenset(
    {"provider/default-devon", "provider/model-a", "provider/model-b"}
)


def _create_binding_store() -> tuple[WorkflowRunStore, BindingStore]:
    """Create a run store and binding store for tests."""
    registry = DefinitionRegistry()
    definition = registry.register(
        WorkflowDefinition(
            "binding_test",
            "1",
            "start",
            (
                Step(
                    "start",
                    "program",
                    transitions=(Edge("e1", "start", "end", "done"),),
                ),
                Step("end", "program"),
            ),
        )
    )
    run_store = WorkflowRunStore(catalog=registry)
    run_store.create_run(definition)
    binding_store = BindingStore(
        default_models=_DEFAULT_MODELS,
        available_models=_AVAILABLE_MODELS,
    )
    return run_store, binding_store


def _get_run_id(run_store: WorkflowRunStore) -> str:
    """Return the first run id from the store."""
    return run_store.list_runs()[0].run_id


# -- AC-FR1301-01 -------------------------------------------------------------


def test_ac_fr1301_01_effective_model_shows_default_and_override():
    """AC-FR1301-01: binding view shows default and override distinction.

    Without any override, the effective model is the default. After an
    override is set, the view distinguishes the two sources.
    """
    run_store, binding_store = _create_binding_store()
    run_id = _get_run_id(run_store)

    bindings = binding_store.list_bindings(run_id)

    devon_binding = next(b for b in bindings if b.agent_role == "devon")
    assert devon_binding.effective_model == "provider/default-devon"
    assert devon_binding.source == "default"

    binding_store.set_override(
        run_id=run_id,
        agent_role="devon",
        model="provider/model-a",
        actor={"kind": "human", "id": "alice"},
        expected_binding_revision=1,
    )

    bindings_after = binding_store.list_bindings(run_id)
    devon_after = next(b for b in bindings_after if b.agent_role == "devon")
    assert devon_after.effective_model == "provider/model-a"
    assert devon_after.source == "override"


# -- AC-FR1301-02 -------------------------------------------------------------


def test_ac_fr1301_02_available_model_accepted_unavailable_rejected():
    """AC-FR1301-02: available model override succeeds; unavailable rejected.

    Setting an override with an available model succeeds and returns the new
    binding with ``effective_from="next_task"``. An unavailable model is
    rejected and the original binding is unchanged.
    """
    run_store, binding_store = _create_binding_store()
    run_id = _get_run_id(run_store)

    override = binding_store.set_override(
        run_id=run_id,
        agent_role="devon",
        model="provider/model-a",
        actor={"kind": "human", "id": "alice"},
        expected_binding_revision=1,
    )

    assert override.effective_model == "provider/model-a"
    assert override.source == "override"

    with pytest.raises(BindingModelUnavailableError):
        binding_store.set_override(
            run_id=run_id,
            agent_role="devon",
            model="provider/unavailable-model",
            actor={"kind": "human", "id": "alice"},
            expected_binding_revision=override.binding_revision,
        )

    # Original binding unchanged after rejection
    bindings = binding_store.list_bindings(run_id)
    devon = next(b for b in bindings if b.agent_role == "devon")
    assert devon.effective_model == "provider/model-a"


# -- AC-FR1301-03 -------------------------------------------------------------


def test_ac_fr1301_03_in_flight_task_keeps_model():
    """AC-FR1301-03: in-flight task keeps its model snapshot.

    When a task has already started with model A, changing the agent's
    binding to model B does not affect the in-flight task. Only the next
    not-yet-started task uses model B.
    """
    run_store, binding_store = _create_binding_store()
    run_id = _get_run_id(run_store)

    task_manifest = binding_store.resolve_task_model(run_id=run_id, agent_role="devon")
    assert task_manifest.model == "provider/default-devon"
    assert task_manifest.source == "default"

    binding_store.set_override(
        run_id=run_id,
        agent_role="devon",
        model="provider/model-b",
        actor={"kind": "human", "id": "alice"},
        expected_binding_revision=1,
    )

    # In-flight task still uses the old model
    assert task_manifest.model == "provider/default-devon"

    # Next task uses the new override
    next_manifest = binding_store.resolve_task_model(run_id=run_id, agent_role="devon")
    assert next_manifest.model == "provider/model-b"
    assert next_manifest.source == "override"


# -- AC-FR1301-04 -------------------------------------------------------------


def test_ac_fr1301_04_binding_change_persists_and_audited():
    """AC-FR1301-04: binding change persists and records audit event.

    After a successful override, querying bindings again returns the new
    binding. The audit event contains actor, agent, old model, new model,
    effective boundary and timestamp.
    """
    run_store, binding_store = _create_binding_store()
    run_id = _get_run_id(run_store)

    events_before = binding_store.list_binding_events(run_id)
    assert len(events_before) == 0

    binding_store.set_override(
        run_id=run_id,
        agent_role="devon",
        model="provider/model-a",
        actor={"kind": "human", "id": "alice"},
        expected_binding_revision=1,
    )

    events = binding_store.list_binding_events(run_id)
    assert len(events) == 1
    event = events[0]
    assert event.actor == {"kind": "human", "id": "alice"}
    assert event.agent_role == "devon"
    assert event.old_model == "provider/default-devon"
    assert event.new_model == "provider/model-a"
    assert event.effective_from == "next_task"
    assert event.at is not None

    # Persists across "reload" (re-query)
    bindings = binding_store.list_bindings(run_id)
    devon = next(b for b in bindings if b.agent_role == "devon")
    assert devon.effective_model == "provider/model-a"


# -- AC-FR1301-05 -------------------------------------------------------------


def test_ac_fr1301_05_override_or_default_resolved_to_manifest():
    """AC-FR1301-05: new tasks use override or default; source is recorded.

    Without an override, the task manifest uses the default model and
    records ``source="default"``. With an override, it uses the override
    and records ``source="override"``.
    """
    run_store, binding_store = _create_binding_store()
    run_id = _get_run_id(run_store)

    default_manifest = binding_store.resolve_task_model(
        run_id=run_id, agent_role="devon"
    )
    assert default_manifest.model == "provider/default-devon"
    assert default_manifest.source == "default"

    binding_store.set_override(
        run_id=run_id,
        agent_role="devon",
        model="provider/model-a",
        actor={"kind": "human", "id": "alice"},
        expected_binding_revision=1,
    )

    override_manifest = binding_store.resolve_task_model(
        run_id=run_id, agent_role="devon"
    )
    assert override_manifest.model == "provider/model-a"
    assert override_manifest.source == "override"


def test_ac_fr1301_05_historical_run_rejects_new_override():
    """AC-FR1301-05: historical runs do not allow new overrides.

    Once a run is marked read-only (archived), setting a new override
    must be rejected.
    """
    run_store, binding_store = _create_binding_store()
    run_id = _get_run_id(run_store)

    binding_store.mark_run_readonly(run_id)

    with pytest.raises(BindingRevisionConflictError):
        binding_store.set_override(
            run_id=run_id,
            agent_role="devon",
            model="provider/model-a",
            actor={"kind": "human", "id": "alice"},
            expected_binding_revision=1,
        )
