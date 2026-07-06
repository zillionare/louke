"""Sage commands - 需求澄清 + spec/issue 流程.

Sage 职责: 多轮提问 → spec.md → acceptance.md → 创建 GitHub issues。
所有命令通过本模块暴露。
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

from ._common import resolve_existing_path


def register(subparsers):
    parser = subparsers.add_parser('sage', help='需求澄清 (Sage)')
    sub = parser.add_subparsers(dest='command', required=True, metavar='<command>')

    # quote-check: 检查 spec.md 的 quote 状态
    p = sub.add_parser('quote-check', help='检查 spec.md 是否所有 quote 都 ✓ resolved')
    p.add_argument('--spec', required=True, help='spec-id, 例 v0.1-001-init')
    p.add_argument('--check-violations', action='store_true', help='检测 ownership violations (谁关了不是自己的 quote)')
    p.add_argument('--format', choices=['text', 'json'], default='text', help='输出格式 (默认 text)')

    # commit-spec: 封装多步 git 操作
    p = sub.add_parser('commit-spec', help='提交 spec + acceptance (git add + commit + push)')
    p.add_argument('--spec', required=True)
    p.add_argument('--message', required=True)
    p.add_argument('--no-push', action='store_true')

    # create-issues: 从 spec 创建 GitHub issues (FR-0410)
    p = sub.add_parser('create-issues', help='从 spec 创建 GitHub issues (含 schema 验证)')
    p.add_argument('--spec', required=True)
    p.add_argument('--spec-file', default='', help='直接指定 spec.md 路径')
    p.add_argument('--dry-run', action='store_true')
    p.add_argument('--skip-project', action='store_true', help='Project URL 缺失时不阻塞')

    # record-lock: 三信号锁定记录 (FR-0420)
    p = sub.add_parser('record-lock', help='记录 spec locked: true (三信号通过后)')
    p.add_argument('--spec', required=True)
    p.add_argument('--confirm', action='store_true')


def run(args):
    handlers = {
        'quote-check': cmd_quote_check,
        'commit-spec': cmd_commit_spec,
        'create-issues': cmd_create_issues,
        'lock-spec': cmd_lock_spec,
        'record-lock': cmd_record_lock,
    }
    return handlers.get(args.command, lambda _: 1)(args) or 0


def cmd_quote_check(args):
    """调用 louke._tools.quote_parser (FR-0450 resolve_spec_path).

    3 个 flag 互斥:
    --check-ready: exit 0 if 0 [open] quotes (Maestro gate; 不输出 JSON)
    --check-violations: 检测谁关了不是自己的 quote (不输出 JSON)
    --format text|json (默认 text): 列出所有 quote + 状态; 拿 JSON 时**不要**同时加 --check-ready
    """
    spec_arg = args.spec
    candidate = Path(spec_arg)
    if not candidate.exists():
        default = Path(f'.louke/project/specs/{args.spec}/spec.md')
        spec_arg = str(default if default.exists() else resolve_existing_path(spec_arg))
    cmd = [sys.executable, '-m', 'louke._tools.quote_parser', spec_arg]
    if args.check_violations:
        cmd.append('--check-violations')
    elif args.check_ready:
        cmd.append('--check-ready')
    # else: 默认行为, --format 控制输出 (text/json)
    if args.format != 'text':
        cmd += ['--format', args.format]
    result = subprocess.run(cmd, cwd=Path.cwd())
    return result.returncode


def cmd_commit_spec(args):
    """git add spec.md + acceptance.md + commit + push (封装多步)."""
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


# ---- FR-0410: create-issues ----

RE_FR_ANCHOR = re.compile(r'<a\s+id="fr-(\d{4})"></a>', re.I)
RE_FR_HEADING = re.compile(r"^###\s+(FR|NFR)-(\d{4})\s+([^\n]+)$", re.MULTILINE)
RE_AC_ANCHOR = re.compile(r'<a\s+id="ac-(fr|nfr)-(\d{4})"></a>', re.I)


def _read_project_info_value(label: str) -> str:
    # fix-002: 委托给 _common. project.toml 取代 project-info.md.
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
    return '无'


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
    """FR-0410: create GitHub issues from spec.md FR anchors (4 位 schema)."""
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
        print('Repo field missing in project.toml; run lk scout foundation first', file=sys.stderr)
        return 1
    branch = _read_project_info_value('Release Branch')
    if not branch:
        print('Release Branch field missing in project.toml; run lk scout foundation first', file=sys.stderr)
        return 1
    project_url = _read_project_info_value('Project ID')
    if not project_url and not args.skip_project:
        print('Project URL field missing in project.toml; cannot link issues', file=sys.stderr)
        print('  hint: lk scout foundation (writes Project ID) or pass --skip-project', file=sys.stderr)
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
            f'### 需求 ID\n{fr_id}\n\n'
            f'### Spec 链接\n{repo_url}/blob/{branch}/.louke/project/specs/{args.spec}/spec.md#fr-{fr_id.split("-")[1]}\n\n'
            f'### 验收标准\n{ac_value}\n'
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
    return subprocess.run([sys.executable, '-m', 'louke.__main__', *args],
                          cwd=cwd or Path.cwd()).returncode


def cmd_record_lock(args):
    """FR-0420: 3-signal lock record. lock: true is a result, not a signal."""
    if not args.confirm:
        print('User signal missing: pass --confirm after IDE confirmation', file=sys.stderr)
        return 1
    # Sage signal
    rc = cmd_quote_check(args)
    if rc != 0:
        print('Sage signal: 未通过 (quote-check exit non-zero)', file=sys.stderr)
        return rc
    # Lex signal
    for sub in (['lex', 'verify-acceptance', '--spec', args.spec],
                ['lex', 'verify-issue', '--spec', args.spec],
                ['lex', 'verify-project', '--spec', args.spec]):
        rc = _run_lk(*sub)
        if rc != 0:
            print(f'Lex signal: {sub[1]} failed (rc={rc})', file=sys.stderr)
            return rc
    spec_path = Path(f'.louke/project/specs/{args.spec}/spec.md')
    if not spec_path.exists():
        spec_path = resolve_existing_path(args.spec)
    text = spec_path.read_text(encoding='utf-8')
    locked_already = False
    if text.startswith('---\n'):
        end = text.find('\n---\n', 4)
        if end != -1:
            fm = text[4:end]
            if 'locked: true' in fm:
                locked_already = True
            else:
                text = text[:end] + f'\nlocked: true\nlocked-at: {datetime_now()}\nlocked-by: lk sage record-lock' + text[end:]
        else:
            text = f'---\nlocked: true\nlocked-at: {datetime_now()}\nlocked-by: lk sage record-lock\n---\n' + text
    else:
        text = f'---\nlocked: true\nlocked-at: {datetime_now()}\nlocked-by: lk sage record-lock\n---\n' + text
    if locked_already:
        print(f'spec already locked; idempotent (spec={args.spec})')
        return 0
    spec_path.write_text(text, encoding='utf-8')
    print(f'locked: true ({args.spec})')
    return 0


def datetime_now():
    from datetime import datetime
    return datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%SZ')