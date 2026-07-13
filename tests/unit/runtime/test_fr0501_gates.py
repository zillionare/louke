"""FR-0501: Unbypassable human gate system.

AC references:
- AC-FR0501-01: reaching a human gate without a decision leaves the run
  ``waiting_for_human`` and blocks resume or subsequent-step requests.
- AC-FR0501-02: an authenticated human principal approves with a matching
  challenge, revision and artifact digest, recording evidence and performing
  the ``approved`` transition.
- AC-FR0501-03: a request containing an arbitrary ``approved_by`` string but
  no host-authenticated human principal is rejected and the gate stays pending.
- AC-FR0501-04: stale challenge, revision, step or artifact digest returns a
  stale-gate/state-conflict error without advancing.
- AC-FR0501-05: after approval, a change to a bound artifact before the next
  allowed step invalidates the old approval and re-enters ``waiting_for_human``
  bound to the new digest.
- AC-FR0501-06: a valid human principal rejection prevents subsequent steps
  and records actor, time, reason and rejected digest for audit.
"""

from __future__ import annotations

import pytest

from louke.runtime.catalog import DefinitionRegistry, Edge, Step, WorkflowDefinition
from louke.runtime.domain import RuntimeCommand
from louke.runtime.gates import (
    GateNotApprovedError,
    GateService,
)
from louke.runtime.orchestrator import WorkflowOrchestrator
from louke.runtime.store import WorkflowRunStore


def _human_gate_definition() -> WorkflowDefinition:
    """Return a minimal definition whose start step is a human gate."""
    lock = Step(
        step_id="m_lock",
        kind="human_gate",
        transitions=(
            Edge(
                edge_id="e_approved",
                from_step="m_lock",
                to_step="design",
                condition="approved",
            ),
            Edge(
                edge_id="e_rejected",
                from_step="m_lock",
                to_step="rework",
                condition="rejected",
            ),
        ),
    )
    design = Step(step_id="design", kind="program")
    rework = Step(step_id="rework", kind="program")
    return WorkflowDefinition(
        definition_id="fr0501",
        version="1",
        start_step="m_lock",
        steps=(lock, design, rework),
    )


def _create_fixtures() -> tuple[
    WorkflowRunStore, WorkflowOrchestrator, GateService, object
]:
    """Create a store, orchestrator and gate service for a fresh run."""
    registry = DefinitionRegistry()
    definition = registry.register(_human_gate_definition())
    store = WorkflowRunStore(catalog=registry)
    gate_service = GateService(store)
    orchestrator = WorkflowOrchestrator(store, gate_service=gate_service)
    run = store.create_run(definition)
    return store, orchestrator, gate_service, run


def test_ac_fr0501_01_run_blocks_at_human_gate_without_decision():
    """AC-FR0501-01: no decision at a human gate keeps the run blocked."""
    store, orchestrator, _gate_service, run = _create_fixtures()

    fetched = store.get_run(run.run_id)
    assert fetched.status == "waiting_for_human"
    assert fetched.current_step == "m_lock"

    resume = RuntimeCommand(
        run_id=run.run_id,
        expected_revision=run.revision,
        result="approved",
    )
    with pytest.raises(GateNotApprovedError):
        orchestrator.apply_command(resume)

    after = store.get_run(run.run_id)
    assert after.current_step == "m_lock"
    assert after.revision == run.revision
    assert after.status == "waiting_for_human"
