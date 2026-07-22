"""Unit tests for Runtime-owned quality programs."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import louke.runtime.quality as quality


def test_run_quality_gate_collects_findings_and_reports_blocking_status(
    monkeypatch, tmp_path: Path
) -> None:
    """The quality gate combines enabled checks and blocks on high findings."""
    monkeypatch.setattr(quality, "resolve_scan_targets", lambda *args: ["tests/unit"])
    monkeypatch.setattr(quality, "_commit_findings", lambda *args: [])
    monkeypatch.setattr(quality, "_rgr_findings", lambda *args: [])
    monkeypatch.setattr(
        quality,
        "_trace_findings",
        lambda *args: [{"severity": "high", "description": "trace failed"}],
    )
    monkeypatch.setattr(quality, "_anti_pattern_findings", lambda *args: [])

    result = quality.run_quality_gate(commit_range="HEAD~1..HEAD", cwd=tmp_path)

    assert result.status == "fail"
    assert result.findings == ({"severity": "high", "description": "trace failed"},)


def test_run_quality_gate_can_skip_optional_checks(monkeypatch, tmp_path: Path) -> None:
    """Skip flags omit trace and anti-pattern subprocess checks."""
    monkeypatch.setattr(quality, "resolve_scan_targets", lambda *args: [])
    monkeypatch.setattr(quality, "_commit_findings", lambda *args: [])
    monkeypatch.setattr(quality, "_rgr_findings", lambda *args: [])
    calls = {"trace": 0, "anti_pattern": 0}

    def trace(*args):
        calls["trace"] += 1
        return []

    def anti_pattern(*args):
        calls["anti_pattern"] += 1
        return []

    monkeypatch.setattr(quality, "_trace_findings", trace)
    monkeypatch.setattr(quality, "_anti_pattern_findings", anti_pattern)

    result = quality.run_quality_gate(
        commit_range="HEAD~1..HEAD",
        cwd=tmp_path,
        skip_ac_trace=True,
        skip_anti_pattern=True,
    )

    assert result.status == "pass"
    assert calls == {"trace": 0, "anti_pattern": 0}


def test_regression_gate_handles_diff_failure(monkeypatch, tmp_path: Path) -> None:
    """A failed diff command is a critical regression finding."""
    monkeypatch.setattr(quality, "git", lambda *args, **kwargs: (1, "fatal", ""))

    result = quality.run_regression_gate(baseline="main", current="HEAD", cwd=tmp_path)

    assert result.status == "fail"
    assert result.findings[0]["severity"] == "critical"


def test_regression_gate_reports_large_and_dependency_changes(
    monkeypatch, tmp_path: Path
) -> None:
    """Large fixes and dependency edits produce blocking findings."""
    changed = "\n".join(
        [
            "a.py",
            "b.py",
            "c.py",
            "d.py",
            "e.py",
            "f.py",
            "pyproject.toml",
            "tests/test_x.py",
        ]
    )
    monkeypatch.setattr(quality, "git", lambda *args, **kwargs: (0, changed, ""))

    result = quality.run_regression_gate(baseline="main", current="HEAD", cwd=tmp_path)

    assert result.status == "fail"
    descriptions = {item["description"] for item in result.findings}
    assert "bug fix changed 7 code files" in descriptions
    assert "dependency file changed: pyproject.toml" in descriptions


def test_resolve_scan_targets_uses_full_roots_and_git_fallback() -> None:
    """Target resolution supports full scans, changed paths, and fallback roots."""
    roots = ["tests/unit"]
    assert quality.resolve_scan_targets("range", roots, Path("."), True) == roots
    changed = quality.resolve_scan_targets(
        "range",
        roots,
        Path("."),
        False,
        lambda *args, **kwargs: (0, "tests/unit/a.py\n", ""),
    )
    fallback = quality.resolve_scan_targets(
        "range", roots, Path("."), False, lambda *args, **kwargs: (1, "", "error")
    )
    assert changed == ["tests/unit/a.py"]
    assert fallback == roots


def test_commit_findings_reports_git_errors_and_nonstandard_subjects(
    monkeypatch, tmp_path: Path
) -> None:
    """Commit inspection reports command errors and unrecognised subjects."""
    monkeypatch.setattr(quality, "git", lambda *args, **kwargs: (1, "bad log", ""))
    assert quality._commit_findings("range", tmp_path)[0]["severity"] == "critical"

    monkeypatch.setattr(
        quality,
        "git",
        lambda *args, **kwargs: (
            0,
            "abc1234 normal commit\ndef5678 refactor: tidy",
            "",
        ),
    )
    findings = quality._commit_findings("range", tmp_path)
    assert findings[0]["commit"] == "abc1234"


def test_rgr_findings_detects_refactor_before_green(
    monkeypatch, tmp_path: Path
) -> None:
    """RGR inspection rejects a green phase following refactor for an issue."""
    monkeypatch.setattr(
        quality,
        "git",
        lambda *args, **kwargs: (0, "refactor: tidy #42\nfeat: green #42", ""),
    )
    findings = quality._rgr_findings("range", tmp_path)
    assert findings[0]["severity"] == "high"

    monkeypatch.setattr(quality, "git", lambda *args, **kwargs: (1, "bad log", ""))
    assert quality._rgr_findings("range", tmp_path)[0]["severity"] == "critical"


def test_trace_findings_handles_missing_targets_and_subprocess_result(
    monkeypatch, tmp_path: Path
) -> None:
    """AC trace reports missing identity or subprocess failure and passes otherwise."""
    assert quality._trace_findings("", ["tests"], [], tmp_path)[0]["severity"] == "high"
    monkeypatch.setattr(quality, "_read_project_info_field", lambda name: "FR-1500")
    assert quality._trace_findings("", [], [], tmp_path) == []
    monkeypatch.setattr(
        quality.subprocess, "run", lambda *args, **kwargs: SimpleNamespace(returncode=1)
    )
    assert (
        quality._trace_findings("FR-1500", ["tests"], ["tests"], tmp_path)[0][
            "severity"
        ]
        == "high"
    )
    monkeypatch.setattr(
        quality.subprocess, "run", lambda *args, **kwargs: SimpleNamespace(returncode=0)
    )
    assert quality._trace_findings("FR-1500", ["tests"], ["tests"], tmp_path) == []


def test_anti_pattern_findings_handles_empty_baseline_and_scan_result(
    monkeypatch, tmp_path: Path
) -> None:
    """Anti-pattern checks support no targets, baseline arguments, and failures."""
    assert quality._anti_pattern_findings([], tmp_path) == []
    baseline = tmp_path / ".louke" / "project" / "baselines"
    baseline.mkdir(parents=True)
    (baseline / "quality-anti-pattern.txt").write_text("baseline", encoding="utf-8")
    monkeypatch.setattr(
        quality.subprocess, "run", lambda *args, **kwargs: SimpleNamespace(returncode=0)
    )
    assert quality._anti_pattern_findings(["tests"], tmp_path) == []
    monkeypatch.setattr(
        quality.subprocess, "run", lambda *args, **kwargs: SimpleNamespace(returncode=1)
    )
    assert quality._anti_pattern_findings(["tests"], tmp_path)[0]["severity"] == "high"


def test_quality_helpers_classify_phases_and_severity() -> None:
    """Phase and severity helpers expose the quality gate policy."""
    assert quality._phase("feat: green #1") == "green"
    assert quality._phase("fix: green #1") == "green"
    assert quality._phase("refactor: tidy") == "refactor"
    assert quality._phase("docs: update") is None
    assert quality._is_blocking({"severity": "critical"})
    assert quality._is_blocking({"severity": "high"})
    assert not quality._is_blocking({"severity": "medium"})
