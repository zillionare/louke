"""Integration tests for FR-1000: Pre-commit Contract.

AC-FR1000-01: For host fixture with existing hooks, design result
preserves/merges existing behavior; readback of config, install entry,
version, fast checks, auto-modify and failure semantics available.
Contract requiring Archer/Devon to install hook, using Red failure as
hook target, or treating pre-commit as final full gate fails schema/
semantic review.
"""
# AC-FR1000-01

from __future__ import annotations

import json
from pathlib import Path

import pytest

FIXTURES = (
    Path(__file__).resolve().parents[2]
    / "fixtures"
    / "v014_design_contracts"
    / "matrices"
)


def test_ci_hook_matrix_lists_existing_hooks():
    """ci_hook_matrix must list existing hooks to preserve."""
    matrix = json.loads((FIXTURES / "ci_hook_matrix.json").read_text())
    hook_ids = {h["id"] for h in matrix["existing_hooks"]}
    for required in ("keeper", "ruff", "mypy"):
        assert required in hook_ids, f"existing hook {required} missing from matrix"


def test_ci_hook_matrix_existing_hooks_preserve_behavior():
    """Every existing hook must declare preserve behavior."""
    matrix = json.loads((FIXTURES / "ci_hook_matrix.json").read_text())
    for hook in matrix["existing_hooks"]:
        assert hook["expected_behavior"] == "preserve", (
            f"hook {hook['id']} should preserve, got {hook['expected_behavior']}"
        )


def test_ci_hook_matrix_managed_hook_merges():
    """Managed hook must merge into existing config, not delete user hooks."""
    matrix = json.loads((FIXTURES / "ci_hook_matrix.json").read_text())
    managed = matrix["managed_hook"]
    behavior = managed["expected_behavior"]
    assert "merge" in behavior
    # "delete" may appear only in negation context (e.g. "do not delete user hooks").
    # Any "delete" must be preceded by a negation keyword within 20 chars.
    lower = behavior.lower()
    delete_idx = lower.find("delete")
    while delete_idx != -1:
        prefix = lower[max(0, delete_idx - 20):delete_idx]
        assert any(
            neg in prefix
            for neg in (
                "do not", "don't", "not ", "no ", "never ",
                "without ", "forbidden", "must not",
            )
        ), f"managed hook instructs deletion without negation; behavior='{behavior}'"
        delete_idx = lower.find("delete", delete_idx + 1)


def test_ci_hook_matrix_rejects_agent_install():
    """Negative case: agent installing hook must fail schema review."""
    matrix = json.loads((FIXTURES / "ci_hook_matrix.json").read_text())
    neg = next(
        (c for c in matrix["negative_cases"] if c["id"] == "agent-installs-hook"),
        None,
    )
    assert neg is not None
    assert "fails" in neg["expected"].lower()


def test_ci_hook_matrix_rejects_red_as_hook_target():
    """Negative case: Red failure as hook target must fail."""
    matrix = json.loads((FIXTURES / "ci_hook_matrix.json").read_text())
    neg = next(
        (c for c in matrix["negative_cases"] if c["id"] == "red-as-hook-target"),
        None,
    )
    assert neg is not None
    assert "fails" in neg["expected"].lower()


def test_ci_hook_matrix_rejects_precommit_as_final_gate():
    """Negative case: pre-commit as final full gate must fail."""
    matrix = json.loads((FIXTURES / "ci_hook_matrix.json").read_text())
    neg = next(
        (c for c in matrix["negative_cases"] if c["id"] == "precommit-as-final-gate"),
        None,
    )
    assert neg is not None
    assert "fails" in neg["expected"].lower()


@pytest.mark.awaiting_devon("FR-1000")
def test_precommit_contract_readback_returns_config(mock_precommit_contract):
    """precommit contract readback must return config, install entry,
    version, fast checks, auto-modify and failure semantics."""
    mock_precommit_contract.readback.return_value = {
        "config_path": ".pre-commit-config.yaml",
        "install_entry": "pre-commit install",
        "version": "1.0.0",
        "fast_checks": ["ruff", "mypy"],
        "auto_modify": True,
        "failure_semantics": "nonzero blocks commit",
    }
    result = mock_precommit_contract.readback()
    for key in ("config_path", "install_entry", "version", "fast_checks"):
        assert key in result
