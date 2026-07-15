"""Single Chromium smoke journey for the v0.13 workbench."""

from __future__ import annotations

import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

import pytest


def _chromium_available() -> bool:
    """Return whether Playwright and its configured Chromium executable are available."""
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as playwright:
            return Path(playwright.chromium.executable_path).exists()
    except Exception:
        return False


def _free_port() -> int:
    """Return an available loopback port for an isolated local server."""
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_for_health(base_url: str) -> None:
    """Wait for the server health endpoint or raise a helpful timeout error."""
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        try:
            with urlopen(f"{base_url}/health", timeout=1) as response:
                if response.status == 200:
                    return
        except (URLError, OSError):
            time.sleep(0.2)
    raise TimeoutError(f"lk serve did not become healthy at {base_url}")


@pytest.mark.chrome_e2e
@pytest.mark.skipif(
    not _chromium_available(),
    reason="Chromium or Playwright is not installed; run: python -m playwright install chromium",
)
def test_v013_chromium_main_journey() -> None:
    """AC-FR1317-01/02/03/04: Chromium navigates Dev Docs, Wiki, and Runs."""
    from playwright.sync_api import sync_playwright

    port = _free_port()
    base_url = f"http://127.0.0.1:{port}"
    server = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "louke",
            "serve",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    browser = None
    try:
        _wait_for_health(base_url)
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                page = browser.new_page()
                page.goto(f"{base_url}/workbench", wait_until="domcontentloaded")
                expect = page.get_by_test_id
                assert expect("workbench-toolbar").is_visible()
                assert expect("workbench-sidebar").is_visible()
                expect("toolbar-dev-docs").click()
                assert expect("devdocs-tree").is_visible()
                page.locator('[data-testid^="devdocs-spec-"]').first.click()
                expect("devdocs-file-spec").first.click()
                page.wait_for_url("**/workbench?spec=*&doc=spec")
                page.wait_for_load_state("domcontentloaded")
                assert "doc=spec" in page.url
                expect("toolbar-wiki").click()
                assert expect("wiki-tree").is_visible()
                expect("wiki-page-README").click()
                assert (
                    expect("workbench-main")
                    .get_by_text("README", exact=True)
                    .is_visible()
                )
                expect("toolbar-runs").click()
                assert expect("runs-sidebar").is_visible()
                assert page.get_by_text("Current project", exact=True).is_visible()
            finally:
                browser.close()
                browser = None
    finally:
        if browser is not None:
            browser.close()
        if server.poll() is None:
            server.terminate()
            try:
                server.wait(timeout=5)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait(timeout=5)
