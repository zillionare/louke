"""IF-CON-01 machine contract instance envelope resolver (FR-1900).

A candidate machine-contract instance never carries its own digest or schema:
its full bytes digest is resolved from the unique external design-artifact
manifest entry (``manifest_ref.identity + revision + kind``), and its facts /
task-manifest provenance must resolve to the declared artifact kind/path/bytes.
Any drift fails closed with a ``CONTRACT_*`` code.  Read-only over the host
design-artifact tree; schema authority stays with the registry.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

CONTRACT_ERROR_CODES = (
    "CONTRACT_KIND_MISSING",
    "CONTRACT_MANIFEST_AMBIGUOUS",
    "CONTRACT_DIGEST_MISMATCH",
    "CONTRACT_PROVENANCE_MISMATCH",
)

_MANIFEST_NAME = "design-artifact-manifest.candidate.json"


class ContractError(Exception):
    """A fail-closed contract-instance rejection carrying an IF-CON-01 code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class ResolvedContract:
    """The external-manifest resolution of a contract instance."""

    contract_path: str
    contract_digest: str


def _file_digest(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def load_manifest(spec_root: Path) -> dict[str, Any]:
    """Load the external design-artifact manifest under ``spec_root``."""
    path = Path(spec_root) / "design-artifacts" / _MANIFEST_NAME
    if not path.is_file():
        raise ContractError(
            "CONTRACT_MANIFEST_AMBIGUOUS", f"manifest not found: {path}"
        )
    return json.loads(path.read_bytes())


def _da_path(spec_root: Path, rel: str) -> Path:
    # Manifest paths are recorded relative to the spec root (``design-artifacts/...``).
    return Path(spec_root) / rel


def resolve_contract(
    instance: dict[str, Any], manifest: dict[str, Any], *, spec_root: Path
) -> ResolvedContract:
    """Resolve a contract instance's full bytes digest via the manifest.

    Locates the unique ``contract_instances`` entry whose kind matches the
    instance and whose manifest identity/revision bind the instance's
    ``manifest_ref``, verifies the recorded bytes digest against the file on
    disk, and returns ``{contract_path, contract_digest}``.  IF-CON-01.
    """
    kind = instance.get("kind")
    if not kind:
        raise ContractError("CONTRACT_KIND_MISSING", "instance has no kind")
    manifest_ref = instance.get("manifest_ref", {})
    if manifest_ref.get("identity") != manifest.get(
        "manifest_identity"
    ) or manifest_ref.get("revision") != manifest.get("manifest_revision"):
        raise ContractError(
            "CONTRACT_MANIFEST_AMBIGUOUS",
            f"manifest_ref does not bind manifest identity/revision for {kind}",
        )
    entries = [
        e for e in manifest.get("contract_instances", []) if e.get("kind") == kind
    ]
    if len(entries) != 1:
        raise ContractError(
            "CONTRACT_MANIFEST_AMBIGUOUS",
            f"expected exactly one manifest entry for kind {kind}, found {len(entries)}",
        )
    entry = entries[0]
    data = _da_path(spec_root, entry["path"]).read_bytes()
    actual = _file_digest(data)
    if actual != entry["digest"]:
        raise ContractError(
            "CONTRACT_DIGEST_MISMATCH",
            f"bytes digest drift for {kind}: {actual} != {entry['digest']}",
        )
    return ResolvedContract(
        contract_path=entry["path"], contract_digest=entry["digest"]
    )


def _require_provenance(
    manifest: dict[str, Any],
    *,
    spec_root: Path,
    expected_kind: str,
    declared_digest: str,
    artifact: dict[str, Any],
) -> None:
    if artifact.get("kind") != expected_kind:
        raise ContractError(
            "CONTRACT_PROVENANCE_MISMATCH",
            f"artifact kind {artifact.get('kind')} != {expected_kind}",
        )
    inputs = [
        e for e in manifest.get("input_artifacts", []) if e.get("kind") == expected_kind
    ]
    if len(inputs) != 1:
        raise ContractError(
            "CONTRACT_PROVENANCE_MISMATCH",
            f"expected one input artifact of kind {expected_kind}, found {len(inputs)}",
        )
    source = inputs[0]
    if artifact.get("path") != source["path"]:
        raise ContractError(
            "CONTRACT_PROVENANCE_MISMATCH",
            f"declared path {artifact.get('path')} != manifest path {source['path']}",
        )
    if declared_digest != source["digest"]:
        raise ContractError(
            "CONTRACT_PROVENANCE_MISMATCH",
            f"declared digest for {expected_kind} != manifest digest",
        )
    actual = _file_digest(_da_path(spec_root, source["path"]).read_bytes())
    if actual != source["digest"]:
        raise ContractError(
            "CONTRACT_PROVENANCE_MISMATCH",
            f"bytes digest drift for {expected_kind}: {actual} != {source['digest']}",
        )


def verify_provenance(
    instance: dict[str, Any], manifest: dict[str, Any], *, spec_root: Path
) -> None:
    """Verify the instance's facts and task-manifest provenance, fail-closed.

    ``scope.project_facts_digest`` must resolve to the ``host-project-facts-
    snapshot`` artifact and ``generated_by.task_manifest_digest`` to the
    ``archer-author-task-manifest`` artifact, each by declared kind/path/bytes.
    IF-CON-01.
    """
    scope = instance.get("scope", {})
    generated_by = instance.get("generated_by", {})
    _require_provenance(
        manifest,
        spec_root=spec_root,
        expected_kind="host-project-facts-snapshot",
        declared_digest=scope.get("project_facts_digest", ""),
        artifact=scope.get("project_facts_artifact", {}),
    )
    _require_provenance(
        manifest,
        spec_root=spec_root,
        expected_kind="archer-author-task-manifest",
        declared_digest=generated_by.get("task_manifest_digest", ""),
        artifact=generated_by.get("task_manifest_artifact", {}),
    )
