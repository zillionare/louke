"""Shield commands - e2e test authoring (B level).

Shield responsibilities: write e2e tests per test-plan section 6
(Playwright/testclient/direct DB query).
B-level agent - method fixed, low cost.
lk provides: run e2e + commit per standard + scaffold generation.

e2e env configuration (after fix-001a):
- read [e2e] section from .louke/project/project.toml (filled by Archer M-ARCH)
- by default run start -> wait ready -> run e2e -> teardown in order
- --no-env skips auto start/stop (user has manually started the project)
- command execution: shlex.split + shell=False (prevents project.toml tampering injection)
"""
import argparse
import shlex
import subprocess
import sys
import time
from pathlib import Path

from ._common import _toml_load, git, PROJECT_INFO_PATH


def register(subparsers):
    parser = subparsers.add_parser('shield', help='e2e test authoring (Shield, B level)')
    sub = parser.add_subparsers(dest='command', required=True, metavar='<command>')

    p = sub.add_parser('run-e2e', help='run e2e tests (default: auto start/stop per project.toml [e2e] section)')
    p.add_argument('--spec', default='', help='spec-id (optional, filter)')
    p.add_argument('--browser', default='chromium', choices=['chromium', 'firefox', 'webkit'])
    p.add_argument('--no-env', action='store_true', help='skip auto start/ready/teardown (user started manually)')

    p = sub.add_parser('commit-e2e', help='commit e2e tests (per standard)')
    p.add_argument('--spec', required=True)
    p.add_argument('--message', required=True)

    p = sub.add_parser('scaffold', help='generate e2e test skeleton (3 templates: Playwright/testclient/DB)')
    p.add_argument('--spec', required=True)
    p.add_argument('--type', required=True, choices=['playwright', 'testclient', 'db'])
    p.add_argument('--scenario', required=True, help='scenario name, e.g. user_login_flow')
    p.add_argument('--ac-id', required=True, help='AC-FRXXXX-YY reference')


def run(args):
    handlers = {
        'run-e2e': cmd_run_e2e,
        'commit-e2e': cmd_commit_e2e,
        'scaffold': cmd_scaffold,
    }
    return handlers.get(args.command, lambda _: 1)(args) or 0


def _read_e2e_env_from_config() -> dict:
    """Read [e2e] section of project.toml. Delegates to _common._toml_load, zero regex.

    Schema:
        [e2e]
        start = "make e2e-env-up"           # optional, starts the project
        ready = "curl -sf http://localhost/health"  # optional, readiness check (exit 0)
        ready_timeout_seconds = 60          # optional, default 60
        framework = "playwright"             # optional, playwright | testclient | db
        browsers = ["chromium"]              # optional, only effective for playwright
        teardown = "make e2e-env-down"      # optional, cleanup
    """
    data = _toml_load(PROJECT_INFO_PATH)
    if not data:
        return {}
    return data.get('e2e', {}) or {}


def _run_command(cmd_str: str, cwd: Path) -> int:
    """Safely execute a shell command. shlex.split + shell=False, prevents project.toml tampering injection.

    Even if project.toml is maliciously modified, shell metacharacters cannot be injected
    (e.g. `rm -rf /tmp; curl evil.com` is split by shlex into ['rm', '-rf', '/tmp;', 'curl', 'evil.com'], curl is not executed).
    """
    if not cmd_str or not cmd_str.strip():
        return 0
    try:
        args = shlex.split(cmd_str)
    except ValueError as e:
        print(f'[shield] command parse failed: {cmd_str!r} ({e})', file=sys.stderr)
        return 1
    if not args:
        return 0
    return subprocess.run(args, cwd=cwd, shell=False, check=False).returncode


def _wait_ready(ready_cmd: str, cwd: Path, timeout_seconds: int) -> bool:
    """Poll the ready command until exit 0 or timeout."""
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if _run_command(ready_cmd, cwd) == 0:
            return True
        time.sleep(2)
    return False


def _default_e2e_config(spec):
    """Built-in default e2e config (playwright pytest). Managed by Shield."""
    return {
        'command': 'python3',
        'args': ['-m', 'pytest', '-q', '--tb=short', '--browser={browser}'],
        'path': f'.louke/project/specs/{spec}/tests/e2e/' if spec else 'tests/e2e/',
    }


def cmd_run_e2e(args):
    """Run e2e tests. Default starts/stops project per project.toml [e2e] section; --no-env skips."""
    cwd = Path.cwd()
    cfg = _default_e2e_config(args.spec)

    env = {} if args.no_env else _read_e2e_env_from_config()
    start = str(env.get('start', '')).strip()
    ready = str(env.get('ready', '')).strip()
    teardown_cmd = str(env.get('teardown', '')).strip()
    try:
        ready_timeout = int(env.get('ready_timeout_seconds', 60))
    except (TypeError, ValueError):
        ready_timeout = 60

    print(f"=== Run E2E ===")
    print(f"Config source: {'--no-env (manual)' if args.no_env else 'project.toml [e2e] section'}")
    print(f"Browser: {args.browser}")

    # 1. Start
    if start:
        print(f"\n[e2e] start: {start}")
        rc = _run_command(start, cwd)
        if rc != 0:
            print(f'[e2e] start failed (rc={rc})', file=sys.stderr)
            return rc

    # 2. Wait ready (poll the ready command until exit 0 or timeout)
    if ready:
        print(f"\n[e2e] waiting ready ({ready}, timeout {ready_timeout}s)")
        if not _wait_ready(ready, cwd, ready_timeout):
            print(f'[e2e] timeout waiting ready ({ready_timeout}s)', file=sys.stderr)
            if teardown_cmd:
                print(f'[e2e] teardown (after timeout): {teardown_cmd}')
                _run_command(teardown_cmd, cwd)
            return 1
        print('[e2e] ready')

    # 3. Run e2e
    cmd = [cfg['command'], *cfg['args'], cfg['path']]
    cmd = [c.replace('{browser}', args.browser) for c in cmd]
    print(f"\n[e2e] run: {' '.join(cmd)}")
    rc = subprocess.run(cmd, cwd=cwd, shell=False, check=False).returncode
    print(f"[e2e] exit code: {rc}")

    # 4. Teardown (regardless of success or failure)
    if teardown_cmd:
        print(f"\n[e2e] teardown: {teardown_cmd}")
        _run_command(teardown_cmd, cwd)

    return rc


def cmd_commit_e2e(args):
    """Commit e2e tests with proper format."""
    cwd = Path.cwd()
    spec_path = f".louke/project/specs/{args.spec}/tests/e2e/"

    print(f"=== Commit E2E ===")
    print(f"Spec path: {spec_path}")
    print(f"Message: {args.message}")

    cmds = [
        ['git', 'add', spec_path],
        ['git', 'commit', '-m', f'e2e: {args.message}'],
        ['git', 'push'],
    ]
    for cmd in cmds:
        rc, out, err = git(*cmd[1:], cwd=cwd)
        if rc != 0:
            print(f"failed: {' '.join(cmd)}\n{err}", file=sys.stderr)
            return rc
    print("✓ E2E committed and pushed")
    return 0


def cmd_scaffold(args):
    """Generate e2e test skeleton template.

    Path aligned with cmd_commit_e2e: .louke/project/specs/{spec}/tests/e2e/
    (e2e tests belong to the spec scope, not the top-level tests/, to avoid cross-spec interference)
    """
    cwd = Path.cwd()
    spec_path = f".louke/project/specs/{args.spec}/tests/e2e"
    target_dir = cwd / spec_path
    target_dir.mkdir(parents=True, exist_ok=True)
    target_file = target_dir / f'test_{args.scenario}.py'

    templates = {
        'playwright': f'''"""E2E test: {args.scenario} (AC: {args.ac_id}).

Generated by lk shield scaffold. Test framework: Playwright.
"""
import pytest
from playwright.sync_api import Page


@pytest.mark.e2e
def test_{args.scenario}(page: Page):
    """{args.ac_id}: {args.scenario}."""
    # 1. Setup (start service / build data)
    # ...

    # 2. Execute (browser operations)
    # page.goto("/...")
    # page.fill(...)
    # page.click(...)

    # 3. Assert (assert on outputs per interfaces.md)
    # assert page.url.endswith("/...")
    # assert page.locator("...").text_content() == "..."
''',
        'testclient': f'''"""E2E test: {args.scenario} (AC: {args.ac_id}).

Generated by lk shield scaffold. Test framework: TestClient (HTTP).
"""
import pytest
from fastapi.testclient import TestClient


@pytest.mark.e2e
def test_{args.scenario}(client: TestClient):
    """{args.ac_id}: {args.scenario}."""
    # 1. Setup
    # ...

    # 2. Execute (API calls)
    # response = client.get("/...")
    # response = client.post("/...", json={{...}})

    # 3. Assert (assert on outputs per interfaces.md)
    # assert response.status_code == 200
    # assert "..." in response.json()
''',
        'db': f'''"""E2E test: {args.scenario} (AC: {args.ac_id}).

Generated by lk shield scaffold. Test framework: direct DB query.
"""
import pytest


@pytest.mark.e2e
def test_{args.scenario}():
    """{args.ac_id}: {args.scenario}."""
    # 1. Setup (DB connection)
    # conn = get_db_connection()

    # 2. Execute (query/operation)
    # row = conn.execute("...").fetchone()

    # 3. Assert (assert on outputs per interfaces.md)
    # assert row["state"] == "..."
''',
    }

    template = templates[args.type]
    target_file.write_text(template)
    print(f"✓ Scaffold created: {target_file}")
    return 0