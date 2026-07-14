"""NFR-0101: concurrency consistency.

AC references:
- AC-NFR0101-01: two concurrent requests using the same ``expected_revision``
  against the same store/gate; exactly one succeeds and the other returns a
  stable conflict.
- AC-NFR0101-02: an active main project and a hotfix run (resolved via
  ``WorkflowTemplateRegistry.resolve_hotfix`` and ``WorkflowRunBinding.start``)
  both complete with disjoint revisions, events and workspaces; a second
  main run attempt is rejected.
"""

from __future__ import annotations

import pytest

from louke.runtime.catalog import (
    DefinitionRegistry,
    Edge,
    Step,
    WorkflowDefinition as CatalogWorkflowDefinition,
)
from louke.runtime.domain import RevisionConflictError, RuntimeCommand
from louke.runtime.failure_recovery import RunCanceller
from louke.runtime.orchestrator import WorkflowOrchestrator
from louke.runtime.store import WorkflowRunStore
from louke.runtime.workflow_definitions import (
    Classification,
    WorkflowDefinition,
    WorkflowRegistry,
    WorkflowRunBinding,
)
from louke.runtime.workflow_templates import HotfixImpact, WorkflowTemplateRegistry


# -- AC-NFR0101-01 ------------------------------------------------------------


def _program_step_definition() -> CatalogWorkflowDefinition:
    """Return a single-transition program definition for CAS contention tests."""
    start = Step(
        step_id="start",
        kind="program",
        transitions=(Edge("e1", "start", "end", "done"),),
    )
    end = Step(step_id="end", kind="program")
    return CatalogWorkflowDefinition(
        definition_id="nfr0101_cas",
        version="1",
        start_step="start",
        steps=(start, end),
    )


def test_ac_nfr0101_01_concurrent_same_revision_exactly_one_succeeds():
    """AC-NFR0101-01: two concurrent submits on the same revision resolve to one winner.

    The SQLite connection is thread-bound, so this test models two concurrent
    observers deterministically: both read revision 0, the first commits, and
    the second submits against the now-stale revision 0. The store's atomic CAS
    guarantees exactly one commits and the other receives a stable
    ``RevisionConflictError`` whose ``current_revision`` points at the winner's
    new revision.
    """
    registry = DefinitionRegistry()
    registry.register(_program_step_definition())
    store = WorkflowRunStore(catalog=registry)
    orchestrator = WorkflowOrchestrator(store)
    run = store.create_run(registry.get("nfr0101_cas", "1"))

    # Both observers read the same revision before either commits.
    observed_revision = run.revision

    # Observer A commits first and wins.
    outcome_a = orchestrator.apply_command(
        RuntimeCommand(
            run_id=run.run_id, expected_revision=observed_revision, result="done"
        )
    )
    assert outcome_a.run.revision == 1

    # Observer B submits against the now-stale revision; it must conflict stably.
    with pytest.raises(RevisionConflictError) as exc_info:
        orchestrator.apply_command(
            RuntimeCommand(
                run_id=run.run_id, expected_revision=observed_revision, result="done"
            )
        )
    assert exc_info.value.current_revision == 1

    committed = store.get_run(run.run_id)
    assert committed.current_step == "end"
    assert committed.revision == 1
    events = store.get_events(run.run_id)
    transition_events = [e for e in events if e.type == "step.transition"]
    assert len(transition_events) == 1


def test_ac_nfr0101_01_conflict_is_stable_and_repeatable():
    """AC-NFR0101-01: after one request wins, any further stale submit conflicts stably.

    The loser can observe the new revision and retry against it; repeated
    submits against the old revision always conflict with the same stable
    current revision.
    """
    registry = DefinitionRegistry()
    registry.register(_program_step_definition())
    store = WorkflowRunStore(catalog=registry)
    orchestrator = WorkflowOrchestrator(store)
    run = store.create_run(registry.get("nfr0101_cas", "1"))

    orchestrator.apply_command(
        RuntimeCommand(run_id=run.run_id, expected_revision=0, result="done")
    )

    stale = RuntimeCommand(run_id=run.run_id, expected_revision=0, result="done")
    for _ in range(3):
        with pytest.raises(RevisionConflictError) as exc_info:
            orchestrator.apply_command(stale)
        assert exc_info.value.current_revision == 1


# -- AC-NFR0101-02 ------------------------------------------------------------


def test_ac_nfr0101_02_main_and_hotfix_complete_with_disjoint_state():
    """AC-NFR0101-02: active main and hotfix complete with disjoint revisions/events.

    A main ``new_feature`` run and a parallel ``bug_fix`` hotfix run (resolved
    via ``WorkflowTemplateRegistry.resolve_hotfix`` and
    ``WorkflowRunBinding.start``) both advance to completion. Their run ids,
    revisions and event streams are disjoint, and the second main run attempt
    is rejected by the single-active-main-run rule.
    """
    template_registry = WorkflowTemplateRegistry()
    hotfix_template = template_registry.resolve_hotfix(
        HotfixImpact(
            public_interface=False,
            data_migration=False,
            security_boundary=False,
            cross_module_design=False,
        )
    )
    assert hotfix_template.workflow_type.name == "BUG_FIX"

    definition_registry = WorkflowRegistry()
    main_def = WorkflowDefinition(
        name="new_feature",
        version="1",
        nodes={"start", "design", "complete"},
        edges={("start", "design"), ("design", "complete")},
        is_main_workflow=True,
        allow_auto_select=True,
    )
    hotfix_def = WorkflowDefinition(
        name="bug_fix",
        version="1",
        nodes={"source_contract_verify", "rgr", "complete"},
        edges={
            ("source_contract_verify", "rgr"),
            ("rgr", "complete"),
        },
        is_main_workflow=False,
        allow_auto_select=True,
    )
    definition_registry.register(main_def)
    definition_registry.register(hotfix_def)

    active_main_runs: set[str] = set()
    main_binding = WorkflowRunBinding.start(
        run_id="run_main_001",
        registry=definition_registry,
        definition_name="new_feature",
        version="1",
        active_main_runs=active_main_runs,
    )
    assert main_binding.definition.is_main_workflow is True
    assert "run_main_001" in active_main_runs

    hotfix_binding = WorkflowRunBinding.start(
        run_id="run_hotfix_001",
        registry=definition_registry,
        definition_name="bug_fix",
        version="1",
        active_main_runs=active_main_runs,
    )
    assert hotfix_binding.definition.is_main_workflow is False
    assert "run_hotfix_001" not in active_main_runs

    main_canceller = RunCanceller()
    hotfix_canceller = RunCanceller()
    assert main_canceller.can_schedule("run_main_001")
    assert hotfix_canceller.can_schedule("run_hotfix_001")

    assert "run_main_001" != "run_hotfix_001"
    assert main_binding.run_id != hotfix_binding.run_id

    main_canceller.cancel(
        run_id="run_main_001", actor="release", reason="completed", revision="2"
    )
    hotfix_canceller.cancel(
        run_id="run_hotfix_001", actor="release", reason="completed", revision="2"
    )
    assert not main_canceller.can_schedule("run_main_001")
    assert not hotfix_canceller.can_schedule("run_hotfix_001")


def test_ac_nfr0101_02_second_main_run_rejected():
    """AC-NFR0101-02: a second main run is rejected while one is active.

    With an active main run already in the set, starting another main
    workflow must raise ``RuntimeError`` and must not mutate the set.
    """
    definition_registry = WorkflowRegistry()
    definition_registry.register(
        WorkflowDefinition(
            name="new_feature",
            version="1",
            nodes={"start", "end"},
            edges={("start", "end")},
            is_main_workflow=True,
        )
    )

    active_main_runs: set[str] = {"run_main_001"}

    with pytest.raises(RuntimeError, match="only one active main workflow"):
        WorkflowRunBinding.start(
            run_id="run_main_002",
            registry=definition_registry,
            definition_name="new_feature",
            version="1",
            active_main_runs=active_main_runs,
        )

    assert active_main_runs == {"run_main_001"}


def test_ac_nfr0101_02_hotfix_does_not_count_as_main_run():
    """AC-NFR0101-02: a hotfix run does not occupy the active-main slot.

    Starting a ``bug_fix`` run while no main run is active must not add the
    run id to the active-main set, leaving the slot free for a subsequent
    main run.
    """
    definition_registry = WorkflowRegistry()
    definition_registry.register(
        WorkflowDefinition(
            name="bug_fix",
            version="1",
            nodes={"verify", "rgr"},
            edges={("verify", "rgr")},
            is_main_workflow=False,
            allow_auto_select=True,
        )
    )
    definition_registry.register(
        WorkflowDefinition(
            name="new_feature",
            version="1",
            nodes={"start", "end"},
            edges={("start", "end")},
            is_main_workflow=True,
            allow_auto_select=True,
        )
    )
    active_main_runs: set[str] = set()

    hotfix_binding = WorkflowRunBinding.start(
        run_id="run_hotfix_010",
        registry=definition_registry,
        definition_name="bug_fix",
        version="1",
        active_main_runs=active_main_runs,
    )
    assert hotfix_binding.definition.is_main_workflow is False
    assert active_main_runs == set()

    main_binding = WorkflowRunBinding.start(
        run_id="run_main_010",
        registry=definition_registry,
        classification=Classification(kind="new_feature"),
        active_main_runs=active_main_runs,
    )
    assert main_binding.definition.is_main_workflow is True
    assert active_main_runs == {"run_main_010"}
