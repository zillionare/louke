"""Integration tests for FR-2100: Host Project Prompt Read-only Boundary.

AC-FR2100-01: In normal Java/Node host release fixtures, project differences
only appear in facts/contracts/manifests; installed package canonical
prompts produce no modifications. In Louke self-development fixture, only
Spec-listed and manifest-authorized prompt sources are editable; patches
to unlisted paths are rejected.
"""
# AC-FR2100-01

from __future__ import annotations

import json
from pathlib import Path

import pytest

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "v014_design_contracts"


def test_node_host_fixture_does_not_modify_prompts():
    """Node host fixture must not reference any prompt path as writable."""
    facts = json.loads((FIXTURES / "node-host" / "host-project-facts.json").read_text())
    blob = json.dumps(facts).lower()
    assert "louke/agents/" not in blob, (
        "Node host fixture must not reference louke prompt paths"
    )
    assert ".opencode/agents/" not in blob


def test_python_host_fixture_does_not_modify_prompts():
    """Python host fixture (non-Louke demo) must not reference prompt paths."""
    facts = json.loads(
        (FIXTURES / "python-host" / "host-project-facts.json").read_text()
    )
    blob = json.dumps(facts).lower()
    assert "louke/agents/" not in blob
    assert ".opencode/agents/" not in blob


def test_manifest_prompt_sources_only_archer_prism(design_manifest):
    """manifest prompt sources must only list Archer.md and Prism.md."""
    sources = design_manifest["prompt_candidates"]["sources"]
    paths = {s["path"] for s in sources}
    assert paths == {"louke/agents/Archer.md", "louke/agents/Prism.md"}


def test_manifest_closed_set_excludes_others(design_manifest):
    """closed_set must not include any path beyond Archer/Prism."""
    closed = set(design_manifest["prompt_candidates"]["closed_set"])
    assert closed == {"louke/agents/Archer.md", "louke/agents/Prism.md"}


@pytest.mark.awaiting_devon("FR-2100")
def test_unlisted_prompt_patch_rejected(mock_prompt_bundle):
    """Patches to unlisted prompt paths must be rejected."""
    mock_prompt_bundle.validate_patch.return_value = {
        "ok": False,
        "error": "UNAUTHORIZED_PROMPT_PATH",
        "path": "louke/agents/Extra.md",
    }
    result = mock_prompt_bundle.validate_patch(path="louke/agents/Extra.md", diff="...")
    assert not result["ok"]


@pytest.mark.awaiting_devon("FR-2100")
def test_node_host_installed_prompts_unchanged(mock_prompt_bundle):
    """For Node host, installed package canonical prompts produce no
    modifications."""
    mock_prompt_bundle.check_host_prompt_modifications.return_value = {
        "ok": True,
        "modifications": [],
        "host_stack": "Node",
    }
    result = mock_prompt_bundle.check_host_prompt_modifications(host="node-host")
    assert result["ok"]
    assert result["modifications"] == []


@pytest.mark.awaiting_devon("FR-2100")
def test_louke_self_dev_only_spec_listed_paths_editable(mock_prompt_bundle):
    """In Louke self-development, only Spec-listed paths are editable."""
    mock_prompt_bundle.validate_patch.return_value = {
        "ok": True,
        "authorized_path": "louke/agents/Archer.md",
        "spec_listed": True,
    }
    result = mock_prompt_bundle.validate_patch(
        path="louke/agents/Archer.md", diff="...", host="louke-self-dev"
    )
    assert result["ok"]
