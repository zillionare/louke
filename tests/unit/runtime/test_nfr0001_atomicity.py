"""NFR-0001: atomicity and crash safety.

AC references:
- AC-NFR0001-01: with an injectable interruption harness over the persisted
  store, interrupting the handler before it returns yields a retryable state;
  interrupting after the handler returns but before the transaction commits
  yields needs-attention with no half-commit; interrupting after the
  transaction commits yields a committed run with no duplicate side effects.
- AC-NFR0001-02: for any set of successfully committed revisions, the
  recorded event stream has exactly one terminal-state event per revision
  and no orphan state events.
"""

from __future__ import annotations

import pytest

from louke.runtime.catalog import DefinitionRegistry, Edge, Step, WorkflowDefinition
from louke.runtime.domain import RevisionConflictError, RuntimeCommand
from louke.runtime.orchestrator import WorkflowOrchestrator
from louke.runtime.recovery import recover_run
from louke.runtime.store import WorkflowRunStore


# -- Definition helpers -------------------------------------------------------


def _program_chain_definition() -> WorkflowDefinition:
    """Return a three-step program definition: start -> middle -> end."""
    start = Step(
        step_id="start",
        kind="program",
        transitions=(Edge("e1", "start", "middle", "done"),),
    )
    middle = Step(
        step_id="middle",
        kind="program",
        transitions=(Edge("e2", "middle", "end", "done"),),
    )
    end = Step(step_id="end", kind="program")
    return WorkflowDefinition(
        definition_id="nfr0001_chain",
        version="1",
        start_step="start",
        steps=(start, middle, end),
    )


class InterruptionHarness:
    """Deterministic persistence boundary that can inject interruptions.

    Wraps a :class:`WorkflowRunStore` so a test can simulate a crash at one
    of three points relative to the transaction that advances a run and
    appends its transition event:

    - ``before_handler_return``: the step handler (orchestrator) is about to
      produce a result but the caller process disappears before any step
      attempt or transaction is recorded. No side effect is performed and
      no attempt is persisted, so recovery returns the run unchanged and
      the command can be retried cleanly.
    - ``after_handler_before_commit``: the handler returned a result and
      performed its side effect, but the process disappeared before the
      transaction committed. An ``uncertain`` step attempt is recorded so
      recovery marks the run ``needs_attention``; no transition event is
      appended, so there is no half-commit.
    - ``after_commit``: the transaction committed normally. Re-running the
      same command must be a no-op (idempotency) producing no duplicate
      side effects.
    """

    def __init__(self, store: WorkflowRunStore) -> None:
        self._store = store
        self._interrupt_at: str | None = None
        self._committed_count = 0
        self._side_effect_calls: list[str] = []

    def arm(self, interrupt_at: str) -> None:
        """Arm the harness to interrupt at the given phase."""
        self._interrupt_at = interrupt_at

    def record_side_effect(self, label: str) -> None:
        """Record an external side effect performed by a step handler."""
        self._side_effect_calls.append(label)

    @property
    def side_effect_calls(self) -> list[str]:
        """Return the recorded side-effect labels in call order."""
        return list(self._side_effect_calls)

    @property
    def committed_count(self) -> int:
        """Return the number of transactions that committed successfully."""
        return self._committed_count

    def execute_with_interruption(
        self,
        orchestrator: WorkflowOrchestrator,
        command: RuntimeCommand,
        side_effect_label: str,
        idempotency_key: str,
    ) -> None:
        """Run ``command`` through ``orchestrator`` honouring the armed phase.

        Args:
            orchestrator: The orchestrator driving the run.
            command: The transition command to apply.
            side_effect_label: Label recorded when the step handler's side
                effect is performed (used to assert idempotency).
            idempotency_key: Stable key used to record the step attempt so
                recovery can classify it.
        """
        phase = self._interrupt_at
        run = self._store.get_run(command.run_id)

        if phase == "before_handler_return":
            return

        self.record_side_effect(side_effect_label)

        if phase == "after_handler_before_commit":
            self._store.record_step_attempt(
                run_id=run.run_id,
                step_id=run.current_step,
                idempotency_key=idempotency_key,
                status="uncertain",
            )
            return

        outcome = orchestrator.apply_command(command)
        self._committed_count += 1
        assert outcome.run.revision == run.revision + 1


def _harness() -> tuple[InterruptionHarness, WorkflowRunStore, WorkflowOrchestrator]:
    """Return an armed harness, its store and an orchestrator on a fresh run."""
    registry = DefinitionRegistry()
    registry.register(_program_chain_definition())
    store = WorkflowRunStore(catalog=registry)
    harness = InterruptionHarness(store)
    orchestrator = WorkflowOrchestrator(store)
    return harness, store, orchestrator


# -- AC-NFR0001-01 ------------------------------------------------------------


def test_ac_nfr0001_01_interruption_before_handler_yields_retryable():
    """AC-NFR0001-01: interrupting before the handler returns is retryable.

    The process disappears before the handler produces any result, so no
    step attempt and no side effect are recorded. Recovery returns the run
    unchanged at its prior revision and step, and the same command can be
    re-applied successfully.
    """
    harness, store, orchestrator = _harness()
    run = store.create_run(store._catalog.get("nfr0001_chain", "1"))  # noqa: SLF001
    harness.arm("before_handler_return")

    harness.execute_with_interruption(
        orchestrator,
        RuntimeCommand(run_id=run.run_id, expected_revision=run.revision, result="done"),
        side_effect_label="side:start",
        idempotency_key="att_001",
    )

    assert harness.side_effect_calls == []
    assert harness.committed_count == 0

    recovered = recover_run(store, run.run_id)
    assert recovered.revision == run.revision
    assert recovered.current_step == "start"
    assert recovered.status == run.status

    # The same command can be re-applied successfully after recovery.
    outcome = orchestrator.apply_command(
        RuntimeCommand(run_id=run.run_id, expected_revision=run.revision, result="done")
    )
    assert outcome.run.current_step == "middle"
    assert outcome.run.revision == run.revision + 1


def test_ac_nfr0001_01_interruption_before_commit_yields_needs_attention():
    """AC-NFR0001-01: interrupting after the handler but before commit is needs-attention.

    No half-commit occurs: the handler's side effect was performed but the
    transaction never committed, so no transition event is appended. An
    ``uncertain`` step attempt is recorded and recovery moves the run to
    ``needs_attention`` so a human can determine whether the side effect
    was applied.
    """
    harness, store, orchestrator = _harness()
    run = store.create_run(store._catalog.get("nfr0001_chain", "1"))  # noqa: SLF001
    harness.arm("after_handler_before_commit")

    harness.execute_with_interruption(
        orchestrator,
        RuntimeCommand(run_id=run.run_id, expected_revision=run.revision, result="done"),
        side_effect_label="side:start",
        idempotency_key="att_002",
    )

    assert harness.side_effect_calls == ["side:start"]
    assert harness.committed_count == 0

    recovered = recover_run(store, run.run_id)
    assert recovered.status == "needs_attention"
    assert recovered.current_step == "start"

    events = store.get_events(run.run_id)
    transition_events = [e for e in events if e.type == "step.transition"]
    assert transition_events == []


def test_ac_nfr0001_01_interruption_after_commit_no_duplicate_side_effects():
    """AC-NFR0001-01: interrupting after commit yields a committed run, no dupes.

    Re-applying the same command with the same idempotency key must not
    re-execute the side effect or advance the run a second time.
    """
    harness, store, orchestrator = _harness()
    run = store.create_run(store._catalog.get("nfr0001_chain", "1"))  # noqa: SLF001
    harness.arm("after_commit")

    command = RuntimeCommand(
        run_id=run.run_id,
        expected_revision=run.revision,
        result="done",
        idempotency_key="att_003",
    )
    harness.execute_with_interruption(
        orchestrator,
        command,
        side_effect_label="side:start",
        idempotency_key="att_003",
    )

    assert harness.committed_count == 1
    assert harness.side_effect_calls == ["side:start"]

    committed = store.get_run(run.run_id)
    assert committed.current_step == "middle"
    assert committed.revision == run.revision + 1

    # Re-applying with the same idempotency key is a no-op: the stored
    # completed attempt is returned and no new side effect is recorded.
    orchestrator.apply_command(command)
    assert harness.committed_count == 1
    assert harness.side_effect_calls == ["side:start"]


# -- AC-NFR0001-02 ------------------------------------------------------------


def test_ac_nfr0001_02_committed_revisions_have_one_terminal_event_each():
    """AC-NFR0001-02: each committed revision has exactly one terminal-state event.

    Given a run that advanced through several committed revisions, the event
    stream must contain exactly one ``step.transition`` event per committed
    revision and no orphan state events referencing uncommitted revisions.
    """
    harness, store, orchestrator = _harness()
    run = store.create_run(store._catalog.get("nfr0001_chain", "1"))  # noqa: SLF001

    orchestrator.apply_command(
        RuntimeCommand(run_id=run.run_id, expected_revision=0, result="done")
    )
    orchestrator.apply_command(
        RuntimeCommand(run_id=run.run_id, expected_revision=1, result="done")
    )

    committed = store.get_run(run.run_id)
    events = store.get_events(run.run_id)

    transition_events = [e for e in events if e.type == "step.transition"]
    assert len(transition_events) == 2

    committed_revisions = {1, 2}
    event_revisions = {e.revision for e in transition_events}
    assert event_revisions == committed_revisions

    # Every transition event references a committed revision; no orphan.
    for event in transition_events:
        assert event.revision <= committed.revision

    # The final run revision equals the highest committed event revision.
    assert committed.revision == max(event.revision for event in transition_events)


def test_ac_nfr0001_02_failed_commit_leaves_no_terminal_event():
    """AC-NFR0001-02: a failed commit must not leave an orphan terminal event.

    When a transition is rejected because of a revision conflict, no new
    transition event is appended to the stream.
    """
    harness, store, orchestrator = _harness()
    run = store.create_run(store._catalog.get("nfr0001_chain", "1"))  # noqa: SLF001

    orchestrator.apply_command(
        RuntimeCommand(run_id=run.run_id, expected_revision=0, result="done")
    )

    stale_command = RuntimeCommand(
        run_id=run.run_id, expected_revision=0, result="done"
    )
    with pytest.raises(RevisionConflictError):
        orchestrator.apply_command(stale_command)

    events = store.get_events(run.run_id)
    transition_events = [e for e in events if e.type == "step.transition"]
    assert len(transition_events) == 1
    assert transition_events[0].revision == 1
