"""Deprecated compatibility CLI for project onboarding commands."""

import argparse
import glob
import json
import re
import subprocess
import sys
from pathlib import Path

import yaml

from ._common import package_root
from .runtime.foundation import (
    FoundationEnsureRequest,
    FoundationError,
    FoundationGap,
    run_foundation_ensure,
)


def register(subparsers):
    parser = subparsers.add_parser(
        "scout", help="deprecated compatibility adapter for onboarding"
    )
    sub = parser.add_subparsers(dest="command", required=True, metavar="<command>")

    # identity-check: validate gh and git account consistency (Step 4a, prevents PR push success but issue create 403)
    p = sub.add_parser(
        "identity-check", help="validate gh/git account consistency (Step 4a)"
    )
    p.add_argument("--repo", required=True, help="owner/repo format")

    # foundation: full foundation flow (MVP + full P0)
    p = sub.add_parser("foundation", help="full foundation flow (Steps 1-8)")
    p.add_argument(
        "--repo",
        default="",
        help="owner/repo (auto-inferred from git remote origin if empty)",
    )
    p.add_argument("--version", required=True)
    p.add_argument(
        "--spec-id",
        default="",
        help="v{version}-NNN-{keyword}; auto-infers next NNN from --keyword + .louke/project/specs/ if empty",
    )
    p.add_argument(
        "--keyword",
        required=True,
        help="spec keyword (<=3 words, joined by -, e.g. knowledge-distillation-karpathy); agent must extract from story",
    )
    p.add_argument("--upstream", default="main")
    p.add_argument("--story", default="")
    p.add_argument("--story-file", default="")
    p.add_argument(
        "--dod",
        default="e2e all pass + unit test coverage >=95% + security review (M-SECURITY)",
    )
    p.add_argument(
        "--security-audit",
        choices=["enabled", "disabled"],
        default="",
        help="explicit; inferred from --dod if empty (backward compatible)",
    )
    p.add_argument("--no-commit", action="store_true")
    p.add_argument(
        "--no-repo",
        action="store_true",
        help="MVP mode: skip creating GitHub repo / Project / Smoke",
    )
    p.add_argument("--dry-run", action="store_true")
    p.add_argument(
        "--public", action="store_true", help="create public repo (default private)"
    )

    p = sub.add_parser(
        "invite-owner", help="add repo owner as GitHub Project collaborator"
    )
    p.add_argument("repo", help="owner/repo")
    p.add_argument("--version", required=True)
    p.add_argument(
        "--project-id",
        default="",
        help="provide Project URL/ID directly (skip list step)",
    )
    p.add_argument("--role", default="READER")
    p.add_argument("--dry-run", action="store_true")

    # commit-foundation: Step 8 multi-step git ops wrapper
    p = sub.add_parser(
        "commit-foundation",
        help="commit foundation artifacts (Step 8: git add + commit + push)",
    )
    p.add_argument("--spec-id", required=True)
    p.add_argument("--message", required=True, help="commit message")
    p.add_argument("--version", required=True, help="release branch name, e.g. v0.1")
    p.add_argument(
        "--no-push",
        action="store_true",
        help="pushes by default; --no-push skips push (FR-0580 default)",
    )

    p = sub.add_parser("install-precommit", help="install pre-commit hook (Step 5)")
    p.add_argument(
        "--force",
        action="store_true",
        help="overwrite existing .pre-commit-config.yaml",
    )


def run(args):
    handlers = {
        "identity-check": cmd_identity_check,
        "foundation": cmd_foundation,
        "invite-owner": cmd_invite_owner,
        "commit-foundation": cmd_commit_foundation,
        "install-precommit": cmd_install_precommit,
    }
    return handlers.get(args.command, lambda _: 1)(args) or 0


def cmd_identity_check(args):
    """Invoke louke._tools.check_identity."""
    result = subprocess.run(
        [sys.executable, "-m", "louke._tools.check_identity", "--repo", args.repo],
        cwd=Path.cwd(),
    )
    return result.returncode


def _gh_run(args, *cmd, check=False, capture=False):
    return subprocess.run(
        cmd, cwd=Path.cwd(), capture_output=capture, text=capture, check=check
    )


def _read_project_info(path: Path) -> str:
    """Read project.toml (after fix-002). Keep old signature (returns full file content) for _render_project_info_13_fields."""
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def _render_project_info_13_fields(
    *,
    version,
    repo,
    owner,
    repo_name,
    spec_id,
    release_branch,
    dod,
    security,
    test_framework="pytest",
    project_id="",
    smoke_issue="TODO",
    smoke_pr="TODO",
    current_stage="M-FOUND",
    created="TODO",
    backlog_project="",
) -> str:
    """Generate 13 project.toml fields (fix-002: replaces original Markdown template)."""
    return f"""[project]
version = "{version}"
repo = "github.com/{repo}"
project = "{repo_name}-{version}"
project_id = "{project_id or "TODO"}"
spec_id = "{spec_id}"
release_branch = "{release_branch}"

[meta]
created = "{created}"
current_stage = "{current_stage}"
security_audit = "{security}"
smoke_test_issue = "#{smoke_issue} (closed)"
smoke_test_pr = "#{smoke_pr} (closed)"
dod = "{dod}"
test_framework = "{test_framework}"
backlog_project = "{backlog_project or "TODO"}"
"""


def _update_project_info_fields(
    path: Path, *, project_id="", smoke_issue="", smoke_pr="", backlog_url=""
) -> None:
    """Update specific fields of project.toml (replaces only matching lines, leaves others intact).

    fix-002: targeted regex replacement instead of full-file rewrite, to avoid
    corrupting list/nested-table/other sections.
    Only handles single-line string fields; does not touch list/dict/multi-line string types.
    """
    if not path.exists():
        return

    text = path.read_text(encoding="utf-8", errors="replace")

    def _set_toml_string_field(
        text: str, key: str, new_value: str, section: str
    ) -> str:
        """Set a TOML string field. Replace if exists, add to section if not."""
        escaped = new_value.replace("\\", "\\\\").replace('"', '\\"')
        pattern = rf'^({re.escape(key)}\s*=\s*)"[^"]*"'
        if re.search(pattern, text, flags=re.MULTILINE):
            return re.sub(pattern, rf'\1"{escaped}"', text, count=1, flags=re.MULTILINE)
        section_pattern = rf"^(\[{re.escape(section)}\]\s*\n)"
        if re.search(section_pattern, text, flags=re.MULTILINE):
            return re.sub(
                section_pattern,
                rf'\1{key} = "{escaped}"\n',
                text,
                count=1,
                flags=re.MULTILINE,
            )
        return text + f'\n[{section}]\n{key} = "{escaped}"\n'

    if project_id:
        text = _set_toml_string_field(text, "project_id", project_id, "project")
    if smoke_issue:
        text = _set_toml_string_field(
            text, "smoke_test_issue", f"#{smoke_issue} (closed)", "meta"
        )
    if smoke_pr:
        text = _set_toml_string_field(
            text, "smoke_test_pr", f"#{smoke_pr} (closed)", "meta"
        )
    if backlog_url:
        text = _set_toml_string_field(text, "backlog_project", backlog_url, "meta")

    path.write_text(text, encoding="utf-8")


def _gh_api_login(args):
    """Return gh user login, or None on failure."""
    try:
        out = subprocess.check_output(
            ["gh", "api", "user", "-q", ".login"], text=True, stderr=subprocess.DEVNULL
        )
        return out.strip()
    except Exception:
        return None


def _gh_repo_view(args, repo):
    try:
        out = subprocess.check_output(
            [
                "gh",
                "repo",
                "view",
                repo,
                "--json",
                "nameWithOwner,isPrivate,defaultBranchRef",
            ],
            text=True,
            stderr=subprocess.DEVNULL,
        )
        return json.loads(out)
    except Exception:
        return None


def _gh_repo_create(args, repo, description, public):
    visibility = "--public" if public else "--private"
    try:
        subprocess.run(
            [
                "gh",
                "repo",
                "create",
                repo,
                visibility,
                "--description",
                description,
                "--add-readme",
            ],
            cwd=Path.cwd(),
            capture_output=True,
            text=True,
            check=True,
        )
        return True
    except subprocess.CalledProcessError as e:
        print(f"gh repo create failed: {e.stderr or e.stdout}", file=sys.stderr)
        return False


def _ensure_release_branch(args, owner_repo, version, upstream="main"):
    """Ensure releases/{version} exists on remote. Return True on success."""
    branch = f"releases/{version}"
    rc, out, err = _git(args, "ls-remote", "--heads", "origin", branch)
    if rc == 0 and out.strip():
        return True
    rc, _, _ = _git(args, "checkout", upstream)
    if rc != 0:
        rc, _, _ = _git(args, "checkout", "-b", upstream, f"origin/{upstream}")
    if rc != 0:
        print(f"cannot checkout {upstream}", file=sys.stderr)
        return False
    rc, _, _ = _git(args, "checkout", "-b", branch)
    if rc != 0:
        print(f"cannot create {branch}", file=sys.stderr)
        return False
    rc, _, _ = _git(args, "push", "-u", "origin", branch)
    if rc != 0:
        print(f"cannot push {branch}", file=sys.stderr)
        return False
    return True


def _gh_project_list(args, owner):
    try:
        out = subprocess.check_output(
            ["gh", "project", "list", "--owner", owner, "--format", "json"],
            text=True,
            stderr=subprocess.DEVNULL,
        )
        data = json.loads(out)
        return data.get("projects") or data if isinstance(data, list) else []
    except Exception:
        return None


def _gh_project_create(args, owner, title, description):
    try:
        out = subprocess.check_output(
            [
                "gh",
                "project",
                "create",
                "--owner",
                owner,
                "--title",
                title,
                "--description",
                description,
                "--format",
                "json",
            ],
            text=True,
            stderr=subprocess.DEVNULL,
        )
        data = json.loads(out)
        return data.get("url") or data.get("number")
    except subprocess.CalledProcessError as e:
        print(f"gh project create failed: {e.stderr}", file=sys.stderr)
        return None


def _gh_project_find(args, owner, title):
    projects = _gh_project_list(args, owner)
    if projects is None:
        return None
    for p in projects:
        if p.get("title") == title:
            return p.get("url") or p.get("id") or p.get("number")
    return None


def _ensure_project(args, owner, title, description):
    """Return Project URL or None. Reuses existing if title matches."""
    found = _gh_project_find(args, owner, title)
    if found:
        print(f"project {title} reused: {found}")
        return found
    print(f"creating project {title} under {owner}...")
    return _gh_project_create(args, owner, title, description)


def _ensure_backlog_project(args, owner, repo_name):
    """FR-0402: ensure per-repo {repo}-backlog project exists."""
    title = f"{repo_name}-backlog"
    description = f"Backlog for {repo_name}: unscheduled user stories and feature ideas"
    found = _gh_project_find(args, owner, title)
    if found:
        print(f"{title} reused (id: {found})")
        return found
    url = _gh_project_create(args, owner, title, description)
    if url is None:
        print(
            f"warn: failed to create {title}; foundation will continue but backlog not ensured",
            file=sys.stderr,
        )
        print(
            f"  retry: gh project create --owner {owner} --title {title}",
            file=sys.stderr,
        )
        return None
    print(f"{title} created: {url}")
    return url


def _gh_smoke_issue(args, repo, version):
    title = f"Good First Issue: {repo.split('/', 1)[1]}-{version}"
    body = "Scout permission smoke test"
    try:
        out = subprocess.check_output(
            [
                "gh",
                "issue",
                "create",
                "--repo",
                repo,
                "--title",
                title,
                "--body",
                body,
                "--label",
                "good first issue",
            ],
            text=True,
            stderr=subprocess.DEVNULL,
        )
        m = re.search(r"/issues/(\d+)", out)
        if m:
            num = m.group(1)
            subprocess.run(
                [
                    "gh",
                    "issue",
                    "close",
                    num,
                    "--comment",
                    "Scout permission validation done",
                ],
                cwd=Path.cwd(),
                capture_output=True,
                text=True,
            )
            return num
    except subprocess.CalledProcessError as e:
        print(f"smoke issue failed: {e.stderr or e.stdout}", file=sys.stderr)
    return None


def _gh_smoke_pr(args, repo, version):
    title = f"Good First PR: {repo.split('/', 1)[1]}-{version}"
    body = "Scout permission smoke test"
    try:
        out = subprocess.check_output(
            [
                "gh",
                "pr",
                "create",
                "--repo",
                repo,
                "--base",
                "main",
                "--head",
                f"releases/{version}",
                "--title",
                title,
                "--body",
                body,
                "--fill",
            ],
            text=True,
            stderr=subprocess.DEVNULL,
        )
        m = re.search(r"/pull/(\d+)", out)
        if m:
            num = m.group(1)
            subprocess.run(
                [
                    "gh",
                    "pr",
                    "close",
                    num,
                    "--comment",
                    "Scout permission validation done",
                    "--delete-branch=false",
                ],
                cwd=Path.cwd(),
                capture_output=True,
                text=True,
            )
            return num
    except subprocess.CalledProcessError as e:
        # PR create may fail when no diff; non-fatal per Scout step 4b
        print(f"smoke pr: {e.stderr or e.stdout}", file=sys.stderr)
    return None


def _git(args, *cmd):
    result = subprocess.run(
        ["git", *cmd], cwd=Path.cwd(), capture_output=True, text=True
    )
    return result.returncode, result.stdout, result.stderr


def _infer_repo_from_git_remote(cwd: Path) -> str | None:
    """Return owner/repo inferred from `git config remote.origin.url`, or None.

    Supports both SSH (`git@github.com:owner/repo.git`) and HTTPS
    (`https://github.com/owner/repo.git`) forms. Returns None when the remote
    is missing or unparsable so the caller can prompt for `--repo`.
    """
    rc, out, _ = _git(cwd, "config", "--get", "remote.origin.url")
    if rc != 0 or not out.strip():
        return None
    url = out.strip()
    ssh = re.match(r"git@[^:]+:(.+?)(?:\.git)?$", url)
    if ssh:
        return ssh.group(1)
    https = re.match(r"https?://[^/]+/(.+?)(?:\.git)?/?$", url)
    if https:
        return https.group(1)
    return None


# Detection priority table for pre-commit language templates.
# Ordered from highest to lowest priority; first existing file wins.
_PRE_COMMIT_DETECTORS = [
    ("pyproject.toml", "python"),
    ("package.json", "node"),
    ("go.mod", "go"),
    ("Cargo.toml", "rust"),
    ("pom.xml", "java"),
]


def _detect_precommit_language(root: Path) -> str:
    """Return the language slug for the pre-commit template to merge.

    Checks the repository root for well-known manifest files in priority
    order. If none match, returns an empty string (base-only configuration).
    """
    for filename, language in _PRE_COMMIT_DETECTORS:
        if (root / filename).exists():
            return language
    return ""


def _load_yaml(path: Path) -> dict:
    """Load a YAML file; return an empty dict if missing or unreadable."""
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data if isinstance(data, dict) else {}
    except Exception as exc:
        print(f"warn: cannot read {path}: {exc}", file=sys.stderr)
        return {}


def _merge_precommit_config(base: dict, lang: dict) -> dict:
    """Merge two pre-commit configs by concatenating their repos lists."""
    return {"repos": (base.get("repos") or []) + (lang.get("repos") or [])}


def _update_project_info_precommit(info_path: Path, language: str) -> None:
    """Update [meta].pre_commit field in project.toml."""
    label = f"{language} + base" if language else "base"
    new_value = f"installed ({label})"
    if not info_path.exists():
        return
    text = info_path.read_text(encoding="utf-8", errors="replace")
    escaped = new_value.replace("\\", "\\\\").replace('"', '\\"')
    pattern = r'^(pre_commit\s*=\s*)"[^"]*"'
    if re.search(pattern, text, flags=re.MULTILINE):
        text = re.sub(pattern, rf'\1"{escaped}"', text, count=1, flags=re.MULTILINE)
    else:
        text = re.sub(
            r"^(\[meta\]\s*\n)",
            rf'\1pre_commit = "{escaped}"\n',
            text,
            count=1,
            flags=re.MULTILINE,
        )
    info_path.write_text(text, encoding="utf-8")


def cmd_install_precommit(args):
    """Install pre-commit hooks and write merged config (FR-0100)."""
    root = Path.cwd().resolve()
    config_path = root / ".pre-commit-config.yaml"

    if config_path.exists() and not args.force:
        print(
            "pre-commit config already exists; use --force to overwrite",
            file=sys.stderr,
        )
        return 1

    language = _detect_precommit_language(root)
    templates_dir = package_root() / "templates" / "pre-commit"
    base_data = _load_yaml(templates_dir / "base.yaml")
    lang_data = _load_yaml(templates_dir / f"{language}.yaml") if language else {}
    merged = _merge_precommit_config(base_data, lang_data)

    try:
        config_path.write_text(
            yaml.safe_dump(merged, sort_keys=False), encoding="utf-8"
        )
    except Exception as exc:
        print(f"failed to write {config_path}: {exc}", file=sys.stderr)
        return 1

    result = subprocess.run(["pre-commit", "install"], cwd=root)
    if result.returncode != 0:
        print("pre-commit install failed", file=sys.stderr)
        return result.returncode

    info_path = root / ".louke" / "project" / "project.toml"
    _update_project_info_precommit(info_path, language)
    print(f"pre-commit installed ({language or 'base'} + base)")
    return 0


def _foundation_request(args, workspace: Path) -> FoundationEnsureRequest | None:
    """Adapt legacy foundation arguments into a Runtime request without writes."""
    repo = args.repo or _infer_repo_from_git_remote(workspace)
    if not repo:
        print(
            "error: --repo is required when git remote origin cannot be inferred; "
            "the deprecated adapter cannot continue",
            file=sys.stderr,
        )
        return None
    spec_id = args.spec_id
    if not spec_id:
        specs_dir = workspace / ".louke/project/specs"
        existing = []
        if specs_dir.exists():
            for directory in specs_dir.iterdir():
                match = re.match(rf"^v{re.escape(args.version)}-(\d+)-", directory.name)
                if match:
                    existing.append(int(match.group(1)))
        next_number = max(existing) + 1 if existing else 1
        spec_id = f"v{args.version}-{next_number:03d}-{args.keyword}"
    return FoundationEnsureRequest(
        workspace=workspace,
        repo=repo,
        version=args.version,
        spec_id=spec_id,
        keyword=args.keyword,
        upstream=args.upstream,
        story=args.story,
        story_file=args.story_file,
        dod=args.dod,
        security_audit=args.security_audit,
        no_commit=args.no_commit,
        no_repo=args.no_repo,
        dry_run=args.dry_run,
        public=args.public,
    )


class _ScoutFoundationAdapter:
    """Compatibility resource adapter used only behind the Runtime handler."""

    def __init__(self, request: FoundationEnsureRequest, args) -> None:
        self._request = request
        self._args = args
        self._complete = False

    def check(self, workspace: str) -> list[FoundationGap]:
        """Return one idempotent compatibility repair until the flow completes."""
        if self._complete:
            return []
        return [FoundationGap(key="compat.foundation.ensure", auto_repairable=True)]

    def create(self, workspace: str, gap: FoundationGap) -> None:
        """Run the legacy resource adapter under Runtime ownership."""
        self._create_resources(Path(workspace))
        self._complete = True

    def _create_resources(self, workspace: Path) -> None:
        request = self._request
        args = self._args
        if not request.dry_run and not request.no_commit:
            raise FoundationError(
                "deprecated foundation commit/push is unsupported; "
                "use the Runtime controlled commit program"
            )
        try:
            owner, repo_name = request.repo.split("/", 1)
        except ValueError as exc:
            raise FoundationError("repo must use owner/name form") from exc

        story_text = request.story
        if request.story_file:
            story_text = Path(request.story_file).read_text(encoding="utf-8")
        if not story_text and not sys.stdin.isatty():
            story_text = sys.stdin.read().strip()
        if not story_text:
            story_text = f"Story for {request.spec_id}"
        security = request.security_audit or (
            "disabled"
            if ("关闭安全" in request.dod or "no security" in request.dod.lower())
            else "enabled"
        )
        spec_dir = workspace / ".louke/project/specs" / request.spec_id
        info_path = workspace / ".louke/project/project.toml"
        if request.dry_run:
            self._print_dry_run(info_path, spec_dir, repo_name, security)
            return

        spec_dir.mkdir(parents=True, exist_ok=True)
        info_path.parent.mkdir(parents=True, exist_ok=True)
        if not info_path.exists():
            info_path.write_text(
                _render_project_info_13_fields(
                    version=request.version,
                    repo=request.repo,
                    owner=owner,
                    repo_name=repo_name,
                    spec_id=request.spec_id,
                    release_branch=f"releases/{request.version}",
                    dod=request.dod,
                    security=security,
                    test_framework="pytest",
                    project_id="",
                    backlog_project="",
                ),
                encoding="utf-8",
            )
        story_path = spec_dir / "story.md"
        if not story_path.exists():
            story_path.write_text(story_text + "\n", encoding="utf-8")

        if not request.no_repo:
            self._ensure_remote_resources(
                args, request, info_path, repo_name, story_text
            )

        # Identity validation is retained only as compatibility onboarding;
        # it does not write workflow state or replace the Runtime gate.
        if cmd_identity_check(argparse.Namespace(repo=request.repo)) != 0:
            raise FoundationError("compatibility identity check failed")

    def _print_dry_run(
        self, info_path: Path, spec_dir: Path, repo_name: str, security: str
    ) -> None:
        """Report compatibility operations without performing side effects."""
        request = self._request
        print(f"would write {info_path}")
        print(f"would write {spec_dir / 'story.md'}")
        print(f"would run Runtime identity check --repo {request.repo}")
        print("would run Runtime foundation program check")
        if not request.no_repo:
            login = _gh_api_login(self._args) or "<gh-user>"
            print(f"would gh repo create/view for {request.repo}")
            print(f"would ensure releases/{request.version} branch")
            print(f"would ensure project {repo_name}-{request.version} under {login}")
            print(f"would ensure project {repo_name}-backlog under {login}")
            print("would gh issue create (smoke) + close")
            print("would gh pr create (smoke) + close")

    def _ensure_remote_resources(
        self,
        args,
        request: FoundationEnsureRequest,
        info_path: Path,
        repo_name: str,
        story_text: str,
    ) -> None:
        """Run compatibility onboarding resource adapters under Runtime control."""
        login = _gh_api_login(args)
        if login is None:
            raise FoundationError(
                "gh not authenticated; use --no-repo for local foundation only"
            )
        repo_view = _gh_repo_view(args, request.repo)
        if repo_view is None:
            description = (story_text.splitlines()[0] if story_text else "").strip()[
                :200
            ]
            if not _gh_repo_create(
                args, request.repo, description or repo_name, request.public
            ):
                print(
                    "repo create failed (owner exists may be collaborator): continue",
                    file=sys.stderr,
                )
        else:
            print(f"repo {request.repo} already exists")
        if not _ensure_release_branch(
            args, request.repo, request.version, request.upstream
        ):
            raise FoundationError("release branch preparation failed")
        project_id = _ensure_project(
            args,
            login,
            f"{repo_name}-{request.version}",
            f"Work for {repo_name} release {request.version}",
        )
        backlog_url = _ensure_backlog_project(args, login, repo_name) or ""
        smoke_issue_num = _gh_smoke_issue(args, request.repo, request.version) or ""
        smoke_pr_num = _gh_smoke_pr(args, request.repo, request.version) or ""
        if project_id:
            # Compatibility onboarding only; this is not a stage authority.
            rc = run(
                argparse.Namespace(
                    command="invite-owner",
                    repo=request.repo,
                    version=request.version,
                    project_id=project_id,
                    role="READER",
                    dry_run=False,
                )
            )
            if rc != 0:
                print(
                    f"warn: invite-owner failed (rc={rc}); foundation continues",
                    file=sys.stderr,
                )
        _update_project_info_fields(
            info_path,
            project_id=project_id,
            smoke_issue=smoke_issue_num,
            smoke_pr=smoke_pr_num,
            backlog_url=backlog_url,
        )


def cmd_foundation(args):
    """Adapt the deprecated foundation CLI to the Runtime ensure handler."""
    request = _foundation_request(args, Path.cwd())
    if request is None:
        return 1
    result = run_foundation_ensure(request, _ScoutFoundationAdapter(request, args))
    if result.status != "pass":
        print(
            f"Runtime foundation ensure {result.status}: {result.details}",
            file=sys.stderr,
        )
        return 1
    print("[foundation complete]")
    return 0


def cmd_invite_owner(args):
    """FR-0120: GraphQL updateProjectV2Collaborators adds repo owner to Project as READER."""
    if not args.version:
        print("--version required", file=sys.stderr)
        return 1
    owner, repo_name = args.repo.split("/", 1)
    title = f"{repo_name}-{args.version}"
    login = _gh_api_login(args)
    if login is None:
        print("gh not authenticated; please run gh auth login", file=sys.stderr)
        return 1
    project_url = args.project_id
    if not project_url:
        project_url = _gh_project_find(args, login, title)
        if not project_url:
            print(
                f"project {title} not found under {login}; create via: gh project create --owner {login} --title {title}",
                file=sys.stderr,
            )
            return 1
    # resolve owner userId via GraphQL
    query = json.dumps({"query": f'query {{ user(login: "{owner}") {{ id }} }}'})
    try:
        out = subprocess.check_output(
            ["gh", "api", "graphql", "-f", f"query={query}"],
            text=True,
            stderr=subprocess.DEVNULL,
        )
        data = json.loads(out)
        owner_id = data.get("data", {}).get("user", {}).get("id")
    except subprocess.CalledProcessError as e:
        print(f"GraphQL owner lookup failed: {e.stderr or e.stdout}", file=sys.stderr)
        return 1
    if not owner_id:
        print(f"GraphQL returned no id for user {owner}", file=sys.stderr)
        return 1
    if args.dry_run:
        print(f"would add {owner} ({owner_id}) to project {project_url} as {args.role}")
        return 0
    # mutation
    mutation = json.dumps(
        {
            "query": (
                "mutation($projectId: ID!, $userId: ID!, $role: ProjectV2CollaboratorRole!) {"
                " updateProjectV2Collaborators(input: { projectId: $projectId, userId: $userId, role: $role }) {"
                " collaborator { user { login } } } }"
            ),
            "variables": {
                "projectId": str(project_url),
                "userId": owner_id,
                "role": args.role,
            },
        }
    )
    try:
        subprocess.run(
            ["gh", "api", "graphql", "--input", "-"],
            input=mutation,
            text=True,
            capture_output=True,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        print(
            f"GraphQL mutation failed: {(e.stderr or e.stdout)[:200]}", file=sys.stderr
        )
        return 1
    print(f"{owner} added to project '{title}' as {args.role}")
    return 0


def cmd_commit_foundation(args):
    """Step 8 multi-step git ops wrapper (FR-0530 glob fix + FR-0580 default no-push)."""
    spec_path = f".louke/project/specs/{args.spec_id}"
    spec_files = sorted(glob.glob(f"{spec_path}/*.md"))
    if not spec_files:
        print(f"warn: no markdown files under {spec_path}", file=sys.stderr)
    add_targets = [*spec_files, ".louke/project/project.toml"]
    cmds = [
        ["git", "add", *add_targets],
        ["git", "commit", "-m", args.message],
    ]
    if not args.no_push:
        cmds.append(["git", "push", "-u", "origin", f"releases/{args.version}"])
    for cmd in cmds:
        result = subprocess.run(cmd, cwd=Path.cwd())
        if result.returncode != 0:
            print(f"failed: {' '.join(cmd)}", file=sys.stderr)
            return result.returncode
    return 0
