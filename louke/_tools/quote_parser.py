#!/usr/bin/env python3
"""
quote_parser.py — parse markdown quote-block dialogue in spec.md

This is the tool introduced by spec 004-quote-dialogue, replacing the PR inline
comment workflow. Sage / Lex / Maestro all rely on it to decide whether a
spec.md is ready.

Design goals:
- Zero LLM tokens: pure structural parsing; even C-tier models can run it
- Zero extra dependencies: Python stdlib only
- Single file, callable from a bash wrapper

Supported quote format:

    > **Sage:** question content [open]
    >> **Aaron:** answer content ✓ resolved
    >>> **Sage:** follow-up [open]
    >>>> **Aaron:** reply again ✓ resolved

The number of leading `>` indicates dialogue depth (1=Sage, 2=user, 3=Sage follow-up, ...).
Status markers: ✓ resolved / [open] / [blocked-by-N] / [wontfix] / [superseded]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path


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

# Unit heading: ### US-0010 / ### FR-0001 / ### NFR-0010 / etc. (4-digit zero-padded)
RE_UNIT_HEADING = re.compile(r"^###\s+(US|FR|NFR)-(\d{4})\b")
# Top section heading: ## Functional Requirements / ## User Stories / ## Non-functional Requirements / ## Out of Scope etc.
RE_TOP_HEADING = re.compile(r"^##\s+\S")

# FR/NFR metadata (table format, since FR-082)
# Table row: | <col1> | <col2> | <col3> |
RE_TABLE_ROW = re.compile(r"^\s*\|\s*(.+?)\s*\|\s*$")
# Header separator row: |---|---|---| or |:--|:--:|--:|
RE_TABLE_SEP = re.compile(r"^\s*\|[\s:|-]+\|\s*$")
# Column names in the header. NOTE: the Chinese keys below are intentional -
# they map Chinese spec.md column headers to English field names so the parser
# handles spec files written in EITHER Chinese or English. Do not remove them.
COLUMN_ALIASES = {
    # Valid requirement (formerly valid) / Valid
    "有效需求": "valid",
    "Valid": "valid",
    "valid": "valid",
    # Testability (formerly testability) / Testable
    "可测性": "testability",
    "Testable": "testability",
    "testability": "testability",
    # Whether decided (formerly resolved) / Decided
    "是否已决定": "resolved",
    "已决定": "resolved",
    "Decided": "resolved",
    "resolved": "resolved",
}

KNOWN_AGENT_NAMES = frozenset(
    {
        "Scout",
        "Sage",
        "Lex",
        "Archer",
        "Maestro",
        "Devon",
        "Prism",
        "Keeper",
        "Shield",
        "Judge",
        "Warden",
        "Librarian",
    }
)

RE_FENCE = re.compile(r"^\s*(```|~~~)")


@dataclass
class Quote:
    """A single quote dialogue unit."""

    depth: int
    speaker: str
    body: str
    status: str
    line_number: int
    blocked_by: int | None = None
    owner_close_role: str = "user"
    has_explicit_status: bool = False  # explicit status marker (✓/[open]/[wontfix]/...)
    is_explanatory: bool = (
        False  # inferred from an explanatory `>` block in spec (no unit, no status)
    )


@dataclass
class Unit:
    """A requirement/story unit in spec.md.

    Scope: from a ### US-XXX / ### FR-XXX / ### NFR-XXX heading up to the next ### or ##.
    """

    id: str  # e.g. "FR-010", "US-001"
    kind: str  # "US" | "FR" | "NFR"
    heading_line: int
    last_quote: Quote | None = None  # the last quote under this unit
    open_quotes: list[Quote] = field(default_factory=list)
    yaml_resolved: str = ""  # resolved value from YAML (✅/⚠️/<empty>)
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
        """Return (ready, blockers)."""
        blockers: list[str] = []
        if self.is_frnfr():
            # FR/NFR: YAML resolved = ✅ AND the last quote status is closed
            # (the dialogue chain only looks at last_quote; intermediate open replies
            # are covered by a later close)
            if self.yaml_resolved == "✅":
                pass
            elif self.yaml_resolved == "⚠️" or self.yaml_resolved == "":
                blockers.append(f"yaml.resolved={self.yaml_resolved!r} (need ✅)")
            else:
                blockers.append(
                    f"yaml.resolved={self.yaml_resolved!r} (unknown marker)"
                )
            if self.last_quote is not None and self.last_quote.status == "open":
                blockers.append(
                    f"last quote status=open at L{self.last_quote.line_number} ({self.last_quote.speaker}: {self.last_quote.body[:40]})"
                )
        else:
            # Other units (US etc.): the last quote must be closed (or there is no quote)
            if self.last_quote is None:
                pass  # no dialogue = not challenged = treated as closed
            elif self.last_quote.status != "resolved":
                blockers.append(
                    f"last quote status={self.last_quote.status!r} (need resolved or no quote)"
                )
        return (len(blockers) == 0, blockers)


@dataclass
class ParseResult:
    """spec.md parse result."""

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
    ready_blockers: list[str] = field(
        default_factory=list
    )  # detailed description of which units block ready


def _emit_quote_block(
    result: "ParseResult", block: list[tuple[int, str, "re.Match | None"]]
) -> None:
    """Accumulate a multi-line quote block, extract (depth, speaker, body, status) and append to result.

    The first item in `block` must contain a match (the speaker's starting line);
    subsequent items are continuation lines (match=None).
    The status marker is only recognized on the last line of the block (status_raw),
    allowing users to mark [open]/✓/etc. only at the end of a multi-line quote.
    """
    head_line, head_raw, head_m = block[0]
    if head_m is None:
        return
    depth = head_m.group("depth").count(">")
    # speaker comes from either name (bold) or plainname (plain ASCII), one or the other
    speaker = (head_m.group("name") or head_m.group("plainname") or "").strip()
    body_parts = [head_m.group("body") or ""]
    # Continuation: the body is concatenated from raw_line after stripping the depth prefix
    for line_no, raw_line, m in block[1:]:
        # raw_line looks like '> suggestion: ... [open]'
        # strip the leading '> ' or '>'
        stripped = raw_line.lstrip()
        if stripped.startswith(">"):
            stripped = stripped[1:].lstrip()
        body_parts.append(stripped)
    full_text = " ".join(p.strip() for p in body_parts if p.strip())
    # status: only look for a marker on the last raw_line of the block
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
    """Parse spec.md.

    Two-layer parsing:
      1) quote block parsing (original) - statistics on the dialogue
      2) unit splitting + YAML meta parsing (new) - split units by ### headings and read each unit's YAML

    Ready decision:
      - FR/NFR units: yaml.resolved == ✅ AND no open quote under the unit
      - Other units: the last quote is resolved, or the unit has no quote
    """
    text = spec_path.read_text(encoding="utf-8")
    lines = text.splitlines()

    result = ParseResult()
    in_code_block = False

    # First pass: quote block parsing (accumulate multi-line)
    # Rule: a quote block starts with a speaker line (`> **Name:** ...`);
    # subsequent `>` continuation lines (no speaker start) are treated as part of the same quote.
    # The status marker is only matched on the last line of the block (allowing users to
    # write multiple lines and only mark ✓ at the end).
    in_code_block = False
    cur_block: list[
        tuple[int, str, re.Match]
    ] = []  # [(line_no, raw_line, match_or_None)]
    for i, line in enumerate(lines, start=1):
        if RE_FENCE.match(line):
            in_code_block = not in_code_block
            if cur_block:
                _emit_quote_block(result, cur_block)
                cur_block = []
            continue
        if in_code_block:
            if cur_block:
                # code block interrupts the quote
                _emit_quote_block(result, cur_block)
                cur_block = []
            continue
        m = RE_QUOTE_LINE.match(line)
        is_continuation = line.lstrip().startswith(">") and not m
        if m:
            # new speaker starting line
            if cur_block:
                _emit_quote_block(result, cur_block)
            cur_block = [(i, line, m)]
        elif is_continuation:
            # quote continuation line
            if cur_block:
                cur_block.append((i, line, None))
            else:
                # orphan `>` continuation (no speaker start): skip
                pass
        else:
            # non-quote line
            if cur_block:
                _emit_quote_block(result, cur_block)
                cur_block = []
    if cur_block:
        _emit_quote_block(result, cur_block)
        cur_block = []

    # Second pass: split units + read table metadata
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
            # the next ## section means the current unit ends
            current_unit = None
            continue
        if RE_FENCE.match(line):
            in_code_block = not in_code_block
            continue
        # Skip content inside code blocks
        if in_code_block:
            continue
        # FR/NFR table metadata parsing (since FR-082)
        # Table form: | col1 | col2 | col3 |  +  separator row  +  data rows
        m_row = RE_TABLE_ROW.match(line)
        if m_row and current_unit is not None:
            cells = [c.strip() for c in m_row.group(1).split("|")]
            # First row: header candidate, second row: separator (---|---|---), third row: data
            table_buf.append(cells)
            if len(table_buf) == 2 and RE_TABLE_SEP.match(line):
                in_table = True  # mark as inside a table
                # parse the header
                header = table_buf[0]
                col_map = {}
                for idx, col_name in enumerate(header):
                    key = COLUMN_ALIASES.get(col_name.strip())
                    if key:
                        col_map[key] = idx
            elif in_table and len(table_buf) >= 3:
                # data row: look up values by column name
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
            # non-table row: reset the table buffer
            if table_buf:
                table_buf = []
                in_table = False
                col_map = {}

    # Third pass: attach quotes to their owning unit
    # Unit line range: [unit.heading_line, next_unit.heading_line) or end of file
    # But the unit and the quote must be in the **same ## top section** - otherwise an
    # explanatory `>` (located in a ## section preamble) would be mis-attached to the previous unit.
    quote_belongs_to_unit: set[int] = set()

    # Rebuild the list of ## top-section start lines (including 0 for file start and a sentinel at the end)
    section_starts: list[int] = [0]
    for i2, line2 in enumerate(lines, start=1):
        if RE_TOP_HEADING.match(line2):
            section_starts.append(i2)
    section_starts.append(10**9)

    def _quote_section_end(line_no: int) -> int:
        """Start line of the next ## top section after the one containing the quote (i.e. this section's upper bound, exclusive)."""
        for s in section_starts:
            if s > line_no:
                return s
        return 10**9

    if result.units:
        for u, next_u in zip(result.units, result.units[1:] + [None]):
            upper = next_u.heading_line if next_u else 10**9
            section_upper = _quote_section_end(u.heading_line)
            for q in result.quotes:
                if (
                    u.heading_line <= q.line_number < upper
                    and q.line_number < section_upper
                ):
                    u.last_quote = q  # the last one wins
                    if q.status == "open":
                        u.open_quotes.append(q)
                    quote_belongs_to_unit.add(id(q))

    # Third pass .5: drop "explanatory" quotes - blocks with no unit ownership and no explicit status,
    # e.g. the "> **format convention**: ..." preamble before the ## FR section; these are not dialogue.
    explanatory_quotes = []
    kept_quotes = []
    for q in result.quotes:
        if not q.has_explicit_status and id(q) not in quote_belongs_to_unit:
            q.is_explanatory = True
            explanatory_quotes.append(q)
        else:
            kept_quotes.append(q)
    result.quotes = kept_quotes
    # sync the other buckets
    result.open_quotes = [q for q in result.open_quotes if not q.is_explanatory]
    result.resolved_quotes = [q for q in result.resolved_quotes if not q.is_explanatory]
    result.blocked_quotes = [q for q in result.blocked_quotes if not q.is_explanatory]
    result.wontfix_quotes = [q for q in result.wontfix_quotes if not q.is_explanatory]
    result.superseded_quotes = [
        q for q in result.superseded_quotes if not q.is_explanatory
    ]
    # a unit's last_quote / open_quotes may also point at a dropped quote; clean them up
    for u in result.units:
        if u.last_quote is not None and u.last_quote.is_explanatory:
            u.last_quote = None
        u.open_quotes = [q for q in u.open_quotes if not q.is_explanatory]
    # rebuild speaker / depth counts (excluding explanatory)
    result.speaker_counts = {}
    result.depth_histogram = {}
    for q in result.quotes:
        result.speaker_counts[q.speaker] = result.speaker_counts.get(q.speaker, 0) + 1
        result.depth_histogram[q.depth] = result.depth_histogram.get(q.depth, 0) + 1

    # Fourth pass: aggregate the ready decision
    # v0.5-011 fix: is_ready must satisfy BOTH "no open quote" AND "no ready blocker"
    # The old logic only looked at ready_blockers, but open quotes should also fail the gate
    # (the design intent of spec 004)
    for u in result.units:
        ready, blockers = u.is_ready()
        if not ready:
            result.ready_blockers.append(f"{u.id}: " + "; ".join(blockers))
    result.is_ready = len(result.open_quotes) == 0 and len(result.ready_blockers) == 0
    return result


def fmt_quote_summary(q: Quote) -> str:
    """Concise summary of a single quote."""
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
            f"spec not ready: {len(result.ready_blockers)} unit(s) blocking",
            file=sys.stderr,
        )
        for b in result.ready_blockers:
            print(f"  {b}", file=sys.stderr)
        return 1

    if args.check_violations:
        violations = []
        for q in (
            result.resolved_quotes
            + result.blocked_quotes
            + result.wontfix_quotes
            + result.superseded_quotes
        ):
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
            "depth_histogram": {
                str(k): v for k, v in sorted(result.depth_histogram.items())
            },
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
