"""AC-FR2900-01: Prism, Judge & Librarian prompt contract.

Prism reviews task graph / Red / final task / Shield tests / candidate
with multiple review kinds, each with explicit schema ref and read-only/
restricted-write scope, returning verdict bound to input identity.  Judge
only does deep semantic security review; program scan and gate execution
are Runtime's responsibility.  Librarian only edits authorised knowledge/
user docs when definition requires; non-required Librarian does NOT block
milestone.  None of the three may persist their own PASS, execute Git/
GitHub/program gate/state advancement.
"""

from __future__ import annotations

from typing import Any

import pytest

from louke.v014.fr2900_review_prompts import (
    ReviewPromptBundle,
    ReviewPromptContractError,
    parse_review_prompt,
    verify_judge_contract,
    verify_librarian_contract,
    verify_prism_contract,
)


def _prism() -> dict[str, Any]:
    return {
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
        "output_delivery": "Runtime/program",
        "schema_ref": "schema:prism-verdict:v1",
        "manifest_ref": "manifest:review:v1",
        "scope": "read-only",
    }


def _judge() -> dict[str, Any]:
    return {
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
        "output_delivery": "Runtime/program",
        "schema_ref": "schema:judge-verdict:v1",
        "manifest_ref": "manifest:security-review:v1",
        "scope": "read-only",
    }


def _librarian(*, required: bool = True) -> dict[str, Any]:
    return {
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
        "output_delivery": "Runtime/program",
        "schema_ref": "schema:librarian-output:v1",
        "manifest_ref": "manifest:docs:v1",
        "scope": "restricted-write",
        "required_by_definition": required,
    }


def test_parse_review_prompt_returns_bundle() -> None:
    """AC-FR2900-01: parse_review_prompt returns the three-role bundle."""
    bundle = parse_review_prompt(
        {
            "prism": _prism(),
            "judge": _judge(),
            "librarian": _librarian(),
        }
    )
    assert isinstance(bundle, ReviewPromptBundle)
    assert bundle.prism.role == "prism"
    assert bundle.judge.role == "judge"
    assert bundle.librarian.role == "librarian"


def test_prism_contract_passes() -> None:
    """AC-FR2900-01: Prism has all required review kinds + read-only scope."""
    bundle = parse_review_prompt(
        {
            "prism": _prism(),
            "judge": _judge(),
            "librarian": _librarian(),
        }
    )
    verify_prism_contract(bundle.prism)


def test_prism_contract_rejects_missing_review_kind() -> None:
    """AC-FR2900-01: Prism must support all 5 review kinds."""
    bad = _prism()
    bad["review_kinds"] = ("task_graph", "red")  # missing kinds
    with pytest.raises(ReviewPromptContractError) as exc:
        verify_prism_contract(
            parse_review_prompt(
                {
                    "prism": bad,
                    "judge": _judge(),
                    "librarian": _librarian(),
                }
            ).prism
        )
    assert exc.value.code == "PRISM_REVIEW_KIND_INCOMPLETE"


def test_prism_contract_rejects_write_scope() -> None:
    """AC-FR2900-01: Prism scope must be read-only."""
    bad = _prism()
    bad["scope"] = "write"
    with pytest.raises(ReviewPromptContractError) as exc:
        verify_prism_contract(
            parse_review_prompt(
                {
                    "prism": bad,
                    "judge": _judge(),
                    "librarian": _librarian(),
                }
            ).prism
        )
    assert exc.value.code == "PRISM_SCOPE_INVALID"


def test_judge_contract_passes() -> None:
    """AC-FR2900-01: Judge only does deep semantic security review."""
    bundle = parse_review_prompt(
        {
            "prism": _prism(),
            "judge": _judge(),
            "librarian": _librarian(),
        }
    )
    verify_judge_contract(bundle.judge)


def test_judge_contract_rejects_code_modification() -> None:
    """AC-FR2900-01: Judge must not modify code."""
    bad = _judge()
    bad["forbidden_actions"] = (
        "commit",
        "push",
        "program-gate",
        "state-advance",
        "pass-persistence",
    )  # missing code-modification
    with pytest.raises(ReviewPromptContractError) as exc:
        verify_judge_contract(
            parse_review_prompt(
                {
                    "prism": _prism(),
                    "judge": bad,
                    "librarian": _librarian(),
                }
            ).judge
        )
    assert exc.value.code == "JUDGE_SIDE_EFFECT_FORBIDDEN"


def test_librarian_contract_passes_when_required() -> None:
    """AC-FR2900-01: Librarian with definition-required docs task is accepted."""
    bundle = parse_review_prompt(
        {
            "prism": _prism(),
            "judge": _judge(),
            "librarian": _librarian(required=True),
        }
    )
    verify_librarian_contract(bundle.librarian)


def test_librarian_does_not_block_milestone_when_not_required() -> None:
    """AC-FR2900-01: non-required Librarian does not block milestone."""
    bundle = parse_review_prompt(
        {
            "prism": _prism(),
            "judge": _judge(),
            "librarian": _librarian(required=False),
        }
    )
    # verify_librarian_contract accepts; non-required does not block.
    verify_librarian_contract(bundle.librarian)
    assert bundle.librarian.required_by_definition is False


def test_librarian_contract_rejects_release_fact_modification() -> None:
    """AC-FR2900-01: Librarian must not modify release facts."""
    bad = _librarian()
    bad["forbidden_actions"] = ("commit", "push", "program-gate", "state-advance")
    # missing release-fact-modification
    with pytest.raises(ReviewPromptContractError) as exc:
        verify_librarian_contract(
            parse_review_prompt(
                {
                    "prism": _prism(),
                    "judge": _judge(),
                    "librarian": bad,
                }
            ).librarian
        )
    assert exc.value.code == "LIBRARIAN_SIDE_EFFECT_FORBIDDEN"


def test_no_role_may_persist_own_pass() -> None:
    """AC-FR2900-01: Prism/Judge/Librarian must not persist their own PASS."""
    for role_source, verify in [
        (_prism(), verify_prism_contract),
        (_judge(), verify_judge_contract),
        (_librarian(), verify_librarian_contract),
    ]:
        bad = dict(role_source)
        bad["forbidden_actions"] = tuple(
            a for a in bad["forbidden_actions"] if a != "pass-persistence"
        )
        with pytest.raises(ReviewPromptContractError):
            bundle = parse_review_prompt(
                {
                    "prism": bad if role_source["role"] == "prism" else _prism(),
                    "judge": bad if role_source["role"] == "judge" else _judge(),
                    "librarian": bad
                    if role_source["role"] == "librarian"
                    else _librarian(),
                }
            )
            if role_source["role"] == "prism":
                verify(bundle.prism)
            elif role_source["role"] == "judge":
                verify(bundle.judge)
            else:
                verify(bundle.librarian)
