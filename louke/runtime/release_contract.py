"""Runtime-owned release contract bundle and entry-definition read model.

The manifest is the single input consumed by the Web Runtime catalog for the
Louke v0.14 bootstrap.  Host projects may use the normal production catalog,
but they cannot opt into this development-only mode.
"""

from __future__ import annotations

import hashlib
import json
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from louke.runtime.catalog import Edge, Step, WorkflowDefinition


MANIFEST_RELATIVE_PATH = Path(".louke/project/release-contract-bundle.json")
LOUKE_REPOSITORY = "github.com/zillionare/louke"
DEVELOPMENT_BOOTSTRAP_MODE = "development_bootstrap"


class ReleaseContractError(ValueError):
    """Raised when the Runtime release contract bundle is invalid or stale."""


class DevelopmentBootstrapError(ReleaseContractError):
    """Raised when development bootstrap is requested outside Louke itself."""


@dataclass(frozen=True, slots=True)
class ContractFile:
    """A current file identity bound into one release contract."""

    path: str
    revision: int | str
    content_digest: str


@dataclass(frozen=True, slots=True)
class ReleaseContract:
    """One versioned contract in a release bundle."""

    spec_id: str
    role: str
    files: tuple[ContractFile, ...]


@dataclass(frozen=True, slots=True)
class ReleaseContractBundle:
    """The immutable Runtime read model for one release contract bundle."""

    manifest_id: str
    release: str
    entry_spec: str
    status: str
    mode: str
    locked_at: str
    human_decision: dict[str, Any]
    checks: dict[str, str]
    contracts: tuple[ReleaseContract, ...]
    definition: dict[str, Any]

    @property
    def contract_ids(self) -> tuple[str, ...]:
        """Return the ordered contract identities in this bundle."""
        return tuple(contract.spec_id for contract in self.contracts)


def is_louke_workspace(workspace_root: str | Path) -> bool:
    """Return whether ``workspace_root`` is the Louke source workspace.

    Args:
        workspace_root: Candidate workspace root to inspect.

    Returns:
        ``True`` only when the project identity is Louke's repository and the
        source package marker is present.

    Raises:
        OSError: Propagated only for unexpected filesystem errors.
    """
    root = Path(workspace_root).resolve()
    project_path = root / ".louke" / "project" / "project.toml"
    package_marker = root / "louke" / "__init__.py"
    if not project_path.is_file() or not package_marker.is_file():
        return False
    try:
        project = tomllib.loads(project_path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return False
    return project.get("project", {}).get("repo") == LOUKE_REPOSITORY


def load_release_contract_bundle(
    workspace_root: str | Path,
    *,
    mode: str,
) -> ReleaseContractBundle:
    """Load and verify the current Runtime release contract bundle.

    Args:
        workspace_root: Workspace containing the manifest and contract files.
        mode: Runtime mode. ``development_bootstrap`` is restricted to Louke.

    Returns:
        The parsed and byte-verified :class:`ReleaseContractBundle`.

    Raises:
        DevelopmentBootstrapError: If bootstrap is requested for a host
            project or with a non-bootstrap manifest.
        ReleaseContractError: If the manifest is missing, malformed, or stale.
    """
    if mode != DEVELOPMENT_BOOTSTRAP_MODE:
        raise ReleaseContractError(
            f"release contract bootstrap requires mode={DEVELOPMENT_BOOTSTRAP_MODE!r}"
        )
    root = Path(workspace_root).resolve()
    if not is_louke_workspace(root):
        raise DevelopmentBootstrapError(
            "development_bootstrap is allowed only for the Louke workspace"
        )
    manifest_path = root / MANIFEST_RELATIVE_PATH
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ReleaseContractError(
            f"release contract manifest missing: {manifest_path}"
        ) from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise ReleaseContractError(
            f"release contract manifest unreadable: {manifest_path}"
        ) from exc
    bundle = _parse_bundle(payload)
    if bundle.mode != mode:
        raise DevelopmentBootstrapError(
            f"manifest mode {bundle.mode!r} does not enable {mode!r}"
        )
    _verify_contract_files(root, bundle)
    return bundle


def build_entry_definition(bundle: ReleaseContractBundle) -> WorkflowDefinition:
    """Build the immutable catalog definition declared by ``bundle``.

    Args:
        bundle: Verified Runtime release contract bundle.

    Returns:
        The versioned Web Runtime workflow definition.

    Raises:
        ReleaseContractError: If the manifest definition is incomplete.
    """
    raw_steps = bundle.definition.get("steps")
    if not isinstance(raw_steps, list) or not raw_steps:
        raise ReleaseContractError("bundle definition must declare ordered steps")
    steps = tuple(_parse_step(raw_step) for raw_step in raw_steps)
    return WorkflowDefinition(
        definition_id=_required_string(bundle.definition, "definition_id"),
        version=_required_string(bundle.definition, "version"),
        start_step=_required_string(bundle.definition, "start_step"),
        steps=steps,
        contract_bundle_id=bundle.manifest_id,
        contract_bundle_release=bundle.release,
        contract_sources=bundle.contract_ids,
    )


def _parse_bundle(payload: dict[str, Any]) -> ReleaseContractBundle:
    """Parse the manifest payload into the typed Runtime read model."""
    if not isinstance(payload, dict):
        raise ReleaseContractError("release contract manifest must be an object")
    contracts = tuple(
        _parse_contract(item) for item in _required_list(payload, "contracts")
    )
    required_ids = (
        "v0.14-001-workflow-reflow-spec",
        "v0.14-002-workflow-reflow-design",
        "v0.14-003-workflow-reflow-impl",
    )
    if tuple(contract.spec_id for contract in contracts) != required_ids:
        raise ReleaseContractError(
            "release bundle must contain 001, 002 and 003 in order"
        )
    checks = payload.get("checks")
    decision = payload.get("human_decision")
    if not isinstance(checks, dict) or not isinstance(decision, dict):
        raise ReleaseContractError(
            "bundle checks and human_decision are required objects"
        )
    return ReleaseContractBundle(
        manifest_id=_required_string(payload, "manifest_id"),
        release=_required_string(payload, "release"),
        entry_spec=_required_string(payload, "entry_spec"),
        status=_required_string(payload, "status"),
        mode=_required_string(payload, "mode"),
        locked_at=_required_string(payload, "locked_at"),
        human_decision=decision,
        checks={str(key): str(value) for key, value in checks.items()},
        contracts=contracts,
        definition=_required_object(payload, "definition"),
    )


def _parse_contract(payload: Any) -> ReleaseContract:
    """Parse one contract entry from the manifest."""
    if not isinstance(payload, dict):
        raise ReleaseContractError("bundle contract entry must be an object")
    files = tuple(_parse_file(item) for item in _required_list(payload, "files"))
    return ReleaseContract(
        spec_id=_required_string(payload, "spec_id"),
        role=_required_string(payload, "role"),
        files=files,
    )


def _parse_file(payload: Any) -> ContractFile:
    """Parse one file identity from a contract entry."""
    if not isinstance(payload, dict):
        raise ReleaseContractError("bundle file entry must be an object")
    revision = payload.get("revision")
    if not isinstance(revision, (int, str)) or isinstance(revision, bool):
        raise ReleaseContractError("bundle file revision must be a string or integer")
    return ContractFile(
        path=_required_string(payload, "path"),
        revision=revision,
        content_digest=_required_string(payload, "content_digest"),
    )


def _parse_step(payload: Any) -> Step:
    """Parse one immutable workflow step declared by the manifest."""
    if not isinstance(payload, dict):
        raise ReleaseContractError("bundle definition step must be an object")
    raw_edges = payload.get("transitions", [])
    if not isinstance(raw_edges, list):
        raise ReleaseContractError("bundle step transitions must be a list")
    edges = tuple(
        Edge(
            edge_id=_required_string(edge, "edge_id"),
            from_step=_required_string(edge, "from_step"),
            to_step=_required_string(edge, "to_step"),
            condition=str(edge.get("condition", "")),
        )
        for edge in raw_edges
        if isinstance(edge, dict)
    )
    if len(edges) != len(raw_edges):
        raise ReleaseContractError("bundle transition must be an object")
    return Step(
        step_id=_required_string(payload, "step_id"),
        kind=_required_string(payload, "kind"),
        transitions=edges,
        handler=payload.get("handler"),
        capability=payload.get("capability"),
        owner=_required_string(payload, "owner"),
        contract_source=_required_string(payload, "contract_source"),
        implemented=bool(payload.get("implemented", False)),
    )


def _verify_contract_files(root: Path, bundle: ReleaseContractBundle) -> None:
    """Verify every manifest digest against the current workspace bytes."""
    for contract in bundle.contracts:
        for artifact in contract.files:
            path = (root / artifact.path).resolve()
            if root not in path.parents:
                raise ReleaseContractError(
                    f"contract path escapes workspace: {artifact.path}"
                )
            if not path.is_file():
                raise ReleaseContractError(f"contract file missing: {artifact.path}")
            digest = "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
            if digest != artifact.content_digest:
                raise ReleaseContractError(
                    f"contract digest stale for {artifact.path}: expected "
                    f"{artifact.content_digest}, got {digest}"
                )


def _required_string(payload: dict[str, Any], key: str) -> str:
    """Return a required non-empty string field."""
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise ReleaseContractError(f"bundle field {key!r} must be a non-empty string")
    return value


def _required_list(payload: dict[str, Any], key: str) -> list[Any]:
    """Return a required list field."""
    value = payload.get(key)
    if not isinstance(value, list):
        raise ReleaseContractError(f"bundle field {key!r} must be a list")
    return value


def _required_object(payload: dict[str, Any], key: str) -> dict[str, Any]:
    """Return a required object field."""
    value = payload.get(key)
    if not isinstance(value, dict):
        raise ReleaseContractError(f"bundle field {key!r} must be an object")
    return value
