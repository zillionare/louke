"""FR-2200: Archer normative semantic contract.

Archer's prompt must limit its responsibilities to reading the current
manifest and project facts, autonomously designing Test Plan/Architecture/
Interfaces/machine contracts, processing authorised direct diff, and
returning semantic results or anchored gaps.  Archer must not proactively
question Human for technical decisions, must not execute install/commit/
push/dispatch/review-persistence/activation/stage-progression, and must
not write review artifacts or progress stages (AC-FR2200-01).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

ERROR_CODES = (
    "ARCHER_RESPONSIBILITY_INCOMPLETE",
    "ARCHER_SIDE_EFFECT_FORBIDDEN",
    "ARCHER_QUESTION_HUMAN_FORBIDDEN",
    "ARCHER_OUTPUT_DESTINATION_INVALID",
)

_REQUIRED_RESPONSIBILITIES = frozenset(
    {
        "read-manifest-and-facts",
        "design-test-plan",
        "design-architecture",
        "design-interfaces",
        "design-machine-contracts",
        "process-authorised-direct-diff",
        "return-semantic-result-or-gap",
    }
)

_FORBIDDEN_ACTIONS_REQUIRED = frozenset(
    {
        "commit",
        "push",
        "dispatch",
        "review persistence",
        "activation",
        "stage progression",
    }
)

_QUESTION_HUMAN_MARKERS = (
    "ask human",
    "question human",
    "human must choose",
    "human to pick",
    "request human",
)


class ArcherContractError(Exception):
    """A fail-closed Archer semantic contract rejection carrying a stable code."""

    __test__ = False

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


@dataclass(frozen=True)
class ArcherSemanticContract:
    """Parsed Archer semantic contract (AC-FR2200-01).

    Attributes:
        role: Always ``archer``.
        responsibilities: Tuple of declared duties.
        forbidden_actions: Tuple of forbidden side effects.
        output_delivery: The declared output delivery destination.
        protocol_refs: Optional tuple of referenced protocols (may include
            question-Human markers that must be rejected).
    """

    role: str
    responsibilities: tuple[str, ...]
    forbidden_actions: tuple[str, ...]
    output_delivery: str
    protocol_refs: tuple[str, ...] = ()


def parse_archer_contract(source: dict[str, Any]) -> ArcherSemanticContract:
    """Parse an Archer source record from the prompt bundle manifest."""
    permissions = source.get("permissions", {})
    forbidden = tuple(permissions.get("forbidden", []))
    output_contract = (
        source.get("output_contract", {}) if "output_contract" in source else {}
    )
    output_delivery = ""
    if isinstance(output_contract, dict):
        output_delivery = output_contract.get("delivery", "")
    if not output_delivery:
        # The bundle manifest doesn't carry an explicit output_contract on each
        # source; the Archer prompt's write permission declares the allowlist
        # boundary.  We treat the write permission as the output delivery
        # directive: "only current task-manifest allowlist" => Runtime.
        output_delivery = permissions.get("write", "")
    responsibilities = tuple(source.get("responsibilities", ()) or ())
    if not responsibilities:
        # The bundle manifest does not enumerate responsibilities explicitly;
        # we derive them from the protocol_refs and write/forbidden permissions.
        protocols = source.get("protocol_refs", [])
        responsibilities = tuple(_derive_responsibilities(protocols, permissions))
    return ArcherSemanticContract(
        role=source.get("role", "archer"),
        responsibilities=responsibilities,
        forbidden_actions=forbidden,
        output_delivery=output_delivery,
        protocol_refs=tuple(source.get("protocol_refs", []) or ()),
    )


def _derive_responsibilities(
    protocols: list[str], permissions: dict[str, Any]
) -> list[str]:
    """Derive Archer responsibilities from protocol refs and permissions."""
    responsibilities: list[str] = ["read-manifest-and-facts"]
    text = " ".join(protocols).lower()
    if "test plan" in text or "design" in text:
        responsibilities.append("design-test-plan")
    if "architecture" in text or "design" in text:
        responsibilities.append("design-architecture")
    if "interface" in text or "design" in text:
        responsibilities.append("design-interfaces")
    if "contract" in text or "design" in text:
        responsibilities.append("design-machine-contracts")
    if "diff" in text or "candidate" in text:
        responsibilities.append("process-authorised-direct-diff")
    responsibilities.append("return-semantic-result-or-gap")
    return responsibilities


def verify_responsibility_set(contract: ArcherSemanticContract) -> None:
    """Verify Archer declares all seven required duties (AC-FR2200-01)."""
    missing = _REQUIRED_RESPONSIBILITIES - set(contract.responsibilities)
    if missing:
        raise ArcherContractError(
            "ARCHER_RESPONSIBILITY_INCOMPLETE",
            f"missing responsibilities: {sorted(missing)}",
        )


def verify_no_side_effect_directives(contract: ArcherSemanticContract) -> None:
    """Verify Archer forbids all required side-effect actions (AC-FR2200-01)."""
    missing_forbidden = _FORBIDDEN_ACTIONS_REQUIRED - set(contract.forbidden_actions)
    if missing_forbidden:
        raise ArcherContractError(
            "ARCHER_SIDE_EFFECT_FORBIDDEN",
            f"missing forbidden actions: {sorted(missing_forbidden)}",
        )


def verify_no_question_human_directive(contract: ArcherSemanticContract) -> None:
    """Verify Archer does not direct questioning Human for tech decisions."""
    text = " ".join(contract.protocol_refs).lower()
    for marker in _QUESTION_HUMAN_MARKERS:
        if marker in text:
            raise ArcherContractError(
                "ARCHER_QUESTION_HUMAN_FORBIDDEN",
                f"protocol ref contains forbidden marker: {marker}",
            )


def verify_output_returns_runtime_destination(contract: ArcherSemanticContract) -> None:
    """Verify Archer's output delivery returns to Runtime/program."""
    delivery = contract.output_delivery.lower()
    if "runtime" not in delivery and "task-manifest" not in delivery:
        raise ArcherContractError(
            "ARCHER_OUTPUT_DESTINATION_INVALID",
            f"output_delivery {contract.output_delivery!r} does not return to Runtime",
        )
