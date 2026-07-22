"""Unit contracts for the installed-wheel browser runner."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.e2e import run_e2e


def test_browser_cache_path_is_explicit_and_must_exist(tmp_path: Path) -> None:
    """A configured Playwright cache is preserved and validated."""
    environment = {"PLAYWRIGHT_BROWSERS_PATH": str(tmp_path)}

    assert run_e2e._resolve_playwright_browsers_path(environment) == tmp_path
    assert environment["PLAYWRIGHT_BROWSERS_PATH"] == str(tmp_path)


def test_browser_cache_path_fails_when_configured_directory_is_missing(
    tmp_path: Path,
) -> None:
    """A missing explicit browser cache cannot become a skipped E2E suite."""
    environment = {"PLAYWRIGHT_BROWSERS_PATH": str(tmp_path / "missing")}

    with pytest.raises(RuntimeError, match="PLAYWRIGHT_BROWSERS_PATH"):
        run_e2e._resolve_playwright_browsers_path(environment)


def test_browser_cache_path_is_derived_from_canonical_chromium_executable(
    tmp_path: Path,
) -> None:
    """A discovered executable yields the cache root passed to child pytest."""
    cache = tmp_path / "ms-playwright"
    executable = cache / "chromium-1208" / "chrome" / "Chromium"
    executable.parent.mkdir(parents=True)
    executable.touch()
    environment: dict[str, str] = {}

    result = run_e2e._resolve_playwright_browsers_path(
        environment, executable_path=executable
    )

    assert result == cache
    assert environment["PLAYWRIGHT_BROWSERS_PATH"] == str(cache)
