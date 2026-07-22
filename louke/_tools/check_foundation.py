#!/usr/bin/env python3
"""
check_foundation.py — validate whether the Runtime foundation program is complete

Why this check is needed:
  The foundation program involves multiple GitHub operations (repo/project/issue/PR) and local file creation.
  Doing these checks inline in the agent is error-prone and hard to maintain. This script centralizes
  all checks in one place and provides consistent PASS/REJECT output.

  Design goals:
  - Zero LLM tokens: pure structural checks
  - Zero extra dependencies: Python stdlib only
  - Idempotent: can be re-run, never creates or modifies any resource
  - Composable: each check is independent and can be skipped individually

Checks (F1-F11):
  F1 Repo accessible:        gh repo view succeeds
  F2 Project exists:        gh project list contains {repo}-{version}
  F3 Test Issue compliant:   title "Good First Issue: {repo}-{version}", state closed
  F4 Test PR compliant:      title "Good First PR: {repo}-{version}", state closed
  F5 Agent files exist:      agents/*.md files exist
  F6 project.toml complete:  .louke/project/project.toml contains required fields (after fix-002)
                          [project] section: version, repo, project, spec_id, release_branch
                          [meta] section: smoke_test_issue, smoke_test_pr, dod, security_audit, current_stage, created
  F7 story.md exists:        .louke/project/specs/{spec-id}/story.md exists
  F8 Dev branch exists:      releases/{version} branch exists on remote (based on main)
  F9 Spec ID format compliant: matches v{version}-{NNN}-{keyword}
  F10 Unmerged releases/*:  no unmerged releases/*; if any exist, project.toml needs
                          [meta].acknowledged_orphan_releases list as a warning pass
  F11 Identity consistency: gh and git same identity (delegates to check_identity.py L1-L5)

Usage:
  python -m louke._tools.check_foundation <owner/repo> --version <version> --spec-id <spec-id>
  python -m louke._tools.check_foundation zillionare/louke --version v0.1 --spec-id v0.1-001-louke

Optional flags:
  --project-id NUMBER   GitHub Project numeric ID (skip auto-lookup)
  --skip F3,F4          skip specific checks (comma-separated)
  --upstream BRANCH     upstream branch the dev branch is based on (skips F8 by default; pass main to enable)
  --offline             offline mode: only run local checks (F5, F6, F7, F9, F10)
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


# ---------- Data structures ----------


@dataclass
class CheckResult:
    code: str  # F1, F2, ...
    name: str  # check name
    passed: bool = False
    message: str = ""  # details on pass
    error: str = ""  # reason on failure
    warning: bool = False  # True = warning rather than blocking


# ---------- Helper functions ----------


def _gh(*args: str) -> tuple[str, bool]:
    """Run a gh command, returns (stdout, success)"""
    try:
        out = (
            subprocess.check_output(["gh", *args], stderr=subprocess.STDOUT)
            .decode()
            .strip()
        )
        return out, True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "", False


def _gh_json(*args: str) -> tuple[dict | list | None, bool]:
    """Run a gh command and parse its JSON output"""
    text, ok = _gh(*args)
    if not ok or not text:
        return None, False
    try:
        return json.loads(text), True
    except json.JSONDecodeError:
        return None, False


# ---------- Checks ----------


def check_f1_repo(repo: str) -> CheckResult:
    """F1: Repo accessible"""
    r = CheckResult(code="F1", name="Repo accessible")
    data, ok = _gh_json("repo", "view", repo, "--json", "nameWithOwner,isPrivate")
    if not ok or not data:
        r.error = f"unable to access repo {repo} — please confirm the repo exists and the current token has permission"
        return r
    visibility = "private" if data.get("isPrivate") else "public"
    r.passed = True
    r.message = f"{data['nameWithOwner']} ({visibility})"
    return r


def check_f2_project(repo: str, version: str, project_id: int | None) -> CheckResult:
    """F2: GitHub Project exists (allowed to be created under repo owner or gh identity)"""
    r = CheckResult(code="F2", name="Project exists")
    expected_title = f"{repo.split('/')[-1]}-{version}"

    if project_id:
        # Validate the specified ID directly
        data, ok = _gh_json(
            "project",
            "view",
            str(project_id),
            "--owner",
            repo.split("/")[0],
            "--json",
            "title,number",
        )
        if ok and data:
            r.passed = True
            r.message = f"{data['title']} (#{data['number']})"
            return r

    # Search project list — check both repo owner and gh identity (collaborator mode)
    repo_owner = repo.split("/")[0]
    gh_user_out, _ = _gh("api", "user", "-q", ".login")
    gh_user = gh_user_out.strip()
    owners_to_check = list({repo_owner, gh_user})  # dedupe preserving order

    for owner in owners_to_check:
        data, ok = _gh_json(
            "project", "list", "--owner", owner, "--format", "json", "--limit", "50"
        )
        if not ok or not data:
            continue
        # gh project list --format json returns {"projects": [...], "totalCount": N}
        if isinstance(data, dict):
            projects = data.get("projects", [])
        elif isinstance(data, list):
            projects = data
        else:
            continue
        for p in projects:
            title = p.get("title", "")
            if expected_title.lower() in title.lower():
                project_owner = p.get("owner", {}).get("login", "?")
                r.passed = True
                r.message = f"{title} (#{p.get('number', '?')}, owner: {project_owner})"
                return r

    r.error = (
        f"Project '{expected_title}' not found — please create it first. "
        f"It can be created under {repo_owner} or {gh_user}. "
        f"If created under {gh_user}, manually set {repo_owner} as project READER in the GitHub UI, "
        f"or call the gh api updateProjectV2Collaborators API"
    )
    return r


def check_f3_test_issue(repo: str, version: str) -> CheckResult:
    """F3: Test Issue exists and is closed."""
    r = CheckResult(code="F3", name="Test Issue compliant")
    expected_title = f"Good First Issue: {repo.split('/')[-1]}-{version}"

    data, ok = _gh_json(
        "issue",
        "list",
        "--repo",
        repo,
        "--state",
        "all",
        "--limit",
        "100",
        "--json",
        "number,title,state",
    )
    if not ok or not data:
        r.error = "unable to list issues — please confirm gh has repo access"
        return r

    for issue in data if isinstance(data, list) else []:
        if expected_title.lower() in issue.get("title", "").lower():
            if issue.get("state") == "CLOSED":
                r.passed = True
                r.message = f"#{issue['number']} (closed)"
                return r
            r.error = f"Test Issue #{issue['number']} state is {issue.get('state')} — needs CLOSED"
            return r

    r.error = f"Test Issue '{expected_title}' not found — foundation prerequisites are incomplete"
    return r


def check_f4_test_pr(repo: str, version: str) -> CheckResult:
    """F4: Test PR exists and is closed."""
    r = CheckResult(code="F4", name="Test PR compliant")
    expected_title = f"Good First PR: {repo.split('/')[-1]}-{version}"

    data, ok = _gh_json(
        "pr",
        "list",
        "--repo",
        repo,
        "--state",
        "all",
        "--limit",
        "100",
        "--json",
        "number,title,state",
    )
    if not ok or not data:
        r.error = "unable to list PRs — please confirm gh has repo access"
        return r

    for pr in data if isinstance(data, list) else []:
        if expected_title.lower() in pr.get("title", "").lower():
            state = pr.get("state")
            if state in ("CLOSED", "MERGED"):
                r.passed = True
                r.message = f"#{pr['number']} ({state.lower()})"
                return r
            r.error = f"Test PR #{pr['number']} state is {state} — needs CLOSED/MERGED"
            return r

    r.error = f"Test PR '{expected_title}' not found — foundation prerequisites are incomplete"
    return r


def check_f5_agents() -> CheckResult:
    """F5: Agent prompt files exist (in .opencode/agents/, the OpenCode output).

    Agents are owned by the louke package — they never live in the project
    source tree. `lk board opencode` materialises them into .opencode/agents/
    so the OpenCode IDE can consume them; that's the canonical location this
    check inspects.
    """
    r = CheckResult(code="F5", name="Agent files exist")
    agents_dir = Path(".opencode/agents")
    if not agents_dir.is_dir():
        r.error = (
            ".opencode/agents/ directory does not exist — "
            "run `lk board opencode` (or `lk init`) to materialise agents"
        )
        return r

    md_files = list(agents_dir.glob("*.md"))
    if not md_files:
        r.error = "no .md files found under .opencode/agents/"
        return r

    r.passed = True
    r.message = f"{len(md_files)} Agent prompt files"
    return r


# Required fields in project.toml (after fix-002, migrated from Markdown to TOML)
# [project] section fields (including project_id spec_id release_branch)
# [meta] section fields (including created security_audit etc.)
REQUIRED_PROJECT_INFO_FIELDS = [
    ("project", "version"),
    ("project", "repo"),
    ("project", "project"),
    ("project", "project_id"),
    ("project", "spec_id"),
    ("project", "release_branch"),
    ("meta", "smoke_test_issue"),
    ("meta", "smoke_test_pr"),
    ("meta", "dod"),
    ("meta", "security_audit"),
    ("meta", "current_stage"),
    ("meta", "created"),
    ("meta", "test_framework"),
]

RE_SPEC_ID = re.compile(r"^v[\w.]+-\d{3}-[\w-]+$")


def check_f6_project_info(spec_id: str | None) -> CheckResult:
    """F6: project.toml exists and contains required fields (after fix-002 migrated from Markdown to TOML)"""
    r = CheckResult(code="F6", name="project.toml complete")
    pi_path = Path(".louke/project/project.toml")
    if not pi_path.is_file():
        r.error = ".louke/project/project.toml does not exist"
        return r

    # Parse with tomllib
    try:
        import tomllib
    except ImportError:
        try:
            import tomli as tomllib  # type: ignore
        except ImportError:
            r.error = "Python tomllib/tomli unavailable, cannot parse project.toml"
            return r
    try:
        with open(pi_path, "rb") as f:
            data = tomllib.load(f)
    except Exception as e:
        r.error = f"project.toml parse failed: {e}"
        return r

    # Check required fields
    missing = []
    for section, key in REQUIRED_PROJECT_INFO_FIELDS:
        if section not in data or key not in data[section]:
            missing.append(f"[{section}].{key}")
    if missing:
        r.error = f"project.toml missing fields: {', '.join(missing)}"
        return r

    # If spec_id is provided, validate F9 (Spec ID format)
    if spec_id:
        if not RE_SPEC_ID.match(spec_id):
            r.error = f"Spec ID format non-compliant: '{spec_id}' — expected v{{version}}-{{NNN}}-{{keyword}} (e.g. v0.3-001-adopt-mode)"
            return r
        actual_spec_id = data.get("project", {}).get("spec_id", "")
        if actual_spec_id != spec_id:
            r.error = f"Spec ID in project.toml does not match argument '{spec_id}'"
            return r

    r.passed = True
    r.message = f"contains {len(REQUIRED_PROJECT_INFO_FIELDS)} required fields"
    return r


def check_f7_story(spec_id: str) -> CheckResult:
    """F7: story.md exists"""
    r = CheckResult(code="F7", name="story.md exists")
    if not spec_id:
        r.error = "no --spec-id provided, cannot check story.md"
        return r

    story_path = Path(f".louke/project/specs/{spec_id}/story.md")
    if not story_path.is_file():
        r.error = f".louke/project/specs/{spec_id}/story.md does not exist"
        return r

    size = story_path.stat().st_size
    r.passed = True
    r.message = f".louke/project/specs/{spec_id}/story.md ({size} bytes)"
    return r


def check_f8_dev_branch(version: str, upstream: str | None) -> CheckResult:
    """F8: dev branch releases/{version} exists on remote"""
    r = CheckResult(code="F8", name="Dev branch exists")
    branch = f"releases/{version}"

    # Use git ls-remote directly (does not depend on gh, also avoids gh api nested shell expansion pitfalls)
    try:
        ls_out = (
            subprocess.check_output(
                ["git", "ls-remote", "--heads", "origin", branch],
                stderr=subprocess.DEVNULL,
            )
            .decode()
            .strip()
        )
        if ls_out:
            r.passed = True
            r.message = f"remote branch {branch} exists"
            if upstream:
                r.message += f" (based on {upstream})"
            return r
    except Exception as e:
        r.warning = True
        r.message = f"unable to list remote branches (downgraded to warning): {e}"
        return r

    r.error = f"remote branch {branch} does not exist — please create it first: git checkout -b {branch} && git push -u origin {branch}"
    return r


def check_f9_spec_id(spec_id: str) -> CheckResult:
    """F9: Spec ID format compliant"""
    r = CheckResult(code="F9", name="Spec ID format compliant")
    if not spec_id:
        r.error = "no --spec-id provided"
        return r

    if RE_SPEC_ID.match(spec_id):
        r.passed = True
        r.message = f"format valid: {spec_id}"
    else:
        r.error = (
            f"Spec ID '{spec_id}' format non-compliant — "
            f"expected v{{version}}-{{NNN}}-{{keyword}} (e.g. v0.3-001-adopt-mode)"
        )
    return r


def check_f10_unmerged_releases(
    repo: str, current_release: str | None = None
) -> CheckResult:
    """F10: check all releases/* branches not merged into main

    Exemption rule: the release currently being worked on (releases/{version} corresponding to --version)
    does not count as an orphan — it is the working branch for this foundation, not being merged yet is normal.

    Other unmerged releases: if explicitly listed in [meta.acknowledged_orphan_releases] in project.toml,
    they pass as a warning (warning=True).
    Acknowledged orphan branches remain warnings rather than blockers and are
    shown with ``[!]`` in the output.
    """
    r = CheckResult(code="F10", name="Unmerged releases/* branches")
    exempt = f"releases/{current_release}" if current_release else None

    # 1. List all releases/* remote branches not merged into main
    try:
        out = (
            subprocess.check_output(
                ["git", "ls-remote", "--heads", "origin", "releases/*"],
                stderr=subprocess.DEVNULL,
            )
            .decode()
            .strip()
        )
    except Exception as e:
        r.error = f"unable to list remote branches: {e}"
        return r

    if not out:
        r.passed = True
        r.message = "project has no releases/* branches (first launch, skipped)"
        return r

    unmerged: list[str] = []
    for line in out.splitlines():
        # Format: <sha>\trefs/heads/releases/v0.x
        parts = line.split()
        if len(parts) < 2:
            continue
        ref = parts[1]
        branch = ref.removeprefix("refs/heads/")
        # Exempt the release branch currently being worked on
        if branch == exempt:
            continue
        # Check whether already merged into main (merge-base --is-ancestor)
        rc = subprocess.run(
            ["git", "merge-base", "--is-ancestor", branch, "main"],
            capture_output=True,
        ).returncode
        if rc != 0:
            unmerged.append(branch)

    if not unmerged:
        r.passed = True
        r.message = "all releases/* branches have been merged into main"
        return r

    # 2. Check whether project.toml explicitly acknowledges these orphans (after fix-002)
    pi_path = Path(".louke/project/project.toml")
    acked: list[str] = []
    if pi_path.is_file():
        try:
            import tomllib
        except ImportError:
            try:
                import tomli as tomllib  # type: ignore
            except ImportError:
                tomllib = None  # type: ignore
        if tomllib is not None:
            try:
                with open(pi_path, "rb") as f:
                    data = tomllib.load(f)
                acked_list = data.get("meta", {}).get(
                    "acknowledged_orphan_releases", []
                )
                if isinstance(acked_list, list):
                    acked = acked_list
            except Exception:
                pass

    unacked = [b for b in unmerged if b not in acked]
    if unacked:
        r.error = (
            f"unmerged release branches not acknowledged by project.toml exist: "
            f"{', '.join(unacked)} — please merge into main first, or list them in project.toml [meta].acknowledged_orphan_releases"
        )
        return r

    # All acked, warning rather than blocking
    r.warning = True
    r.passed = False
    r.error = (
        f"the following release branches are not merged into main, marked as acknowledged orphan in project.toml: "
        f"{', '.join(unmerged)}"
    )
    return r


def check_f11_identity(repo: str) -> CheckResult:
    """F11: gh and git identity consistency (delegates to check_identity.py)"""
    r = CheckResult(code="F11", name="Identity consistency (gh/git)")
    # Intentionally two layers of except: ImportError/AttributeError is an F11 integration bug itself
    # (e.g. check_identity changed its signature and this was not updated), must surface to the user,
    # cannot silently downgrade to a warning and let the hold point fail.
    try:
        from louke._tools import check_identity
    except ImportError as e:
        r.error = f"F11 integration error: cannot import check_identity — {e}"
        return r

    try:
        # collect_gh() returns (user, emails); collect_git() returns
        # (name, email, last_author, remote). Build Identity with explicit
        # kwargs (collect_repo_role needs the repo arg).
        gh_user, gh_emails = check_identity.collect_gh()
        git_name, git_email, last_author, remote_url = check_identity.collect_git()
        repo_role = check_identity.collect_repo_role(repo)
        ident = check_identity.Identity(
            gh_user=gh_user,
            gh_emails=gh_emails,
            git_name=git_name,
            git_email=git_email,
            last_commit_author=last_author,
            remote_url=remote_url,
            repo_role=repo_role,
        )
        check_identity.check(ident, repo)
        rc = check_identity.report(ident, repo)
    except (AttributeError, TypeError) as e:
        # F11 integration bug itself (signature mismatch, Identity fields mismatched, etc.)
        r.error = f"F11 integration error: check_identity API mismatch — {e}"
        return r
    except Exception as e:
        # Genuine external exception (gh/git not installed, network issue) — downgrade to warning
        r.warning = True
        r.message = f"identity check exception (downgraded to warning): {e}"
        return r

    if rc == 0:
        r.passed = True
        r.message = "identity consistent"
        return r
    # Identity check failed → warning (GH identity drift is no longer a blocker,
    # agent can resolve by creating project under its own name)
    r.warning = True
    r.message = f"identity check failed (exit code {rc}, downgraded to warning — see check_identity output above)"
    return r


# ---------- Report ----------


def report(results: list[CheckResult]) -> int:
    passed = [r for r in results if r.passed]
    failed = [r for r in results if not r.passed and not r.warning]
    warnings = [r for r in results if not r.passed and r.warning]

    print(f"\nRuntime foundation program — {len(results)} checks\n")

    for r in results:
        if r.passed:
            print(f"  [✓] {r.code} {r.name}: {r.message}")
        elif r.warning:
            print(f"  [!] {r.code} {r.name}: {r.error}")
        else:
            print(f"  [✗] {r.code} {r.name}: {r.error}")

    print()

    if failed:
        print(
            f"[REJECT] {len(failed)} blocking, {len(warnings)} warnings, {len(passed)} passed\n"
        )
        return 1

    if warnings:
        print(
            f"[PASS+warning] {len(warnings)} warnings need confirmation, {len(passed)} passed\n"
        )
        return 0

    print(f"[PASS] all {len(passed)} checks passed\n")
    return 0


# ---------- Entry point ----------


def main() -> int:
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("repo", help="owner/repo, e.g. zillionare/louke")
    p.add_argument("--version", required=True, help="version number, e.g. v0.1")
    p.add_argument(
        "--spec-id", dest="spec_id", help="Spec ID, e.g. v0.3-001-adopt-mode"
    )
    p.add_argument(
        "--project-id",
        dest="project_id",
        type=int,
        help="GitHub Project numeric ID (skip auto-lookup)",
    )
    p.add_argument("--upstream", help="upstream branch name (enables F8 check)")
    p.add_argument("--skip", help="skip specific checks, comma-separated (e.g. F3,F4)")
    p.add_argument(
        "--offline",
        action="store_true",
        help="offline mode: only run local checks (F5, F6, F7, F9)",
    )

    args = p.parse_args()

    skip_set = set()
    if args.skip:
        skip_set = {s.strip().upper() for s in args.skip.split(",")}

    results: list[CheckResult] = []

    # Local checks (no network needed)
    if "F5" not in skip_set:
        results.append(check_f5_agents())
    if "F6" not in skip_set:
        results.append(check_f6_project_info(args.spec_id))
    if "F9" not in skip_set and args.spec_id:
        results.append(check_f9_spec_id(args.spec_id))
    if args.spec_id and "F7" not in skip_set:
        results.append(check_f7_story(args.spec_id))

    if args.offline:
        return report(results)

    # Remote checks (need gh + network)
    if "F1" not in skip_set:
        results.insert(0, check_f1_repo(args.repo))
    if "F2" not in skip_set:
        results.insert(1, check_f2_project(args.repo, args.version, args.project_id))
    if "F3" not in skip_set:
        results.append(check_f3_test_issue(args.repo, args.version))
    if "F4" not in skip_set:
        results.append(check_f4_test_pr(args.repo, args.version))
    if args.upstream and "F8" not in skip_set:
        results.append(check_f8_dev_branch(args.version, args.upstream))
    if "F10" not in skip_set:
        results.append(check_f10_unmerged_releases(args.repo, args.version))
    if "F11" not in skip_set:
        results.append(check_f11_identity(args.repo))

    return report(results)


if __name__ == "__main__":
    sys.exit(main())
