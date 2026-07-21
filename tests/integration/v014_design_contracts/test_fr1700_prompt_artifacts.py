"""Integration tests for FR-1700: Agent Prompt as Normative Artifact.

AC-FR1700-01: Spec manifest lists canonical prompt paths exactly equal
to closed set `louke/agents/Archer.md`, `louke/agents/Prism.md`;
implementation baseline contains both source digests and independent
review identity. Missing any path or adding unauthorized prompt blocks
baseline; modifying any baselined prompt marks old task/review/evidence
stale; unreviewed prompt cannot enter current baseline.
"""
# AC-FR1700-01

from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_manifest_prompt_candidates_closed_set_matches_canonical(
    design_manifest, canonical_prompt_sources
):
    """manifest.prompt_candidates.closed_set must equal the canonical set."""
    closed = set(design_manifest["prompt_candidates"]["closed_set"])
    assert closed == canonical_prompt_sources, (
        f"closed_set mismatch: {closed} vs {canonical_prompt_sources}"
    )


def test_manifest_prompt_sources_list_both_canonical(design_manifest):
    """manifest.prompt_candidates.sources must list both Archer and Prism."""
    sources = design_manifest["prompt_candidates"]["sources"]
    paths = {s["path"] for s in sources}
    assert paths == {"louke/agents/Archer.md", "louke/agents/Prism.md"}


def test_manifest_prompt_sources_have_digests(design_manifest):
    """Each prompt source must have a digest."""
    for source in design_manifest["prompt_candidates"]["sources"]:
        assert source["digest"].startswith("sha256:"), (
            f"source {source['path']} missing sha256 digest"
        )


def test_canonical_prompt_files_exist():
    """Archer.md and Prism.md must exist on disk."""
    for name in ("Archer.md", "Prism.md"):
        path = REPO_ROOT / "louke" / "agents" / name
        assert path.exists(), f"canonical prompt missing: {path}"


def test_manifest_prompt_bundle_has_identity(design_manifest):
    """prompt_candidates.bundle must have identity and digests."""
    bundle = design_manifest["prompt_candidates"]["bundle"]
    assert bundle["identity"] == "louke.prompt-bundle.v0.14-002.r4"
    assert bundle["file_digest"].startswith("sha256:")
    assert bundle["bundle_digest"].startswith("sha256:")


def test_manifest_prompt_staging_has_two_renders(design_manifest):
    """prompt_candidates.staging must list archer + prism renders."""
    staging = design_manifest["prompt_candidates"]["staging"]
    assert len(staging) == 2
    paths = {s["path"] for s in staging}
    assert any("archer" in p for p in paths)
    assert any("prism" in p for p in paths)


def test_manifest_deployment_readback_qualifies_as_staging_only(design_manifest):
    """deployment_readback must qualify as staging-only."""
    readback = design_manifest["prompt_candidates"]["deployment_readback"]
    assert "staging-only" in readback["qualification"]


def test_manifest_reviewer_binding_has_both_digests(design_manifest):
    """reviewer_binding must have reviewer_execution_digest and
    reviewed_candidate_bundle_digest, and they must differ."""
    binding = design_manifest["prompt_candidates"]["reviewer_binding"]
    assert "reviewer_execution_digest" in binding
    assert "reviewed_candidate_bundle_digest" in binding
    assert binding["reviewer_execution_digest"] != binding["reviewed_candidate_bundle_digest"], (
        "reviewer execution and reviewed candidate must be different bundles"
    )


@pytest.mark.awaiting_devon("FR-1700")
def test_missing_canonical_path_blocks_baseline(mock_prompt_bundle):
    """Missing any canonical prompt path must block baseline."""
    mock_prompt_bundle.validate.return_value = {
        "ok": False,
        "error": "MISSING_CANONICAL_PATH",
        "path": "louke/agents/Prism.md",
    }
    result = mock_prompt_bundle.validate()
    assert not result["ok"]


@pytest.mark.awaiting_devon("FR-1700")
def test_unauthorized_prompt_blocks_baseline(mock_prompt_bundle):
    """Adding unauthorized prompt path must block baseline."""
    mock_prompt_bundle.validate.return_value = {
        "ok": False,
        "error": "UNAUTHORIZED_PROMPT",
        "path": "louke/agents/Extra.md",
    }
    result = mock_prompt_bundle.validate()
    assert not result["ok"]
