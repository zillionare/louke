"""AC-FR1507-01@v0.13.1 and AC-FR1508-03@v0.13.1 upgrade target tests."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from louke.__main__ import _do_upgrade, main


def _runtime(root: Path, relative: str) -> Path:
    executable = root / relative
    executable.parent.mkdir(parents=True)
    executable.write_text("python", encoding="utf-8")
    return executable


def test_ac_fr1509_01_both_targets_receive_index_and_version(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    """AC-FR1509-01@v0.13.1: both pip commands receive the same package pin."""
    project = tmp_path / "project"
    project.mkdir()
    manifest = project / ".louke" / "project" / "project.toml"
    manifest.parent.mkdir(parents=True)
    manifest.write_text('[harness]\nboard_args = ["opencode"]\n', encoding="utf-8")
    local = _runtime(project, ".venv/bin/python")
    home = tmp_path / "home"
    global_python = _runtime(home, ".louke/venv/bin/python")
    monkeypatch.chdir(project)
    monkeypatch.setenv("HOME", str(home))

    calls: list[tuple[list[str], dict]] = []

    def fake_run(command, **kwargs):
        calls.append((list(command), kwargs))
        return SimpleNamespace(
            returncode=0,
            stdout="Successfully installed louke-1.2.3",
            stderr="",
        )

    monkeypatch.setattr("subprocess.run", fake_run)
    assert (
        _do_upgrade(
            [
                "--both",
                "--index",
                "https://example.test/simple",
                "--version",
                "1.2.3",
            ]
        )
        == 0
    )
    pip_calls = [call[0] for call in calls if "pip" in call[0]]
    assert len(pip_calls) == 2
    for command, expected_python in (
        (pip_calls[0], local),
        (pip_calls[1], global_python),
    ):
        assert command[:1] == [str(expected_python)]
        assert "louke==1.2.3" in command
        assert (
            command[command.index("--index-url") + 1] == "https://example.test/simple"
        )
    assert sum("board" in call[0] for call in calls) == 1
    assert "Running (local board)" in capsys.readouterr().out


def test_ac_fr1507_02_failed_pip_does_not_board(tmp_path: Path, monkeypatch) -> None:
    """AC-FR1507-02@v0.13.1: a failed pip upgrade never invokes board."""
    monkeypatch.chdir(tmp_path)
    _runtime(tmp_path, ".venv/bin/python")
    calls: list[list[str]] = []

    def fake_run(command, **kwargs):
        calls.append(list(command))
        return SimpleNamespace(returncode=1, stdout="", stderr="network error")

    monkeypatch.setattr("subprocess.run", fake_run)
    assert _do_upgrade([]) == 1
    assert all("board" not in command for command in calls)


def test_ac_fr1508_04_conflicting_targets_are_rejected() -> None:
    """AC-FR1508-04@v0.13.1: mutually exclusive target flags fail."""
    assert main(["upgrade", "--local", "--global"]) == 2


def test_ac_nfr1503_02_existing_local_install_is_not_modified(
    tmp_path: Path, monkeypatch, capsys
) -> None:
    """AC-NFR1503-02@v0.13.1: lk install rejects an existing local venv."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".venv").mkdir()
    assert main(["install"]) == 1
    assert "run lk upgrade" in capsys.readouterr().err
