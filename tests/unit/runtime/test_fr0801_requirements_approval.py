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


from louke.runtime.catalog import DefinitionRegistry, Edge, Step, WorkflowDefinition
from louke.runtime.contract_gates import contract_digest
from louke.runtime.gates import GateService
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
