"""Unit tests for CI scanner baseline propagation."""

from louke._tools import ci_scan


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
