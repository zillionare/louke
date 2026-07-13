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
    StaleGateError,
    UnauthenticatedPrincipalError,
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


def test_ac_fr0501_02_valid_principal_approval_advances_run():
    """AC-FR0501-02: matching approval records evidence and transitions."""
    store, orchestrator, gate_service, run = _create_fixtures()
    gate = gate_service.ensure_gate(
        run_id=run.run_id,
        step_id="m_lock",
        bound_digest="sha256:abc123",
    )

    outcome = orchestrator.apply_gate_decision(
        run_id=run.run_id,
        gate_id=gate.gate_id,
        decision="approve",
        bound_digest="sha256:abc123",
        expected_revision=run.revision,
        principal={"kind": "human", "id": "alice"},
    )

    assert outcome.run.current_step == "design"
    assert outcome.run.revision == 1
    assert outcome.run.status == "completed"

    approved_gate = store.get_gate(gate.gate_id)
    assert approved_gate.status == "approved"
    assert approved_gate.actor_id == "alice"
    assert approved_gate.bound_digest == "sha256:abc123"

    events = store.get_events(run.run_id)
    assert any(event.type == "gate.approved" for event in events)
    transition_events = [event for event in events if event.type == "step.transition"]
    assert len(transition_events) == 1
    assert transition_events[0].to_step == "design"
    assert transition_events[0].actor == {"kind": "human", "id": "alice"}


def test_ac_fr0501_03_free_text_approved_by_rejected_without_principal():
    """AC-FR0501-03: a free-text approved_by string cannot replace a host principal."""
    _store, orchestrator, gate_service, run = _create_fixtures()
    gate = gate_service.ensure_gate(
        run_id=run.run_id,
        step_id="m_lock",
        bound_digest="sha256:abc123",
    )

    with pytest.raises(UnauthenticatedPrincipalError):
        orchestrator.apply_gate_decision(
            run_id=run.run_id,
            gate_id=gate.gate_id,
            decision="approve",
            bound_digest="sha256:abc123",
            expected_revision=run.revision,
            principal={"approved_by": "mallory"},
        )

    after = orchestrator._store.get_run(run.run_id)
    assert after.current_step == "m_lock"
    assert after.revision == run.revision
    assert after.status == "waiting_for_human"

    pending_gate = orchestrator._store.get_gate(gate.gate_id)
    assert pending_gate.status == "waiting_for_human"


def test_ac_fr0501_04_stale_revision_step_or_digest_rejected():
    """AC-FR0501-04: stale revision, step or digest returns stale-gate error."""
    store, orchestrator, gate_service, run = _create_fixtures()
    gate = gate_service.ensure_gate(
        run_id=run.run_id,
        step_id="m_lock",
        bound_digest="sha256:abc123",
    )

    with pytest.raises(StaleGateError):
        orchestrator.apply_gate_decision(
            run_id=run.run_id,
            gate_id=gate.gate_id,
            decision="approve",
            bound_digest="sha256:abc123",
            expected_revision=run.revision + 1,
            principal={"kind": "human", "id": "alice"},
        )

    with pytest.raises(StaleGateError):
        orchestrator.apply_gate_decision(
            run_id=run.run_id,
            gate_id=gate.gate_id,
            decision="approve",
            bound_digest="sha256:wrong",
            expected_revision=run.revision,
            principal={"kind": "human", "id": "alice"},
        )

    store.update_run(
        run.with_step(current_step="design", status="in_progress"), run.revision
    )
    with pytest.raises(StaleGateError):
        orchestrator.apply_gate_decision(
            run_id=run.run_id,
            gate_id=gate.gate_id,
            decision="approve",
            bound_digest="sha256:abc123",
            expected_revision=run.revision + 1,
            principal={"kind": "human", "id": "alice"},
        )

    final = store.get_run(run.run_id)
    assert final.current_step != "rework"


def test_ac_fr0501_05_artifact_change_after_approval_invalidates_old_decision():
    """AC-FR0501-05: changed artifact digest invalidates an approved gate."""
    store, orchestrator, gate_service, run = _create_fixtures()
    gate = gate_service.ensure_gate(
        run_id=run.run_id,
        step_id="m_lock",
        bound_digest="sha256:abc123",
    )
    orchestrator.apply_gate_decision(
        run_id=run.run_id,
        gate_id=gate.gate_id,
        decision="approve",
        bound_digest="sha256:abc123",
        expected_revision=run.revision,
        principal={"kind": "human", "id": "alice"},
    )
    approved_gate = store.get_gate(gate.gate_id)
    assert approved_gate.status == "approved"

    new_gate = gate_service.ensure_gate(
        run_id=run.run_id,
        step_id="m_lock",
        bound_digest="sha256:def456",
    )

    assert new_gate.gate_id == gate.gate_id
    assert new_gate.status == "waiting_for_human"
    assert new_gate.bound_digest == "sha256:def456"
    assert new_gate.challenge_id != gate.challenge_id

    with pytest.raises(StaleGateError):
        orchestrator.apply_gate_decision(
            run_id=run.run_id,
            gate_id=gate.gate_id,
            decision="approve",
            bound_digest="sha256:abc123",
            expected_revision=store.get_run(run.run_id).revision,
            principal={"kind": "human", "id": "alice"},
        )
