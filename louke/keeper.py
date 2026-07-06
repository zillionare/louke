"""Keeper commands - gate 检查.

Keeper 职责: per-commit gate (R-G-R 顺序 + commit 格式 + AC trace + 反模式扫描) +
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

    p = sub.add_parser('gate', help='per-commit gate (format + R-G-R 顺序 + AC trace + 反模式扫描)')
    p.add_argument('--commit-range', default='HEAD~1..HEAD', help='要检查的 commit 范围')
    p.add_argument('--tests', action='store_true', help='已废弃 (v0.7-001)')
    p.add_argument('--lint', action='store_true', help='已废弃 (v0.7-001)')
    p.add_argument('--typecheck', action='store_true', help='已废弃 (v0.7-001)')
    p.add_argument('--skip-ac-trace', action='store_true', help='跳过 AC trace 校验')
    p.add_argument('--skip-anti-pattern', action='store_true', help='跳过反模式扫描')

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
    """检查 commit message 格式 - R-G-R 模式 (test: red / feat: green / refactor:)."""
    rc, out, _ = git('log', '--format=%H %s', commit_range, cwd=cwd)
    if rc != 0:
        return [{'error': f'git log failed: {out}', 'severity': 'critical'}]

    valid_prefixes = (
        'test: red',
        'feat: green',
        'fix: green',
        'refactor:',
        'fix:',
        'docs:',
        'chore:',
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


# ---- FR-0590: R-G-R 顺序校验 ----

PHASE_ORDER = {'test: red': 1, 'feat: green': 2, 'fix: green': 2, 'refactor:': 3}


def check_rgr_order(commit_range: str, cwd: Path = None) -> list:
    """同 cycle 内 test: red → feat: green → refactor 顺序不允许跳跃或回退。"""
    rc, out, _ = git('log', '--reverse', '--format=%s', commit_range, cwd=cwd)
    if rc != 0:
        return [{'error': f'git log failed: {out}', 'severity': 'critical'}]
    findings = []
    last_phase = 0
    for line in out.strip().split('\n'):
        s = line.strip()
        for prefix, order in PHASE_ORDER.items():
            if s.startswith(prefix):
                if order < last_phase:
                    findings.append({
                        'subject': s,
                        'severity': 'high',
                        'description': f'R-G-R order violation: {s} after phase {last_phase}',
                    })
                last_phase = max(last_phase, order)
                break
    return findings


def check_test_before_impl(commit_range: str, cwd: Path = None) -> list:
    """cycle 内 test: red 必须先于 green (feat: green / fix: green 等价)。"""
    rc, out, _ = git('log', '--reverse', '--format=%s', commit_range, cwd=cwd)
    if rc != 0:
        return [{'error': f'git log failed: {out}', 'severity': 'critical'}]
    findings = []
    seen_red = False
    seen_green = False
    for line in out.strip().split('\n'):
        s = line.strip()
        if s.startswith('test: red'):
            seen_red = True
        elif s.startswith('feat: green') or s.startswith('fix: green'):
            if not seen_red:
                findings.append({
                    'subject': s,
                    'severity': 'high',
                    'description': f'green before test: red in cycle',
                })
            seen_green = True
        elif s.startswith('refactor:'):
            if not seen_green:
                findings.append({
                    'subject': s,
                    'severity': 'high',
                    'description': f'refactor without preceding green',
                })
    return findings


def cmd_gate(args):
    """per-commit gate 检查: commit format + R-G-R 顺序 + AC trace + 反模式扫描。"""
    if args.tests:
        print('error: --tests 已废弃 (v0.7-001); lint/test/typecheck 不再由 keeper gate 调度', file=sys.stderr)
        return 1
    if args.lint:
        print('error: --lint 已废弃 (v0.7-001); lint/test/typecheck 不再由 keeper gate 调度', file=sys.stderr)
        return 1
    if args.typecheck:
        print('error: --typecheck 已废弃 (v0.7-001); lint/test/typecheck 不再由 keeper gate 调度', file=sys.stderr)
        return 1

    cwd = Path.cwd()
    print(f"=== Keeper Gate ===")
    print(f"Commit range: {args.commit_range}")
    print()

    all_findings = []

    findings = check_commit_messages(args.commit_range, cwd=cwd)
    print(f"--- Commit Message Format ({len(findings)} findings) ---")
    for f in findings:
        print(f"[{f.get('severity','?')}] {f.get('commit','?')} - {f.get('subject','?')}")
    all_findings.extend(findings)

    findings = check_rgr_order(args.commit_range, cwd=cwd)
    print(f"--- R-G-R Order ({len(findings)} findings) ---")
    for f in findings:
        print(f"[{f.get('severity','?')}] {f.get('subject','?')} - {f.get('description','')}")
    all_findings.extend(findings)

    findings = check_test_before_impl(args.commit_range, cwd=cwd)
    print(f"--- Test Before Impl ({len(findings)} findings) ---")
    for f in findings:
        print(f"[{f.get('severity','?')}] {f.get('subject','?')} - {f.get('description','')}")
    all_findings.extend(findings)

    if not args.skip_ac_trace:
        rc = subprocess.run([sys.executable, '-m', 'louke.__main__', 'archer', 'ci-scan', '--spec', args.commit_range],
                            cwd=cwd).returncode
        if rc != 0:
            all_findings.append({'severity': 'high', 'description': 'archer ci-scan failed (AC 未引用)'})
            print('--- AC Trace: FAIL ---')

    if not args.skip_anti_pattern:
        rc = subprocess.run([sys.executable, '-m', 'louke._tools.check_assertions', '--tests', 'tests/'],
                            cwd=cwd).returncode
        if rc != 0:
            all_findings.append({'severity': 'high', 'description': 'anti-pattern scan failed'})
            print('--- Anti-Pattern: FAIL ---')

    has_blocking = any(f.get('severity') in ('critical', 'high') for f in all_findings)
    if has_blocking:
        print(f"\n→ 拒绝 ({sum(1 for f in all_findings if f.get('severity') in ('critical','high'))} blocking findings)")
        return 1
    print(f"\n→ gate 通过 ({len(all_findings)} non-blocking findings)")
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

    test_changes = [f for f in changed if 'test' in f.lower()]
    code_changes = [f for f in changed if 'test' not in f.lower()]

    print(f"  Test changes:  {len(test_changes)}")
    print(f"  Code changes:  {len(code_changes)}")

    findings = []

    if len(code_changes) > 5:
        findings.append({
            'severity': 'medium',
            'description': f'Bug fix 改了 {len(code_changes)} 个代码文件 (建议 ≤5, 超出可能引入新回归)',
        })

    for f in changed:
        if any(p in f for p in ('package.json', 'requirements.txt', 'pyproject.toml',
                                  'Cargo.toml', 'go.mod')):
            findings.append({
                'severity': 'high',
                'description': f'依赖文件 {f} 在 bug fix 中被改 (可能是版本变化, 需审查)',
            })

    if args.tests:
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