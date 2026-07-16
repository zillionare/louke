"""Unit checks for the non-destructive release identity trace."""

from pathlib import Path


TRACE = Path(__file__).parents[3] / ".louke/project/commit-trace/v0.13.1-002.md"


def test_i10_existing_commits_are_mapped_to_issue_217() -> None:
    """The pushed I-10 commits remain addressable without rewriting history."""
    content = TRACE.read_text(encoding="utf-8")

    assert "Issue: #217" in content
    assert "6a82274" in content
    assert "ab3acd9" in content
    assert "AC-FR1510-01/02/03" in content
    assert "AC-NFR1504-02" in content
