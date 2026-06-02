#!/usr/bin/env python3
"""
check_identity.py — 检测 gh CLI 身份 vs git 身份的一致性

为什么需要这个检查:
  specforge 的工作流混合使用 gh API (issues/PRs/labels) 和 git (push/clone)。
  如果两个通道用了不同 GitHub 账号,会出现:
    - git push 成功 (用 aaronyang 的 SSH key)
    - gh issue create 失败 403 (用 quantclaws 的 token, 没权限)

  这种不统一在两个账号都有权时不会暴露,一旦任一降权就炸。
  本脚本在每次流程启动时显式检测,提前报警。

检查项 (L1-L5):
  L1 gh 已认证           gh api user 返回非空
  L2 gh 对目标 repo 有写权 viewerPermission ∈ {ADMIN, MAINTAIN, WRITE}
  L3 git user.name/email 已设置
  L4 git 最近 commit 的 author email 属于 gh 用户的已知邮箱
  L5 git remote origin 的 owner 与 gh user 同属一个 org (或就是本人)

L4/L5 是关键 — 它们就是"两个身份"的检测器。

使用:
  python tools/check_identity.py --repo OWNER/REPO
  python tools/check_identity.py --repo OWNER/REPO --offline \\
      --gh-user aaronyang --gh-emails "aaron@x.com aaron@y.com" \\
      --git-name aaron --git-email aaron@x.com \\
      --repo-role WRITE --last-commit-author "aaron <aaron@x.com>" \\
      --remote-url "git@github.com:zillionare/specforge.git"
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
    failures: list[str] = field(default_factory=list)   # 阻塞:任一存在即拒绝
    warnings: list[str] = field(default_factory=list)   # 提示:不阻塞,需用户确认

    @property
    def ok(self) -> bool:
        return not self.failures


# ---------- 收集各源信息 ----------


def collect_gh() -> tuple[str, list[str]]:
    """返回 (gh_login, [gh 用户已知邮箱列表])"""
    user = ""
    emails: list[str] = []
    try:
        user = subprocess.check_output(
            ["gh", "api", "user", "-q", ".login"]
        ).decode().strip()
    except Exception as e:
        return "", []

    # 公开邮箱 (PAT `repo` scope 即可)
    try:
        out = subprocess.check_output(
            ["gh", "api", "user", "-q", ".email"]
        ).decode().strip()
        if out and out != "null":
            emails.append(out)
    except Exception:
        pass

    # 全部邮箱 (需要 `user` scope,失败就跳过)
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

    # 去重保序
    seen = set()
    deduped = []
    for e in emails:
        if e not in seen:
            seen.add(e)
            deduped.append(e)
    return user, deduped


def collect_git() -> tuple[str, str, str, str]:
    """返回 (user.name, user.email, last_commit_author, remote_url)"""
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


# ---------- 检查 ----------


def check(ident: Identity, repo: str) -> Identity:
    # L1: gh 已认证
    if not ident.gh_user:
        ident.failures.append(
            "L1 gh 未认证 — 请运行 'gh auth login' 或 'gh auth refresh'"
        )

    # L2: 对目标 repo 有写权
    if not ident.repo_role:
        ident.failures.append(
            f"L2 无法读取 {repo} 的 viewerPermission (token 缺 scope? 或 repo 不存在?)"
        )
    elif ident.repo_role not in WRITE_ROLES:
        ident.failures.append(
            f"L2 gh 账号 {ident.gh_user or '?'} 在 {repo} 上只有 {ident.repo_role} 权限,"
            f"无法创建/编辑 issue、PR、label。需要 WRITE/MAINTAIN/ADMIN。"
        )

    # L3: git user.name + user.email 已设置
    if not ident.git_name or not ident.git_email:
        ident.failures.append(
            f"L3 git user.name/email 未设置 (当前 name={ident.git_name!r}, "
            f"email={ident.git_email!r}) — 'git config user.name/email' 后再继续"
        )

    # L4: 最近 commit 的 author email 属于 gh 用户
    if ident.last_commit_author and ident.gh_emails:
        m = re.search(r"<([^>]+)>", ident.last_commit_author)
        if m:
            last_email = m.group(1).strip()
            if last_email and last_email not in ident.gh_emails:
                ident.failures.append(
                    f"L4 最近 commit 作者 {ident.last_commit_author!r} 的 email "
                    f"{last_email!r} 不在 gh 账号 {ident.gh_user!r} 的已知邮箱中 "
                    f"{ident.gh_emails}。这意味着 git 和 gh 用了不同身份 — "
                    f"git push 成功但 gh 操作会失败,或反之。"
                )

    # L5: remote URL 的 owner 与 gh user 不一致 → 仅警告 (不阻塞)
    # 原因: 个人 token 操作 org repo 是合法场景,只要 token 已被授予访问权。
    #       但值得提示用户确认。
    if ident.remote_url and ident.gh_user:
        m = re.search(r"github\.com[:/]([\w.-]+)/", ident.remote_url)
        if m:
            remote_owner = m.group(1)
            if remote_owner != ident.gh_user:
                ident.warnings.append(
                    f"L5 提示: git remote owner={remote_owner!r} 与 gh user={ident.gh_user!r} 不同。"
                    f"如属正常 (个人 token 操作 org repo),可忽略;"
                    f"否则请用 'gh auth switch' 切换到 {remote_owner} 账号。"
                )

    return ident


# ---------- 报告 ----------


def report(ident: Identity, repo: str) -> int:
    print(f"\n身份一致性检查 — target repo: {repo}\n")
    print(f"  gh user:           {ident.gh_user or '(未认证)'}")
    print(f"  gh 已知邮箱:       {ident.gh_emails or '(无)'}")
    print(f"  git user.name:     {ident.git_name or '(未设置)'}")
    print(f"  git user.email:    {ident.git_email or '(未设置)'}")
    print(f"  最近 commit 作者:  {ident.last_commit_author or '(无)'}")
    print(f"  remote origin:     {ident.remote_url or '(无)'}")
    print(f"  {repo} viewerPermission: {ident.repo_role or '(未读取)'}")
    print()

    # 阻塞项
    if ident.failures:
        print("[拒绝] 身份不一致或权限不足\n")
        for f in ident.failures:
            print(f"  - {f}")
        print()
        print("建议:")
        print("  1. 用 'gh auth status' 查看当前 token 账号")
        print("  2. 切换 token: 'gh auth login' 或 'gh auth switch'")
        print("  3. 或修改 git config: 'git config user.email <gh 账号关联邮箱>'")
        print("  4. 重新跑本脚本确认\n")
        return 1

    # 仅警告
    if ident.warnings:
        print("[通过+警告] 主体一致,但有提示项需确认\n")
        for w in ident.warnings:
            print(f"  ! {w}")
        print()
        return 0

    print("[通过] gh 与 git 身份完全一致,token 权限足够\n")
    return 0


# ---------- 入口 ----------


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo", required=True, help="OWNER/REPO,如 zillionare/specforge")
    p.add_argument("--offline", action="store_true", help="离线模式 (给 bats 用)")
    p.add_argument("--gh-user", help="离线: gh login")
    p.add_argument("--gh-emails", help="离线: 空格分隔的 gh 邮箱列表")
    p.add_argument("--git-name", help="离线: git user.name")
    p.add_argument("--git-email", help="离线: git user.email")
    p.add_argument("--last-commit-author", dest="last_commit_author", help="离线: 'Name <email>'")
    p.add_argument("--remote-url", dest="remote_url", help="离线: remote URL")
    p.add_argument("--repo-role", dest="repo_role", help="离线: viewerPermission")
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
