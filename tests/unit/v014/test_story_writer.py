"""Unit contracts for the controlled initial Story Git writer."""

from __future__ import annotations

from pathlib import Path

import pytest

from louke.v014.fr0500_story_init import StoryInitConflict
from louke.v014.foundation_adapter import ShellFoundationAdapter


def _writer_workspace(tmp_path: Path) -> tuple[ShellFoundationAdapter, Path]:
    template = tmp_path / "louke/templates/story.md"
    template.parent.mkdir(parents=True)
    template.write_text(
        "# Story\n\n## 0. 原始输入\n\n> {用户原始输入，逐字记录，不修改或转述}\n\n## 1. Details\n",
        encoding="utf-8",
    )
    adapter = ShellFoundationAdapter(tmp_path, spec_id="spec-1")
    target = tmp_path / ".louke/project/specs/spec-1/story.md"
    target.parent.mkdir(parents=True)
    return adapter, target


def test_write_story_preserves_template_and_commits_once(tmp_path, monkeypatch) -> None:
    """FR-0500: writer replaces only the original-input placeholder."""
    adapter, target = _writer_workspace(tmp_path)
    commands: list[tuple[str, ...]] = []

    def run(*command: str) -> tuple[bool, str]:
        commands.append(command)
        return True, ""

    monkeypatch.setattr(adapter, "_run", run)
    monkeypatch.setattr(adapter, "_output_at", lambda path, *command: ("sha-story", ""))

    result = adapter.write_story(
        workspace=str(tmp_path),
        spec_id="spec-1",
        human_story="Ship the reflow",
        actor="human:alice",
        run_id="run-1",
    )

    body = target.read_text(encoding="utf-8")
    assert "> Ship the reflow" in body
    assert "## 1. Details" in body
    assert result.evidence.commit_sha == "sha-story"
    assert commands == [
        ("git", "add", "--", ".louke/project/specs/spec-1/story.md"),
        ("git", "commit", "-m", "chore: initialize Story run-1"),
    ]


def test_write_story_conflict_does_not_change_existing_bytes(tmp_path) -> None:
    """FR-0500: a mismatched existing Story is not overwritten."""
    adapter, target = _writer_workspace(tmp_path)
    target.write_bytes(b"human edit")

    with pytest.raises(StoryInitConflict) as error:
        adapter.write_story(
            workspace=str(tmp_path),
            spec_id="spec-1",
            human_story="Ship the reflow",
            actor="human:alice",
            run_id="run-1",
        )

    assert error.value.code == "STORY_INITIALIZATION_CONFLICT"
    assert target.read_bytes() == b"human edit"
