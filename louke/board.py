"""IDE board generation commands."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from ._common import git_root
from .models import resolve_model


SKIP = {'README.md', 'ROSTER.md'}

# v0.6-009 FR-0030: 透传白名单 (除 description / mode / model 已单独处理).
# 来源: OpenCode 官方 frontmatter 字段 + permission.
PASSTHROUGH_KEYS = {
    'permission',   # v0.6-009 FR-0010/0060/0070 落地
    'hidden',       # OpenCode 支持
    'color',        # OpenCode 支持
    'temperature',  # OpenCode 支持
    'top_p',        # OpenCode 支持
    'steps',        # OpenCode 支持
    'disable',      # OpenCode 支持
}


def register(parser):
    """Register board subcommands on the given parser."""
    sub = parser.add_subparsers(dest='command', required=True, metavar='<command>')
    p = sub.add_parser('opencode', help='生成 OpenCode agents')
    p.add_argument('--dry-run', action='store_true')
    p.add_argument('--quiet', action='store_true', help='不打印每步进度 (只输出最终汇总)')
    p.add_argument('--root', help='显式指定项目根目录 (默认: 当前 git 仓库根)')
    p = sub.add_parser('status', help='查看 board 状态')
    p.add_argument('--root', default='', help='显式指定项目根目录 (默认: 当前 git 仓库根)')
    p = sub.add_parser('vscode', help='VS Code board 当前不支持')
    p.add_argument('--dry-run', action='store_true')
    p.add_argument('--root', default='')


def run(args):
    handlers = {'opencode': cmd_opencode, 'status': cmd_status, 'vscode': cmd_vscode}
    return handlers[args.command](args)


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Parse YAML-like frontmatter into a dict.

    louke agent 风格: `---\\nkey: value\\n\\nbody...` (无 closing `---`,
    以首个空行结尾). body 中的 `---` (markdown 水平线) 不影响 frontmatter 识别.

    嵌套结构支持:
    - `key: value` (字符串)
    - `key:` + 缩进的 `  - item` (列表, 用于 `models:`)
    - `key:` + 缩进的 `  subkey: value` (字典, 用于 `permission:`)
    """
    if not text.startswith('---\n'):
        return {}, text
    # louke agent 风格: 第一个空行就是 frontmatter 结束
    # (不能依赖 `\n---\n` 因为 body 可能含 markdown 水平线)
    lines = text[4:].splitlines()
    end_idx = 0
    while end_idx < len(lines) and lines[end_idx].strip():
        end_idx += 1
    raw = lines[:end_idx]
    body = '\n'.join(lines[end_idx:]).lstrip('\n')

    data: dict = {}
    i = 0
    while i < len(raw):
        line = raw[i]
        if not line.strip():
            i += 1
            continue
        stripped = line.lstrip()
        indent = len(line) - len(stripped)
        if indent != 0:
            i += 1
            continue
        if ':' not in stripped:
            i += 1
            continue
        key, value = stripped.split(':', 1)
        key = key.strip()
        value = value.strip()
        if value:
            data[key] = value
            i += 1
            continue
        # Container: collect children
        children: dict = {}
        child_list: list = []
        j = i + 1
        while j < len(raw):
            child_line = raw[j]
            if not child_line.strip():
                j += 1
                continue
            child_stripped = child_line.lstrip()
            child_indent = len(child_line) - len(child_stripped)
            if child_indent <= indent:
                break
            if child_stripped.startswith('- '):
                child_list.append(child_stripped[2:].strip())
            elif ':' in child_stripped:
                ck, cv = child_stripped.split(':', 1)
                children[ck.strip()] = cv.strip()
            j += 1
        if children:
            data[key] = children
        if child_list:
            data[key] = child_list
        i = j
    return data, body


def agent_source(root: Path) -> Path:
    for candidate in (root / '.louke/agents', root / 'agents'):
        if candidate.exists():
            return candidate
    from ._common import package_root
    return package_root() / 'agents'


def _render_passthrough_block(fm: dict, exclude: set[str]) -> str:
    """Render passthrough keys as YAML lines.

    `exclude` 应该包含 `description` / `mode` / `model` (已单独处理).
    返回的字符串以换行结尾, 如 'hidden: true\ncolor: blue\n'.
    """
    lines = []
    for key in PASSTHROUGH_KEYS:
        if key in exclude:
            continue
        if key not in fm:
            continue
        value = fm[key]
        if isinstance(value, dict):
            lines.append(f'{key}:')
            for k, v in value.items():
                lines.append(f'  {k}: {v}')
        elif isinstance(value, list):
            lines.append(f'{key}:')
            for item in value:
                lines.append(f'  - {item}')
        else:
            lines.append(f'{key}: {value}')
    return '\n'.join(lines) + ('\n' if lines else '')


def _require_project_root(args, command: str):
    """Resolve and validate the project root.

    Priority: --root arg > git_root() > error.
    Errors out (exit 1) if neither available, with hint about lk init.
    """
    from ._color import red, cyan
    explicit = getattr(args, 'root', None)
    if explicit:
        root = Path(explicit).resolve()
    else:
        root = git_root()
    if root is None:
        print(
            f'{red("error:")} {command} 需要 git 仓库 (或显式 --root).',
            file=sys.stderr,
        )
        print(
            f'  {cyan("hint:")} 在 louke 项目根目录 (有 .git/) 跑, 或 --root <path>',
            file=sys.stderr,
        )
        return None
    return Path(root)


def cmd_opencode(args):
    root = _require_project_root(args, 'lk board opencode')
    if root is None:
        return 1
    quiet = getattr(args, 'quiet', False)
    dry_run = getattr(args, 'dry_run', False)
    src = agent_source(root)
    dest_dir = root / '.opencode/agents'

    from ._color import (
        cyan, dim, yellow, green as g, red as r, bold, ok, fail, warn, info,
        Spinner,
    )

    if not quiet:
        print(f'{cyan("[1/5]")} 读取 source agents: {src}', flush=True)

    # 1. 收集 source agents
    source_files = []
    for fp in sorted(src.glob('*.md')):
        if fp.name in SKIP:
            continue
        source_files.append(fp)
    if not quiet:
        print(f'      发现 {len(source_files)} 个 agent prompt', flush=True)

    # 2. 解析 frontmatter, 收集所有 abstract model names
    from .models import opencode_models, auth_providers, model_costs
    parsed = []  # [(fp, fm, body)]
    abstract_models = set()
    for fp in source_files:
        text = fp.read_text(encoding='utf-8')
        fm, body = parse_frontmatter(text)
        parsed.append((fp, fm, body))
        models = fm.get('models') or []
        if isinstance(models, str):
            models = [models]
        for m in models:
            if m and not m.startswith(('ark/', 'openrouter/', 'opencode/', 'kimi/', 'aliyun/', 'minimax/', 'glm', 'xfei', 'deepseek')):
                abstract_models.add(m)

    if not quiet:
        print(f'{cyan("[2/5]")} 查询 opencode models + 解析 provider/model bind', flush=True)
    if not quiet:
        alias_user = (Path.home() / '.louke/models.json')
        alias_proj = root / '.louke/models.json'
        print(f'      用户级 alias: {alias_user}', flush=True)
        print(f'      项目级 alias: {alias_proj}', flush=True)
    # opencode models (subprocess, 可能慢) — spinner
    available: list[str] = []
    if abstract_models:
        if not quiet:
            print(f'      调用 opencode models (N={len(abstract_models)} abstract names)...',
                  flush=True)
        with Spinner('查询 opencode models'):
            try:
                available = opencode_models()
            except Exception as e:
                if not quiet:
                    print(f'      {warn(f"opencode models 失败: {e}")}', flush=True)
        if not quiet:
            print(f'      opencode models 返回 {len(available)} 个 model', flush=True)
    # auth providers + model costs
    if not quiet:
        print(f'{cyan("[3/5]")} 读取 auth providers + cost index', flush=True)
    with Spinner('读取 auth.json + cost index'):
        auth = auth_providers()
        costs = model_costs()
    if not quiet:
        sample = sorted(auth)[:3]
        more = '...' if len(auth) > 3 else ''
        print(f'      auth providers: {len(auth)} 个 ({sample}{more})', flush=True)
        free_count = sum(1 for v in costs.values() if v == (0, 0))
        print(f'      model costs: {len(costs)} 个, 其中 free {free_count} 个', flush=True)

    # 4. 解析每个 source 的 model, 写文件
    if not quiet:
        print(f'{cyan("[4/5]")} 解析 model bind + 写入 .opencode/agents/', flush=True)
    generated = []
    unbound_abstracts: list[tuple[str, str]] = []  # (agent_name, abstract)
    for fp, fm, body in parsed:
        name = str(fm.get('name') or fp.stem).lower()
        description = fm.get('description') or fp.stem
        mode = fm.get('mode') or 'all'
        models = fm.get('models') or []
        if isinstance(models, str):
            models = [models]
        model = resolve_model(models[0], root=root, models=available) if models else ''
        # 探测 unbound: 名字没 '/' (即仍是 abstract) + 没 alias
        if model and '/' not in model and not quiet:
            unbound_abstracts.append((name, model))
        passthrough = _render_passthrough_block(fm, exclude={'description', 'mode', 'model'})

        unknown_keys = set(fm.keys()) - {'name', 'description', 'mode', 'model', 'models'} - PASSTHROUGH_KEYS
        if unknown_keys and dry_run:
            for k in sorted(unknown_keys):
                print(f'{warn(f"dropped unknown frontmatter key {k!r} from {fp.name}")}',
                      flush=True)

        head = f'---\ndescription: {description}\nmode: {mode}\nmodel: {model}\n'
        if passthrough:
            out = head + passthrough + '---\n' + body
        else:
            out = head + '---\n' + body

        dest = dest_dir / f'{name}.md'
        generated.append(dest)
        if dry_run:
            if not quiet:
                marker = cyan('+')
                print(f'      {marker} {name:<12} {mode:<10} {dim("->")} {model}',
                      flush=True)
        else:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(out, encoding='utf-8')
            if not quiet:
                marker = g('✓')
                print(f'      {marker} {name:<12} {mode:<10} {dim("->")} {model}',
                      flush=True)

    if not dry_run and not quiet:
        print(f'{cyan("[5/5]")} 完成: 生成 {len(generated)} 个 OpenCode agent -> {dest_dir}',
              flush=True)
    # unbound 提示
    if unbound_abstracts and not quiet:
        print(f'\n{warn(f"{len(unbound_abstracts)} 个 abstract 未绑定 (output model 没 provider 前缀, OpenCode 用不起来):")}')
        for n, a in unbound_abstracts:
            print(f'  {dim("-")} {n}: {a}')
        print(f'\n{info("修复:")} {cyan("lk models bind <abstract> <provider>/<model>")} '
              f'或 {cyan("lk models bind <abstract>")} (交互式)')
        # 建议交互式
        if available:
            print(f'      交互式会列出 {len(available)} 个 opencode model 供选择')
    return 0


def _default_agent_status(root: Path) -> str:
    project = root / 'opencode.json'
    if project.exists():
        try:
            if json.loads(project.read_text(encoding='utf-8')).get('default_agent') == 'maestro':
                return 'maestro (project opencode.json)'
        except json.JSONDecodeError:
            pass
    global_cfg = Path.home() / '.config/opencode/opencode.json'
    if global_cfg.exists():
        try:
            if json.loads(global_cfg.read_text(encoding='utf-8')).get('default_agent') == 'maestro':
                return 'maestro (global opencode.json)'
        except json.JSONDecodeError:
            pass
    return '(not set)'


def cmd_status(args):
    root = _require_project_root(args, 'lk board status')
    if root is None:
        return 1
    files = list((root / '.opencode/agents').glob('*.md')) if (root / '.opencode/agents').exists() else []
    ok = any('model:' in f.read_text(encoding='utf-8', errors='replace').split('---', 2)[1] for f in files if f.exists())
    mark = '✓' if ok else '-'
    print(f'opencode    {mark}  (.opencode/agents/ — {len(files)} agents)')
    print(f'default_agent: {_default_agent_status(root)}')
    return 0


def cmd_vscode(args):
    print('lk board vscode is not supported in this release', flush=True)
    return 1
