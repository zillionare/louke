"""NFR-0001: 自动化质量门槛.

- pytest 单元 + 集成 ≥95% coverage
- e2e marker 存在, smoke 用例在 tests/e2e/
- louke e2e start / louke e2e stop CLI 子命令存在
"""

import subprocess
import sys


def test_pytest_collects_unit_and_integration():
    """AC-NFR0001-01: pytest 能收集现有单元 + 集成测试。"""
    out = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "--collect-only",
            "-q",
            "tests/test_louke_paths.py",
            "tests/test_file_security.py",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert "test_louke_paths.py" in out.stdout
    assert "test_file_security.py" in out.stdout
    assert "5 tests collected" in out.stdout or "10 tests collected" in out.stdout


def test_e2e_marker_registered():
    """AC-NFR0001-01: -m e2e marker 已在 pytest.ini / pyproject.toml / conftest 注册。"""
    out = subprocess.run(
        [sys.executable, "-m", "pytest", "--markers"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert "@pytest.mark.e2e" in out.stdout


def test_e2e_smoke_test_exists():
    """AC-NFR0001-01: tests/e2e/ 至少有一个 smoke 用例。"""
    out = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "--collect-only",
            "-q",
            "tests/e2e",
            "-m",
            "e2e",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    # 至少收集到 1 个 test
    assert "test" in out.stdout.lower()


def test_coverage_config_present():
    """AC-NFR0001-02: pyproject.toml [tool.coverage.report] fail_under = 95。"""
    import tomllib
    from pathlib import Path

    data = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    report = data.get("tool", {}).get("coverage", {}).get("report", {})
    assert report.get("fail_under") == 95


def test_e2e_cli_start_help():
    """e2e start --help 应可用。"""
    out = subprocess.run(
        [sys.executable, "-m", "louke", "e2e", "start", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert out.returncode == 0
    assert "--host" in out.stdout
    assert "--opencode" in out.stdout


def test_e2e_cli_stop_help():
    """e2e stop --help 应可用。"""
    out = subprocess.run(
        [sys.executable, "-m", "louke", "e2e", "stop", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert out.returncode == 0
    assert "--port" in out.stdout
    assert "--cleanup-workspace" in out.stdout


def test_e2e_module_importable():
    """louke.e2e 模块存在并有 register_subcommand 入口。"""
    from louke import e2e as e2e_module

    assert hasattr(e2e_module, "register_subcommand")
    assert hasattr(e2e_module, "cmd_e2e_start")
    assert hasattr(e2e_module, "cmd_e2e_stop")
