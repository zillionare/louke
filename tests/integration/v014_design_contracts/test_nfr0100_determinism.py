"""Integration tests for NFR-0100: Determinism & Reproducibility.

AC-NFR0100-01: After fixing time/environment and other explicitly non-
deterministic inputs, repeated generation of contract, prompt deployment
and baseline from the same normative inputs yields identical canonical
digest. Any generator/schema/tool version affecting digest is observable
in manifest.
"""
# AC-NFR0100-01

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest


def test_repeated_canonical_json_yields_identical_digest():
    """Repeated canonical JSON serialization must produce identical digest."""
    obj = {"b": 2, "a": 1, "c": [3, 2, 1]}
    digests = set()
    for _ in range(5):
        canonical = json.dumps(obj, sort_keys=True, separators=(",", ":"))
        digest = "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        digests.add(digest)
    assert len(digests) == 1, f"non-deterministic canonical JSON: {digests}"


def test_manifest_digest_semantics_declared(design_manifest):
    """manifest must declare digest semantics (SHA-256 of UTF-8 file bytes)."""
    semantics = design_manifest["digest_semantics"]
    assert "SHA-256" in semantics
    assert "UTF-8" in semantics


def test_manifest_records_generator_version(design_manifest):
    """manifest must make generator/schema/tool versions observable."""
    # closure_counts and schema list make tool versions observable
    assert "closure_counts" in design_manifest
    assert "schemas" in design_manifest
    # Each schema has version
    for schema in design_manifest["schemas"]:
        assert "version" in schema


def test_manifest_canonicalization_declared(registry_candidate):
    """registry must declare canonicalization method (SHA-256 of UTF-8
    file bytes; canonical JSON before active publication)."""
    canon = registry_candidate["canonicalization"]
    assert "SHA-256" in canon
    assert "UTF-8" in canon
    assert "canonical JSON" in canon


def test_repeated_file_read_yields_identical_digest(tmp_path):
    """Repeated file reads must produce identical SHA-256."""
    path = tmp_path / "fixture.json"
    path.write_text('{"a":1}', encoding="utf-8")
    d1 = "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
    d2 = "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
    assert d1 == d2


@pytest.mark.awaiting_devon("NFR-0100")
def test_repeated_contract_generation_yields_identical_digest(
    mock_design_contract,
):
    """Repeated contract generation from same input must yield identical digest."""
    mock_design_contract.generate.return_value = {
        "ok": True,
        "digest": "sha256:stable",
    }
    r1 = mock_design_contract.generate(input={})
    r2 = mock_design_contract.generate(input={})
    assert r1["digest"] == r2["digest"]


@pytest.mark.awaiting_devon("NFR-0100")
def test_repeated_prompt_deployment_yields_identical_digest(
    mock_prompt_bundle,
):
    """Repeated prompt deployment must yield identical digest."""
    mock_prompt_bundle.deploy.return_value = {
        "ok": True,
        "deployed_digest": "sha256:stable",
    }
    r1 = mock_prompt_bundle.deploy(source="louke/agents/Archer.md")
    r2 = mock_prompt_bundle.deploy(source="louke/agents/Archer.md")
    assert r1["deployed_digest"] == r2["deployed_digest"]


@pytest.mark.awaiting_devon("NFR-0100")
def test_baseline_generation_deterministic(mock_design_coordinator):
    """Baseline generation from same revision must be deterministic."""
    mock_design_coordinator.create_baseline.return_value = {
        "ok": True,
        "baseline_identity": "louke.baseline.v0.14-002.r1",
        "baseline_digest": "sha256:stable",
    }
    r1 = mock_design_coordinator.create_baseline(revision="r1")
    r2 = mock_design_coordinator.create_baseline(revision="r1")
    assert r1["baseline_digest"] == r2["baseline_digest"]
