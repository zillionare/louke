"""Judge commands - security audit (S level).

Judge responsibilities: per-milestone deep security audit. S-level agent,
slow/deep/expensive.
lk provides tooling support: diff + pattern scan + structured report.
S-level Judge performs semantic deep analysis on top of lk output
(understanding attack vectors, trust boundaries).
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
    parser = subparsers.add_parser('judge', help='security audit (Judge, S level)')
    sub = parser.add_subparsers(dest='command', required=True, metavar='<command>')

    p = sub.add_parser('security-audit', help='per-milestone deep security audit (FR-0610 two-stage)')
    p.add_argument('--release', required=True, help='release branch, e.g. releases/v0.1')
    p.add_argument('--baseline', default='main', help='baseline (default main)')
    p.add_argument('--checklist', default='.louke/templates/security-checklist.md',
                   help='audit baseline (default security-checklist.md)')
    p.add_argument('--use-llm', action='store_true', help='stage 2: agent semantic review (requires configured model)')
    p.add_argument('--model', default='', help='override default review model (LOUKE_OPENCODE_REVIEW_MODEL)')

    p = sub.add_parser('quick-scan', help='shallow security quick scan (per-PR)')
    p.add_argument('--diff', default='HEAD', help='ref/branch/commit to scan')


def run(args):
    handlers = {
        'security-audit': cmd_security_audit,
        'quick-scan': cmd_quick_scan,
    }
    return handlers.get(args.command, lambda _: 1)(args) or 0


def cmd_security_audit(args):
    """Per-milestone security audit: pattern scan + S-level semantic analysis frame.

    The command emits structured findings; S-level Judge performs deep
    analysis on top of this output:
    - business-logic bugs (race condition / atomicity / state machine)
    - context reasoning (implicit trust chain / attack vectors)
    - complex control flow (callback injection / reentrancy)

    Exit code: any critical/high -> 1 (block release); otherwise 0.
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
            print(f'-> verdict: {verdict} (stage 2 skipped)')
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
        print(f"-> verdict: REJECT (critical/high patterns present)")
        return 1
    if verdict == 'needs-human-review':
        print(f"-> verdict: needs-human-review (medium/low non-blocking; needs S-level Judge review)")
        return 2
    print(f"-> verdict: PASS (stage 1 has no blocking findings)")
    return 0


def cmd_quick_scan(args):
    """Shallow quick scan - any critical finding fails."""
    cwd = Path.cwd()
    changed_files = get_diff_files('HEAD~1', args.diff, cwd=cwd)
    if not changed_files:
        # try git diff --cached
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

    # quick scan only fails on critical
    if any(f['severity'] == 'critical' for f in all_findings):
        print("\n-> Quick scan REJECT (critical pattern found)")
        return 1
    print(f"\n-> Quick scan PASS ({len(all_findings)} non-critical findings)")
    return 0