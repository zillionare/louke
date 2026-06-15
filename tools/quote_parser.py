#!/usr/bin/env python3
"""
quote_parser.py — 解析 spec.md 中的 markdown quote block 对话

这是 spec 004-quote-dialogue 引入的工具, 取代 PR inline comment 流程。
Sage/Lex/Maestro 都依赖它来判定 spec.md 是否 ready。

设计目标:
- 零 LLM token: 纯结构化解析, C 档模型也能跑
- 零额外依赖: 仅 Python stdlib
- 单文件, 可被 bash 包装调用

支持的 quote 格式:

    > **Sage:** 问题内容 [open]
    >> **Aaron:** 回答内容 ✓ resolved
    >>> **Sage:** 追问 [open]
    >>>> **Aaron:** 再回答 ✓ resolved

前缀 > 数量表示对话深度 (1=Sage, 2=用户, 3=Sage 追问, ...).
状态标记: ✓ resolved / [open] / [blocked-by-N] / [wontfix] / [superseded]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any


RE_STATUS_EXPLICIT = re.compile(
    r"(?:"
    r"✓\s*resolved"
    r"|\[open\]"
    r"|\[blocked-by-(\d+)\]"
    r"|\[wontfix\]"
    r"|\[superseded\]"
    r")\s*$"
)

RE_QUOTE_LINE = re.compile(
    r"^(?P<depth>\s*(?:>\s*)+)"
    r"\*\*"
    r"(?P<name>[^*:]+?)"
    r":\*\*\s*"
    r"(?P<body>.*?)\s*"
    r"(?P<status>✓\s*resolved|\[open\]|\[blocked-by-\d+\]|\[wontfix\]|\[superseded])?\s*$"
)

# 单元标题: ### US-010 / ### FR-001 / ### NFR-010 / 等 (3 位零填充)
RE_UNIT_HEADING = re.compile(r"^###\s+(US|FR|NFR)-(\d{3})\b")
# 顶节标题: ## 功能需求 / ## 用户故事 / ## 非功能需求 / ## 排除项 等
RE_TOP_HEADING = re.compile(r"^##\s+\S")

# YAML 字段: resolved: ✅ / resolved: ⚠️ / resolved: 某个状态
RE_YAML_FIELD = re.compile(r"^\s*resolved\s*:\s*(\S+)\s*$", re.IGNORECASE)
# YAML 字段: testability / valid
RE_YAML_TESTABILITY = re.compile(r"^\s*testability\s*:\s*(\S+)\s*$", re.IGNORECASE)
RE_YAML_VALID = re.compile(r"^\s*valid\s*:\s*(\S+)\s*$", re.IGNORECASE)

KNOWN_AGENT_NAMES = frozenset({
    "Sage", "Lex", "Scout", "Warden", "Probe", "Judge",
    "Archer", "Cynic", "Forge", "Prism", "Keeper",
    "Herald", "Arbiter", "Hunter", "Shield", "Maestro",
})

RE_FENCE = re.compile(r"^\s*(```|~~~)")


@dataclass
class Quote:
    """一条 quote 对话单元"""

    depth: int
    speaker: str
    body: str
    status: str
    line_number: int
    blocked_by: int | None = None
    owner_close_role: str = "user"


@dataclass
class Unit:
    """spec.md 中的一个需求/故事单元

    范围: ### US-XXX / ### FR-XXX / ### NFR-XXX 标题后, 到下一个 ### 或 ## 之前。
    """
    id: str                            # 例 "FR-010", "US-001"
    kind: str                          # "US" | "FR" | "NFR"
    heading_line: int
    last_quote: Quote | None = None    # 该单元下最后一条 quote
    open_quotes: list[Quote] = field(default_factory=list)
    yaml_resolved: str = ""            # YAML 里的 resolved 值 (✅/⚠️/<empty>)
    yaml_testability: str = ""
    yaml_valid: str = ""

    @property
    def has_yaml(self) -> bool:
        return self.yaml_resolved != ""

    def quote_state_summary(self) -> str:
        if not self.open_quotes:
            if self.last_quote is None:
                return "no-quote"
            return self.last_quote.status
        return f"{len(self.open_quotes)} open"

    def is_frnfr(self) -> bool:
        return self.kind in ("FR", "NFR")

    def is_ready(self) -> tuple[bool, list[str]]:
        """返回 (ready, blockers)。"""
        blockers: list[str] = []
        if self.is_frnfr():
            # FR/NFR: YAML resolved = ✅ 且 单元下没有 open quote
            if self.yaml_resolved == "✅":
                pass
            elif self.yaml_resolved == "⚠️" or self.yaml_resolved == "":
                blockers.append(f"yaml.resolved={self.yaml_resolved!r} (need ✅)")
            else:
                blockers.append(f"yaml.resolved={self.yaml_resolved!r} (unknown marker)")
            if self.open_quotes:
                blockers.append(
                    f"{len(self.open_quotes)} open quote(s) (last={self.last_quote.status if self.last_quote else 'none'})"
                )
        else:
            # 其他单元 (US 等): 最后一条 quote 是 closed (或没有 quote)
            if self.last_quote is None:
                pass  # 无对话 = 未被质疑 = 视为 closed
            elif self.last_quote.status != "resolved":
                blockers.append(
                    f"last quote status={self.last_quote.status!r} (need resolved or no quote)"
                )
        return (len(blockers) == 0, blockers)


@dataclass
class ParseResult:
    """spec.md 解析结果"""

    quotes: list[Quote] = field(default_factory=list)
    open_quotes: list[Quote] = field(default_factory=list)
    resolved_quotes: list[Quote] = field(default_factory=list)
    blocked_quotes: list[Quote] = field(default_factory=list)
    wontfix_quotes: list[Quote] = field(default_factory=list)
    superseded_quotes: list[Quote] = field(default_factory=list)
    speaker_counts: dict[str, int] = field(default_factory=dict)
    depth_histogram: dict[int, int] = field(default_factory=dict)
    units: list[Unit] = field(default_factory=list)
    is_ready: bool = False
    ready_blockers: list[str] = field(default_factory=list)  # 详细描述哪些单元阻止 ready


def parse_spec(spec_path: Path) -> ParseResult:
    """解析 spec.md。

    两层解析:
      1) quote block 解析 (原有) — 统计对话
      2) unit 切分 + YAML meta 解析 (新) — 按 ### 标题切单元, 读每个单元的 YAML

    ready 判定:
      - FR/NFR 单元: yaml.resolved == ✅ 且 单元下没有 open quote
      - 其他单元: 最后一条 quote 是 resolved, 或该单元没有 quote
    """
    text = spec_path.read_text(encoding="utf-8")
    lines = text.splitlines()

    result = ParseResult()
    in_code_block = False

    # 第一遍: quote block 解析 (保持原行为)
    for i, line in enumerate(lines, start=1):
        if RE_FENCE.match(line):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue
        m = RE_QUOTE_LINE.match(line)
        if not m:
            continue

        prefix = m.group("depth")
        depth = prefix.count(">")
        speaker = m.group("name").strip()
        body = m.group("body").strip()
        status_raw = (m.group("status") or "").strip()

        if not status_raw:
            status = "open"
            blocked_by = None
        elif status_raw.startswith("✓"):
            status = "resolved"
            blocked_by = None
        elif status_raw == "[open]":
            status = "open"
            blocked_by = None
        elif status_raw.startswith("[blocked-by-"):
            n = int(re.search(r"\d+", status_raw).group(0))
            status = "blocked"
            blocked_by = n
        elif status_raw == "[wontfix]":
            status = "wontfix"
            blocked_by = None
        elif status_raw == "[superseded]":
            status = "superseded"
            blocked_by = None
        else:
            status = "unknown"
            blocked_by = None

        owner_role = "agent" if speaker in KNOWN_AGENT_NAMES else "user"
        quote = Quote(
            depth=depth,
            speaker=speaker,
            body=body,
            status=status,
            line_number=i,
            blocked_by=blocked_by,
            owner_close_role=owner_role,
        )
        result.quotes.append(quote)

        if status == "open":
            result.open_quotes.append(quote)
        elif status == "resolved":
            result.resolved_quotes.append(quote)
        elif status == "blocked":
            result.blocked_quotes.append(quote)
        elif status == "wontfix":
            result.wontfix_quotes.append(quote)
        elif status == "superseded":
            result.superseded_quotes.append(quote)

        result.speaker_counts[speaker] = result.speaker_counts.get(speaker, 0) + 1
        result.depth_histogram[depth] = result.depth_histogram.get(depth, 0) + 1

    # 第二遍: 切单元 + 读 YAML meta
    current_unit: Unit | None = None
    in_code_block = False
    for i, line in enumerate(lines, start=1):
        m_head = RE_UNIT_HEADING.match(line)
        if m_head:
            kind = m_head.group(1)
            num = m_head.group(2)
            unit_id = f"{kind}-{num}"
            current_unit = Unit(id=unit_id, kind=kind, heading_line=i)
            result.units.append(current_unit)
            continue
        if current_unit is None:
            continue
        if RE_TOP_HEADING.match(line):
            # 下一个 ## 章节意味着当前单元结束
            current_unit = None
            continue
        if RE_FENCE.match(line):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            m_r = RE_YAML_FIELD.match(line)
            m_t = RE_YAML_TESTABILITY.match(line)
            m_v = RE_YAML_VALID.match(line)
            if m_r:
                current_unit.yaml_resolved = m_r.group(1)
            elif m_t:
                current_unit.yaml_testability = m_t.group(1)
            elif m_v:
                current_unit.yaml_valid = m_v.group(1)
            continue

    # 第三遍: 把 quote 挂到所属 unit
    # 单元的 line 范围: [unit.heading_line, next_unit.heading_line) 或文件末尾
    if result.units:
        for u, next_u in zip(result.units, result.units[1:] + [None]):
            upper = next_u.heading_line if next_u else 10**9
            for q in result.quotes:
                if u.heading_line <= q.line_number < upper:
                    u.last_quote = q  # 最后一个胜出
                    if q.status == "open":
                        u.open_quotes.append(q)

    # 第四遍: 汇总 ready 判定
    for u in result.units:
        ready, blockers = u.is_ready()
        if not ready:
            result.ready_blockers.append(f"{u.id}: " + "; ".join(blockers))
    result.is_ready = len(result.ready_blockers) == 0
    return result


def fmt_quote_summary(q: Quote) -> str:
    """单条 quote 的简明摘要"""
    blocked = f" (blocked by FR-{q.blocked_by:03d})" if q.blocked_by else ""
    return f"L{q.line_number} [d{q.depth}] {q.speaker}: {q.body[:80]}{blocked}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("spec_path", type=Path, help="path to spec.md")
    parser.add_argument(
        "--check-ready",
        action="store_true",
        help="exit 0 if 0 [open] quotes, exit 1 otherwise (for Maestro gate)",
    )
    parser.add_argument(
        "--check-violations",
        action="store_true",
        help="detect ownership violations: who closed a quote that wasn't theirs",
    )
    parser.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="output format",
    )
    args = parser.parse_args()

    if not args.spec_path.exists():
        print(f"quote_parser: {args.spec_path} not found", file=sys.stderr)
        return 2

    result = parse_spec(args.spec_path)

    if args.check_ready:
        if result.is_ready:
            return 0
        print(f"spec not ready: {len(result.ready_blockers)} unit(s) blocking", file=sys.stderr)
        for b in result.ready_blockers:
            print(f"  {b}", file=sys.stderr)
        return 1

    if args.check_violations:
        violations = []
        for q in result.resolved_quotes + result.blocked_quotes + result.wontfix_quotes + result.superseded_quotes:
            if q.owner_close_role == "user" and q.status != "open":
                violations.append(q)
        if not violations:
            print(f"no ownership violations in {args.spec_path}")
            return 0
        print(
            f"OWNERSHIP VIOLATIONS: {len(violations)} quote(s) closed by non-owner",
            file=sys.stderr,
        )
        for v in violations:
            print(
                f"  L{v.line_number} d{v.depth} {v.speaker} [status={v.status}]: "
                f"a user quote should only be closed by user",
                file=sys.stderr,
            )
        return 1

    if args.format == "json":
        out = {
            "total_quotes": len(result.quotes),
            "open_count": len(result.open_quotes),
            "resolved_count": len(result.resolved_quotes),
            "blocked_count": len(result.blocked_quotes),
            "wontfix_count": len(result.wontfix_quotes),
            "superseded_count": len(result.superseded_quotes),
            "is_ready": result.is_ready,
            "ready_blockers": result.ready_blockers,
            "speaker_counts": result.speaker_counts,
            "depth_histogram": {str(k): v for k, v in sorted(result.depth_histogram.items())},
            "open_quotes": [asdict(q) for q in result.open_quotes],
            "resolved_quotes": [asdict(q) for q in result.resolved_quotes],
            "blocked_quotes": [asdict(q) for q in result.blocked_quotes],
            "units": [asdict(u) for u in result.units],
        }
        print(json.dumps(out, ensure_ascii=False, indent=2))
    else:
        print(f"spec: {args.spec_path}")
        print(f"  total quotes: {len(result.quotes)}")
        print(f"  open: {len(result.open_quotes)}")
        print(f"  resolved: {len(result.resolved_quotes)}")
        if result.blocked_quotes:
            print(f"  blocked: {len(result.blocked_quotes)}")
        if result.wontfix_quotes:
            print(f"  wontfix: {len(result.wontfix_quotes)}")
        if result.superseded_quotes:
            print(f"  superseded: {len(result.superseded_quotes)}")
        print(f"  units: {len(result.units)}")
        print(f"  is_ready: {result.is_ready}")
        if result.ready_blockers:
            print("\n[ready] blockers:")
            for b in result.ready_blockers:
                print(f"  {b}")
        if result.speaker_counts:
            print(f"  speakers: {result.speaker_counts}")
        if result.depth_histogram:
            hist = ", ".join(
                f"d{k}={v}" for k, v in sorted(result.depth_histogram.items())
            )
            print(f"  depth: {hist}")
        if result.open_quotes:
            print("\n[open] quotes:")
            for q in result.open_quotes:
                print(f"  {fmt_quote_summary(q)}")
        if result.resolved_quotes:
            print(f"\n[resolved] quotes: {len(result.resolved_quotes)} total")

    return 0


if __name__ == "__main__":
    sys.exit(main())