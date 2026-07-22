"""AC-FR0900-01, AC-FR0800-01: project-runner foundation.

Devon 首个 foundation task（test-plan §2.3.1 + design-artifacts/runner/
project-runner.candidate.json）：扩展现有 ``tests/e2e/run_e2e.py`` 的 profile/
runtime parser、integration 发现顺序、design-contracts profile 路径，以及锁定的
``v014-runner-evidence.json`` schema 字段。断言只落在 runner 的公开解析/发现出口，
不接线真实收集（真实收集属 Shield 的 integration/e2e）。
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest


def _load_runner():
    """AC-FR0900-01: load the project runner harness from tests/e2e/run_e2e.py."""
    root = Path(__file__).resolve().parents[3]
    path = root / "tests" / "e2e" / "run_e2e.py"
    spec = importlib.util.spec_from_file_location("run_e2e_under_test", path)
    if spec is None or spec.loader is None:  # AC-FR0900-01: runner must be importable
        raise RuntimeError(f"cannot load runner: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


runner = _load_runner()


def test_v014_profile_is_exposed() -> None:
    """AC-FR0900-01: the v0.14 entry profile is part of the runner DAG."""
    parser = runner._parser()
    args = parser.parse_args(["e2e", "--profile", "v014", "--runtime", "local"])
    assert args.profile == "v014"
    assert runner._expand_profiles("all") == ["install", "chromium", "v014"]


def test_e2e_profile_choices_include_delivered_profiles() -> None:
    """AC-FR0900-01: --profile choices include v014."""
    parser = runner._parser()
    args = parser.parse_args(["e2e", "--profile", "install", "--runtime", "local"])
    assert args.profile == "install"


def test_all_profile_expands_to_delivered_profiles() -> None:
    """AC-FR0900-01: all expands exactly to install,chromium,v014."""
    assert runner._expand_profiles("all") == ["install", "chromium", "v014"]


def test_unknown_profile_exits_nonzero() -> None:
    """AC-FR0900-01: unknown profile -> argparse SystemExit (nonzero)."""
    parser = runner._parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["e2e", "--profile", "bogus", "--runtime", "local"])


def test_runtime_choices_unchanged() -> None:
    """AC-FR0900-01: --runtime choices stay local|global|both."""
    parser = runner._parser()
    for runtime in ("local", "global", "both"):
        args = parser.parse_args(["e2e", "--profile", "install", "--runtime", runtime])
        assert args.runtime == runtime


def test_integration_discovery_is_ordered() -> None:
    """AC-FR0800-01: integration discovery includes both v014 suites."""
    assert runner._integration_paths() == [
        "tests/integration/install_experience",
        "tests/integration/v014_design_contracts",
        "tests/integration/v014_workflow_reflow",
    ]


def test_install_profile_path() -> None:
    """AC-FR0900-01: install profile resolves to the install e2e directory."""
    paths, _selection = runner._profile_paths("install")
    assert paths == ["tests/e2e/install_experience"]


def test_v014_profile_path() -> None:
    """AC-FR0900-01: v014 resolves to the workflow reflow e2e directory."""
    paths, selection = runner._profile_paths("v014")
    assert paths == ["tests/e2e/v014_workflow_reflow"]
    assert selection == ["-m", "chromium_e2e"]


def test_server_contract_uses_product_interpreter_and_isolated_workspace(
    tmp_path: Path,
) -> None:
    """AC-NFR0300-01: Shield receives a product-only public server command."""
    product_python = tmp_path / "product" / "bin" / "python"
    workspace = tmp_path / "workspace"
    command = runner._server_command(product_python, workspace)
    assert command == [
        str(product_python),
        "-m",
        "louke",
        "serve",
        "--project-root",
        str(workspace),
        "--host",
        "127.0.0.1",
        "--opencode-backend",
        "mock",
    ]
    assert "lk" not in command


def test_wheel_path_rejects_ambiguous_product_artifacts(tmp_path: Path) -> None:
    """AC-NFR0300-03: product installation has exactly one wheel input."""
    wheelhouse = tmp_path / "wheelhouse"
    wheelhouse.mkdir()
    (wheelhouse / "louke-0.14.0-a.whl").write_bytes(b"a")
    (wheelhouse / "louke-0.14.0-b.whl").write_bytes(b"b")
    with pytest.raises(RuntimeError, match="exactly one"):
        runner._wheel_path(wheelhouse, "0.14.0")


def test_product_identity_accepts_symlinked_product_python(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC-NFR0300-03: venv Python symlinks must not invalidate product identity."""
    root = tmp_path / "repo"
    physical_case_root = tmp_path / "physical-case"
    case_root = tmp_path / "case"
    root.mkdir()
    physical_case_root.mkdir()
    case_root.symlink_to(physical_case_root, target_is_directory=True)
    product_root = case_root / "workspace" / ".venv"
    product_bin = product_root / "bin"
    product_bin.mkdir(parents=True)
    product_python = product_bin / "python"
    resolved_python = tmp_path / "shared" / "python"
    resolved_python.parent.mkdir()
    product_python.symlink_to(resolved_python)
    product_louke = (
        product_root / "lib" / "python3.14" / "site-packages" / "louke" / "__init__.py"
    )
    probe_cwd = case_root / "probe"
    probe_cwd.mkdir()

    monkeypatch.setattr(
        runner.subprocess,
        "run",
        lambda *args, **kwargs: type(
            "Completed",
            (),
            {
                "returncode": 0,
                "stdout": json.dumps(
                    {
                        "python": str(resolved_python),
                        "louke": str(product_louke.resolve()),
                        "version": "0.14.0",
                    }
                ),
                "stderr": "",
            },
        )(),
    )

    runner._verify_product_identity(
        product_python,
        "0.14.0",
        root,
        {"LOUKE_E2E_CASE_CWD": str(probe_cwd)},
    )


def test_evidence_schema_required_fields() -> None:
    """AC-FR0900-01: locked v014 runner evidence carries every required field."""
    required = {
        "schema_version",
        "release_identity",
        "spec_id",
        "base_commit",
        "runner_digest",
        "command",
        "profile",
        "runtime",
        "expected_node_ids",
        "collected_node_ids",
        "ac_layers",
        "suite_results",
        "service_lifecycle",
        "started_at",
        "finished_at",
        "exit_reason",
        "evidence_digest",
    }
    assert required == set(runner.EVIDENCE_REQUIRED_FIELDS)
