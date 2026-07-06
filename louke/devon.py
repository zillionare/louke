"""Devon commands - R-G-R 编码.

Devon 职责: Red → Green → Refactor 循环, 单元测试驱动。
lk 提供: 运行测试 + 按 R-G-R 规范 commit。
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

from ._common import git


RGR_PREFIX = {
    ('feature', 'green'): 'feat: green',
    ('feature', 'refactor'): 'refactor:',
    ('fix', 'green'): 'fix: green',
    ('fix', 'refactor'): 'refactor:',
}


def register(subparsers):
    parser = subparsers.add_parser('devon', help='R-G-R 编码 (Devon)')
    sub = parser.add_subparsers(dest='command', required=True, metavar='<command>')

    p = sub.add_parser('commit-rgr', help='按 R-G-R 规范 commit (FR-0580 默认 no-push)')
    p.add_argument('--phase', required=True, help='R-G-R 阶段 (green/refactor); red 阶段已废弃')
    p.add_argument('--message', required=True, help='commit message 主体')
    p.add_argument('--issue', required=True, help='当前处理的 GitHub issue 编号')
    p.add_argument('--label', default='', help='强制指定 issue 类型 (feature/fix); 默认读取 issue labels')
    p.add_argument('--push', action='store_true', help='显式 push（默认 no-push）')


def run(args):
    handlers = {
        'commit-rgr': cmd_commit_rgr,
    }
    return handlers.get(args.command, lambda _: 1)(args) or 0


def _infer_issue_label(issue: str) -> str:
    """读取 GitHub issue labels，推断是 feature 还是 fix。

    未找到 label 或读取失败时默认返回 'feature'（louke 主流程以 FR 为主）。
    """
    try:
        out = subprocess.check_output(
            ['gh', 'issue', 'view', issue, '--json', 'labels'],
            text=True,
            stderr=subprocess.DEVNULL,
            timeout=30,
        )
        data = json.loads(out)
        labels = {label.get('name', '').lower() for label in data.get('labels', [])}
    except Exception:
        labels = set()

    if 'bug' in labels or 'fix' in labels:
        return 'fix'
    if 'feature' in labels or 'fr' in labels or 'enhancement' in labels:
        return 'feature'
    # 无明确 label 时默认 FR，不阻塞流程
    return 'feature'


def cmd_commit_rgr(args):
    """FR-0580: 默认 no-push；--push 才 push；自动从 issue label 推断前缀。"""
    if args.phase == 'red':
        print('error: --phase red 已废弃 (v0.7-001); Red 阶段不再 commit', file=sys.stderr)
        return 1
    if args.phase not in ('green', 'refactor'):
        print(f"error: --phase must be 'green' or 'refactor', got {args.phase!r}", file=sys.stderr)
        return 1

    cwd = Path.cwd()
    label = args.label.lower() if args.label else _infer_issue_label(args.issue)
    if label not in ('feature', 'fix'):
        print(f"warning: unknown label {label!r}, falling back to 'feature'", file=sys.stderr)
        label = 'feature'

    prefix = RGR_PREFIX[(label, args.phase)]
    body = ' – '.join([prefix, f'#{args.issue}', args.message])
    if args.phase == 'green':
        body += f'\n\nCloses #{args.issue}'

    print("=== R-G-R Commit ===")
    print(f"Phase:  {args.phase}")
    print(f"Label:  {label}")
    print(f"Prefix: {prefix}")
    print(f"Body:\n{body}")
    print()

    rc, out, _ = git('commit', '-m', body, cwd=cwd)
    if rc != 0:
        print(f"git commit failed: {out}", file=sys.stderr)
        return 1

    rc, sha, _ = git('rev-parse', '--short', 'HEAD', cwd=cwd)
    print(f"✓ Committed: {sha}")
    if args.push:
        rc, out, _ = git('push', cwd=cwd)
        if rc != 0:
            print(f"git push failed: {out}", file=sys.stderr)
            return rc
        print(f"✓ Pushed: {sha}")
    else:
        print('(push skipped; pass --push to push)')
    return 0
