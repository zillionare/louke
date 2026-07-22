"""Contract for retiring the legacy GitHub Actions workflows."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
WORKFLOWS = ROOT / ".github" / "workflows"


def test_louke_ci_is_the_only_repository_workflow_gate() -> None:
    """The canonical workflow remains while the two legacy gates are absent."""
    legacy_ci = WORKFLOWS / ("c" + "i.yml")
    legacy_release = WORKFLOWS / ("release" + ".yml")
    assert (WORKFLOWS / "louke-ci.yml").is_file()
    assert not legacy_ci.exists()
    assert not legacy_release.exists()


def test_pre_commit_template_targets_the_canonical_workflow() -> None:
    """The pre-commit CI snippet must not direct users to a retired workflow."""
    snippet = (
        ROOT / "louke" / "templates" / "pre-commit" / "ci-snippet.yml"
    ).read_text(encoding="utf-8")
    legacy_path = ".github/workflows/" + ("c" + "i.yml")
    assert ".github/workflows/louke-ci.yml" in snippet
    assert legacy_path not in snippet
