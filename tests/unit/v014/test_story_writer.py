"""Unit contracts for the controlled initial Story Git writer."""

from __future__ import annotations

from pathlib import Path
import subprocess

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

    def run_at(path: Path, *command: str) -> tuple[bool, str]:
        commands.append(command)
        return True, ""

    monkeypatch.setattr(adapter, "_run_at", run_at)
    monkeypatch.setattr(adapter, "_output_at", lambda path, *command: ("sha-story", ""))
    monkeypatch.setattr(
        adapter, "_output_bytes_at", lambda path, *command: (target.read_bytes(), "")
    )

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
        (
            "git",
            "commit",
            "--only",
            "-m",
            "chore: initialize Story run-1",
            "--",
            ".louke/project/specs/spec-1/story.md",
        ),
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


def test_provision_creates_missing_release_branch_in_real_clean_git_workspace(
    tmp_path: Path, monkeypatch
) -> None:
    """AC-FR0400-02: clean origin/main workspaces create the absent release ref."""
    origin = tmp_path / "origin.git"
    workspace = tmp_path / "workspace"
    _git("init", "--bare", str(origin), cwd=tmp_path)
    _git("init", "-b", "main", str(workspace), cwd=tmp_path)
    _git("config", "user.email", "test@example.invalid", cwd=workspace)
    _git("config", "user.name", "Foundation Test", cwd=workspace)
    (workspace / ".louke/project/specs/spec-1").mkdir(parents=True)
    (workspace / ".louke/project/specs/spec-1/acceptance.md").write_text(
        "# Acceptance\n", encoding="utf-8"
    )
    _git("add", ".", cwd=workspace)
    _git("commit", "-m", "main", cwd=workspace)
    _git("remote", "add", "origin", str(origin), cwd=workspace)
    _git("push", "origin", "main", cwd=workspace)

    adapter = ShellFoundationAdapter(workspace, spec_id="spec-1")
    monkeypatch.setattr(
        adapter,
        "_ensure_github_project",
        lambda version: (
            {"node_id": "project-1", "url": "https://example.invalid"},
            "",
        ),
    )
    main_sha = _git("rev-parse", "HEAD", cwd=workspace).stdout.strip()
    main_check = adapter.preflight("Ship the reflow", "0.14.0")

    assert main_check.status == "pass"
    outcome = adapter.provision("Ship the reflow", "0.14.0", "run-1", main_check)

    assert outcome.status == "ready"
    assert outcome.resources["release_branch"]["start_sha"] == main_sha
    assert (
        _git(
            "show-ref", "--verify", "refs/heads/releases/0.14.0", cwd=workspace
        ).returncode
        == 0
    )


def test_failed_git_output_cannot_be_used_as_a_ref_identity(
    tmp_path, monkeypatch
) -> None:
    """AC-FR0400-02: failed ref lookup discards misleading stdout."""
    adapter = ShellFoundationAdapter(tmp_path, spec_id="spec-1")

    monkeypatch.setattr(
        "louke.v014.foundation_adapter.subprocess.run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args, 128, stdout="refs/heads/releases/0.14.0\n", stderr="fatal: missing"
        ),
    )

    output, error = adapter._output("git", "rev-parse", "refs/heads/releases/0.14.0")

    assert output == ""
    assert error == "fatal: missing"


def _git(*command: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    """Run a real Git command for the Foundation workspace fixture."""
    return subprocess.run(
        ["git", *command], cwd=cwd, text=True, capture_output=True, check=True
    )
