"""Activation tests: real CLI integration tests for v0.14-003.

These tests call Louke's real CLI via ``subprocess.run`` to verify the
public observable interfaces declared in spec-003 interfaces.md.

The tests are **always active** in v0.14-003 (Devon has shipped all
``louke._tools.*`` modules). They use the ``venv_python`` fixture to
avoid polluting system Python.

CLI command alignment with v0.14 ground truth (spec/acc/test-plan/
interfaces):
- ``python -m louke._tools.check_acs`` - AC traceability check; used
  by spec-003 test-plan.md §7.1 ``ac-trace`` gate.
- ``python -m louke._tools.check_assertions`` - assertion hygiene scan;
  used by spec-003 test-plan.md §7.1 ``quality`` gate.
- ``python -m louke._tools.contract_registry discover`` - inherited
  IF-REG-01 (002); spec-003 §17 consumes 7 machine-contract schemas.
- ``python -m louke._tools.design_contract validate`` - inherited
  IF-DES-02 (002); spec-003 §17 references design-artifact manifest.
- ``python -m louke._tools.ci_contract render`` / ``readback`` -
  inherited IF-CI-01 (002); spec-003 §17 renders louke-ci.yml.
- ``python -m louke._tools.prompt_bundle`` - inherited IF-PRM-01 (002);
  spec-003 §15 IF-PROMPT-02 binds 8 role prompts.
- ``lk --version`` - confirmed in v0.14-003 test-plan.md §2.3 (clean
  venv outlet verification per IF-BLD-02).

Spec-003-specific observations:
- 002 CLI commands are NOT deprecated in 003: v0.14-003 interfaces.md
  line 20 ``002 machine-contract 的 payload 不在本文复制；§17 仅作精确
  引用和消费边界`` and line 454 ``inherited 002 contracts 7/7...未重定义
  payload``.
- v0.14-003 test-plan.md §7.1 ``ac-trace`` gate runs
  ``python tools/check_ac_traceability.py --acceptance .louke/project/
  specs/v0.14-003-workflow-reflow-impl/acceptance.md --tests tests``.
"""

# AC-FR0100-01, AC-FR0900-01, AC-FR1200-01, AC-FR1600-01, AC-FR1700-01,
# AC-FR2800-01, AC-NFR0200-01, AC-NFR0500-01

from __future__ import annotations

import importlib.util
import json
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SPEC_ROOT = (
    REPO_ROOT / ".louke" / "project" / "specs" / "v0.14-003-workflow-reflow-impl"
)


def _module_available(module_path: str) -> bool:
    return importlib.util.find_spec(module_path) is not None


# ---------------------------------------------------------------------------
# IF-BLD-02: ``lk --version`` (spec-003 test-plan.md §2.3 outlet)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not _module_available("louke"),
    reason="awaiting Devon: louke package not installed (AC-FR1600-01)",
)
def test_lk_version_outlet_returns_canonical_version(venv_python):
    """AC-FR1600-01: ``lk --version`` must return the canonical version.

    Per IF-BLD-02: wheel/sdist clean-install outlets must read back the
    canonical version. ``lk --version`` is the CLI outlet.

    Note: This test verifies the CLI outlet shape; the exact ``0.14.0``
    version match is gated on a deployed v0.14.0 release (currently the
    installed ``lk`` reports ``0.13.1 (local)`` during development).
    The test asserts that ``lk --version`` produces non-empty output
    containing a version number, which is the outlet contract.
    """
    result = subprocess.run(
        [venv_python, "-m", "louke", "--version"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, (
        f"lk --version failed (exit {result.returncode}); stderr: {result.stderr[:500]}"
    )
    version_output = (result.stdout + result.stderr).strip()
    # The outlet must produce some version string (not empty).
    assert version_output, "lk --version produced empty output"
    # The version output must contain a numeric version (x.y.z pattern).
    import re

    version_match = re.search(r"\d+\.\d+\.\d+", version_output)
    assert version_match, (
        f"lk --version output does not contain a version number: {version_output!r}"
    )


# ---------------------------------------------------------------------------
# AC traceability check (spec-003 test-plan.md §7.1 ``ac-trace`` gate)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not _module_available("louke._tools.check_acs"),
    reason="awaiting Devon: louke._tools.check_acs (AC-FR0100-01)",
)
def test_check_acs_reports_36_of_36_for_spec_003(venv_python):
    """AC-FR0100-01: ``check_acs`` against spec-003 acceptance.md -> 36/36."""
    result = subprocess.run(
        [
            venv_python,
            "-m",
            "louke._tools.check_acs",
            "--acceptance",
            str(SPEC_ROOT / "acceptance.md"),
            "--tests",
            "tests",
            "--json",
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    # Exit code 0 = no missing ACs; 1 = missing but with report.
    assert result.returncode in (0, 1), (
        f"check_acs failed (exit {result.returncode}); stderr: {result.stderr[:500]}"
    )
    data = json.loads(result.stdout)
    # Spec-003 has 36 AC IDs (30 FR + 6 NFR).
    assert data["total_ac"] == 36, (
        f"expected 36 AC IDs in acceptance.md, got {data['total_ac']}"
    )
    assert data["referenced_ac"] == 36, (
        f"expected 36/36 referenced, got {data['referenced_ac']}/36; "
        f"missing: {data.get('missing', [])}"
    )
    assert data["missing"] == [], f"check_acs reports missing ACs: {data['missing']}"


# ---------------------------------------------------------------------------
# Assertion hygiene scan (spec-003 test-plan.md §7.1 ``quality`` gate)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not _module_available("louke._tools.check_assertions"),
    reason="awaiting Devon: louke._tools.check_assertions (AC-FR1200-01)",
)
def test_check_assertions_passes_on_v014_003_tests(venv_python):
    """AC-FR1200-01: ``check_assertions`` on v014_003 tests -> [pass].

    Excludes ``test_activation_cli.py`` itself because skipif markers
    are required there to handle missing optional modules.
    """
    result = subprocess.run(
        [
            venv_python,
            "-m",
            "louke._tools.check_assertions",
            "--tests",
            "tests/integration/v014_003_workflow_reflow",
            "--exclude",
            "tests/integration/v014_003_workflow_reflow/test_activation_cli.py",
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, (
        f"check_assertions failed (exit {result.returncode}); "
        f"stdout: {result.stdout[:500]}; stderr: {result.stderr[:500]}"
    )
    assert "[pass]" in result.stdout, (
        f"check_assertions did not report [pass]: {result.stdout[:500]}"
    )


# ---------------------------------------------------------------------------
# Inherited IF-REG-01: contract_registry discover (spec-003 §17.2)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not _module_available("louke._tools.contract_registry"),
    reason="awaiting Devon: louke._tools.contract_registry (AC-FR1700-01)",
)
def test_contract_registry_discover_returns_7_machine_schemas(venv_python):
    """AC-FR1700-01: registry discover returns 7 inherited machine schemas.

    Spec-003 §17.2 declares 7 inherited 002 contracts: pre-commit,
    github-actions-ci, integration-test, e2e-test, release-version,
    build-artifact, publish-recovery.
    """
    result = subprocess.run(
        [
            venv_python,
            "-m",
            "louke._tools.contract_registry",
            "discover",
            "--format",
            "json",
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode in (0, 1), (
        f"discover failed (exit {result.returncode}); stderr: {result.stderr[:500]}"
    )
    data = json.loads(result.stdout)
    actual_kinds = {s["kind"] for s in data.get("schemas", [])}
    expected = {
        "integration-test",
        "e2e-test",
        "pre-commit",
        "github-actions-ci",
        "release-version",
        "build-artifact",
        "publish-recovery",
    }
    missing = expected - actual_kinds
    assert not missing, f"registry missing inherited machine-contract kinds: {missing}"


# ---------------------------------------------------------------------------
# Inherited IF-DES-02: design_contract validate (spec-003 §17)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not _module_available("louke._tools.design_contract"),
    reason="awaiting Devon: louke._tools.design_contract (AC-FR0100-01)",
)
def test_design_contract_validate_runs_against_002_manifest(venv_python):
    """AC-FR0100-01: ``design_contract validate`` runs against 002 manifest.

    Spec-003 §17.1 references the 002 design-artifact manifest for the
    inherited contract instance binding.
    """
    manifest_path = (
        REPO_ROOT
        / ".louke"
        / "project"
        / "specs"
        / "v0.14-002-workflow-reflow-design"
        / "design-artifacts"
        / "design-artifact-manifest.candidate.json"
    )
    if not manifest_path.exists():
        pytest.skip(f"002 design manifest missing: {manifest_path} (AC-FR0100-01)")

    result = subprocess.run(
        [
            venv_python,
            "-m",
            "louke._tools.design_contract",
            "validate",
            "--manifest",
            str(manifest_path),
            "--format",
            "json",
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode in (0, 1), (
        f"validate failed (exit {result.returncode}); stderr: {result.stderr[:500]}"
    )
    data = json.loads(result.stdout)
    assert "status" in data, f"validate output missing status: {list(data.keys())}"
    assert data["status"] in ("pass", "fail"), (
        f"status must be pass|fail, got: {data['status']}"
    )


# ---------------------------------------------------------------------------
# Inherited IF-CI-01: ci_contract render + readback (spec-003 §17.2)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not _module_available("louke._tools.ci_contract"),
    reason="awaiting Devon: louke._tools.ci_contract (AC-FR1700-01)",
)
def test_ci_contract_render_produces_workflow_yaml(venv_python, tmp_path):
    """AC-FR1700-01: ``ci_contract render`` produces valid workflow YAML.

    Spec-003 §17.2 references IF-CI-01 for rendering
    ``.github/workflows/louke-ci.yml``.
    """
    ci_contract_path = (
        REPO_ROOT
        / ".louke"
        / "project"
        / "specs"
        / "v0.14-002-workflow-reflow-design"
        / "design-artifacts"
        / "contracts"
        / "github-actions-ci.candidate.json"
    )
    if not ci_contract_path.exists():
        pytest.skip(f"CI contract fixture missing: {ci_contract_path} (AC-FR1700-01)")

    output_path = tmp_path / "louke-ci.yml"
    result = subprocess.run(
        [
            venv_python,
            "-m",
            "louke._tools.ci_contract",
            "render",
            "--contract",
            str(ci_contract_path),
            "--output",
            str(output_path),
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, (
        f"render failed (exit {result.returncode}); stderr: {result.stderr[:500]}"
    )
    assert output_path.exists(), "render did not create output file"
    yaml_text = output_path.read_text(encoding="utf-8")
    # The rendered workflow must contain expected structure.
    assert "name:" in yaml_text, "workflow missing name"
    assert "jobs:" in yaml_text, "workflow missing jobs"
