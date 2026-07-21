"""AC-FR0800-01, AC-FR0900-01: project.toml foundation identity for v0.14-002.

The runner/project foundation (test-plan §2.3.1 + design-artifacts/runner/
project-runner.candidate.json ``project_toml_target``) pins the active project
identity to the v0.14.0 release and appends the v014 integration/e2e discovery
paths.  Pure TOML readback — no Runtime wiring.
"""

from __future__ import annotations

from pathlib import Path
import tomllib
from typing import Any


def _project_toml() -> dict[str, Any]:
    root = Path(__file__).resolve().parents[3]
    with (root / ".louke" / "project" / "project.toml").open("rb") as stream:
        return tomllib.load(stream)


def test_project_identity_targets_v014_002() -> None:
    """AC-FR0800-01: active identity is the v0.14.0 / v0.14-002 release."""
    project = _project_toml()["project"]
    assert project["version"] == "0.14.0"
    assert project["spec_id"] == "v0.14-002-workflow-reflow-design"
    assert project["release_branch"] == "releases/0.14.0"


def test_integration_paths_append_v014_suite() -> None:
    """AC-FR0800-01: integration discovery paths append the v014 suite."""
    paths = _project_toml()["integration"]["paths"]
    assert "tests/integration/v014_design_contracts" in paths


def test_e2e_paths_append_v014_suite() -> None:
    """AC-FR0900-01: e2e discovery paths append the v014 suite."""
    paths = _project_toml()["e2e"]["paths"]
    assert "tests/e2e/v014_design_contracts" in paths
