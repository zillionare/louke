#!/usr/bin/env python3
"""
verify_issue_schema.py — 验证 GitHub Feature issue 的 schema 合规性

这是 Lex/Sage 创建 issue 后的门禁脚本。它把"issue 是否包含可机读的结构化数据"
作为单一不变量来检查,所有 Probe/Archer/Herald 都依赖这个不变量。

设计目标:
- 零 LLM token: 纯结构化检查,任何 C 档或更低模型都能跑
- 零额外依赖: 仅 Python stdlib
- 离线可测: 支持 --offline + fixture 文件,bats 可直接喂样例

检查项(L1-L8):
  L1 标题格式:    ^\[FR-\d{3}\]
  L2 需求 ID 字段: 存在且匹配 ^FR-\d{3}$
  L3 Spec URL 字段: 存在且匹配 ^https://github.com/.../spec\.md#(fr|nfr)-\d{3}$
  L4 spec 可达:    gh api 可拉取 spec.md 原文
  L5 锚点存在:    spec.md 中存在 <a id="fr-XXX"></a>
  L6 锚点内容:    锚点上下文包含 "FR-XXX" 字样(防锚点误复用)
  L7 AC 锚点:      验收标准字段是 acceptance.md 完整 URL + 锚点可达 + 锚点存在 + 上下文含 FR-XXX
  L8 双向覆盖:    spec 中每个 FR 都有 issue;issue 中每个 FR 都在 spec

使用:
  python tools/verify_issue_schema.py --spec v0.1-001-specforge
  python tools/verify_issue_schema.py --spec v0.1-001-specforge --repo owner/repo
  python tools/verify_issue_schema.py --offline \\
      --spec-file .specforge/project/specs/v0.1-001-specforge/spec.md \\
      --issues-json /tmp/issues.json
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# ---------- 正则定义(单一真相源) ----------

RE_FR_ID = re.compile(r"^(FR|NFR)-\d{3}$")
RE_FR_IN_TITLE = re.compile(r"^\[(FR|NFR)-(\d{3})\]")
RE_SPEC_URL = re.compile(
    r"^https://github\.com/"
    r"(?P<owner>[A-Za-z0-9._-]+)/(?P<repo>[A-Za-z0-9._-]+)/blob/"
    r"(?P<branch>[A-Za-z0-9._/-]+)/\.specforge/project/specs/(?P<spec_id>[A-Za-z0-9._-]+)/spec\.md"
    r"#(?P<fragment>(?:fr|nfr)-\d{3})$"
)
RE_AC_URL = re.compile(
    r"^https://github\.com/"
    r"(?P<owner>[A-Za-z0-9._-]+)/(?P<repo>[A-Za-z0-9._-]+)/blob/"
    r"(?P<branch>[A-Za-z0-9._/-]+)/\.specforge/project/specs/(?P<spec_id>[A-Za-z0-9._-]+)/acceptance\.md"
    r"#(?P<fragment>ac-(?:fr|nfr)-\d{3})$"
)
RE_ANCHOR = re.compile(r'<a\s+id="((?:fr|nfr)-\d{3})"></a>')
RE_AC_ANCHOR = re.compile(r'<a\s+id="(ac-(?:fr|nfr)-\d{3})"></a>')
RE_AC_LINE = re.compile(r"^AC-\d+:\s*\S+")
RE_AC_FULL = re.compile(r"^AC-(\d+):\s*(.+)$")

# issue form 渲染后字段标题(必须与 .github/ISSUE_TEMPLATE/feature.yml 一致)
FIELD_FR_ID = "需求 ID"
FIELD_SPEC_URL = "Spec 链接"
FIELD_AC = "验收标准"


# ---------- 数据结构 ----------


@dataclass
class IssueCheck:
    number: int
    title: str
    fr_id: str = ""
    spec_url: str = ""
    spec_url_parsed: dict = field(default_factory=dict)
    ac_url: str = ""
    ac_url_parsed: dict = field(default_factory=dict)
    ac_lines: list[str] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.failures


# ---------- 解析 issue body ----------


def parse_issue_form(body: str) -> dict[str, str]:
    """
    从 issue form 渲染后的 markdown 抽取字段值。

    GitHub 把 form 字段渲染为:
        ### 需求 ID
        FR-001

        ### Spec 链接
        https://.../spec.md#fr-001

        ### 验收标准
        https://.../acceptance.md#ac-fr-001
    """
    fields: dict[str, str] = {}
    current: str | None = None
    buf: list[str] = []
    for line in body.splitlines():
        m = re.match(r"^###\s+(.+?)\s*$", line)
        if m:
            if current is not None:
                fields[current] = "\n".join(buf).strip()
            current = m.group(1).strip()
            buf = []
        else:
            if current is not None:
                buf.append(line)
    if current is not None:
        fields[current] = "\n".join(buf).strip()
    return fields


# ---------- 检查 ----------


def check_issue(
    issue: dict[str, Any], spec_cache: dict[str, str]
) -> IssueCheck:
    """对单个 issue 跑 L1-L7,返回检查结果(spec_cache 用于 L4-L6 跨调用复用)"""
    ic = IssueCheck(number=issue["number"], title=issue["title"])
    body = issue.get("body") or ""

    # L1: 标题
    m = RE_FR_IN_TITLE.match(ic.title)
    if not m:
        ic.failures.append(
            f"L1 标题必须以 [FR-XXX] 或 [NFR-XXX] 开头,当前: {ic.title!r}"
        )
    else:
        ic.fr_id = m.group(1) + "-" + m.group(2)

    # 解析 form 字段
    fields = parse_issue_form(body)

    # L2: 需求 ID 字段
    raw_fr = fields.get(FIELD_FR_ID, "").strip()
    if not raw_fr:
        ic.failures.append(f"L2 字段 '{FIELD_FR_ID}' 缺失")
    elif not RE_FR_ID.match(raw_fr):
        ic.failures.append(
            f"L2 字段 '{FIELD_FR_ID}' 格式错误,期望 ^(FR|NFR)-\\d{{3}}$, 实际: {raw_fr!r}"
        )
    elif ic.fr_id and raw_fr != ic.fr_id:
        ic.failures.append(
            f"L2 字段 '{FIELD_FR_ID}'({raw_fr})与标题中的 [{ic.fr_id}] 不一致"
        )
    else:
        ic.fr_id = raw_fr

    # L3: Spec URL 字段
    raw_url = fields.get(FIELD_SPEC_URL, "").strip()
    if not raw_url:
        ic.failures.append(f"L3 字段 '{FIELD_SPEC_URL}' 缺失")
    else:
        m = RE_SPEC_URL.match(raw_url)
        if not m:
            ic.failures.append(
                f"L3 字段 '{FIELD_SPEC_URL}' 格式错误,期望完整 GitHub URL "
                f"+ #fr-XXX (小写) 或 #nfr-XXX (小写),实际: {raw_url!r}"
            )
        else:
            ic.spec_url = raw_url
            ic.spec_url_parsed = m.groupdict()
            expected_fragment = raw_fr.split("-")[0].lower() + "-" + raw_fr.split("-")[1] if raw_fr else ""
            if m.group("fragment") != expected_fragment:
                ic.failures.append(
                    f"L3 URL fragment {m.group('fragment')!r} 与需求 ID {raw_fr!r} 不匹配 "
                    f"(应为 #{expected_fragment!r})"
                )

            # L4-L6: spec 可达 + 锚点存在 + 内容匹配
            if "OFFLINE" in spec_cache:
                # 离线模式:复用 fixture spec
                spec_text = spec_cache["OFFLINE"]
            else:
                spec_key = f"{m.group('owner')}/{m.group('repo')}@{m.group('branch')}:{m.group('spec_id')}"
                if spec_key not in spec_cache:
                    spec_cache[spec_key] = fetch_spec_markdown(
                        m.group("owner"),
                        m.group("repo"),
                        m.group("branch"),
                        m.group("spec_id"),
                    )
                spec_text = spec_cache[spec_key]

            if spec_text is None:
                ic.failures.append(
                    f"L4 无法获取 spec 文件 .specforge/project/specs/{m.group('spec_id')}/spec.md "
                    f"(repo {m.group('owner')}/{m.group('repo')}@{m.group('branch')})"
                )
            else:
                anchors = RE_ANCHOR.findall(spec_text)
                if m.group("fragment") not in anchors:
                    ic.failures.append(
                        f"L5 spec.md 中找不到锚点 {m.group('fragment')!r}; "
                        f"已声明的 FR 锚点: {sorted(set(anchors))}"
                    )
                else:
                    # L6: 锚点上下文(锚点行 + 后续 5 行)必须包含 "FR-XXX"
                    lines = spec_text.splitlines()
                    for i, line in enumerate(lines):
                        if f'<a id="{m.group("fragment")}">' in line:
                            context = "\n".join(lines[i : i + 6])
                            if raw_fr not in context:
                                ic.failures.append(
                                    f"L6 锚点 {m.group('fragment')!r} 周围找不到 {raw_fr!r}, "
                                    f"可能锚点被错误复用。上下文:\n{context}"
                                )
                            break

    # L7: AC 验收标准字段 — 必须是 acceptance.md URL + 锚点存在 + 上下文匹配
    raw_ac = fields.get(FIELD_AC, "").strip()
    if not raw_ac:
        ic.failures.append(f"L7 字段 '{FIELD_AC}' 缺失")
    else:
        m = RE_AC_URL.match(raw_ac)
        if not m:
            ic.failures.append(
                f"L7 字段 '{FIELD_AC}' 格式错误,期望完整 GitHub URL "
                f"+ #ac-fr-XXX 或 #ac-nfr-XXX (小写),实际: {raw_ac!r}"
            )
        else:
            ic.ac_url = raw_ac
            ic.ac_url_parsed = m.groupdict()
            expected_frag = (
                "ac-" + (raw_fr.split("-")[0].lower() + "-" + raw_fr.split("-")[1])
                if raw_fr
                else ""
            )
            if m.group("fragment") != expected_frag:
                ic.failures.append(
                    f"L7 URL fragment {m.group('fragment')!r} 与需求 ID {raw_fr!r} 不匹配 "
                    f"(应为 #{expected_frag!r})"
                )

            # 拉 acceptance.md 验证锚点
            if "OFFLINE" in spec_cache and "OFFLINE_ACC" in spec_cache:
                acc_text = spec_cache["OFFLINE_ACC"]
            else:
                acc_key = f"{m.group('owner')}/{m.group('repo')}@{m.group('branch')}:{m.group('spec_id')}"
                if acc_key not in spec_cache:
                    spec_cache[acc_key] = fetch_acceptance_markdown(
                        m.group("owner"),
                        m.group("repo"),
                        m.group("branch"),
                        m.group("spec_id"),
                    )
                acc_text = spec_cache[acc_key]

            if acc_text is None:
                ic.failures.append(
                    f"L7 无法获取 acceptance 文件 .specforge/project/specs/{m.group('spec_id')}/acceptance.md "
                    f"(repo {m.group('owner')}/{m.group('repo')}@{m.group('branch')})"
                )
            else:
                acc_anchors = RE_AC_ANCHOR.findall(acc_text)
                if m.group("fragment") not in acc_anchors:
                    ic.failures.append(
                        f"L7 acceptance.md 中找不到锚点 {m.group('fragment')!r}; "
                        f"已声明的 AC 锚点: {sorted(set(acc_anchors))}"
                    )
                else:
                    # 锚点上下文(锚点行 + 后续 8 行)必须包含 "FR-XXX" 字样
                    lines = acc_text.splitlines()
                    for i, line in enumerate(lines):
                        if f'<a id="{m.group("fragment")}">' in line:
                            context = "\n".join(lines[i : i + 9])
                            if raw_fr not in context:
                                ic.failures.append(
                                    f"L7 锚点 {m.group('fragment')!r} 周围找不到 {raw_fr!r}, "
                                    f"可能锚点被错误复用。上下文:\n{context}"
                                )
                            break

    return ic


def fetch_spec_markdown(
    owner: str, repo: str, branch: str, spec_id: str
) -> str | None:
    """
    用 gh api 拉取 spec.md 原文。返回 None 表示拉取失败。
    gh api 自动处理公私仓库 auth。
    """
    path = f".specforge/project/specs/{spec_id}/spec.md"
    try:
        out = subprocess.check_output(
            [
                "gh",
                "api",
                f"repos/{owner}/{repo}/contents/{path}",
                "-H",
                f"Accept: application/vnd.github.raw",
                "--method",
                "GET",
                "--field",
                f"ref={branch}",
            ],
            stderr=subprocess.STDOUT,
        )
        return out.decode("utf-8", errors="replace")
    except subprocess.CalledProcessError as e:
        sys.stderr.write(
            f"[warn] gh api failed for {owner}/{repo}@{branch}:{path}\n"
            f"       {e.output.decode(errors='replace')}\n"
        )
        return None
    except FileNotFoundError:
        sys.stderr.write(
            "[warn] gh CLI not found;请安装 https://cli.github.com/\n"
        )
        return None


def fetch_acceptance_markdown(
    owner: str, repo: str, branch: str, spec_id: str
) -> str | None:
    """用 gh api 拉取 acceptance.md 原文。返回 None 表示拉取失败。"""
    path = f".specforge/project/specs/{spec_id}/acceptance.md"
    try:
        out = subprocess.check_output(
            [
                "gh",
                "api",
                f"repos/{owner}/{repo}/contents/{path}",
                "-H",
                f"Accept: application/vnd.github.raw",
                "--method",
                "GET",
                "--field",
                f"ref={branch}",
            ],
            stderr=subprocess.STDOUT,
        )
        return out.decode("utf-8", errors="replace")
    except subprocess.CalledProcessError as e:
        sys.stderr.write(
            f"[warn] gh api failed for {owner}/{repo}@{branch}:{path}\n"
            f"       {e.output.decode(errors='replace')}\n"
        )
        return None
    except FileNotFoundError:
        sys.stderr.write(
            "[warn] gh CLI not found;请安装 https://cli.github.com/\n"
        )
        return None


# ---------- 报告 ----------


def report(checks: list[IssueCheck], spec_frs: set[str] | None) -> int:
    ok = [c for c in checks if c.ok]
    bad = [c for c in checks if not c.ok]
    print(f"\n总览: {len(checks)} 个 Feature issue 验证,{len(ok)} 通过,{len(bad)} 失败\n")

    if bad:
        print("[拒绝]\n")
        for c in bad:
            print(f"Issue #{c.number}  {c.title}")
            for f in c.failures:
                print(f"  - {f}")
            print()
        # 最多列出 3 个阻塞问题(同 Lex 风格)
        flat = []
        for c in bad:
            for f in c.failures:
                flat.append((c, f))
        if len(flat) > 3:
            print(f"... 还有 {len(flat) - 3} 个问题(被 Lex 风格截断)\n")
        return 1

    # 双向覆盖
    if spec_frs is not None and checks:
        issue_frs = {c.fr_id for c in ok}
        orphans_in_spec = sorted(spec_frs - issue_frs)
        orphans_in_issues = sorted(issue_frs - spec_frs)
        if orphans_in_spec or orphans_in_issues:
            print("[拒绝] L8 双向覆盖失败\n")
            if orphans_in_spec:
                print(f"  - spec 中有以下 FR 没有对应 issue: {orphans_in_spec}")
            if orphans_in_issues:
                print(f"  - 以下 issue 引用了 spec 中不存在的 FR: {orphans_in_issues}")
            print()
            return 1

    print("[通过]\n")
    for c in checks:
        print(
            f"  Issue #{c.number}  {c.title}  "
            f"(AC 锚点: {c.ac_url_parsed.get('fragment', '-')})"
        )
    return 0


# ---------- 入口 ----------


def load_issues_from_gh(repo: str) -> list[dict[str, Any]]:
    out = subprocess.check_output(
        [
            "gh",
            "issue",
            "list",
            "--repo",
            repo,
            "--label",
            "Feature",
            "--state",
            "all",
            "--json",
            "number,title,body,state",
            "--limit",
            "500",
        ]
    )
    return json.loads(out)


def load_spec_frs_from_gh(
    owner: str, repo: str, branch: str, spec_id: str
) -> set[str] | None:
    text = fetch_spec_markdown(owner, repo, branch, spec_id)
    if text is None:
        return None
    return {f"FR-{a.split('-')[1].zfill(3)}" for a in RE_ANCHOR.findall(text)}


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--spec", help="spec-id,例如 v0.1-001-specforge")
    p.add_argument("--repo", help="owner/repo,默认从 gh repo view 推断")
    p.add_argument("--branch", help="默认分支,默认从 gh repo view 推断")
    p.add_argument(
        "--offline",
        action="store_true",
        help="离线模式(给 bats 用): 用 --spec-file + --acceptance-file + --issues-json",
    )
    p.add_argument("--spec-file", help="离线模式: spec.md 路径")
    p.add_argument("--acceptance-file", help="离线模式: acceptance.md 路径(L7 锚点校验)")
    p.add_argument("--issues-json", help="离线模式: issue 列表 JSON 路径")
    args = p.parse_args()

    if args.offline:
        if not (args.spec_file and args.issues_json):
            sys.stderr.write("--offline 必须配合 --spec-file 和 --issues-json\n")
            return 2
        spec_text = Path(args.spec_file).read_text(encoding="utf-8")
        spec_frs = {f"FR-{a.split('-')[1].zfill(3)}" for a in RE_ANCHOR.findall(spec_text)}
        with open(args.issues_json, "r", encoding="utf-8") as f:
            issues = json.load(f)
        # 离线模式:任何 spec_url/ac_url 都视为指向同一份 fixture
        # (L4/L7 不发网络请求,L5/L6 用 spec fixture 的锚点表;L7 用 acceptance fixture)
        spec_cache: dict[str, str] = {"OFFLINE": spec_text}
        if args.acceptance_file:
            acc_path = Path(args.acceptance_file)
            if acc_path.exists():
                spec_cache["OFFLINE_ACC"] = acc_path.read_text(encoding="utf-8")
    else:
        if not args.spec:
            sys.stderr.write("--spec 必填(或使用 --offline)\n")
            return 2
        repo = args.repo
        branch = args.branch
        if not repo:
            repo = subprocess.check_output(
                ["gh", "repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"]
            ).decode().strip()
        if not branch:
            branch = subprocess.check_output(
                [
                    "gh", "repo", "view", repo,
                    "--json", "defaultBranchRef", "-q", ".defaultBranchRef.name",
                ]
            ).decode().strip()
        owner, reponame = repo.split("/", 1)
        spec_frs = load_spec_frs_from_gh(owner, reponame, branch, args.spec)
        issues = load_issues_from_gh(repo)
        spec_cache = {}

    checks = [check_issue(i, spec_cache) for i in issues]
    return report(checks, spec_frs)


if __name__ == "__main__":
    sys.exit(main())
