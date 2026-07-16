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
    """The pushed I-10 commits remain addressable without rewriting history."""
    content = TRACE.read_text(encoding="utf-8")

    assert all(marker in content for marker in REQUIRED_TRACE)
