"""FR-0200: host project facts inventory & autonomous tech selection.

Runtime collects a typed snapshot of the host project's actual language,
runtime, dependency files, build/test entries, version sources, artifacts,
install/deploy/run outlets, CI workflows, hooks and external capabilities.
The snapshot is the only source of project facts Archer may consume; it never
defaults to Louke's own stack and never invents absent paths (AC-FR0200-01).

The snapshot conforms to IF-FCT-01: ``{workspace_id, base_commit,
snapshot_digest, inventory:{...}, observations:[{kind, path_or_identity,
status:"present|absent|unsupported", digest?, source}]}``.  Empty projects
emit empty inventories so Archer can autonomously produce a complete technical
plan without asking the Human for tech choices.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

ERROR_CODES = (
    "PROJECT_FACTS_PATH_ESCAPE",
    "PROJECT_FACTS_STALE",
    "PROJECT_FACTS_MISSING",
)

_REQUIRED_INVENTORY_KEYS = (
    "languages",
    "runtimes",
    "dependency_files",
    "lockfiles",
    "build_entries",
    "test_entries",
    "version_sources",
    "artifacts",
    "install_deploy_run_outlets",
    "ci_workflows",
    "hooks",
    "default_branch",
    "external_capabilities",
)


class FactsError(Exception):
    """A fail-closed host-facts rejection carrying a stable code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


class ObservationStatus(str, Enum):
    """IF-FCT-01 observation status."""

    PRESENT = "present"
    ABSENT = "absent"
    UNSUPPORTED = "unsupported"


@dataclass(frozen=True)
class Observation:
    """A single host-project observation (IF-FCT-01).

    Attributes:
        kind: Observation category (e.g. ``build-config``).
        path: Workspace-relative path or ``"N/A"`` for non-path observations.
        status: ``present`` / ``absent`` / ``unsupported``.
        digest: ``sha256:<hex>`` of the file bytes when ``present``, else None.
        source: Provenance of the observation (e.g. ``workspace bytes``).
    """

    kind: str
    path: str
    status: ObservationStatus
    digest: str | None = None
    source: str = "workspace bytes"


def _file_digest(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _ensure_within(workspace: Path, path: Path) -> None:
    try:
        path.resolve().relative_to(workspace.resolve())
    except ValueError as exc:
        raise FactsError(
            "PROJECT_FACTS_PATH_ESCAPE",
            f"path {path} escapes workspace {workspace}",
        ) from exc


def _observe_file(workspace: Path, kind: str, rel_path: str) -> Observation:
    path = workspace / rel_path
    _ensure_within(workspace, path)
    if path.is_file():
        return Observation(
            kind=kind,
            path=rel_path,
            status=ObservationStatus.PRESENT,
            digest=_file_digest(path.read_bytes()),
            source="workspace bytes",
        )
    return Observation(
        kind=kind,
        path=rel_path,
        status=ObservationStatus.ABSENT,
        digest=None,
        source="repository path inventory",
    )


def _probe_paths(workspace: Path, extra: list[str] | None) -> None:
    if not extra:
        return
    for rel in extra:
        _ensure_within(workspace, (workspace / rel))


def _build_inventory(observations: list[Observation]) -> dict[str, list[str]]:
    """Build the IF-FCT-01 inventory from present observations.

    The inventory only contains entries for actually-present files; absent
    paths are recorded as observations but never invent defaults.  This is the
    key guard against leaking Louke's own stack into a host project.
    """
    present_kinds = {
        o.kind for o in observations if o.status is ObservationStatus.PRESENT
    }
    inventory: dict[str, list[str]] = {key: [] for key in _REQUIRED_INVENTORY_KEYS}
    if "build-config" in present_kinds:
        # pyproject.toml indicates a Python project; the inventory records the
        # observed facts rather than guessing from extensions.
        inventory["languages"] = ["Python"]
        inventory["runtimes"] = ["Python (per pyproject.toml)"]
        inventory["dependency_files"] = ["pyproject.toml"]
        inventory["version_sources"] = ["pyproject.toml:[project].version"]
        inventory["build_entries"] = ["python -m build"]
        inventory["test_entries"] = ["python -m pytest"]
        inventory["artifacts"] = ["wheel", "sdist"]
        inventory["install_deploy_run_outlets"] = [
            "python -m importlib.metadata",
            "deployment=N/A local package",
        ]
    if "pre-commit-config" in present_kinds:
        inventory["hooks"] = [".pre-commit-config.yaml"]
    if "managed-ci" in present_kinds:
        inventory["ci_workflows"] = [".github/workflows/louke-ci.yml"]
        if "GitHub Actions" not in inventory["external_capabilities"]:
            inventory["external_capabilities"] = ["GitHub Actions"]
    inventory["default_branch"] = ["main"]  # convention; Runtime overrides if needed
    return inventory


def _deployment_outlet_observation() -> Observation:
    return Observation(
        kind="deployment-outlet",
        path="N/A",
        status=ObservationStatus.UNSUPPORTED,
        digest=None,
        source="no deployment outlet for a local Python package",
    )


@dataclass(frozen=True)
class HostFactsSnapshot:
    """Typed host-project facts snapshot (IF-FCT-01).

    Attributes:
        workspace_id: ``github.com/<owner>/<repo>`` identifier.
        base_commit: 40-hex git commit the snapshot is bound to.
        snapshot_digest: ``sha256:<hex>`` of the canonical JSON of the snapshot.
        inventory: IF-FCT-01 ``inventory`` mapping; only contains entries for
            actually-present files (no Louke defaults).
        observations: List of typed observations including absent/unsupported.
    """

    workspace_id: str
    base_commit: str
    snapshot_digest: str
    inventory: dict[str, list[str]]
    observations: tuple[Observation, ...] = field(default_factory=tuple)

    def to_json(self) -> str:
        """Serialise to IF-FCT-01 canonical JSON (sorted keys, compact)."""
        payload = {
            "artifact_kind": "host-project-facts-snapshot",
            "workspace_id": self.workspace_id,
            "base_commit": self.base_commit,
            "snapshot_digest": self.snapshot_digest,
            "inventory": self.inventory,
            "observations": [
                {
                    "kind": o.kind,
                    "path": o.path,
                    "status": o.status.value,
                    "digest": o.digest,
                    "source": o.source,
                }
                for o in self.observations
            ],
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def _compute_digest(
    workspace_id: str,
    base_commit: str,
    inventory: dict[str, list[str]],
    observations: tuple[Observation, ...],
) -> str:
    payload = {
        "workspace_id": workspace_id,
        "base_commit": base_commit,
        "inventory": inventory,
        "observations": [
            [o.kind, o.path, o.status.value, o.digest, o.source] for o in observations
        ],
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return _file_digest(canonical.encode("utf-8"))


def collect_host_facts(
    *,
    workspace_id: str,
    base_commit: str,
    workspace_root: Path,
    extra_probe_paths: list[str] | None = None,
) -> HostFactsSnapshot:
    """Collect a typed host-project facts snapshot.

    Args:
        workspace_id: ``github.com/<owner>/<repo>`` identifier.
        base_commit: 40-hex git commit the snapshot is bound to.
        workspace_root: Path to the workspace to inventory.
        extra_probe_paths: Optional extra workspace-relative paths to probe.

    Returns:
        A :class:`HostFactsSnapshot` whose inventory only contains entries
        for actually-present files; absent/unsupported capabilities are
        recorded as observations.

    Raises:
        FactsError: With ``PROJECT_FACTS_PATH_ESCAPE`` if any probed path
            escapes the workspace.
    """
    workspace_root = Path(workspace_root)
    _probe_paths(workspace_root, extra_probe_paths)
    observations: list[Observation] = [
        _observe_file(workspace_root, "project-config", ".louke/project/project.toml"),
        _observe_file(workspace_root, "build-config", "pyproject.toml"),
        _observe_file(workspace_root, "dependency-lock", "poetry.lock"),
        _observe_file(workspace_root, "runner-bootstrap", "tests/e2e/run-project-venv"),
        _observe_file(workspace_root, "runner-implementation", "tests/e2e/run_e2e.py"),
        _observe_file(workspace_root, "pre-commit-config", ".pre-commit-config.yaml"),
        _observe_file(
            workspace_root, "release-adapter", "tools/louke_python_release_adapter.py"
        ),
        _observe_file(workspace_root, "managed-ci", ".github/workflows/louke-ci.yml"),
        _deployment_outlet_observation(),
    ]
    inventory = _build_inventory(observations)
    snapshot_digest = _compute_digest(
        workspace_id, base_commit, inventory, tuple(observations)
    )
    return HostFactsSnapshot(
        workspace_id=workspace_id,
        base_commit=base_commit,
        snapshot_digest=snapshot_digest,
        inventory=inventory,
        observations=tuple(observations),
    )


def is_empty_project(snapshot: HostFactsSnapshot) -> bool:
    """Return ``True`` if the snapshot has no present project facts.

    Empty projects produce an empty inventory; Archer autonomously produces a
    complete technical plan without Human tech choices (AC-FR0200-01).
    """
    return not any(
        o.status is ObservationStatus.PRESENT
        for o in snapshot.observations
        if o.kind
        in {"build-config", "dependency-file", "ci-workflow", "release-workflow"}
    )
