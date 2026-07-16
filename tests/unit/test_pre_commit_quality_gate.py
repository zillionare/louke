"""AC-NFR1506-01@v0.13.1, AC-NFR1506-02@v0.13.1, AC-NFR1506-03@v0.13.1."""

from louke._tools.pre_commit import should_scan_ac_trace, validate_subject
from louke.keeper import resolve_scan_targets


def test_commit_subject_accepts_quality_gate_prefixes():
    """AC-NFR1506-01@v0.13.1: accept the documented subject prefixes."""
    assert validate_subject("feat: green – #223 – implement") == []
    assert validate_subject("fix: green – #223 – repair") == []
    assert validate_subject("refactor: – #223 – simplify") == []


def test_commit_subject_rejects_undocumented_prefix():
    """AC-NFR1506-01@v0.13.1: reject an undocumented subject prefix."""
    findings = validate_subject("test: add coverage")

    assert findings
    assert "commit subject" in findings[0]


def test_fix_subject_skips_ac_trace_but_not_antipattern_scan():
    """AC-NFR1506-02@v0.13.1: fix subjects skip only AC trace."""
    assert should_scan_ac_trace("fix: repair regression") is False
    assert should_scan_ac_trace("feat: green – #223 – implement") is True


def test_scan_targets_include_every_file_in_commit_range(monkeypatch):
    """AC-NFR1506-03@v0.13.1: diff-only scan covers a multi-commit range."""
    monkeypatch.setattr(
        "louke.keeper.git",
        lambda *args, **kwargs: (0, "tests/first.py\ntests/second.py\n", ""),
    )

    assert resolve_scan_targets("HEAD~2..HEAD", ["tests/"]) == [
        "tests/first.py",
        "tests/second.py",
    ]
