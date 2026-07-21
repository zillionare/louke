"""AC-FR2800-01: Archer, Devon & Shield prompt contract.

The locked prompt bundle must constrain: Archer only outputs implementation
task graph/advisory (no GitHub tasks, no flow advancement); Devon only edits
authorised unit tests + implementation per manifest/phase (Red/Green/Refactor
rules clear, no commit/push/install/hook-bypass/Issue-close/gate-evidence/
stage-advance); Shield only writes authorised integration/e2e and returns
semantic handoff (no commit/push/program-PASS/Maestro-advance request).  All
three must reference program-owned schema + manifest identity, and must NOT
proactively request Human technical decisions.
"""

from __future__ import annotations

from typing import Any

import pytest

from louke.v014.fr2800_impl_prompts import (
    ImplPromptBundle,
    ImplPromptContractError,
    parse_impl_prompt,
    verify_devon_contract,
    verify_shield_contract,
    verify_archer_contract,
)


def _archer() -> dict[str, Any]:
    return {
        "role": "archer",
        "responsibilities": ("task-graph", "advisory"),
        "forbidden_actions": (
            "commit",
            "push",
            "issue-creation",
            "stage-advance",
            "review-persistence",
            "activation",
        ),
        "output_delivery": "Runtime/program",
        "schema_ref": "schema:archer-output:v1",
        "manifest_ref": "manifest:task-graph:v1",
        "protocol_refs": (),
    }


def _devon() -> dict[str, Any]:
    return {
        "role": "devon",
        "responsibilities": ("edit-unit-tests", "edit-implementation"),
        "forbidden_actions": (
            "commit",
            "push",
            "install",
            "hook-bypass",
            "issue-close",
            "gate-evidence",
            "stage-advance",
        ),
        "output_delivery": "Runtime/program",
        "schema_ref": "schema:devon-output:v1",
        "manifest_ref": "manifest:task-attempt:v1",
        "protocol_refs": (),
    }


def _shield() -> dict[str, Any]:
    return {
        "role": "shield",
        "responsibilities": ("write-integration-e2e", "return-semantic-handoff"),
        "forbidden_actions": ("commit", "push", "program-pass", "maestro-advance"),
        "output_delivery": "Runtime/program",
        "schema_ref": "schema:shield-output:v1",
        "manifest_ref": "manifest:test-asset:v1",
        "protocol_refs": (),
    }


def test_parse_impl_prompt_returns_bundle() -> None:
    """AC-FR2800-01: parse_impl_prompt returns the three-role bundle."""
    bundle = parse_impl_prompt(
        {
            "archer": _archer(),
            "devon": _devon(),
            "shield": _shield(),
        }
    )
    assert isinstance(bundle, ImplPromptBundle)
    assert bundle.archer.role == "archer"
    assert bundle.devon.role == "devon"
    assert bundle.shield.role == "shield"


def test_archer_contract_passes() -> None:
    """AC-FR2800-01: Archer only outputs task graph + advisory."""
    bundle = parse_impl_prompt(
        {
            "archer": _archer(),
            "devon": _devon(),
            "shield": _shield(),
        }
    )
    verify_archer_contract(bundle.archer)  # does not raise


def test_archer_contract_rejects_issue_creation() -> None:
    """AC-FR2800-01: Archer must not create GitHub Issues."""
    bad = _archer()
    bad["forbidden_actions"] = ("commit", "push")  # missing issue-creation
    with pytest.raises(ImplPromptContractError) as exc:
        verify_archer_contract(
            parse_impl_prompt(
                {
                    "archer": bad,
                    "devon": _devon(),
                    "shield": _shield(),
                }
            ).archer
        )
    assert exc.value.code == "ARCHER_SIDE_EFFECT_FORBIDDEN"


def test_devon_contract_passes() -> None:
    """AC-FR2800-01: Devon edits unit tests + impl per manifest/phase."""
    bundle = parse_impl_prompt(
        {
            "archer": _archer(),
            "devon": _devon(),
            "shield": _shield(),
        }
    )
    verify_devon_contract(bundle.devon)


def test_devon_contract_rejects_missing_hook_bypass_forbidden() -> None:
    """AC-FR2800-01: Devon must forbid hook bypass."""
    bad = _devon()
    bad["forbidden_actions"] = (
        "commit",
        "push",
        "install",
        "issue-close",
        "gate-evidence",
        "stage-advance",
    )
    # missing hook-bypass
    with pytest.raises(ImplPromptContractError) as exc:
        verify_devon_contract(
            parse_impl_prompt(
                {
                    "archer": _archer(),
                    "devon": bad,
                    "shield": _shield(),
                }
            ).devon
        )
    assert exc.value.code == "DEVON_SIDE_EFFECT_FORBIDDEN"


def test_shield_contract_passes() -> None:
    """AC-FR2800-01: Shield writes integration/e2e + returns semantic handoff."""
    bundle = parse_impl_prompt(
        {
            "archer": _archer(),
            "devon": _devon(),
            "shield": _shield(),
        }
    )
    verify_shield_contract(bundle.shield)


def test_shield_contract_rejects_program_pass_claim() -> None:
    """AC-FR2800-01: Shield must not declare program PASS."""
    bad = _shield()
    bad["forbidden_actions"] = (
        "commit",
        "push",
        "maestro-advance",
    )  # missing program-pass
    with pytest.raises(ImplPromptContractError) as exc:
        verify_shield_contract(
            parse_impl_prompt(
                {
                    "archer": _archer(),
                    "devon": _devon(),
                    "shield": bad,
                }
            ).shield
        )
    assert exc.value.code == "SHIELD_SIDE_EFFECT_FORBIDDEN"


def test_prompt_rejects_question_human_marker() -> None:
    """AC-FR2800-01: prompts must not direct questioning Human for tech decisions."""
    bad = _devon()
    bad["protocol_refs"] = ["ask Human to pick testing framework"]
    with pytest.raises(ImplPromptContractError) as exc:
        verify_devon_contract(
            parse_impl_prompt(
                {
                    "archer": _archer(),
                    "devon": bad,
                    "shield": _shield(),
                }
            ).devon
        )
    assert exc.value.code == "PROMPT_QUESTION_HUMAN_FORBIDDEN"


def test_prompt_bundle_immutable() -> None:
    """AC-FR2800-01: the parsed bundle is immutable."""
    bundle = parse_impl_prompt(
        {
            "archer": _archer(),
            "devon": _devon(),
            "shield": _shield(),
        }
    )
    with pytest.raises(Exception):
        bundle.archer.role = "tampered"  # type: ignore[misc]
