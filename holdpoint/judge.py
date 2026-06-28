"""Judge commands - 安全审计 (S 级).

Judge 职责: per-milestone 深度安全审计。S 级 agent, 慢/深/贵。
hp 提供工具支持: diff + pattern scan + 结构化报告。
S 级 Judge 在 hp 输出基础上做语义层深度分析（理解攻击向量、信任边界）。
"""
import argparse
import sys
from pathlib import Path

from ._common import get_diff_files, print_findings, has_blocking_severity
from ._security import scan_file


def register(subparsers):
    parser = subparsers.add_parser('judge', help='安全审计 (Judge, S 级)')
    sub = parser.add_subparsers(dest='command', required=True, metavar='<command>')

    p = sub.add_parser('security-audit', help='per-milestone 深度安全审计 (含 pattern scan + 报告框架)')
    p.add_argument('--release', required=True, help='release 分支, 例 releases/v0.1')
    p.add_argument('--baseline', default='main', help='基线 (默认 main)')
    p.add_argument('--checklist', default='.holdpoint/templates/security-checklist.md',
                   help='审计基线 (默认 security-checklist.md)')

    p = sub.add_parser('quick-scan', help='浅层安全 quick scan (per-PR 用)')
    p.add_argument('--diff', default='HEAD', help='要扫描的 ref/branch/commit')


def run(args):
    handlers = {
        'security-audit': cmd_security_audit,
        'quick-scan': cmd_quick_scan,
    }
    return handlers.get(args.command, lambda _: 1)(args) or 0


def cmd_security_audit(args):
    """Per-milestone 安全审计: pattern scan + S 级语义分析框架.

    命令输出结构化 findings, S 级 Judge 在此基础上做深度分析:
    - 业务逻辑漏洞 (race condition / atomicity / state machine)
    - 上下文推理 (隐式信任链 / 攻击向量)
    - 复杂控制流 (callback 注入 / 重入)

    退出码: 任一 critical/high → 1 (block release); 否则 0.
    """
    cwd = Path.cwd()
    print(f"=== Security Audit (hp judge) ===")
    print(f"Release:  {args.release}")
    print(f"Baseline: {args.baseline}")
    print(f"Checklist: {args.checklist}")
    print()

    changed_files = get_diff_files(args.baseline, args.release, cwd=cwd)
    print(f"Changed files: {len(changed_files)}")
    if changed_files:
        print(f"  (first 10: {changed_files[:10]})")
    print()

    # Scan code files for security patterns
    all_findings = []
    for fp_str in changed_files:
        fp = cwd / fp_str
        if not fp.exists() or fp.is_dir():
            continue
        all_findings.extend(scan_file(fp))

    print_findings(all_findings, header='Security Pattern Findings (Auto)')

    # Summary
    by_sev = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0}
    for f in all_findings:
        by_sev[f['severity']] = by_sev.get(f['severity'], 0) + 1

    print(f"\n=== Pattern Scan Summary ===")
    print(f"Critical: {by_sev['critical']}")
    print(f"High:     {by_sev['high']}")
    print(f"Medium:   {by_sev['medium']}")
    print(f"Low:      {by_sev['low']}")
    print()
    print(f"Note: This is AUTOMATED pattern scan only.")
    print(f"      S-level Judge (you) must do SEMANTIC analysis:")
    print(f"      - Business logic vulnerabilities (atomicity, race conditions)")
    print(f"      - Implicit trust chains")
    print(f"      - Attack vector reasoning")
    print(f"      See {args.checklist} for full audit baseline.")

    if has_blocking_severity(all_findings):
        print("\n→ 判定: 拒绝 (存在 critical/high pattern hits)")
        return 1
    print("\n→ 判定: pattern scan 通过 (S 级 Judge 应再做语义层分析)")
    return 0


def cmd_quick_scan(args):
    """浅层 quick scan - 任何 critical 即 fail."""
    cwd = Path.cwd()
    changed_files = get_diff_files('HEAD~1', args.diff, cwd=cwd)
    if not changed_files:
        # 尝试 git diff --cached
        changed_files = get_diff_files('--cached', args.diff, cwd=cwd)

    print(f"=== Quick Scan ===")
    print(f"Diff: {args.diff}")
    print(f"Files: {len(changed_files)}")

    all_findings = []
    for fp_str in changed_files:
        fp = cwd / fp_str
        if not fp.exists() or fp.is_dir():
            continue
        all_findings.extend(scan_file(fp))

    print_findings(all_findings, header='Findings')

    # quick scan 只对 critical 失败
    if any(f['severity'] == 'critical' for f in all_findings):
        print("\n→ Quick scan 拒绝 (有 critical pattern)")
        return 1
    print(f"\n→ Quick scan 通过 ({len(all_findings)} non-critical findings)")
    return 0