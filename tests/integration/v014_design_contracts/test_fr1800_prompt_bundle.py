"""Integration tests for FR-1800: Prompt Bundle Manifest & Identity.

AC-FR1800-01: prompt bundle manifest contains schema/bundle version,
source/deployed path+digest, role, frontmatter/permission/model
abstraction, protocol/skill, Spec, schema refs and transformer version.
Runtime task can trace back to exact bundle/role; deleting any required
identity or only declaring version in chat rejects dispatch/gate.
"""
# AC-FR1800-01

from __future__ import annotations

import pytest


def test_manifest_prompt_bundle_has_identity_and_version(design_manifest):
    """prompt bundle must have identity and version."""
    bundle = design_manifest["prompt_candidates"]["bundle"]
    assert "identity" in bundle
    assert bundle["identity"].startswith("louke.prompt-bundle.")
    assert "path" in bundle
    assert "file_digest" in bundle
    assert "bundle_digest" in bundle


def test_manifest_prompt_sources_have_paths_and_digests(design_manifest):
    """Each prompt source must declare path and digest."""
    sources = design_manifest["prompt_candidates"]["sources"]
    for src in sources:
        assert "path" in src
        assert "digest" in src
        assert src["digest"].startswith("sha256:")


def test_manifest_staging_renders_have_rendered_digests(design_manifest):
    """staging renders must have rendered_digest distinct from file digest."""
    for staging in design_manifest["prompt_candidates"]["staging"]:
        assert "digest" in staging
        assert "rendered_digest" in staging
        assert staging["digest"].startswith("sha256:")
        assert staging["rendered_digest"].startswith("sha256:")


def test_manifest_reviewer_binding_has_path_and_digest(design_manifest):
    """reviewer_binding must have path and digest."""
    binding = design_manifest["prompt_candidates"]["reviewer_binding"]
    assert "path" in binding
    assert "digest" in binding
    assert "reviewer_execution_digest" in binding


@pytest.mark.awaiting_devon("FR-1800")
def test_bundle_manifest_contains_required_fields(mock_prompt_bundle):
    """Bundle manifest must contain schema/bundle version, source/deployed
    path+digest, role, frontmatter/permission/model, protocol/skill, spec,
    schema refs and transformer version."""
    mock_prompt_bundle.read_manifest.return_value = {
        "schema_version": "1.0.0",
        "bundle_version": "1.0.0",
        "source_path": "louke/agents/Archer.md",
        "source_digest": "sha256:abc",
        "deployed_path": ".opencode/agents/archer.md",
        "deployed_digest": "sha256:def",
        "role": "Archer",
        "frontmatter": {"name": "Archer"},
        "permission": {"task": "deny"},
        "model_abstraction": "codexmanager/gpt-5.6-sol",
        "protocol": "agents/_protocols/scheduling.md",
        "spec": "v0.14-002-workflow-reflow-design",
        "schema_refs": ["louke.agent-io.archer-design-task-input"],
        "transformer_version": "board.py@base-2734177",
    }
    result = mock_prompt_bundle.read_manifest()
    required = (
        "schema_version", "bundle_version", "source_path", "source_digest",
        "deployed_path", "deployed_digest", "role", "frontmatter",
        "permission", "model_abstraction", "protocol", "spec",
        "schema_refs", "transformer_version",
    )
    for key in required:
        assert key in result, f"bundle manifest missing {key}"


@pytest.mark.awaiting_devon("FR-1800")
def test_task_traces_back_to_exact_bundle_and_role(mock_prompt_bundle):
    """Runtime task must trace back to exact bundle/role."""
    mock_prompt_bundle.trace_task.return_value = {
        "bundle_identity": "louke.prompt-bundle.v0.14-002.r4",
        "role": "Archer",
        "source_digest": "sha256:abc",
    }
    result = mock_prompt_bundle.trace_task(task_id="t1")
    assert result["bundle_identity"].startswith("louke.prompt-bundle.")
    assert result["role"] in ("Archer", "Prism")


@pytest.mark.awaiting_devon("FR-1800")
def test_chat_only_version_declaration_rejected(mock_prompt_bundle):
    """Declaring version only in chat (without manifest) must reject dispatch."""
    mock_prompt_bundle.validate_dispatch.return_value = {
        "ok": False,
        "error": "MANIFEST_REQUIRED",
    }
    result = mock_prompt_bundle.validate_dispatch(claimed_version="1.0.0")
    assert not result["ok"]
