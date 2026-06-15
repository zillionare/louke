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
    is_ready: bool = False


def parse_spec(spec_path: Path) -> ParseResult:
    """解析 spec.md, 返回所有 quote + 统计"""
    text = spec_path.read_text(encoding="utf-8")
    lines = text.splitlines()

    result = ParseResult()
    in_code_block = False

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

    result.is_ready = len(result.open_quotes) == 0
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
        print(
            f"spec not ready: {len(result.open_quotes)} [open] quote(s)",
            file=sys.stderr,
        )
        for q in result.open_quotes:
            print(f"  {fmt_quote_summary(q)}", file=sys.stderr)
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
            "speaker_counts": result.speaker_counts,
            "depth_histogram": {str(k): v for k, v in sorted(result.depth_histogram.items())},
            "open_quotes": [asdict(q) for q in result.open_quotes],
            "resolved_quotes": [asdict(q) for q in result.resolved_quotes],
            "blocked_quotes": [asdict(q) for q in result.blocked_quotes],
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
        print(f"  is_ready: {result.is_ready}")
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