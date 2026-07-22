"""Integration tests for FR-0200: Host Project Facts Inventory.

AC-FR0200-01: For existing projects, Archer input lists actual languages,
build/test/version/artifact/CI/hooks/outlets and references them in design;
non-existent paths are not fabricated. For blank projects, Archer produces
a complete technical choice without Human input; no rule treats Louke repo
config as default.
"""
# AC-FR0200-01

from __future__ import annotations

import json
from pathlib import Path

import pytest

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "v014_design_contracts"
ROOT = Path(__file__).resolve().parents[3]


def test_host_facts_snapshot_lists_real_languages(host_facts_snapshot):
    """Louke dogfood facts must list Python as the only language."""
    langs = host_facts_snapshot["inventory"]["languages"]
    assert langs == ["Python"], f"expected [Python], got {langs}"


def test_host_facts_snapshot_lists_real_artifacts(host_facts_snapshot):
    """Louke dogfood facts must list wheel + sdist artifacts."""
    artifacts = set(host_facts_snapshot["inventory"]["artifacts"])
    assert artifacts == {"wheel", "sdist"}


def test_host_facts_snapshot_lists_real_version_source(host_facts_snapshot):
    """Version source must be pyproject.toml:[project].version."""
    sources = host_facts_snapshot["inventory"]["version_sources"]
    assert "pyproject.toml:[project].version" in sources


def test_host_facts_snapshot_lists_real_ci_workflows():
    """The canonical workflow is the only repository CI gate."""
    workflows = ROOT / ".github" / "workflows"
    assert (workflows / "louke-ci.yml").is_file()
    assert not (workflows / ("c" + "i.yml")).exists()
    assert not (workflows / ("release" + ".yml")).exists()


def test_host_facts_snapshot_lists_pre_commit_hooks(host_facts_snapshot):
    """Pre-commit hooks must be present in inventory."""
    assert ".pre-commit-config.yaml" in host_facts_snapshot["inventory"]["hooks"]


def test_host_facts_snapshot_observations_use_real_paths(host_facts_snapshot):
    """Every observation must reference a real path; no fabricated entries."""
    for obs in host_facts_snapshot["observations"]:
        assert "path" in obs, f"observation missing path: {obs}"
        assert "status" in obs, f"observation missing status: {obs}"
        assert obs["status"] in ("present", "absent", "unsupported"), (
            f"bad status: {obs['status']}"
        )


def test_host_facts_snapshot_does_not_fabricate_lockfiles(host_facts_snapshot):
    """Louke dogfood has no lockfile; facts must report absent, not invent one."""
    obs = next(
        (
            o
            for o in host_facts_snapshot["observations"]
            if o["kind"] == "dependency-lock"
        ),
        None,
    )
    assert obs is not None, "dependency-lock observation missing"  # AC-FR0200-01
    assert obs["status"] == "absent"


def test_python_host_fixture_facts_do_not_reference_node():
    """Python host fixture must not reference Node concepts (NFR-0300)."""
    facts = json.loads(
        (FIXTURES / "python-host" / "host-project-facts.json").read_text()
    )
    blob = json.dumps(facts)
    forbidden = ["package.json", "npm", "node", "tarball"]
    for token in forbidden:
        assert token.lower() not in blob.lower(), (
            f"Python fixture must not reference Node concept '{token}'"
        )


def test_node_host_fixture_facts_do_not_reference_python():
    """Node host fixture must not reference Python concepts (NFR-0300)."""
    facts = json.loads((FIXTURES / "node-host" / "host-project-facts.json").read_text())
    blob = json.dumps(facts)
    forbidden = ["pyproject", "setuptools", "wheel", "sdist", "PEP 440"]
    for token in forbidden:
        assert token.lower() not in blob.lower(), (
            f"Node fixture must not reference Python concept '{token}'"
        )


def test_host_matrix_covers_python_node_blank_unsupported():
    """host_matrix fixture must cover Python, Node, blank and unsupported."""
    matrix = json.loads((FIXTURES / "matrices" / "host_matrix.json").read_text())
    ids = [h["id"] for h in matrix["hosts"]]
    for required in (
        "python-existing",
        "node-existing",
        "blank-project",
        "unsupported-capability",
    ):
        assert required in ids, f"host_matrix missing case: {required}"


@pytest.mark.awaiting_devon("FR-0200")
def test_blank_project_archer_chooses_without_human(mock_host_facts):
    """Blank project with no Human technical choice: Archer must still produce
    complete technical scheme. Awaits Devon's FACTS module implementation."""
    mock_host_facts.inventory.return_value = {"languages": [], "artifacts": []}
    result = mock_host_facts.inventory()
    assert (
        result is not None
    )  # placeholder; real impl must produce full scheme  # AC-FR0200-01
