"""Workflow definition registry and run binding (FR-1701).

A workflow definition is an immutable graph: nodes, edges, gates, decisions and
version. The runtime can enumerate the whole definition and refuses runtime
mutations. Runs are bound either to a user-selected definition or to a definition
chosen by program classification. Semantic decisions are made with bounded
context and candidate sets; illegal or low-confidence suggestions are rejected
or routed to a human clarification gate.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


class IllegalSuggestionError(ValueError):
    """Raised when a Maestro suggestion is outside the allowed candidate set."""


@dataclass(frozen=True, slots=True)
class WorkflowDefinition:
    """Immutable declaration of a workflow graph.

    Attributes:
        name: Unique workflow name.
        version: Semantic version string.
        nodes: Set of node identifiers.
        edges: Set of legal (source, target) transitions.
        gates: Optional set of gate node identifiers.
        decisions: Optional set of decision node identifiers.
        allow_auto_select: Whether the runtime may auto-select this definition
            when the user did not explicitly choose one.
        is_main_workflow: Whether this definition represents a primary project
            run; only one main run may be active at a time.
    """

    name: str
    version: str
    nodes: frozenset[str]
    edges: frozenset[tuple[str, str]]
    gates: frozenset[str] = field(default_factory=frozenset)
    decisions: frozenset[str] = field(default_factory=frozenset)
    allow_auto_select: bool = False
    is_main_workflow: bool = False

    def __init__(  # noqa: PLR0913
        self,
        name: str,
        version: str,
        nodes: set[str],
        edges: set[tuple[str, str]],
        gates: set[str] | None = None,
        decisions: set[str] | None = None,
        allow_auto_select: bool = False,
        is_main_workflow: bool = False,
    ) -> None:
        object.__setattr__(self, "name", name)
        object.__setattr__(self, "version", version)
        object.__setattr__(self, "nodes", frozenset(nodes))
        object.__setattr__(self, "edges", frozenset(edges))
        object.__setattr__(self, "gates", frozenset(gates or ()))
        object.__setattr__(self, "decisions", frozenset(decisions or ()))
        object.__setattr__(self, "allow_auto_select", allow_auto_select)
        object.__setattr__(self, "is_main_workflow", is_main_workflow)


@dataclass(frozen=True, slots=True)
class Classification:
    """Program classification result when the user did not select a workflow.

    Attributes:
        kind: Classification kind, e.g. ``new_feature`` or ``hotfix``.
        reason: Human-readable reason for the classification.
    """

    kind: str
    reason: str = ""


@dataclass(frozen=True, slots=True)
class DecisionSuggestion:
    """Result of a semantic decision consultation.

    Attributes:
        candidate: The selected candidate value.
        metadata: Additional structured metadata such as reason and confidence.
        requires_human_clarification: True if confidence was below the required
            threshold.
    """

    candidate: str
    metadata: dict[str, Any]
    requires_human_clarification: bool = False


class WorkflowRegistry:
    """Registry of immutable workflow definitions.

    Registering a definition with the same ``name`` and ``version`` as an
    existing definition is treated as a mutation attempt and rejected.
    """

    def __init__(self) -> None:
        self._definitions: dict[tuple[str, str], WorkflowDefinition] = {}

    def register(self, definition: WorkflowDefinition) -> None:
        """Register a workflow definition.

        Args:
            definition: The immutable workflow definition to register.

        Raises:
            RuntimeError: If a definition with the same name and version is
                already registered.
        """
        key = (definition.name, definition.version)
        if key in self._definitions:
            raise RuntimeError(
                f"workflow {definition.name!r} version {definition.version!r} "
                "is already registered and cannot be mutated"
            )
        self._definitions[key] = definition

    def get(self, name: str, version: str) -> WorkflowDefinition:
        """Return the definition for ``name``/``version``.

        Raises:
            KeyError: If no such definition is registered.
        """
        definition = self._definitions.get((name, version))
        if definition is None:
            raise KeyError(f"workflow {name!r} version {version!r} not found")
        return definition

    def select_by_classification(
        self, classification: Classification
    ) -> WorkflowDefinition:
        """Select an auto-selectable definition matching ``classification``.

        Args:
            classification: The program classification.

        Returns:
            The matching :class:`WorkflowDefinition`.

        Raises:
            KeyError: If no auto-selectable definition matches ``classification``.
        """
        for definition in self._definitions.values():
            if definition.allow_auto_select and definition.name == classification.kind:
                return definition
        raise KeyError(
            f"no auto-selectable workflow for classification {classification.kind!r}"
        )

    def definitions(self) -> dict[tuple[str, str], WorkflowDefinition]:
        """Return a read-only view of all registered definitions."""
        return dict(self._definitions)


class WorkflowRunBinding:
    """Binding between a run and a workflow definition.

    The binding records whether the user explicitly selected the workflow or
    whether it was chosen by program classification, and it enforces the
    single-active-main-run rule.
    """

    def __init__(
        self,
        run_id: str,
        definition: WorkflowDefinition,
        selected_by_user: bool,
        classification: Classification | None = None,
    ) -> None:
        self.run_id = run_id
        self.definition = definition
        self.selected_by_user = selected_by_user
        self.classification = classification

    @classmethod
    def _ensure_single_main_run(
        cls,
        definition: WorkflowDefinition,
        run_id: str,
        active_main_runs: set[str] | None,
    ) -> None:
        """Enforce the single-active-main-run rule.

        Raises:
            RuntimeError: If ``run_id`` already holds or would create a second
                active main workflow.
        """
        if not definition.is_main_workflow:
            return
        active = active_main_runs or set()
        if run_id in active:
            raise RuntimeError(f"run {run_id!r} already has an active main workflow")
        existing = active - {run_id}
        if existing:
            raise RuntimeError(
                "only one active main workflow is allowed; existing runs: "
                f"{sorted(existing)}"
            )
        if active_main_runs is not None:
            active_main_runs.add(run_id)

    @classmethod
    def start(
        cls,
        run_id: str,
        registry: WorkflowRegistry,
        definition_name: str | None = None,
        version: str | None = None,
        classification: Classification | None = None,
        active_main_runs: set[str] | None = None,
    ) -> "WorkflowRunBinding":
        """Create a new run binding.

        Exactly one of ``definition_name``/``version`` or ``classification``
        must be provided.

        Args:
            run_id: Unique run identifier.
            registry: Workflow definition registry.
            definition_name: User-selected workflow name.
            version: User-selected workflow version.
            classification: Program classification when user did not select.
            active_main_runs: Set of run ids currently holding an active main
                workflow; updated if the chosen definition is a main workflow.

        Returns:
            A new :class:`WorkflowRunBinding`.

        Raises:
            RuntimeError: If a second main run is requested while one is active.
            ValueError: If neither selection nor classification is supplied.
        """
        if definition_name is not None and version is not None:
            definition = registry.get(definition_name, version)
            selected_by_user = True
            binding_classification = None
        elif classification is not None:
            definition = registry.select_by_classification(classification)
            selected_by_user = False
            binding_classification = classification
        else:
            raise ValueError(
                "either definition_name/version or classification must be provided"
            )

        cls._ensure_single_main_run(definition, run_id, active_main_runs)

        return cls(
            run_id=run_id,
            definition=definition,
            selected_by_user=selected_by_user,
            classification=binding_classification,
        )

    def request_semantic_decision(
        self,
        decision: str,
        context: dict[str, Any],
        candidates: list[str],
        suggestion: str | None = None,
        confidence: float = 1.0,
        min_confidence: float = 0.0,
    ) -> DecisionSuggestion:
        """Request a semantic decision from Maestro.

        Args:
            decision: Decision node identifier.
            context: Bounded context for the decision.
            candidates: Allowed candidate values.
            suggestion: Optional pre-selected candidate (for testing/validation).
            confidence: Confidence level of the suggestion.
            min_confidence: Minimum confidence required to avoid human
                clarification.

        Returns:
            A :class:`DecisionSuggestion`.

        Raises:
            IllegalSuggestionError: If ``suggestion`` is not in ``candidates``.
        """
        if suggestion is not None and suggestion not in candidates:
            raise IllegalSuggestionError(
                f"suggestion {suggestion!r} not in candidates {candidates!r}"
            )

        chosen = suggestion if suggestion is not None else candidates[0]
        return DecisionSuggestion(
            candidate=chosen,
            metadata={
                "decision": decision,
                "context": dict(context),
                "candidates": list(candidates),
                "reason": f"selected {chosen} from {len(candidates)} candidates",
                "confidence": confidence,
            },
            requires_human_clarification=confidence < min_confidence,
        )
