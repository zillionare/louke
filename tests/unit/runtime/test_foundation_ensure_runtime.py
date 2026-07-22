"""Runtime foundation ensure compatibility boundary tests."""

from __future__ import annotations

from pathlib import Path

from louke.runtime.foundation import (
    FoundationEnsureRequest,
    FoundationError,
    FoundationGap,
    FoundationProgramResult,
    run_foundation_ensure,
)


def _request(tmp_path: Path) -> FoundationEnsureRequest:
    """Return a normalized request for a Runtime handler unit test."""
    return FoundationEnsureRequest(
        workspace=tmp_path,
        repo="owner/repo",
        version="0.14.0",
        spec_id="v0.14.0-003-foundation",
        keyword="foundation",
        upstream="main",
        story="story",
        story_file="",
        dod="unit pass",
        security_audit="disabled",
        no_commit=True,
        no_repo=True,
        dry_run=False,
        public=False,
    )


class CompleteAdapter:
    """Adapter with no gaps for the satisfied transition."""

    def check(self, workspace: str) -> list[FoundationGap]:
        """Return no gaps."""
        return []

    def create(self, workspace: str, gap: FoundationGap) -> None:
        """Reject unexpected repair attempts."""
        raise AssertionError("complete adapter must not create resources")


class BlockedAdapter:
    """Adapter with a human-decidable gap."""

    def check(self, workspace: str) -> list[FoundationGap]:
        """Return a blocked question."""
        return [
            FoundationGap(
                key="foundation.owner",
                auto_repairable=False,
                question={"question_id": "foundation.owner"},
            )
        ]

    def create(self, workspace: str, gap: FoundationGap) -> None:
        """Reject resource creation for a blocked gap."""
        raise AssertionError("blocked adapter must not create resources")


class FailingCreateAdapter:
    """Adapter whose repair reports a terminal Runtime error."""

    def check(self, workspace: str) -> list[FoundationGap]:
        """Return one repairable gap."""
        return [FoundationGap(key="foundation.file", auto_repairable=True)]

    def create(self, workspace: str, gap: FoundationGap) -> None:
        """Raise the configured terminal error."""
        raise FoundationError("write denied")


class FailingCheckAdapter:
    """Adapter whose check reports a retryable Runtime error."""

    def check(self, workspace: str) -> list[FoundationGap]:
        """Raise a retryable error."""
        raise FoundationError("network unavailable", retryable=True)

    def create(self, workspace: str, gap: FoundationGap) -> None:
        """Reject unexpected repair attempts."""
        raise AssertionError("check failure must not create resources")


def test_runtime_foundation_ensure_maps_satisfied_to_pass(tmp_path: Path) -> None:
    """The canonical Runtime result maps a satisfied handler to ``pass``."""
    result = run_foundation_ensure(_request(tmp_path), CompleteAdapter())
    assert isinstance(result, FoundationProgramResult)
    assert result.status == "pass"
    assert result.details["handler_result"] == "satisfied"


def test_runtime_foundation_ensure_preserves_blocked_questions(tmp_path: Path) -> None:
    """Human-decidable gaps remain blocked with structured diagnostics."""
    result = run_foundation_ensure(_request(tmp_path), BlockedAdapter())
    assert result.status == "blocked"
    assert result.details["questions"] == [{"question_id": "foundation.owner"}]


def test_runtime_foundation_ensure_fails_closed_on_adapter_errors(
    tmp_path: Path,
) -> None:
    """Adapter errors never become a false successful foundation result."""
    terminal = run_foundation_ensure(_request(tmp_path), FailingCreateAdapter())
    retryable = run_foundation_ensure(_request(tmp_path), FailingCheckAdapter())
    assert terminal.status == "failed"
    assert terminal.details["error"] == "failed to create foundation.file: write denied"
    assert retryable.status == "retryable"
    assert retryable.details["error"] == "network unavailable"
