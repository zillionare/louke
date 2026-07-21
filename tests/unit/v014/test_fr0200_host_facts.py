"""AC-FR0200-01: host project facts inventory & autonomous tech selection.

FR-0200 requires Runtime to provide Archer with the actual host project
language/runtime/build/test/version-source/artifact/outlet/CI/hooks inventory,
and Archer must produce a complete technical plan based on real facts (never
inventing absent paths, never defaulting to the Louke repo's own stack).
The host facts inventory adapter emits a typed snapshot per IF-FCT-01.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from louke.v014.fr0200_host_facts import (
    FactsError,
    HostFactsSnapshot,
    Observation,
    ObservationStatus,
    collect_host_facts,
    is_empty_project,
)

_ROOT = Path(__file__).resolve().parents[3]
_SPEC_ROOT = _ROOT / ".louke" / "project" / "specs" / "v0.14-002-workflow-reflow-design"


def _make_workspace(tmp_path: Path) -> Path:
    """Materialise a minimal Python host workspace."""
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname = "demo"\nversion = "0.1.0"\n', encoding="utf-8"
    )
    (tmp_path / ".pre-commit-config.yaml").write_text("repos: []\n", encoding="utf-8")
    (tmp_path / ".github" / "workflows").mkdir(parents=True)
    (tmp_path / ".github" / "workflows" / "ci.yml").write_text(
        "name: ci\n", encoding="utf-8"
    )
    return tmp_path


def test_collect_host_facts_returns_typed_snapshot(tmp_path: Path) -> None:
    """AC-FR0200-01: collection returns a typed snapshot per IF-FCT-01."""
    workspace = _make_workspace(tmp_path)
    snapshot = collect_host_facts(
        workspace_id="github.com/example/demo",
        base_commit="a" * 40,
        workspace_root=workspace,
    )
    assert isinstance(snapshot, HostFactsSnapshot)
    assert snapshot.workspace_id == "github.com/example/demo"
    assert snapshot.base_commit == "a" * 40
    assert snapshot.snapshot_digest.startswith("sha256:")
    assert "Python" in snapshot.inventory["languages"]


def test_collect_host_facts_records_present_observation_with_digest(
    tmp_path: Path,
) -> None:
    """AC-FR0200-01: a present file yields a present observation with digest."""
    workspace = _make_workspace(tmp_path)
    snapshot = collect_host_facts(
        workspace_id="github.com/example/demo",
        base_commit="a" * 40,
        workspace_root=workspace,
    )
    build_config = next(o for o in snapshot.observations if o.kind == "build-config")
    assert build_config.status is ObservationStatus.PRESENT
    assert build_config.path == "pyproject.toml"
    assert build_config.digest and build_config.digest.startswith("sha256:")


def test_collect_host_facts_records_absent_observation_without_digest(
    tmp_path: Path,
) -> None:
    """AC-FR0200-01: a missing file is recorded as absent (a fact, not invented)."""
    workspace = _make_workspace(tmp_path)
    snapshot = collect_host_facts(
        workspace_id="github.com/example/demo",
        base_commit="a" * 40,
        workspace_root=workspace,
    )
    managed_ci = next(o for o in snapshot.observations if o.kind == "managed-ci")
    assert managed_ci.status is ObservationStatus.ABSENT
    assert managed_ci.digest is None


def test_collect_host_facts_records_unsupported_outlet(tmp_path: Path) -> None:
    """AC-FR0200-01: an unsupported capability is recorded as ``unsupported``."""
    workspace = _make_workspace(tmp_path)
    snapshot = collect_host_facts(
        workspace_id="github.com/example/demo",
        base_commit="a" * 40,
        workspace_root=workspace,
    )
    deployment = next(o for o in snapshot.observations if o.kind == "deployment-outlet")
    assert deployment.status is ObservationStatus.UNSUPPORTED


def test_empty_project_detection_yields_empty_inventory(tmp_path: Path) -> None:
    """AC-FR0200-01: an empty project produces an empty inventory, not Louke defaults."""
    snapshot = collect_host_facts(
        workspace_id="github.com/example/blank",
        base_commit="b" * 40,
        workspace_root=tmp_path,
    )
    assert is_empty_project(snapshot) is True
    assert snapshot.inventory["languages"] == []
    assert snapshot.inventory["build_entries"] == []
    # Critical: empty project must NOT default to Louke's own Python stack
    assert "Python" not in snapshot.inventory["languages"]
    assert "pyproject.toml" not in snapshot.inventory["dependency_files"]


def test_empty_project_observations_record_absent_files(tmp_path: Path) -> None:
    """AC-FR0200-01: absent paths are still facts, not invented defaults."""
    snapshot = collect_host_facts(
        workspace_id="github.com/example/blank",
        base_commit="b" * 40,
        workspace_root=tmp_path,
    )
    statuses = {o.kind: o.status for o in snapshot.observations}
    assert statuses["build-config"] is ObservationStatus.ABSENT
    assert statuses["pre-commit-config"] is ObservationStatus.ABSENT
    assert statuses["managed-ci"] is ObservationStatus.ABSENT


def test_collect_host_facts_does_not_invent_paths(tmp_path: Path) -> None:
    """AC-FR0200-01: paths come from the snapshot; absent paths are not invented."""
    workspace = _make_workspace(tmp_path)
    snapshot = collect_host_facts(
        workspace_id="github.com/example/demo",
        base_commit="a" * 40,
        workspace_root=workspace,
    )
    for observation in snapshot.observations:
        if observation.status is ObservationStatus.PRESENT:
            assert (workspace / observation.path).is_file() or observation.path == "N/A"


def test_collect_host_facts_rejects_path_escape(tmp_path: Path) -> None:
    """AC-FR0200-01: path escape outside the workspace is rejected."""
    workspace = _make_workspace(tmp_path)
    with pytest.raises(FactsError) as exc:
        collect_host_facts(
            workspace_id="github.com/example/demo",
            base_commit="a" * 40,
            workspace_root=workspace,
            extra_probe_paths=["../../etc/passwd"],
        )
    assert exc.value.code == "PROJECT_FACTS_PATH_ESCAPE"


def test_snapshot_is_deterministic(tmp_path: Path) -> None:
    """AC-FR0200-01: re-collecting the same workspace yields the same digest."""
    workspace = _make_workspace(tmp_path)
    first = collect_host_facts(
        workspace_id="github.com/example/demo",
        base_commit="a" * 40,
        workspace_root=workspace,
    )
    second = collect_host_facts(
        workspace_id="github.com/example/demo",
        base_commit="a" * 40,
        workspace_root=workspace,
    )
    assert first.snapshot_digest == second.snapshot_digest


def test_snapshot_to_json_round_trips(tmp_path: Path) -> None:
    """AC-FR0200-01: the snapshot serialises to JSON per IF-FCT-01 schema."""
    workspace = _make_workspace(tmp_path)
    snapshot = collect_host_facts(
        workspace_id="github.com/example/demo",
        base_commit="a" * 40,
        workspace_root=workspace,
    )
    payload = json.loads(snapshot.to_json())
    assert payload["workspace_id"] == "github.com/example/demo"
    assert payload["base_commit"] == "a" * 40
    assert payload["artifact_kind"] == "host-project-facts-snapshot"
    assert isinstance(payload["inventory"], dict)
    assert isinstance(payload["observations"], list)


def test_snapshot_drift_when_workspace_changes(tmp_path: Path) -> None:
    """AC-FR0200-01: a changed workspace produces a different snapshot digest."""
    workspace = _make_workspace(tmp_path)
    first = collect_host_facts(
        workspace_id="github.com/example/demo",
        base_commit="a" * 40,
        workspace_root=workspace,
    )
    (workspace / "pyproject.toml").write_text(
        '[project]\nname = "demo"\nversion = "0.2.0"\n', encoding="utf-8"
    )
    second = collect_host_facts(
        workspace_id="github.com/example/demo",
        base_commit="a" * 40,
        workspace_root=workspace,
    )
    assert first.snapshot_digest != second.snapshot_digest


def test_observation_immutable() -> None:
    """AC-FR0200-01: observation records are immutable value objects."""
    obs = Observation(
        kind="build-config",
        path="pyproject.toml",
        status=ObservationStatus.PRESENT,
        digest="sha256:" + "a" * 64,
        source="workspace bytes",
    )
    with pytest.raises(Exception):
        obs.kind = "tampered"  # type: ignore[misc]
