#!/usr/bin/env python3
"""
check_identity.py — detect consistency between gh CLI identity and git identity.

Why this check is needed:
  Louke's workflow mixes gh API (issues/PRs/labels) with git (push/clone).
  If the two channels use different GitHub accounts, you get:
    - git push succeeds (using account A's SSH key)
    - gh issue create fails 403 (using account B's token, no permission)

  This inconsistency stays hidden when both accounts have access, but breaks
  as soon as either is downgraded. This script explicitly checks at workflow
  startup to catch issues early.

Check items (L1-L5):
  L1 gh authenticated       gh api user returns non-empty
  L2 gh has write access    viewerPermission ∈ {ADMIN, MAINTAIN, WRITE}
  L3 git user.name/email    are set
  L4 last commit author     email belongs to gh user's known emails
  L5 remote origin owner    belongs to same org as gh user (or is the user)

L4/L5 are the critical ones — they detect "two identities".

Usage:
  python louke/_tools/check_identity.py --repo OWNER/REPO
  python louke/_tools/check_identity.py --repo OWNER/REPO --offline \\
      --gh-user aaronyang --gh-emails "aaron@x.com aaron@y.com" \\
      --git-name aaron --git-email aaron@x.com \\
      --repo-role WRITE --last-commit-author "aaron <aaron@x.com>" \\
      --remote-url "git@github.com:zillionare/louke.git"
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field


WRITE_ROLES = {"ADMIN", "MAINTAIN", "WRITE"}


@dataclass
class Identity:
    gh_user: str = ""
    gh_emails: list[str] = field(default_factory=list)
    git_name: str = ""
    git_email: str = ""
    last_commit_author: str = ""  # "Name <email>"
    remote_url: str = ""
    repo_role: str = ""  # ADMIN/MAINTAIN/WRITE/READ/NONE
    failures: list[str] = field(default_factory=list)   # blocking: any present → reject
    warnings: list[str] = field(default_factory=list)   # advisory: non-blocking, needs user confirmation

    @property
    def ok(self) -> bool:
        return not self.failures


# ---------- Collect source info ----------


def collect_gh() -> tuple[str, list[str]]:
    """Return (gh_login, [list of gh user's known emails])"""
    user = ""
    emails: list[str] = []
    try:
        user = subprocess.check_output(
            ["gh", "api", "user", "-q", ".login"]
        ).decode().strip()
    except Exception as e:
        return "", []

    # Public email (PAT `repo` scope is enough)
    try:
        out = subprocess.check_output(
            ["gh", "api", "user", "-q", ".email"]
        ).decode().strip()
        if out and out != "null":
            emails.append(out)
    except Exception:
        pass

    # All emails (needs `user` scope; skip on failure)
    try:
        out = subprocess.check_output(
            ["gh", "api", "user/emails", "-q", ".[].email"]
        ).decode().strip()
        for e in out.splitlines():
            e = e.strip()
            if e and e != "null":
                emails.append(e)
    except Exception:
        pass

    # Deduplicate, preserving order
    seen = set()
    deduped = []
    for e in emails:
        if e not in seen:
            seen.add(e)
            deduped.append(e)
    return user, deduped


def collect_git() -> tuple[str, str, str, str]:
    """Return (user.name, user.email, last_commit_author, remote_url)"""
    def _git(*args: str) -> str:
        try:
            return subprocess.check_output(
                ["git", *args], stderr=subprocess.DEVNULL
            ).decode().strip()
        except Exception:
            return ""

    name = _git("config", "user.name")
    email = _git("config", "user.email")
    last_author = _git("log", "-1", "--format=%an <%ae>")
    remote = _git("config", "--get", "remote.origin.url")
    return name, email, last_author, remote


def collect_repo_role(repo: str) -> str:
    try:
        out = subprocess.check_output(
            [
                "gh", "repo", "view", repo,
                "--json", "viewerPermission",
                "-q", ".viewerPermission",
            ]
        ).decode().strip()
        return out
    except Exception:
        return ""


# ---------- Check ----------


def check(ident: Identity, repo: str) -> Identity:
    # L1: gh authenticated
    if not ident.gh_user:
        ident.failures.append(
            "L1 gh not authenticated — run 'gh auth login' or 'gh auth refresh'"
        )

    # L2: has write access to target repo
    if not ident.repo_role:
        ident.failures.append(
            f"L2 cannot read viewerPermission for {repo} (token missing scope? or repo does not exist?)"
        )
    elif ident.repo_role not in WRITE_ROLES:
        ident.failures.append(
            f"L2 gh account {ident.gh_user or '?'} only has {ident.repo_role} permission on {repo}, "
            f"cannot create/edit issues, PRs, or labels. Need WRITE/MAINTAIN/ADMIN."
        )

    # L3: git user.name + user.email are set
    if not ident.git_name or not ident.git_email:
        ident.failures.append(
            f"L3 git user.name/email not set (current name={ident.git_name!r}, "
            f"email={ident.git_email!r}) — run 'git config user.name/email' before continuing"
        )

    # L4: last commit's author email belongs to gh user
    if ident.last_commit_author and ident.gh_emails:
        m = re.search(r"<([^>]+)>", ident.last_commit_author)
        if m:
            last_email = m.group(1).strip()
            if last_email and last_email not in ident.gh_emails:
                ident.failures.append(
                    f"L4 last commit author {ident.last_commit_author!r} email "
                    f"{last_email!r} is not in gh account {ident.gh_user!r}'s known emails "
                    f"{ident.gh_emails}. This means git and gh are using different identities — "
                    f"git push will succeed but gh operations will fail, or vice versa."
                )

    # L5: remote URL owner differs from gh user → warning only (non-blocking)
    # Reason: personal token operating on org repo is a valid scenario, as long as
    #         the token has been granted access. But worth prompting user to confirm.
    if ident.remote_url and ident.gh_user:
        m = re.search(r"github\.com[:/]([\w.-]+)/", ident.remote_url)
        if m:
            remote_owner = m.group(1)
            if remote_owner != ident.gh_user:
                ident.warnings.append(
                    f"L5 note: git remote owner={remote_owner!r} differs from gh user={ident.gh_user!r}. "
                    f"If this is expected (personal token operating on org repo), ignore; "
                    f"otherwise use 'gh auth switch' to switch to the {remote_owner} account."
                )

    # L6: agent's role on {repo} must be OWNER or collaborator
    # Two collaboration modes are allowed:
    #   - agent == owner: all permissions are inherent
    #   - agent == collaborator (WRITE level): must be invited by repo owner, Project is
    #     created under agent's account, then call updateProjectV2Collaborators to set owner as READER
    # L2 already verified WRITE/MAINTAIN/ADMIN to run the workflow; this adds an informational
    # note to help users understand the two modes
    if ident.repo_role and ident.remote_url and ident.gh_user:
        m = re.search(r"github\.com[:/]([\w.-]+)/", ident.remote_url)
        if m:
            remote_owner = m.group(1)
            if remote_owner == ident.gh_user:
                # Agent identity = repo owner
                ident.warnings.append(
                    f"L6 collaboration mode: agent is owner of {remote_owner} — Project will be created under {remote_owner}, no additional invite needed"
                )
            elif ident.repo_role in WRITE_ROLES:
                # Agent identity = collaborator (has WRITE)
                ident.warnings.append(
                    f"L6 collaboration mode: agent {ident.gh_user} is a collaborator on {remote_owner} — "
                    f"Project will be created under {ident.gh_user}'s account, then use gh api "
                    f"updateProjectV2Collaborators to set {remote_owner} as Project READER"
                )
            # L2 failure case already recorded in failures above, not repeated here

    return ident


# ---------- Report ----------


def report(ident: Identity, repo: str) -> int:
    print(f"\nIdentity consistency check — target repo: {repo}\n")
    print(f"  gh user:           {ident.gh_user or '(not authenticated)'}")
    print(f"  gh known emails:  {ident.gh_emails or '(none)'}")
    print(f"  git user.name:    {ident.git_name or '(not set)'}")
    print(f"  git user.email:   {ident.git_email or '(not set)'}")
    print(f"  last commit author: {ident.last_commit_author or '(none)'}")
    print(f"  remote origin:    {ident.remote_url or '(none)'}")
    print(f"  {repo} viewerPermission: {ident.repo_role or '(not read)'}")
    print()

    # Blocking failures
    if ident.failures:
        print("[REJECT] Identity inconsistent or permissions insufficient\n")
        for f in ident.failures:
            print(f"  - {f}")
        print()
        print("Suggestions:")
        print("  1. Check current token account with 'gh auth status'")
        print("  2. Switch token: 'gh auth login' or 'gh auth switch'")
        print("  3. Or update git config: 'git config user.email <email linked to gh account>'")
        print("  4. Re-run this script to confirm\n")
        return 1

    # Warnings only
    if ident.warnings:
        print("[PASS+warning] Identity consistent, but there are items to confirm\n")
        for w in ident.warnings:
            print(f"  ! {w}")
        print()
        return 0

    print("[PASS] gh and git identities are fully consistent, token permissions sufficient\n")
    return 0


# ---------- Entry ----------


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo", required=True, help="OWNER/REPO, e.g. zillionare/louke")
    p.add_argument("--offline", action="store_true", help="offline mode (for bats tests)")
    p.add_argument("--gh-user", help="offline: gh login")
    p.add_argument("--gh-emails", help="offline: space-separated gh email list")
    p.add_argument("--git-name", help="offline: git user.name")
    p.add_argument("--git-email", help="offline: git user.email")
    p.add_argument("--last-commit-author", dest="last_commit_author", help="offline: 'Name <email>'")
    p.add_argument("--remote-url", dest="remote_url", help="offline: remote URL")
    p.add_argument("--repo-role", dest="repo_role", help="offline: viewerPermission")
    args = p.parse_args()

    if args.offline:
        ident = Identity(
            gh_user=args.gh_user or "",
            gh_emails=(args.gh_emails.split() if args.gh_emails else []),
            git_name=args.git_name or "",
            git_email=args.git_email or "",
            last_commit_author=args.last_commit_author or "",
            remote_url=args.remote_url or "",
            repo_role=args.repo_role or "",
        )
    else:
        user, emails = collect_gh()
        name, email, last_author, remote = collect_git()
        role = collect_repo_role(args.repo)
        ident = Identity(
            gh_user=user,
            gh_emails=emails,
            git_name=name,
            git_email=email,
            last_commit_author=last_author,
            remote_url=remote,
            repo_role=role,
        )

    check(ident, args.repo)
    return report(ident, args.repo)


if __name__ == "__main__":
    sys.exit(main())
