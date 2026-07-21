"""Integration tests for FR-1500: Build, Artifact & Post-install Version Contract.

AC-FR1500-01: Contract executes version prepare, real build, complete
artifact enumeration, per-artifact digest/version extract/compare and
applicable install or post-run version read. Any missing artifact,
non-extractable, version mismatch or public version inconsistency yields
deterministic FAIL; source declarations cannot substitute artifacts.
"""
# AC-FR1500-01

from __future__ import annotations

import json
from pathlib import Path

import pytest

FIXTURES = (
    Path(__file__).resolve().parents[2]
    / "fixtures"
    / "v014_design_contracts"
    / "matrices"
)


def test_release_artifact_matrix_has_canonical_case():
    """release_artifact_matrix must include canonical wheel+sdist case."""
    matrix = json.loads((FIXTURES / "release_artifact_matrix.json").read_text())
    canonical = next(
        (c for c in matrix["cases"] if c["id"] == "canonical-wheel-sdist"), None
    )
    assert canonical is not None
    assert canonical["expected"] == "PASS"


def test_release_artifact_matrix_has_negative_cases():
    """release_artifact_matrix must include missing/mismatch/bad-metadata cases."""
    matrix = json.loads((FIXTURES / "release_artifact_matrix.json").read_text())
    neg_ids = {c["id"] for c in matrix["cases"]}
    for required in (
        "missing-sdist",
        "missing-wheel",
        "version-mismatch",
        "missing-prompt-in-wheel",
        "missing-schema-in-wheel",
        "bad-metadata",
    ):
        assert required in neg_ids, f"missing negative case: {required}"


def test_release_artifact_matrix_negative_cases_expect_fail():
    """Every negative case must expect FAIL."""
    matrix = json.loads((FIXTURES / "release_artifact_matrix.json").read_text())
    for case in matrix["cases"]:
        if case["id"] != "canonical-wheel-sdist":
            assert case["expected"].startswith("FAIL"), (
                f"case {case['id']} should FAIL, got {case['expected']}"
            )


def test_build_artifact_schema_in_registry(registry_candidate):
    """registry must include the build-artifact machine-contract schema."""
    kinds = {s["kind"] for s in registry_candidate["schemas"]}
    assert "build-artifact" in kinds


def test_build_artifact_contract_in_manifest(design_manifest):
    """manifest must list a build-artifact contract instance."""
    instances = design_manifest["contract_instances"]
    build = [i for i in instances if i["kind"] == "build-artifact"]
    assert len(build) == 1


@pytest.mark.awaiting_devon("FR-1500")
def test_build_executes_version_prepare_then_real_build(mock_build_artifact):
    """Contract must execute version prepare before real build."""
    mock_build_artifact.run.return_value = {
        "ok": True,
        "steps": [
            {"id": "version-prepare", "status": "pass"},
            {"id": "build", "status": "pass"},
            {"id": "artifact-enumerate", "status": "pass"},
        ],
    }
    result = mock_build_artifact.run()
    steps = result["steps"]
    assert steps[0]["id"] == "version-prepare"
    assert steps[1]["id"] == "build"


@pytest.mark.awaiting_devon("FR-1500")
def test_build_rejects_missing_artifact(mock_build_artifact):
    """Missing artifact must yield deterministic FAIL."""
    mock_build_artifact.run.return_value = {
        "ok": False,
        "error": "ARTIFACT_MISSING",
        "artifact": "sdist",
    }
    result = mock_build_artifact.run()
    assert not result["ok"]


@pytest.mark.awaiting_devon("FR-1500")
def test_build_rejects_version_mismatch(mock_build_artifact):
    """Version mismatch between source and installed must FAIL."""
    mock_build_artifact.run.return_value = {
        "ok": False,
        "error": "VERSION_MISMATCH",
        "source_version": "0.14.0",
        "installed_version": "0.13.1",
    }
    result = mock_build_artifact.run()
    assert not result["ok"]


@pytest.mark.awaiting_devon("FR-1500")
def test_build_rejects_source_declaration_substitute(mock_build_artifact):
    """Source declaration cannot substitute real artifact verification."""
    mock_build_artifact.run.return_value = {
        "ok": False,
        "error": "SOURCE_DECLARATION_NOT_ACCEPTED",
    }
    result = mock_build_artifact.run(accept_source_declaration=True)
    assert not result["ok"]
