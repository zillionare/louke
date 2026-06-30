"""Judge commands - 安全审计 (S 级).

Judge 职责: per-milestone 深度安全审计。S 级 agent, 慢/深/贵。
lk 提供工具支持: diff + pattern scan + 结构化报告。
S 级 Judge 在 lk 输出基础上做语义层深度分析（理解攻击向量、信任边界）。
"""
import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from ._common import get_diff_files, print_findings, has_blocking_severity
from ._security import scan_file


def register(subparsers):
    parser = subparsers.add_parser('judge', help='安全审计 (Judge, S 级)')
    sub = parser.add_subparsers(dest='command', required=True, metavar='<command>')

    p = sub.add_parser('security-audit', help='per-milestone 深度安全审计 (FR-0610 两阶段)')
    p.add_argument('--release', required=True, help='release 分支, 例 releases/v0.1')
    p.add_argument('--baseline', default='main', help='基线 (默认 main)')
    p.add_argument('--checklist', default='.louke/templates/security-checklist.md',
                   help='审计基线 (默认 security-checklist.md)')
    p.add_argument('--use-llm', action='store_true', help='阶段二: agent 语义审查（需配置模型）')
    p.add_argument('--model', default='', help='覆盖默认 review model (LOUKE_OPENCODE_REVIEW_MODEL)')

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
    print(f"=== Security Audit (lk judge) ===")
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

    print_findings(all_findings, header='Security Pattern Findings (Stage 1)')

    # Summary
    by_sev = {'critical': 0, 'high': 0, 'medium': 0, 'low': 0}
    for f in all_findings:
        by_sev[f['severity']] = by_sev.get(f['severity'], 0) + 1

    print(f"\n=== Stage 1 Pattern Scan Summary ===")
    print(f"Critical: {by_sev['critical']}")
    print(f"High:     {by_sev['high']}")
    print(f"Medium:   {by_sev['medium']}")
    print(f"Low:      {by_sev['low']}")

    blockers = [f for f in all_findings if f['severity'] in ('critical', 'high')]
    warnings = [f for f in all_findings if f['severity'] in ('medium', 'low')]
    verdict = 'fail' if blockers else ('pass' if not warnings else 'needs-human-review')

    report = {
        'audit_id': f'{args.release}-{datetime.now().isoformat(timespec="seconds")}',
        'stage1_findings': all_findings,
        'stage2_findings': None,
        'blockers': [{'file': f.get('file'), 'line': f.get('line'), 'description': f.get('description')} for f in blockers],
        'warnings': [{'file': f.get('file'), 'line': f.get('line'), 'description': f.get('description')} for f in warnings],
        'verdict': verdict,
    }

    if args.use_llm:
        model = args.model or os.environ.get('LOUKE_OPENCODE_REVIEW_MODEL', '')
        if not model:
            raw_dir = Path('.louke/raw')
            raw_dir.mkdir(parents=True, exist_ok=True)
            report_path = raw_dir / f'security-audit-{datetime.now().strftime("%Y%m%d")}.json'
            report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
            print(f'warn: --use-llm but no model configured (set LOUKE_OPENCODE_REVIEW_MODEL)', file=sys.stderr)
            print(f'      stage 2 skipped; report written: {report_path}', file=sys.stderr)
            print(f'→ 判定: {verdict} (stage 2 skipped)')
            return 0 if verdict != 'fail' else 1
        # Stage 2 placeholder: model invocation deferred to integration w/ OpenCode agent.
        print(f'Stage 2: model={model} (placeholder; integrate with OpenCode review agent)')
        report['stage2_findings'] = [{'note': f'would invoke {model} for semantic review'}]
        verdict = 'needs-human-review'

    # Persist machine-readable report
    raw_dir = Path('.louke/raw')
    raw_dir.mkdir(parents=True, exist_ok=True)
    report_path = raw_dir / f'security-audit-{datetime.now().strftime("%Y%m%d-%H%M%S")}.json'
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'report written: {report_path}')

    if verdict == 'fail':
        print(f"→ 判定: 拒绝 (存在 critical/high pattern)")
        return 1
    if verdict == 'needs-human-review':
        print(f"→ 判定: needs-human-review (medium/low 未阻塞，需 S 级 Judge 复审)")
        return 2
    print(f"→ 判定: 通过 (stage 1 无 blocking findings)")
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