#!/usr/bin/env python3
"""
verify_acceptance.py — 验证 Sage 生成的 acceptance.md 是否合格

这是 Lex 阶段一输入校验的工具。Lex 在读 spec.md 之前先跑这个,
确认 Sage 的工作(尤其是 acceptance 拆分)有没有做好, 再做语义级审核。

设计目标:
- 零 LLM token: 纯结构化检查
- 零额外依赖: 仅 Python stdlib
- 离线可测: 支持 --offline + fixture 文件, bats 直接喂样例

检查项(L1-L5):
  L1 文件存在:        .specforge/project/specs/{id}/acceptance.md 存在
  L2 FR/NFR 节存在:   spec.md 中的每个 FR/NFR 在 acceptance.md 中都有对应 ## 节
  L3 AC 编号连续:     每个 FR/NFR 节内, ### AC-N 从 1 开始连续递增
  L4 AC 内容非空:     每个 ### AC-N 至少 1 条项目符号, 且有可断言的具体内容
  L5 反向覆盖:        acceptance.md 中的 ## FR/NFR 节都对应 spec.md 中存在的 FR/NFR
                      (防 acceptance 多出 spec 没有的"幽灵 FR")

使用:
  python tools/verify_acceptance.py --spec v0.1-001-specforge
  python tools/verify_acceptance.py --offline \\
      --spec-file .specforge/project/specs/v0.1-001-specforge/spec.md \\
      --acceptance-file .specforge/project/specs/v0.1-001-specforge/acceptance.md
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# ---------- 正则定义 ----------

# spec.md 中的 FR/NFR 节: ## FR-010 {title} 或 ## NFR-020 {title}
RE_FR_SECTION = re.compile(r"^##\s+(FR|NFR)-(\d{3})\b", re.MULTILINE)

# acceptance.md 中的 FR/NFR 节: ## FR-010 {title}
RE_ACC_FR_SECTION = re.compile(r"^##\s+(FR|NFR)-(\d{3})\b", re.MULTILINE)

# acceptance.md 中的 AC 节: ### AC-1 或 ### AC-2
RE_AC_SECTION = re.compile(r"^###\s+AC-(\d+)\s*$", re.MULTILINE)

# 项目符号: 行首可选空白 + (- 或 *) + 至少一个空白 + 捕获后面的非空内容
RE_BULLET = re.compile(r"^[\s]*[-*]\s+(.+)$")

# 严禁作为 AC 内容的占位符(应被替换为真实条件)
PLACEHOLDER_PATTERNS = [
    re.compile(r"\{\{.*?\}\}"),  # {{ 变量 }}
    re.compile(r"\{[a-z_]+\}"),   # {placeholder}
]


# ---------- 数据类 ----------

@dataclass
class AccResult:
    code: str           # L1/L2/...
    name: str
    passed: bool
    message: str = ""
    failures: list[str] = field(default_factory=list)


@dataclass
class SpecFRSpec:
    fr_id: str          # FR-010
    nfr: bool           # True if NFR
    number: int         # 10
    title: str = ""


# ---------- 工具函数 ----------

def gh_api_read(path: str) -> str | None:
    """用 gh api 读取文件。返回 None 表示失败。"""
    try:
        out = subprocess.check_output(
            ["gh", "api", f"contents/{path}?ref=main"],
            stderr=subprocess.STDOUT,
        )
        import base64
        import json
        data = json.loads(out)
        return base64.b64decode(data["content"]).decode("utf-8")
    except Exception as e:  # noqa: BLE001
        print(f"warn: gh api failed for {path}: {e}", file=sys.stderr)
        return None


def fetch_spec_text(spec_id: str) -> str | None:
    """读 main 分支上的 .specforge/project/specs/{spec_id}/spec.md"""
    return gh_api_read(f".specforge/project/specs/{spec_id}/spec.md")


def fetch_acceptance_text(spec_id: str) -> str | None:
    """读 main 分支上的 .specforge/project/specs/{spec_id}/acceptance.md"""
    return gh_api_read(f".specforge/project/specs/{spec_id}/acceptance.md")


def parse_fr_sections(text: str) -> list[SpecFRSpec]:
    """从 spec.md 文本中提取所有 FR/NFR 节。"""
    result = []
    for m in RE_FR_SECTION.finditer(text):
        is_nfr = m.group(1) == "NFR"
        result.append(SpecFRSpec(
            fr_id=f"{m.group(1)}-{m.group(2)}",
            nfr=is_nfr,
            number=int(m.group(2)),
        ))
    return result


def parse_acc_sections(text: str) -> dict[str, list[int]]:
    """从 acceptance.md 文本中提取所有 FR/NFR 节 + 其下 AC-N 列表。

    返回: { "FR-010": [1, 2, 3], "NFR-020": [1], ... }
    """
    sections: dict[str, list[int]] = {}
    current_fr: str | None = None
    current_acs: list[int] = []

    for line in text.splitlines():
        # 匹配 ## FR-XXX 或 ## NFR-XXX 节标题
        m = RE_ACC_FR_SECTION.match(line)
        if m:
            # 进入新节: 提交上一个节
            if current_fr is not None:
                sections[current_fr] = current_acs
            current_fr = f"{m.group(1)}-{m.group(2)}"
            current_acs = []
            continue

        # 匹配 ### AC-N
        am = RE_AC_SECTION.match(line)
        if am and current_fr is not None:
            current_acs.append(int(am.group(1)))

    # 收尾
    if current_fr is not None:
        sections[current_fr] = current_acs

    return sections


def extract_ac_body(text: str, fr_id: str, ac_num: int) -> list[str]:
    """提取 acceptance.md 中, ## FR-XXX 节下 ### AC-N 标题后面的项目符号列表。

    返回: 项目符号文本列表(去掉前导 - 符号)。
    """
    lines = text.splitlines()
    in_section = False
    in_target_ac = False
    bullets: list[str] = []

    for line in lines:
        # 进入目标 FR/NFR 节
        m = RE_ACC_FR_SECTION.match(line)
        if m and f"{m.group(1)}-{m.group(2)}" == fr_id:
            in_section = True
            continue
        if m and in_section:
            # 进入下一个节, 结束
            break

        if not in_section:
            continue

        # 检查是否进入目标 AC 节
        am = RE_AC_SECTION.match(line)
        if am:
            if int(am.group(1)) == ac_num:
                in_target_ac = True
                continue
            else:
                in_target_ac = False
                continue

        if in_target_ac:
            m = RE_BULLET.match(line)
            if m:
                bullets.append(m.group(1).strip())

    return bullets


# ---------- L1-L5 校验 ----------

def check_L1_exists(acceptance_text: str | None) -> AccResult:
    r = AccResult(code="L1", name="文件存在", passed=False)
    if acceptance_text is None:
        r.message = "acceptance.md 缺失"
        r.failures.append("未找到 acceptance.md")
        return r
    if acceptance_text.strip() == "":
        r.message = "acceptance.md 为空"
        r.failures.append("acceptance.md 内容为空")
        return r
    r.passed = True
    r.message = f"acceptance.md 已读取 ({len(acceptance_text)} 字符)"
    return r


def check_L2_fr_sections(spec_frs: list[SpecFRSpec], acc_sections: dict[str, list[int]]) -> AccResult:
    """spec.md 中每个 FR/NFR 在 acceptance.md 都有同名节。"""
    r = AccResult(code="L2", name="FR/NFR 节存在", passed=False)
    spec_ids = {f.fr_id for f in spec_frs}
    acc_ids = set(acc_sections.keys())
    missing = spec_ids - acc_ids
    if missing:
        r.failures.append(
            f"acceptance.md 缺少 {len(missing)} 个 FR/NFR 节: {sorted(missing)}"
        )
        return r
    r.passed = True
    r.message = f"spec.md 中 {len(spec_ids)} 个 FR/NFR 在 acceptance.md 中都有同名节"
    return r


def check_L3_ac_sequential(acc_sections: dict[str, list[int]]) -> AccResult:
    """每个 FR/NFR 节内, AC-N 从 1 开始连续递增。"""
    r = AccResult(code="L3", name="AC 编号连续", passed=False)
    bad: list[str] = []
    for fr_id, acs in acc_sections.items():
        if not acs:
            bad.append(f"{fr_id}: 无任何 AC")
            continue
        expected = list(range(1, len(acs) + 1))
        if acs != expected:
            bad.append(f"{fr_id}: AC 编号 {acs} (应为 {expected})")
    if bad:
        r.failures.append("AC 编号不连续: " + "; ".join(bad))
        return r
    r.passed = True
    r.message = f"{len(acc_sections)} 个 FR/NFR 节的 AC 编号都从 1 连续"
    return r


def check_L4_ac_content(acceptance_text: str, acc_sections: dict[str, list[int]]) -> AccResult:
    """每个 AC 至少 1 条项目符号, 内容不是占位符。"""
    r = AccResult(code="L4", name="AC 内容非空", passed=False)
    bad: list[str] = []
    for fr_id, acs in acc_sections.items():
        for ac_num in acs:
            bullets = extract_ac_body(acceptance_text, fr_id, ac_num)
            if not bullets:
                bad.append(f"{fr_id} / AC-{ac_num}: 缺少项目符号内容")
                continue
            # 检查是否全是占位符
            for b in bullets:
                if any(p.search(b) for p in PLACEHOLDER_PATTERNS):
                    bad.append(
                        f"{fr_id} / AC-{ac_num}: 项目符号 '{b[:40]}...' 是占位符, 应替换为真实条件"
                    )
                    break
    if bad:
        r.failures.append("AC 内容不合格: " + "; ".join(bad))
        return r
    r.passed = True
    total_ac = sum(len(acs) for acs in acc_sections.values())
    r.message = f"全部 {total_ac} 条 AC 都有项目符号内容, 无占位符残留"
    return r


def check_L5_reverse_cover(spec_frs: list[SpecFRSpec], acc_sections: dict[str, list[int]]) -> AccResult:
    """acceptance.md 中的 ## FR/NFR 节都对应 spec.md 中存在的 FR/NFR (防幽灵 FR)。"""
    r = AccResult(code="L5", name="反向覆盖", passed=False)
    spec_ids = {f.fr_id for f in spec_frs}
    acc_ids = set(acc_sections.keys())
    ghost = acc_ids - spec_ids
    if ghost:
        r.failures.append(
            f"acceptance.md 引用了 spec.md 中不存在的 FR/NFR: {sorted(ghost)}"
        )
        return r
    r.passed = True
    r.message = f"acceptance.md 中 {len(acc_ids)} 个 FR/NFR 都在 spec.md 中存在"
    return r


# ---------- 主流程 ----------

def run_checks(
    spec_text: str,
    acceptance_text: str,
) -> list[AccResult]:
    spec_frs = parse_fr_sections(spec_text)
    acc_sections = parse_acc_sections(acceptance_text)

    return [
        check_L1_exists(acceptance_text),
        check_L2_fr_sections(spec_frs, acc_sections),
        check_L3_ac_sequential(acc_sections),
        check_L4_ac_content(acceptance_text, acc_sections),
        check_L5_reverse_cover(spec_frs, acc_sections),
    ]


def report(results: list[AccResult]) -> int:
    failed = [r for r in results if not r.passed]
    passed = [r for r in results if r.passed]

    for r in results:
        status = "[通过]" if r.passed else "[拒绝]"
        print(f"{r.code} {status} {r.name}: {r.message}")
        for f in r.failures:
            print(f"   - {f}")

    print()
    if failed:
        print(f"[拒绝] {len(failed)} 项校验失败, {len(passed)} 项通过")
        print("Sage 须修复 acceptance.md 后再通知 Lex 重审")
        return 1
    print(f"[通过] {len(passed)} 项校验全部通过")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="验证 acceptance.md 是否合格 (Lex 阶段一)")
    p.add_argument("--spec", help="spec-id, 例如 v0.1-001-specforge")
    p.add_argument("--repo", default="zillionare/specforge", help="owner/repo, 默认 zillionare/specforge")
    p.add_argument("--branch", default="main", help="spec 所在分支, 默认 main")
    p.add_argument("--offline", action="store_true", help="离线模式: 直接用 --spec-file/--acceptance-file")
    p.add_argument("--spec-file", help="离线模式: spec.md 路径")
    p.add_argument("--acceptance-file", help="离线模式: acceptance.md 路径")
    args = p.parse_args()

    if args.offline:
        if not args.spec_file:
            print("--offline 必须配合 --spec-file", file=sys.stderr)
            return 1
        spec_path = Path(args.spec_file)
        if not spec_path.exists():
            print(f"找不到 {spec_path}", file=sys.stderr)
            return 1
        spec_text = spec_path.read_text(encoding="utf-8")
        # acceptance 文件缺失不算 hard error: 让 L1 检查统一报告
        if args.acceptance_file:
            acc_path = Path(args.acceptance_file)
            acceptance_text = acc_path.read_text(encoding="utf-8") if acc_path.exists() else None
        else:
            acceptance_text = None
    else:
        if not args.spec:
            print("非离线模式必须 --spec SPEC_ID", file=sys.stderr)
            return 1
        spec_text = fetch_spec_text(args.spec)
        acceptance_text = fetch_acceptance_text(args.spec)
        if spec_text is None:
            print(f"无法读取 main 分支上的 .specforge/project/specs/{args.spec}/spec.md", file=sys.stderr)
            return 1
        if acceptance_text is None:
            # 不报错, 走 L1 检查
            pass

    results = run_checks(spec_text or "", acceptance_text or "")
    return report(results)


if __name__ == "__main__":
    sys.exit(main())
