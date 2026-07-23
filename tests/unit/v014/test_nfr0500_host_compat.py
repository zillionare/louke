"""AC-NFR0500-01: Host project compatibility.

The implementation must support different languages, builders, test
frameworks and artifact types through 002 project-local contracts,
preserve existing hooks/workflows/rules, and use Archer's current design
for brand-new projects.  It must NOT hardcode Louke's own repo facts.
At least two distinct tech-stack fixtures must each complete to candidate
through their own project-local test/build/artifact/pre-commit/CI contracts
while preserving existing hooks/workflows/rules.  The execution path must
NOT read Louke's own language/build config as host default; unsupported
adapters must return a clear capability diagnostic.
"""

from __future__ import annotations


import pytest

from louke.runtime.host_compat import (
    HostAdapter,
    HostCompatError,
    detect_adapter,
    preserve_existing_assets,
    validate_host_compat,
)


def _python_adapter() -> HostAdapter:
    return HostAdapter(
        stack_id="python",
        test_command=".venv/bin/python3 -m pytest -q",
        build_command=".venv/bin/python3 -m build",
        artifact_kinds=("wheel", "sdist"),
        precommit_config_path=".pre-commit-config.yaml",
        ci_workflow_path=".github/workflows/louke-ci.yml",
        capabilities=frozenset({"test", "build", "artifact", "pre-commit", "ci"}),
    )


def _node_adapter() -> HostAdapter:
    return HostAdapter(
        stack_id="node",
        test_command="npm test",
        build_command="npm run build",
        artifact_kinds=("tarball",),
        precommit_config_path=".husky/pre-commit",
        ci_workflow_path=".github/workflows/louke-ci.yml",
        capabilities=frozenset({"test", "build", "artifact", "pre-commit", "ci"}),
    )


def test_detect_adapter_returns_python_for_python_stack() -> None:
    """AC-NFR0500-01: detect_adapter recognises a Python host project."""
    adapter = detect_adapter(stack_files=("pyproject.toml", "tests/"))
    assert adapter.stack_id == "python"


def test_detect_adapter_returns_node_for_node_stack() -> None:
    """AC-NFR0500-01: detect_adapter recognises a Node host project."""
    adapter = detect_adapter(stack_files=("package.json", "test/"))
    assert adapter.stack_id == "node"


def test_detect_adapter_returns_unsupported_diagnostic_for_unknown_stack() -> None:
    """AC-NFR0500-01: unknown stack returns clear unsupported diagnostic."""
    with pytest.raises(HostCompatError) as exc:
        detect_adapter(
            stack_files=("Cargo.toml",)
        )  # Rust - not supported in this fixture
    assert exc.value.code == "HOST_UNSUPPORTED"
    assert (
        "Rust" in exc.value.message
        or "rust" in exc.value.message.lower()
        or "unsupported" in exc.value.message.lower()
    )


def test_validate_host_compat_passes_for_python_stack() -> None:
    """AC-NFR0500-01: Python host with all capabilities completes to candidate."""
    report = validate_host_compat(_python_adapter())
    assert report.status == "pass"


def test_validate_host_compat_passes_for_node_stack() -> None:
    """AC-NFR0500-01: Node host with all capabilities completes to candidate."""
    report = validate_host_compat(_node_adapter())
    assert report.status == "pass"


def test_validate_host_compat_fails_when_capability_missing() -> None:
    """AC-NFR0500-01: missing capability produces a fail-closed diagnostic."""
    bad = _python_adapter()
    bad_missing = HostAdapter(
        stack_id=bad.stack_id,
        test_command=bad.test_command,
        build_command=bad.build_command,
        artifact_kinds=bad.artifact_kinds,
        precommit_config_path=bad.precommit_config_path,
        ci_workflow_path=bad.ci_workflow_path,
        capabilities=frozenset({"test"}),  # missing build, artifact, etc.
    )
    with pytest.raises(HostCompatError) as exc:
        validate_host_compat(bad_missing)
    assert exc.value.code == "HOST_CAPABILITY_MISSING"


def test_preserve_existing_assets_keeps_user_hooks_and_workflows() -> None:
    """AC-NFR0500-01: existing hooks/workflows/rules are preserved."""
    existing = {
        "hooks": [{"id": "user-hook-1"}],
        "workflows": [{"path": ".github/workflows/user-ci.yml"}],
        "rules": [{"id": "user-rule-1"}],
    }
    preserved = preserve_existing_assets(
        existing,
        runtime_additions={"hooks": [{"id": "louke-fast-quality"}]},
    )
    preserved_hook_ids = {h["id"] for h in preserved["hooks"]}
    assert "user-hook-1" in preserved_hook_ids
    assert "louke-fast-quality" in preserved_hook_ids
    preserved_workflow_paths = {w["path"] for w in preserved["workflows"]}
    assert ".github/workflows/user-ci.yml" in preserved_workflow_paths


def test_adapter_does_not_read_louke_defaults_for_host() -> None:
    """AC-NFR0500-01: host adapter does NOT default to Louke Python facts."""
    adapter = detect_adapter(stack_files=("package.json", "test/"))
    # Adapter must NOT default to .venv/bin/python3 when the host is Node.
    assert "python" not in adapter.test_command
    assert "npm" in adapter.test_command


def test_adapter_capability_diagnostic_for_unsupported_feature() -> None:
    """AC-NFR0500-01: unsupported adapter feature returns clear diagnostic."""
    adapter = _python_adapter()
    with pytest.raises(HostCompatError) as exc:
        adapter.require_capability("deploy-kubernetes")  # not in capabilities
    assert exc.value.code == "HOST_CAPABILITY_MISSING"
