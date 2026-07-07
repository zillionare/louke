"""Keeper commands - gate checks.

Keeper responsibilities: per-commit gate (R-G-R order + commit format + AC trace +
anti-pattern scan) + regression check (merges Shield's judgment portion).
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path
from typing import Optional

from ._common import git


def register(subparsers):
    parser = subparsers.add_parser('keeper', help='gate check (Keeper)')
    sub = parser.add_subparsers(dest='command', required=True, metavar='<command>')

    p = sub.add_parser('gate', help='per-commit gate (format + R-G-R order + AC trace + anti-pattern scan)')
    p.add_argument('--commit-range', default='HEAD~1..HEAD', help='commit range to check')
    p.add_argument('--tests', action='store_true', help='deprecated (v0.7-001)')
    p.add_argument('--lint', action='store_true', help='deprecated (v0.7-001)')
    p.add_argument('--typecheck', action='store_true', help='deprecated (v0.7-001)')
    p.add_argument('--skip-ac-trace', action='store_true', help='skip AC trace validation')
    p.add_argument('--skip-anti-pattern', action='store_true', help='skip anti-pattern scan')

    p = sub.add_parser('regression', help='regression check (per-bug-fix, compare before/after fix)')
    p.add_argument('--baseline', default='main', help='baseline (before fix)')
    p.add_argument('--current', default='HEAD', help='current (after fix)')
    p.add_argument('--tests', action='store_true', help='run tests for actual comparison (default: diff range only)')


def run(args):
    handlers = {
        'gate': cmd_gate,
        'regression': cmd_regression,
    }
    return handlers.get(args.command, lambda _: 1)(args) or 0


def check_commit_messages(commit_range: str, cwd: Path = None) -> list:
    """Check commit message format - R-G-R pattern (feat: green / fix: green / refactor:)."""
    rc, out, _ = git('log', '--format=%H %s', commit_range, cwd=cwd)
    if rc != 0:
        return [{'error': f'git log failed: {out}', 'severity': 'critical'}]

    valid_prefixes = (
        'feat: green',
        'fix: green',
        'refactor:',
        'fix:',
        'docs:',
        'chore:',
        'e2e:',
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
                    f'commit format non-standard (must start with one of {" / ".join(valid_prefixes)}; '
                    f'Green phase uses "feat: green" / "fix: green")'
                ),
            })
    return findings


# ---- FR-0400.3: R-G-R order validation ----

_ISSUE_RE = re.compile(r'#(\d+)')


def _issue_key(subject: str) -> str:
    """Extract issue number from commit subject as grouping key; return subject itself if no issue number."""
    match = _ISSUE_RE.search(subject)
    return match.group(1) if match else subject


def _rgr_phase(subject: str) -> Optional[str]:
    """Return the R-G-R phase corresponding to the subject: 'green' / 'refactor'; None for unrelated phases."""
    if subject.startswith('feat: green') or subject.startswith('fix: green'):
        return 'green'
    if subject.startswith('refactor:'):
        return 'refactor'
    return None


def check_rgr_order(commit_range: str, cwd: Path = None) -> list:
    """Validate by issue grouping that green must precede refactor; cross-issue commits skip order validation.

    Allowed sequences within the same issue:
    - [green]
    - [green, refactor...]
    - [refactor...]

    Forbidden sequences:
    - [refactor..., green...] (refactor appears before green)
    """
    rc, out, _ = git('log', '--reverse', '--format=%s', commit_range, cwd=cwd)
    if rc != 0:
        return [{'error': f'git log failed: {out}', 'severity': 'critical'}]

    grouped: dict[str, list[tuple[str, str]]] = {}
    for line in out.strip().split('\n'):
        subject = line.strip()
        phase = _rgr_phase(subject)
        if phase is None:
            continue
        grouped.setdefault(_issue_key(subject), []).append((phase, subject))

    findings = []
    for commits in grouped.values():
        seen_refactor = False
        for phase, subject in commits:
            if phase == 'green' and seen_refactor:
                findings.append({
                    'subject': subject,
                    'severity': 'high',
                    'description': 'refactor before green within the same issue',
                })
            elif phase == 'refactor':
                seen_refactor = True
    return findings


def cmd_gate(args):
    """per-commit gate check: commit format + R-G-R order + AC trace + anti-pattern scan."""
    if args.tests:
        print('error: --tests deprecated (v0.7-001); lint/test/typecheck no longer scheduled by keeper gate', file=sys.stderr)
        return 1
    if args.lint:
        print('error: --lint deprecated (v0.7-001); lint/test/typecheck no longer scheduled by keeper gate', file=sys.stderr)
        return 1
    if args.typecheck:
        print('error: --typecheck deprecated (v0.7-001); lint/test/typecheck no longer scheduled by keeper gate', file=sys.stderr)
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

    if not args.skip_ac_trace:
        rc = subprocess.run([sys.executable, '-m', 'louke.__main__', 'archer', 'ci-scan', '--spec', args.commit_range],
                            cwd=cwd).returncode
        if rc != 0:
            all_findings.append({'severity': 'high', 'description': 'archer ci-scan failed (AC not referenced)'})
            print('--- AC Trace: FAIL ---')

    if not args.skip_anti_pattern:
        rc = subprocess.run([sys.executable, '-m', 'louke._tools.check_assertions', '--tests', 'tests/'],
                            cwd=cwd).returncode
        if rc != 0:
            all_findings.append({'severity': 'high', 'description': 'anti-pattern scan failed'})
            print('--- Anti-Pattern: FAIL ---')

    has_blocking = any(f.get('severity') in ('critical', 'high') for f in all_findings)
    if has_blocking:
        print(f"\n→ REJECT ({sum(1 for f in all_findings if f.get('severity') in ('critical','high'))} blocking findings)")
        return 1
    print(f"\n→ gate PASS ({len(all_findings)} non-blocking findings)")
    return 0


def cmd_regression(args):
    """Regression check: compare baseline vs current test results."""
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
            'description': f'Bug fix changed {len(code_changes)} code files (recommend ≤5; exceeding may introduce new regressions)',
        })

    for f in changed:
        if any(p in f for p in ('package.json', 'requirements.txt', 'pyproject.toml',
                                  'Cargo.toml', 'go.mod')):
            findings.append({
                'severity': 'high',
                'description': f'Dependency file {f} changed in bug fix (may be version change; needs review)',
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
                'description': 'Current test suite failed (regression test did not pass)',
            })
        else:
            print("[ok] current tests passed")

    print(f"\n=== Findings ({len(findings)}) ===")
    for f in findings:
        print(f"[{f['severity']}] {f['description']}")

    if any(f['severity'] in ('critical', 'high') for f in findings):
        print("\n→ REJECT (critical/high issues)")
        return 1
    print("\n→ regression check PASS")
    return 0
