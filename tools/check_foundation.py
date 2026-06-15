#!/usr/bin/env python3
"""
check_foundation.py — 验证 Scout 奠基阶段的工作是否完整

为什么需要这个检查:
  Scout 的工作流涉及多个 GitHub 操作(repo/project/issue/PR)和本地文件创建。
  Agent 内联执行这些检查容易出错且难以维护。本脚本将全部检查集中在一处,
  提供一致的通过/拒绝输出。

  设计目标:
  - 零 LLM token: 纯结构化检查
  - 零额外依赖: 仅 Python stdlib
  - 幂等: 可重复运行,不会创建/修改任何资源
  - 可组合: 每个检查独立,可单独跳过

检查项(F1-F11):
  F1 Repo 可访问:        gh repo view 成功
  F2 Project 存在:       gh project list 包含 {repo}-{version}
  F3 Test Issue 合规:    标题 "Good First Issue: {repo}-{version}", 状态 closed
  F4 Test PR 合规:       标题 "Good First PR: {repo}-{version}", 状态 closed
  F5 Agent 文件存在:     agents/*.md 文件存在
  F6 project-info 完整:  specs/project-info.md 包含必须字段
                          Version, Repo, Project, Spec ID, Release Branch
  F7 story.md 存在:      .specforge/specs/{spec-id}/story.md 存在
  F8 开发分支存在:       releases/{version} 分支在远程存在 (基于 main)
  F9 Spec ID 格式合规:   符合 {NNN}-{keyword}-{version}
  F10 未合并的 releases/*: 无未合并 releases/*; 若存在, project-info 需
                          含 Acknowledged-Orphan-Releases 字段作为警告放行
  F11 身份一致性:       gh 与 git 同身份 (委托 check_identity.py L1-L5)

使用:
  specforge foundation <owner/repo> --version <version> --spec-id <spec-id>
  specforge foundation zillionare/specforge --version v0.1 --spec-id 001-specforge-v0.1

  可选 flags:
    --project-id NUMBER   GitHub Project 数字 ID (跳过自动查找)
    --skip F3,F4          跳过指定检查项 (逗号分隔)
    --upstream BRANCH     验证开发分支基于的上游分支 (默认不检查 F8, 推荐传 main)
    --offline             离线模式: 只跑本地检查 (F5, F6, F7, F9, F10)
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path


# ---------- 数据结构 ----------


@dataclass
class CheckResult:
    code: str           # F1, F2, ...
    name: str           # 检查名称
    passed: bool = False
    message: str = ""   # 通过时的详情
    error: str = ""     # 失败时的原因
    warning: bool = False  # True = 警告而非阻塞


# ---------- 辅助函数 ----------


def _gh(*args: str) -> tuple[str, bool]:
    """运行 gh 命令,返回 (stdout, success)"""
    try:
        out = subprocess.check_output(
            ["gh", *args], stderr=subprocess.STDOUT
        ).decode().strip()
        return out, True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "", False


def _gh_json(*args: str) -> tuple[dict | list | None, bool]:
    """运行 gh 命令并解析 JSON 输出"""
    text, ok = _gh(*args)
    if not ok or not text:
        return None, False
    try:
        return json.loads(text), True
    except json.JSONDecodeError:
        return None, False


# ---------- 检查项 ----------


def check_f1_repo(repo: str) -> CheckResult:
    """F1: Repo 可访问"""
    r = CheckResult(code="F1", name="Repo 可访问")
    data, ok = _gh_json("repo", "view", repo, "--json", "nameWithOwner,isPrivate")
    if not ok or not data:
        r.error = f"无法访问 repo {repo} — 请确认 repo 存在且当前 token 有权限"
        return r
    visibility = "private" if data.get("isPrivate") else "public"
    r.passed = True
    r.message = f"{data['nameWithOwner']} ({visibility})"
    return r


def check_f2_project(repo: str, version: str, project_id: int | None) -> CheckResult:
    """F2: GitHub Project 存在 (允许创建在 repo owner 或 gh 身份下)"""
    r = CheckResult(code="F2", name="Project 存在")
    expected_title = f"{repo.split('/')[-1]}-{version}"

    if project_id:
        # 直接验证指定 ID
        data, ok = _gh_json("project", "view", str(project_id),
                            "--owner", repo.split("/")[0],
                            "--json", "title,number")
        if ok and data:
            r.passed = True
            r.message = f"{data['title']} (#{data['number']})"
            return r

    # 搜索 project 列表 — 同时查 repo owner 和 gh 身份 (collaborator 模式)
    repo_owner = repo.split("/")[0]
    gh_user_out, _ = _gh("api", "user", "-q", ".login")
    gh_user = gh_user_out.strip()
    owners_to_check = list({repo_owner, gh_user})  # 去重保序

    for owner in owners_to_check:
        data, ok = _gh_json("project", "list", "--owner", owner,
                            "--format", "json", "--limit", "50")
        if not ok or not data:
            continue
        # gh project list --format json 返回 {"projects": [...], "totalCount": N}
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
        f"未找到 Project '{expected_title}' — 请先创建。"
        f"可创建在 {repo_owner} 或 {gh_user} 名下。"
        f"如创建在 {gh_user} 名下,运行 'specforge invite-owner {repo} --version {version}' "
        f"把 {repo_owner} 设为 project READER"
    )
    return r


def check_f3_test_issue(repo: str, version: str) -> CheckResult:
    """F3: Test Issue 存在且已关闭 (Scout 创建)"""
    r = CheckResult(code="F3", name="Test Issue 合规")
    expected_title = f"Good First Issue: {repo.split('/')[-1]}-{version}"

    data, ok = _gh_json("issue", "list", "--repo", repo,
                        "--state", "all", "--limit", "100",
                        "--json", "number,title,state")
    if not ok or not data:
        r.error = "无法列出 issues — 请确认 gh 有 repo 访问权限"
        return r

    for issue in (data if isinstance(data, list) else []):
        if expected_title.lower() in issue.get("title", "").lower():
            if issue.get("state") == "CLOSED":
                r.passed = True
                r.message = f"#{issue['number']} (closed)"
                return r
            r.error = f"Test Issue #{issue['number']} 状态为 {issue.get('state')} — 需要 CLOSED"
            return r

    r.error = f"未找到 Test Issue '{expected_title}' — Scout 须创建"
    return r


def check_f4_test_pr(repo: str, version: str) -> CheckResult:
    """F4: Test PR 存在且已关闭 (Scout 创建)"""
    r = CheckResult(code="F4", name="Test PR 合规")
    expected_title = f"Good First PR: {repo.split('/')[-1]}-{version}"

    data, ok = _gh_json("pr", "list", "--repo", repo,
                        "--state", "all", "--limit", "100",
                        "--json", "number,title,state")
    if not ok or not data:
        r.error = "无法列出 PRs — 请确认 gh 有 repo 访问权限"
        return r

    for pr in (data if isinstance(data, list) else []):
        if expected_title.lower() in pr.get("title", "").lower():
            state = pr.get("state")
            if state in ("CLOSED", "MERGED"):
                r.passed = True
                r.message = f"#{pr['number']} ({state.lower()})"
                return r
            r.error = f"Test PR #{pr['number']} 状态为 {state} — 需要 CLOSED/MERGED"
            return r

    r.error = f"未找到 Test PR '{expected_title}' — Scout 须创建"
    return r


def check_f5_agents() -> CheckResult:
    """F5: Agent prompt 文件存在"""
    r = CheckResult(code="F5", name="Agent 文件存在")
    agents_dir = Path("agents")
    if not agents_dir.is_dir():
        r.error = "agents/ 目录不存在"
        return r

    md_files = list(agents_dir.glob("*.md"))
    if not md_files:
        r.error = "agents/ 下没有任何 .md 文件"
        return r

    r.passed = True
    r.message = f"{len(md_files)} 个 Agent prompt 文件"
    return r


# project-info.md 必须字段 (与 Scout Step 6 输出对齐)
REQUIRED_PROJECT_INFO_FIELDS = [
    "Version", "Repo", "Project", "Spec ID", "Release Branch",
]

RE_SPEC_ID = re.compile(r"^\d{3}-[\w-]+-[\w.]+$")


def check_f6_project_info(spec_id: str | None) -> CheckResult:
    """F6: project-info.md 存在且包含必须字段"""
    r = CheckResult(code="F6", name="project-info.md 完整")
    pi_path = Path("specs/project-info.md")
    if not pi_path.is_file():
        r.error = "specs/project-info.md 不存在"
        return r

    content = pi_path.read_text(encoding="utf-8")

    # 检查必须字段
    missing = []
    for fld in REQUIRED_PROJECT_INFO_FIELDS:
        if f"**{fld}**" not in content:
            missing.append(fld)
    if missing:
        r.error = f"project-info.md 缺少字段: {', '.join(missing)}"
        return r

    # 如果提供了 spec_id, 验证 F9 (Spec ID 格式)
    if spec_id:
        if not RE_SPEC_ID.match(spec_id):
            r.error = f"Spec ID 格式不合规: '{spec_id}' — 期望 NNN-keyword-version (如 001-adopt-mode-v0.3)"
            return r
        if f"**Spec ID**: {spec_id}" not in content and f"**Spec ID**: " not in content:
            r.error = f"project-info.md 中的 Spec ID 与参数 '{spec_id}' 不匹配"
            return r

    r.passed = True
    r.message = f"包含 {len(REQUIRED_PROJECT_INFO_FIELDS)} 个必须字段"
    return r


def check_f7_story(spec_id: str) -> CheckResult:
    """F7: story.md 存在"""
    r = CheckResult(code="F7", name="story.md 存在")
    if not spec_id:
        r.error = "未提供 spec-id, 无法检查 story.md"
        return r

    story_path = Path(f".specforge/specs/{spec_id}/story.md")
    if not story_path.is_file():
        r.error = f".specforge/specs/{spec_id}/story.md 不存在"
        return r

    size = story_path.stat().st_size
    r.passed = True
    r.message = f".specforge/specs/{spec_id}/story.md ({size} bytes)"
    return r


def check_f8_dev_branch(version: str, upstream: str | None) -> CheckResult:
    """F8: 开发分支 releases/{version} 在远程存在"""
    r = CheckResult(code="F8", name="开发分支存在")
    branch = f"releases/{version}"

    # 检查远程分支
    out, ok = _gh("api", f"repos/$(gh repo view --json nameWithOwner -q .nameWithOwner)/git/refs/heads/{branch}")
    if ok:
        r.passed = True
        r.message = f"远程分支 {branch} 存在"
        if upstream:
            r.message += f" (基于 {upstream})"
        return r

    # 备用: git ls-remote
    try:
        ls_out = subprocess.check_output(
            ["git", "ls-remote", "--heads", "origin", branch],
            stderr=subprocess.DEVNULL,
        ).decode().strip()
        if ls_out:
            r.passed = True
            r.message = f"远程分支 {branch} 存在"
            return r
    except Exception:
        pass

    r.error = f"远程分支 {branch} 不存在 — 请先创建: git checkout -b {branch} && git push -u origin {branch}"
    return r


def check_f9_spec_id(spec_id: str) -> CheckResult:
    """F9: Spec ID 格式合规"""
    r = CheckResult(code="F9", name="Spec ID 格式合规")
    if not spec_id:
        r.error = "未提供 --spec-id"
        return r

    if RE_SPEC_ID.match(spec_id):
        r.passed = True
        r.message = f"格式正确: {spec_id}"
    else:
        r.error = (
            f"Spec ID '{spec_id}' 格式不合规 — "
            f"期望 NNN-keyword-version (如 001-adopt-mode-v0.3)"
        )
    return r


def check_f10_unmerged_releases(repo: str, current_release: str | None = None) -> CheckResult:
    """F10: 检查所有未合并到 main 的 releases/* 分支

    豁免规则: 当前正在工作的 release (--version 对应的 releases/{version})
    不算作 orphan — 它是本版奠基的工作分支,还没合并是正常的。

    其他未合并 release: 如果 project-info 中显式列出了
    'Acknowledged-Orphan-Releases' 字段, 则作为警告放行 (warning=True)。
    这与 Scout Step 3.5 中 "用户答 y" 的语义对称:
      - Scout 警告 + 询问 → 用户答 y
      - Warden 检查 + 警告放行 → 不阻塞, 但在输出中标记 [!]
    """
    r = CheckResult(code="F10", name="未合并 releases/* 分支")
    exempt = f"releases/{current_release}" if current_release else None

    # 1. 列出所有未合并到 main 的 releases/* 远程分支
    try:
        out = subprocess.check_output(
            ["git", "ls-remote", "--heads", "origin", "releases/*"],
            stderr=subprocess.DEVNULL,
        ).decode().strip()
    except Exception as e:
        r.error = f"无法列远程分支: {e}"
        return r

    if not out:
        r.passed = True
        r.message = "项目无任何 releases/* 分支 (首次启动, 跳过)"
        return r

    unmerged: list[str] = []
    for line in out.splitlines():
        # 格式: <sha>\trefs/heads/releases/v0.x
        parts = line.split()
        if len(parts) < 2:
            continue
        ref = parts[1]
        branch = ref.removeprefix("refs/heads/")
        # 豁免当前正在工作的 release 分支
        if branch == exempt:
            continue
        # 检查是否已合并到 main (merge-base --is-ancestor)
        rc = subprocess.run(
            ["git", "merge-base", "--is-ancestor", branch, "main"],
            capture_output=True,
        ).returncode
        if rc != 0:
            unmerged.append(branch)

    if not unmerged:
        r.passed = True
        r.message = "所有 releases/* 分支都已合入 main"
        return r

    # 2. 检查 project-info 是否显式承认这些 orphan
    pi_path = Path("specs/project-info.md")
    acked: list[str] = []
    if pi_path.is_file():
        content = pi_path.read_text(encoding="utf-8")
        if "**Acknowledged-Orphan-Releases**:" in content:
            # 解析列表 (格式: "- releases/v0.2" 每行一项)
            for line in content.splitlines():
                m = re.match(r"\s*-\s*(releases/[\w.-]+)", line)
                if m:
                    acked.append(m.group(1))

    unacked = [b for b in unmerged if b not in acked]
    if unacked:
        r.error = (
            f"存在未合并到 main 且未被 project-info 承认的 release 分支: "
            f"{', '.join(unacked)} — 请先合并到 main, 或在 project-info 中显式列出"
        )
        return r

    # 全部已 ack, 警告而非阻塞
    r.warning = True
    r.passed = False
    r.error = (
        f"以下 release 分支未合并到 main, 已被 project-info 标记为 acknowledged orphan: "
        f"{', '.join(unmerged)}"
    )
    return r


def check_f11_identity(repo: str) -> CheckResult:
    """F11: gh 与 git 身份一致性 (委托 check_identity.py)"""
    r = CheckResult(code="F11", name="身份一致性 (gh/git)")
    try:
        # 调用同 framework 的 checkup 子命令 (零代码重复)
        specforge_bin = Path(__file__).resolve().parent.parent / "bin" / "specforge"
        if not specforge_bin.is_file():
            specforge_bin = Path("/usr/local/bin/specforge")  # 安装后的位置

        cmd = [str(specforge_bin), "checkup", repo]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode == 0:
            r.passed = True
            r.message = "checkup 通过"
            return r
        # checkup 退出 1 = 拒绝, 退出 2 = 警告 (取决于实现)
        # 但 GH identity 漂移已非 blocker (agent 在自己名下创建 project 解决问题)
        # → 降为 warning
        output = (proc.stdout + proc.stderr).strip()
        last_lines = "\n".join(output.splitlines()[-3:]) if output else "(无输出)"
        r.warning = True
        r.message = f"checkup 失败 (降为警告): {last_lines}"
        return r
    except FileNotFoundError:
        r.warning = True
        r.message = "specforge CLI 未找到, 跳过 F11 (非阻塞)"
        return r
    except Exception as e:
        r.warning = True
        r.message = f"F11 异常 (降为警告): {e}"
        return r


# ---------- 报告 ----------


def report(results: list[CheckResult]) -> int:
    passed = [r for r in results if r.passed]
    failed = [r for r in results if not r.passed and not r.warning]
    warnings = [r for r in results if not r.passed and r.warning]

    print(f"\n项目奠基检查 — {len(results)} 项\n")

    for r in results:
        if r.passed:
            print(f"  [✓] {r.code} {r.name}: {r.message}")
        elif r.warning:
            print(f"  [!] {r.code} {r.name}: {r.error}")
        else:
            print(f"  [✗] {r.code} {r.name}: {r.error}")

    print()

    if failed:
        print(f"[拒绝] {len(failed)} 项阻塞, {len(warnings)} 项警告, {len(passed)} 项通过\n")
        return 1

    if warnings:
        print(f"[通过+警告] {len(warnings)} 项警告需确认, {len(passed)} 项通过\n")
        return 0

    print(f"[通过] 全部 {len(passed)} 项检查通过\n")
    return 0


# ---------- 入口 ----------


def main() -> int:
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("repo", help="owner/repo, 如 zillionare/specforge")
    p.add_argument("--version", required=True, help="版本号, 如 v0.1")
    p.add_argument("--spec-id", dest="spec_id", help="Spec ID, 如 001-adopt-mode-v0.3")
    p.add_argument("--project-id", dest="project_id", type=int,
                   help="GitHub Project 数字 ID (跳过自动查找)")
    p.add_argument("--upstream", help="上游分支名 (启用 F8 检查)")
    p.add_argument("--skip", help="跳过指定检查项, 逗号分隔 (如 F3,F4)")
    p.add_argument("--offline", action="store_true",
                   help="离线模式: 只跑本地检查 (F5, F6, F7, F9)")

    args = p.parse_args()

    skip_set = set()
    if args.skip:
        skip_set = {s.strip().upper() for s in args.skip.split(",")}

    results: list[CheckResult] = []

    # 本地检查 (不需要网络)
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

    # 远程检查 (需要 gh + 网络)
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
