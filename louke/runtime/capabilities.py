"""Capability registry for semantic tasks and decision nodes.

The registry separates the capability contract (``agent_task``, ``decision``)
from the concrete adapters that satisfy them.  Runtime validation uses the
registry to reject workflow definitions that reference capabilities that have
not been registered, preventing echo/placeholder runs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


class UnsupportedCapabilityError(ValueError):
    """Raised when a workflow step references an unregistered capability."""


@dataclass(frozen=True, slots=True)
class CapabilityInfo:
    """Public report entry for a runtime capability.

    Attributes:
        name: Stable capability identifier, e.g. ``agent_task``.
        supported: Whether a concrete adapter is currently registered.
        kind: Capability class; currently the same as ``name``.
        description: Human-readable summary of the capability contract.
    """

    name: str
    supported: bool
    kind: str
    description: str


Adapter = Callable[..., Any]


class CapabilityRegistry:
    """Registry of named runtime capabilities and their concrete adapters.

    The registry starts empty.  Capabilities required by the v0.12 delivery
    (``agent_task`` and ``decision``) are reported as known entries even before
    an adapter is registered, so callers can distinguish "not yet wired" from
    "unknown".
    """

    _KNOWN_CAPABILITIES: tuple[str, ...] = ("agent_task", "decision")

    def __init__(self) -> None:
        self._adapters: dict[str, Adapter] = {}

    def register(self, name: str, adapter: Adapter) -> None:
        """Register ``adapter`` as the implementation of capability ``name``.

        Args:
            name: Stable capability identifier.
            adapter: Callable invoked by :meth:`invoke` when the capability is
                used.

        Raises:
            ValueError: If ``name`` is already registered.
        """
        if name in self._adapters:
            raise ValueError(f"capability {name!r} is already registered")
        self._adapters[name] = adapter

    def is_supported(self, name: str) -> bool:
        """Return whether ``name`` has a registered adapter."""
        return name in self._adapters

    def report(self) -> dict[str, CapabilityInfo]:
        """Return a capability report for the known v0.12 capabilities.

        The report includes every known capability even if no adapter is
        registered, marking it as unsupported so that product reports cannot
        hide missing integrations.
        """
        names = {*self._KNOWN_CAPABILITIES, *self._adapters.keys()}
        return {
            name: CapabilityInfo(
                name=name,
                supported=name in self._adapters,
                kind=name,
                description=self._description(name),
            )
            for name in sorted(names)
        }

    def invoke(self, name: str, **kwargs: Any) -> Any:
        """Invoke the registered adapter for ``name``.

        Args:
            name: The capability to invoke.
            **kwargs: Adapter-specific inputs.

        Returns:
            The adapter result.

        Raises:
            UnsupportedCapabilityError: If no adapter is registered for
                ``name``.
        """
        adapter = self._adapters.get(name)
        if adapter is None:
            raise UnsupportedCapabilityError(f"capability {name!r} is not registered")
        return adapter(**kwargs)

    @staticmethod
    def _description(name: str) -> str:
        descriptions = {
            "agent_task": "Dispatch a task to a registered agent adapter.",
            "decision": "Request a structured choice from a registered decision advisor.",
        }
        return descriptions.get(name, "Custom runtime capability.")
