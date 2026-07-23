"""FR-2900: Prism, Judge & Librarian prompt contract.

Prism reviews task graph / Red / final task / Shield tests / candidate
with multiple review kinds, each with explicit schema ref and read-only/
restricted-write scope, returning verdict bound to input identity.  Judge
only does deep semantic security review; program scan and gate execution
are Runtime's responsibility.  Librarian only edits authorised knowledge/
user docs when definition requires; non-required Librarian does NOT block
milestone.  None of the three may persist their own PASS, execute Git/
GitHub/program gate/state advancement (AC-FR2900-01).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

ERROR_CODES = (
    "PRISM_REVIEW_KIND_INCOMPLETE",
    "PRISM_SCOPE_INVALID",
    "PRISM_SIDE_EFFECT_FORBIDDEN",
    "JUDGE_RESPONSIBILITY_INCOMPLETE",
    "JUDGE_SIDE_EFFECT_FORBIDDEN",
    "JUDGE_SCOPE_INVALID",
    "LIBRARIAN_RESPONSIBILITY_INCOMPLETE",
    "LIBRARIAN_SIDE_EFFECT_FORBIDDEN",
    "LIBRARIAN_SCOPE_INVALID",
    "REVIEW_PROMPT_SCHEMA_INVALID",
)

_PRISM_REQUIRED_REVIEW_KINDS = frozenset(
    {
        "task_graph",
        "red",
        "final_task",
        "shield_tests",
        "candidate",
    }
)

_PRISM_REQUIRED_FORBIDDEN = frozenset(
    {
        "commit",
        "push",
        "program-gate",
        "state-advance",
        "pass-persistence",
    }
)

_JUDGE_REQUIRED_RESPONSIBILITIES = frozenset({"deep-semantic-security-review"})
_JUDGE_REQUIRED_FORBIDDEN = frozenset(
    {
        "commit",
        "push",
        "program-gate",
        "state-advance",
        "pass-persistence",
        "code-modification",
    }
)

_LIBRARIAN_REQUIRED_RESPONSIBILITIES = frozenset({"edit-authorised-docs"})
_LIBRARIAN_REQUIRED_FORBIDDEN = frozenset(
    {
        "commit",
        "push",
        "program-gate",
        "state-advance",
        "release-fact-modification",
        "pass-persistence",
    }
)


class ReviewPromptContractError(Exception):
    """A fail-closed review prompt contract rejection carrying a stable code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


@dataclass(frozen=True)
class PrismPromptContract:
    """Prism's prompt contract (AC-FR2900-01).

    Attributes:
        role: Always ``prism``.
        review_kinds: Tuple of supported review kinds.
        forbidden_actions: Tuple of forbidden side effects.
        output_delivery: Output delivery destination.
        schema_ref: Program-owned schema reference.
        manifest_ref: Program-owned manifest reference.
        scope: ``read-only`` (required).
    """

    role: str
    review_kinds: tuple[str, ...]
    forbidden_actions: tuple[str, ...]
    output_delivery: str
    schema_ref: str
    manifest_ref: str
    scope: str


@dataclass(frozen=True)
class JudgePromptContract:
    """Judge's prompt contract (AC-FR2900-01).

    Attributes:
        role: Always ``judge``.
        responsibilities: Tuple of declared duties.
        forbidden_actions: Tuple of forbidden side effects.
        output_delivery: Output delivery destination.
        schema_ref: Program-owned schema reference.
        manifest_ref: Program-owned manifest reference.
        scope: ``read-only`` (required).
    """

    role: str
    responsibilities: tuple[str, ...]
    forbidden_actions: tuple[str, ...]
    output_delivery: str
    schema_ref: str
    manifest_ref: str
    scope: str


@dataclass(frozen=True)
class LibrarianPromptContract:
    """Librarian's prompt contract (AC-FR2900-01).

    Attributes:
        role: Always ``librarian``.
        responsibilities: Tuple of declared duties.
        forbidden_actions: Tuple of forbidden side effects.
        output_delivery: Output delivery destination.
        schema_ref: Program-owned schema reference.
        manifest_ref: Program-owned manifest reference.
        scope: ``restricted-write`` (required).
        required_by_definition: ``True`` if WorkflowDefinition requires Librarian.
    """

    role: str
    responsibilities: tuple[str, ...]
    forbidden_actions: tuple[str, ...]
    output_delivery: str
    schema_ref: str
    manifest_ref: str
    scope: str
    required_by_definition: bool = False


@dataclass(frozen=True)
class ReviewPromptBundle:
    """The three-role review prompt bundle (AC-FR2900-01)."""

    prism: PrismPromptContract
    judge: JudgePromptContract
    librarian: LibrarianPromptContract


def parse_review_prompt(source: dict[str, Any]) -> ReviewPromptBundle:
    """Parse the three-role review prompt bundle (AC-FR2900-01)."""
    p = source["prism"]
    j = source["judge"]
    lib = source["librarian"]
    return ReviewPromptBundle(
        prism=PrismPromptContract(
            role=str(p.get("role", "prism")),
            review_kinds=tuple(p.get("review_kinds", ()) or ()),
            forbidden_actions=tuple(p.get("forbidden_actions", ()) or ()),
            output_delivery=str(p.get("output_delivery", "")),
            schema_ref=str(p.get("schema_ref", "")),
            manifest_ref=str(p.get("manifest_ref", "")),
            scope=str(p.get("scope", "")),
        ),
        judge=JudgePromptContract(
            role=str(j.get("role", "judge")),
            responsibilities=tuple(j.get("responsibilities", ()) or ()),
            forbidden_actions=tuple(j.get("forbidden_actions", ()) or ()),
            output_delivery=str(j.get("output_delivery", "")),
            schema_ref=str(j.get("schema_ref", "")),
            manifest_ref=str(j.get("manifest_ref", "")),
            scope=str(j.get("scope", "")),
        ),
        librarian=LibrarianPromptContract(
            role=str(lib.get("role", "librarian")),
            responsibilities=tuple(lib.get("responsibilities", ()) or ()),
            forbidden_actions=tuple(lib.get("forbidden_actions", ()) or ()),
            output_delivery=str(lib.get("output_delivery", "")),
            schema_ref=str(lib.get("schema_ref", "")),
            manifest_ref=str(lib.get("manifest_ref", "")),
            scope=str(lib.get("scope", "")),
            required_by_definition=bool(lib.get("required_by_definition", False)),
        ),
    )


def _check_schema_and_manifest(role: str, schema_ref: str, manifest_ref: str) -> None:
    if not schema_ref or not manifest_ref:
        raise ReviewPromptContractError(
            "REVIEW_PROMPT_SCHEMA_INVALID",
            f"role {role!r} must reference program-owned schema + manifest",
        )


def verify_prism_contract(contract: PrismPromptContract) -> None:
    """Verify Prism's prompt contract (AC-FR2900-01)."""
    missing_kinds = _PRISM_REQUIRED_REVIEW_KINDS - set(contract.review_kinds)
    if missing_kinds:
        raise ReviewPromptContractError(
            "PRISM_REVIEW_KIND_INCOMPLETE",
            f"missing review kinds: {sorted(missing_kinds)}",
        )
    missing_forbidden = _PRISM_REQUIRED_FORBIDDEN - set(contract.forbidden_actions)
    if missing_forbidden:
        raise ReviewPromptContractError(
            "PRISM_SIDE_EFFECT_FORBIDDEN",
            f"missing forbidden actions: {sorted(missing_forbidden)}",
        )
    if contract.scope != "read-only":
        raise ReviewPromptContractError(
            "PRISM_SCOPE_INVALID",
            f"scope {contract.scope!r} must be 'read-only'",
        )
    _check_schema_and_manifest(
        contract.role, contract.schema_ref, contract.manifest_ref
    )


def verify_judge_contract(contract: JudgePromptContract) -> None:
    """Verify Judge's prompt contract (AC-FR2900-01)."""
    missing_resp = _JUDGE_REQUIRED_RESPONSIBILITIES - set(contract.responsibilities)
    if missing_resp:
        raise ReviewPromptContractError(
            "JUDGE_RESPONSIBILITY_INCOMPLETE",
            f"missing responsibilities: {sorted(missing_resp)}",
        )
    missing_forbidden = _JUDGE_REQUIRED_FORBIDDEN - set(contract.forbidden_actions)
    if missing_forbidden:
        raise ReviewPromptContractError(
            "JUDGE_SIDE_EFFECT_FORBIDDEN",
            f"missing forbidden actions: {sorted(missing_forbidden)}",
        )
    if contract.scope != "read-only":
        raise ReviewPromptContractError(
            "JUDGE_SCOPE_INVALID",
            f"scope {contract.scope!r} must be 'read-only'",
        )
    _check_schema_and_manifest(
        contract.role, contract.schema_ref, contract.manifest_ref
    )


def verify_librarian_contract(contract: LibrarianPromptContract) -> None:
    """Verify Librarian's prompt contract (AC-FR2900-01).

    Note: non-required Librarian does NOT block milestone; this verifier
    still validates the contract shape so that any future required flag
    is honoured consistently.
    """
    missing_resp = _LIBRARIAN_REQUIRED_RESPONSIBILITIES - set(contract.responsibilities)
    if missing_resp:
        raise ReviewPromptContractError(
            "LIBRARIAN_RESPONSIBILITY_INCOMPLETE",
            f"missing responsibilities: {sorted(missing_resp)}",
        )
    missing_forbidden = _LIBRARIAN_REQUIRED_FORBIDDEN - set(contract.forbidden_actions)
    if missing_forbidden:
        raise ReviewPromptContractError(
            "LIBRARIAN_SIDE_EFFECT_FORBIDDEN",
            f"missing forbidden actions: {sorted(missing_forbidden)}",
        )
    if contract.scope != "restricted-write":
        raise ReviewPromptContractError(
            "LIBRARIAN_SCOPE_INVALID",
            f"scope {contract.scope!r} must be 'restricted-write'",
        )
    _check_schema_and_manifest(
        contract.role, contract.schema_ref, contract.manifest_ref
    )
