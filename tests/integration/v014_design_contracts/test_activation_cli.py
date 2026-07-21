"""Activation tests: real CLI integration tests for v0.14-002.

These tests are **dormant** when Devon's implementation does not exist.
They activate automatically when ``louke._tools.*`` modules become
importable, testing the real CLI interface defined in ``interfaces.md``.

How it works:
- ``_module_available(path)`` checks ``importlib.util.find_spec``.
- If the module is NOT available → ``pytest.skip`` (dormant).
- If the module IS available → run the real CLI via ``subprocess.run``
  and assert the output matches the contract in ``interfaces.md``.

This file does NOT use MagicMock. It is the real integration test that
replaces the 125 ``awaiting_devon`` mock tests when Devon ships code.

Interfaces covered (per interfaces.md):
- IF-DES-02: ``python -m louke._tools.design_contract validate``
- IF-REG-01: ``python -m louke._tools.contract_registry discover``
- IF-CI-01: ``python -m louke._tools.ci_contract render`` / ``readback``
- IF-WEB-01: ``lk web`` + ``GET /health`` (HTTP, not CLI)
"""

# AC-FR0400-01, AC-FR0600-01, AC-FR0700-01, AC-FR0900-01, AC-FR1100-01

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SPEC_ROOT = (
    REPO_ROOT
    / ".louke"
    / "project"
    / "specs"
    / "v0.14-002-workflow-reflow-design"
)
DESIGN_ARTIFACTS = SPEC_ROOT / "design-artifacts"
MANIFEST_PATH = DESIGN_ARTIFACTS / "design-artifact-manifest.candidate.json"


def _module_available(module_path: str) -> bool:
    """Check if a module is importable without actually importing it."""
    return importlib.util.find_spec(module_path) is not None


# Skip the entire module if NONE of the v0.14-002 tools exist yet.
# Individual tests still skip per-module, but this gives a fast-path
# when everything is still awaiting Devon.
_V014_TOOLS = [
    "louke._tools.design_contract",
    "louke._tools.contract_registry",
    "louke._tools.ci_contract",
    "louke._tools.workbench",
]

pytestmark = pytest.mark.skipif(
    not any(_module_available(m) for m in _V014_TOOLS),
    reason="No v0.14-002 louke._tools.* modules implemented yet; "
    "all activation tests are dormant",
)


# ---------------------------------------------------------------------------
# IF-DES-02: design_contract validate
# ---------------------------------------------------------------------------

@pytest.mark.skipif(
    not _module_available("louke._tools.design_contract"),
    reason="awaiting Devon: louke._tools.design_contract",
)
def test_design_contract_validate_real_cli():
    """IF-DES-02: ``python -m louke._tools.design_contract validate``.

    When Devon ships the real module, this test calls the actual CLI
    with the candidate manifest and asserts the contract-defined output
    shape: ``{status, revision_id, checks[], evidence_digest}``.
    """
    result = subprocess.run(
        [
            sys.executable, "-m", "louke._tools.design_contract",
            "validate",
            "--manifest", str(MANIFEST_PATH),
            "--format", "json",
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    # The validator may return pass or fail depending on candidate state,
    # but it must produce valid JSON on stdout with the contract shape.
    assert result.returncode in (0, 1), (
        f"unexpected exit code {result.returncode}; "
        f"stderr: {result.stderr[:500]}"
    )
    data = json.loads(result.stdout)
    assert "status" in data, f"output missing 'status': {list(data.keys())}"
    assert data["status"] in ("pass", "fail"), (
        f"status must be pass|fail, got: {data['status']}"
    )
    assert "checks" in data, "output missing 'checks'"
    assert isinstance(data["checks"], list), "'checks' must be a list"
    # Each check must have the contract-defined fields (interfaces.md line 28)
    if data["checks"]:
        check = data["checks"][0]
        assert "check_id" in check, f"check missing check_id: {check}"
        assert "status" in check, f"check missing status: {check}"


@pytest.mark.skipif(
    not _module_available("louke._tools.design_contract"),
    reason="awaiting Devon: louke._tools.design_contract",
)
def test_design_contract_validate_has_stable_check_ids():
    """IF-DES-02: validator output must include stable check IDs.

    Per interfaces.md: at least DESIGN.TRACE.CLOSURE,
    DESIGN.INTERFACE.RESOLUTION, DESIGN.ARCH.CARRIER, etc.
    """
    result = subprocess.run(
        [
            sys.executable, "-m", "louke._tools.design_contract",
            "validate",
            "--manifest", str(MANIFEST_PATH),
            "--format", "json",
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    data = json.loads(result.stdout)
    check_ids = {c["check_id"] for c in data.get("checks", [])}
    required_ids = {
        "DESIGN.TRACE.CLOSURE",
        "DESIGN.INTERFACE.RESOLUTION",
        "DESIGN.ARCH.CARRIER",
        "DESIGN.CONTRACT.PARITY",
        "DESIGN.SCHEMA.ACTIVE",
        "DESIGN.PROMPT.PARITY",
        "DESIGN.SECRET",
    }
    missing = required_ids - check_ids
    assert not missing, (
        f"validator missing stable check IDs: {missing}"
    )


# ---------------------------------------------------------------------------
# IF-REG-01: contract_registry discover
# ---------------------------------------------------------------------------

@pytest.mark.skipif(
    not _module_available("louke._tools.contract_registry"),
    reason="awaiting Devon: louke._tools.contract_registry",
)
def test_contract_registry_discover_real_cli():
    """IF-REG-01: ``python -m louke._tools.contract_registry discover``.

    When Devon ships the real module, this test calls discover and
    asserts the output shape: ``{registry_version, registry_digest,
    schemas[]}`` with each schema having identity/kind/version/digest/status.
    """
    result = subprocess.run(
        [
            sys.executable, "-m", "louke._tools.contract_registry",
            "discover",
            "--format", "json",
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode in (0, 1), (
        f"unexpected exit code {result.returncode}; "
        f"stderr: {result.stderr[:500]}"
    )
    data = json.loads(result.stdout)
    assert "registry_version" in data, (
        f"output missing registry_version: {list(data.keys())}"
    )
    assert "registry_digest" in data, "output missing registry_digest"
    assert "schemas" in data, "output missing schemas"
    assert isinstance(data["schemas"], list), "schemas must be a list"

    # Each schema must have the contract-defined fields
    if data["schemas"]:
        schema = data["schemas"][0]
        for field in ("identity", "kind", "version", "digest", "status"):
            assert field in schema, f"schema missing {field}: {schema}"
        assert schema["status"] in ("active", "candidate", "retired"), (
            f"invalid status: {schema['status']}"
        )


@pytest.mark.skipif(
    not _module_available("louke._tools.contract_registry"),
    reason="awaiting Devon: louke._tools.contract_registry",
)
def test_contract_registry_discover_returns_7_machine_schemas():
    """IF-REG-01: discover must list 7 machine-contract schemas."""
    result = subprocess.run(
        [
            sys.executable, "-m", "louke._tools.contract_registry",
            "discover",
            "--format", "json",
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    data = json.loads(result.stdout)
    machine_kinds = {
        "integration-test",
        "e2e-test",
        "pre-commit",
        "github-actions-ci",
        "release-version",
        "build-artifact",
        "publish-recovery",
    }
    actual_kinds = {s["kind"] for s in data["schemas"]}
    missing = machine_kinds - actual_kinds
    assert not missing, f"registry missing machine schema kinds: {missing}"


# ---------------------------------------------------------------------------
# IF-CI-01: ci_contract render + readback
# ---------------------------------------------------------------------------

@pytest.mark.skipif(
    not _module_available("louke._tools.ci_contract"),
    reason="awaiting Devon: louke._tools.ci_contract",
)
def test_ci_contract_render_real_cli(tmp_path):
    """IF-CI-01: ``python -m louke._tools.ci_contract render``.

    Render the candidate CI contract to a temporary workflow file and
    assert the output is valid YAML with expected structure.
    """
    ci_contract_path = DESIGN_ARTIFACTS / "contracts" / "github-actions-ci.candidate.json"
    if not ci_contract_path.exists():
        pytest.skip(f"CI contract fixture missing: {ci_contract_path}")

    output_path = tmp_path / "louke-ci.yml"
    result = subprocess.run(
        [
            sys.executable, "-m", "louke._tools.ci_contract",
            "render",
            "--contract", str(ci_contract_path),
            "--output", str(output_path),
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, (
        f"render failed (exit {result.returncode}); "
        f"stderr: {result.stderr[:500]}"
    )
    assert output_path.exists(), "render did not create output file"

    # The rendered YAML must be valid and contain expected workflow structure
    yaml_text = output_path.read_text(encoding="utf-8")
    assert "name:" in yaml_text, "workflow missing name"
    assert "on:" in yaml_text or "true:" in yaml_text, "workflow missing trigger"
    assert "jobs:" in yaml_text, "workflow missing jobs"


@pytest.mark.skipif(
    not _module_available("louke._tools.ci_contract"),
    reason="awaiting Devon: louke._tools.ci_contract",
)
def test_ci_contract_readback_real_cli(tmp_path):
    """IF-CI-01: ``python -m louke._tools.ci_contract readback``.

    After render, readback must return ``{status, contract_digest,
    workflow_digest, checks, commands}`` with status in
    in_sync|missing|invalid|drifted|conflict.
    """
    ci_contract_path = DESIGN_ARTIFACTS / "contracts" / "github-actions-ci.candidate.json"
    if not ci_contract_path.exists():
        pytest.skip(f"CI contract fixture missing: {ci_contract_path}")

    output_path = tmp_path / "louke-ci.yml"
    # First render
    subprocess.run(
        [
            sys.executable, "-m", "louke._tools.ci_contract",
            "render",
            "--contract", str(ci_contract_path),
            "--output", str(output_path),
        ],
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    )
    # Then readback
    result = subprocess.run(
        [
            sys.executable, "-m", "louke._tools.ci_contract",
            "readback",
            "--contract", str(ci_contract_path),
            "--workflow", str(output_path),
            "--format", "json",
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, (
        f"readback failed (exit {result.returncode}); "
        f"stderr: {result.stderr[:500]}"
    )
    data = json.loads(result.stdout)
    assert "status" in data, f"readback missing status: {list(data.keys())}"
    assert data["status"] in (
        "in_sync", "missing", "invalid", "drifted", "conflict"
    ), f"invalid readback status: {data['status']}"
    assert "contract_digest" in data, "readback missing contract_digest"
    assert "workflow_digest" in data, "readback missing workflow_digest"


# ---------------------------------------------------------------------------
# IF-WEB-01: lk web + GET /health (HTTP, not CLI)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(
    not _module_available("louke._tools.workbench"),
    reason="awaiting Devon: louke._tools.workbench",
)
def test_workbench_health_endpoint_real():
    """IF-WEB-01: ``lk web`` server must respond to ``GET /health``.

    Per interfaces.md: ``GET /health`` returns HTTP 200 with expected
    version. This test starts the server, polls /health, and tears down.
    """
    import socket
    import time
    import urllib.request

    # Find a free port
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]

    proc = subprocess.Popen(
        [
            sys.executable, "-m", "louke",
            "web", "--host", "127.0.0.1", "--port", str(port),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    try:
        # Poll /health for up to 10 seconds
        deadline = time.time() + 10
        last_error = None
        while time.time() < deadline:
            try:
                resp = urllib.request.urlopen(
                    f"http://127.0.0.1:{port}/health", timeout=2
                )
                assert resp.status == 200, (
                    f"/health returned {resp.status}"
                )
                body = json.loads(resp.read().decode("utf-8"))
                assert "version" in body, (
                    f"/health missing version: {body}"
                )
                return  # success
            except Exception as exc:
                last_error = exc
                time.sleep(0.5)

        pytest.fail(
            f"lk web did not respond to /health within 10s; "
            f"last error: {last_error}"
        )
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
