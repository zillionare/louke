"""AC-NFR0501-01: traceability must fail closed on declaration drift."""

from pathlib import Path
import subprocess
import sys


def test_expected_count_rejects_acceptance_declaration_drift(tmp_path: Path) -> None:
    """The CI contract rejects an acceptance file with too few declared IDs."""
    acceptance = tmp_path / "acceptance.md"
    spec = tmp_path / "spec.md"
    tests = tmp_path / "tests"
    tests.mkdir()
    acceptance.write_text("### AC-FR0001-01\n", encoding="utf-8")
    spec.write_text("FR-0001\n", encoding="utf-8")
    (tests / "test_contract.py").write_text('"""AC-FR0001-01"""\n', encoding="utf-8")

    result = subprocess.run(
        [
            sys.executable,
            "tools/check_ac_traceability.py",
            "--acceptance",
            str(acceptance),
            "--tests",
            str(tests),
            "--expected-count",
            "2",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    assert "expected 2" in result.stdout
