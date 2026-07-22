"""AC-FR0900-01, AC-FR0800-01: project-runner foundation.

Devon 首个 foundation task（test-plan §2.3.1 + design-artifacts/runner/
project-runner.candidate.json）：扩展现有 ``tests/e2e/run_e2e.py`` 的 profile/
runtime parser、integration 发现顺序、design-contracts profile 路径，以及锁定的
``v014-runner-evidence.json`` schema 字段。断言只落在 runner 的公开解析/发现出口，
不接线真实收集（真实收集属 Shield 的 integration/e2e）。
"""

from __future__ import annotations

import importlib.util
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


def test_unwired_design_contracts_profile_is_not_exposed() -> None:
    """AC-FR0900-01: an undelivered profile cannot enter the stand-in DAG."""
    parser = runner._parser()

    with pytest.raises(SystemExit):
        parser.parse_args(
            ["e2e", "--profile", "design-contracts", "--runtime", "local"]
        )
    assert runner._expand_profiles("all") == ["install", "chromium"]


def test_e2e_profile_choices_include_delivered_profiles() -> None:
    """AC-FR0900-01: --profile choices are install|chromium|all."""
    parser = runner._parser()
    args = parser.parse_args(["e2e", "--profile", "install", "--runtime", "local"])
    assert args.profile == "install"


def test_all_profile_expands_to_delivered_profiles() -> None:
    """AC-FR0900-01: all expands exactly to install,chromium."""
    assert runner._expand_profiles("all") == ["install", "chromium"]


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
    """AC-FR0800-01: integration discovery keeps historical path then v014 path."""
    assert runner._integration_paths() == [
        "tests/integration/install_experience",
        "tests/integration/v014_design_contracts",
    ]


def test_install_profile_path() -> None:
    """AC-FR0900-01: install profile resolves to the install e2e directory."""
    paths, _selection = runner._profile_paths("install")
    assert paths == ["tests/e2e/install_experience"]


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
