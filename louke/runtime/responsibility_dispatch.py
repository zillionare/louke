"""Responsibility catalog and dispatcher (FR-1601).

The runtime distinguishes three kinds of responsibilities:

- ``program``: deterministic, enumerable rules executed by a registered handler.
- ``semantic``: requires agent judgement with declared inputs/outputs.
- ``unclassified``: not yet classified; validation rejects these.

Agent results are validated against declared schemas and digests before any
workflow state transition is allowed. Only program adapters may cause control
plane or release side effects.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Any, Callable


class ResponsibilityKind(Enum):
    """Classification of a workflow responsibility."""

    PROGRAM = auto()
    SEMANTIC = auto()
    UNCLASSIFIED = auto()


class UnknownResponsibilityError(KeyError):
    """Raised when a responsibility is not present in the catalog/registry."""


class ValidationError(ValueError):
    """Raised when a result or catalog fails validation."""


@dataclass(frozen=True, slots=True)
class DispatchResult:
    """Outcome of dispatching a responsibility.

    Attributes:
        kind: The kind of responsibility that was dispatched.
        output: The structured output produced by the handler.
    """

    kind: ResponsibilityKind
    output: dict[str, Any]


class ResponsibilityRegistry:
    """Registry that maps program responsibilities to their handlers.

    Program handlers are pure functions that take a dict of inputs and return a
    dict of outputs. They run synchronously inside the runtime and may perform
    the actual control-plane side effects that agents are not allowed to claim.
    """

    def __init__(self) -> None:
        self._handlers: dict[str, Callable[[dict[str, Any]], dict[str, Any]]] = {}

    def register(
        self,
        name: str,
        kind: ResponsibilityKind,
        handler: Callable[[dict[str, Any]], dict[str, Any]],
    ) -> None:
        """Register a responsibility handler.

        Args:
            name: Unique responsibility name.
            kind: Must be :attr:`ResponsibilityKind.PROGRAM`; semantic
                responsibilities are not dispatched through this registry.
            handler: Synchronous callable that receives inputs and returns a
                dict of outputs.

        Raises:
            ValidationError: If ``kind`` is not ``PROGRAM``.
        """
        if kind != ResponsibilityKind.PROGRAM:
            raise ValidationError(
                f"registry only accepts program handlers, got {kind.name}"
            )
        self._handlers[name] = handler

    def dispatch(self, name: str, inputs: dict[str, Any]) -> DispatchResult:
        """Execute the program handler for ``name``.

        Args:
            name: Registered responsibility name.
            inputs: Inputs for the handler.

        Returns:
            A :class:`DispatchResult` wrapping the handler output.

        Raises:
            UnknownResponsibilityError: If ``name`` is not registered.
        """
        handler = self._handlers.get(name)
        if handler is None:
            raise UnknownResponsibilityError(f"no program handler for {name!r}")
        return DispatchResult(
            kind=ResponsibilityKind.PROGRAM,
            output=handler(inputs),
        )


@dataclass(frozen=True, slots=True)
class ResponsibilityEntry:
    """Static declaration of a responsibility.

    Attributes:
        name: Unique responsibility name.
        kind: ``PROGRAM``, ``SEMANTIC`` or ``UNCLASSIFIED``.
        input_schema: Declared input shape (runtime-typed dict).
        output_schema: Declared output shape (runtime-typed dict).
    """

    name: str
    kind: ResponsibilityKind
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]


class ResponsibilityCatalog:
    """Catalog of all responsibilities in a workflow definition.

    The catalog is used both at build time (to ensure every responsibility is
    classified) and at runtime (to validate agent results). It rejects
    unclassified responsibilities and schema-invalid results.
    """

    def __init__(self) -> None:
        self._entries: dict[str, ResponsibilityEntry] = {}

    def register(
        self,
        name: str,
        kind: ResponsibilityKind,
        input_schema: dict[str, Any],
        output_schema: dict[str, Any],
    ) -> None:
        """Declare a responsibility in the catalog.

        Args:
            name: Unique responsibility name.
            kind: Responsibility classification.
            input_schema: Declared input shape.
            output_schema: Declared output shape.
        """
        self._entries[name] = ResponsibilityEntry(
            name=name,
            kind=kind,
            input_schema=dict(input_schema),
            output_schema=dict(output_schema),
        )

    def kind_of(self, name: str) -> ResponsibilityKind:
        """Return the kind of the responsibility ``name``.

        Args:
            name: Responsibility name.

        Returns:
            The :class:`ResponsibilityKind`.

        Raises:
            UnknownResponsibilityError: If ``name`` is not in the catalog.
        """
        entry = self._entries.get(name)
        if entry is None:
            raise UnknownResponsibilityError(f"unknown responsibility {name!r}")
        return entry.kind

    def validate_result(self, name: str, result: dict[str, Any]) -> None:
        """Validate that ``result`` conforms to the declared output schema.

        Args:
            name: Responsibility name.
            result: Agent-produced result.

        Raises:
            UnknownResponsibilityError: If ``name`` is not in the catalog.
            ValidationError: If ``result`` is missing required keys or contains
                unexpected keys.
        """
        entry = self._entries.get(name)
        if entry is None:
            raise UnknownResponsibilityError(f"unknown responsibility {name!r}")
        expected = set(entry.output_schema.keys())
        actual = set(result.keys())
        if expected != actual:
            raise ValidationError(
                f"result for {name!r} does not match output schema: "
                f"expected {sorted(expected)}, got {sorted(actual)}"
            )

    def validate(self) -> None:
        """Validate the entire catalog.

        Every registered responsibility must be classified as ``PROGRAM`` or
        ``SEMANTIC``. Unclassified entries cause a :class:`ValidationError`.

        Raises:
            ValidationError: If any entry is unclassified.
        """
        unclassified = [
            entry.name
            for entry in self._entries.values()
            if entry.kind == ResponsibilityKind.UNCLASSIFIED
        ]
        if unclassified:
            raise ValidationError(
                f"unclassified responsibilities: {sorted(unclassified)}"
            )

    def entries(self) -> dict[str, ResponsibilityEntry]:
        """Return a read-only view of the catalog entries."""
        return dict(self._entries)
