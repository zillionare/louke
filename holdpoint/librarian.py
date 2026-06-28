"""Librarian commands - wiki 健康维护.

Librarian 职责: raw → wiki 蒸馏、index 维护、lint 健康检查。
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

from ._common import git


def register(subparsers):
    parser = subparsers.add_parser('librarian', help='wiki 健康维护 (Librarian)')
    sub = parser.add_subparsers(dest='command', required=True, metavar='<command>')

    p = sub.add_parser('distill', help='raw → wiki 蒸馏 (按 LLM, hp 仅准备)')
    p.add_argument('--source', default='.holdpoint/raw/',
                   help='raw 路径 (默认 .holdpoint/raw/)')
    p.add_argument('--target', default='.holdpoint/wiki/pages/',
                   help='wiki 路径 (默认 .holdpoint/wiki/pages/)')

    p = sub.add_parser('lint', help='wiki 健康检查 (broken links, orphaned pages)')
    p.add_argument('--wiki', default='.holdpoint/wiki/')

    p = sub.add_parser('rebuild-index', help='重建 wiki 导航目录')
    p.add_argument('--wiki', default='.holdpoint/wiki/')

    p = sub.add_parser('from-raw', help='从 raw 提取 status=resolved 的会话, 蒸馏到 wiki (简单实现)')
    p.add_argument('--since', default='', help='只处理此日期之后的, 例 2026-06-27')


def run(args):
    handlers = {
        'distill': cmd_distill,
        'lint': cmd_lint,
        'rebuild-index': cmd_rebuild_index,
        'from-raw': cmd_from_raw,
    }
    return handlers.get(args.command, lambda _: 1)(args) or 0


def cmd_distill(args):
    """Distill raw → wiki — LLM 蒸馏的 hp 包装.

    LLM 蒸馏是 LLM 的事, hp 仅:
    1. 扫描 raw/ 下 status=resolved 的会话
    2. 生成待蒸馏清单 (供 LLM 阅读)
    3. LLM 蒸馏后, hp 写入 wiki/

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

    print(f"\n下一步: LLM 阅读这些条目, 蒸馏后用 hp librarian write <wiki-page> 写入")
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


def cmd_from_raw(args):
    """从 raw 提取 status=resolved 条目, 写为 wiki 草稿.

    简单实现: 不调用 LLM, 仅按 frontmatter 状态过滤 + 按日期归档.
    LLM 蒸馏由后续流程调用 hp librarian distill.
    """
    cwd = Path.cwd()
    raw_dir = cwd / '.holdpoint/raw/'
    wiki_pages_dir = cwd / '.holdpoint/wiki/pages/'

    if not raw_dir.exists():
        print(f"raw dir 不存在: {raw_dir}")
        return 1
    wiki_pages_dir.mkdir(parents=True, exist_ok=True)

    print(f"=== From Raw (auto-promote resolved) ===")
    count = 0
    for fp in sorted(raw_dir.rglob('*.md')):
        try:
            content = fp.read_text(encoding='utf-8', errors='replace')
        except (OSError, PermissionError):
            continue

        if not re.search(r'^status:\s*resolved', content, re.MULTILINE):
            continue

        # 日期过滤
        if args.since:
            date_m = re.search(r'^date:\s*(\d{4}-\d{2}-\d{2})', content, re.MULTILINE)
            if date_m and date_m.group(1) < args.since:
                continue

        # 简单搬运 (不调用 LLM)
        wiki_target = wiki_pages_dir / f"{fp.stem}.md"
        wiki_target.write_text(content)
        count += 1
        print(f"  + {wiki_target.relative_to(cwd)}")

    print(f"\n✓ Promoted {count} entries (无 LLM 蒸馏, 仅按状态+日期归档)")
    print(f"  下一步: hp librarian distill 调用 LLM 蒸馏这些 raw 草稿")
    return 0