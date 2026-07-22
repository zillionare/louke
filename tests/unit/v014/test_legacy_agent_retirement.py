"""Deterministic contracts for v0.14 legacy Agent retirement."""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from louke import agent, board, keeper, maestro
from louke.runtime.foundation import FoundationProgramResult


LEGACY_ROLES = {"scout", "warden", "keeper"}


def test_canonical_semantic_agent_registry_excludes_legacy_roles() -> None:
    """The canonical registry must not expose retired semantic Agents."""
    assert LEGACY_ROLES.isdisjoint(agent.CANONICAL_SEMANTIC_AGENTS)
    assert LEGACY_ROLES.isdisjoint(agent.AGENTS)


def test_board_source_and_generated_bundle_exclude_legacy_prompts() -> None:
    """Board generation must neither read nor render retired prompts."""
    source_names = {path.stem.lower() for path in board.canonical_agent_sources()}
    assert LEGACY_ROLES.isdisjoint(source_names)
    assert LEGACY_ROLES.isdisjoint(board.GENERATED_AGENT_NAMES)


def test_canonical_maestro_stage_table_uses_runtime_gates() -> None:
    """Canonical stages identify Runtime programs rather than retired Agents."""
    stages = {
        code: (implementer, reviewer)
        for code, _, implementer, reviewer in maestro.STAGES
    }
    assert stages["M-FOUND"] == ("Runtime program", "none")
    assert stages["M-DEV"] == ("Devon", "Prism -> Runtime gate")
    assert stages["M-E2E"] == ("Shield", "Prism -> Runtime gate")
    assert stages["M-BUGFIX"] == ("Devon", "Runtime regression gate")
    assert all(
        role not in repr(maestro.STAGES) for role in ("Scout", "Warden", "Keeper")
    )


def test_foundation_holdpoint_calls_runtime_program(
    monkeypatch, tmp_path: Path
) -> None:
    """M-FOUND must use the Runtime foundation program directly."""
    calls: list[Path] = []

    def runtime_check(workspace: Path) -> FoundationProgramResult:
        calls.append(workspace)
        return FoundationProgramResult(status="pass", details={})

    monkeypatch.setattr(maestro, "foundation_program_check", runtime_check)
    monkeypatch.chdir(tmp_path)
    args = type("Args", (), {"spec_id": "", "commit_range": "HEAD~1..HEAD"})()

    passed, message = maestro._holdpoint("M-FOUND", args)

    assert passed is True
    assert message == "Runtime foundation program passed"
    assert calls == [tmp_path]


def test_keeper_compatibility_cli_delegates_to_runtime_without_state_writer(
    monkeypatch,
) -> None:
    """Deprecated Keeper CLI must call the Runtime handler, never persist authority."""
    called: list[dict[str, object]] = []

    def runtime_gate(**kwargs: object) -> dict[str, object]:
        called.append(kwargs)
        return {"status": "pass", "findings": []}

    monkeypatch.setattr(keeper, "run_quality_gate", runtime_gate)
    monkeypatch.setattr(
        keeper,
        "write_stage_result",
        lambda **_: pytest.fail("compatibility CLI wrote stage authority"),
    )
    args = type(
        "Args",
        (),
        {
            "tests": False,
            "lint": False,
            "typecheck": False,
            "commit_range": "HEAD~1..HEAD",
            "tests_root": [],
            "skip_ac_trace": False,
            "skip_anti_pattern": False,
            "full_scan": False,
            "spec_id": "",
            "stage": "M-DEV",
        },
    )()

    assert keeper.cmd_gate(args) == 0
    assert called and called[0]["commit_range"] == "HEAD~1..HEAD"


def test_canonical_dispatch_has_no_retired_agent_invocations() -> None:
    """Future canonical dispatch changes must not reintroduce legacy calls."""
    source = inspect.getsource(maestro)
    for pattern in (
        "agent scout",
        "agent warden",
        "agent keeper",
        '"scout"',
        '"warden"',
        '"keeper"',
    ):
        assert pattern not in source.lower()
