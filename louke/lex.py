"""Lex commands - spec + issue review.

Lex responsibilities: stage 1/2/3 (spec semantic review / issue coverage
validation / schema validation).
"""

import json
import re
import subprocess
import sys
from pathlib import Path

from ._common import resolve_existing_path


def register(subparsers):
    parser = subparsers.add_parser("lex", help="spec + issue review (Lex)")
    sub = parser.add_subparsers(dest="command", required=True, metavar="<command>")

    # verify-acceptance: L1-L5 structural validation (Stage 1)
    p = sub.add_parser(
        "verify-acceptance", help="run L1-L5 structural validation (Stage 1)"
    )
    p.add_argument("--spec", required=True)
    p.add_argument(
        "--repo",
        default="",
        help="owner/repo (default inferred from project-info or gh repo view)",
    )
    p.add_argument("--branch", default="", help="override default release branch")
    p.add_argument("--spec-file", default="")
    p.add_argument("--acceptance-file", default="")

    # verify-issue: L1-L8 schema validation (Stage 3)
    p = sub.add_parser("verify-issue", help="run L1-L8 schema validation (Stage 3)")
    p.add_argument("--spec", required=True)
    p.add_argument("--repo", default="")
    p.add_argument(
        "--branch", default="", help="override default release branch (fix-094)"
    )

    p = sub.add_parser(
        "verify-project", help="validate Feature issues linked to Project (FR-0740)"
    )
    p.add_argument("--spec", required=True)
    p.add_argument("--repo", default="")
    p.add_argument("--dry-run", action="store_true")

    # quote-check: reuses discuss.py (v0.7-003 inline-discussion, same as Sage quote-check)
    p = sub.add_parser(
        "quote-check", help="check whether all threads in spec.md are resolved"
    )
    p.add_argument(
        "--check-ready",
        action="store_true",
        help="exit 0 if ready (Maestro gate; no JSON output)",
    )
    p.add_argument(
        "--check-violations",
        action="store_true",
        help="detect status markers on nested reply lines",
    )
    p.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="output format (default text)",
    )
    p.add_argument("--spec", required=True)


def run(args):
    handlers = {
        "verify-acceptance": cmd_verify_acceptance,
        "verify-issue": cmd_verify_issue,
        "verify-project": cmd_verify_project,
        "quote-check": cmd_quote_check,
    }
    return handlers.get(args.command, lambda _: 1)(args) or 0


def _read_project_info(label: str) -> str:
    # fix-002: delegate to _common. project.toml replaces project-info.md.
    from ._common import _read_project_info_field

    return _read_project_info_field(label)


def cmd_verify_acceptance(args):
    """FR-0540: default branch from project-info Release Branch; --repo auto-resolved."""
    cmd = [sys.executable, "-m", "louke._tools.verify_acceptance", "--spec", args.spec]
    repo = args.repo or _read_project_info("Repo").replace("github.com/", "")
    if repo:
        cmd.extend(["--repo", repo])
    branch = args.branch or _read_project_info("Release Branch")
    if branch:
        cmd.extend(["--branch", branch])
    if args.spec_file or args.acceptance_file:
        cmd.append("--offline")
        if args.spec_file:
            cmd.extend(["--spec-file", str(resolve_existing_path(args.spec_file))])
        if args.acceptance_file:
            cmd.extend(
                ["--acceptance-file", str(resolve_existing_path(args.acceptance_file))]
            )
    result = subprocess.run(
        cmd,
        cwd=Path.cwd(),
    )
    return result.returncode


def cmd_verify_issue(args):
    """FR-0540 partial: --repo auto-resolved from project-info. fix-094: --branch."""
    cmd = [
        sys.executable,
        "-m",
        "louke._tools.verify_issue_schema",
        "--spec",
        args.spec,
    ]
    repo = args.repo or _read_project_info("Repo").replace("github.com/", "")
    if repo:
        cmd.extend(["--repo", repo])
    branch = args.branch or _read_project_info("Release Branch")
    if branch:
        cmd.extend(["--branch", branch])
    result = subprocess.run(
        cmd,
        cwd=Path.cwd(),
    )
    return result.returncode


def _resolve_repo(args) -> str:
    repo = args.repo or _read_project_info("Repo").replace("github.com/", "")
    if not repo:
        try:
            out = subprocess.check_output(
                [
                    "gh",
                    "repo",
                    "view",
                    "--json",
                    "nameWithOwner",
                    "-q",
                    ".nameWithOwner",
                ],
                text=True,
                stderr=subprocess.DEVNULL,
            )
            repo = out.strip()
        except Exception:
            repo = ""
    return repo


def _extract_frs_from_spec(spec_id: str):
    spec_path = Path(f".louke/project/specs/{spec_id}/spec.md")
    if not spec_path.exists():
        spec_path = resolve_existing_path(spec_id)
    if not spec_path.exists():
        return "", []
    text = spec_path.read_text(encoding="utf-8", errors="replace")
    frs = sorted({m.group(1) for m in re.finditer(r'<a\s+id="fr-(\d{4})"></a>', text)})
    return text, frs


def _parse_project_url(project_url: str):
    """Extract (project_number, owner) from a GitHub Projects URL.

    Accepts both user-scoped and repo-scoped project URLs::

        https://github.com/users/{owner}/projects/{number}
        https://github.com/{owner}/{repo}/projects/{number}

    Args:
        project_url: full HTTPS GitHub Projects URL.

    Returns:
        ``(project_number, owner)`` tuple of strings, or ``(None, None)`` when the
        URL does not match either shape.
    """
    m_num = re.search(r"/projects/(\d+)", project_url)
    if not m_num:
        return None, None
    # Path after host: ["users", "{owner}", "projects", "{num}"]
    # or ["{owner}", "{repo}", "projects", "{num}"]. Owner is first non-users seg.
    m_path = re.search(r"github\.com/(.+)", project_url)
    if not m_path:
        return None, None
    segments = m_path.group(1).split("/")
    if len(segments) < 3 or "projects" not in segments:
        return None, None
    if segments[0] == "users":
        owner = segments[1]
    else:
        owner = segments[0]
    return m_num.group(1), owner


def cmd_verify_project(args):
    """FR-0740: validate that all FR issues in the spec are linked to the Project."""
    project_url = _read_project_info("Project ID")
    if not project_url or not project_url.startswith("https://"):
        print(
            "Project URL missing in project.toml; run lk agent scout foundation first",
            file=sys.stderr,
        )
        return 1
    project_number, owner = _parse_project_url(project_url)
    if not project_number or not owner:
        print(
            f"cannot parse project number/owner from {project_url}",
            file=sys.stderr,
        )
        return 1
    spec_text, frs = _extract_frs_from_spec(args.spec)
    if not frs:
        print(f"no FR anchors in spec {args.spec}; nothing to verify", file=sys.stderr)
        return 0
    repo = _resolve_repo(args)
    if not repo:
        print(
            "cannot resolve repo; pass --repo or set Repo in project.toml",
            file=sys.stderr,
        )
        return 1
    if args.dry_run:
        print(f"would verify {len(frs)} FR issues in {repo} against {project_url}")
        return 0
    try:
        items_out = subprocess.check_output(
            [
                "gh",
                "project",
                "item-list",
                project_number,
                "--owner",
                owner,
                "--format",
                "json",
            ],
            text=True,
            stderr=subprocess.DEVNULL,
        )
        items = json.loads(items_out)
        if isinstance(items, dict):
            items = items.get("items") or []
        linked_urls = set()
        for it in items:
            content = it.get("content") or {}
            url = content.get("url") or content.get("html_url")
            if url:
                linked_urls.add(url)
            url2 = it.get("url")
            if url2:
                linked_urls.add(url2)
    except subprocess.CalledProcessError as e:
        print(
            f"gh project item-list failed: {(e.stderr or e.stdout)[:200]}",
            file=sys.stderr,
        )
        return 1
    issues_out = subprocess.check_output(
        [
            "gh",
            "issue",
            "list",
            "--repo",
            repo,
            "--state",
            "all",
            "--search",
            "in:title [FR-]",
            "--json",
            "number,title,body,url",
        ],
        text=True,
        stderr=subprocess.DEVNULL,
    )
    issues = json.loads(issues_out) or []
    spec_path_marker = f"specs/{args.spec}/spec.md"
    unlinked = []
    for issue in issues:
        title = issue.get("title", "")
        m = re.search(r"\[FR-(\d{4})\]", title)
        if not m or m.group(1) not in frs:
            continue
        body = issue.get("body") or ""
        if spec_path_marker not in body:
            continue
        if issue.get("url") not in linked_urls:
            unlinked.append(issue.get("number"))
    if unlinked:
        print(f"unlinked issues: {unlinked}", file=sys.stderr)
        return 1
    print(f"all {len(frs)} FR issues linked to {project_url}")
    return 0


def cmd_quote_check(args):
    """Invoke louke._tools.discuss (same as Sage quote-check + FR-0450 resolve_spec_path, v0.7-003).

    3 mutually-exclusive flags:
    --check-ready: exit 0 if is_ready (Maestro gate; emits blockers to stderr)
    --check-violations: detect status markers on nested reply lines
    --format text|json (default text): list all threads + status
    """
    spec_arg = args.spec
    if not spec_arg:
        spec_arg = _read_project_info("Spec ID")
    candidate = Path(spec_arg)
    if not candidate.exists():
        default = Path(f".louke/project/specs/{args.spec}/spec.md")
        spec_arg = str(default if default.exists() else resolve_existing_path(spec_arg))
    spec_path = Path(spec_arg)
    if not spec_path.exists():
        print(f"lex quote-check: {spec_path} not found", file=sys.stderr)
        return 2
    from ._tools import discuss

    if args.check_ready:
        design_docs = [
            spec_path,
            spec_path.parent / "architecture.md",
            spec_path.parent / "interfaces.md",
            spec_path.parent / "test-plan.md",
        ]
        existing_docs = [p for p in design_docs if p.exists()]
        all_blockers: list[str] = []
        ready = True
        for p in existing_docs:
            r, b = discuss.DiscussParser().is_ready(p)
            if not r:
                ready = False
                for bb in b:
                    all_blockers.append(f"[{p.name}] {bb}")
        if not ready:
            print(
                f"spec not ready: {len(all_blockers)} blocker(s) across "
                f"{len(existing_docs)} doc(s)",
                file=sys.stderr,
            )
            for b in all_blockers:
                print(f"  {b}", file=sys.stderr)
        return 0 if ready else 1
    if args.check_violations:
        exit_code, msg = discuss.check_violations(spec_path)
        print(msg)
        return exit_code
    exit_code, output = discuss.format_ready(spec_path, args.format)
    print(output)
    return exit_code
