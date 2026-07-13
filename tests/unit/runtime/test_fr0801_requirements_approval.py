"""FR-0801: requirements document human approval gate.

AC references:
- AC-FR0801-01: reaching the requirements approval step creates a gate bound
  to the combined digest of story, spec and acceptance.
- AC-FR0801-02: design tasks are rejected while requirements approval is
  pending or rejected, and no design artifact is accepted.
- AC-FR0801-03: valid approval only enters the design phase; implementation
  steps remain blocked.
- AC-FR0801-04: changing any bound requirement document invalidates the prior
  approval and rebinds the gate to the new digest.
- AC-FR0801-05: rejection returns the run to requirements authoring/review with
  a recorded reason and audit evidence.
- AC-FR0801-06: bug_fix runs inherit an existing source requirements approval
  when the fix only corrects implementation deviation; otherwise the quick
  path is rejected.
"""

from __future__ import annotations

import pytest

from louke.runtime.catalog import DefinitionRegistry, Edge, Step, WorkflowDefinition
from louke.runtime.contract_gates import contract_digest
from louke.runtime.domain import RuntimeCommand
from louke.runtime.gates import (
    GateNotApprovedError,
    GateService,
    StaleGateError,
)
from louke.runtime.orchestrator import WorkflowOrchestrator
from louke.runtime.store import WorkflowRunStore


def _requirements_approval_definition() -> WorkflowDefinition:
    """Return a definition with a requirements approval gate before design."""
    req_gate = Step(
        step_id="requirements_approval",
        kind="human_gate",
        transitions=(
            Edge(
                edge_id="e_req_approved",
                from_step="requirements_approval",
                to_step="design",
                condition="approved",
            ),
            Edge(
                edge_id="e_req_rejected",
                from_step="requirements_approval",
                to_step="requirements_review",
                condition="rejected",
            ),
        ),
    )
    design = Step(step_id="design", kind="program")
    review = Step(step_id="requirements_review", kind="program")
    return WorkflowDefinition(
        definition_id="fr0801",
        version="1",
        start_step="requirements_approval",
        steps=(req_gate, design, review),
    )


def _create_fixtures() -> tuple[
    WorkflowRunStore, WorkflowOrchestrator, GateService, object
]:
    """Create a store, orchestrator and gate service for a fresh run."""
    registry = DefinitionRegistry()
    definition = registry.register(_requirements_approval_definition())
    store = WorkflowRunStore(catalog=registry)
    gate_service = GateService(store)
    orchestrator = WorkflowOrchestrator(store, gate_service=gate_service)
    run = store.create_run(definition)
    return store, orchestrator, gate_service, run


def test_ac_fr0801_01_requirements_gate_created_with_bound_digest():
    """AC-FR0801-01: reaching requirements approval creates a bound gate."""
    store, orchestrator, _gate_service, run = _create_fixtures()

    gate = orchestrator.ensure_requirements_gate(
        run_id=run.run_id,
        story_digest="sha256:story_v1",
        spec_digest="sha256:spec_v1",
        acceptance_digest="sha256:acceptance_v1",
    )

    assert gate.step_id == "requirements_approval"
    assert gate.status == "waiting_for_human"
    expected_digest = contract_digest(
        {
            "story": "sha256:story_v1",
            "spec": "sha256:spec_v1",
            "acceptance": "sha256:acceptance_v1",
        }
    )
    assert gate.bound_digest == expected_digest

    persisted = store.get_gate(gate.gate_id)
    assert persisted.bound_digest == expected_digest

    events = store.get_events(run.run_id)
    assert any(event.type == "gate.created" for event in events)


def test_ac_fr0801_02_design_tasks_rejected_when_pending_or_rejected():
    """AC-FR0801-02: design tasks are rejected without requirements approval."""
    store, orchestrator, gate_service, run = _create_fixtures()
    gate_service.ensure_gate(
        run_id=run.run_id,
        step_id="requirements_approval",
        bound_digest=contract_digest(
            {
                "story": "sha256:story_v1",
                "spec": "sha256:spec_v1",
                "acceptance": "sha256:acceptance_v1",
            }
        ),
    )

    with pytest.raises(GateNotApprovedError):
        orchestrator.check_requirements_approval(run.run_id)

    orchestrator.apply_gate_decision(
        run_id=run.run_id,
        gate_id=store.get_gate_for_run_step(
            run.run_id, "requirements_approval"
        ).gate_id,
        decision="reject",
        bound_digest=contract_digest(
            {
                "story": "sha256:story_v1",
                "spec": "sha256:spec_v1",
                "acceptance": "sha256:acceptance_v1",
            }
        ),
        expected_revision=run.revision,
        principal={"kind": "human", "id": "bob"},
        reason="requirements unclear",
    )

    with pytest.raises(GateNotApprovedError):
        orchestrator.check_requirements_approval(run.run_id)

    design_attempts = [
        attempt
        for attempt in store.get_step_attempts(run.run_id)
        if attempt.step_id == "design"
    ]
    assert len(design_attempts) == 0


def _requirements_approval_with_implementation_definition() -> WorkflowDefinition:
    """Return a definition that goes design -> implementation after requirements approval.

    The implementation step is a ``semantic_task`` (an agent dispatch) that must
    remain blocked until M-LOCK is approved, even though the definition declares
    a ``design -> implementation`` edge.
    """
    req_gate = Step(
        step_id="requirements_approval",
        kind="human_gate",
        transitions=(
            Edge(
                edge_id="e_req_approved",
                from_step="requirements_approval",
                to_step="design",
                condition="approved",
            ),
            Edge(
                edge_id="e_req_rejected",
                from_step="requirements_approval",
                to_step="requirements_review",
                condition="rejected",
            ),
        ),
    )
    design = Step(
        step_id="design",
        kind="program",
        transitions=(
            Edge(
                edge_id="e_design_done",
                from_step="design",
                to_step="implementation",
                condition="done",
            ),
        ),
    )
    implementation = Step(
        step_id="implementation",
        kind="semantic_task",
        capability="agent_task",
    )
    review = Step(step_id="requirements_review", kind="program")
    return WorkflowDefinition(
        definition_id="fr0801_ac3",
        version="1",
        start_step="requirements_approval",
        steps=(req_gate, design, implementation, review),
    )


def _create_ac3_fixtures() -> tuple[
    WorkflowRunStore, WorkflowOrchestrator, GateService, object
]:
    """Create fixtures for AC-3 with a design -> implementation edge."""
    registry = DefinitionRegistry()
    definition = registry.register(
        _requirements_approval_with_implementation_definition()
    )
    store = WorkflowRunStore(catalog=registry)
    gate_service = GateService(store)
    orchestrator = WorkflowOrchestrator(store, gate_service=gate_service)
    run = store.create_run(definition)
    return store, orchestrator, gate_service, run


def test_ac_fr0801_03_approval_unlocks_design_only():
    """AC-FR0801-03: valid approval enters design but implementation stays blocked.

    After a human principal approves the current requirements digest, the run
    may transition into the design step (a ``program`` step that produces and
    reviews design documents). However, attempting to transition from design to
    the implementation step (a ``semantic_task`` / agent dispatch) must be
    rejected, because M-LOCK has not been approved yet. The declared
    ``design -> implementation`` edge does not override the M-LOCK requirement.
    """
    store, orchestrator, _gate_service, run = _create_ac3_fixtures()

    bound_digest = contract_digest(
        {
            "story": "sha256:story_v1",
            "spec": "sha256:spec_v1",
            "acceptance": "sha256:acceptance_v1",
        }
    )
    orchestrator.ensure_requirements_gate(
        run_id=run.run_id,
        story_digest="sha256:story_v1",
        spec_digest="sha256:spec_v1",
        acceptance_digest="sha256:acceptance_v1",
    )

    approval_outcome = orchestrator.apply_gate_decision(
        run_id=run.run_id,
        gate_id=store.get_gate_for_run_step(
            run.run_id, "requirements_approval"
        ).gate_id,
        decision="approve",
        bound_digest=bound_digest,
        expected_revision=run.revision,
        principal={"kind": "human", "id": "alice"},
    )

    assert approval_outcome.run.current_step == "design"
    assert approval_outcome.run.status == "in_progress"

    design_run = store.get_run(run.run_id)
    implementation_command = RuntimeCommand(
        run_id=run.run_id,
        expected_revision=design_run.revision,
        result="done",
    )

    with pytest.raises(GateNotApprovedError):
        orchestrator.apply_command(implementation_command)

    blocked_run = store.get_run(run.run_id)
    assert blocked_run.current_step == "design"
    assert blocked_run.revision == design_run.revision

    events = store.get_events(run.run_id)
    assert any(event.type == "gate.approved" for event in events)
    design_transitions = [
        event
        for event in events
        if event.type == "step.transition" and event.to_step == "design"
    ]
    assert len(design_transitions) == 1
    implementation_transitions = [
        event
        for event in events
        if event.type == "step.transition" and event.to_step == "implementation"
    ]
    assert len(implementation_transitions) == 0


def test_ac_fr0801_04_rebind_on_doc_change():
    """AC-FR0801-04: changing a bound requirement document invalidates the prior approval.

    After the requirements gate is approved for the combined digest of story,
    spec and acceptance, changing any one of the three documents produces a new
    combined digest. Calling ``ensure_gate`` with the new digests must mark the
    prior approval as stale (so the design flow cannot continue on the old
    approval) and bind the gate to the new digest. ``check_approval`` must then
    raise a stale-gate / state-conflict error, and the persisted gate must
    carry the new digest.
    """
    store, orchestrator, _gate_service, run = _create_fixtures()

    original_digest = contract_digest(
        {
            "story": "sha256:story_v1",
            "spec": "sha256:spec_v1",
            "acceptance": "sha256:acceptance_v1",
        }
    )
    orchestrator.ensure_requirements_gate(
        run_id=run.run_id,
        story_digest="sha256:story_v1",
        spec_digest="sha256:spec_v1",
        acceptance_digest="sha256:acceptance_v1",
    )
    orchestrator.apply_gate_decision(
        run_id=run.run_id,
        gate_id=store.get_gate_for_run_step(
            run.run_id, "requirements_approval"
        ).gate_id,
        decision="approve",
        bound_digest=original_digest,
        expected_revision=run.revision,
        principal={"kind": "human", "id": "alice"},
    )

    approved_before = store.get_gate_for_run_step(run.run_id, "requirements_approval")
    assert approved_before.status == "approved"
    assert approved_before.bound_digest == original_digest

    new_gate = orchestrator.ensure_requirements_gate(
        run_id=run.run_id,
        story_digest="sha256:story_v2",
        spec_digest="sha256:spec_v1",
        acceptance_digest="sha256:acceptance_v1",
    )

    new_digest = contract_digest(
        {
            "story": "sha256:story_v2",
            "spec": "sha256:spec_v1",
            "acceptance": "sha256:acceptance_v1",
        }
    )
    assert new_gate.bound_digest == new_digest
    assert new_digest != original_digest

    persisted = store.get_gate_for_run_step(run.run_id, "requirements_approval")
    assert persisted.bound_digest == new_digest

    with pytest.raises((StaleGateError, GateNotApprovedError)):
        orchestrator.check_requirements_approval(run.run_id)

    events = store.get_events(run.run_id)
    stale_events = [event for event in events if event.type == "gate.stale"]
    assert len(stale_events) == 1
    stale_event = stale_events[0]
    assert stale_event.details["gate_id"] == approved_before.gate_id
    assert stale_event.details["bound_digest"] == original_digest


def test_ac_fr0801_05_rejection_audit():
    """AC-FR0801-05: rejection returns the run to requirements review with audit.

    When a human principal rejects the requirements gate with a reason, the
    run must return to the requirements authoring/review state, the rejection
    reason and the bound digest must be auditable on the ``gate.rejected``
    event AND on the committed transition event, and no design task may be
    recorded. Linking the reason onto the transition event is required so a
    consumer walking the transition trail can see why the run moved back to
    review without having to correlate separate gate events.
    """
    store, orchestrator, _gate_service, run = _create_fixtures()

    bound_digest = contract_digest(
        {
            "story": "sha256:story_v1",
            "spec": "sha256:spec_v1",
            "acceptance": "sha256:acceptance_v1",
        }
    )
    orchestrator.ensure_requirements_gate(
        run_id=run.run_id,
        story_digest="sha256:story_v1",
        spec_digest="sha256:spec_v1",
        acceptance_digest="sha256:acceptance_v1",
    )

    outcome = orchestrator.apply_gate_decision(
        run_id=run.run_id,
        gate_id=store.get_gate_for_run_step(
            run.run_id, "requirements_approval"
        ).gate_id,
        decision="reject",
        bound_digest=bound_digest,
        expected_revision=run.revision,
        principal={"kind": "human", "id": "bob"},
        reason="unclear",
    )

    assert outcome.run.current_step == "requirements_review"

    persisted_gate = store.get_gate_for_run_step(run.run_id, "requirements_approval")
    assert persisted_gate.status == "rejected"
    assert persisted_gate.reason == "unclear"
    assert persisted_gate.bound_digest == bound_digest
    assert persisted_gate.actor_id == "bob"

    events = store.get_events(run.run_id)

    rejected_events = [event for event in events if event.type == "gate.rejected"]
    assert len(rejected_events) == 1
    rejected_event = rejected_events[0]
    assert rejected_event.details["reason"] == "unclear"
    assert rejected_event.details["bound_digest"] == bound_digest
    assert rejected_event.actor == {"kind": "human", "id": "bob"}

    rejection_transitions = [
        event
        for event in events
        if event.type == "step.transition"
        and event.from_step == "requirements_approval"
        and event.to_step == "requirements_review"
    ]
    assert len(rejection_transitions) == 1
    transition_event = rejection_transitions[0]
    assert transition_event.details["result"] == "rejected"
    assert transition_event.details["reason"] == "unclear"
    assert transition_event.details["bound_digest"] == bound_digest

    design_events = [
        event
        for event in events
        if event.type == "step.transition" and event.to_step == "design"
    ]
    assert len(design_events) == 0

    design_attempts = [
        attempt
        for attempt in store.get_step_attempts(run.run_id)
        if attempt.step_id == "design"
    ]
    assert len(design_attempts) == 0
