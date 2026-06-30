"""Lex commands - spec + issue 审核.

Lex 职责: 阶段一/二/三（spec 语义审核 / issue 覆盖验证 / schema 验证）。
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path


def register(subparsers):
    parser = subparsers.add_parser('lex', help='spec + issue 审核 (Lex)')
    sub = parser.add_subparsers(dest='command', required=True, metavar='<command>')

    # verify-acceptance: L1-L5 结构化校验 (Stage 1)
    p = sub.add_parser('verify-acceptance', help='运行 L1-L5 结构化校验 (Stage 1)')
    p.add_argument('--spec', required=True)
    p.add_argument('--repo', default='', help='owner/repo (默认从 project-info 或 gh repo view 推断)')
    p.add_argument('--branch', default='', help='覆盖默认 release 分支')
    p.add_argument('--spec-file', default='')
    p.add_argument('--acceptance-file', default='')

    # verify-issue: L1-L8 schema 验证 (Stage 3)
    p = sub.add_parser('verify-issue', help='运行 L1-L8 schema 验证 (Stage 3)')
    p.add_argument('--spec', required=True)
    p.add_argument('--repo', default='')

    p = sub.add_parser('verify-project', help='验证 Feature issues 已关联 Project (FR-0740)')
    p.add_argument('--spec', required=True)
    p.add_argument('--repo', default='')
    p.add_argument('--dry-run', action='store_true')

    # quote-check: 复用 Sage 的 quote-check (同 louke/_tools/quote_parser.py)
    p = sub.add_parser('quote-check', help='检查 spec.md 是否所有 quote 都 ✓ resolved')
    p.add_argument('--spec', required=True)


def run(args):
    handlers = {
        'verify-acceptance': cmd_verify_acceptance,
        'verify-issue': cmd_verify_issue,
        'verify-project': cmd_verify_project,
        'quote-check': cmd_quote_check,
    }
    return handlers.get(args.command, lambda _: 1)(args) or 0


from ._common import resolve_existing_path


def _read_project_info(label: str) -> str:
    path = Path('.louke/project/project-info.md')
    if not path.exists():
        return ''
    for line in path.read_text(encoding='utf-8', errors='replace').splitlines():
        prefix = f'- **{label}**:'
        if line.startswith(prefix):
            return line.split(':', 1)[1].strip().strip('`')
    return ''


def cmd_verify_acceptance(args):
    """FR-0540: default branch from project-info Release Branch; --repo auto-resolved."""
    cmd = [sys.executable, '-m', 'louke._tools.verify_acceptance', '--spec', args.spec]
    repo = args.repo or _read_project_info('Repo').replace('github.com/', '')
    if repo:
        cmd.extend(['--repo', repo])
    branch = args.branch or _read_project_info('Release Branch')
    if branch:
        cmd.extend(['--branch', branch])
    if args.spec_file or args.acceptance_file:
        cmd.append('--offline')
        if args.spec_file:
            cmd.extend(['--spec-file', str(resolve_existing_path(args.spec_file))])
        if args.acceptance_file:
            cmd.extend(['--acceptance-file', str(resolve_existing_path(args.acceptance_file))])
    result = subprocess.run(
        cmd,
        cwd=Path.cwd(),
    )
    return result.returncode


def cmd_verify_issue(args):
    """FR-0540 partial: --repo auto-resolved from project-info."""
    cmd = [sys.executable, '-m', 'louke._tools.verify_issue_schema', '--spec', args.spec]
    repo = args.repo or _read_project_info('Repo').replace('github.com/', '')
    if repo:
        cmd.extend(['--repo', repo])
    result = subprocess.run(
        cmd,
        cwd=Path.cwd(),
    )
    return result.returncode


def _resolve_repo(args) -> str:
    repo = args.repo or _read_project_info('Repo').replace('github.com/', '')
    if not repo:
        try:
            out = subprocess.check_output(['gh', 'repo', 'view', '--json', 'nameWithOwner', '-q', '.nameWithOwner'],
                                          text=True, stderr=subprocess.DEVNULL)
            repo = out.strip()
        except Exception:
            repo = ''
    return repo


def _extract_frs_from_spec(spec_id: str):
    spec_path = Path(f'.louke/project/specs/{spec_id}/spec.md')
    if not spec_path.exists():
        spec_path = resolve_existing_path(spec_id)
    if not spec_path.exists():
        return '', []
    text = spec_path.read_text(encoding='utf-8', errors='replace')
    frs = sorted({m.group(1) for m in re.finditer(r'<a\s+id="fr-(\d{4})"></a>', text)})
    return text, frs


def cmd_verify_project(args):
    """FR-0740: 验证 spec 中所有 FR issue 已关联 Project."""
    project_url = _read_project_info('Project ID')
    if not project_url or not project_url.startswith('https://'):
        print('Project URL missing in project-info.md; run lk scout foundation first', file=sys.stderr)
        return 1
    spec_text, frs = _extract_frs_from_spec(args.spec)
    if not frs:
        print(f'no FR anchors in spec {args.spec}; nothing to verify', file=sys.stderr)
        return 0
    repo = _resolve_repo(args)
    if not repo:
        print('cannot resolve repo; pass --repo or set Repo in project-info.md', file=sys.stderr)
        return 1
    if args.dry_run:
        print(f'would verify {len(frs)} FR issues in {repo} against {project_url}')
        return 0
    try:
        items_out = subprocess.check_output(['gh', 'project', 'item-list', str(project_url), '--format', 'json'],
                                            text=True, stderr=subprocess.DEVNULL)
        items = json.loads(items_out)
        if isinstance(items, dict):
            items = items.get('items') or []
        linked_urls = set()
        for it in items:
            content = it.get('content') or {}
            url = content.get('url') or content.get('html_url')
            if url:
                linked_urls.add(url)
            url2 = it.get('url')
            if url2:
                linked_urls.add(url2)
    except subprocess.CalledProcessError as e:
        print(f'gh project item-list failed: {(e.stderr or e.stdout)[:200]}', file=sys.stderr)
        return 1
    issues_out = subprocess.check_output(['gh', 'issue', 'list', '--repo', repo, '--state', 'all',
                                          '--search', 'in:title [FR-]', '--json', 'number,title,url'],
                                         text=True, stderr=subprocess.DEVNULL)
    issues = json.loads(issues_out) or []
    unlinked = []
    for issue in issues:
        title = issue.get('title', '')
        m = re.search(r'\[FR-(\d{4})\]', title)
        if not m or m.group(1) not in frs:
            continue
        if issue.get('url') not in linked_urls:
            unlinked.append(issue.get('number'))
    if unlinked:
        print(f'unlinked issues: {unlinked}', file=sys.stderr)
        return 1
    print(f'all {len(frs)} FR issues linked to {project_url}')
    return 0


def cmd_quote_check(args):
    """调用 louke._tools.quote_parser (同 Sage quote-check + FR-0450 resolve_spec_path)."""
    spec_arg = args.spec
    candidate = Path(spec_arg)
    if not candidate.exists():
        default = Path(f'.louke/project/specs/{args.spec}/spec.md')
        spec_arg = str(default if default.exists() else resolve_existing_path(spec_arg))
    result = subprocess.run(
        [sys.executable, '-m', 'louke._tools.quote_parser', spec_arg, '--check-ready'],
        cwd=Path.cwd(),
    )
    return result.returncode