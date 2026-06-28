"""Keeper commands - gate 检查.

Keeper 职责: per-commit gate (R-G-R + tests pass + lint + commit 格式) +
回归判断 (合并 Shield 的判断部分)。
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

from ._common import git


def register(subparsers):
    parser = subparsers.add_parser('keeper', help='gate 检查 (Keeper)')
    sub = parser.add_subparsers(dest='command', required=True, metavar='<command>')

    p = sub.add_parser('gate', help='per-commit gate (R-G-R + tests + lint + commit 格式)')
    p.add_argument('--commit-range', default='HEAD~1..HEAD', help='要检查的 commit 范围')
    p.add_argument('--tests', action='store_true', help='运行测试套件 (默认不跑, 仅检查 commit format)')

    p = sub.add_parser('regression', help='回归判断 (per-bug-fix, 对比修复前后)')
    p.add_argument('--baseline', default='main', help='基线 (修复前)')
    p.add_argument('--current', default='HEAD', help='当前 (修复后)')
    p.add_argument('--tests', action='store_true', help='跑测试做实际对比 (默认不跑, 仅 diff 范围)')


def run(args):
    handlers = {
        'gate': cmd_gate,
        'regression': cmd_regression,
    }
    return handlers.get(args.command, lambda _: 1)(args) or 0


def check_commit_messages(commit_range: str, cwd: Path = None) -> list:
    """检查 commit message 格式 - R-G-R 模式 (test: red / feat: green / refactor:).

    严格匹配 devon.py 的 RGR_PREFIX; 非 RGR 的提交 (e2e/docs/chore/fix)
    用各自前缀。
    """
    rc, out, _ = git('log', '--format=%H %s', commit_range, cwd=cwd)
    if rc != 0:
        return [{'error': f'git log failed: {out}', 'severity': 'critical'}]

    # 与 devon.RGR_PREFIX + 非 RGR 提交前缀保持一一对应
    # (旧版 'feat: green' / 'fix: green' 是冗余 — 'feat:'/'fix:' 已 startswith 匹配)
    valid_prefixes = (
        'test: red',     # Devon R-G-R 阶段 1
        'feat: green',   # Devon R-G-R 阶段 2 (与 'feat:' 区分, 强制 R-G-R 规范)
        'refactor:',     # Devon R-G-R 阶段 3
        'e2e:',          # Shield 提交
        'fix:',          # bug fix (注意: 'feat: green' 不会被 'feat:' 误匹配, 因为 'feat: green' startswith 'feat:' 也 OK,
                         #  但反过来 'feat: something' 不会 startswith 'feat: green', 区分了 R-G-R)
        'docs:',         # 文档
        'chore:',        # 杂项
    )

    findings = []
    for line in out.strip().split('\n'):
        if not line.strip():
            continue
        parts = line.split(' ', 1)
        if len(parts) != 2:
            continue
        sha, subject = parts
        if not any(subject.startswith(p) for p in valid_prefixes):
            findings.append({
                'commit': sha[:8],
                'subject': subject,
                'severity': 'medium',
                'description': (
                    f'commit 格式不规范 (需以 {" / ".join(valid_prefixes)} 之一开头; '
                    f'Red-Green 阶段必须严格用 "test: red" / "feat: green")'
                ),
            })
    return findings


def cmd_gate(args):
    """per-commit gate 检查: commit 格式 + (可选) 测试套件 + lint."""
    cwd = Path.cwd()
    print(f"=== Keeper Gate ===")
    print(f"Commit range: {args.commit_range}")
    print(f"Run tests: {args.tests}")
    print()

    # 1. Commit message format
    findings = check_commit_messages(args.commit_range, cwd=cwd)
    print(f"--- Commit Message Format ({len(findings)} findings) ---")
    for f in findings:
        sev = f.get('severity', '?')
        if 'error' in f:
            print(f"[{sev}] ERROR: {f['error']}")
        else:
            print(f"[{sev}] {f.get('commit', '?')} - {f.get('subject', '?')}")
            print(f"   {f.get('description', '')}")

    has_blocking = any(f.get('severity') == 'critical' for f in findings)
    if has_blocking:
        print("\n→ 拒绝 (有 critical 问题)")
        return 1

    # 2. Optional test run
    if args.tests:
        print(f"\n--- Running Tests ---")
        result = subprocess.run(
            ['python3', '-m', 'pytest', 'tests/', '-x', '--tb=short', '-q'],
            cwd=cwd, capture_output=True, text=True,
        )
        print(result.stdout[-500:] if len(result.stdout) > 500 else result.stdout)
        if result.returncode != 0:
            print("[high] 测试套件失败")
            print("\n→ 拒绝 (测试失败)")
            return 1
        print("[ok] 测试套件通过")

    print(f"\n→ gate 通过 (commit 格式检查{'+ 测试通过' if args.tests else ''})")
    return 0


def cmd_regression(args):
    """回归判断: 对比 baseline 与 current 测试结果."""
    cwd = Path.cwd()
    print(f"=== Keeper Regression Check ===")
    print(f"Baseline: {args.baseline}")
    print(f"Current: {args.current}")
    print()

    rc, diff_out, _ = git('diff', '--name-only', args.baseline, args.current, cwd=cwd)
    if rc != 0:
        print(f"git diff failed")
        return 1

    changed = [f for f in diff_out.strip().split('\n') if f]
    print(f"Changed files: {len(changed)}")

    # 分析变更范围
    test_changes = [f for f in changed if 'test' in f.lower()]
    code_changes = [f for f in changed if 'test' not in f.lower()]

    print(f"  Test changes:  {len(test_changes)}")
    print(f"  Code changes:  {len(code_changes)}")

    # 范围评估
    findings = []

    # 检查: 修改的文件数是否合理 (bug fix 应小范围)
    if len(code_changes) > 5:
        findings.append({
            'severity': 'medium',
            'description': f'Bug fix 改了 {len(code_changes)} 个代码文件 (建议 ≤5, 超出可能引入新回归)',
        })

    # 检查: 是否有不相关的代码变更
    for f in changed:
        # 这些文件通常不在 bug fix 范围
        if any(p in f for p in ('package.json', 'requirements.txt', 'pyproject.toml',
                                  'Cargo.toml', 'go.mod')):
            findings.append({
                'severity': 'high',
                'description': f'依赖文件 {f} 在 bug fix 中被改 (可能是版本变化, 需审查)',
            })

    if args.tests:
        # 跑测试, 对比结果
        print(f"\n--- Running Tests on Current ---")
        result = subprocess.run(
            ['python3', '-m', 'pytest', 'tests/', '--tb=short', '-q'],
            cwd=cwd, capture_output=True, text=True,
        )
        if result.returncode != 0:
            findings.append({
                'severity': 'critical',
                'description': '当前测试套件失败 (回归测试不通过)',
            })
        else:
            print("[ok] 当前测试通过")

    print(f"\n=== Findings ({len(findings)}) ===")
    for f in findings:
        print(f"[{f['severity']}] {f['description']}")

    if any(f['severity'] in ('critical', 'high') for f in findings):
        print("\n→ 拒绝 (有 critical/high 问题)")
        return 1
    print("\n→ 回归检查通过")
    return 0