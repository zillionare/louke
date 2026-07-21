"""Host-project integration tests for v0.14-002.

These tests run Louke's CLI tools against a **synthetic host project**
(``tests/fixtures/v014_design_contracts/synthetic-host/``) that has its
own ``.louke/project/specs/synthetic-001-demo/`` directory with spec
documents, design artifacts, and contract instances.

Key difference from ``test_activation_cli.py``:
- Activation tests run CLI in the **Louke repo** (self-dogfood)
- Host integration tests run CLI in the **synthetic host project** (cwd=synthetic-host)

This validates that Louke's tools work correctly when invoked in a host
project context — reading the host project's own spec documents, not
Louke's own ``.louke/`` directory.

Virtual environment policy:
- All subprocess calls use the ``venv_python`` fixture (provided by
  conftest.py) instead of ``sys.executable``. This skips the test if
  pytest is not running inside a venv, preventing accidental pollution
  of system Python. See conftest.py::venv_python for details.

CLI command alignment with v0.14 ground truth (spec/acc/test-plan/interfaces):
- ``python -m louke._tools.design_contract validate`` — defined in
  v0.14-002 interfaces.md §IF-DES-02 line 27
- ``python -m louke._tools.contract_registry discover`` — defined in
  v0.14-002 interfaces.md §IF-REG-01 line 58
- 002 CLI commands are NOT deprecated in 003: v0.14-003 interfaces.md
  §17 "inherited 002 contracts 7/7...未重定义payload"

When Devon's implementation does not exist, all tests skip (dormant).
When Devon ships ``louke._tools.*``, these tests activate and call the
real CLI via ``subprocess.run(cwd=synthetic_host_dir)``.
"""

# AC-FR0400-01, AC-FR0600-01, AC-FR0700-01, AC-FR0900-01

from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURES_ROOT = REPO_ROOT / "tests" / "fixtures" / "v014_design_contracts"
SYNTHETIC_HOST = FIXTURES_ROOT / "synthetic-host"
SYNTHETIC_SPEC = (
    SYNTHETIC_HOST
    / ".louke"
    / "project"
    / "specs"
    / "synthetic-001-demo"
)
SYNTHETIC_MANIFEST = (
    SYNTHETIC_SPEC
    / "design-artifacts"
    / "design-artifact-manifest.candidate.json"
)


def _module_available(module_path: str) -> bool:
    """Check if a module is importable without actually importing it."""
    return importlib.util.find_spec(module_path) is not None


# Skip entire module if no v0.14-002 tools exist yet.
_V014_TOOLS = [
    "louke._tools.design_contract",
    "louke._tools.contract_registry",
]

pytestmark = pytest.mark.skipif(
    not any(_module_available(m) for m in _V014_TOOLS),
    reason="No v0.14-002 louke._tools.* modules implemented yet; "
    "all host integration tests are dormant",
)


@pytest.fixture
def synthetic_host_dir(tmp_path):
    """Copy the synthetic host project to a temp dir for isolation.

    This ensures tests can modify files (e.g., tamper with digests)
    without affecting the committed fixture.
    """
    dest = tmp_path / "synthetic-host"
    shutil.copytree(SYNTHETIC_HOST, dest)
    return dest


@pytest.fixture
def synthetic_manifest_path(synthetic_host_dir):
    """Path to the manifest in the copied synthetic host project."""
    return (
        synthetic_host_dir
        / ".louke"
        / "project"
        / "specs"
        / "synthetic-001-demo"
        / "design-artifacts"
        / "design-artifact-manifest.candidate.json"
    )


# ---------------------------------------------------------------------------
# IF-DES-02: design_contract validate (in host project context)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(
    not _module_available("louke._tools.design_contract"),
    reason="awaiting Devon: louke._tools.design_contract",
)
def test_host_validate_runs_in_synthetic_project(venv_python, synthetic_host_dir, synthetic_manifest_path):
    """IF-DES-02: ``design_contract validate`` must run in the host project.

    The CLI must read the host project's own ``.louke/`` directory —
    not Louke's repo. This is the core host-project integration test.
    """
    result = subprocess.run(
        [
            venv_python, "-m", "louke._tools.design_contract",
            "validate",
            "--manifest", str(synthetic_manifest_path),
            "--format", "json",
        ],
        capture_output=True,
        text=True,
        timeout=30,
        cwd=str(synthetic_host_dir),
    )
    # The validator may pass or fail (candidate state → SCHEMA_NOT_ACTIVE),
    # but it must produce valid JSON with the contract-defined shape.
    assert result.returncode in (0, 1), (
        f"unexpected exit code {result.returncode}; "
        f"stderr: {result.stderr[:500]}"
    )
    data = json.loads(result.stdout)
    assert "status" in data, (
        f"output missing 'status': {list(data.keys())}"
    )
    assert data["status"] in ("pass", "fail"), (
        f"status must be pass|fail, got: {data['status']}"
    )


@pytest.mark.skipif(
    not _module_available("louke._tools.design_contract"),
    reason="awaiting Devon: louke._tools.design_contract",
)
def test_host_validate_detects_tampered_digest(venv_python, synthetic_host_dir, synthetic_manifest_path):
    """IF-DES-02: validator must detect when a file's digest doesn't match.

    Tamper with acceptance.md, then run validate. The validator must
    report a digest mismatch failure.
    """
    # Tamper with acceptance.md (change content without updating manifest digest)
    acceptance_path = (
        synthetic_host_dir
        / ".louke"
        / "project"
        / "specs"
        / "synthetic-001-demo"
        / "acceptance.md"
    )
    original = acceptance_path.read_text(encoding="utf-8")
    acceptance_path.write_text(original + "\n<!-- tampered -->", encoding="utf-8")

    result = subprocess.run(
        [
            venv_python, "-m", "louke._tools.design_contract",
            "validate",
            "--manifest", str(synthetic_manifest_path),
            "--format", "json",
        ],
        capture_output=True,
        text=True,
        timeout=30,
        cwd=str(synthetic_host_dir),
    )
    data = json.loads(result.stdout)
    assert data["status"] == "fail", (
        f"validator must fail when digest is tampered; got: {data['status']}"
    )
    # At least one check must report the digest mismatch
    check_ids = {c.get("check_id", "") for c in data.get("checks", [])}
    assert any("DIGEST" in cid or "digest" in cid.lower() for cid in check_ids), (
        f"no digest-related check failed: {check_ids}"
    )


@pytest.mark.skipif(
    not _module_available("louke._tools.design_contract"),
    reason="awaiting Devon: louke._tools.design_contract",
)
def test_host_validate_reports_candidate_state(venv_python, synthetic_host_dir, synthetic_manifest_path):
    """IF-DES-02: validator must report SCHEMA_NOT_ACTIVE for candidate registry.

    The synthetic host's registry has ``activation_state=candidate``.
    The validator must fail-closed with SCHEMA_NOT_ACTIVE (not pass).
    """
    result = subprocess.run(
        [
            venv_python, "-m", "louke._tools.design_contract",
            "validate",
            "--manifest", str(synthetic_manifest_path),
            "--format", "json",
        ],
        capture_output=True,
        text=True,
        timeout=30,
        cwd=str(synthetic_host_dir),
    )
    data = json.loads(result.stdout)
    # Candidate state → must fail-closed
    assert data["status"] == "fail", (
        f"candidate registry must fail-closed; got: {data['status']}"
    )
    # Must include DESIGN.SCHEMA.ACTIVE check
    check_ids = {c.get("check_id", "") for c in data.get("checks", [])}
    assert "DESIGN.SCHEMA.ACTIVE" in check_ids, (
        f"missing DESIGN.SCHEMA.ACTIVE check: {check_ids}"
    )


@pytest.mark.skipif(
    not _module_available("louke._tools.design_contract"),
    reason="awaiting Devon: louke._tools.design_contract",
)
def test_host_validate_checks_ac_closure(venv_python, synthetic_host_dir, synthetic_manifest_path):
    """IF-DES-02: validator must verify AC closure in the host project.

    The synthetic host has 3 ACs (AC-FR0100-01, AC-FR0200-01, AC-NFR0100-01).
    The validator must check that all 3 are covered in ac_closure.
    """
    result = subprocess.run(
        [
            venv_python, "-m", "louke._tools.design_contract",
            "validate",
            "--manifest", str(synthetic_manifest_path),
            "--format", "json",
        ],
        capture_output=True,
        text=True,
        timeout=30,
        cwd=str(synthetic_host_dir),
    )
    data = json.loads(result.stdout)
    check_ids = {c.get("check_id", "") for c in data.get("checks", [])}
    assert "DESIGN.TRACE.CLOSURE" in check_ids, (
        f"missing DESIGN.TRACE.CLOSURE check: {check_ids}"
    )


# ---------------------------------------------------------------------------
# IF-REG-01: contract_registry discover (in host project context)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(
    not _module_available("louke._tools.contract_registry"),
    reason="awaiting Devon: louke._tools.contract_registry",
)
def test_host_registry_discover_in_synthetic_project(venv_python, synthetic_host_dir):
    """IF-REG-01: ``contract_registry discover`` must run in host project.

    The registry must discover the host project's own schemas (2 in
    synthetic-001-demo), not Louke's own schemas (7 in v0.14-002).
    """
    result = subprocess.run(
        [
            venv_python, "-m", "louke._tools.contract_registry",
            "discover",
            "--format", "json",
        ],
        capture_output=True,
        text=True,
        timeout=30,
        cwd=str(synthetic_host_dir),
    )
    assert result.returncode in (0, 1), (
        f"unexpected exit code {result.returncode}; "
        f"stderr: {result.stderr[:500]}"
    )
    data = json.loads(result.stdout)
    assert "registry_version" in data, (
        f"output missing registry_version: {list(data.keys())}"
    )
    assert "schemas" in data, "output missing schemas"
    assert isinstance(data["schemas"], list), "schemas must be a list"
    # Synthetic host has 2 schemas (integration-test + e2e-test)
    # NOT Louke's 7 schemas — this proves the CLI reads the host project's registry
    actual_kinds = {s["kind"] for s in data["schemas"]}
    assert "integration-test" in actual_kinds, (
        f"missing integration-test schema: {actual_kinds}"
    )
    assert "e2e-test" in actual_kinds, (
        f"missing e2e-test schema: {actual_kinds}"
    )


@pytest.mark.skipif(
    not _module_available("louke._tools.contract_registry"),
    reason="awaiting Devon: louke._tools.contract_registry",
)
def test_host_registry_reports_candidate_status(venv_python, synthetic_host_dir):
    """IF-REG-01: registry must report ``status=candidate`` for synthetic host.

    The synthetic host's registry has ``activation_state=candidate``.
    All schemas must have ``status=candidate`` (not ``active``).
    """
    result = subprocess.run(
        [
            venv_python, "-m", "louke._tools.contract_registry",
            "discover",
            "--format", "json",
        ],
        capture_output=True,
        text=True,
        timeout=30,
        cwd=str(synthetic_host_dir),
    )
    data = json.loads(result.stdout)
    for schema in data["schemas"]:
        assert schema["status"] == "candidate", (
            f"schema {schema.get('identity')} must be candidate, "
            f"got: {schema['status']}"
        )


@pytest.mark.skipif(
    not _module_available("louke._tools.contract_registry"),
    reason="awaiting Devon: louke._tools.contract_registry",
)
def test_host_registry_does_not_leak_louke_own_schemas(venv_python, synthetic_host_dir):
    """IF-REG-01: host project registry must NOT contain Louke's own schemas.

    This is the key isolation test: the synthetic host has 2 schemas
    (integration-test, e2e-test). If the CLI reads Louke's own registry
    instead of the host project's, it would find 7 schemas. This test
    catches that regression.
    """
    result = subprocess.run(
        [
            venv_python, "-m", "louke._tools.contract_registry",
            "discover",
            "--format", "json",
        ],
        capture_output=True,
        text=True,
        timeout=30,
        cwd=str(synthetic_host_dir),
    )
    data = json.loads(result.stdout)
    actual_kinds = {s["kind"] for s in data["schemas"]}
    # Synthetic host has only 2 kinds; Louke's own repo has 7
    forbidden_kinds = {
        "pre-commit",
        "github-actions-ci",
        "release-version",
        "build-artifact",
        "publish-recovery",
    }
    leaked = actual_kinds & forbidden_kinds
    assert not leaked, (
        f"registry leaked Louke's own schemas into host project: {leaked}; "
        f"actual kinds: {actual_kinds}"
    )
