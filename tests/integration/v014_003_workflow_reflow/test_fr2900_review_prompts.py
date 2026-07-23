"""Integration tests for FR-2900: Prism, Judge & Librarian prompt contract.

AC-FR2900-01: Prism's multiple review kinds, Judge's security review,
and Librarian's authorised docs task all have explicit schema ref +
read-only/restricted-write scope, and their results bind to input
identity. None of the three may execute Git/GitHub/program gate/state
advancement or self-persist PASS. Non-required Librarian does NOT block
milestone.

Interfaces covered (per interfaces.md):
- IF-PROMPT-02 (Primary ARC-01)
- IF-REV-02 (Prism review kinds, ARC-07)
- IF-SEC-01 (Judge scope, ARC-13)
"""
# AC-FR2900-01

from __future__ import annotations

import pytest

from louke.runtime.review_prompts import (
    ERROR_CODES,
    JudgePromptContract,
    LibrarianPromptContract,
    PrismPromptContract,
    ReviewPromptBundle,
    ReviewPromptContractError,
    parse_review_prompt,
    verify_judge_contract,
    verify_librarian_contract,
    verify_prism_contract,
)


def _valid_prism() -> PrismPromptContract:
    return PrismPromptContract(
        role="prism",
        review_kinds=("task_graph", "red", "final_task", "shield_tests", "candidate"),
        forbidden_actions=(
            "commit",
            "push",
            "program-gate",
            "state-advance",
            "pass-persistence",
        ),
        output_delivery="verdict-proposal",
        schema_ref="louke.agent-io.prism-review-1.0.0.schema.json",
        manifest_ref="manifest:prism:1.0.0",
        scope="read-only",
    )


def _valid_judge() -> JudgePromptContract:
    return JudgePromptContract(
        role="judge",
        responsibilities=("deep-semantic-security-review",),
        forbidden_actions=(
            "commit",
            "push",
            "program-gate",
            "state-advance",
            "pass-persistence",
            "code-modification",
        ),
        output_delivery="finding-verdict",
        schema_ref="louke.agent-io.judge-verdict-1.0.0.schema.json",
        manifest_ref="manifest:judge:1.0.0",
        scope="read-only",
    )


def _valid_librarian() -> LibrarianPromptContract:
    return LibrarianPromptContract(
        role="librarian",
        responsibilities=("edit-authorised-docs",),
        forbidden_actions=(
            "commit",
            "push",
            "program-gate",
            "state-advance",
            "release-fact-modification",
            "pass-persistence",
        ),
        output_delivery="doc-edit-proposal",
        schema_ref="louke.agent-io.librarian-doc-edit-1.0.0.schema.json",
        manifest_ref="manifest:librarian:1.0.0",
        scope="restricted-write",
    )


# ---------------------------------------------------------------------------
# Prism contract
# ---------------------------------------------------------------------------


@pytest.mark.real_module
def test_verify_prism_contract_passes_with_all_review_kinds():
    """AC-FR2900-01: Prism with 5 review kinds + read-only scope -> OK."""
    verify_prism_contract(_valid_prism())  # no raise


@pytest.mark.real_module
def test_verify_prism_contract_rejects_missing_review_kind():
    """AC-FR2900-01: Prism must support all 5 review kinds."""
    bad = PrismPromptContract(
        role="prism",
        review_kinds=(
            "task_graph",
            "red",
        ),  # missing final_task, shield_tests, candidate
        forbidden_actions=_valid_prism().forbidden_actions,
        output_delivery="x",
        schema_ref="x",
        manifest_ref="x",
        scope="read-only",
    )
    with pytest.raises(ReviewPromptContractError) as exc:
        verify_prism_contract(bad)
    assert exc.value.code == "PRISM_REVIEW_KIND_INCOMPLETE"


@pytest.mark.real_module
def test_verify_prism_contract_rejects_non_read_only_scope():
    """AC-FR2900-01: Prism scope must be read-only."""
    bad = PrismPromptContract(
        role="prism",
        review_kinds=_valid_prism().review_kinds,
        forbidden_actions=_valid_prism().forbidden_actions,
        output_delivery="x",
        schema_ref="x",
        manifest_ref="x",
        scope="read-write",  # wrong
    )
    with pytest.raises(ReviewPromptContractError) as exc:
        verify_prism_contract(bad)
    assert exc.value.code == "PRISM_SCOPE_INVALID"


@pytest.mark.real_module
def test_verify_prism_contract_rejects_missing_forbidden_pass_persistence():
    """AC-FR2900-01: Prism must NOT self-persist PASS."""
    bad = PrismPromptContract(
        role="prism",
        review_kinds=_valid_prism().review_kinds,
        forbidden_actions=(
            "commit",
            "push",
            "program-gate",
            "state-advance",
        ),  # missing pass-persistence
        output_delivery="x",
        schema_ref="x",
        manifest_ref="x",
        scope="read-only",
    )
    with pytest.raises(ReviewPromptContractError) as exc:
        verify_prism_contract(bad)
    assert exc.value.code == "PRISM_SIDE_EFFECT_FORBIDDEN"


# ---------------------------------------------------------------------------
# Judge contract
# ---------------------------------------------------------------------------


@pytest.mark.real_module
def test_verify_judge_contract_passes_with_semantic_review():
    """AC-FR2900-01: Judge with deep-semantic-security-review -> OK."""
    verify_judge_contract(_valid_judge())  # no raise


@pytest.mark.real_module
def test_verify_judge_contract_rejects_missing_semantic_review():
    """AC-FR2900-01: Judge must do deep semantic security review (not program scan)."""
    bad = JudgePromptContract(
        role="judge",
        responsibilities=("program-scan",),  # wrong responsibility
        forbidden_actions=_valid_judge().forbidden_actions,
        output_delivery="x",
        schema_ref="x",
        manifest_ref="x",
        scope="read-only",
    )
    with pytest.raises(ReviewPromptContractError) as exc:
        verify_judge_contract(bad)
    assert exc.value.code == "JUDGE_RESPONSIBILITY_INCOMPLETE"


@pytest.mark.real_module
def test_verify_judge_contract_rejects_missing_forbidden_code_modification():
    """AC-FR2900-01: Judge must NOT modify code."""
    bad = JudgePromptContract(
        role="judge",
        responsibilities=_valid_judge().responsibilities,
        forbidden_actions=(
            "commit",
            "push",
            "program-gate",
            "state-advance",
            "pass-persistence",
        ),  # missing code-modification
        output_delivery="x",
        schema_ref="x",
        manifest_ref="x",
        scope="read-only",
    )
    with pytest.raises(ReviewPromptContractError) as exc:
        verify_judge_contract(bad)
    assert exc.value.code == "JUDGE_SIDE_EFFECT_FORBIDDEN"


@pytest.mark.real_module
def test_verify_judge_contract_rejects_non_read_only_scope():
    """AC-FR2900-01: Judge scope must be read-only."""
    bad = JudgePromptContract(
        role="judge",
        responsibilities=_valid_judge().responsibilities,
        forbidden_actions=_valid_judge().forbidden_actions,
        output_delivery="x",
        schema_ref="x",
        manifest_ref="x",
        scope="read-write",  # wrong
    )
    with pytest.raises(ReviewPromptContractError) as exc:
        verify_judge_contract(bad)
    assert exc.value.code == "JUDGE_SCOPE_INVALID"


# ---------------------------------------------------------------------------
# Librarian contract
# ---------------------------------------------------------------------------


@pytest.mark.real_module
def test_verify_librarian_contract_passes_with_restricted_write():
    """AC-FR2900-01: Librarian with edit-authorised-docs + restricted-write -> OK."""
    verify_librarian_contract(_valid_librarian())  # no raise


@pytest.mark.real_module
def test_verify_librarian_contract_rejects_wrong_scope():
    """AC-FR2900-01: Librarian scope must be restricted-write (not read-only)."""
    bad = LibrarianPromptContract(
        role="librarian",
        responsibilities=_valid_librarian().responsibilities,
        forbidden_actions=_valid_librarian().forbidden_actions,
        output_delivery="x",
        schema_ref="x",
        manifest_ref="x",
        scope="read-only",  # wrong
    )
    with pytest.raises(ReviewPromptContractError) as exc:
        verify_librarian_contract(bad)
    assert exc.value.code == "LIBRARIAN_SCOPE_INVALID"


@pytest.mark.real_module
def test_verify_librarian_contract_rejects_missing_forbidden_release_fact_modification():
    """AC-FR2900-01: Librarian must NOT modify release facts."""
    bad = LibrarianPromptContract(
        role="librarian",
        responsibilities=_valid_librarian().responsibilities,
        forbidden_actions=(
            "commit",
            "push",
            "program-gate",
            "state-advance",
            "pass-persistence",
        ),  # missing release-fact-modification
        output_delivery="x",
        schema_ref="x",
        manifest_ref="x",
        scope="restricted-write",
    )
    with pytest.raises(ReviewPromptContractError) as exc:
        verify_librarian_contract(bad)
    assert exc.value.code == "LIBRARIAN_SIDE_EFFECT_FORBIDDEN"


# ---------------------------------------------------------------------------
# Schema/manifest requirement
# ---------------------------------------------------------------------------


@pytest.mark.real_module
def test_verify_contract_rejects_missing_schema_ref():
    """AC-FR2900-01: every role must reference program-owned schema + manifest."""
    bad = PrismPromptContract(
        role="prism",
        review_kinds=_valid_prism().review_kinds,
        forbidden_actions=_valid_prism().forbidden_actions,
        output_delivery="x",
        schema_ref="",  # missing
        manifest_ref="x",
        scope="read-only",
    )
    with pytest.raises(ReviewPromptContractError) as exc:
        verify_prism_contract(bad)
    assert exc.value.code == "REVIEW_PROMPT_SCHEMA_INVALID"


@pytest.mark.real_module
def test_parse_review_prompt_returns_three_role_bundle():
    """AC-FR2900-01: parse returns Prism+Judge+Librarian bundle."""
    source = {
        "prism": {
            "role": "prism",
            "review_kinds": (
                "task_graph",
                "red",
                "final_task",
                "shield_tests",
                "candidate",
            ),
            "forbidden_actions": (
                "commit",
                "push",
                "program-gate",
                "state-advance",
                "pass-persistence",
            ),
            "output_delivery": "x",
            "schema_ref": "x",
            "manifest_ref": "x",
            "scope": "read-only",
        },
        "judge": {
            "role": "judge",
            "responsibilities": ("deep-semantic-security-review",),
            "forbidden_actions": (
                "commit",
                "push",
                "program-gate",
                "state-advance",
                "pass-persistence",
                "code-modification",
            ),
            "output_delivery": "x",
            "schema_ref": "x",
            "manifest_ref": "x",
            "scope": "read-only",
        },
        "librarian": {
            "role": "librarian",
            "responsibilities": ("edit-authorised-docs",),
            "forbidden_actions": (
                "commit",
                "push",
                "program-gate",
                "state-advance",
                "release-fact-modification",
                "pass-persistence",
            ),
            "output_delivery": "x",
            "schema_ref": "x",
            "manifest_ref": "x",
            "scope": "restricted-write",
        },
    }
    bundle = parse_review_prompt(source)
    assert isinstance(bundle, ReviewPromptBundle)
    assert bundle.prism.role == "prism"
    assert bundle.judge.role == "judge"
    assert bundle.librarian.role == "librarian"


@pytest.mark.real_module
def test_error_codes_set_covers_all_documented_codes():
    """AC-FR2900-01: ERROR_CODES includes all codes from interfaces.md §15."""
    expected = {
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
    }
    actual = set(ERROR_CODES)
    missing = expected - actual
    assert not missing, f"ERROR_CODES missing: {missing}"
