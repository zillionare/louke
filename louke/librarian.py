"""Librarian commands - wiki 健康维护.

Librarian 职责: raw → wiki 蒸馏、index 维护、lint 健康检查。
"""
import argparse
import re
import subprocess
import sys
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

from ._common import git


CACHE_PATH = Path.cwd() / '.louke' / 'wiki' / '.cache.toml'


def register(subparsers):
    parser = subparsers.add_parser('librarian', help='wiki 健康维护 (Librarian)')
    sub = parser.add_subparsers(dest='command', required=True, metavar='<command>')

    p = sub.add_parser('distill', help='raw → wiki 蒸馏 (按 LLM, lk 仅准备)')
    p.add_argument('--source', default='.louke/raw/',
                   help='raw 路径 (默认 .louke/raw/)')
    p.add_argument('--target', default='.louke/wiki/pages/',
                   help='wiki 路径 (默认 .louke/wiki/pages/)')

    p = sub.add_parser('lint', help='wiki 健康检查 (broken links, orphaned pages)')
    p.add_argument('--wiki', default='.louke/wiki/')

    p = sub.add_parser('rebuild-index', help='重建 wiki 导航目录')
    p.add_argument('--wiki', default='.louke/wiki/')

    p = sub.add_parser('compact', help='cron 入口: 准备 distillation bundle + 更新 last_distill')
    p.add_argument('--dry-run', action='store_true', help='仅打印计划, 不写文件')
    p.add_argument('--threshold-tokens', type=int, default=50_000, help='M0/M1 切换阈值 (默认 50K)')
    p.add_argument('--m2-threshold', type=int, default=200_000, help='M1/M2 切换阈值 (默认 200K)')

    p = sub.add_parser('rewrite', help='LLM 整体重写 pages/, 通过 opencode run --agent librarian')
    p.add_argument('--model', default='', help='指定模型 ID (优先级最高, 透传给 opencode run --model)')
    p.add_argument('--model-from-config', action='store_true', help='走 lk models bind (第二优先级)')
    p.add_argument('--full', action='store_true', help='全量重写 (忽略默认增量, FR-0140.5)')
    p.add_argument('--dry-run', action='store_true', help='仅打印将调用的 opencode 命令')


def run(args):
    handlers = {
        'distill': cmd_distill,
        'lint': cmd_lint,
        'rebuild-index': cmd_rebuild_index,
        'compact': cmd_compact,
        'rewrite': cmd_rewrite,
    }
    return handlers.get(args.command, lambda _: 1)(args) or 0


# ---- .cache.toml (last_distill + SHA256 增量索引) ----

def _read_cache() -> dict:
    if not CACHE_PATH.exists():
        return {}
    try:
        import tomllib
    except ImportError:
        try:
            import tomli as tomllib  # type: ignore
        except ImportError:
            return {}
    try:
        with open(CACHE_PATH, 'rb') as f:
            return tomllib.load(f)
    except Exception:
        return {}


def _write_cache(data: dict) -> None:
    try:
        import tomllib
    except ImportError:
        try:
            import tomli as tomllib  # type: ignore
        except ImportError:
            return
    try:
        import tomli_w
    except ImportError:
        # 写入端无 tomli_w: 退回手工构造 (避免新增依赖)
        lines = []
        for k, v in data.items():
            if isinstance(v, str):
                lines.append(f'{k} = "{v}"')
            elif isinstance(v, dict):
                lines.append(f'[{k}]')
                for sk, sv in v.items():
                    if isinstance(sv, str):
                        lines.append(f'{sk} = "{sv}"')
                    else:
                        lines.append(f'{sk} = {sv}')
            else:
                lines.append(f'{k} = {v}')
        CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        CACHE_PATH.write_text('\n'.join(lines) + '\n')
        return
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CACHE_PATH, 'wb') as f:
        tomli_w.dump(data, f)


def cmd_distill(args):
    """Distill raw → wiki — LLM 蒸馏的 lk 包装.

    LLM 蒸馏是 LLM 的事, lk 仅:
    1. 扫描 raw/ 下 status=resolved 的会话
    2. 生成待蒸馏清单 (供 LLM 阅读)
    3. LLM 蒸馏后, lk 写入 wiki/

    当前为占位: 仅扫描 + 打印清单.
    """
    cwd = Path.cwd()
    raw_dir = cwd / args.source
    if not raw_dir.exists():
        print(f"raw dir 不存在: {raw_dir}")
        return 1

    print(f"=== Distill (scan) ===")
    print(f"Source: {raw_dir}")

    resolved = []
    for fp in sorted(raw_dir.rglob('*.md')):
        try:
            content = fp.read_text(encoding='utf-8', errors='replace')
        except (OSError, PermissionError):
            continue
        if re.search(r'^status:\s*resolved', content, re.MULTILINE):
            resolved.append(fp)

    print(f"待蒸馏条目 (status=resolved): {len(resolved)}")
    for fp in resolved:
        print(f"  - {fp.relative_to(cwd)}")

    print(f"\n下一步: LLM 阅读这些条目, 蒸馏后用 lk librarian write <wiki-page> 写入")
    return 0


def cmd_lint(args):
    """Wiki lint - 找 broken links 和 orphaned pages."""
    cwd = Path.cwd()
    wiki_dir = cwd / args.wiki
    if not wiki_dir.exists():
        print(f"wiki dir 不存在: {wiki_dir}")
        return 1

    print(f"=== Wiki Lint ===")
    print(f"Wiki: {wiki_dir}")

    pages = list(wiki_dir.rglob('*.md'))
    print(f"Pages: {len(pages)}")

    # 找所有 [[wikilink]] 引用
    all_refs = set()
    for p in pages:
        try:
            content = p.read_text(encoding='utf-8', errors='replace')
        except (OSError, PermissionError):
            continue
        refs = re.findall(r'\[\[([^\]]+)\]\]', content)
        all_refs.update(refs)

    # 找所有页面名 (不含 .md)
    page_names = {p.stem for p in pages}

    # broken links
    broken = [r for r in all_refs if r not in page_names]
    print(f"\n[broken links] {len(broken)}")
    for b in broken[:10]:
        print(f"  - [[{b}]]")

    # orphaned pages (没有任何 wikilink 引用)
    referenced = set()
    for p in pages:
        try:
            content = p.read_text(encoding='utf-8', errors='replace')
        except (OSError, PermissionError):
            continue
        for r in re.findall(r'\[\[([^\]]+)\]\]', content):
            referenced.add(r)
    orphaned = page_names - referenced
    print(f"\n[orphaned pages] {len(orphaned)}")
    for o in list(orphaned)[:10]:
        print(f"  - {o}.md")

    if broken or orphaned:
        return 1
    print("\n→ wiki 健康")
    return 0


def cmd_rebuild_index(args):
    """重建 wiki 导航 index.md."""
    cwd = Path.cwd()
    wiki_dir = cwd / args.wiki
    if not wiki_dir.exists():
        return 1

    pages = sorted(wiki_dir.rglob('*.md'))
    print(f"=== Rebuild Index ===")
    print(f"Pages: {len(pages)}")

    lines = ['# Wiki Index', '', f'共 {len(pages)} 个页面', '']
    for p in pages:
        rel = p.relative_to(wiki_dir)
        lines.append(f'- [[{p.stem}]] (`{rel}`)')

    index_path = wiki_dir / 'index.md'
    index_path.write_text('\n'.join(lines) + '\n')
    print(f"✓ Index rebuilt: {index_path}")
    return 0


def _scan_resolved_raw(since: str, until: str) -> tuple[list, list]:
    """扫描 raw/ 下 status=resolved + 日期在 [since, until] 范围内的条目.

    返回 (matched, skipped_no_date).
    - matched: 满足条件的 (file_path, file_date, content)
    - skipped_no_date: 无 date 字段被跳过的 (file_path,)
    """
    cwd = Path.cwd()
    raw_dir = cwd / '.louke/raw/'
    if not raw_dir.exists():
        return [], []

    matched = []
    skipped = []
    for fp in sorted(raw_dir.rglob('*.md')):
        try:
            content = fp.read_text(encoding='utf-8', errors='replace')
        except (OSError, PermissionError):
            continue

        if not re.search(r'^status:\s*resolved', content, re.MULTILINE):
            continue

        date_m = re.search(r'^date:\s*(\d{4}-\d{2}-\d{2})', content, re.MULTILINE)
        file_date = date_m.group(1) if date_m else ''
        if not file_date:
            # FR-0080 P1-8: 无 date 字段 → 跳过 + warning
            skipped.append(fp)
            continue
        if since and file_date < since:
            continue
        if until and file_date > until:
            continue
        matched.append((fp, file_date, content))
    return matched, skipped


def _estimate_tokens(items: list) -> int:
    """粗略估算 token 数 (~4 chars / token)."""
    return sum(len(c) for _, _, c in items) // 4


def _cleanup_old_bundles(wiki_dir: Path) -> int:
    """删除 wiki_dir 下所有 .compact-bundle*.md (FR-0140.2 P0-3 / P1-4).

    Bundle 是 compact 的中间产物, 不持久化. 每次 compact 开始清理.
    返回删除数量.
    """
    count = 0
    for f in wiki_dir.glob('.compact-bundle*.md'):
        try:
            f.unlink()
            count += 1
        except OSError:
            pass
    return count


def _write_bundle(bundle_path: Path, items: list, mode: str, existing_pages: str, dry_run: bool) -> None:
    """写入单个 bundle 文件."""
    if dry_run:
        return
    total_chars = sum(len(c) for _, _, c in items)
    lines = [
        '# Librarian Compact Bundle',
        f'> Generated: {date.today().isoformat()}',
        f'> Mode: {mode}',
        f'> Raw entries: {len(items)}',
        f'> Total chars: {total_chars}',
        '',
        '## Raw Sessions (append-only history)',
        '',
    ]
    for fp, file_date, content in items:
        lines.append(f'### {fp.name} ({file_date})')
        lines.append('')
        lines.append(content)
        lines.append('')
    lines.extend([
        '## Current Pages (to be REWRITTEN, not patched)',
        '',
        existing_pages or '(empty)',
        '',
        '## Instructions',
        '',
        '重写 pages/. 保留仍成立决策; 删除/更新过时的; 补充新出现的主题.',
        '每条 wiki 决策必须能从 raw 中找到依据 (quote dialogue 语法, 详见 v0.4-004).',
        '',
    ])
    bundle_path.write_text('\n'.join(lines))


def cmd_compact(args):
    """cron 入口: 准备 distillation bundle + 更新 last_distill.

    FR-0080: 删除 cmd_from_raw + cmd_daily; 合并为 cmd_compact.
    FR-0140: 按 token 量自动选模式 M0/M1/M2.
    FR-0140.2 P0-3 / P1-4: 进入时清理旧 bundle.
    FR-0080 P1-8: 无 date 字段的 raw 跳过 + warning.
    """
    cwd = Path.cwd()
    wiki_dir = cwd / '.louke' / 'wiki'
    wiki_pages_dir = wiki_dir / 'pages'
    raw_dir = cwd / '.louke' / 'raw'

    if not raw_dir.exists():
        print('raw dir 不存在: .louke/raw/', file=sys.stderr)
        return 1
    wiki_pages_dir.mkdir(parents=True, exist_ok=True)

    # 1. 清理旧 bundle (P0-3 / P1-4)
    if not args.dry_run:
        cleaned = _cleanup_old_bundles(wiki_dir)
        if cleaned:
            print(f'[compact] 清理 {cleaned} 个旧 bundle')

    # 2. 计算窗口
    cache = _read_cache()
    last = cache.get('last_distill', '')
    today = date.today()
    yesterday = (today - timedelta(days=1)).isoformat()
    if not last:
        last = '1970-01-01'
        print(f'[compact] cache.last_distill 未设置, 从 {last} 开始处理所有历史 raw')
    else:
        print(f'[compact] 上次蒸馏: {last}')
    print(f'[compact] 蒸馏窗口: [{last}, {yesterday}]')

    # 3. 扫描 raw
    matched, skipped_no_date = _scan_resolved_raw(since=last, until=yesterday)
    if skipped_no_date:
        print(f'[compact] WARN: {len(skipped_no_date)} 个 raw 条目无 date 字段, 已跳过:')
        for fp in skipped_no_date[:10]:
            print(f'  - {fp.relative_to(cwd)}')
        if len(skipped_no_date) > 10:
            print(f'  ... (+{len(skipped_no_date) - 10} more)')

    if not matched:
        print('[compact] 无新 raw 待蒸馏, 零输出')
        # 即使零输出, 也更新 last_distill 以保持幂等 (dry-run 不写)
        if not args.dry_run:
            cache = _read_cache()
            cache['last_distill'] = yesterday
            _write_cache(cache)
        return 0

    # 4. 读取现有 pages
    existing_pages = ''
    if wiki_pages_dir.exists():
        for fp in sorted(wiki_pages_dir.glob('*.md')):
            try:
                existing_pages += f'\n### {fp.stem}\n\n{fp.read_text(encoding="utf-8", errors="replace")}\n'
            except OSError:
                pass

    # 5. 估算 token + 选模式
    total_tokens = _estimate_tokens(matched)
    m1_thresh = args.threshold_tokens
    m2_thresh = args.m2_threshold
    print(f'[compact] token 估算: {total_tokens} (M0≤{m1_thresh} < M1≤{m2_thresh} < M2)')

    if total_tokens <= m1_thresh:
        mode = 'M0_incremental'
    elif total_tokens <= m2_thresh:
        mode = 'M1_full'
        print(f'[compact] WARN: 建议 --model gemini-1.5-pro (1M context) 或 claude-sonnet-4 (200K)')
    else:
        mode = 'M2_map_reduce'
        print(f'[compact] M2: 按月分块, 将产出多个 bundle + merged')

    # 6. 写 bundle(s)
    if mode == 'M2_map_reduce':
        from collections import defaultdict
        grouped = defaultdict(list)
        for fp, file_date, content in matched:
            month = file_date[:7]  # YYYY-MM
            grouped[month].append((fp, file_date, content))
        for month, items in sorted(grouped.items()):
            bundle = wiki_dir / f'.compact-bundle-{month}.md'
            _write_bundle(bundle, items, f'M2:{mode}', existing_pages, args.dry_run)
            if not args.dry_run:
                print(f'  + {bundle.name} ({len(items)} entries, ~{_estimate_tokens(items)} tokens)')
        merged = wiki_dir / '.compact-bundle-merged.md'
        merge_lines = [
            '# Librarian Compact Bundle (M2 merged)',
            f'> Generated: {date.today().isoformat()}',
            f'> Bundles: {sorted(grouped.keys())}',
            '',
            '## Sub-bundles',
            '',
        ]
        for month in sorted(grouped.keys()):
            merge_lines.append(f'- .compact-bundle-{month}.md')
        _write_bundle(merged, matched, f'M2:merge', existing_pages, args.dry_run)
        if not args.dry_run:
            print(f'  + {merged.name} (references {len(grouped)} sub-bundles)')
    else:
        bundle = wiki_dir / '.compact-bundle.md'
        _write_bundle(bundle, matched, mode, existing_pages, args.dry_run)
        if not args.dry_run:
            print(f'  + {bundle.name} ({len(matched)} entries, ~{total_tokens} tokens)')

    # 7. 更新 last_distill (幂等: 跑过一次就推进, 无论是否新增)
    if not args.dry_run:
        cache = _read_cache()
        cache['last_distill'] = yesterday
        _write_cache(cache)
        print(f'[compact] → .cache.last_distill: {last or "(unset)"} → {yesterday}')

    return 0


def cmd_rewrite(args):
    """LLM 整体重写 pages/, 通过 opencode run --agent librarian.

    FR-0130: shell-out 到 OpenCode CLI, 不直接调 LLM SDK.
    FR-0140.4 P1-7: 模型优先级链 --model > --model-from-config > frontmatter.
    """
    cwd = Path.cwd()
    wiki_dir = cwd / '.louke' / 'wiki'
    bundle_main = wiki_dir / '.compact-bundle.md'
    bundle_merged = wiki_dir / '.compact-bundle-merged.md'

    if not bundle_main.exists() and not bundle_merged.exists():
        print('error: .compact-bundle.md 不存在, 请先跑 lk librarian compact', file=sys.stderr)
        return 1

    # 选择 bundle: M2 用 merged, 其他用 main
    if bundle_merged.exists() and not args.full:
        bundle = bundle_merged
        mode_hint = 'M2_map_reduce'
    else:
        bundle = bundle_main
        mode_hint = 'M0/M1_full'

    # 模型优先级链: --model > --model-from-config > frontmatter (FR-0140.4)
    model_flag = []
    if args.model:
        model_flag = ['--model', args.model]
    elif args.model_from_config:
        # 通过 louke models bind 取当前模型 (FR-0140.4 第二优先级)
        try:
            bound = subprocess.run(
                ['lk', 'models', 'bind', '--get-current'],
                capture_output=True, text=True, check=False,
            )
            if bound.returncode == 0 and bound.stdout.strip():
                model_flag = ['--model', bound.stdout.strip()]
        except FileNotFoundError:
            pass
    # 否则: 不传 --model, OpenCode 用 frontmatter models: 第一项

    if args.dry_run:
        cmd_preview = ['opencode', 'run', '--agent', 'librarian']
        cmd_preview += model_flag
        cmd_preview += ['--', '<prompt>']
        print(f'[dry-run] {bundle.name} ({mode_hint})')
        print(f'[dry-run] cmd: {" ".join(cmd_preview)}')
        return 0

    prompt = f'''
你是 Librarian subagent, 处于 CLI 批处理模式 (通过 `opencode run --agent librarian` 启动).

任务: 基于 raw 整体重写 wiki pages/.

输入:
1. 读 {bundle} (含 raw 全文 + 现有 pages/ + 蒸馏指令, 模式: {mode_hint})
2. 读 .louke/wiki/pages/ 全部现存页面

输出:
1. **整体重写** .louke/wiki/pages/ (不是 patch):
   - 保留仍成立的决策
   - 删除/合并过时的
   - 补充新出现的主题
   - 每条 wiki 决策必须能从 raw 中找到依据 (quote dialogue 语法, 详见 v0.4-004)
2. 跑 `lk librarian rebuild-index` 重建 index.md
3. 跑 `lk librarian lint` 健康检查; 如有 broken links / 缺失 frontmatter 自愈

完成后 exit 0. 如 lint 不过自愈不了 exit 1.
'''
    cmd = ['opencode', 'run', '--agent', 'librarian']
    cmd += model_flag
    cmd += ['--', prompt]
    print(f'[rewrite] shell-out: bundle={bundle.name} mode={mode_hint} model={"<default>" if not model_flag else model_flag[1]}')
    rc = subprocess.run(cmd).returncode
    return rc
