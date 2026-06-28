"""Librarian commands - wiki 健康维护.

Librarian 职责: raw → wiki 蒸馏、index 维护、lint 健康检查。
"""
import argparse
import subprocess
import sys
from pathlib import Path


def register(subparsers):
    parser = subparsers.add_parser('librarian', help='wiki 健康维护 (Librarian)')
    sub = parser.add_subparsers(dest='command', required=True, metavar='<command>')

    # distill: raw → wiki 蒸馏
    p = sub.add_parser('distill', help='raw 会话记录 → wiki 蒸馏')
    p.add_argument('--source', default='.specforge/raw/',
                   help='raw 路径 (默认 .specforge/raw/)')
    p.add_argument('--target', default='.specforge/wiki/pages/',
                   help='wiki 路径 (默认 .specforge/wiki/pages/)')

    # lint: wiki 健康检查 (orphaned pages, broken links)
    p = sub.add_parser('lint', help='wiki 健康检查 (orphaned pages, broken links)')
    p.add_argument('--wiki', default='.specforge/wiki/')

    # rebuild-index: 重建 wiki 导航目录
    p = sub.add_parser('rebuild-index', help='重建 wiki 导航目录 index.md')
    p.add_argument('--wiki', default='.specforge/wiki/')


def run(args):
    handlers = {
        'distill': cmd_distill,
        'lint': cmd_lint,
        'rebuild-index': cmd_rebuild_index,
    }
    return handlers.get(args.command, lambda _: 1)(args) or 0


def cmd_distill(args):
    """Distill raw → wiki — 占位."""
    print(f"distill: {args.source} → {args.target} (to be implemented)")
    return 1


def cmd_lint(args):
    """Wiki lint — 占位."""
    print(f"lint: {args.wiki} (to be implemented)")
    return 1


def cmd_rebuild_index(args):
    """Rebuild wiki index — 占位."""
    print(f"rebuild-index: {args.wiki} (to be implemented)")
    return 1