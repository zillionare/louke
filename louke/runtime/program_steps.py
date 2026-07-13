"""Registered program step handlers and executor.

This module provides the handler registry used by catalog validation and the
executor that invokes handlers with a read-only StepContext.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass(frozen=True, slots=True)
class StepContext:
    """Read-only context supplied to a program step handler.

    Attributes:
        run_id: Opaque identifier of the workflow run.
        step_id: Identifier of the step being executed.
        attempt_id: Opaque identifier of this attempt.
        workspace: Absolute path to the workspace root.
        idempotency_key: Stable key used to deduplicate the attempt.
    """

    run_id: str
    step_id: str
    attempt_id: str
    workspace: str
    idempotency_key: str


@dataclass(frozen=True, slots=True)
class HandlerResult:
    """Structured result returned by a program step handler.

    Attributes:
        result: The transition condition produced by the handler.
        output: Additional structured output validated against the step schema.
    """

    result: str
    output: dict[str, Any] = field(default_factory=dict)


Handler = Callable[[StepContext], HandlerResult]


class HandlerNotFoundError(KeyError):
    """Raised when a requested handler name is not registered."""


class HandlerRegistry:
    """Registry of named program step handlers.

    Handlers are keyed by name.  Once registered a name cannot be replaced
    without first unregistering it, keeping catalog validation deterministic.
    """

    def __init__(self) -> None:
        self._handlers: dict[str, Handler] = {}

    def register(self, name: str, handler: Handler) -> None:
        """Register ``handler`` under ``name``.

        Args:
            name: Stable handler identifier referenced by program steps.
            handler: Callable accepting a :class:`StepContext` and returning a
                :class:`HandlerResult`.
        """
        self._handlers[name] = handler

    def get(self, name: str) -> Handler:
        """Return the handler registered under ``name``.

        Args:
            name: The stable handler identifier.

        Returns:
            The registered handler callable.

        Raises:
            HandlerNotFoundError: If no handler with that name is registered.
        """
        handler = self._handlers.get(name)
        if handler is None:
            raise HandlerNotFoundError(f"handler {name!r} not registered")
        return handler

    def __contains__(self, name: str) -> bool:
        return name in self._handlers
