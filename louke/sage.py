"""Sage commands - requirement clarification + spec/issue flow.

Sage responsibilities: multi-round questioning -> spec.md -> acceptance.md
-> create GitHub issues.
All commands are exposed via this module.
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

from ._common import resolve_existing_path
from .stage_results import write_stage_result


def register(subparsers):
    parser = subparsers.add_parser('sage', help='requirement clarification (Sage)')
    sub = parser.add_subparsers(dest='command', required=True, metavar='<command>')

    # quote-check: check quote status in spec.md (v0.7-003: invokes discuss.py internally)
    p = sub.add_parser('quote-check', help='check whether all quotes in spec.md are resolved')
    p.add_argument('--spec', required=True, help='spec-id, e.g. v0.1-001-init')
    p.add_argument('--check-ready', action='store_true', help='exit 0 if ready (Maestro gate; no JSON output)')
    p.add_argument('--check-violations', action='store_true', help='detect ownership violations (who closed someone else\'s quote)')
    p.add_argument('--format', choices=['text', 'json'], default='text', help='output format (default text)')

    # commit-spec: multi-step git ops wrapper
    p = sub.add_parser('commit-spec', help='commit spec + acceptance (git add + commit + push)')
    p.add_argument('--spec', required=True)
    p.add_argument('--message', required=True)
    p.add_argument('--no-push', action='store_true')

    # create-issues: create GitHub issues from spec (FR-0410)
    p = sub.add_parser('create-issues', help='create GitHub issues from spec (with schema validation)')
    p.add_argument('--spec', required=True)
    p.add_argument('--spec-file', default='', help='directly specify spec.md path')
    p.add_argument('--dry-run', action='store_true')
    p.add_argument('--skip-project', action='store_true', help='do not block when Project URL is missing')

    # record-lock: 3-signal lock record (FR-0420)
    p = sub.add_parser('record-lock', help='record spec locked: true (after 3 signals pass)')
    p.add_argument('--spec', required=True)
    p.add_argument('--confirm', action='store_true')

    p = sub.add_parser('record-testplan-review', help='persist Sage test-plan review verdict as a stage artifact')
    p.add_argument('--spec', required=True)
    p.add_argument('--verdict', required=True, choices=['pass', 'reject'])
    p.add_argument('--reviewed-target', dest='reviewed_targets', action='append', default=[],
                   help='repeatable path reviewed by Sage')
    p.add_argument('--blocking-finding', action='append', default=[],
                   help='repeatable blocking finding summary')
    p.add_argument('--accepted-risk', action='append', default=[],
                   help='repeatable accepted risk summary')


def run(args):
    handlers = {
        'quote-check': cmd_quote_check,
        'commit-spec': cmd_commit_spec,
        'create-issues': cmd_create_issues,
        'lock-spec': cmd_lock_spec,
        'record-lock': cmd_record_lock,
        'record-testplan-review': cmd_record_testplan_review,
    }
    return handlers.get(args.command, lambda _: 1)(args) or 0


def cmd_quote_check(args):
    """Invoke louke._tools.discuss (FR-0450 resolve_spec_path, v0.7-003 inline-discussion).

    3 mutually-exclusive flags:
    --check-ready: exit 0 if is_ready (Maestro gate; emits blockers to stderr)
    --check-violations: detect status markers on nested reply lines (parser ignores them, but writer intent is wrong)
    --format text|json (default text): list all threads + status; do NOT combine --check-ready when requesting JSON
    """
    spec_path = _resolve_quote_check_spec(args)
    if not spec_path.exists():
        print(f'sage quote-check: {spec_path} not found', file=sys.stderr)
        return 2
    from ._tools import discuss
    if args.check_ready:
        ready, blockers = discuss.DiscussParser().is_ready(spec_path)
        if not ready:
            print(f'spec not ready: {len(blockers)} blocker(s)', file=sys.stderr)
            for b in blockers:
                print(f'  {b}', file=sys.stderr)
        return 0 if ready else 1
    if args.check_violations:
        exit_code, msg = discuss.check_violations(spec_path)
        print(msg)
        return exit_code
    exit_code, output = discuss.format_ready(spec_path, args.format)
    print(output)
    return exit_code


def _resolve_quote_check_spec(args) -> Path:
    """Resolve --spec argument to a spec.md Path (spec-id or direct path)."""
    spec_arg = args.spec
    candidate = Path(spec_arg)
    if candidate.exists():
        return candidate
    default = Path(f'.louke/project/specs/{args.spec}/spec.md')
    if default.exists():
        return default
    return resolve_existing_path(spec_arg)


def cmd_commit_spec(args):
    """git add spec.md + acceptance.md + commit + push (multi-step wrapper)."""
    spec_path = f".louke/project/specs/{args.spec}"
    cmds = [
        ['git', 'add', f"{spec_path}/spec.md", f"{spec_path}/acceptance.md"],
        ['git', 'commit', '-m', args.message],
    ]
    if not args.no_push:
        cmds.append(['git', 'push'])
    for cmd in cmds:
        result = subprocess.run(cmd, cwd=Path.cwd())
        if result.returncode != 0:
            print(f"failed: {' '.join(cmd)}", file=sys.stderr)
            return result.returncode
    return 0


def cmd_record_testplan_review(args):
    """Persist Sage's M-TESTPLAN review verdict so Maestro can gate on a concrete artifact."""
    targets = args.reviewed_targets or [f'.louke/project/specs/{args.spec}/test-plan.md']
    path = write_stage_result(
        spec_id=args.spec,
        stage='M-TESTPLAN',
        kind='review-result',
        role='Sage',
        verdict='pass' if args.verdict == 'pass' else 'fail',
        reviewed_targets=targets,
        blocking_findings=args.blocking_finding,
        accepted_risks=args.accepted_risk,
    )
    print(f'✓ review artifact written: {path}')
    return 0


# ---- FR-0410: create-issues ----

RE_FR_ANCHOR = re.compile(r'<a\s+id="fr-(\d{4})"></a>', re.I)
RE_FR_HEADING = re.compile(r"^###\s+(FR|NFR)-(\d{4})\s+([^\n]+)$", re.MULTILINE)
RE_AC_ANCHOR = re.compile(r'<a\s+id="ac-(fr|nfr)-(\d{4})"></a>', re.I)


def _read_project_info_value(label: str) -> str:
    # fix-002: delegate to _common. project.toml replaces project-info.md.
    from ._common import _read_project_info_field
    return _read_project_info_field(label)


def _find_spec_path(args) -> Path:
    if args.spec_file:
        candidate = Path(args.spec_file)
        if not candidate.exists():
            candidate = resolve_existing_path(args.spec_file)
        return Path(candidate)
    default = Path(f'.louke/project/specs/{args.spec}/spec.md')
    if default.exists():
        return default
    return resolve_existing_path(args.spec)


def _extract_frs(spec_text: str) -> list[tuple[str, str]]:
    """Return list of (fr_id, title)."""
    frs = []
    seen = set()
    for m in RE_FR_HEADING.finditer(spec_text):
        prefix, num, title = m.group(1), m.group(2), m.group(3).strip()
        fr_id = f'{prefix}-{num}'
        if fr_id in seen:
            continue
        seen.add(fr_id)
        frs.append((fr_id, title))
    return frs


def _acceptance_spec_text(spec_id: str) -> str:
    acc_path = Path(f'.louke/project/specs/{spec_id}/acceptance.md')
    return acc_path.read_text(encoding='utf-8') if acc_path.exists() else ''


def _decide_ac_value(fr_id: str, spec_text: str, acc_text: str, branch: str, repo_url: str) -> str:
    num = fr_id.split('-')[1]
    if RE_AC_ANCHOR.search(acc_text):
        if repo_url:
            return f'{repo_url}/blob/{branch}/.louke/project/specs/{spec_id}/acceptance.md#ac-fr-{num}'
        return f'.louke/project/specs/{spec_id}/acceptance.md#ac-fr-{num}'
    if re.search(rf'<a\s+id="fr-{num}"></a>', spec_text):
        if repo_url:
            return f'{repo_url}/blob/{branch}/.louke/project/specs/{spec_id}/spec.md#fr-{num}'
        return f'spec.md#fr-{num}'
    return 'None'


def _gh_list_issues_with_fr(repo, fr_id):
    try:
        out = subprocess.check_output(['gh', 'issue', 'list', '--repo', repo, '--state', 'all',
                                       '--search', f'in:title [{fr_id}]', '--json', 'number,title,url'],
                                      text=True, stderr=subprocess.DEVNULL)
        return json.loads(out) or []
    except Exception:
        return []


def _gh_create_issue(repo, title, body):
    try:
        out = subprocess.check_output(['gh', 'issue', 'create', '--repo', repo,
                                       '--title', title, '--label', 'Feature',
                                       '--body', body],
                                      text=True, stderr=subprocess.DEVNULL)
        m = re.search(r'/issues/(\d+)', out)
        return f'https://github.com/{repo}/issues/{m.group(1)}' if m else out.strip()
    except subprocess.CalledProcessError as e:
        print(f'gh issue create failed for {title}: {(e.stderr or e.stdout)[:200]}', file=sys.stderr)
        return None


def _gh_link_to_project(project_url, issue_url):
    try:
        subprocess.run(['gh', 'project', 'item-add', str(project_url), '--url', issue_url],
                       cwd=Path.cwd(), capture_output=True, text=True, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f'gh project item-add failed: {(e.stderr or e.stdout)[:200]}', file=sys.stderr)
        return False


def cmd_create_issues(args):
    """FR-0410: create GitHub issues from spec.md FR anchors (4-digit schema)."""
    spec_path = _find_spec_path(args)
    if not spec_path.exists():
        print(f'spec file not found: {args.spec_file or args.spec}', file=sys.stderr)
        return 1
    spec_text = spec_path.read_text(encoding='utf-8', errors='replace')
    frs = _extract_frs(spec_text)
    if not frs:
        print('0 created, 0 skipped')
        return 0
    acc_text = _acceptance_spec_text(args.spec)
    repo = _read_project_info_value('Repo').replace('github.com/', '')
    if not repo:
        print('Repo field missing in project.toml; run lk agent scout foundation first', file=sys.stderr)
        return 1
    branch = _read_project_info_value('Release Branch')
    if not branch:
        print('Release Branch field missing in project.toml; run lk agent scout foundation first', file=sys.stderr)
        return 1
    project_url = _read_project_info_value('Project ID')
    if not project_url and not args.skip_project:
        print('Project URL field missing in project.toml; cannot link issues', file=sys.stderr)
        print('  hint: lk agent scout foundation (writes Project ID) or pass --skip-project', file=sys.stderr)
        return 1
    repo_url = f'https://github.com/{repo}'
    created, skipped, linked = 0, 0, 0
    for fr_id, title in frs:
        existing = _gh_list_issues_with_fr(repo, fr_id)
        if existing:
            skipped += 1
            print(f'[-] {fr_id} {existing[0].get("number", "?")} (exists)')
            continue
        ac_value = _decide_ac_value(fr_id, spec_text, acc_text, branch, repo_url)
        body = (
            f'### Requirement ID\n{fr_id}\n\n'
            f'### Spec Link\n{repo_url}/blob/{branch}/.louke/project/specs/{args.spec}/spec.md#fr-{fr_id.split("-")[1]}\n\n'
            f'### Acceptance Criteria\n{ac_value}\n'
        )
        if args.dry_run:
            print(f'[+] {fr_id} {title!r} body len={len(body)}')
            created += 1
            continue
        issue_url = _gh_create_issue(repo, f'[{fr_id}] {title}', body)
        if not issue_url:
            continue
        created += 1
        print(f'[+] {fr_id} -> {issue_url}')
        if project_url and _gh_link_to_project(project_url, issue_url):
            linked += 1
    print(f'{created} created, {skipped} skipped, {linked} linked')
    return 0


def cmd_lock_spec(args):
    """Backward-compatible alias for record-lock requiring manual confirmation outside CLI."""
    print('lock-spec is deprecated; use record-lock --confirm', file=sys.stderr)
    return cmd_record_lock(argparse.Namespace(spec=args.spec, confirm=False))


def _run_lk(*args, cwd=None) -> int:
    return subprocess.run([sys.executable, '-m', 'louke.__main__', 'agent', *args],
                          cwd=cwd or Path.cwd()).returncode


def cmd_record_lock(args):
    """FR-0420: 3-signal lock record. lock: true is a result, not a signal.

    FR-0060 v0.7-003: Sage signal uses inline-discussion protocol (call discuss.is_ready).
    """
    if not args.confirm:
        print('User signal missing: pass --confirm after IDE confirmation', file=sys.stderr)
        return 1
    # Sage signal (FR-0060: uses inline-discussion)
    spec_path = Path(f'.louke/project/specs/{args.spec}/spec.md')
    if not spec_path.exists():
        spec_path = resolve_existing_path(args.spec)
    if spec_path is None or not spec_path.exists():
        print(f'spec not found: {args.spec}', file=sys.stderr)
        return 1
    from ._tools import discuss as _discuss
    result = _discuss.DiscussParser().parse_file(spec_path)
    if not result.is_ready:
        print('Sage signal: not passed (inline-discussion is_ready=False)', file=sys.stderr)
        for b in result.ready_blockers:
            print(f'  {b}', file=sys.stderr)
        return 1
    # Lex signal
    for sub in (['lex', 'verify-acceptance', '--spec', args.spec],
                ['lex', 'verify-issue', '--spec', args.spec],
                ['lex', 'verify-project', '--spec', args.spec]):
        rc = _run_lk(*sub)
        if rc != 0:
            print(f'Lex signal: {sub[1]} failed (rc={rc})', file=sys.stderr)
            return rc
    text = spec_path.read_text(encoding='utf-8')
    locked_already = False
    if text.startswith('---\n'):
        end = text.find('\n---\n', 4)
        if end != -1:
            fm = text[4:end]
            if 'locked: true' in fm:
                locked_already = True
            else:
                text = text[:end] + f'\nlocked: true\nlocked-at: {datetime_now()}\nlocked-by: lk agent sage record-lock' + text[end:]
        else:
            text = f'---\nlocked: true\nlocked-at: {datetime_now()}\nlocked-by: lk agent sage record-lock\n---\n' + text
    else:
        text = f'---\nlocked: true\nlocked-at: {datetime_now()}\nlocked-by: lk agent sage record-lock\n---\n' + text
    if locked_already:
        print(f'spec already locked; idempotent (spec={args.spec})')
        return 0
    spec_path.write_text(text, encoding='utf-8')
    print(f'locked: true ({args.spec})')
    return 0


def datetime_now():
    from datetime import datetime
    return datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')
