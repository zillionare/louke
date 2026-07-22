"""FR-0901: design document review and M-LOCK.

AC references:
- AC-FR0901-01: only when requirements approval is valid can design tasks start
  and be accepted; invalid requirements approval rejects the same requests.
- AC-FR0901-02: after design docs complete validation/review/user review,
  Runtime creates an M-LOCK gate bound to the common contract digest of the
  approved requirements documents and the current design documents.
- AC-FR0901-03: M-LOCK not approved => no implementation task, session,
  worktree or commit can be created or started.
- AC-FR0901-04: human principal approves M-LOCK => run enters the
  implementation phase along the ``approved`` edge with full approval evidence.
- AC-FR0901-05: M-LOCK approved but implementation not started => any bound
  document changes => old approval becomes stale, Runtime returns to the
  upstream step per workflow rules, and no implementation task is silently
  created.
"""

from __future__ import annotations

import pytest

from louke.runtime.catalog import DefinitionRegistry, Edge, Step, WorkflowDefinition
from louke.runtime.contract_gates import (
    contract_digest,
)
from louke.runtime.domain import RuntimeCommand
from louke.runtime.gates import (
    GATE_APPROVED,
    GATE_WAITING,
    GateNotApprovedError,
    GateService,
    StaleGateError,
)
from louke.runtime.orchestrator import WorkflowOrchestrator
from louke.runtime.store import WorkflowRunStore


# -- Definition helpers -------------------------------------------------------


def _full_workflow_definition() -> WorkflowDefinition:
    """Return a definition: requirements_approval -> design -> m_lock -> implementation.

    The design step is a ``program`` step that produces design documents.
    The M-LOCK step is a ``human_gate`` that gates the implementation step.
    The implementation step is a ``semantic_task`` (agent dispatch).
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
        implemented=True,
    )
    design = Step(
        step_id="design",
        kind="program",
        transitions=(
            Edge(
                edge_id="e_design_done",
                from_step="design",
                to_step="m_lock",
                condition="done",
            ),
        ),
        implemented=True,
    )
    m_lock = Step(
        step_id="m_lock",
        kind="human_gate",
        transitions=(
            Edge(
                edge_id="e_mlock_approved",
                from_step="m_lock",
                to_step="implementation",
                condition="approved",
            ),
            Edge(
                edge_id="e_mlock_rejected",
                from_step="m_lock",
                to_step="design",
                condition="rejected",
            ),
        ),
        implemented=True,
    )
    implementation = Step(
        step_id="implementation",
        kind="semantic_task",
        capability="agent_task",
        transitions=(
            Edge(
                edge_id="e_impl_done",
                from_step="implementation",
                to_step="archive",
                condition="done",
            ),
        ),
        implemented=True,
    )
    archive = Step(step_id="archive", kind="program", implemented=True)
    review = Step(step_id="requirements_review", kind="program", implemented=True)
    return WorkflowDefinition(
        definition_id="fr0901",
        version="1",
        start_step="requirements_approval",
        steps=(req_gate, design, m_lock, implementation, archive, review),
    )


def _create_fixtures() -> tuple[
    WorkflowRunStore, WorkflowOrchestrator, GateService, object
]:
    """Create a store, orchestrator and gate service for a fresh run."""
    registry = DefinitionRegistry()
    definition = registry.register(_full_workflow_definition())
    store = WorkflowRunStore(catalog=registry)
    gate_service = GateService(store)
    orchestrator = WorkflowOrchestrator(store, gate_service=gate_service)
    run = store.create_run(definition)
    return store, orchestrator, gate_service, run


_REQ_DIGESTS = {
    "story": "sha256:story_v1",
    "spec": "sha256:spec_v1",
    "acceptance": "sha256:acceptance_v1",
}

_DESIGN_DIGESTS = {
    "test_plan": "sha256:test_plan_v1",
    "architecture": "sha256:architecture_v1",
    "interfaces": "sha256:interfaces_v1",
}


def _req_contract_digest() -> str:
    return contract_digest(_REQ_DIGESTS)


def _m_lock_contract_digest() -> str:
    return contract_digest({**_REQ_DIGESTS, **_DESIGN_DIGESTS})


def _approve_requirements(
    store: WorkflowRunStore,
    orchestrator: WorkflowOrchestrator,
    run: object,
) -> None:
    """Approve the requirements gate and advance the run to design."""
    orchestrator.ensure_requirements_gate(
        run_id=run.run_id,
        story_digest=_REQ_DIGESTS["story"],
        spec_digest=_REQ_DIGESTS["spec"],
        acceptance_digest=_REQ_DIGESTS["acceptance"],
    )
    orchestrator.apply_gate_decision(
        run_id=run.run_id,
        gate_id=store.get_gate_for_run_step(
            run.run_id, "requirements_approval"
        ).gate_id,
        decision="approve",
        bound_digest=_req_contract_digest(),
        expected_revision=run.revision,
        principal={"kind": "human", "id": "alice"},
    )


def _advance_to_m_lock(
    store: WorkflowRunStore,
    orchestrator: WorkflowOrchestrator,
    run: object,
) -> None:
    """Approve requirements then transition design -> m_lock."""
    _approve_requirements(store, orchestrator, run)
    design_run = store.get_run(run.run_id)
    orchestrator.apply_command(
        RuntimeCommand(
            run_id=run.run_id,
            expected_revision=design_run.revision,
            result="done",
        )
    )


# -- AC-FR0901-01 -------------------------------------------------------------


def test_ac_fr0901_01_design_tasks_blocked_without_requirements_approval():
    """AC-FR0901-01: design tasks are rejected when requirements approval is invalid.

    After the run is created (positioned at ``requirements_approval``),
    requesting a transition to ``design`` without an approved requirements
    gate must be rejected. No design artifact or step attempt is accepted.
    """
    store, orchestrator, _gate_service, run = _create_fixtures()

    with pytest.raises(GateNotApprovedError):
        orchestrator.check_requirements_approval(run.run_id)

    command = RuntimeCommand(
        run_id=run.run_id,
        expected_revision=run.revision,
        result="approved",
    )
    with pytest.raises(GateNotApprovedError):
        orchestrator.apply_command(command)

    persisted_run = store.get_run(run.run_id)
    assert persisted_run.current_step == "requirements_approval"

    design_attempts = [
        attempt
        for attempt in store.get_step_attempts(run.run_id)
        if attempt.step_id == "design"
    ]
    assert len(design_attempts) == 0


def test_ac_fr0901_01_design_tasks_allowed_with_requirements_approval():
    """AC-FR0901-01: design tasks can start when requirements approval is valid."""
    store, orchestrator, _gate_service, run = _create_fixtures()
    _approve_requirements(store, orchestrator, run)

    persisted_run = store.get_run(run.run_id)
    assert persisted_run.current_step == "design"
    assert persisted_run.status == "in_progress"


# -- AC-FR0901-02 -------------------------------------------------------------


def test_ac_fr0901_02_m_lock_gate_created_with_combined_digest():
    """AC-FR0901-02: M-LOCK gate binds approved requirements + design docs.

    After the run reaches the M-LOCK step, calling ``ensure_m_lock_gate``
    with the requirements and design document digests must create a gate
    whose ``bound_digest`` is the common contract digest of all six
    documents. The gate must be in ``waiting_for_human`` status.
    """
    store, orchestrator, _gate_service, run = _create_fixtures()
    _advance_to_m_lock(store, orchestrator, run)

    gate = orchestrator.ensure_m_lock_gate(
        run_id=run.run_id,
        story_digest=_REQ_DIGESTS["story"],
        spec_digest=_REQ_DIGESTS["spec"],
        acceptance_digest=_REQ_DIGESTS["acceptance"],
        test_plan_digest=_DESIGN_DIGESTS["test_plan"],
        architecture_digest=_DESIGN_DIGESTS["architecture"],
        interfaces_digest=_DESIGN_DIGESTS["interfaces"],
    )

    assert gate.step_id == "m_lock"
    assert gate.status == GATE_WAITING
    expected = _m_lock_contract_digest()
    assert gate.bound_digest == expected

    persisted = store.get_gate(gate.gate_id)
    assert persisted.bound_digest == expected

    events = store.get_events(run.run_id)
    assert any(event.type == "gate.created" for event in events)


# -- AC-FR0901-03 -------------------------------------------------------------


def test_ac_fr0901_03_implementation_blocked_without_m_lock():
    """AC-FR0901-03: implementation tasks are rejected without M-LOCK approval.

    When the run is at the M-LOCK step and no approval has been recorded,
    any attempt to transition into the implementation step must be rejected.
    No implementation step attempt is recorded.
    """
    store, orchestrator, _gate_service, run = _create_fixtures()
    _advance_to_m_lock(store, orchestrator, run)
    orchestrator.ensure_m_lock_gate(
        run_id=run.run_id,
        story_digest=_REQ_DIGESTS["story"],
        spec_digest=_REQ_DIGESTS["spec"],
        acceptance_digest=_REQ_DIGESTS["acceptance"],
        test_plan_digest=_DESIGN_DIGESTS["test_plan"],
        architecture_digest=_DESIGN_DIGESTS["architecture"],
        interfaces_digest=_DESIGN_DIGESTS["interfaces"],
    )

    with pytest.raises(GateNotApprovedError):
        orchestrator.check_m_lock_approval(run.run_id)

    m_lock_run = store.get_run(run.run_id)
    command = RuntimeCommand(
        run_id=run.run_id,
        expected_revision=m_lock_run.revision,
        result="approved",
    )
    with pytest.raises(GateNotApprovedError):
        orchestrator.apply_command(command)

    persisted_run = store.get_run(run.run_id)
    assert persisted_run.current_step == "m_lock"

    impl_attempts = [
        attempt
        for attempt in store.get_step_attempts(run.run_id)
        if attempt.step_id == "implementation"
    ]
    assert len(impl_attempts) == 0


# -- AC-FR0901-04 -------------------------------------------------------------


def test_ac_fr0901_04_m_lock_approval_enters_implementation():
    """AC-FR0901-04: valid M-LOCK approval enters the implementation phase.

    When a human principal approves the M-LOCK gate with the matching
    bound digest and revision, the run must transition along the
    ``approved`` edge into the implementation step. The approval event and
    the transition event must both be recorded.
    """
    store, orchestrator, _gate_service, run = _create_fixtures()
    _advance_to_m_lock(store, orchestrator, run)
    bound_digest = _m_lock_contract_digest()
    orchestrator.ensure_m_lock_gate(
        run_id=run.run_id,
        story_digest=_REQ_DIGESTS["story"],
        spec_digest=_REQ_DIGESTS["spec"],
        acceptance_digest=_REQ_DIGESTS["acceptance"],
        test_plan_digest=_DESIGN_DIGESTS["test_plan"],
        architecture_digest=_DESIGN_DIGESTS["architecture"],
        interfaces_digest=_DESIGN_DIGESTS["interfaces"],
    )

    m_lock_run = store.get_run(run.run_id)
    outcome = orchestrator.apply_gate_decision(
        run_id=run.run_id,
        gate_id=store.get_gate_for_run_step(run.run_id, "m_lock").gate_id,
        decision="approve",
        bound_digest=bound_digest,
        expected_revision=m_lock_run.revision,
        principal={"kind": "human", "id": "alice"},
    )

    assert outcome.run.current_step == "implementation"
    assert outcome.run.status == "in_progress"

    persisted_gate = store.get_gate_for_run_step(run.run_id, "m_lock")
    assert persisted_gate.status == GATE_APPROVED
    assert persisted_gate.actor_id == "alice"

    events = store.get_events(run.run_id)
    assert any(event.type == "gate.approved" for event in events)
    impl_transitions = [
        event
        for event in events
        if event.type == "step.transition" and event.to_step == "implementation"
    ]
    assert len(impl_transitions) == 1


# -- AC-FR0901-05 -------------------------------------------------------------


def test_ac_fr0901_05_bound_doc_change_invalidates_m_lock():
    """AC-FR0901-05: changing a bound document after M-LOCK makes approval stale.

    After the M-LOCK gate is approved (but before implementation starts),
    changing any bound design document produces a new contract digest.
    Calling ``ensure_m_lock_gate`` with the new digests must invalidate the
    prior approval and bind the gate to the new digest. ``check_m_lock_approval``
    must then fail because the old approval is no longer valid.
    """
    store, orchestrator, _gate_service, run = _create_fixtures()
    _advance_to_m_lock(store, orchestrator, run)
    original_digest = _m_lock_contract_digest()
    orchestrator.ensure_m_lock_gate(
        run_id=run.run_id,
        story_digest=_REQ_DIGESTS["story"],
        spec_digest=_REQ_DIGESTS["spec"],
        acceptance_digest=_REQ_DIGESTS["acceptance"],
        test_plan_digest=_DESIGN_DIGESTS["test_plan"],
        architecture_digest=_DESIGN_DIGESTS["architecture"],
        interfaces_digest=_DESIGN_DIGESTS["interfaces"],
    )

    m_lock_run = store.get_run(run.run_id)
    orchestrator.apply_gate_decision(
        run_id=run.run_id,
        gate_id=store.get_gate_for_run_step(run.run_id, "m_lock").gate_id,
        decision="approve",
        bound_digest=original_digest,
        expected_revision=m_lock_run.revision,
        principal={"kind": "human", "id": "alice"},
    )

    approved_before = store.get_gate_for_run_step(run.run_id, "m_lock")
    assert approved_before.status == GATE_APPROVED

    new_gate = orchestrator.ensure_m_lock_gate(
        run_id=run.run_id,
        story_digest=_REQ_DIGESTS["story"],
        spec_digest=_REQ_DIGESTS["spec"],
        acceptance_digest=_REQ_DIGESTS["acceptance"],
        test_plan_digest="sha256:test_plan_v2",
        architecture_digest=_DESIGN_DIGESTS["architecture"],
        interfaces_digest=_DESIGN_DIGESTS["interfaces"],
    )

    new_digest = contract_digest(
        {
            **_REQ_DIGESTS,
            "test_plan": "sha256:test_plan_v2",
            "architecture": _DESIGN_DIGESTS["architecture"],
            "interfaces": _DESIGN_DIGESTS["interfaces"],
        }
    )
    assert new_gate.bound_digest == new_digest
    assert new_digest != original_digest

    with pytest.raises((StaleGateError, GateNotApprovedError)):
        orchestrator.check_m_lock_approval(run.run_id)

    events = store.get_events(run.run_id)
    stale_events = [event for event in events if event.type == "gate.stale"]
    assert len(stale_events) == 1
    assert stale_events[0].details["bound_digest"] == original_digest

    impl_attempts = [
        attempt
        for attempt in store.get_step_attempts(run.run_id)
        if attempt.step_id == "implementation"
    ]
    assert len(impl_attempts) == 0
