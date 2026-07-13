"""Workflow definition catalog and static validation.

This module holds the immutable workflow definition schema and the validator
used before a WorkflowRun can be created. It must not execute shell commands
or persist run state.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Iterable

if TYPE_CHECKING:
    from louke.runtime.program_steps import HandlerRegistry

SUPPORTED_STEP_KINDS: frozenset[str] = frozenset(
    {"program", "human_gate", "semantic_task", "decision"}
)


class DefinitionInvalidError(ValueError):
    """Raised when a workflow definition fails catalog validation."""

    def __init__(self, errors: list["DefinitionValidationError"]) -> None:
        self.errors = errors
        super().__init__(f"definition invalid: {errors!r}")


class DefinitionNotFoundError(KeyError):
    """Raised when a requested definition id/version is not registered."""


class DefinitionVersionExistsError(ValueError):
    """Raised when re-registering a definition version with different content."""


@dataclass(frozen=True)
class Edge:
    """A directed transition between two workflow steps.

    Attributes:
        edge_id: Stable identifier for this transition within the definition.
        from_step: Source step id.
        to_step: Target step id.
        condition: Human-readable condition that selects this transition.
    """

    edge_id: str
    from_step: str
    to_step: str
    condition: str = ""


@dataclass(frozen=True)
class Step:
    """A single node in a workflow definition.

    Attributes:
        step_id: Stable step identifier, unique within the definition.
        kind: One of the supported step kinds in ``SUPPORTED_STEP_KINDS``.
        required: Whether the step must be reachable from ``start_step``.
        transitions: Outgoing edges to subsequent steps.
        handler: Registered handler name for ``program`` steps.
        shell: Forbidden shell command field; rejected by validation.
    """

    step_id: str
    kind: str
    required: bool = True
    transitions: tuple[Edge, ...] = field(default_factory=tuple)
    handler: str | None = None
    shell: str | None = None


@dataclass(frozen=True)
class WorkflowDefinition:
    """Immutable versioned workflow definition.

    Attributes:
        definition_id: Stable catalog identifier.
        version: Immutable version string.
        start_step: Id of the entry step.
        steps: Finite, ordered collection of steps.
    """

    definition_id: str
    version: str
    start_step: str
    steps: tuple[Step, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class DefinitionValidationError:
    """A stable, locatable validation error for a workflow definition.

    Attributes:
        code: Stable error type, e.g. ``unknown_step``.
        message: Human-readable explanation.
        step_id: Step locator when the error concerns a step.
        edge_id: Edge locator when the error concerns a transition.
    """

    code: str
    message: str
    step_id: str | None = None
    edge_id: str | None = None


def validate_definition(
    definition: WorkflowDefinition,
    handler_registry: HandlerRegistry | None = None,
) -> list[DefinitionValidationError]:
    """Validate ``definition`` and return a list of stable, locatable errors.

    The validator checks the five invalid situations required by AC-FR0001-01:
    unknown step, dangling transition, duplicate step/edge id,
    unreachable required step and unsupported step type.  When
    ``handler_registry`` is supplied, program steps are also checked for
    registered handlers and forbidden shell command fields (AC-FR0301-01).

    Args:
        definition: The workflow definition to validate.
        handler_registry: Optional registry used to validate program step
            handler references.

    Returns:
        A list of ``DefinitionValidationError``; empty for a valid definition.
    """
    errors: list[DefinitionValidationError] = []
    step_ids = {step.step_id for step in definition.steps}

    _check_start_step(definition, step_ids, errors)
    _check_duplicate_step_ids(definition.steps, errors)
    _check_steps_and_edges(definition, step_ids, errors)
    _check_unreachable_required_steps(definition, errors)
    _check_program_steps(definition, handler_registry, errors)

    return errors


def _check_start_step(
    definition: WorkflowDefinition,
    step_ids: set[str],
    errors: list[DefinitionValidationError],
) -> None:
    if definition.start_step not in step_ids:
        errors.append(
            DefinitionValidationError(
                code="unknown_step",
                message=f"start_step '{definition.start_step}' is not defined",
                step_id=definition.start_step,
            )
        )


def _check_duplicate_step_ids(
    steps: Iterable[Step],
    errors: list[DefinitionValidationError],
) -> None:
    seen: set[str] = set()
    for step in steps:
        if step.step_id in seen:
            errors.append(
                DefinitionValidationError(
                    code="duplicate_step_id",
                    message=f"duplicate step id '{step.step_id}'",
                    step_id=step.step_id,
                )
            )
            return
        seen.add(step.step_id)


def _check_steps_and_edges(
    definition: WorkflowDefinition,
    step_ids: set[str],
    errors: list[DefinitionValidationError],
) -> None:
    seen_edge_ids: set[str] = set()
    for step in definition.steps:
        if step.kind not in SUPPORTED_STEP_KINDS:
            errors.append(
                DefinitionValidationError(
                    code="unsupported_step_type",
                    message=(
                        f"step '{step.step_id}' has unsupported kind '{step.kind}'"
                    ),
                    step_id=step.step_id,
                )
            )

        for edge in step.transitions:
            if edge.edge_id in seen_edge_ids:
                errors.append(
                    DefinitionValidationError(
                        code="duplicate_edge_id",
                        message=f"duplicate edge id '{edge.edge_id}'",
                        edge_id=edge.edge_id,
                    )
                )
                return
            seen_edge_ids.add(edge.edge_id)

            if edge.to_step not in step_ids:
                errors.append(
                    DefinitionValidationError(
                        code="dangling_transition",
                        message=(
                            f"edge '{edge.edge_id}' targets undefined step "
                            f"'{edge.to_step}'"
                        ),
                        step_id=edge.to_step,
                        edge_id=edge.edge_id,
                    )
                )


def _check_unreachable_required_steps(
    definition: WorkflowDefinition,
    errors: list[DefinitionValidationError],
) -> None:
    reachable = _reachable_step_ids(definition)
    for step in definition.steps:
        if step.required and step.step_id not in reachable:
            errors.append(
                DefinitionValidationError(
                    code="unreachable_required_step",
                    message=f"required step '{step.step_id}' is unreachable",
                    step_id=step.step_id,
                )
            )


def _check_program_steps(
    definition: WorkflowDefinition,
    handler_registry: HandlerRegistry | None,
    errors: list[DefinitionValidationError],
) -> None:
    """Reject program steps with unregistered handlers or shell commands."""
    for step in definition.steps:
        if step.kind != "program":
            continue

        if step.shell is not None:
            errors.append(
                DefinitionValidationError(
                    code="shell_command_forbidden",
                    message=(
                        f"step '{step.step_id}' contains a forbidden shell command"
                    ),
                    step_id=step.step_id,
                )
            )

        if handler_registry is None:
            continue

        if step.handler is None or step.handler not in handler_registry:
            errors.append(
                DefinitionValidationError(
                    code="unregistered_handler",
                    message=(
                        f"step '{step.step_id}' references unregistered handler "
                        f"{step.handler!r}"
                    ),
                    step_id=step.step_id,
                )
            )


def _reachable_step_ids(definition: WorkflowDefinition) -> set[str]:
    """Return the set of step ids reachable from ``start_step`` via transitions."""
    if not definition.steps:
        return set()

    step_by_id = {step.step_id: step for step in definition.steps}
    reachable: set[str] = set()
    queue = [definition.start_step]

    while queue:
        current_id = queue.pop()
        if current_id in reachable or current_id not in step_by_id:
            continue
        reachable.add(current_id)
        for edge in step_by_id[current_id].transitions:
            if edge.to_step not in reachable:
                queue.append(edge.to_step)

    return reachable


def derive_status(step_id: str, definition: WorkflowDefinition) -> str:
    """Return the runtime status for a run positioned at ``step_id``.

    Args:
        step_id: The step the run is currently positioned at.
        definition: The bound workflow definition.

    Returns:
        ``waiting_for_human`` for ``human_gate`` steps, ``completed`` for
        terminal steps and ``in_progress`` for all other steps.
    """
    step = next(
        (step for step in definition.steps if step.step_id == step_id),
        None,
    )
    if step is None:
        return "in_progress"
    if step.kind == "human_gate":
        return "waiting_for_human"
    if not step.transitions:
        return "completed"
    return "in_progress"


class DefinitionRegistry:
    """Immutable versioned catalog of workflow definitions.

    Definitions are keyed by ``(definition_id, version)``.  Once a version is
    registered it cannot be replaced with a different definition, so runs that
    are pinned to a version always see the same steps and transitions.
    """

    def __init__(self) -> None:
        self._definitions: dict[tuple[str, str], WorkflowDefinition] = {}

    def register(self, definition: WorkflowDefinition) -> WorkflowDefinition:
        """Register ``definition`` after validating it.

        Args:
            definition: The workflow definition to register.

        Returns:
            The registered definition.  If the exact same definition is
            registered again, the existing copy is returned.

        Raises:
            DefinitionInvalidError: If the definition fails catalog validation.
            DefinitionVersionExistsError: If the same id/version is already
                registered with a different definition.
        """
        errors = validate_definition(definition)
        if errors:
            raise DefinitionInvalidError(errors)

        key = (definition.definition_id, definition.version)
        existing = self._definitions.get(key)
        if existing is not None:
            if existing == definition:
                return existing
            raise DefinitionVersionExistsError(
                f"definition {definition.definition_id!r} version "
                f"{definition.version!r} is already registered"
            )
        self._definitions[key] = definition
        return definition

    def get(self, definition_id: str, version: str) -> WorkflowDefinition:
        """Return the registered definition for ``definition_id``/``version``.

        Args:
            definition_id: The stable definition identifier.
            version: The immutable version string.

        Returns:
            The matching ``WorkflowDefinition``.

        Raises:
            DefinitionNotFoundError: If no definition with that id/version
                has been registered.
        """
        key = (definition_id, version)
        definition = self._definitions.get(key)
        if definition is None:
            raise DefinitionNotFoundError(
                f"definition {definition_id!r} version {version!r} not found"
            )
        return definition
