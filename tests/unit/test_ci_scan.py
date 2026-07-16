"""AC-NFR1506-01@v0.13.1, AC-NFR1506-02@v0.13.1, AC-NFR1506-03@v0.13.1."""

from louke._tools import ci_scan

MULTIPLE_TARGETS = [
    "tests/unit/test_quality_gate.py",
    "tests/unit/test_pre_commit_quality_gate.py",
]


def test_ci_scan_applies_project_baseline_to_ac_and_assertion_scans(
    tmp_path, monkeypatch
) -> None:
    """Deferred ACs and historical findings use the same project baseline."""
    baseline = tmp_path / ".louke/project/baselines/keeper-anti-pattern.txt"
    baseline.parent.mkdir(parents=True)
    baseline.write_text("AC-FR1501-01\n", encoding="utf-8")
    (tmp_path / "acceptance.md").write_text("", encoding="utf-8")

    commands = []

    def fake_run(command):
        commands.append(command)
        return 0, "ok"

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(ci_scan, "run", fake_run)
    monkeypatch.setattr(
        ci_scan.sys, "argv", ["ci_scan", "--acceptance", "acceptance.md"]
    )

    assert ci_scan.main() == 0
    assert all("--legacy-baseline" in command for command in commands)


def test_ci_scan_forwards_multiple_diff_only_test_targets(
    monkeypatch, tmp_path
) -> None:
    """AC-NFR1506-03@v0.13.1: scan every changed test file in a commit range."""
    (tmp_path / "acceptance.md").write_text("", encoding="utf-8")
    commands = []

    def fake_run(command):
        commands.append(command)
        return 0, "ok"

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(ci_scan, "run", fake_run)
    monkeypatch.setattr(
        ci_scan.sys,
        "argv",
        [
            "ci_scan",
            "--acceptance",
            "acceptance.md",
            "--tests",
            *MULTIPLE_TARGETS,
            "--diff-only",
        ],
    )

    assert ci_scan.main() == 0
    assert len(commands) == 2
    for command in commands:
        assert command[command.index("--tests") + 1 : command.index("--exclude")] == [
            *MULTIPLE_TARGETS,
        ]
        assert "--diff-only" in command or command[1].endswith("check_assertions.py")


def test_ci_scan_keeps_single_test_target_compatible(monkeypatch, tmp_path) -> None:
    """AC-NFR1506-03@v0.13.1: a single explicit test path remains valid."""
    (tmp_path / "acceptance.md").write_text("", encoding="utf-8")
    commands = []

    monkeypatch.chdir(tmp_path)

    def fake_run(command):
        commands.append(command)
        return 0, "ok"

    monkeypatch.setattr(ci_scan, "run", fake_run)
    monkeypatch.setattr(
        ci_scan.sys,
        "argv",
        [
            "ci_scan",
            "--acceptance",
            "acceptance.md",
            "--tests",
            "tests/unit/test_quality_gate.py",
        ],
    )

    assert ci_scan.main() == 0
    assert all(
        command[command.index("--tests") + 1 : command.index("--exclude")]
        == ["tests/unit/test_quality_gate.py"]
        for command in commands
    )
