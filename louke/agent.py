"""Agent subcommand router + lk agent lint.

Usage:
    lk agent <name> <subcommand> [options]   # per-agent commands
    lk agent lint [options]                   # v0.6-009 FR-0040: validate agent frontmatter
    lk agent set-model <name> <abstract>      # v0.6-006: 改 model + 绑 + probe

All agent commands are dispatched through this module.
`lk agent lint` and `lk agent set-model` are special commands (not agents) for cross-agent operations.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

from . import (
    scout,
    sage,
    warden,
    lex,
    archer,
    keeper,
    judge,
    prism,
    devon,
    shield,
    librarian,
    maestro,
)


AGENTS = {
    'scout': scout,
    'sage': sage,
    'warden': warden,
    'lex': lex,
    'archer': archer,
    'keeper': keeper,
    'judge': judge,
    'prism': prism,
    'devon': devon,
    'shield': shield,
    'librarian': librarian,
    'maestro': maestro,
}

from ._common import git_root

# v0.6-009 FR-0010.5: OpenCode permission 键白名单
# (Qwen A-003-3 校准: todowrite 不在; external_directory + doom_loop 加入)
PERMISSION_KEYS = {
    'read', 'edit', 'glob', 'grep', 'bash', 'task', 'skill', 'lsp',
    'question', 'webfetch', 'websearch', 'external_directory', 'doom_loop',
}

# v0.6-009 FR-0010: 5 个 agent 必填 permission 块
PERMISSION_REQUIRED = {
    'warden', 'judge', 'archer', 'librarian', 'maestro',
}

VALID_MODES = {'primary', 'subagent', 'all'}

# v0.6-009 NFR-0050: 单一 primary agent 白名单
SINGLE_PRIMARY = {'maestro'}

# v0.6-009 NFR-0040: 最低 OpenCode 版本 (Qwen A-8.4 校准)
# 常量定义在 louke/__init__.py MIN_OPENCODE_VERSION, 此处 re-export 方便内部引用
from . import MIN_OPENCODE_VERSION


def register(parser):
    """Register agent subcommands + special 'lint' / 'set-model' commands."""
    sub = parser.add_subparsers(dest='agent_command', required=True, metavar='<command>')

    # v0.6-009 FR-0040: lk agent lint
    p = sub.add_parser('lint', help='校验 source agents/*.md 的 frontmatter 合规')
    p.add_argument('--check-opencode-version', action='store_true',
                   help='同时检查 opencode --version 是否 >= MIN_OPENCODE_VERSION')
    p.add_argument('--strict', action='store_true',
                   help='严格模式: 白名单外字段也报错 (默认仅 warning)')

    # v0.6-006: lk agent set-model <name> <abstract>
    p = sub.add_parser('set-model',
                       help='改 agent models[0] 为指定 abstract, 交互绑 + probe + 自动重生 board')
    p.add_argument('name', help='agent 名字 (e.g. archer)')
    p.add_argument('model', help='abstract 模型名 (e.g. glm-5.2)')
    p.add_argument('--no-probe', action='store_true', help='跳过 probe 检查')
    p.add_argument('--no-regen', action='store_true', help='改完不跑 lk board opencode')
    p.add_argument('--root', help='项目根目录 (默认: 当前 git 仓库)')
    p.add_argument('--dry-run', action='store_true', help='只打印会做什么, 不实际改')

    # 12 个 agent 子命令
    for name, module in AGENTS.items():
        if hasattr(module, 'register'):
            module.register(sub)


def run(args):
    if args.agent_command == 'lint':
        return cmd_lint(args)
    if args.agent_command == 'set-model':
        return cmd_set_model(args)
    module = AGENTS.get(args.agent_command)
    if not module or not hasattr(module, 'run'):
        print(f"lk agent: '{args.agent_command}' not found", flush=True)
        return 1
    return module.run(args) or 0


def agent_source(root: Path) -> Path:
    """Reuse board.py 的 agent 源目录查找逻辑."""
    for candidate in (root / '.louke/agents', root / 'agents'):
        if candidate.exists():
            return candidate
    from ._common import package_root
    return package_root() / 'agents'


def _check_permission_block(name: str, perm, errors: list[str]) -> None:
    """v0.6-009 FR-0040 AC-2: permission 内容校验."""
    if not isinstance(perm, dict):
        errors.append(f'{name}: permission must be a YAML dict, got {type(perm).__name__}')
        return
    bad_keys = set(perm.keys()) - PERMISSION_KEYS
    if bad_keys:
        errors.append(f'{name}: permission has unknown keys: {sorted(bad_keys)}; '
                      f'allowed = {sorted(PERMISSION_KEYS)}')
    for key, value in perm.items():
        if key not in PERMISSION_KEYS:
            continue
        if not isinstance(value, str):
            errors.append(f'{name}: permission.{key} must be string, got {type(value).__name__}')
            continue
        if value not in ('allow', 'deny', 'ask') and '*' not in value and '?' not in value:
            errors.append(f'{name}: permission.{key} value {value!r} not in '
                          f'{{allow, deny, ask, glob-pattern}}')


def _check_mode_uniqueness(agents_fm: dict, errors: list[str]) -> None:
    """v0.6-009 NFR-0050: mode: primary 数量 = 1 (白名单 = maestro)."""
    primaries = [n for n, fm in agents_fm.items() if fm.get('mode') == 'primary']
    if len(primaries) != 1:
        errors.append(f'only maestro can be primary; found {len(primaries)} '
                      f'agents with mode: primary ({primaries})')
    elif primaries[0] not in SINGLE_PRIMARY:
        errors.append(f'mode: primary is reserved for {SINGLE_PRIMARY}, '
                      f'got {primaries[0]}')
    all_modes = [n for n, fm in agents_fm.items() if fm.get('mode') == 'all']
    if all_modes:
        errors.append(f'mode: all is deprecated; use primary or subagent. '
                      f'found in: {all_modes}')


def _get_opencode_version() -> str | None:
    """Read `opencode --version`, return None if opencode unavailable."""
    try:
        out = subprocess.check_output(['opencode', '--version'],
                                      text=True, stderr=subprocess.DEVNULL)
        m = re.search(r'(\d+\.\d+\.\d+)', out)
        return m.group(1) if m else None
    except Exception:
        return None


def _version_tuple(v: str) -> tuple[int, ...]:
    return tuple(int(x) for x in v.split('.'))


def cmd_lint(args):
    root = git_root() or Path.cwd()
    src = agent_source(root)
    if not src.exists():
        print(f'[!] agent source dir not found: {src}', flush=True)
        return 1

    from .board import parse_frontmatter

    agents_fm: dict[str, dict] = {}
    errors: list[str] = []

    for fp in sorted(src.glob('*.md')):
        if fp.name in {'README.md', 'ROSTER.md'}:
            continue
        text = fp.read_text(encoding='utf-8')
        fm, _ = parse_frontmatter(text)
        name = fm.get('name') or fp.stem
        agents_fm[name] = fm

        # FR-0040 AC-2: 5 个 agent 必填 permission
        if name in PERMISSION_REQUIRED:
            if 'permission' not in fm:
                errors.append(f'missing permission block for {name}')
                continue
            _check_permission_block(name, fm['permission'], errors)

        # FR-0040 AC-2: mode 字段必填且合法
        mode = fm.get('mode')
        if not mode:
            errors.append(f'{name}: missing mode field')
        elif mode not in VALID_MODES:
            errors.append(f'{name}: mode {mode!r} not in {sorted(VALID_MODES)}')

    # NFR-0050: 单一 primary 约束
    _check_mode_uniqueness(agents_fm, errors)

    # NFR-0040: OpenCode 版本检查 (optional)
    if args.check_opencode_version:
        actual = _get_opencode_version()
        if actual is None:
            print('[!] opencode --version unavailable, skip version check',
                  flush=True)
        elif _version_tuple(actual) < _version_tuple(MIN_OPENCODE_VERSION):
            print(f'[!] opencode {actual} < MIN_OPENCODE_VERSION '
                  f'{MIN_OPENCODE_VERSION}; permission object format may not work',
                  flush=True)
        else:
            print(f'[ok] opencode {actual} >= MIN_OPENCODE_VERSION '
                  f'{MIN_OPENCODE_VERSION}', flush=True)

    if errors:
        from ._color import fail, red
        print(f'{fail(f"{len(errors)} errors:")}', flush=True)
        for e in errors:
            print(f'  {red("-")} {e}', flush=True)
        return 1
    from ._color import ok, cyan, dim
    print(f'{ok()} {len(agents_fm)} agents pass lint '
          f'{dim("(")}{cyan(str(sum(1 for n in agents_fm if n in PERMISSION_REQUIRED)))}{dim(" with permission)")}',
          flush=True)
    return 0


def _resolve_root(args) -> Path | None:
    """Resolve project root for set-model: --root > git_root() > error."""
    from ._color import red, cyan
    explicit = getattr(args, 'root', None)
    if explicit:
        root = Path(explicit).resolve()
    else:
        root = git_root()
    if root is None:
        print(
            f'{red("error:")} lk agent set-model 需要 git 仓库 (或显式 --root).',
            file=sys.stderr,
        )
        print(f'  {cyan("hint:")} 在 louke 项目根目录 (有 .git/) 跑, 或 --root <path>',
              file=sys.stderr)
        return None
    return Path(root)


def cmd_set_model(args):
    """v0.6-006: lk agent set-model <name> <abstract>

    1. 改 <name>.md 的 models[0] 为 <abstract>
    2. 跑交互式 bind (resolve abstract → real model, probe + save)
    3. 自动跑 lk board opencode 重生 .opencode/agents/<name>.md
    """
    from ._color import ok, fail, warn, info, cyan, dim, red
    from .board import agent_source, cmd_opencode
    from .models import (
        resolve_model, _interactive_bind_one, _probe_or_skip, _direct_bind,
    )

    name: str = args.name
    abstract: str = args.model

    # 1. Resolve project root
    root = _resolve_root(args)
    if root is None:
        return 1

    # 2. Find agent source file
    src = agent_source(root)
    agent_file = src / f'{name}.md'
    if not agent_file.exists():
        candidates = [f for f in src.glob('*.md') if f.stem.lower() == name.lower()]
        if not candidates:
            print(f'{fail(f"agent file not found: {agent_file}")}', file=sys.stderr)
            return 1
        if len(candidates) > 1:
            names = ', '.join(c.name for c in candidates)
            print(f'{fail(f"multiple matches for {name!r}: {names}")}', file=sys.stderr)
            return 1
        agent_file = candidates[0]

    # 3. Update models: first entry in frontmatter (preserve rest of file)
    text = agent_file.read_text(encoding='utf-8')
    pattern = re.compile(r'(^models:\s*\n\s*-\s*)\S+', re.MULTILINE)
    match = pattern.search(text)
    if not match:
        print(f'{fail(f"no models: list found in {agent_file.name}")}', file=sys.stderr)
        return 1
    old_first = match.group(0).split('-', 1)[1].strip()
    if old_first == abstract:
        print(f'{info(f"{agent_file.name} models[0] 已经是 {abstract}, 无变化")}')
    else:
        if args.dry_run:
            print(f'{info(f"[dry-run] {agent_file.name} models[0] {old_first} -> {abstract}")}')
        else:
            new_text = pattern.sub(rf'\g<1>{abstract}', text, count=1)
            agent_file.write_text(new_text, encoding='utf-8')
            print(f'{ok(f"{agent_file.name}: models[0] {old_first} -> {abstract}")}')

    # 4. Bind abstract to real model (if not already bound)
    if args.dry_run:
        return 0
    resolved = resolve_model(abstract)
    if resolved == abstract:
        # 未绑 — 交互式
        print(f'{warn(f"{abstract} 未绑定, 进入交互式...")}')
        if args.no_probe:
            print(f'{info("提示: 跑 lk models bind <abstract> <full> 设 alias")}')
            return 0
        result = _interactive_bind_one(abstract, False)
        if result != 0:
            return result
        resolved = resolve_model(abstract)
    else:
        # 已绑 (alias or opencode 匹配) — probe 验证
        if not args.no_probe:
            ok = _probe_or_skip(resolved, False, allow_skip=True)
            if not ok:
                print(f'{warn(f"{resolved} probe 失败但已绑, 继续 (可能运行时失败)")}')
        print(f'{ok(f"{abstract} -> {resolved} (已绑定)")}')

    # 5. Regenerate board
    if not args.no_regen:
        print(f'{info("重新生成 board...")}')
        regen_args = argparse.Namespace(
            root=str(root),
            quiet=True,
            dry_run=False,
        )
        cmd_opencode(regen_args)

    return 0
