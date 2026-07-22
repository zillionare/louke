"""Ground-truth test: every design-artifact digest in
``design-artifact-manifest.candidate.json`` must match the SHA-256 of the
referenced file bytes. Independent of louke manifest resolver.

This catches manifest/file drift without invoking any louke code.
"""
# AC-FR0700-01 (ground-truth half): digest independence from registry.
# AC-NFR0100-01 (partial): deterministic digest across runs.

from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SPEC_ROOT = (
    REPO_ROOT / ".louke" / "project" / "specs" / "v0.14-002-workflow-reflow-design"
)
DESIGN_ARTIFACTS = SPEC_ROOT / "design-artifacts"
MANIFEST_PATH = DESIGN_ARTIFACTS / "design-artifact-manifest.candidate.json"


def _resolve_artifact_path(rel_path: str) -> Path | None:
    """Try several base directories for a manifest-relative path."""
    candidates = [
        SPEC_ROOT / rel_path,
        DESIGN_ARTIFACTS.parent / rel_path,
        DESIGN_ARTIFACTS / rel_path,
        REPO_ROOT / rel_path,
    ]
    return next((c for c in candidates if c.exists()), None)


def _walk_artifact_refs(manifest: dict):
    """Yield (path, expected_digest) for every artifact referenced in manifest."""
    for section in (
        "design_docs",
        "schemas",
        "agent_io_schemas",
        "contract_instances",
    ):
        for entry in manifest.get(section, []):
            path = entry.get("path")
            digest = entry.get("digest")
            if path and digest:
                yield path, digest
    for entry in manifest.get("input_artifacts", []):
        path = entry.get("path")
        digest = entry.get("digest")
        if path and digest:
            yield path, digest
    registry = manifest.get("registry")
    if registry and registry.get("path") and registry.get("digest"):
        yield registry["path"], registry["digest"]
    prompts = manifest.get("prompt_candidates", {})
    for src in prompts.get("sources", []):
        if src.get("path") and src.get("digest"):
            yield src["path"], src["digest"]
    bundle = prompts.get("bundle")
    if bundle and bundle.get("path") and bundle.get("file_digest"):
        yield bundle["path"], bundle["file_digest"]


# AC-FR0700-01
@pytest.mark.xfail(
    reason=(
        "Candidate-state finding (2026-07-21): manifest declares stale "
        "digests for 2 Agent I/O schema files "
        "(archer-design-task-input-1.0.0.schema.json, "
        "prism-design-review-task-input-1.0.0.schema.json). Devon must "
        "regenerate manifest digests before registry activation. "
        "See REPORT.md §4."
    ),
    strict=True,
)
def test_manifest_digests_match_file_bytes():
    """Every digest in design-artifact-manifest must match file bytes SHA-256."""
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    mismatches: list[str] = []
    checked = 0
    for rel_path, expected_digest in _walk_artifact_refs(manifest):
        file_path = _resolve_artifact_path(rel_path)
        if file_path is None:
            mismatches.append(f"{rel_path}: file not found")
            continue
        import hashlib

        actual = "sha256:" + hashlib.sha256(file_path.read_bytes()).hexdigest()
        checked += 1
        if actual != expected_digest:
            mismatches.append(f"{rel_path}: expected {expected_digest}, got {actual}")
    assert checked > 0, "no artifact refs walked; manifest structure changed?"
    assert not mismatches, (
        f"{len(mismatches)} digest mismatch(es):\n  - " + "\n  - ".join(mismatches[:10])
    )


def test_manifest_has_seven_machine_schemas():
    """Manifest must enumerate exactly 7 machine-contract schema kinds."""
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    schemas = manifest.get("schemas", [])
    assert len(schemas) == 7, f"expected 7 schemas, got {len(schemas)}"


def test_manifest_has_four_agent_io_schemas():
    """Manifest must enumerate exactly 4 Agent I/O schemas."""
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    schemas = manifest.get("agent_io_schemas", [])
    assert len(schemas) == 4, f"expected 4 agent I/O schemas, got {len(schemas)}"


def test_manifest_has_seven_contract_instances():
    """Manifest must enumerate exactly 7 contract instances."""
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    instances = manifest.get("contract_instances", [])
    assert len(instances) == 7, f"expected 7 contract instances, got {len(instances)}"
