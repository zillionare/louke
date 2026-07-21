"""Integration tests for FR-2800: Archer, Devon & Shield prompt contract.

AC-FR2800-01: The locked prompt bundle constrains Archer to task graph
+ advisory only (no GitHub task creation, no flow advancement); Devon
to authorised unit tests + implementation per manifest/phase (Red/
Green/Refactor rules clear, no commit/push/install/hook-bypass/Issue-
close/gate-evidence/stage-advance); Shield to authorised integration/
e2e + semantic handoff (no commit/push/program-PASS/Maestro-advance).
All three reference program-owned schema + manifest identity and must
NOT proactively request Human technical decisions.

Interfaces covered (per interfaces.md):
- IF-PROMPT-02 (Primary ARC-01)
- IF-TASK-01 (task graph scope, ARC-03)
"""
# AC-FR2800-01

from __future__ import annotations

import pytest

from louke.v014.fr2800_impl_prompts import (
    ERROR_CODES,
    ImplPromptBundle,
    ImplPromptContractError,
    RolePromptContract,
    parse_impl_prompt,
    verify_archer_contract,
    verify_devon_contract,
    verify_shield_contract,
)


def _valid_archer() -> RolePromptContract:
    return RolePromptContract(
        role="archer",
        responsibilities=("task-graph", "advisory"),
        forbidden_actions=(
            "commit",
            "push",
            "issue-creation",
            "stage-advance",
            "review-persistence",
            "activation",
        ),
        output_delivery="task-graph-proposal",
        schema_ref="louke.agent-io.archer-impl-task-input-1.0.0.schema.json",
        manifest_ref="manifest:archer:1.0.0",
        protocol_refs=(),
    )


def _valid_devon() -> RolePromptContract:
    return RolePromptContract(
        role="devon",
        responsibilities=("edit-unit-tests", "edit-implementation"),
        forbidden_actions=(
            "commit",
            "push",
            "install",
            "hook-bypass",
            "issue-close",
            "gate-evidence",
            "stage-advance",
        ),
        output_delivery="patch-proposal",
        schema_ref="louke.agent-io.devon-impl-task-input-1.0.0.schema.json",
        manifest_ref="manifest:devon:1.0.0",
        protocol_refs=(),
    )


def _valid_shield() -> RolePromptContract:
    return RolePromptContract(
        role="shield",
        responsibilities=("write-integration-e2e", "return-semantic-handoff"),
        forbidden_actions=("commit", "push", "program-pass", "maestro-advance"),
        output_delivery="test-patch-proposal",
        schema_ref="louke.agent-io.shield-impl-task-input-1.0.0.schema.json",
        manifest_ref="manifest:shield:1.0.0",
        protocol_refs=(),
    )


# ---------------------------------------------------------------------------
# Archer contract
# ---------------------------------------------------------------------------


@pytest.mark.real_module
def test_verify_archer_contract_passes_with_full_responsibilities():
    """AC-FR2800-01: Archer with task-graph+advisory + all forbidden -> OK."""
    verify_archer_contract(_valid_archer())  # no raise


@pytest.mark.real_module
def test_verify_archer_contract_rejects_missing_task_graph():
    """AC-FR2800-01: Archer must output task graph."""
    bad = RolePromptContract(
        role=_valid_archer().role,
        responsibilities=("advisory",),  # missing task-graph
        forbidden_actions=_valid_archer().forbidden_actions,
        output_delivery="x",
        schema_ref="x",
        manifest_ref="x",
    )
    with pytest.raises(ImplPromptContractError) as exc:
        verify_archer_contract(bad)
    assert exc.value.code == "ARCHER_RESPONSIBILITY_INCOMPLETE"


@pytest.mark.real_module
def test_verify_archer_contract_rejects_missing_forbidden_commit():
    """AC-FR2800-01: Archer must NOT commit."""
    bad = RolePromptContract(
        role=_valid_archer().role,
        responsibilities=_valid_archer().responsibilities,
        forbidden_actions=("push",),  # missing commit
        output_delivery="x",
        schema_ref="x",
        manifest_ref="x",
    )
    with pytest.raises(ImplPromptContractError) as exc:
        verify_archer_contract(bad)
    assert exc.value.code == "ARCHER_SIDE_EFFECT_FORBIDDEN"


@pytest.mark.real_module
def test_verify_archer_contract_rejects_question_human_marker():
    """AC-FR2800-01: Archer must NOT ask Human for technical decisions."""
    bad = RolePromptContract(
        role=_valid_archer().role,
        responsibilities=_valid_archer().responsibilities,
        forbidden_actions=_valid_archer().forbidden_actions,
        output_delivery="x",
        schema_ref="x",
        manifest_ref="x",
        protocol_refs=("ask human for design choice",),  # forbidden
    )
    with pytest.raises(ImplPromptContractError) as exc:
        verify_archer_contract(bad)
    assert exc.value.code == "PROMPT_QUESTION_HUMAN_FORBIDDEN"


# ---------------------------------------------------------------------------
# Devon contract
# ---------------------------------------------------------------------------


@pytest.mark.real_module
def test_verify_devon_contract_passes_with_full_responsibilities():
    """AC-FR2800-01: Devon with edit-unit-tests+edit-implementation -> OK."""
    verify_devon_contract(_valid_devon())  # no raise


@pytest.mark.real_module
def test_verify_devon_contract_rejects_missing_edit_unit_tests():
    """AC-FR2800-01: Devon must edit unit tests."""
    bad = RolePromptContract(
        role="devon",
        responsibilities=("edit-implementation",),  # missing edit-unit-tests
        forbidden_actions=_valid_devon().forbidden_actions,
        output_delivery="x",
        schema_ref="x",
        manifest_ref="x",
    )
    with pytest.raises(ImplPromptContractError) as exc:
        verify_devon_contract(bad)
    assert exc.value.code == "DEVON_RESPONSIBILITY_INCOMPLETE"


@pytest.mark.real_module
def test_verify_devon_contract_rejects_missing_forbidden_hook_bypass():
    """AC-FR2800-01: Devon must NOT bypass hooks."""
    bad = RolePromptContract(
        role="devon",
        responsibilities=_valid_devon().responsibilities,
        forbidden_actions=("commit", "push"),  # missing hook-bypass + others
        output_delivery="x",
        schema_ref="x",
        manifest_ref="x",
    )
    with pytest.raises(ImplPromptContractError) as exc:
        verify_devon_contract(bad)
    assert exc.value.code == "DEVON_SIDE_EFFECT_FORBIDDEN"


# ---------------------------------------------------------------------------
# Shield contract
# ---------------------------------------------------------------------------


@pytest.mark.real_module
def test_verify_shield_contract_passes_with_full_responsibilities():
    """AC-FR2800-01: Shield with write-integration-e2e+return-semantic-handoff -> OK."""
    verify_shield_contract(_valid_shield())  # no raise


@pytest.mark.real_module
def test_verify_shield_contract_rejects_missing_write_integration_e2e():
    """AC-FR2800-01: Shield must write integration/e2e."""
    bad = RolePromptContract(
        role="shield",
        responsibilities=("return-semantic-handoff",),  # missing write-integration-e2e
        forbidden_actions=_valid_shield().forbidden_actions,
        output_delivery="x",
        schema_ref="x",
        manifest_ref="x",
    )
    with pytest.raises(ImplPromptContractError) as exc:
        verify_shield_contract(bad)
    assert exc.value.code == "SHIELD_RESPONSIBILITY_INCOMPLETE"


@pytest.mark.real_module
def test_verify_shield_contract_rejects_missing_forbidden_program_pass():
    """AC-FR2800-01: Shield must NOT declare program PASS."""
    bad = RolePromptContract(
        role="shield",
        responsibilities=_valid_shield().responsibilities,
        forbidden_actions=("commit", "push", "maestro-advance"),  # missing program-pass
        output_delivery="x",
        schema_ref="x",
        manifest_ref="x",
    )
    with pytest.raises(ImplPromptContractError) as exc:
        verify_shield_contract(bad)
    assert exc.value.code == "SHIELD_SIDE_EFFECT_FORBIDDEN"


# ---------------------------------------------------------------------------
# Schema/manifest requirement
# ---------------------------------------------------------------------------


@pytest.mark.real_module
def test_verify_contract_rejects_missing_schema_ref():
    """AC-FR2800-01: every role must reference program-owned schema + manifest."""
    bad = RolePromptContract(
        role="archer",
        responsibilities=_valid_archer().responsibilities,
        forbidden_actions=_valid_archer().forbidden_actions,
        output_delivery="x",
        schema_ref="",  # missing
        manifest_ref="x",
    )
    with pytest.raises(ImplPromptContractError) as exc:
        verify_archer_contract(bad)
    assert exc.value.code == "PROMPT_SCHEMA_INVALID"


@pytest.mark.real_module
def test_parse_impl_prompt_returns_three_role_bundle():
    """AC-FR2800-01: parse_impl_prompt returns Archer+Devon+Shield bundle."""
    source = {
        "archer": {
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
            "output_delivery": "x",
            "schema_ref": "x",
            "manifest_ref": "x",
        },
        "devon": {
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
            "output_delivery": "x",
            "schema_ref": "x",
            "manifest_ref": "x",
        },
        "shield": {
            "role": "shield",
            "responsibilities": ("write-integration-e2e", "return-semantic-handoff"),
            "forbidden_actions": ("commit", "push", "program-pass", "maestro-advance"),
            "output_delivery": "x",
            "schema_ref": "x",
            "manifest_ref": "x",
        },
    }
    bundle = parse_impl_prompt(source)
    assert isinstance(bundle, ImplPromptBundle)
    assert bundle.archer.role == "archer"
    assert bundle.devon.role == "devon"
    assert bundle.shield.role == "shield"


@pytest.mark.real_module
def test_error_codes_set_covers_all_documented_codes():
    """AC-FR2800-01: ERROR_CODES includes all codes from interfaces.md §15."""
    expected = {
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
    }
    actual = set(ERROR_CODES)
    missing = expected - actual
    assert not missing, f"ERROR_CODES missing: {missing}"
