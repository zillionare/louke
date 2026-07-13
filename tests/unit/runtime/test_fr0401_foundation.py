"""FR-0401: Foundation programmatic preconditions.

AC references:
- AC-FR0401-01: complete foundation yields ``satisfied`` and does not invoke
  Scout or Warden agents.
- AC-FR0401-02: auto-repairable gaps are repaired once and become ``satisfied``
  on re-execution.
- AC-FR0401-03: gaps requiring human choice block with structured questions
  and no guessed resources.
- AC-FR0401-04: unrecoverable errors yield ``failed`` (or retryable per
  policy) and do not advance to the main workflow step.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from louke.runtime.catalog import DefinitionRegistry, Edge, Step, WorkflowDefinition
from louke.runtime.program_steps import HandlerRegistry, ProgramStepExecutor
from louke.runtime.store import WorkflowRunStore


def _step(step_id: str, kind: str, **kwargs: Any) -> Step:
    return Step(step_id=step_id, kind=kind, **kwargs)


def _edge(edge_id: str, from_step: str, to_step: str, condition: str = "") -> Edge:
    return Edge(
        edge_id=edge_id,
        from_step=from_step,
        to_step=to_step,
        condition=condition,
    )


def _foundation_definition() -> WorkflowDefinition:
    """Return a workflow exercising all foundation result transitions."""
    return WorkflowDefinition(
        definition_id="fr0401",
        version="1",
        start_step="foundation",
        steps=(
            _step(
                "foundation",
                "program",
                handler="foundation.ensure",
                transitions=(
                    _edge(
                        "e_sat", "foundation", "contract_verify", condition="satisfied"
                    ),
                    _edge(
                        "e_rep", "foundation", "contract_verify", condition="repaired"
                    ),
                    _edge("e_blk", "foundation", "blocked_step", condition="blocked"),
                    _edge("e_fail", "foundation", "failed_step", condition="failed"),
                    _edge(
                        "e_retry",
                        "foundation",
                        "retry_step",
                        condition="retryable",
                    ),
                ),
            ),
            _step("contract_verify", "program", handler="foundation.ensure"),
            _step("blocked_step", "program", handler="foundation.ensure"),
            _step("failed_step", "program", handler="foundation.ensure"),
            _step("retry_step", "program", handler="foundation.ensure"),
        ),
    )


@dataclass(frozen=True)
class FoundationGap:
    """A missing foundation resource or decision.

    Attributes:
        key: Stable identifier for the gap, used for idempotency.
        auto_repairable: Whether the gap can be resolved without human input.
        question: Structured question when ``auto_repairable`` is ``False``.
    """

    key: str
    auto_repairable: bool
    question: dict[str, Any] | None = None


class SpyFoundationAdapter:
    """Test adapter that records every operation and never calls agents."""

    def __init__(self, gaps: list[FoundationGap] | None = None) -> None:
        self._gaps = list(gaps or [])
        self._created_keys: set[str] = set()
        self.check_calls: list[str] = []
        self.create_calls: list[tuple[str, FoundationGap]] = []
        self.scout_calls: list[Any] = []
        self.warden_calls: list[Any] = []

    def set_gaps(self, gaps: list[FoundationGap]) -> None:
        """Replace the gaps returned by :meth:`check`."""
        self._gaps = list(gaps)

    def check(self, workspace: str) -> list[FoundationGap]:
        """Return the configured gaps and record the call."""
        self.check_calls.append(workspace)
        return list(self._gaps)

    def create(self, workspace: str, gap: FoundationGap) -> None:
        """Record the repair request, enforce key idempotency and remove the gap."""
        if gap.key in self._created_keys:
            raise AssertionError(
                f"resource {gap.key!r} was already created; adapter must be idempotent"
            )
        self._created_keys.add(gap.key)
        self.create_calls.append((workspace, gap))
        self._gaps = [g for g in self._gaps if g.key != gap.key]

    def dispatch_scout(self, task: Any) -> None:
        """Agent boundary marker; tests assert this is never called."""
        self.scout_calls.append(task)

    def dispatch_warden(self, task: Any) -> None:
        """Agent boundary marker; tests assert this is never called."""
        self.warden_calls.append(task)


class AllCompleteAdapter(SpyFoundationAdapter):
    """Adapter reporting a fully satisfied foundation."""

    def __init__(self) -> None:
        super().__init__(gaps=[])

    def create(self, workspace: str, gap: FoundationGap) -> None:
        raise AssertionError("create must not be called when foundation is complete")


def test_ac_fr0401_01_complete_foundation_advances_without_agent_calls(tmp_path):
    """AC-FR0401-01: satisfied foundation advances without Scout/Warden calls."""
    from louke.runtime.foundation import foundation_ensure_handler

    adapter = AllCompleteAdapter()
    handler = foundation_ensure_handler(adapter)

    registry = HandlerRegistry()
    registry.register("foundation.ensure", handler)

    definition_registry = DefinitionRegistry()
    definition = definition_registry.register(_foundation_definition())

    store = WorkflowRunStore(catalog=definition_registry)
    run = store.create_run(definition)

    executor = ProgramStepExecutor(registry)
    outcome = executor.execute(
        store=store,
        run_id=run.run_id,
        workspace=str(tmp_path),
        idempotency_key="foundation-01",
    )

    assert outcome.run.current_step == "contract_verify"
    assert outcome.run.status == "completed"
    assert outcome.error_code is None

    attempts = store.get_step_attempts(run.run_id)
    assert len(attempts) == 1
    assert attempts[0].status == "completed"
    assert attempts[0].result == "satisfied"

    assert len(adapter.scout_calls) == 0
    assert len(adapter.warden_calls) == 0


def test_ac_fr0401_02_auto_repair_is_idempotent_and_becomes_satisfied(tmp_path):
    """AC-FR0401-02: auto-repairable gaps repair once and re-execute as satisfied."""
    from louke.runtime.foundation import foundation_ensure_handler

    adapter = SpyFoundationAdapter(
        gaps=[FoundationGap(key="workspace/config", auto_repairable=True)]
    )
    handler = foundation_ensure_handler(adapter)

    registry = HandlerRegistry()
    registry.register("foundation.ensure", handler)

    definition_registry = DefinitionRegistry()
    definition = definition_registry.register(_foundation_definition())

    store = WorkflowRunStore(catalog=definition_registry)
    executor = ProgramStepExecutor(registry)
    workspace = str(tmp_path)

    first_run = store.create_run(definition)
    first = executor.execute(
        store=store,
        run_id=first_run.run_id,
        workspace=workspace,
        idempotency_key="foundation-02-first",
    )

    assert first.run.current_step == "contract_verify"
    assert first.run.status == "completed"
    assert first.error_code is None

    first_attempts = store.get_step_attempts(first_run.run_id)
    assert len(first_attempts) == 1
    assert first_attempts[0].result == "repaired"

    assert len(adapter.create_calls) == 1
    created_key = adapter.create_calls[0][1].key
    assert created_key == "workspace/config"

    second_run = store.create_run(definition)
    second = executor.execute(
        store=store,
        run_id=second_run.run_id,
        workspace=workspace,
        idempotency_key="foundation-02-second",
    )

    assert second.run.current_step == "contract_verify"
    assert second.run.status == "completed"
    assert second.error_code is None

    second_attempts = store.get_step_attempts(second_run.run_id)
    assert len(second_attempts) == 1
    assert second_attempts[0].result == "satisfied"

    assert len(adapter.create_calls) == 1
