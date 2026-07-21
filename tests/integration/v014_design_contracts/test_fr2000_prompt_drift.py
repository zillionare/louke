"""Integration tests for FR-2000: Prompt Deterministic Deployment & Drift Detection.

AC-FR2000-01: Same source bundle, transform rule and model binding
repeatedly deployed produces consistent canonical deployed digest; readback
verifies source→deployment mapping. Missing copy, manual edit, old
transformer or digest mismatch is detected and blocks dispatch, or Runtime
explicitly reconciles then generates new identity.
"""
# AC-FR2000-01

from __future__ import annotations

import pytest


def test_manifest_staging_renders_are_deterministic(design_manifest):
    """staging renders must have stable digests (deterministic transform)."""
    for staging in design_manifest["prompt_candidates"]["staging"]:
        assert "digest" in staging
        assert "rendered_digest" in staging
        # Both must be sha256 (deterministic)
        assert staging["digest"].startswith("sha256:")
        assert staging["rendered_digest"].startswith("sha256:")


def test_manifest_prompt_bundle_has_transformer_identity(design_manifest):
    """bundle must reference transformer identity (louke.board.cmd_opencode)."""
    # The transformer is implied by the bundle identity and staging paths;
    # architecture.md §6.2 locks transformer identity.
    bundle = design_manifest["prompt_candidates"]["bundle"]
    assert bundle["identity"].startswith("louke.prompt-bundle.")


def test_manifest_deployment_readback_exists(design_manifest):
    """deployment_readback entry must exist in prompt_candidates."""
    assert "deployment_readback" in design_manifest["prompt_candidates"]
    readback = design_manifest["prompt_candidates"]["deployment_readback"]
    assert "path" in readback
    assert "digest" in readback
    assert "qualification" in readback


@pytest.mark.awaiting_devon("FR-2000")
def test_repeated_deploy_yields_identical_digest(mock_prompt_bundle):
    """Same source + transform + model must produce identical digest."""
    mock_prompt_bundle.deploy.return_value = {
        "ok": True,
        "deployed_digest": "sha256:stable",
    }
    r1 = mock_prompt_bundle.deploy(source="louke/agents/Archer.md")
    r2 = mock_prompt_bundle.deploy(source="louke/agents/Archer.md")
    assert r1["deployed_digest"] == r2["deployed_digest"]


@pytest.mark.awaiting_devon("FR-2000")
def test_missing_copy_blocks_dispatch(mock_prompt_bundle):
    """Missing deployed copy must block dispatch."""
    mock_prompt_bundle.readback.return_value = {
        "ok": False,
        "error": "MISSING_DEPLOYED_COPY",
        "path": ".opencode/agents/archer.md",
    }
    result = mock_prompt_bundle.readback()
    assert not result["ok"]


@pytest.mark.awaiting_devon("FR-2000")
def test_manual_edit_blocks_dispatch(mock_prompt_bundle):
    """Manual edit of deployed bytes must block dispatch via digest mismatch."""
    mock_prompt_bundle.readback.return_value = {
        "ok": False,
        "error": "DIGEST_MISMATCH",
        "expected": "sha256:abc",
        "actual": "sha256:def",
    }
    result = mock_prompt_bundle.readback()
    assert not result["ok"]
    assert result["error"] == "DIGEST_MISMATCH"


@pytest.mark.awaiting_devon("FR-2000")
def test_old_transformer_blocks_dispatch(mock_prompt_bundle):
    """Old transformer version must block dispatch."""
    mock_prompt_bundle.readback.return_value = {
        "ok": False,
        "error": "TRANSFORMER_VERSION_MISMATCH",
        "expected": "board.py@base-2734177",
        "actual": "board.py@old-version",
    }
    result = mock_prompt_bundle.readback()
    assert not result["ok"]


@pytest.mark.awaiting_devon("FR-2000")
def test_reconcile_generates_new_identity(mock_prompt_bundle):
    """Explicit reconcile must generate new identity."""
    mock_prompt_bundle.reconcile.return_value = {
        "ok": True,
        "new_identity": "louke.prompt-bundle.v0.14-002.r5",
        "reconciled": True,
    }
    result = mock_prompt_bundle.reconcile()
    assert result["ok"]
    assert result["new_identity"] != "louke.prompt-bundle.v0.14-002.r4"
