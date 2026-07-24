"""Release builds prefer PyPI and retry network failures through Aliyun."""

from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import subprocess
from typing import Any


_SPEC = spec_from_file_location(
    "build_with_index_fallback_test_module",
    Path("tools/build_with_index_fallback.py"),
)
assert _SPEC and _SPEC.loader
adapter = module_from_spec(_SPEC)
_SPEC.loader.exec_module(adapter)


def test_build_uses_pypi_without_retry_on_success(monkeypatch) -> None:
    """A successful primary build does not contact the fallback index."""
    calls: list[dict[str, Any]] = []

    def run(command, *, env, **kwargs):
        calls.append({"command": command, "env": env, **kwargs})
        return subprocess.CompletedProcess(command, 0, stdout="built\n", stderr="")

    monkeypatch.setattr(adapter.subprocess, "run", run)

    assert adapter.build(["--wheel"]) == 0
    assert len(calls) == 1
    assert calls[0]["env"]["PIP_INDEX_URL"] == adapter.PYPI_INDEX
    assert "PIP_EXTRA_INDEX_URL" not in calls[0]["env"]


def test_build_retries_network_failure_with_aliyun(monkeypatch) -> None:
    """A network failure retries the isolated build against Aliyun."""
    calls: list[dict[str, Any]] = []
    results = iter(
        [
            subprocess.CompletedProcess(
                ["build"], 1, stdout="", stderr="SSLError: EOF"
            ),
            subprocess.CompletedProcess(["build"], 0, stdout="built\n", stderr=""),
        ]
    )

    def run(command, *, env, **kwargs):
        calls.append({"command": command, "env": env, **kwargs})
        return next(results)

    monkeypatch.setattr(adapter.subprocess, "run", run)

    assert adapter.build(["--sdist"]) == 0
    assert [call["env"]["PIP_INDEX_URL"] for call in calls] == [
        adapter.PYPI_INDEX,
        adapter.ALIYUN_INDEX,
    ]


def test_build_does_not_retry_non_network_failure(monkeypatch) -> None:
    """A build/configuration failure is returned without masking its cause."""
    calls: list[dict[str, Any]] = []

    def run(command, *, env, **kwargs):
        calls.append({"command": command, "env": env, **kwargs})
        return subprocess.CompletedProcess(
            command, 1, stdout="", stderr="invalid pyproject"
        )

    monkeypatch.setattr(adapter.subprocess, "run", run)

    assert adapter.build([]) == 1
    assert len(calls) == 1
