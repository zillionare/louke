"""FR-2800: Archer, Devon & Shield prompt contract.

The locked prompt bundle must constrain: Archer only outputs implementation
task graph/advisory (no GitHub tasks, no flow advancement); Devon only edits
authorised unit tests + implementation per manifest/phase (Red/Green/Refactor
rules clear, no commit/push/install/hook-bypass/Issue-close/gate-evidence/
stage-advance); Shield only writes authorised integration/e2e and returns
semantic handoff (no commit/push/program-PASS/Maestro-advance request).  All
three must reference program-owned schema + manifest identity, and must NOT
proactively request Human technical decisions (AC-FR2800-01).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

ERROR_CODES = (
    "ARCHER_RESPONSIBILITY_INCOMPLETE",
    "ARCHER_SIDE_EFFECT_FORBIDDEN",
    "ARCHER_QUESTION_HUMAN_FORBIDDEN",
    "DEVON_RESPONSIBILITY_INCOMPLETE",
    "DEVON_SIDE_EFFECT_FORBIDDEN",
    "DEVON_QUESTION_HUMAN_FORBIDDEN",
    "SHIELD_RESPONSIBILITY_INCOMPLETE",
    "SHIELD_SIDE_EFFECT_FORBIDDEN",
    "SHIELD_QUESTION_HUMAN_FORBIDDEN",
    "PROMPT_QUESTION_HUMAN_FORBIDDEN",
    "PROMPT_SCHEMA_INVALID",
)

_ARCHER_REQUIRED_RESPONSIBILITIES = frozenset({"task-graph", "advisory"})
_ARCHER_REQUIRED_FORBIDDEN = frozenset(
    {
        "commit",
        "push",
        "issue-creation",
        "stage-advance",
        "review-persistence",
        "activation",
    }
)

_DEVON_REQUIRED_RESPONSIBILITIES = frozenset({"edit-unit-tests", "edit-implementation"})
_DEVON_REQUIRED_FORBIDDEN = frozenset(
    {
        "commit",
        "push",
        "install",
        "hook-bypass",
        "issue-close",
        "gate-evidence",
        "stage-advance",
    }
)

_SHIELD_REQUIRED_RESPONSIBILITIES = frozenset(
    {
        "write-integration-e2e",
        "return-semantic-handoff",
    }
)
_SHIELD_REQUIRED_FORBIDDEN = frozenset(
    {
        "commit",
        "push",
        "program-pass",
        "maestro-advance",
    }
)

_QUESTION_HUMAN_MARKERS = (
    "ask human",
    "question human",
    "human must choose",
    "human to pick",
    "request human",
    "ask Human",
)


class ImplPromptContractError(Exception):
    """A fail-closed impl prompt contract rejection carrying a stable code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


@dataclass(frozen=True)
class RolePromptContract:
    """A single role's prompt contract (AC-FR2800-01).

    Attributes:
        role: ``archer|devon|shield``.
        responsibilities: Tuple of declared duties.
        forbidden_actions: Tuple of forbidden side effects.
        output_delivery: Declared output delivery destination.
        schema_ref: Program-owned schema reference.
        manifest_ref: Program-owned manifest reference.
        protocol_refs: Tuple of protocol refs (may include forbidden markers).
    """

    role: str
    responsibilities: tuple[str, ...]
    forbidden_actions: tuple[str, ...]
    output_delivery: str
    schema_ref: str
    manifest_ref: str
    protocol_refs: tuple[str, ...] = ()


@dataclass(frozen=True)
class ImplPromptBundle:
    """The locked three-role impl prompt bundle (AC-FR2800-01).

    Attributes:
        archer: Archer's :class:`RolePromptContract`.
        devon: Devon's :class:`RolePromptContract`.
        shield: Shield's :class:`RolePromptContract`.
    """

    archer: RolePromptContract
    devon: RolePromptContract
    shield: RolePromptContract


def _parse_role(source: dict[str, Any]) -> RolePromptContract:
    return RolePromptContract(
        role=str(source.get("role", "")),
        responsibilities=tuple(source.get("responsibilities", ()) or ()),
        forbidden_actions=tuple(source.get("forbidden_actions", ()) or ()),
        output_delivery=str(source.get("output_delivery", "")),
        schema_ref=str(source.get("schema_ref", "")),
        manifest_ref=str(source.get("manifest_ref", "")),
        protocol_refs=tuple(source.get("protocol_refs", ()) or ()),
    )


def parse_impl_prompt(source: dict[str, Any]) -> ImplPromptBundle:
    """Parse the three-role impl prompt bundle (AC-FR2800-01)."""
    return ImplPromptBundle(
        archer=_parse_role(source["archer"]),
        devon=_parse_role(source["devon"]),
        shield=_parse_role(source["shield"]),
    )


def _check_no_question_human(contract: RolePromptContract) -> None:
    text = " ".join(contract.protocol_refs).lower()
    for marker in _QUESTION_HUMAN_MARKERS:
        if marker in text:
            raise ImplPromptContractError(
                "PROMPT_QUESTION_HUMAN_FORBIDDEN",
                f"protocol ref contains forbidden marker: {marker}",
            )


def _check_required(
    contract: RolePromptContract,
    required: frozenset[str],
    code_missing: str,
    forbidden: frozenset[str],
    code_forbidden: str,
) -> None:
    missing = required - set(contract.responsibilities)
    if missing:
        raise ImplPromptContractError(
            code_missing,
            f"missing responsibilities: {sorted(missing)}",
        )
    missing_forbidden = forbidden - set(contract.forbidden_actions)
    if missing_forbidden:
        raise ImplPromptContractError(
            code_forbidden,
            f"missing forbidden actions: {sorted(missing_forbidden)}",
        )
    if not contract.schema_ref or not contract.manifest_ref:
        raise ImplPromptContractError(
            "PROMPT_SCHEMA_INVALID",
            f"role {contract.role!r} must reference program-owned schema + manifest",
        )
    _check_no_question_human(contract)


def verify_archer_contract(contract: RolePromptContract) -> None:
    """Verify Archer's prompt contract (AC-FR2800-01)."""
    _check_required(
        contract,
        _ARCHER_REQUIRED_RESPONSIBILITIES,
        "ARCHER_RESPONSIBILITY_INCOMPLETE",
        _ARCHER_REQUIRED_FORBIDDEN,
        "ARCHER_SIDE_EFFECT_FORBIDDEN",
    )


def verify_devon_contract(contract: RolePromptContract) -> None:
    """Verify Devon's prompt contract (AC-FR2800-01)."""
    _check_required(
        contract,
        _DEVON_REQUIRED_RESPONSIBILITIES,
        "DEVON_RESPONSIBILITY_INCOMPLETE",
        _DEVON_REQUIRED_FORBIDDEN,
        "DEVON_SIDE_EFFECT_FORBIDDEN",
    )


def verify_shield_contract(contract: RolePromptContract) -> None:
    """Verify Shield's prompt contract (AC-FR2800-01)."""
    _check_required(
        contract,
        _SHIELD_REQUIRED_RESPONSIBILITIES,
        "SHIELD_RESPONSIBILITY_INCOMPLETE",
        _SHIELD_REQUIRED_FORBIDDEN,
        "SHIELD_SIDE_EFFECT_FORBIDDEN",
    )
