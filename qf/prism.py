"""Prism commands - 代码 review (含测试代码 + 安全 quick scan).

Prism 职责: 多视角代码 review + 批判性视角 + 测试反模式扫描 + 安全 quick scan。
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

from ._common import get_diff_files, print_findings, has_blocking_severity
from ._security import scan_file
from ._tests import scan_test_file, find_test_files


def register(subparsers):
    parser = subparsers.add_parser('prism', help='代码 review (Prism)')
    sub = parser.add_subparsers(dest='command', required=True, metavar='<command>')

    p = sub.add_parser('review', help='完整 review (生产 + 测试 + 安全)')
    p.add_argument('--diff', default='HEAD', help='要 review 的 ref (默认 HEAD)')

    p = sub.add_parser('test-patterns', help='测试代码反模式扫描 (8 类 + AC 引用)')
    p.add_argument('--tests', default='tests/', help='tests 目录 (默认 tests/)')

    p = sub.add_parser('security-quick-scan', help='浅层安全 pattern 扫描')
    p.add_argument('--diff', default='HEAD', help='要扫描的 ref')

    p = sub.add_parser('code-quality', help='代码质量检查 (函数长度 / 嵌套深度 / DRY)')
    p.add_argument('--diff', default='HEAD', help='要扫描的 ref')


def run(args):
    handlers = {
        'review': cmd_review,
        'test-patterns': cmd_test_patterns,
        'security-quick-scan': cmd_security_quick_scan,
        'code-quality': cmd_code_quality,
    }
    return handlers.get(args.command, lambda _: 1)(args) or 0


def cmd_review(args):
    """完整 review: 生产 + 测试 + 安全 quick scan."""
    cwd = Path.cwd()
    print(f"=== Prism Full Review ===")
    print(f"Diff: {args.diff}")
    print()

    changed = get_diff_files('HEAD~1', args.diff, cwd=cwd)

    # Test patterns
    test_findings = []
    for fp_str in changed:
        if 'test' in fp_str.lower():
            fp = cwd / fp_str
            if fp.exists():
                test_findings.extend(scan_test_file(fp))

    # Security patterns
    security_findings = []
    for fp_str in changed:
        fp = cwd / fp_str
        if fp.exists():
            security_findings.extend(scan_file(fp))

    print_findings(test_findings, header='Test Anti-patterns')
    print_findings(security_findings, header='Security Quick Scan')

    print(f"\n=== Summary ===")
    print(f"Test findings:     {len(test_findings)}")
    print(f"Security findings: {len(security_findings)}")

    # 判定: critical/high → 拒绝
    all_findings = test_findings + security_findings
    if has_blocking_severity(all_findings):
        print("→ 拒绝 (有 critical/high)")
        return 1
    print("→ 通过 (semantic review 仍需 Prism 主体)")
    return 0


def cmd_test_patterns(args):
    """测试代码反模式扫描."""
    cwd = Path.cwd()
    test_root = cwd / args.tests

    test_files = find_test_files(test_root)
    print(f"=== Test Anti-patterns Scan ===")
    print(f"Test root: {test_root}")
    print(f"Files found: {len(test_files)}")

    all_findings = []
    for fp in test_files:
        all_findings.extend(scan_test_file(fp))

    print_findings(all_findings, header='Test Anti-pattern Findings')

    print(f"\n=== Summary: {len(all_findings)} findings ===")
    if has_blocking_severity(all_findings):
        print("→ critical/high 命中, 需修复")
        return 1
    return 0


def cmd_security_quick_scan(args):
    """安全 pattern 浅扫 - 与 judge quick-scan 类似但视角不同 (Prism 看代码质量)."""
    cwd = Path.cwd()
    changed = get_diff_files('HEAD~1', args.diff, cwd=cwd)
    print(f"=== Prism Security Quick Scan ===")
    print(f"Files: {len(changed)}")

    all_findings = []
    for fp_str in changed:
        fp = cwd / fp_str
        if fp.exists():
            all_findings.extend(scan_file(fp))

    print_findings(all_findings, header='Findings')
    return 1 if has_blocking_severity(all_findings) else 0


def cmd_code_quality(args):
    """代码质量检查 (函数长度 / 嵌套深度)."""
    cwd = Path.cwd()
    changed = get_diff_files('HEAD~1', args.diff, cwd=cwd)
    print(f"=== Code Quality Check ===")
    print(f"Files: {len(changed)}")

    findings = []
    for fp_str in changed:
        fp = cwd / fp_str
        if not fp.exists() or fp.suffix != '.py':
            continue
        try:
            content = fp.read_text(encoding='utf-8', errors='replace')
        except (OSError, PermissionError):
            continue

        # 函数长度检查
        lines = content.split('\n')
        in_func = False
        func_start = 0
        func_name = ''
        func_indent = 0
        for i, line in enumerate(lines):
            m = re.match(r'^(\s*)(?:async\s+)?def\s+(\w+)\s*\(', line)
            if m:
                # 进入新函数
                if in_func:
                    func_len = i - func_start
                    if func_len > 30:
                        findings.append({
                            'file': str(fp), 'line': func_start + 1,
                            'severity': 'medium', 'pattern_id': 'func-too-long',
                            'description': f'函数 {func_name} 长度 {func_len} 行 (建议 ≤30)',
                            'matched': 'function length',
                            'snippet': lines[func_start].strip()[:120],
                        })
                in_func = True
                func_start = i
                func_name = m.group(2)
                func_indent = len(m.group(1))
            elif in_func and line.strip() and not line.startswith(' ' * (func_indent + 1)) and not line.startswith(func_indent * ' '):
                # 函数结束
                func_len = i - func_start
                if func_len > 30:
                    findings.append({
                        'file': str(fp), 'line': func_start + 1,
                        'severity': 'medium', 'pattern_id': 'func-too-long',
                        'description': f'函数 {func_name} 长度 {func_len} 行 (建议 ≤30)',
                        'matched': 'function length',
                        'snippet': lines[func_start].strip()[:120],
                    })
                in_func = False

    print_findings(findings, header='Code Quality Findings')
    print(f"\n=== Summary: {len(findings)} findings ===")
    return 1 if has_blocking_severity(findings) else 0