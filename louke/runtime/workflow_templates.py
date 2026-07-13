"""Built-in workflow templates for new_feature and bug_fix (FR-2101).

The registry exposes the canonical node sets for ``new_feature`` and
``bug_fix`` workflows, resolves hotfix paths based on impact rules, and
validates that completion only occurs when all required evidence is present.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto


class WorkflowType(Enum):
    """Built-in workflow types."""

    NEW_FEATURE = auto()
    BUG_FIX = auto()


class CompletionBlockedError(RuntimeError):
    """Raised when a workflow cannot be completed due to missing evidence."""


@dataclass(frozen=True, slots=True)
class HotfixImpact:
    """Declarative hotfix impact flags.

    If any flag is True the hotfix must follow the full design-required path.
    """

    public_interface: bool
    data_migration: bool
    security_boundary: bool
    cross_module_design: bool


@dataclass(frozen=True, slots=True)
class CompletionResult:
    """Result of a successful workflow completion.

    Attributes:
        terminal_state: Always ``completed``.
        archived_to_history: Whether the run was archived to history.
    """

    terminal_state: str
    archived_to_history: bool


class CompletableWorkflow:
    """A workflow template with gate and completion validation."""

    def __init__(
        self,
        workflow_type: WorkflowType,
        nodes: set[str],
        preflight_steps: set[str],
        required_completion_nodes: set[str],
    ) -> None:
        self.workflow_type = workflow_type
        self.nodes = frozenset(nodes)
        self.preflight_steps = frozenset(preflight_steps)
        self.required_completion_nodes = frozenset(required_completion_nodes)

    def bypass_gate(self, gate_id: str, actor: str, reason: str) -> None:
        """Reject any attempt to bypass a gate.

        Args:
            gate_id: Gate being bypassed.
            actor: Actor requesting bypass.
            reason: Bypass reason.

        Raises:
            PermissionError: Always, because gates cannot be bypassed.
        """
        raise PermissionError(
            f"gate {gate_id!r} cannot be bypassed by {actor!r}: {reason}"
        )

    def complete(self, evidence: dict[str, bool]) -> CompletionResult:
        """Complete the workflow if all required evidence is present.

        Args:
            evidence: Map from node id to whether it is satisfied.

        Returns:
            A :class:`CompletionResult`.

        Raises:
            CompletionBlockedError: If any required node is missing or False.
        """
        missing = [
            node
            for node in self.required_completion_nodes
            if not evidence.get(node)
        ]
        if missing:
            raise CompletionBlockedError(
                f"completion blocked by missing evidence: {sorted(missing)}"
            )
        return CompletionResult(terminal_state="completed", archived_to_history=True)


class SourceContractValidation:
    """Validate source-contract linkage for bug_fix and hotfix workflows."""

    def validate(self, spec_status: str, has_issue_link: bool) -> bool:
        """Return True if the bug_fix can be created against the spec/issue."""
        return spec_status == "approved" and has_issue_link

    def can_inherit_requirements_approval(
        self,
        spec_status: str,
        source_contract_digest_matches: bool,
    ) -> bool:
        """Return True if a hotfix may inherit an existing requirements approval.

        Inheritance is only allowed when the spec is approved and the source
        contract digest still matches.
        """
        return spec_status == "approved" and source_contract_digest_matches


class WorkflowTemplateRegistry:
    """Registry of built-in workflow templates."""

    def __init__(self) -> None:
        self._templates: dict[WorkflowType, CompletableWorkflow] = {
            WorkflowType.NEW_FEATURE: self._build_new_feature(),
            WorkflowType.BUG_FIX: self._build_bug_fix(),
        }

    @staticmethod
    def _build_new_feature() -> CompletableWorkflow:
        nodes = {
            "requirements_author",
            "requirements_review",
            "requirements_approval",
            "test_plan_author",
            "test_plan_review",
            "architecture_author",
            "interfaces_author",
            "architecture_review",
            "interfaces_review",
            "m_lock",
            "traceable_implementation",
            "code",
            "authoritative_tests",
            "e2e",
            "policy_release",
            "human_milestone_close",
            "history",
        }
        required = {
            "requirements_approval",
            "m_lock",
            "traceable_implementation",
            "code",
            "authoritative_tests",
            "e2e",
            "policy_release",
            "human_milestone_close",
        }
        return CompletableWorkflow(
            workflow_type=WorkflowType.NEW_FEATURE,
            nodes=nodes,
            preflight_steps={"foundation_preflight"},
            required_completion_nodes=required,
        )

    @staticmethod
    def _build_bug_fix() -> CompletableWorkflow:
        nodes = {
            "issue_source_contract_validation",
            "failure_reproduction",
            "m_lock",
            "devon_rgr",
            "review",
            "authoritative_regression",
            "policy_release_confirmation",
            "history",
        }
        required = {
            "issue_source_contract_validation",
            "m_lock",
            "devon_rgr",
            "review",
            "authoritative_regression",
            "policy_release_confirmation",
        }
        return CompletableWorkflow(
            workflow_type=WorkflowType.BUG_FIX,
            nodes=nodes,
            preflight_steps={"foundation_preflight"},
            required_completion_nodes=required,
        )

    def get(self, workflow_type: WorkflowType) -> CompletableWorkflow:
        """Return the template for ``workflow_type``.

        Raises:
            KeyError: If the workflow type is not built in.
        """
        template = self._templates.get(workflow_type)
        if template is None:
            raise KeyError(f"workflow type {workflow_type} not found")
        return template

    def resolve_hotfix(self, impact: HotfixImpact) -> CompletableWorkflow:
        """Return the appropriate hotfix template based on impact flags.

        Low-impact hotfixes use the ``quick_rgr`` path and skip design.
        High-impact hotfixes include test-plan, architecture and interface work.
        """
        high_impact = any(
            (
                impact.public_interface,
                impact.data_migration,
                impact.security_boundary,
                impact.cross_module_design,
            )
        )
        if high_impact:
            nodes = {
                "issue_source_contract_validation",
                "test_plan_author",
                "test_plan_review",
                "architecture_author",
                "interfaces_author",
                "architecture_review",
                "interfaces_review",
                "m_lock",
                "devon_rgr",
                "review",
                "authoritative_regression",
                "policy_release_confirmation",
                "history",
            }
            required = {
                "issue_source_contract_validation",
                "test_plan_author",
                "architecture_author",
                "interfaces_author",
                "m_lock",
                "devon_rgr",
                "review",
                "authoritative_regression",
                "policy_release_confirmation",
            }
        else:
            nodes = {
                "issue_source_contract_validation",
                "quick_rgr",
                "design_skipped",
                "m_lock",
                "review",
                "authoritative_regression",
                "policy_release_confirmation",
                "history",
            }
            required = {
                "issue_source_contract_validation",
                "quick_rgr",
                "m_lock",
                "review",
                "authoritative_regression",
                "policy_release_confirmation",
            }
        return CompletableWorkflow(
            workflow_type=WorkflowType.BUG_FIX,
            nodes=nodes,
            preflight_steps={"foundation_preflight"},
            required_completion_nodes=required,
        )

    def hotfix_decision_candidates(self) -> list[str]:
        """Return the candidate set presented to Maestro for hotfix routing."""
        return ["quick_rgr", "design_required"]
