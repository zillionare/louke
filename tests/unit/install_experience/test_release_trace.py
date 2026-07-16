"""Unit checks for the non-destructive release identity trace."""

from pathlib import Path


TRACE = Path(__file__).parents[3] / ".louke/project/commit-trace/v0.13.1-002.md"
REQUIRED_TRACE = (
    "Issue: #217",
    "6a82274",
    "ab3acd9",
    "AC-FR1510-01/02/03",
    "AC-NFR1504-02",
)


def test_i10_existing_commits_are_mapped_to_issue_217() -> None:
    """The pushed I-10 commits remain addressable without rewriting history (AC-FR1510-01)."""
    content = TRACE.read_text(encoding="utf-8")

    assert all(marker in content for marker in REQUIRED_TRACE)


def test_issue_217_follow_up_records_green_before_refactor() -> None:
    """The #217 follow-up records accepted R-G-R chronology (AC-FR1510-03)."""
    content = TRACE.read_text(encoding="utf-8")

    chronology = "4dd5225 (green)", "f18d10e (refactor)", "37babfa (green)"
    positions = [content.index(marker) for marker in chronology]

    assert positions == sorted(positions)
