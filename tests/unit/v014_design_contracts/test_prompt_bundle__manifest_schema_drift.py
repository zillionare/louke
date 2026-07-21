"""AC-FR1800-01/AC-FR1900-01/AC-FR2000-01: prompt bundle manifest, schema separation, drift.

Extends the existing prompt_bundle tests with: schema_ref activation_state must
never be 'active' for candidate bundles (FR-1900); prompt sources only carry
schema *references*, never substitute schema (FR-1900); bundle manifest carries
schema_version, bundle_version, role, frontmatter/permission/model abstraction,
protocol/skill refs, owning spec/revision, transformer identity/version/source/
digest (FR-1800); deterministic deployment digest + readback with reconcile on
drift (FR-2000).
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any


from louke._tools import prompt_bundle as pb

_ROOT = Path(__file__).resolve().parents[3]
_SPEC_ROOT = _ROOT / ".louke" / "project" / "specs" / "v0.14-002-workflow-reflow-design"


def _manifest() -> dict[str, Any]:
    return json.loads(
        (
            _SPEC_ROOT / "design-artifacts" / "prompts" / "prompt-bundle.candidate.json"
        ).read_bytes()
    )


# --- FR-1900 Prompt semantic vs schema separation ---------------------------------


def test_schema_refs_are_candidate_never_active() -> None:
    """AC-FR1900-01: candidate schema refs must declare candidate activation_state."""
    manifest = _manifest()
    for source in manifest["sources"]:
        for ref_key in ("input_schema_ref", "output_schema_ref"):
            ref = source[ref_key]
            assert ref["activation_state"] == "candidate"
            assert ref["identity"].startswith("louke.agent-io.")
            assert ref["version"] == "1.0.0"
            assert ref["digest"].startswith("sha256:")


def test_sources_do_not_carry_inline_schema() -> None:
    """AC-FR1900-01: sources reference schemas; they must not embed substitute schemas."""
    manifest = _manifest()
    for source in manifest["sources"]:
        # The source may only carry schema_ref pointers, not actual schema content
        forbidden_keys = {"schema", "schema_body", "schema_definition", "schema_inline"}
        assert not (forbidden_keys & set(source.keys()))


def test_schema_refs_resolve_to_registry_identities() -> None:
    """AC-FR1900-01: every schema ref is one of the four registry Agent I/O identities."""
    manifest = _manifest()
    allowed = {
        "louke.agent-io.archer-design-task-input",
        "louke.agent-io.archer-design-result",
        "louke.agent-io.prism-design-review-task-input",
        "louke.agent-io.prism-design-review",
    }
    for source in manifest["sources"]:
        assert source["input_schema_ref"]["identity"] in allowed
        assert source["output_schema_ref"]["identity"] in allowed


def test_prompt_does_not_self_certify_schema() -> None:
    """AC-FR1900-01: the candidate manifest cannot claim schema active=true."""
    manifest = _manifest()
    for source in manifest["sources"]:
        for ref_key in ("input_schema_ref", "output_schema_ref"):
            assert source[ref_key]["activation_state"] != "active"


# --- FR-1800 Prompt bundle manifest & identity ------------------------------------


def test_manifest_carries_schema_and_bundle_version() -> None:
    """AC-FR1800-01: schema_version and bundle_version are present."""
    manifest = _manifest()
    assert manifest["schema_version"] == "1.0.0"
    assert manifest["bundle_version"]
    assert manifest["bundle_identity"]


def test_manifest_carries_transformer_identity_version_source_digest() -> None:
    """AC-FR1800-01: transformer carries identity/version/source/digest."""
    transformer = _manifest()["transformer"]
    for key in ("identity", "version", "source", "digest"):
        assert transformer[key]
    assert transformer["digest"].startswith("sha256:")


def test_manifest_carries_owning_spec_and_design_revision() -> None:
    """AC-FR1800-01: owning_spec and design_revision are pinned."""
    manifest = _manifest()
    assert manifest["owning_spec"] == "v0.14-002-workflow-reflow-design"
    assert manifest["design_revision"]


def test_manifest_carriers_role_frontmatter_permission_model() -> None:
    """AC-FR1800-01: each source declares role/frontmatter/permission/model."""
    manifest = _manifest()
    for source in manifest["sources"]:
        assert source["role"] in {"archer", "prism"}
        assert source["frontmatter"]
        assert source["permissions"]
        assert source["model_abstraction"]
        assert source["protocol_refs"]
        assert source["skill_refs"]


def test_manifest_activation_state_is_candidate_not_deployed() -> None:
    """AC-FR1800-01: bundle activation_state is candidate-not-deployed."""
    assert _manifest()["activation_state"] == "candidate-not-deployed"


def test_manifest_activation_prerequisites_listed() -> None:
    """AC-FR1800-01: activation prerequisites are explicitly listed."""
    prereq = _manifest()["activation_prerequisites"]
    assert prereq
    assert any("closed set" in p.lower() for p in prereq)
    assert any("trusted" in p.lower() for p in prereq)


def test_manifest_stale_if_covers_source_transformer_environment_inputs() -> None:
    """AC-FR1800-01: stale_if covers all freshness triggers."""
    stale_if = _manifest()["stale_if"]
    joined = " ".join(stale_if).lower()
    assert "source" in joined
    assert "transformer" in joined
    assert "environment" in joined
    assert "rendered" in joined
    assert "requirements" in joined or "design" in joined


# --- FR-2000 Prompt deterministic deployment & drift ------------------------------


def test_bundle_digest_recomputes_deterministically() -> None:
    """AC-FR2000-01/AC-NFR0100-01: same inputs produce same canonical digest."""
    manifest = _manifest()
    first = pb.compute_bundle_digest(manifest)
    second = pb.compute_bundle_digest(manifest)
    assert first == second == manifest["bundle_digest"]


def test_bundle_digest_drift_when_source_changes() -> None:
    """AC-FR2000-01: a modified source digest drifts the bundle digest."""
    manifest = copy.deepcopy(_manifest())
    original = pb.compute_bundle_digest(manifest)
    manifest["sources"][0]["digest"] = "sha256:" + "0" * 64
    drifted = pb.compute_bundle_digest(manifest)
    assert drifted != original


def test_bundle_digest_drift_when_rendered_changes() -> None:
    """AC-FR2000-01: a modified rendered digest drifts the bundle digest."""
    manifest = copy.deepcopy(_manifest())
    original = pb.compute_bundle_digest(manifest)
    manifest["deployments"][0]["rendered_digest"] = "sha256:" + "1" * 64
    drifted = pb.compute_bundle_digest(manifest)
    assert drifted != original


def test_bundle_digest_drift_when_transformer_changes() -> None:
    """AC-FR2000-01: a modified transformer digest drifts the bundle digest."""
    manifest = copy.deepcopy(_manifest())
    original = pb.compute_bundle_digest(manifest)
    manifest["transformer"]["digest"] = "sha256:" + "2" * 64
    drifted = pb.compute_bundle_digest(manifest)
    assert drifted != original


def test_bundle_digest_drift_when_schema_ref_changes() -> None:
    """AC-FR2000-01: a modified input schema ref drifts the bundle digest."""
    manifest = copy.deepcopy(_manifest())
    original = pb.compute_bundle_digest(manifest)
    manifest["sources"][0]["input_schema_ref"]["digest"] = "sha256:" + "3" * 64
    drifted = pb.compute_bundle_digest(manifest)
    assert drifted != original


def test_bundle_digest_forbids_current_or_digest_source_placeholder() -> None:
    """AC-FR1900-01/AC-FR2000-01: bundle_digest must not be 'current' or 'digest_source'."""
    manifest = _manifest()
    assert manifest["bundle_digest"] not in ("current", "digest_source")
    assert manifest["bundle_digest"].startswith("sha256:")
    for source in manifest["sources"]:
        for ref_key in ("input_schema_ref", "output_schema_ref"):
            ref = source[ref_key]
            assert ref["digest"] not in ("current", "digest_source")
            assert ref["identity"] not in ("current", "digest_source")


def test_staging_readback_in_sync_for_pinned_tree() -> None:
    """AC-FR2000-01: readback of the pinned tree is candidate_staging_in_sync."""
    result = pb.staging_readback(_manifest(), spec_root=_SPEC_ROOT, repo_root=_ROOT)
    assert result["status"] == "candidate_staging_in_sync"
    assert result["active_changed"] is False


def test_staging_readback_returns_records_for_each_role() -> None:
    """AC-FR2000-01: readback returns one record per role."""
    result = pb.staging_readback(_manifest(), spec_root=_SPEC_ROOT, repo_root=_ROOT)
    roles = {r["role"] for r in result["records"]}
    assert roles == {"archer", "prism"}


def test_staging_readback_never_claims_active_in_sync() -> None:
    """AC-FR2000-01: readback is staging-only; never claims active in_sync."""
    result = pb.staging_readback(_manifest(), spec_root=_SPEC_ROOT, repo_root=_ROOT)
    assert result["readback_kind"] == "candidate-staging"
    assert result["active_changed"] is False


def test_deployment_readback_candidate_file_exists() -> None:
    """AC-FR2000-01: deployment-readback.candidate.json is present and pinned."""
    readback_path = (
        _SPEC_ROOT
        / "design-artifacts"
        / "prompts"
        / "deployment-readback.candidate.json"
    )
    assert readback_path.is_file()
    payload = json.loads(readback_path.read_bytes())
    assert payload["bundle_identity"] == _manifest()["bundle_identity"]
    assert payload["transformer_expected"] == _manifest()["transformer"]["digest"]


def test_reviewer_binding_candidate_file_exists() -> None:
    """AC-FR2050-01/AC-FR2500-01: reviewer-binding.candidate.json pins trusted reviewer."""
    binding_path = (
        _SPEC_ROOT / "design-artifacts" / "prompts" / "reviewer-binding.candidate.json"
    )
    assert binding_path.is_file()
    payload = json.loads(binding_path.read_bytes())
    assert payload["reviewer_execution_bundle"]["state"] == "trusted-active-existing"
    assert payload["reviewed_candidate_bundle"]["state"] == "candidate-not-deployed"
