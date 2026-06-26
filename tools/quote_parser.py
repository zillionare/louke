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
    r"(?:"
    r"\*\*(?P<name>[^*\s][^*]*?):?\*\*:?\s*"
    r"|"
    r"(?P<plainname>[A-Za-z][A-Za-z0-9_\-]*|\*\*[^*]+\*\*):\s+"
    r")"
    r"(?P<body>.*?)"
    r"\s*"
    r"(?P<status>✓\s*(?:resolved)?|\[open\]|\[blocked-by-\d+\]|\[wontfix\]|\[superseded])?"
    r"\s*$"
)

# 单元标题: ### US-010 / ### FR-001 / ### NFR-010 / 等 (3 位零填充)
RE_UNIT_HEADING = re.compile(r"^###\s+(US|FR|NFR)-(\d{3})\b")
# 顶节标题: ## 功能需求 / ## 用户故事 / ## 非功能需求 / ## 排除项 等
RE_TOP_HEADING = re.compile(r"^##\s+\S")

# FR/NFR 元数据 (表格格式, FR-082 起)
# 表格行: | <col1> | <col2> | <col3> |
RE_TABLE_ROW = re.compile(r"^\s*\|\s*(.+?)\s*\|\s*$")
# 表头分隔行: |---|---|---| 或 |:--|:--:|--:|
RE_TABLE_SEP = re.compile(r"^\s*\|[\s:|-]+\|\s*$")
# 表头里的列名
COLUMN_ALIASES = {
    # 有效需求 (原 valid)
    "有效需求": "valid",
    "valid": "valid",
    # 可测性 (原 testability)
    "可测性": "testability",
    "testability": "testability",
    # 是否已决定 (原 resolved)
    "是否已决定": "resolved",
    "已决定": "resolved",
    "resolved": "resolved",
}

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
    has_explicit_status: bool = False  # 显式 status marker (✓/[open]/[wontfix]/...)
    is_explanatory: bool = False      # 由 spec 中的说明型 > 段推断 (无 unit, 无 status)


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
            # FR/NFR: YAML resolved = ✅ 且 最后一条 quote 状态 closed
            # (对话链只看 last_quote; 中间 open 的 reply 由后续 close 覆盖)
            if self.yaml_resolved == "✅":
                pass
            elif self.yaml_resolved == "⚠️" or self.yaml_resolved == "":
                blockers.append(f"yaml.resolved={self.yaml_resolved!r} (need ✅)")
            else:
                blockers.append(f"yaml.resolved={self.yaml_resolved!r} (unknown marker)")
            if self.last_quote is not None and self.last_quote.status == "open":
                blockers.append(
                    f"last quote status=open at L{self.last_quote.line_number} ({self.last_quote.speaker}: {self.last_quote.body[:40]})"
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


def _emit_quote_block(result: "ParseResult", block: list[tuple[int, str, "re.Match | None"]]) -> None:
    """累积多行 quote block, 提取 (depth, speaker, body, status) 并加入 result.

    block 列表中第一项必含 match (speaker 起始行), 后续项是续行 (match=None).
    status marker 只在 block 最后一行 (status_raw) 中识别, 允许用户在多行 quote
    末尾才标 [open]/✓/etc.
    """
    head_line, head_raw, head_m = block[0]
    if head_m is None:
        return
    depth = head_m.group("depth").count(">")
    # speaker 来自 name (加粗) 或 plainname (plain ASCII) 二选一
    speaker = (head_m.group("name") or head_m.group("plainname") or "").strip()
    body_parts = [head_m.group("body") or ""]
    # 续行: body 从 raw_line 去掉 depth prefix 后拼接
    for line_no, raw_line, m in block[1:]:
        # raw_line 形如 '> 修改建议: ... [open]'
        # 去掉开头的 '> ' 或 '>'
        stripped = raw_line.lstrip()
        if stripped.startswith(">"):
            stripped = stripped[1:].lstrip()
        body_parts.append(stripped)
    full_text = " ".join(p.strip() for p in body_parts if p.strip())
    # status: 只在 block 最后一行 raw_line 中找 marker
    last_line = block[-1][1]
    status_match = re.search(
        r"(?P<status>\u2713\s*(?:resolved)?|\[open\]|\[blocked-by-\d+\]|\[wontfix\]|\[superseded])\s*$",
        last_line,
    )
    status_raw = status_match.group("status").strip() if status_match else ""

    if not status_raw:
        status = "open"
        blocked_by = None
    elif status_raw.startswith("\u2713"):
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
        body=full_text,
        status=status,
        line_number=head_line,
        blocked_by=blocked_by,
        owner_close_role=owner_role,
        has_explicit_status=bool(status_raw),
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

    # 第一遍: quote block 解析 (累积多行)
    # 规则: 一个 quote block 由一行 speaker 起始 (`> **Name:** ...`) 开头,
    # 后续的 `>` 续行 (无 speaker 起始) 视为同一 quote 的一部分.
    # status marker 只在 block 最后一行匹配 (允许用户多行写完最后才标 ✓).
    in_code_block = False
    cur_block: list[tuple[int, str, re.Match]] = []  # [(line_no, raw_line, match_or_None)]
    for i, line in enumerate(lines, start=1):
        if RE_FENCE.match(line):
            in_code_block = not in_code_block
            if cur_block:
                _emit_quote_block(result, cur_block)
                cur_block = []
            continue
        if in_code_block:
            if cur_block:
                # code block 中断 quote
                _emit_quote_block(result, cur_block)
                cur_block = []
            continue
        m = RE_QUOTE_LINE.match(line)
        is_continuation = line.lstrip().startswith(">") and not m
        if m:
            # 新的 speaker 起始行
            if cur_block:
                _emit_quote_block(result, cur_block)
            cur_block = [(i, line, m)]
        elif is_continuation:
            # quote 续行
            if cur_block:
                cur_block.append((i, line, None))
            else:
                # 游离的 `>` 续行 (没有 speaker 起始), 跳过
                pass
        else:
            # 非 quote 行
            if cur_block:
                _emit_quote_block(result, cur_block)
                cur_block = []
    if cur_block:
        _emit_quote_block(result, cur_block)
        cur_block = []

    # 第二遍: 切单元 + 读表格元数据
    current_unit: Unit | None = None
    in_code_block = False
    table_buf: list[list[str]] = []
    in_table = False
    col_map: dict[str, int] = {}
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
        # 跳过代码块内的内容
        if in_code_block:
            continue
        # FR/NFR 表格元数据解析 (FR-082 起)
        # 表格形式: | col1 | col2 | col3 |  +  分隔行  +  数据行
        m_row = RE_TABLE_ROW.match(line)
        if m_row and current_unit is not None:
            cells = [c.strip() for c in m_row.group(1).split("|")]
            # 第一行: 表头候选, 第二行: 分隔 (---|---|---), 第三行: 数据
            table_buf.append(cells)
            if len(table_buf) == 2 and RE_TABLE_SEP.match(line):
                in_table = True  # 标记为表格中
                # 解析表头
                header = table_buf[0]
                col_map: dict[str, int] = {}
                for idx, col_name in enumerate(header):
                    key = COLUMN_ALIASES.get(col_name.strip())
                    if key:
                        col_map[key] = idx
            elif in_table and len(table_buf) >= 3:
                # 数据行: 按列名索引取值
                for key, idx in col_map.items():
                    if idx < len(cells):
                        val = cells[idx]
                        if key == "valid" and not current_unit.yaml_valid:
                            current_unit.yaml_valid = val
                        elif key == "testability" and not current_unit.yaml_testability:
                            current_unit.yaml_testability = val
                        elif key == "resolved" and not current_unit.yaml_resolved:
                            current_unit.yaml_resolved = val
            continue
        elif m_row is None:
            # 非表格行, 重置表格缓冲
            if table_buf:
                table_buf = []
                in_table = False
                col_map = {}

    # 第三遍: 把 quote 挂到所属 unit
    # 单元的 line 范围: [unit.heading_line, next_unit.heading_line) 或文件末尾
    # 但要求 unit 与 quote 在**同一个 ## 顶节内** —— 否则说明型 `>` (位于 ## 章节
    # 前言) 会被错挂到上一个 unit.
    quote_belongs_to_unit: set[int] = set()

    # 重建 ## 顶节起始行表 (含文件开头 0 与文件末尾哨兵)
    section_starts: list[int] = [0]
    for i2, line2 in enumerate(lines, start=1):
        if RE_TOP_HEADING.match(line2):
            section_starts.append(i2)
    section_starts.append(10**9)

    def _quote_section_end(line_no: int) -> int:
        """quote 所在 ## 顶节的下一节起始行 (即本节上界, 不含)."""
        for s in section_starts:
            if s > line_no:
                return s
        return 10**9

    if result.units:
        for u, next_u in zip(result.units, result.units[1:] + [None]):
            upper = next_u.heading_line if next_u else 10**9
            section_upper = _quote_section_end(u.heading_line)
            for q in result.quotes:
                if u.heading_line <= q.line_number < upper and q.line_number < section_upper:
                    u.last_quote = q  # 最后一个胜出
                    if q.status == "open":
                        u.open_quotes.append(q)
                    quote_belongs_to_unit.add(id(q))

    # 第三遍.5: 丢弃"说明型" quote —— 既无 unit 归属、也无显式 status 的块,
    # 例如 ## FR 章节前的 "> **格式约定**: ..." 这种说明段, 不是对话.
    explanatory_quotes = []
    kept_quotes = []
    for q in result.quotes:
        if not q.has_explicit_status and id(q) not in quote_belongs_to_unit:
            q.is_explanatory = True
            explanatory_quotes.append(q)
        else:
            kept_quotes.append(q)
    result.quotes = kept_quotes
    # 同步其它桶
    result.open_quotes = [q for q in result.open_quotes if not q.is_explanatory]
    result.resolved_quotes = [q for q in result.resolved_quotes if not q.is_explanatory]
    result.blocked_quotes = [q for q in result.blocked_quotes if not q.is_explanatory]
    result.wontfix_quotes = [q for q in result.wontfix_quotes if not q.is_explanatory]
    result.superseded_quotes = [q for q in result.superseded_quotes if not q.is_explanatory]
    # unit 的 last_quote / open_quotes 中也可能指向已丢弃的 quote, 清掉
    for u in result.units:
        if u.last_quote is not None and u.last_quote.is_explanatory:
            u.last_quote = None
        u.open_quotes = [q for q in u.open_quotes if not q.is_explanatory]
    # 重建 speaker / depth 计数 (排除 explanatory)
    result.speaker_counts = {}
    result.depth_histogram = {}
    for q in result.quotes:
        result.speaker_counts[q.speaker] = result.speaker_counts.get(q.speaker, 0) + 1
        result.depth_histogram[q.depth] = result.depth_histogram.get(q.depth, 0) + 1

    # 第四遍: 汇总 ready 判定
    # v0.5-011 修复: is_ready 必须同时满足 "无 open quote" AND "无 ready blocker"
    # 旧逻辑只看 ready_blockers, 但 open quote 也应让 gate 失败 (spec 004 设计意图)
    for u in result.units:
        ready, blockers = u.is_ready()
        if not ready:
            result.ready_blockers.append(f"{u.id}: " + "; ".join(blockers))
    result.is_ready = (len(result.open_quotes) == 0 and
                       len(result.ready_blockers) == 0)
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
