"""Devon commands - R-G-R coding.

Devon responsibilities: Red -> Green -> Refactor loop, unit-test driven.
lk provides: run tests + commit per R-G-R standard.
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
    parser = subparsers.add_parser('devon', help='R-G-R coding (Devon)')
    sub = parser.add_subparsers(dest='command', required=True, metavar='<command>')

    p = sub.add_parser('commit-rgr', help='commit per R-G-R standard (FR-0580 default no-push)')
    p.add_argument('--phase', required=True, help='R-G-R phase (green/refactor); red phase deprecated')
    p.add_argument('--message', required=True, help='commit message body')
    p.add_argument('--issue', required=True, help='GitHub issue number currently being handled')
    p.add_argument('--label', default='', help='force issue type (feature/fix); default reads issue labels')
    p.add_argument('--push', action='store_true', help='explicit push (default no-push)')


def run(args):
    handlers = {
        'commit-rgr': cmd_commit_rgr,
    }
    return handlers.get(args.command, lambda _: 1)(args) or 0


def _infer_issue_label(issue: str) -> str:
    """Read GitHub issue labels and infer whether it is feature or fix.

    Defaults to 'feature' when no label is found or reading fails
    (louke main flow is primarily FR-driven).
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
    # default to FR when no explicit label; do not block flow
    return 'feature'


def cmd_commit_rgr(args):
    """FR-0580: default no-push; --push to push; auto-infer prefix from issue label."""
    if args.phase == 'red':
        print('error: --phase red deprecated (v0.7-001); Red phase no longer commits', file=sys.stderr)
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
