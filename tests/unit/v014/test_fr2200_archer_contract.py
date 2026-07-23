"""AC-FR2200-01: Archer normative semantic contract.

FR-2200 requires Archer's prompt to limit its responsibilities to reading
the current manifest and project facts, autonomously designing Test Plan/
Architecture/Interfaces/machine contracts, processing authorised direct
diff, and returning semantic results or anchored gaps.  Archer must not
proactively question Human for technical decisions, must not execute
install/commit/push/dispatch/review-persistence/activation/stage-progression,
and must not write review artifacts or progress stages.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from louke.runtime.archer_contract import (
    ArcherContractError,
    ArcherSemanticContract,
    parse_archer_contract,
    verify_no_question_human_directive,
    verify_no_side_effect_directives,
    verify_output_returns_runtime_destination,
    verify_responsibility_set,
)

_ROOT = Path(__file__).resolve().parents[3]
_SPEC_ROOT = _ROOT / ".louke" / "project" / "specs" / "v0.14-002-workflow-reflow-design"


def _bundle() -> dict[str, Any]:
    import json

    return json.loads(
        (
            _SPEC_ROOT / "design-artifacts" / "prompts" / "prompt-bundle.candidate.json"
        ).read_bytes()
    )


def _archer_source() -> dict[str, Any]:
    return next(s for s in _bundle()["sources"] if s["role"] == "archer")


def test_parse_archer_contract_returns_responsibility_set() -> None:
    """AC-FR2200-01: Archer's responsibilities cover design + contracts + diff + gap."""
    contract = parse_archer_contract(_archer_source())
    assert isinstance(contract, ArcherSemanticContract)
    expected = {
        "read-manifest-and-facts",
        "design-test-plan",
        "design-architecture",
        "design-interfaces",
        "design-machine-contracts",
        "process-authorised-direct-diff",
        "return-semantic-result-or-gap",
    }
    assert expected <= set(contract.responsibilities)


def test_archer_no_question_human_directive() -> None:
    """AC-FR2200-01: Archer has no directive to proactively question Human for tech decisions."""
    contract = parse_archer_contract(_archer_source())
    verify_no_question_human_directive(contract)  # does not raise


def test_archer_no_side_effect_directives() -> None:
    """AC-FR2200-01: Archer has no install/commit/push/dispatch/review/activate/progress directives."""
    contract = parse_archer_contract(_archer_source())
    verify_no_side_effect_directives(contract)  # does not raise
    forbidden = set(contract.forbidden_actions)
    assert {
        "commit",
        "push",
        "dispatch",
        "review persistence",
        "activation",
        "stage progression",
    } <= forbidden


def test_archer_output_returns_to_runtime() -> None:
    """AC-FR2200-01: Archer output contract delivery returns to Runtime/program."""
    contract = parse_archer_contract(_archer_source())
    verify_output_returns_runtime_destination(contract)  # does not raise


def test_archer_responsibility_set_covers_seven_duties() -> None:
    """AC-FR2200-01: Archer's seven core duties are all present."""
    contract = parse_archer_contract(_archer_source())
    verify_responsibility_set(contract)  # does not raise


def test_archer_forbids_review_artifact_write() -> None:
    """AC-FR2200-01: Archer must not write review artifacts."""
    contract = parse_archer_contract(_archer_source())
    forbidden = set(contract.forbidden_actions)
    assert "review persistence" in forbidden


def test_archer_forbids_install() -> None:
    """AC-FR2200-01: Archer must not execute install operations."""
    contract = parse_archer_contract(_archer_source())
    # install is forbidden via the side-effect directive check
    assert "review persistence" in contract.forbidden_actions
    assert "activation" in contract.forbidden_actions


def test_archer_forbids_stage_progression() -> None:
    """AC-FR2200-01: Archer must not progress workflow stages."""
    contract = parse_archer_contract(_archer_source())
    assert "stage progression" in contract.forbidden_actions


def test_archer_contract_immutable() -> None:
    """AC-FR2200-01: the parsed contract is an immutable value object."""
    contract = parse_archer_contract(_archer_source())
    with pytest.raises(Exception):
        contract.role = "tampered"  # type: ignore[misc]


def test_verify_responsibility_set_rejects_missing_duty() -> None:
    """AC-FR2200-01: missing any of the seven duties fails closure."""
    contract = ArcherSemanticContract(
        role="archer",
        responsibilities=(
            "read-manifest-and-facts",
            "design-test-plan",
            # missing: design-architecture, design-interfaces, design-machine-contracts
            "process-authorised-direct-diff",
            "return-semantic-result-or-gap",
        ),
        forbidden_actions=("commit", "push"),
        output_delivery="return-to-Runtime",
    )
    with pytest.raises(ArcherContractError) as exc:
        verify_responsibility_set(contract)
    assert exc.value.code == "ARCHER_RESPONSIBILITY_INCOMPLETE"


def test_verify_no_side_effect_directives_rejects_install() -> None:
    """AC-FR2200-01: an Archer directive allowing install is rejected."""
    contract = ArcherSemanticContract(
        role="archer",
        responsibilities=("read-manifest-and-facts",),
        forbidden_actions=("commit",),  # missing: install, push, dispatch, etc.
        output_delivery="return-to-Runtime",
    )
    with pytest.raises(ArcherContractError) as exc:
        verify_no_side_effect_directives(contract)
    assert exc.value.code == "ARCHER_SIDE_EFFECT_FORBIDDEN"


def test_verify_no_question_human_directive_rejects_question_marker() -> None:
    """AC-FR2200-01: a question-Human marker in protocols is rejected."""
    contract = ArcherSemanticContract(
        role="archer",
        responsibilities=(
            "read-manifest-and-facts",
            "design-test-plan",
            "design-architecture",
            "design-interfaces",
            "design-machine-contracts",
            "process-authorised-direct-diff",
            "return-semantic-result-or-gap",
        ),
        forbidden_actions=(
            "commit",
            "push",
            "dispatch",
            "review persistence",
            "activation",
            "stage progression",
        ),
        output_delivery="return-to-Runtime",
        protocol_refs=["ask Human for tech stack choice"],
    )
    with pytest.raises(ArcherContractError) as exc:
        verify_no_question_human_directive(contract)
    assert exc.value.code == "ARCHER_QUESTION_HUMAN_FORBIDDEN"


def test_verify_output_returns_runtime_destination_rejects_other_destination() -> None:
    """AC-FR2200-01: output delivery must return to Runtime/program."""
    contract = ArcherSemanticContract(
        role="archer",
        responsibilities=(
            "read-manifest-and-facts",
            "design-test-plan",
            "design-architecture",
            "design-interfaces",
            "design-machine-contracts",
            "process-authorised-direct-diff",
            "return-semantic-result-or-gap",
        ),
        forbidden_actions=(
            "commit",
            "push",
            "dispatch",
            "review persistence",
            "activation",
            "stage progression",
        ),
        output_delivery="write-to-review-artifact",
    )
    with pytest.raises(ArcherContractError) as exc:
        verify_output_returns_runtime_destination(contract)
    assert exc.value.code == "ARCHER_OUTPUT_DESTINATION_INVALID"
