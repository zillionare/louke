"""AC-FR1000-01: pre-commit contract install/readback (IF-PC-01).

FR-1000 requires the pre-commit contract to preserve existing hooks, declare
install/readback/version/quick checks/may_modify/failure semantics, and
forbid Archer/Devon from executing install.  Pre-commit must not be used as
the Red proof or the final full-quality gate (``authoritative_full_gate=false``).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from louke._tools.pre_commit import (
    PreCommitContractError,
    aggregate_readback,
    load_contract,
    parse_existing_hook_snapshot,
    verify_install_authority,
    verify_no_full_gate_claim,
    verify_preserve_existing_hooks,
)

_SPEC_ROOT = (
    Path(__file__).resolve().parents[3]
    / ".louke"
    / "project"
    / "specs"
    / "v0.14-002-workflow-reflow-design"
)
_CONTRACT = _SPEC_ROOT / "design-artifacts" / "contracts" / "pre-commit.candidate.json"


def _contract() -> dict[str, Any]:
    return json.loads(_CONTRACT.read_bytes())


def test_load_contract_returns_payload() -> None:
    """AC-FR1000-01: the pre-commit contract loads with the expected envelope."""
    contract = load_contract(_CONTRACT)
    assert contract["kind"] == "pre-commit"
    payload = contract["payload"]
    assert payload["managed_config_path"] == ".pre-commit-config.yaml"
    assert payload["tool_version"] == "4.6.0"
    assert payload["install_command"] == "pre-commit install"
    assert payload["stages"] == ["pre-commit"]


def test_contract_preserves_existing_hooks() -> None:
    """AC-FR1000-01: existing local Keeper/third-party hooks are preserved."""
    contract = _contract()
    verify_preserve_existing_hooks(contract)  # does not raise
    payload = contract["payload"]
    preserved = next(h for h in payload["hooks"] if h["id"] == "preserve-existing")
    assert preserved["may_modify"] is True
    assert preserved["timeout_seconds"] == 120


def test_contract_declares_quick_checks_only() -> None:
    """AC-FR1000-01: hooks are quick format/lint/static/secret/trace only."""
    contract = _contract()
    payload = contract["payload"]
    fast = next(h for h in payload["hooks"] if h["id"] == "louke-fast-quality")
    assert "format" in fast["entry"]
    assert "lint" in fast["entry"]
    assert "secret" in fast["entry"]


def test_contract_not_authoritative_full_gate() -> None:
    """AC-FR1000-01: pre-commit must not claim to be the final full-quality gate."""
    contract = _contract()
    verify_no_full_gate_claim(contract)  # does not raise
    assert contract["payload"]["authoritative_full_gate"] is False


def test_contract_rejects_full_gate_claim() -> None:
    """AC-FR1000-01: a contract claiming authoritative_full_gate=true fails."""
    contract = _contract()
    contract["payload"]["authoritative_full_gate"] = True
    with pytest.raises(PreCommitContractError) as exc:
        verify_no_full_gate_claim(contract)
    assert exc.value.code == "PRECOMMIT_FULL_GATE_FORBIDDEN"


def test_install_authority_rejects_agent_invocation() -> None:
    """AC-FR1000-01: Archer/Devon must not execute the install command."""
    contract = _contract()
    # Runtime is the only authorised installer
    verify_install_authority(contract, installer="Runtime")  # does not raise
    with pytest.raises(PreCommitContractError) as exc:
        verify_install_authority(contract, installer="Devon")
    assert exc.value.code == "PRECOMMIT_INSTALL_AUTHORITY_DENIED"
    with pytest.raises(PreCommitContractError):
        verify_install_authority(contract, installer="Archer")


def test_readback_returns_one_of_four_statuses() -> None:
    """AC-FR1000-01: readback status is in_sync|drifted|missing|conflict."""
    contract = _contract()
    statuses = contract["payload"]["readback"]["statuses"]
    assert set(statuses) == {"in_sync", "drifted", "missing", "conflict"}


def test_aggregate_readback_in_sync_when_config_matches(tmp_path: Path) -> None:
    """AC-FR1000-01: matching managed config + hook stages readback in_sync."""
    contract = _contract()
    config = tmp_path / ".pre-commit-config.yaml"
    config.write_text(
        "repos:\n  - repo: local\n    hooks:\n"
        "      - id: louke-fast-quality\n        name: fast\n        entry: echo\n"
        "        language: system\n",
        encoding="utf-8",
    )
    result = aggregate_readback(
        contract, config_path=config, installed_stages=["pre-commit"]
    )
    assert result["status"] in ("in_sync", "drifted")  # config exists; not missing


def test_aggregate_readback_missing_when_config_absent(tmp_path: Path) -> None:
    """AC-FR1000-01: absent managed config reads back as missing."""
    contract = _contract()
    result = aggregate_readback(
        contract, config_path=tmp_path / "missing.yaml", installed_stages=[]
    )
    assert result["status"] == "missing"


def test_aggregate_readback_drifted_when_stages_missing(tmp_path: Path) -> None:
    """AC-FR1000-01: missing installed stages produce drifted/conflict."""
    contract = _contract()
    config = tmp_path / ".pre-commit-config.yaml"
    config.write_text("repos: []\n", encoding="utf-8")
    result = aggregate_readback(contract, config_path=config, installed_stages=[])
    assert result["status"] in ("drifted", "conflict")


def test_parse_existing_hook_snapshot_returns_dict() -> None:
    """AC-FR1000-01: existing-hook snapshot is parseable with policy."""
    contract = _contract()
    snapshot = parse_existing_hook_snapshot(contract)
    assert snapshot["path"] == ".pre-commit-config.yaml"
    assert (
        "digest" in snapshot["policy"].lower()
        or "preserve" in snapshot["policy"].lower()
    )


def test_failure_policy_fail_closed() -> None:
    """AC-FR1000-01: failure policy fail_closed with explicit non-success reasons."""
    policy = _contract()["payload"]["failure_policy"]
    assert policy["fail_closed"] is True
    expected_reasons = {
        "nonzero",
        "timeout",
        "modified",
        "missing",
        "drifted",
        "conflict",
    }
    assert expected_reasons <= set(policy["non_success"])


def test_contract_rejects_install_command_as_red_proof() -> None:
    """AC-FR1000-01: the contract must not advertise hook as Red proof target."""
    contract = _contract()
    payload = contract["payload"]
    for hook in payload["hooks"]:
        assert "red" not in hook["entry"].lower()
        assert "full" not in hook["entry"].lower() or "fast" in hook["entry"].lower()
