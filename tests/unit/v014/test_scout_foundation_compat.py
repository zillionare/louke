"""AC-FR3000-01: Scout foundation compatibility delegates to Runtime.

The retired Scout foundation command may adapt legacy arguments, but it must
not retain a second foundation authority. All resource creation, metadata
updates, and controlled commit behavior must be reached through the Runtime
foundation handler.
"""

from __future__ import annotations

from types import SimpleNamespace
from pathlib import Path

import pytest

from louke import keeper, scout, warden
from louke.runtime.foundation import FoundationProgramResult
from louke.runtime.quality import run_quality_gate


LEGACY_FOUNDATION_HELPERS = (
    "_render_project_info_13_fields",
    "_update_project_info_fields",
    "_gh_api_login",
    "_gh_repo_view",
    "_gh_repo_create",
    "_ensure_release_branch",
    "_ensure_project",
    "_ensure_backlog_project",
    "_gh_smoke_issue",
    "_gh_smoke_pr",
    "cmd_identity_check",
    "cmd_commit_foundation",
)


def _args(**overrides: object) -> SimpleNamespace:
    """Return the legacy foundation argument shape used by the adapter."""
    values = {
        "repo": "owner/repo",
        "version": "0.14.0",
        "spec_id": "v0.14.0-003-foundation",
        "keyword": "foundation",
        "upstream": "main",
        "story": "A foundation story",
        "story_file": "",
        "dod": "unit pass",
        "security_audit": "disabled",
        "no_commit": False,
        "no_repo": False,
        "dry_run": False,
        "public": False,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _block_legacy_helpers(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make every old foundation side effect fail if compatibility calls it."""
    for name in LEGACY_FOUNDATION_HELPERS:
        monkeypatch.setattr(
            scout,
            name,
            lambda *args, _name=name, **kwargs: pytest.fail(
                f"legacy foundation helper called: {_name}"
            ),
        )


def test_ac_fr3000_01_scout_foundation_delegates_only_to_runtime(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """AC-FR3000-01: compatibility foundation invokes one Runtime handler."""
    calls: list[tuple[object, object]] = []
    _block_legacy_helpers(monkeypatch)
    monkeypatch.chdir(tmp_path)

    def runtime_handler(request: object, adapter: object) -> FoundationProgramResult:
        calls.append((request, adapter))
        return FoundationProgramResult(status="pass", details={})

    monkeypatch.setattr(scout, "run_foundation_ensure", runtime_handler, raising=False)

    result = scout.cmd_foundation(_args())

    assert result == 0
    assert len(calls) == 1
    request, adapter = calls[0]
    assert request.repo == "owner/repo"
    assert request.version == "0.14.0"
    assert request.spec_id == "v0.14.0-003-foundation"
    assert isinstance(adapter, scout._ScoutFoundationAdapter)
    assert not (tmp_path / ".louke").exists()


@pytest.mark.parametrize("status", ["blocked", "failed"])
def test_ac_fr3000_01_scout_foundation_fails_closed_without_authority_write(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    status: str,
) -> None:
    """AC-FR3000-01: blocked or failed Runtime results return nonzero safely."""
    calls: list[object] = []
    _block_legacy_helpers(monkeypatch)
    monkeypatch.chdir(tmp_path)

    def runtime_handler(request, adapter):
        calls.append(request)
        return FoundationProgramResult(status=status, details={"reason": status})

    monkeypatch.setattr(
        scout,
        "run_foundation_ensure",
        runtime_handler,
        raising=False,
    )
    monkeypatch.setattr(
        scout,
        "write_stage_result",
        lambda **_: pytest.fail("compatibility foundation wrote stage authority"),
        raising=False,
    )

    result = scout.cmd_foundation(_args())

    assert result == 1
    assert len(calls) == 1
    assert not (tmp_path / ".louke").exists()


def test_ac_fr3000_01_warden_and_keeper_use_runtime_handlers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-FR3000-01: retained adapters delegate to Runtime-owned handlers."""
    foundation_calls: list[Path] = []

    def foundation_check(workspace: Path) -> FoundationProgramResult:
        foundation_calls.append(workspace)
        return FoundationProgramResult(status="pass", details={})

    monkeypatch.setattr(warden, "foundation_program_check", foundation_check)
    args = SimpleNamespace(
        command="foundation-check",
        repo="owner/repo",
        version="0.14.0",
        spec_id="v0.14.0-003-foundation",
        upstream="main",
    )
    assert warden.cmd_foundation_check(args) == 0
    assert foundation_calls == [Path.cwd()]
    assert keeper.run_quality_gate is run_quality_gate
