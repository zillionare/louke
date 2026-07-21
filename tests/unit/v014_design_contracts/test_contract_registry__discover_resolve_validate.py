"""AC-FR0700-01: IF-REG-01 machine contract registry discover/resolve/validate.

The registry (``louke/_tools/contract_registry.py`` over ``louke/schemas/``)
must discover the seven required machine-contract kinds plus the four Agent I/O
schemas, resolve fail-closed while the atomic activation gate is open, and
validate instance bytes against packaged schemas.  Pure package-owned readback;
no host wiring.
"""

from __future__ import annotations

import json

import pytest

from louke._tools import contract_registry as reg

_REQUIRED_MACHINE_KINDS = (
    "integration-test",
    "e2e-test",
    "pre-commit",
    "github-actions-ci",
    "release-version",
    "build-artifact",
    "publish-recovery",
)
_AGENT_IO_IDENTITIES = (
    "louke.agent-io.archer-design-task-input",
    "louke.agent-io.archer-design-result",
    "louke.agent-io.prism-design-review-task-input",
    "louke.agent-io.prism-design-review",
)


def _valid_archer_result() -> dict:
    zero = "sha256:" + "0" * 64
    return {
        "status": "candidate_complete",
        "bound_input_digest": zero,
        "artifact_manifest_path": "manifest.json",
        "artifact_manifest_digest": zero,
        "artifacts": [
            {"path": "a.json", "digest": zero, "activation_state": "candidate"}
        ],
        "gaps": [],
        "handoff": "ready",
    }


def test_discover_lists_all_required_machine_kinds() -> None:
    """AC-FR0700-01: all seven required machine-contract kinds are discoverable."""
    view = reg.discover()
    kinds = {
        s["kind"]
        for s in view.schemas
        if s.get("identity", "").startswith("louke.machine-contract.")
    }
    assert kinds == set(_REQUIRED_MACHINE_KINDS)


def test_discover_lists_four_agent_io_schemas() -> None:
    """AC-FR0700-01: the two task inputs plus two outputs are discoverable."""
    view = reg.discover()
    identities = {s["identity"] for s in view.schemas}
    assert set(_AGENT_IO_IDENTITIES) <= identities


def test_discover_every_schema_carries_identity_version_digest() -> None:
    """AC-FR0700-01: each authoritative schema resolves identity/version/digest."""
    for schema in reg.discover().schemas:
        assert schema["identity"]
        assert schema["version"] == "1.0.0"
        assert schema["digest"].startswith("sha256:")
        assert len(schema["digest"]) == len("sha256:") + 64


def test_discover_filter_by_kind() -> None:
    """AC-FR0700-01: discovery may be narrowed to a single required kind."""
    view = reg.discover("integration-test")
    assert [s["kind"] for s in view.schemas] == ["integration-test"]


def test_all_schemas_remain_candidate_until_gate_closes() -> None:
    """AC-FR0700-01: no candidate schema flips active before the atomic gate."""
    for schema in reg.discover().schemas:
        assert schema["status"] == "candidate"


def test_recorded_digests_match_packaged_schema_bytes() -> None:
    """AC-FR0700-01: registry digests are self-consistent with packaged bytes."""
    for schema in reg.discover().schemas:
        path = reg.SCHEMAS_ROOT / schema["path"]
        assert reg.file_digest(path.read_bytes()) == schema["digest"]


def test_resolve_candidate_fails_closed_not_active() -> None:
    """AC-FR0700-01: resolve rejects candidate schemas with SCHEMA_NOT_ACTIVE."""
    schema = reg.discover("integration-test").schemas[0]
    with pytest.raises(reg.RegistryError) as excinfo:
        reg.resolve(schema["identity"], schema["version"], schema["digest"])
    assert excinfo.value.code == "SCHEMA_NOT_ACTIVE"


def test_resolve_unknown_identity() -> None:
    """AC-FR0700-01: unknown identity is rejected, never silently ignored."""
    with pytest.raises(reg.RegistryError) as excinfo:
        reg.resolve(
            "louke.machine-contract.does-not-exist", "1.0.0", "sha256:" + "0" * 64
        )
    assert excinfo.value.code == "SCHEMA_UNKNOWN"


def test_resolve_unknown_version() -> None:
    """AC-FR0700-01: an unknown version has no compatible migration."""
    with pytest.raises(reg.RegistryError) as excinfo:
        reg.resolve(
            "louke.machine-contract.integration-test", "9.9.9", "sha256:" + "0" * 64
        )
    assert excinfo.value.code == "SCHEMA_UNKNOWN"


def test_validate_accepts_conformant_instance() -> None:
    """AC-FR0700-01: a conformant instance validates against its schema."""
    schema = next(
        s
        for s in reg.discover().schemas
        if s["identity"] == "louke.agent-io.archer-design-result"
    )
    ref = reg.SchemaRef(schema["identity"], schema["version"], schema["digest"])
    result = reg.validate(ref, json.dumps(_valid_archer_result()).encode("utf-8"))
    assert result.valid is True
    assert result.errors == []


def test_validate_rejects_missing_required_field() -> None:
    """AC-FR0700-01: a missing required field is rejected, not ignored."""
    schema = next(
        s
        for s in reg.discover().schemas
        if s["identity"] == "louke.agent-io.archer-design-result"
    )
    ref = reg.SchemaRef(schema["identity"], schema["version"], schema["digest"])
    instance = _valid_archer_result()
    del instance["handoff"]
    result = reg.validate(ref, json.dumps(instance).encode("utf-8"))
    assert result.valid is False
    assert any(err["keyword"] == "required" for err in result.errors)


def test_validate_unknown_schema_ref() -> None:
    """AC-FR0700-01: validation against an unknown schema is rejected."""
    ref = reg.SchemaRef("louke.agent-io.nope", "1.0.0", "sha256:" + "0" * 64)
    with pytest.raises(reg.RegistryError) as excinfo:
        reg.validate(ref, b"{}")
    assert excinfo.value.code == "SCHEMA_UNKNOWN"


def test_validate_digest_mismatch() -> None:
    """AC-FR0700-01: a schema ref whose digest drifts is rejected."""
    schema = next(
        s
        for s in reg.discover().schemas
        if s["identity"] == "louke.agent-io.archer-design-result"
    )
    ref = reg.SchemaRef(schema["identity"], schema["version"], "sha256:" + "f" * 64)
    with pytest.raises(reg.RegistryError) as excinfo:
        reg.validate(ref, json.dumps(_valid_archer_result()).encode("utf-8"))
    assert excinfo.value.code == "SCHEMA_DIGEST_MISMATCH"


def test_cli_discover_emits_json(capsys: pytest.CaptureFixture[str]) -> None:
    """AC-FR0700-01: the CLI mirrors discover as machine-readable JSON."""
    code = reg.main(["discover", "--format", "json"])
    assert code == 0
    payload = json.loads(capsys.readouterr().out)
    kinds = {
        s["kind"]
        for s in payload["schemas"]
        if s.get("identity", "").startswith("louke.machine-contract.")
    }
    assert kinds == set(_REQUIRED_MACHINE_KINDS)
