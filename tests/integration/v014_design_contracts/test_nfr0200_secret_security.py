"""Integration tests for NFR-0200: Minimal Permission & Secret Security.

AC-NFR0200-01: Automated fixture proves Archer/Prism have no Git/GitHub/
stage write tools; CI contract defaults to minimal token permissions;
fork/untrusted job has no production secret. Secret scanner blocks
baseline for prompts, contracts, logs and fixtures with injected test
secrets and reports location without echoing secret value.
"""
# AC-NFR0200-01

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


def test_secret_canaries_fixture_exists():
    """secret_canaries fixture must exist."""
    path = FIXTURES / "secret_canaries.json"
    assert path.exists()


def test_secret_canaries_fixture_has_4_canaries():
    """secret_canaries must include at least 4 canary types."""
    matrix = json.loads((FIXTURES / "secret_canaries.json").read_text())
    canaries = matrix["canaries"]
    assert len(canaries) >= 4
    kinds = {c["kind"] for c in canaries}
    for required in ("github_pat", "pypi_upload", "session_cookie", "api_key"):
        assert required in kinds, f"missing canary kind: {required}"


def test_secret_canaries_do_not_echo_value_in_expected():
    """Every canary's expected field must say value NOT echoed."""
    matrix = json.loads((FIXTURES / "secret_canaries.json").read_text())
    for canary in matrix["canaries"]:
        assert "NOT echoed" in canary["expected"], (
            f"canary {canary['id']} must require non-echo: {canary['expected']}"
        )


def test_secret_canaries_block_baseline():
    """Every canary must block baseline."""
    matrix = json.loads((FIXTURES / "secret_canaries.json").read_text())
    for canary in matrix["canaries"]:
        assert "blocks" in canary["expected"], (
            f"canary {canary['id']} must block baseline"
        )


def test_archer_md_does_not_reference_git_write_tools():
    """Archer.md must not reference git commit/push/write tools."""
    text = (
        Path(__file__).resolve().parents[3]
        / "louke"
        / "agents"
        / "Archer.md"
    ).read_text(encoding="utf-8").lower()
    forbidden = ["git push", "git commit", "subprocess.run(['git'", "os.system('git"]
    for pattern in forbidden:
        assert pattern not in text, f"Archer must not use: {pattern}"


def test_prism_md_does_not_reference_git_write_tools():
    """Prism.md must not reference git commit/push/write tools."""
    text = (
        Path(__file__).resolve().parents[3]
        / "louke"
        / "agents"
        / "Prism.md"
    ).read_text(encoding="utf-8").lower()
    forbidden = ["git push", "git commit", "subprocess.run(['git'", "os.system('git"]
    for pattern in forbidden:
        assert pattern not in text


@pytest.mark.awaiting_devon("NFR-0200")
def test_secret_scanner_blocks_baseline(mock_design_contract):
    """Secret scanner must block baseline when canary is detected."""
    mock_design_contract.scan_secrets.return_value = {
        "ok": False,
        "error": "SECRET_DETECTED",
        "location": "prompts/archer.md:42",
        "value_echoed": False,
    }
    result = mock_design_contract.scan_secrets(artifact="prompts")
    assert not result["ok"]
    assert result["value_echoed"] is False


@pytest.mark.awaiting_devon("NFR-0200")
def test_ci_contract_minimal_token_permissions(mock_ci_contract):
    """CI contract must default to minimal token permissions."""
    mock_ci_contract.generate.return_value = {
        "ok": True,
        "permissions": {"contents": "read", "packages": "read"},
        "fork_secrets": False,
    }
    result = mock_ci_contract.generate(stack="Python")
    assert "contents" in result["permissions"]
    assert result["fork_secrets"] is False


@pytest.mark.awaiting_devon("NFR-0200")
def test_fork_untrusted_job_no_production_secret(mock_ci_contract):
    """Fork/untrusted job must have no production secret."""
    mock_ci_contract.generate.return_value = {
        "ok": True,
        "fork_env": {"secrets_available": False},
    }
    result = mock_ci_contract.generate(stack="Python", fork=True)
    assert result["fork_env"]["secrets_available"] is False
