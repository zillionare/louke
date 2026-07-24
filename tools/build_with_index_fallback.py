#!/usr/bin/env python3
"""Build Python artifacts with a deterministic PyPI-to-Aliyun fallback."""

from __future__ import annotations

import os
import subprocess
import sys


PYPI_INDEX = "https://pypi.org/simple"
ALIYUN_INDEX = "https://mirrors.aliyun.com/pypi/simple"
_NETWORK_MARKERS = (
    "could not fetch url",
    "connectionerror",
    "failed to establish a new connection",
    "max retries exceeded",
    "network is unreachable",
    "name or service not known",
    "remote end closed connection",
    "sslerror",
    "ssleoferror",
    "temporary failure",
    "timed out",
    "timeout",
)


def _build_environment(index: str) -> dict[str, str]:
    """Return an isolated-build environment using exactly one package index."""
    environment = os.environ.copy()
    environment["PIP_INDEX_URL"] = index
    environment.pop("PIP_EXTRA_INDEX_URL", None)
    return environment


def _is_network_failure(result: subprocess.CompletedProcess[str]) -> bool:
    """Return whether build output identifies a package-index network failure."""
    output = f"{result.stdout}\n{result.stderr}".lower()
    return any(marker in output for marker in _NETWORK_MARKERS)


def _run_build(arguments: list[str], index: str) -> subprocess.CompletedProcess[str]:
    """Run the isolated build command with one selected package index."""
    return subprocess.run(
        [sys.executable, "-m", "build", *arguments],
        env=_build_environment(index),
        capture_output=True,
        text=True,
        check=False,
    )


def _write_output(result: subprocess.CompletedProcess[str]) -> None:
    """Forward captured build output to the caller's standard streams."""
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)


def build(arguments: list[str]) -> int:
    """Build artifacts from ``arguments`` with PyPI-first Aliyun fallback.

    Args:
        arguments: Options passed unchanged to ``python -m build``.
    Returns:
        The build process exit code.
    Raises:
        OSError: If the Python subprocess cannot be started.
    Side effects:
        Creates the artifacts requested by the underlying build command.
    """
    primary = _run_build(arguments, PYPI_INDEX)
    _write_output(primary)
    if primary.returncode == 0 or not _is_network_failure(primary):
        return primary.returncode
    print(
        "Primary PyPI index unavailable; retrying isolated build via Aliyun.",
        file=sys.stderr,
    )
    fallback = _run_build(arguments, ALIYUN_INDEX)
    _write_output(fallback)
    return fallback.returncode


def main(argv: list[str] | None = None) -> int:
    """Pass build arguments through and return the fallback build exit code."""
    return build(list(sys.argv[1:] if argv is None else argv))


if __name__ == "__main__":
    raise SystemExit(main())
