"""Agent-model binding store with run-scoped overrides (FR-1301).

This module manages the agent-to-model binding graph for workflow runs. Each
agent role has a default model from the Louke configuration. Users can create
run-scoped overrides that take effect for the next not-yet-started task.
Overrides are versioned with optimistic concurrency and audited.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone


class BindingModelUnavailableError(ValueError):
    """Raised when a binding override references an unavailable model."""


class BindingRevisionConflictError(Exception):
    """Raised when a binding update is based on a stale revision."""


class BindingNotFoundError(KeyError):
    """Raised when a requested binding does not exist."""


class RunReadonlyError(Exception):
    """Raised when a binding operation is attempted on a read-only run."""


@dataclass(frozen=True, slots=True)
class AgentBindingSummary:
    """A view of one agent's effective model binding.

    Attributes:
        agent_role: The agent role identifier (e.g. ``devon``).
        effective_model: The model the next task will use.
        source: ``default`` or ``override``.
        binding_revision: The current binding revision for CAS.
    """

    agent_role: str
    effective_model: str
    source: str
    binding_revision: int


@dataclass(frozen=True, slots=True)
class TaskModelManifest:
    """A snapshot of the model resolved for a specific task.

    Attributes:
        agent_role: The agent role.
        model: The resolved model identifier.
        source: ``default`` or ``override``.
    """

    agent_role: str
    model: str
    source: str


@dataclass(frozen=True, slots=True)
class BindingEvent:
    """An audit event recording a binding change.

    Attributes:
        event_id: Opaque event identifier.
        run_id: The run the binding belongs to.
        agent_role: The agent whose binding changed.
        old_model: The previous effective model.
        new_model: The new effective model.
        actor: The actor who made the change.
        effective_from: When the change takes effect (``next_task``).
        at: ISO 8601 UTC timestamp.
    """

    event_id: str
    run_id: str
    agent_role: str
    old_model: str
    new_model: str
    actor: dict[str, str]
    effective_from: str
    at: str


class BindingStore:
    """Manage agent-model bindings with run-scoped overrides.

    Each run starts with binding revision 1 and all agents using their
    default models. Overrides are stored per (run_id, agent_role) and
    increment the run's binding revision. Historical (read-only) runs
    reject new overrides.

    Args:
        default_models: Mapping from agent role to default model id.
        available_models: Set of model ids that can be used in overrides.
    """

    def __init__(
        self,
        default_models: dict[str, str],
        available_models: frozenset[str],
    ) -> None:
        self._default_models = dict(default_models)
        self._available_models = frozenset(available_models)
        self._overrides: dict[tuple[str, str], str] = {}
        self._binding_revisions: dict[str, int] = {}
        self._events: dict[str, list[BindingEvent]] = {}
        self._readonly_runs: set[str] = set()

    def list_bindings(self, run_id: str) -> tuple[AgentBindingSummary, ...]:
        """Return all agent bindings for ``run_id``.

        Args:
            run_id: The run to list bindings for.

        Returns:
            A tuple of :class:`AgentBindingSummary` for all known agent roles.
        """
        revision = self._binding_revisions.get(run_id, 1)
        return tuple(
            self._build_summary(run_id, role, revision)
            for role in sorted(self._default_models)
        )

    def set_override(
        self,
        run_id: str,
        agent_role: str,
        model: str,
        actor: dict[str, str],
        expected_binding_revision: int,
    ) -> AgentBindingSummary:
        """Set or replace a run-scoped model override for ``agent_role``.

        Args:
            run_id: The run to set the override on.
            agent_role: The agent whose model should be overridden.
            model: The model to bind. Must be in ``available_models``.
            actor: The actor making the change.
            expected_binding_revision: The binding revision the caller last
                observed, for optimistic concurrency.

        Returns:
            The updated :class:`AgentBindingSummary`.

        Raises:
            RunReadonlyError: If the run is marked read-only.
            BindingRevisionConflictError: If the expected revision is stale.
            BindingModelUnavailableError: If ``model`` is not available.
        """
        if run_id in self._readonly_runs:
            raise BindingRevisionConflictError(
                f"run {run_id!r} is read-only; no new overrides allowed"
            )

        current_revision = self._binding_revisions.get(run_id, 1)
        if current_revision != expected_binding_revision:
            raise BindingRevisionConflictError(
                f"binding revision conflict: expected {expected_binding_revision}, "
                f"found {current_revision}"
            )

        if model not in self._available_models:
            raise BindingModelUnavailableError(f"model {model!r} is not available")

        old_model = self._effective_model(run_id, agent_role)
        self._overrides[(run_id, agent_role)] = model
        new_revision = current_revision + 1
        self._binding_revisions[run_id] = new_revision

        event = BindingEvent(
            event_id=f"bevt_{uuid.uuid4().hex[:12]}",
            run_id=run_id,
            agent_role=agent_role,
            old_model=old_model,
            new_model=model,
            actor=dict(actor),
            effective_from="next_task",
            at=datetime.now(timezone.utc).isoformat(),
        )
        self._events.setdefault(run_id, []).append(event)

        return self._build_summary(run_id, agent_role, new_revision)

    def resolve_task_model(
        self,
        run_id: str,
        agent_role: str,
    ) -> TaskModelManifest:
        """Resolve the model for a new task of ``agent_role`` on ``run_id``.

        Args:
            run_id: The run the task belongs to.
            agent_role: The agent role to resolve.

        Returns:
            A :class:`TaskModelManifest` with the resolved model and source.
        """
        model = self._effective_model(run_id, agent_role)
        source = self._source(run_id, agent_role)
        return TaskModelManifest(agent_role=agent_role, model=model, source=source)

    def list_binding_events(self, run_id: str) -> tuple[BindingEvent, ...]:
        """Return all binding audit events for ``run_id``.

        Args:
            run_id: The run to list events for.

        Returns:
            A tuple of :class:`BindingEvent` in chronological order.
        """
        return tuple(self._events.get(run_id, ()))

    def mark_run_readonly(self, run_id: str) -> None:
        """Mark ``run_id`` as read-only, preventing new overrides.

        Args:
            run_id: The run to mark as read-only.
        """
        self._readonly_runs.add(run_id)

    def _effective_model(self, run_id: str, agent_role: str) -> str:
        """Return the effective model for ``agent_role`` on ``run_id``."""
        override = self._overrides.get((run_id, agent_role))
        if override is not None:
            return override
        return self._default_models.get(agent_role, "")

    def _source(self, run_id: str, agent_role: str) -> str:
        """Return ``override`` or ``default`` for the agent's binding source."""
        if (run_id, agent_role) in self._overrides:
            return "override"
        return "default"

    def _build_summary(
        self,
        run_id: str,
        agent_role: str,
        revision: int,
    ) -> AgentBindingSummary:
        """Build an :class:`AgentBindingSummary` for one agent role."""
        return AgentBindingSummary(
            agent_role=agent_role,
            effective_model=self._effective_model(run_id, agent_role),
            source=self._source(run_id, agent_role),
            binding_revision=revision,
        )
