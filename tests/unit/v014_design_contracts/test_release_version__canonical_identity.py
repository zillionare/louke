"""AC-FR1400-01: canonical release identity & version source.

FR-1400 requires a registry required kind ``release-version`` contract instance
that maps the Human canonical version to release branch/tag and a host project
version source, with adapter/read/prepare/compare semantics.  Already-covered:
the ``inspect-source`` adapter subcommand.  This test extends with the
canonical version mapping, prefix normalization, version-source identity, and
failure semantics for missing/invalid mappings.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from louke._tools import contract_registry as reg
from louke._tools.release_version import (
    ReleaseVersionError,
    canonical_to_branch,
    canonical_to_tag,
    load_contract,
    normalise_external_version,
    resolve_version_source,
    verify_canonical_mapping,
)

_SPEC_ROOT = (
    Path(__file__).resolve().parents[3]
    / ".louke"
    / "project"
    / "specs"
    / "v0.14-002-workflow-reflow-design"
)
_CONTRACT = (
    _SPEC_ROOT / "design-artifacts" / "contracts" / "release-version.candidate.json"
)


def _contract() -> dict[str, Any]:
    return json.loads(_CONTRACT.read_bytes())


def test_registry_discovers_release_version_kind() -> None:
    """AC-FR1400-01: registry discovers the release-version required kind."""
    view = reg.discover("release-version")
    assert [s["kind"] for s in view.schemas] == ["release-version"]
    schema = view.schemas[0]
    assert schema["identity"] == "louke.machine-contract.release-version"
    assert schema["version"] == "1.0.0"
    assert schema["digest"].startswith("sha256:")


def test_load_contract_returns_canonical_envelope() -> None:
    """AC-FR1400-01: the contract loads with the canonical envelope."""
    contract = load_contract(_CONTRACT)
    assert contract["kind"] == "release-version"
    assert contract["identity"] == "louke.contract.v0.14-002.release-version"
    assert contract["schema_ref"]["identity"] == (
        "louke.machine-contract.release-version"
    )


def test_canonical_to_branch_and_tag_match_louke_0_14_0() -> None:
    """AC-FR1400-01: canonical 0.14.0 maps to releases/0.14.0 + v0.14.0."""
    assert canonical_to_branch("0.14.0") == "releases/0.14.0"
    assert canonical_to_tag("0.14.0") == "v0.14.0"


def test_normalise_external_version_strips_v_prefix() -> None:
    """AC-FR1400-01: the v prefix is stripped before PEP 440 comparison."""
    assert normalise_external_version("v0.14.0") == "0.14.0"
    assert normalise_external_version("0.14.0") == "0.14.0"


def test_normalise_external_version_rejects_non_pep440() -> None:
    """AC-FR1400-01: a non-PEP-440 version cannot be normalised."""
    with pytest.raises(ReleaseVersionError) as exc:
        normalise_external_version("v0.14.0-foo bar")
    assert exc.value.code == "RELEASE_VERSION_INVALID"


def test_resolve_version_source_returns_path_and_selector() -> None:
    """AC-FR1400-01: the version source path/selector are resolvable."""
    contract = _contract()
    source = resolve_version_source(contract)
    assert source["path"] == "pyproject.toml"
    assert source["selector"] == "project.version"


def test_verify_canonical_mapping_passes_for_louke_0_14_0() -> None:
    """AC-FR1400-01: canonical->adapter->branch/tag mapping is consistent."""
    contract = _contract()
    verify_canonical_mapping(
        contract,
        canonical_version="0.14.0",
        branch="releases/0.14.0",
        tag="v0.14.0",
    )  # does not raise


def test_verify_canonical_mapping_rejects_branch_mismatch() -> None:
    """AC-FR1400-01: a branch mismatch with canonical version fails."""
    contract = _contract()
    with pytest.raises(ReleaseVersionError) as exc:
        verify_canonical_mapping(
            contract,
            canonical_version="0.14.0",
            branch="releases/0.13.1",
            tag="v0.14.0",
        )
    assert exc.value.code == "RELEASE_VERSION_MISMATCH"


def test_verify_canonical_mapping_rejects_tag_mismatch() -> None:
    """AC-FR1400-01: a tag mismatch with canonical version fails."""
    contract = _contract()
    with pytest.raises(ReleaseVersionError) as exc:
        verify_canonical_mapping(
            contract,
            canonical_version="0.14.0",
            branch="releases/0.14.0",
            tag="v0.13.1",
        )
    assert exc.value.code == "RELEASE_VERSION_MISMATCH"


def test_verify_canonical_mapping_rejects_tag_only() -> None:
    """AC-FR1400-01: branch/tag alone cannot prove version source."""
    contract = _contract()
    with pytest.raises(ReleaseVersionError) as exc:
        verify_canonical_mapping(
            contract,
            canonical_version="",
            branch="releases/0.14.0",
            tag="v0.14.0",
        )
    assert exc.value.code == "RELEASE_VERSION_INVALID"


def test_contract_does_not_ask_human_to_choose_tech_stack() -> None:
    """AC-FR1400-01: contract must not require Human to choose Maven/npm/Cargo/etc."""
    text = json.dumps(_contract())
    forbidden = ("choose Maven", "choose npm", "choose Cargo", "Human must pick")
    for token in forbidden:
        assert token not in text


def test_contract_evidence_separates_scheme_and_prepared() -> None:
    """AC-FR1400-01: evidence records version-scheme-selected and version-source-prepared."""
    payload = _contract()["payload"]
    evidence = payload["evidence"]
    assert "version-scheme-selected" in evidence
    assert "version-source-prepared" in evidence


def test_failure_policy_fail_closed_with_explicit_reasons() -> None:
    """AC-FR1400-01: failure policy fail_closed with explicit reasons."""
    policy = _contract()["payload"]["failure_policy"]
    assert policy["fail_closed"] is True
    expected_reasons = {"missing", "invalid", "mismatch", "unknown", "drift"}
    assert expected_reasons <= set(policy["non_success"])


def test_node_release_version_fixture_uses_same_schema() -> None:
    """AC-FR1400-01: a Node/SemVer/package.json fixture validates under the same schema."""
    node_fixture = (
        _SPEC_ROOT
        / "design-artifacts"
        / "validation"
        / "release-version-node-host.valid.candidate.json"
    )
    payload = json.loads(node_fixture.read_bytes())
    assert payload["schema_ref"]["identity"] == (
        "louke.machine-contract.release-version"
    )
    # The Node fixture must NOT reference Python-specific identifiers
    text = json.dumps(payload)
    assert "pyproject.toml" not in text
    assert "PEP 440" not in text
    # It should reference Node-specific identifiers
    assert "package.json" in text


def test_louke_uses_python_release_adapter() -> None:
    """AC-FR1400-01: Louke uses tools/louke_python_release_adapter.py."""
    payload = _contract()["payload"]
    assert payload["adapter"] == "tools/louke_python_release_adapter.py"
    assert "inspect-source" in payload["read_command"]
    assert "prepare --tag v0.14.0" in payload["prepare_command"]


def test_write_policy_only_isolated_build_workspace() -> None:
    """AC-FR1400-01: write policy only writes to isolated build workspace version source."""
    payload = _contract()["payload"]
    write_policy = payload["write_policy"].lower()
    assert "isolated" in write_policy
    assert "user workspace" in write_policy or "pr validates only" in write_policy
