"""Integration tests for NFR-0500: Host project compatibility.

AC-NFR0500-01: At least two different tech-stack fixtures each complete
to candidate via their own project-local test/build/artifact/pre-commit/
CI contracts while preserving existing hooks/workflows/rules. The
execution path does NOT read Louke's own language/build config as host
default; unsupported adapters return a clear capability diagnostic.

Interfaces covered (per interfaces.md):
- IF-IMPL-01 (host adapter, ARC-02)
- IF-TEST-02 (test contract, ARC-08)
- IF-CI-02 (CI contract, ARC-11)
- IF-BLD-02 (build contract, ARC-12)
"""
# AC-NFR0500-01

from __future__ import annotations

import pytest

from louke.v014.nfr0500_host_compat import (
    ERROR_CODES,
    HostAdapter,
    HostCompatError,
    HostCompatReport,
    detect_adapter,
    preserve_existing_assets,
    validate_host_compat,
)


# ---------------------------------------------------------------------------
# detect_adapter
# ---------------------------------------------------------------------------


@pytest.mark.real_module
def test_detect_adapter_detects_python_from_pyproject_toml():
    """AC-NFR0500-01: pyproject.toml -> python adapter."""
    adapter = detect_adapter(stack_files=("pyproject.toml", "README.md"))
    assert isinstance(adapter, HostAdapter)
    assert adapter.stack_id == "python"
    assert "wheel" in adapter.artifact_kinds
    assert "sdist" in adapter.artifact_kinds


@pytest.mark.real_module
def test_detect_adapter_detects_python_from_setup_py():
    """AC-NFR0500-01: setup.py -> python adapter."""
    adapter = detect_adapter(stack_files=("setup.py",))
    assert adapter.stack_id == "python"


@pytest.mark.real_module
def test_detect_adapter_detects_node_from_package_json():
    """AC-NFR0500-01: package.json -> node adapter (heterogeneous stack)."""
    adapter = detect_adapter(stack_files=("package.json",))
    assert adapter.stack_id == "node"
    assert "tarball" in adapter.artifact_kinds


@pytest.mark.real_module
def test_detect_adapter_rejects_unsupported_stack():
    """AC-NFR0500-01: unknown stack -> HOST_UNSUPPORTED with clear diagnostic."""
    with pytest.raises(HostCompatError) as exc:
        detect_adapter(stack_files=("Cargo.toml",))  # Rust, unsupported
    assert exc.value.code == "HOST_UNSUPPORTED"
    assert "Cargo.toml" in str(exc.value) or "unsupported" in str(exc.value).lower()


# ---------------------------------------------------------------------------
# validate_host_compat
# ---------------------------------------------------------------------------


@pytest.mark.real_module
def test_validate_host_compat_passes_when_all_required_capabilities_present():
    """AC-NFR0500-01: adapter with test/build/artifact/pre-commit/ci -> pass."""
    adapter = detect_adapter(stack_files=("pyproject.toml",))
    report = validate_host_compat(adapter)
    assert isinstance(report, HostCompatReport)
    assert report.status == "pass"


@pytest.mark.real_module
def test_validate_host_compat_rejects_missing_capability():
    """AC-NFR0500-01: missing capability -> HOST_CAPABILITY_MISSING."""
    adapter = HostAdapter(
        stack_id="python",
        test_command="pytest",
        build_command="build",
        artifact_kinds=("wheel",),
        precommit_config_path=".pre-commit-config.yaml",
        ci_workflow_path=".github/workflows/ci.yml",
        capabilities=frozenset({"test", "build"}),  # missing artifact/pre-commit/ci
    )
    with pytest.raises(HostCompatError) as exc:
        validate_host_compat(adapter)
    assert exc.value.code == "HOST_CAPABILITY_MISSING"


# ---------------------------------------------------------------------------
# preserve_existing_assets
# ---------------------------------------------------------------------------


@pytest.mark.real_module
def test_preserve_existing_assets_preserves_hooks_workflows_rules():
    """AC-NFR0500-01: existing hooks/workflows/rules are preserved."""
    existing = {
        "hooks": [{"id": "user-hook-1"}],
        "workflows": [{"name": "user-ci.yml"}],
        "rules": [{"id": "user-rule-1"}],
    }
    runtime_additions = {
        "hooks": [{"id": "louke-rgr"}],
        "workflows": [{"name": "louke-ci.yml"}],
    }
    merged = preserve_existing_assets(existing, runtime_additions=runtime_additions)
    # Existing assets preserved.
    assert {"id": "user-hook-1"} in merged["hooks"]
    assert {"name": "user-ci.yml"} in merged["workflows"]
    assert {"id": "user-rule-1"} in merged["rules"]
    # Runtime additions added.
    assert {"id": "louke-rgr"} in merged["hooks"]
    assert {"name": "louke-ci.yml"} in merged["workflows"]


@pytest.mark.real_module
def test_preserve_existing_assets_does_not_duplicate_runtime_additions():
    """AC-NFR0500-01: existing categories get Runtime additions appended (not replaced)."""
    existing = {"hooks": [{"id": "user-hook-1"}]}
    runtime_additions = {"hooks": [{"id": "louke-rgr"}]}
    merged = preserve_existing_assets(existing, runtime_additions=runtime_additions)
    assert len(merged["hooks"]) == 2  # user + runtime, not replaced


# ---------------------------------------------------------------------------
# Host adapter command isolation (no Louke default leakage)
# ---------------------------------------------------------------------------


@pytest.mark.real_module
def test_python_adapter_test_command_does_not_hardcode_louke_paths():
    """AC-NFR0500-01: adapter commands must not hardcode Louke's own paths.

    The host adapter provides commands the host will run in its own
    context; the commands are generic (``pytest`` / ``build``) and
    reference the host's own venv, not Louke's repo paths.
    """
    adapter = detect_adapter(stack_files=("pyproject.toml",))
    # Commands should not reference Louke's own source tree.
    assert "louke/" not in adapter.test_command
    assert "louke/" not in adapter.build_command


@pytest.mark.real_module
def test_node_adapter_uses_npm_commands():
    """AC-NFR0500-01: Node adapter uses npm (not Python tools)."""
    adapter = detect_adapter(stack_files=("package.json",))
    assert "npm" in adapter.test_command
    assert "npm" in adapter.build_command


@pytest.mark.real_module
def test_error_codes_set_covers_all_documented_codes():
    """AC-NFR0500-01: ERROR_CODES includes all codes from interfaces.md."""
    expected = {"HOST_UNSUPPORTED", "HOST_CAPABILITY_MISSING", "HOST_DEFAULT_LEAKED"}
    actual = set(ERROR_CODES)
    missing = expected - actual
    assert not missing, f"ERROR_CODES missing: {missing}"
