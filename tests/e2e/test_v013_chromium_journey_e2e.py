"""Chromium closes the complete v0.13 workbench product journey."""

from __future__ import annotations

import json
import os
import socket
import subprocess
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

import pytest


def _chromium_available() -> bool:
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as playwright:
            return Path(playwright.chromium.executable_path).exists()
    except Exception:
        return False


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_for_health(base_url: str) -> None:
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        try:
            with urlopen(f"{base_url}/health", timeout=1) as response:
                if response.status == 200:
                    return
        except (URLError, OSError):
            time.sleep(0.2)
    raise TimeoutError(f"lk serve did not become healthy at {base_url}")


def _prepare_workspace(root: Path) -> None:
    spec_id = "v0.13-999-browser-fixture"
    project = root / ".louke" / "project"
    specs = project / "specs" / spec_id
    end_user = root / ".louke" / "end-user-docs"
    wiki = root / ".louke" / "wiki" / "pages"
    specs.mkdir(parents=True, exist_ok=True)
    end_user.mkdir(parents=True, exist_ok=True)
    wiki.mkdir(parents=True, exist_ok=True)
    (project / "project.toml").write_text(
        "\n".join(
            (
                "[project]",
                'version = "0.13.1"',
                f'spec_id = "{spec_id}"',
                'project = "browser fixture"',
                "",
                "[meta]",
                'current_stage = "M-E2E"',
            )
        )
        + "\n",
        encoding="utf-8",
    )
    (root / ".louke" / "web-users.json").write_text(
        json.dumps(
            {"version": 1, "users": [{"username": "owner", "password": "secret"}]}
        )
        + "\n",
        encoding="utf-8",
    )
    (specs / "story.md").write_text("# Story\n\nSee US-1301.\n", encoding="utf-8")
    (specs / "spec.md").write_text(
        '# Fixture Spec\n\n<a id="fr-1301"></a>\n## FR-1301 Chrome\n\nSee US-1301.\n',
        encoding="utf-8",
    )
    (specs / "acceptance.md").write_text(
        '<a id="fr-1301"></a>\n## FR-1301\n\nBrowser acceptance.\n',
        encoding="utf-8",
    )
    (specs / "architecture.md").write_text("# Architecture\n", encoding="utf-8")
    (end_user / "guide.md").write_text("# User Guide\n\nHello.\n", encoding="utf-8")
    (wiki / "README.md").write_text("# README\n", encoding="utf-8")
    fixture = Path(__file__).parents[1] / "fixtures" / "runs" / "project_active.json"
    (project / "runs.json").write_text(
        fixture.read_text(encoding="utf-8"), encoding="utf-8"
    )


@pytest.mark.chromium_e2e
@pytest.mark.skipif(
    not _chromium_available(),
    reason="Chromium or Playwright is not installed; run: python -m playwright install chromium; issue #180",
)
@pytest.mark.skipif(
    not os.environ.get("LOUKE_E2E_SERVER_PYTHON")
    or not os.environ.get("LOUKE_E2E_CASE_CWD"),
    reason="v0.13 Chromium journey must run through the project-venv E2E runner",
)
def test_v013_chromium_main_journey() -> None:
    """AC-FR1317-01/02/03/04@v0.13: complete real-browser journey."""
    from playwright.sync_api import sync_playwright

    product_python_raw = os.environ.get("LOUKE_E2E_SERVER_PYTHON", "")
    workspace_raw = os.environ.get("LOUKE_E2E_CASE_CWD", "")
    assert product_python_raw, "LOUKE_E2E_SERVER_PYTHON must select a product venv"
    assert workspace_raw, "LOUKE_E2E_CASE_CWD must select the isolated workspace"
    product_python = Path(product_python_raw)
    workspace = Path(workspace_raw).resolve()
    runner_python = Path(os.environ["LOUKE_PROJECT_RUNNER_PYTHON"])
    repo_venv = Path(__file__).parents[2] / ".venv"
    # Compare venv *prefixes* (not resolved executables): on Linux both venv
    # shims may resolve to the same base interpreter, so ``.resolve()``
    # produces identical paths.  The installed-wheel guarantee is that the
    # product venv directory differs from the runner venv and that ``louke``
    # resolves under the product environment -- not that the Python binaries
    # are distinct files.
    product_venv_root = product_python.parent.parent
    runner_venv_root = runner_python.parent.parent
    assert product_venv_root != runner_venv_root, (
        f"product venv {product_venv_root} must differ from runner venv {runner_venv_root}"
    )
    assert product_venv_root.resolve() != repo_venv.resolve(), (
        f"product venv must not be the repo .venv: {product_venv_root}"
    )
    _prepare_workspace(workspace)

    port = _free_port()
    base_url = f"http://127.0.0.1:{port}"
    environment = os.environ.copy()
    server = subprocess.Popen(
        [
            str(product_python),
            "-m",
            "louke",
            "serve",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
            "--project-root",
            str(workspace),
            "--opencode-backend",
            "mock",
        ],
        cwd=workspace,
        env=environment,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    browser = None
    try:
        _wait_for_health(base_url)
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page()
            errors: list[str] = []
            failed_requests: list[str] = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.on(
                "response",
                lambda response: (
                    failed_requests.append(f"{response.status} {response.url}")
                    if response.status >= 500
                    else None
                ),
            )
            login = page.request.post(
                f"{base_url}/api/auth/login",
                data={"username": "owner", "password": "secret"},
            )
            assert login.ok
            page.goto(f"{base_url}/workbench", wait_until="domcontentloaded")
            expect = page.get_by_test_id
            assert expect("workbench-toolbar").is_visible()
            assert expect("workbench-sidebar").is_visible()
            assert expect("workbench-main").is_visible()

            expect("toolbar-dev-docs").click()
            assert expect("devdocs-tree").is_visible()
            page.locator('[data-testid^="devdocs-spec-"]').first.click()
            expect("devdocs-file-spec").first.click()
            page.wait_for_url("**/workbench?spec=*&doc=spec")
            page.wait_for_load_state("domcontentloaded")
            expect("devdocs-pane-container").locator(".doc-pane").first.wait_for()
            assert expect("devdocs-cross-ref-US-1301").is_visible()
            expect("devdocs-cross-ref-US-1301").click()
            assert "#us-1301" in page.url

            expect("toolbar-end-user-docs").click()
            assert expect("enduserdocs-tree").is_visible()
            expect("enduserdocs-file-guide").click()
            assert expect("enduserdocs-editor").is_visible()
            assert "User Guide" in expect("enduserdocs-editor").input_value()

            expect("toolbar-wiki").click()
            assert expect("wiki-tree").is_visible()
            expect("wiki-page-README").click()
            assert page.get_by_text("README", exact=True).last.is_visible()

            expect("toolbar-runs").click()
            assert expect("runs-sidebar").is_visible()
            expect("runs-project-project-active").click()
            expect("runs-node-review").click()
            detail = expect("stage-artifact-detail")
            assert detail.is_visible()
            for value in ("abc123", "PASS", "Prism", "Looks good"):
                assert value in detail.inner_text()

            open_tabs = page.locator('[data-testid="workbench-tab"]:not([hidden])')
            keys = open_tabs.evaluate_all(
                "nodes => nodes.map(node => node.dataset.tabKey)"
            )
            assert {"dev-docs", "end-user-docs", "wiki", "runs"}.issubset(set(keys))
            assert not errors
            assert not failed_requests
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
