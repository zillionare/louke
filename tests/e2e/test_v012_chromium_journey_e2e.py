"""S8 (#180): single Chromium product journey against an installed-wheel server.

gap-analysis §4 Batch 5 / §3 P1-2: one supported-browser (Chromium) product
journey, not a multi-browser matrix. The journey exercises the real user
entry path from a clean install:

1. Build the wheel and install it in a clean venv (hermetic; no source tree).
2. Spawn ``lk serve`` in setup-only mode (fresh project root, no principal).
3. Launch Chromium via Playwright.
4. Wait for ``/health`` to confirm the server is up.
5. Navigate to ``/`` and assert the setup-only redirect to ``/setup``.
6. Locate the setup wizard via semantic selectors (title, role, text, id).
7. Fill the first-user form and submit, proving the page renders and the
   form posts through to the real API.
8. Take a screenshot for evidence.
9. Close the browser and kill the server (always, even on failure).

The test is marked ``@pytest.mark.chromium_e2e`` so it can be excluded from
the default ``tests/e2e`` run (it needs a real browser) and selected with
``-m chromium_e2e``. It skips with a clear message when Chromium is not
installed locally, since a missing browser is an environment condition, not
a product pass.

Selector strategy: semantic (``text=``, ``role=``, ``id=``, ``get_by_*``),
never CSS classes or pixel layout - those belong to v0.14's UI rewrite.
"""

from __future__ import annotations

import os
import signal
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Chromium availability detection
# ---------------------------------------------------------------------------

def chromium_is_installed() -> bool:
    """Return True if Playwright's expected Chromium executable is installed.

    Checks the executable path that the installed Playwright library would
    actually launch, not just that some ``chromium-*`` directory exists in
    the cache. This catches the common version-mismatch case where an older
    Chromium is cached but the installed Playwright expects a newer build.
    A bare directory check would incorrectly report installed and then fail
    at launch time, which would be reported as a product failure rather
    than the environment condition it is.
    """
    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            return Path(p.chromium.executable_path).exists()
    except Exception:
        return False


_SKIP_REASON = (
    "Chromium not installed; run `python -m playwright install chromium` "
    "to enable the S8 product journey test"
)


# ---------------------------------------------------------------------------
# Server boot helpers (mirror S7's hermetic clean-venv approach)
# ---------------------------------------------------------------------------

def _repo_root() -> Path:
    """Return the repository root (this file lives under it).

    This file lives at ``<root>/tests/e2e/test_v012_chromium_journey_e2e.py``,
    so the repo root is three parents up: ``e2e`` -> ``tests`` -> root.
    """
    return Path(__file__).resolve().parents[2]


def _subprocess_env() -> dict[str, str]:
    """Return an env for subprocess calls to clean-venv pythons.

    Propagates ``DYLD_LIBRARY_PATH`` on macOS standalone CPython builds so
    the venv python can resolve ``libpythonX.Y.dylib`` when ``lk`` invokes
    it. Without this, the spawned server SIGABRTs before binding its port.
    """
    env = os.environ.copy()
    for candidate in (Path(sys.base_prefix) / "lib", Path(sys.base_prefix).parent / "lib"):
        if candidate.exists() and any(candidate.glob("libpython*.dylib")):
            env["DYLD_LIBRARY_PATH"] = (
                str(candidate) + os.pathsep + env.get("DYLD_LIBRARY_PATH", "")
            )
            break
    return env


def _free_port() -> int:
    """Bind a transient socket to discover a free TCP port for the server."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]
    finally:
        sock.close()


def _build_wheel(out_dir: Path) -> Path:
    """Build the louke wheel into ``out_dir`` and return its path."""
    completed = subprocess.run(
        [sys.executable, "-m", "build", "--wheel", "--outdir", str(out_dir)],
        cwd=str(_repo_root()),
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"python -m build failed:\nstdout:\n{completed.stdout}\n"
            f"stderr:\n{completed.stderr}"
        )
    wheels = list(out_dir.glob("louke-*.whl"))
    if not wheels:
        raise RuntimeError(f"no wheel produced in {out_dir}")
    return wheels[0]


def _create_clean_venv(prefix: Path) -> Path:
    """Create a throwaway virtualenv at ``prefix`` and return its python path."""
    import venv

    venv.create(str(prefix), with_pip=False, clear=True)
    py = prefix / "bin" / "python"
    completed = subprocess.run(
        [str(py), "-m", "ensurepip", "--upgrade", "--default-pip"],
        capture_output=True,
        text=True,
        env=_subprocess_env(),
    )
    if completed.returncode != 0:
        raise RuntimeError(f"ensurepip failed:\n{completed.stderr}")
    return py


def _install_wheel(venv_python: Path, wheel_path: Path) -> None:
    """Install ``wheel_path`` (with its declared deps) into the target venv."""
    completed = subprocess.run(
        [str(venv_python), "-m", "pip", "install", "--force-reinstall",
         str(wheel_path)],
        capture_output=True,
        text=True,
        env=_subprocess_env(),
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"pip install failed:\n{completed.stdout}\n{completed.stderr}"
        )


def _wait_for_health(base_url: str, *, timeout: float = 30.0) -> None:
    """Poll ``{base_url}/health`` until it returns 200 or ``timeout`` passes.

    Raises:
        TimeoutError: If ``/health`` does not return 200 within ``timeout``.
    """
    deadline = time.time() + timeout
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"{base_url}/health", timeout=2) as resp:
                if resp.status == 200:
                    return
        except (urllib.request.URLError, ConnectionError, OSError) as exc:
            last_error = exc
        time.sleep(0.5)
    raise TimeoutError(
        f"/health did not return 200 within {timeout}s at {base_url} "
        f"(last error: {last_error!r})"
    )


class _ServerProcess:
    """Wraps a background ``lk serve`` subprocess with guaranteed teardown.

    SIGTERM first, then SIGKILL after a grace period, always reaps the
    zombie. The terminate method is safe to call even if the process
    already exited.
    """

    def __init__(self, proc: subprocess.Popen) -> None:
        self._proc = proc

    def terminate(self, *, grace_seconds: float = 5.0) -> None:
        """Terminate the server, escalating SIGTERM -> SIGKILL if needed."""
        if self._proc.poll() is not None:
            return
        self._proc.send_signal(signal.SIGTERM)
        try:
            self._proc.wait(timeout=grace_seconds)
        except subprocess.TimeoutExpired:
            self._proc.kill()
            self._proc.wait(timeout=grace_seconds)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def installed_wheel_server(tmp_path_factory: pytest.TempPathFactory):
    """Build wheel, install in clean venv, spawn ``lk serve``; yield base URL.

    Module-scoped so the expensive wheel build + venv install happens once
    for the journey. The server is started in setup-only mode (fresh project
    root) and torn down on module exit regardless of test outcomes.
    """
    work_dir = tmp_path_factory.mktemp("chromium_journey")
    wheel = _build_wheel(work_dir / "wheel_out")
    venv_dir = work_dir / "venv"
    venv_python = _create_clean_venv(venv_dir)
    _install_wheel(venv_python, wheel)

    project_root = work_dir / "project_root"
    project_root.mkdir(parents=True, exist_ok=True)
    port = _free_port()

    env = _subprocess_env()
    env["PATH"] = str(venv_dir / "bin") + os.pathsep + env.get("PATH", "")
    env.pop("PYTHONPATH", None)

    proc = subprocess.Popen(
        [
            str(venv_dir / "bin" / "lk"), "serve",
            "--host", "127.0.0.1",
            "--port", str(port),
            "--project-root", str(project_root),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
    )
    server = _ServerProcess(proc)
    base_url = f"http://127.0.0.1:{port}"
    try:
        _wait_for_health(base_url)
        yield base_url
    finally:
        server.terminate()


# ---------------------------------------------------------------------------
# Journey test
# ---------------------------------------------------------------------------

@pytest.mark.chromium_e2e
@pytest.mark.skipif(not chromium_is_installed(), reason=_SKIP_REASON)
def test_chromium_setup_journey(installed_wheel_server, tmp_path: Path) -> None:
    """Chromium drives the setup-only wizard end-to-end.

    Journey:
    1. Server is up (fixture waited on ``/health``).
    2. Navigate to ``/`` -> expect 303 redirect to ``/setup``.
    3. The setup page renders with the expected title and first-user form.
    4. Fill the form (semantic selectors: id, label text) and submit.
    5. Assert the page renders without a server error (no 5xx, title present).
    6. Screenshot captured for evidence.

    Uses semantic Playwright selectors exclusively; no CSS classes or pixel
    assertions, which belong to the v0.14 UI rewrite.
    """
    from playwright.sync_api import sync_playwright

    base_url = installed_wheel_server

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page()

            # Navigate to /; in setup-only mode the server redirects to /setup.
            response = page.goto(base_url + "/", wait_until="domcontentloaded")
            assert response is not None, "navigation to / returned no response"
            # A 303 redirect is reported as the final response after following.
            assert "/setup" in page.url, (
                f"expected / to redirect to /setup, landed on {page.url!r}"
            )

            # The setup wizard must render its known title and first-user form.
            # Use the <title> text as a stable, layout-independent signal.
            page.wait_for_load_state("domcontentloaded")
            title = page.title()
            assert "setup" in title.lower(), (
                f"setup page title should mention 'setup', got {title!r}"
            )

            # Locate the first-user form via stable element semantics: the form
            # inputs have id="name" and id="credential" in the setup wizard HTML.
            name_input = page.locator("#name")
            credential_input = page.locator("#credential")
            submit_button = page.get_by_role("button", name="Create first user")

            name_input.fill("aaron")
            credential_input.fill("secret-passphrase")
            submit_button.click()

            # After submit, the form posts to /setup/first-user which redirects
            # back to /setup (303). Wait for the navigation to settle and assert
            # we did not land on a 5xx error page.
            page.wait_for_load_state("domcontentloaded")
            final_url = page.url
            assert "setup" in final_url, (
                f"after first-user submit, expected to stay on /setup, "
                f"landed on {final_url!r}"
            )
            # The page should still render the setup shell (not an error page).
            assert "setup" in page.title().lower(), (
                f"post-submit page title should still mention 'setup', "
                f"got {page.title()!r}"
            )

            # Evidence screenshot.
            screenshot_path = tmp_path / "chromium_setup_journey.png"
            page.screenshot(path=str(screenshot_path), full_page=True)
            assert screenshot_path.exists(), "screenshot was not written"
        finally:
            browser.close()
