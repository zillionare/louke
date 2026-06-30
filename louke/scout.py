"""Scout commands - 项目奠基.

Scout 职责: 收集项目信息、创建 repo、创建 project、验证权限。
所有命令通过本模块暴露。
"""
import argparse
import glob
import json
import re
import subprocess
import sys
from pathlib import Path


def register(subparsers):
    parser = subparsers.add_parser('scout', help='项目奠基 (Scout)')
    sub = parser.add_subparsers(dest='command', required=True, metavar='<command>')

    # identity-check: 验证 gh 与 git 账号一致 (Step 4a, 防止 PR push 成功但 issue create 403)
    p = sub.add_parser('identity-check', help='验证 gh/git 账号一致 (Step 4a)')
    p.add_argument('--repo', required=True, help='owner/repo 格式')

    # foundation: 完整奠基流程 (MVP + 完整 P0)
    p = sub.add_parser('foundation', help='完整奠基流程 (Steps 1-8)')
    p.add_argument('--repo', required=True)
    p.add_argument('--version', required=True)
    p.add_argument('--spec-id', required=True)
    p.add_argument('--upstream', default='main')
    p.add_argument('--story', default='')
    p.add_argument('--story-file', default='')
    p.add_argument('--dod', default='e2e 全通过 + 单元测试覆盖率 ≥95% + 安全审查 (M-SECURITY)')
    p.add_argument('--no-commit', action='store_true')
    p.add_argument('--no-repo', action='store_true', help='MVP 模式：跳过创建 GitHub repo / Project / Smoke')
    p.add_argument('--dry-run', action='store_true')
    p.add_argument('--public', action='store_true', help='创建 public repo（默认 private）')

    p = sub.add_parser('invite-owner', help='把 repo owner 加入 GitHub Project collaborator')
    p.add_argument('repo', help='owner/repo')
    p.add_argument('--version', required=True)
    p.add_argument('--project-id', default='', help='直接提供 Project URL/ID（跳过 list 步骤）')
    p.add_argument('--role', default='READER')
    p.add_argument('--dry-run', action='store_true')

    # commit-foundation: Step 8 多步 git 操作封装
    p = sub.add_parser('commit-foundation', help='提交奠基产物 (Step 8: git add + commit + push)')
    p.add_argument('--spec-id', required=True)
    p.add_argument('--message', required=True, help='commit message')
    p.add_argument('--version', required=True, help='release 分支名, 例 v0.1')
    p.add_argument('--no-push', action='store_true', help='默认会 push；--no-push 跳过 push（FR-0580 默认）')


def run(args):
    handlers = {
        'identity-check': cmd_identity_check,
        'foundation': cmd_foundation,
        'invite-owner': cmd_invite_owner,
        'commit-foundation': cmd_commit_foundation,
    }
    return handlers.get(args.command, lambda _: 1)(args) or 0


def cmd_identity_check(args):
    """调用 louke._tools.check_identity."""
    result = subprocess.run(
        [sys.executable, '-m', 'louke._tools.check_identity', '--repo', args.repo],
        cwd=Path.cwd(),
    )
    return result.returncode


def _gh_run(args, *cmd, check=False, capture=False):
    return subprocess.run(cmd, cwd=Path.cwd(), capture_output=capture, text=capture, check=check)


def _read_project_info(path: Path) -> str:
    if not path.exists():
        return ''
    return path.read_text(encoding='utf-8', errors='replace')


def _render_project_info_12_fields(*, version, repo, owner, repo_name, spec_id, release_branch, dod, security, project_id='', smoke_issue='TODO', smoke_pr='TODO', current_stage='M-FOUND', created='TODO', backlog_project='') -> str:
    return f"""# Project Info

- **Version**: {version}
- **Repo**: github.com/{repo}
- **Project**: {repo_name}-{version}
- **Project ID**: {project_id or 'TODO'}
- **Spec ID**: {spec_id}
- **Release Branch**: `{release_branch}`
- **Smoke Test Issue**: #{smoke_issue} (closed)
- **Smoke Test PR**: #{smoke_pr} (closed)
- **DoD**: {dod}
- **Security Audit**: {security}
- **Current Stage**: {current_stage}
- **Backlog Project**: {backlog_project or 'TODO'}
- **Created**: {created}
"""


def _gh_api_login(args):
    """Return gh user login, or None on failure."""
    try:
        out = subprocess.check_output(['gh', 'api', 'user', '-q', '.login'], text=True, stderr=subprocess.DEVNULL)
        return out.strip()
    except Exception:
        return None


def _gh_repo_view(args, repo):
    try:
        out = subprocess.check_output(['gh', 'repo', 'view', repo, '--json', 'nameWithOwner,isPrivate,defaultBranchRef'], text=True, stderr=subprocess.DEVNULL)
        return json.loads(out)
    except Exception:
        return None


def _gh_repo_create(args, repo, description, public):
    visibility = '--public' if public else '--private'
    try:
        subprocess.run(['gh', 'repo', 'create', repo, visibility, '--description', description, '--add-readme'],
                       cwd=Path.cwd(), capture_output=True, text=True, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f'gh repo create failed: {e.stderr or e.stdout}', file=sys.stderr)
        return False


def _ensure_release_branch(args, owner_repo, version, upstream='main'):
    """Ensure releases/{version} exists on remote. Return True on success."""
    branch = f'releases/{version}'
    rc, out, err = _git(args, 'ls-remote', '--heads', 'origin', branch)
    if rc == 0 and out.strip():
        return True
    rc, _, _ = _git(args, 'checkout', upstream)
    if rc != 0:
        rc, _, _ = _git(args, 'checkout', '-b', upstream, f'origin/{upstream}')
    if rc != 0:
        print(f'cannot checkout {upstream}', file=sys.stderr)
        return False
    rc, _, _ = _git(args, 'checkout', '-b', branch)
    if rc != 0:
        print(f'cannot create {branch}', file=sys.stderr)
        return False
    rc, _, _ = _git(args, 'push', '-u', 'origin', branch)
    if rc != 0:
        print(f'cannot push {branch}', file=sys.stderr)
        return False
    return True


def _gh_project_list(args, owner):
    try:
        out = subprocess.check_output(['gh', 'project', 'list', '--owner', owner, '--format', 'json'],
                                      text=True, stderr=subprocess.DEVNULL)
        data = json.loads(out)
        return data.get('projects') or data if isinstance(data, list) else []
    except Exception:
        return None


def _gh_project_create(args, owner, title, description):
    try:
        out = subprocess.check_output(['gh', 'project', 'create', '--owner', owner, '--title', title,
                                       '--description', description, '--format', 'json'],
                                      text=True, stderr=subprocess.DEVNULL)
        data = json.loads(out)
        return data.get('url') or data.get('number')
    except subprocess.CalledProcessError as e:
        print(f'gh project create failed: {e.stderr}', file=sys.stderr)
        return None


def _gh_project_find(args, owner, title):
    projects = _gh_project_list(args, owner)
    if projects is None:
        return None
    for p in projects:
        if p.get('title') == title:
            return p.get('url') or p.get('id') or p.get('number')
    return None


def _ensure_project(args, owner, title, description):
    """Return Project URL or None. Reuses existing if title matches."""
    found = _gh_project_find(args, owner, title)
    if found:
        print(f'project {title} reused: {found}')
        return found
    print(f'creating project {title} under {owner}...')
    return _gh_project_create(args, owner, title, description)


def _ensure_backlog_project(args, owner, repo_name):
    """FR-0402: ensure per-repo {repo}-backlog project exists."""
    title = f'{repo_name}-backlog'
    description = f'Backlog for {repo_name}: unscheduled user stories and feature ideas'
    found = _gh_project_find(args, owner, title)
    if found:
        print(f'{title} reused (id: {found})')
        return found
    url = _gh_project_create(args, owner, title, description)
    if url is None:
        print(f'warn: failed to create {title}; foundation will continue but backlog not ensured', file=sys.stderr)
        print(f'  retry: gh project create --owner {owner} --title {title}', file=sys.stderr)
        return None
    print(f'{title} created: {url}')
    return url


def _gh_smoke_issue(args, repo, version):
    title = f'Good First Issue: {repo.split("/",1)[1]}-{version}'
    body = 'Scout 权限冒烟测试'
    try:
        out = subprocess.check_output(['gh', 'issue', 'create', '--repo', repo, '--title', title,
                                       '--body', body, '--label', 'good first issue'],
                                      text=True, stderr=subprocess.DEVNULL)
        m = re.search(r'/issues/(\d+)', out)
        if m:
            num = m.group(1)
            subprocess.run(['gh', 'issue', 'close', num, '--comment', 'Scout 权限验证完成'],
                           cwd=Path.cwd(), capture_output=True, text=True)
            return num
    except subprocess.CalledProcessError as e:
        print(f'smoke issue failed: {e.stderr or e.stdout}', file=sys.stderr)
    return None


def _gh_smoke_pr(args, repo, version):
    title = f'Good First PR: {repo.split("/",1)[1]}-{version}'
    body = 'Scout 权限冒烟测试'
    try:
        out = subprocess.check_output(['gh', 'pr', 'create', '--repo', repo,
                                       '--base', 'main', '--head', f'releases/{version}',
                                       '--title', title, '--body', body, '--fill'],
                                      text=True, stderr=subprocess.DEVNULL)
        m = re.search(r'/pull/(\d+)', out)
        if m:
            num = m.group(1)
            subprocess.run(['gh', 'pr', 'close', num, '--comment', 'Scout 权限验证完成', '--delete-branch=false'],
                           cwd=Path.cwd(), capture_output=True, text=True)
            return num
    except subprocess.CalledProcessError as e:
        # PR create may fail when no diff; non-fatal per Scout step 4b
        print(f'smoke pr: {e.stderr or e.stdout}', file=sys.stderr)
    return None


def _git(args, *cmd):
    return subprocess.run(['git', *cmd], cwd=Path.cwd(), capture_output=True, text=True).returncode, None, None


def cmd_foundation(args):
    """Scout foundation: MVP (FR-0400) + 完整 P0 (FR-0401) + backlog (FR-0402)."""
    cwd = Path.cwd()
    spec_dir = cwd / '.louke/project/specs' / args.spec_id
    info_path = cwd / '.louke/project/project-info.md'
    story_text = args.story
    if args.story_file:
        story_text = Path(args.story_file).read_text(encoding='utf-8')
    if not story_text and not sys.stdin.isatty():
        story_text = sys.stdin.read().strip()
    if not story_text:
        story_text = f'Story for {args.spec_id}'
    owner, repo_name = args.repo.split('/', 1)
    security = 'disabled' if ('关闭安全' in args.dod or 'no security' in args.dod.lower()) else 'enabled'
    release_branch = f'releases/{args.version}'

    full_p0 = not args.no_repo

    project_id = ''
    smoke_issue_num = ''
    smoke_pr_num = ''
    backlog_url = ''

    if args.dry_run:
        print(f'would write {info_path}')
        print(f'would write {spec_dir / "story.md"}')
        print(f'would run lk scout identity-check --repo {args.repo}')
        print(f'would run lk warden foundation-check --repo {args.repo} --version {args.version} --spec-id {args.spec_id}')
        if full_p0:
            print(f'would gh repo create/view for {args.repo}')
            print(f'would ensure releases/{args.version} branch')
            print(f'would ensure project {repo_name}-{args.version} under {owner}')
            print(f'would ensure project {repo_name}-backlog under {owner}')
            print(f'would gh issue create (smoke) + close')
            print(f'would gh pr create (smoke) + close')
        return 0

    spec_dir.mkdir(parents=True, exist_ok=True)
    info_path.parent.mkdir(parents=True, exist_ok=True)
    if not info_path.exists():
        info_path.write_text(
            _render_project_info_12_fields(
                version=args.version, repo=args.repo, owner=owner,
                repo_name=repo_name, spec_id=args.spec_id,
                release_branch=release_branch, dod=args.dod,
                security=security, project_id='', backlog_project='',
            ),
            encoding='utf-8',
        )
    story_path = spec_dir / 'story.md'
    if not story_path.exists():
        story_path.write_text(story_text + '\n', encoding='utf-8')

    if full_p0:
        login = _gh_api_login(args)
        if login is None:
            print('gh 未认证；请运行 gh auth login 或使用 --no-repo 仅做 MVP', file=sys.stderr)
            return 1
        owner_to_use = login
        # Step 2: ensure repo
        repo_view = _gh_repo_view(args, args.repo)
        if repo_view is None:
            description = (story_text.splitlines()[0] if story_text else '').strip()[:200]
            ok = _gh_repo_create(args, args.repo, description or f'{repo_name}', args.public)
            if not ok:
                print(f'repo create failed (owner exists may be collaborator): continue', file=sys.stderr)
        else:
            print(f'repo {args.repo} already exists')
        # Step 4: release branch
        if not _ensure_release_branch(args, args.repo, args.version, args.upstream):
            return 1
        # Step 3: per-release Project
        project_id = _ensure_project(args, owner_to_use, f'{repo_name}-{args.version}',
                                     f'Work for {repo_name} release {args.version}')
        # Step 3.5: per-repo backlog Project (FR-0402; soft-fail)
        backlog_url = _ensure_backlog_project(args, owner_to_use, repo_name) or ''
        # Step 4b: smoke issue + PR
        smoke_issue_num = _gh_smoke_issue(args, args.repo, args.version) or ''
        smoke_pr_num = _gh_smoke_pr(args, args.repo, args.version) or ''
        # Step 6: invite-owner
        if project_id:
            from . import scout as _self
            rc = _self.run(argparse.Namespace(
                command='invite-owner', repo=args.repo, version=args.version,
                project_id=project_id, role='READER', dry_run=False,
            ))
            if rc != 0:
                print(f'warn: invite-owner failed (rc={rc}); foundation continues', file=sys.stderr)
        # Update project-info.md with resolved IDs
        info_text = _read_project_info(info_path)
        if project_id:
            info_text = re.sub(r'- \*\*Project ID\*\*:[^\n]*', f'- **Project ID**: {project_id}', info_text)
        if smoke_issue_num:
            info_text = re.sub(r'- \*\*Smoke Test Issue\*\*:[^\n]*', f'- **Smoke Test Issue**: #{smoke_issue_num} (closed)', info_text)
        if smoke_pr_num:
            info_text = re.sub(r'- \*\*Smoke Test PR\*\*:[^\n]*', f'- **Smoke Test PR**: #{smoke_pr_num} (closed)', info_text)
        if backlog_url:
            info_text = re.sub(r'- \*\*Backlog Project\*\*:[^\n]*', f'- **Backlog Project**: {backlog_url}', info_text)
        info_path.write_text(info_text, encoding='utf-8')

    # Step 4a / 4: identity + foundation-check (existing tools)
    for cmd in (
        [sys.executable, '-m', 'louke.__main__', 'scout', 'identity-check', '--repo', args.repo],
        [sys.executable, '-m', 'louke.__main__', 'warden', 'foundation-check',
         '--repo', args.repo, '--version', args.version, '--spec-id', args.spec_id],
    ):
        result = subprocess.run(cmd, cwd=cwd)
        if result.returncode != 0:
            print(f"failed: {' '.join(cmd)}", file=sys.stderr)
            return result.returncode
    if not args.no_commit:
        return cmd_commit_foundation(argparse.Namespace(
            spec_id=args.spec_id,
            message=f'story/prd: initial draft for {args.spec_id}',
            version=args.version,
            no_push=False,
        ))
    print('[项目奠基完成]')
    return 0


def cmd_invite_owner(args):
    """FR-0120: GraphQL updateProjectV2Collaborators 把 repo owner 加入 Project READER."""
    if not args.version:
        print('--version required', file=sys.stderr)
        return 1
    owner, repo_name = args.repo.split('/', 1)
    title = f'{repo_name}-{args.version}'
    login = _gh_api_login(args)
    if login is None:
        print('gh 未认证；请运行 gh auth login', file=sys.stderr)
        return 1
    project_url = args.project_id
    if not project_url:
        project_url = _gh_project_find(args, login, title)
        if not project_url:
            print(f'project {title} not found under {login}; create via: gh project create --owner {login} --title {title}', file=sys.stderr)
            return 1
    # resolve owner userId via GraphQL
    query = json.dumps({'query': f'query {{ user(login: "{owner}") {{ id }} }}'})
    try:
        out = subprocess.check_output(['gh', 'api', 'graphql', '-f', f'query={query}'], text=True, stderr=subprocess.DEVNULL)
        data = json.loads(out)
        owner_id = data.get('data', {}).get('user', {}).get('id')
    except subprocess.CalledProcessError as e:
        print(f'GraphQL owner lookup failed: {e.stderr or e.stdout}', file=sys.stderr)
        return 1
    if not owner_id:
        print(f'GraphQL returned no id for user {owner}', file=sys.stderr)
        return 1
    if args.dry_run:
        print(f'would add {owner} ({owner_id}) to project {project_url} as {args.role}')
        return 0
    # mutation
    mutation = json.dumps({
        'query': (
            'mutation($projectId: ID!, $userId: ID!, $role: ProjectV2CollaboratorRole!) {'
            ' updateProjectV2Collaborators(input: { projectId: $projectId, userId: $userId, role: $role }) {'
            ' collaborator { user { login } } } }'
        ),
        'variables': {'projectId': str(project_url), 'userId': owner_id, 'role': args.role},
    })
    try:
        subprocess.run(['gh', 'api', 'graphql', '--input', '-'],
                       input=mutation, text=True, capture_output=True, check=True)
    except subprocess.CalledProcessError as e:
        print(f'GraphQL mutation failed: {(e.stderr or e.stdout)[:200]}', file=sys.stderr)
        return 1
    print(f'{owner} 已加入 project \'{title}\' 为 {args.role}')
    return 0


def cmd_commit_foundation(args):
    """Step 8 多步 git 操作封装 (FR-0530 glob fix + FR-0580 默认 no-push)."""
    spec_path = f".louke/project/specs/{args.spec_id}"
    spec_files = sorted(glob.glob(f"{spec_path}/*.md"))
    if not spec_files:
        print(f"warn: no markdown files under {spec_path}", file=sys.stderr)
    add_targets = [*spec_files, '.louke/project/project-info.md']
    cmds = [
        ['git', 'add', *add_targets],
        ['git', 'commit', '-m', args.message],
    ]
    if not args.no_push:
        cmds.append(['git', 'push', '-u', 'origin', f'releases/{args.version}'])
    for cmd in cmds:
        result = subprocess.run(cmd, cwd=Path.cwd())
        if result.returncode != 0:
            print(f"failed: {' '.join(cmd)}", file=sys.stderr)
            return result.returncode
    return 0