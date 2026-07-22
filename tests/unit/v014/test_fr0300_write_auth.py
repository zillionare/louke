"""AC-FR0300-01: design write authorisation & artifact ownership.

FR-0300 requires Runtime to grant Archer a single-write manifest listing the
editable design docs, machine contracts and affected canonical prompts, and
forbidding Git/stage/GitHub side effects.  Each round must attribute diffs;
out-of-scope or unattributed changes cannot be silently absorbed into the
design baseline (AC-FR0300-01).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from louke.v014.fr0300_write_auth import (
    DesignWriteAuthError,
    DiffAttribution,
    WriteAuthorisationManifest,
    attribute_diff,
    build_write_manifest,
    is_diff_in_scope,
)

_SPEC_ID = "v0.14-002-workflow-reflow-design"
_SPEC_ROOT = (
    Path(__file__).resolve().parents[3] / ".louke" / "project" / "specs" / _SPEC_ID
)


def _design_doc_paths() -> list[str]:
    return [
        f".louke/project/specs/{_SPEC_ID}/test-plan.md",
        f".louke/project/specs/{_SPEC_ID}/architecture.md",
        f".louke/project/specs/{_SPEC_ID}/interfaces.md",
    ]


def _contract_paths() -> list[str]:
    return [
        f".louke/project/specs/{_SPEC_ID}/design-artifacts/contracts/{kind}.candidate.json"
        for kind in (
            "integration-test",
            "e2e-test",
            "pre-commit",
            "github-actions-ci",
            "release-version",
            "build-artifact",
            "publish-recovery",
        )
    ]


def _prompt_paths() -> list[str]:
    return ["louke/agents/Archer.md", "louke/agents/Prism.md"]


def test_build_manifest_lists_all_authorised_artifacts() -> None:
    """AC-FR0300-01: manifest lists design docs, contracts, prompts and forbids side effects."""
    manifest = build_write_manifest(
        spec_id=_SPEC_ID,
        design_doc_paths=_design_doc_paths(),
        contract_paths=_contract_paths(),
        prompt_paths=_prompt_paths(),
    )
    assert isinstance(manifest, WriteAuthorisationManifest)
    assert manifest.spec_id == _SPEC_ID
    assert set(manifest.design_doc_paths) == set(_design_doc_paths())
    assert set(manifest.contract_paths) == set(_contract_paths())
    assert set(manifest.prompt_paths) == set(_prompt_paths())
    forbidden = set(manifest.forbidden_effects)
    assert {
        "git-side-effect",
        "stage-side-effect",
        "github-side-effect",
        "active-opencode-write",
        "business-code-write",
        "test-code-write",
        "project-toml-write",
    } <= forbidden


def test_is_diff_in_scope_accepts_design_doc() -> None:
    """AC-FR0300-01: an in-scope design doc edit is accepted."""
    manifest = build_write_manifest(
        spec_id=_SPEC_ID,
        design_doc_paths=_design_doc_paths(),
        contract_paths=_contract_paths(),
        prompt_paths=_prompt_paths(),
    )
    assert (
        is_diff_in_scope(manifest, f".louke/project/specs/{_SPEC_ID}/architecture.md")
        is True
    )


def test_is_diff_in_scope_accepts_design_artifact_glob() -> None:
    """AC-FR0300-01: design-artifacts/** is in scope."""
    manifest = build_write_manifest(
        spec_id=_SPEC_ID,
        design_doc_paths=_design_doc_paths(),
        contract_paths=_contract_paths(),
        prompt_paths=_prompt_paths(),
        extra_globs=[f".louke/project/specs/{_SPEC_ID}/design-artifacts/**"],
    )
    assert (
        is_diff_in_scope(
            manifest,
            f".louke/project/specs/{_SPEC_ID}/design-artifacts/contracts/foo.candidate.json",
        )
        is True
    )


def test_is_diff_in_scope_rejects_out_of_scope_path() -> None:
    """AC-FR0300-01: an out-of-scope path is rejected."""
    manifest = build_write_manifest(
        spec_id=_SPEC_ID,
        design_doc_paths=_design_doc_paths(),
        contract_paths=_contract_paths(),
        prompt_paths=_prompt_paths(),
    )
    assert is_diff_in_scope(manifest, "louke/v014/fr0300_write_auth.py") is False
    assert is_diff_in_scope(manifest, ".github/workflows/louke-ci.yml") is False


def test_attribute_diff_accepts_in_scope_change() -> None:
    """AC-FR0300-01: in-scope diff is attributed to the actor."""
    manifest = build_write_manifest(
        spec_id=_SPEC_ID,
        design_doc_paths=_design_doc_paths(),
        contract_paths=_contract_paths(),
        prompt_paths=_prompt_paths(),
    )
    attribution = attribute_diff(
        manifest,
        path=f".louke/project/specs/{_SPEC_ID}/architecture.md",
        actor_id="archer:att-1",
        base_digest="sha256:" + "a" * 64,
        current_digest="sha256:" + "b" * 64,
    )
    assert isinstance(attribution, DiffAttribution)
    assert attribution.actor_id == "archer:att-1"
    assert attribution.in_scope is True
    assert attribution.block_reason is None


def test_attribute_diff_rejects_out_of_scope_change() -> None:
    """AC-FR0300-01: out-of-scope diff is rejected with WRITE_SCOPE_DENIED."""
    manifest = build_write_manifest(
        spec_id=_SPEC_ID,
        design_doc_paths=_design_doc_paths(),
        contract_paths=_contract_paths(),
        prompt_paths=_prompt_paths(),
    )
    with pytest.raises(DesignWriteAuthError) as exc:
        attribute_diff(
            manifest,
            path="louke/v014/fr0300_write_auth.py",
            actor_id="archer:att-1",
            base_digest="sha256:" + "a" * 64,
            current_digest="sha256:" + "b" * 64,
        )
    assert exc.value.code == "WRITE_SCOPE_DENIED"


def test_attribute_diff_rejects_unattributed_change() -> None:
    """AC-FR0300-01: a diff without actor identity is rejected."""
    manifest = build_write_manifest(
        spec_id=_SPEC_ID,
        design_doc_paths=_design_doc_paths(),
        contract_paths=_contract_paths(),
        prompt_paths=_prompt_paths(),
    )
    with pytest.raises(DesignWriteAuthError) as exc:
        attribute_diff(
            manifest,
            path=f".louke/project/specs/{_SPEC_ID}/architecture.md",
            actor_id="",
            base_digest="sha256:" + "a" * 64,
            current_digest="sha256:" + "b" * 64,
        )
    assert exc.value.code == "DESIGN_DIFF_UNATTRIBUTED"


def test_attribute_diff_rejects_git_side_effect_path() -> None:
    """AC-FR0300-01: Git/Stage/GitHub side effects are forbidden even if path is in-tree."""
    manifest = build_write_manifest(
        spec_id=_SPEC_ID,
        design_doc_paths=_design_doc_paths(),
        contract_paths=_contract_paths(),
        prompt_paths=_prompt_paths(),
    )
    with pytest.raises(DesignWriteAuthError) as exc:
        attribute_diff(
            manifest,
            path=".git/refs/heads/main",
            actor_id="archer:att-1",
            base_digest="sha256:" + "a" * 64,
            current_digest="sha256:" + "b" * 64,
        )
    assert exc.value.code == "WRITE_SCOPE_DENIED"


def test_manifest_immutable() -> None:
    """AC-FR0300-01: the manifest is immutable once issued."""
    manifest = build_write_manifest(
        spec_id=_SPEC_ID,
        design_doc_paths=_design_doc_paths(),
        contract_paths=_contract_paths(),
        prompt_paths=_prompt_paths(),
    )
    with pytest.raises(Exception):
        manifest.spec_id = "tampered"  # type: ignore[misc]


def test_manifest_to_json_round_trips() -> None:
    """AC-FR0300-01: manifest serialises for the task-manifest allowlist."""
    manifest = build_write_manifest(
        spec_id=_SPEC_ID,
        design_doc_paths=_design_doc_paths(),
        contract_paths=_contract_paths(),
        prompt_paths=_prompt_paths(),
    )
    import json

    payload = json.loads(manifest.to_json())
    assert payload["spec_id"] == _SPEC_ID
    assert payload["design_doc_paths"] == _design_doc_paths()
    assert "git-side-effect" in payload["forbidden_effects"]
