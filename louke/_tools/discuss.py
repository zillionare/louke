"""louke/_tools/discuss.py — Inline Discussion protocol parser (FR-0020).

The inline-discussion protocol (v0.7-003) replaces the v0.6-016 quote-dialogue protocol.

Core API:
- Thread (dataclass): a single discussion thread, with 5-tuple locating fields
- DiscussParser: parses spec.md, provides the is_ready() gate, and a 4-level fallback lookup

Replaces the core functionality of louke/_tools/quote_parser.py. quote_parser.py is
kept as a backward-compatible thin wrapper.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path


# Status: only 3 states (QoderWork P0-NEW: reopen counts as blocking)
STATUS_OPEN = "open"
STATUS_RESOLVED = "resolved"
STATUS_REOPEN = "reopen"

# Status marker matching (only valid on root-comment lines)
# ✓ (U+2713) is a backward-compatible marker, mapped to resolved (older specs use ✓)
RE_STATUS_MARKER = re.compile(
    r"\s*(?:\[(?P<bracket_status>open|resolved|reopen)\]"
    r"|\u2713\s*(?:resolved)?)\s*$",
    re.IGNORECASE,
)

# Quote line matching:
# one or more `>` at the start, followed by **Speaker** or **@Speaker** (with optional [STATUS]) : content
# @mention syntax (QoderWork P1-NEW-3 retained)
# Note: in a raw string `\*\*` is actually `\\*\\*` in Python (2 chars: `\*` + `*`, i.e. literal \* + Kleene 0+ *),
#       to express the literal `**` you must use `[*][*]`, or `\*\*` outside a raw string
RE_QUOTE_LINE = re.compile(
    r"^(?P<depth>\s*(?:>\s*)+)"
    r"(?P<speaker>[*][*]@?[A-Za-z][^*]*?[*][*])"
    r"(?:\s*(?:\[(?P<status>open|resolved|reopen)\]|(?P<check>\u2713\s*(?:resolved)?)))?"
    r"\s*:\s*"
    r"(?P<body>.*?)\s*$",
    re.IGNORECASE,
)

# Unit heading (FR-0020 AC-7 retained): ### US-0010 / ### FR-0001 / ### NFR-0010
RE_UNIT_HEADING = re.compile(r"^###\s+(US|FR|NFR)-(\d{4})\b")

# FR/NFR metadata. NOTE: the Chinese keys below are intentional - they map
# Chinese spec.md column headers to English field names so the parser handles
# spec files written in EITHER Chinese or English. Do not remove the Chinese keys.
COLUMN_ALIASES = {
    "有效需求": "valid",
    "Valid": "valid",
    "valid": "valid",
    "可测性": "testability",
    "Testable": "testability",
    "testability": "testability",
    "是否已决定": "resolved",
    "已决定": "resolved",
    "Decided": "resolved",
    "resolved": "resolved",
}

RE_TABLE_ROW = re.compile(r"^\s*\|\s*(.+?)\s*\|\s*$")
RE_TABLE_SEP = re.compile(r"^\s*\|[\s:|-]+\|\s*$")
RE_TOP_HEADING = re.compile(r"^##\s+\S")
RE_FENCE = re.compile(r"^\s*(```|~~~)")


def normalize_text(s: str) -> str:
    """FR-0050 normalization rules: strip leading/trailing whitespace + collapse runs of whitespace to a single space + Unicode NFC.

    Does not change case and does not strip markdown formatting.
    """
    import unicodedata

    s = unicodedata.normalize("NFC", s)
    s = s.strip()
    s = re.sub(r"\s+", " ", s)
    return s


def levenshtein(a: str, b: str) -> int:
    """Classic edit distance (Levenshtein distance)."""
    if len(a) < len(b):
        a, b = b, a
    if not a:
        return len(b)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a):
        curr = [i + 1]
        for j, cb in enumerate(b):
            curr.append(
                min(
                    prev[j + 1] + 1,  # deletion
                    curr[j] + 1,  # insertion
                    prev[j] + (ca != cb),  # substitution
                )
            )
        prev = curr
    return prev[len(b)]


@dataclass
class Thread:
    """A single discussion thread (FR-0020 dataclass).

    5-tuple locating fields (QoderWork P0-2):
    - total_lines: total line count of the file at creation time (used for line-drift correction)
    - anchor_line: line number of the content being commented on (quick-jump hint)
    - anchor_text: the commented content (normalized)
    - root_line: line number of the root comment's `>` line
    - root_text: the root comment's speaker + body (normalized)
    """

    thread_id: str  # "T-NNN" auto-increment sequence
    initiator: str  # root comment speaker (lowercased for normalized comparison)
    status: str  # STATUS_OPEN / RESOLVED / REOPEN
    last_speaker: str  # last person to speak in the thread
    reply_count: int
    snippet: str  # first 80 chars of the root comment body

    # 5-tuple locating fields
    total_lines: int  # total line count of the file at creation time
    anchor_line: int  # line number of the commented content
    anchor_text: str  # normalized text
    root_line: int  # root comment line number
    root_text: str  # root comment speaker + body (normalized)

    # @mention parsing
    mentioned_agents: list[str] = field(default_factory=list)


@dataclass
class ParseResult:
    """spec.md parse result.

    is_ready decision (QoderWork P0-NEW): all thread statuses == "resolved".
    """

    threads: list[Thread] = field(default_factory=list)
    units: list[dict] = field(default_factory=list)  # [{id, kind, yaml_resolved, ...}]
    is_ready: bool = False
    ready_blockers: list[str] = field(default_factory=list)


class DiscussParser:
    """inline-discussion protocol parser (FR-0020)."""

    def __init__(self) -> None:
        self._thread_counter = 0
        self._threads: list[Thread] = []
        self._units: list[dict] = []

    def parse_file(self, path: Path) -> ParseResult:
        """Parse spec.md and return a ParseResult."""
        text = path.read_text(encoding="utf-8")
        lines = text.splitlines()
        return self._parse(text, lines)

    def _parse(self, text: str, lines: list[str]) -> ParseResult:
        # Two-pass parsing:
        # Pass 1: scan quote lines, collect threads
        self._threads = []
        in_code_block = False
        for line_no, raw_line in enumerate(lines, start=1):
            if RE_FENCE.match(raw_line):
                in_code_block = not in_code_block
                continue
            if in_code_block:
                continue
            m = RE_QUOTE_LINE.match(raw_line)
            if not m:
                continue
            # Parse the quote
            depth_prefix = m.group("depth")
            depth = depth_prefix.count(">")
            speaker_raw = m.group("speaker").strip("*").lstrip("@")
            # Extract the @mention list (speaker tag + body, FR-0020 AC-8)
            mentioned = re.findall(
                r"@([A-Za-z][A-Za-z0-9_\-]*)",
                m.group("speaker") + " " + m.group("body"),
            )
            body = m.group("body").strip()
            # ✓ (U+2713) compatibility: older specs use ✓ to mark resolved
            if m.group("status"):
                status_raw = m.group("status").lower()
            elif m.group("check") is not None or m.group("check") == "":
                status_raw = STATUS_RESOLVED
            else:
                status_raw = ""
            # Only recognize status on root comments (depth=1)
            if depth == 1:
                self._thread_counter += 1
                status = status_raw or STATUS_OPEN
                if status not in (STATUS_OPEN, STATUS_RESOLVED, STATUS_REOPEN):
                    status = STATUS_OPEN
                # anchor_line: the nearest non-empty, non-`>` line **above** the root comment
                anchor_line = self._find_anchor_line(lines, line_no)
                anchor_text = self._get_line(lines, anchor_line) if anchor_line else ""
                root_text = f"{speaker_raw}: {body}"
                thread = Thread(
                    thread_id=f"T-{self._thread_counter:03d}",
                    initiator=speaker_raw.lower(),
                    status=status,
                    last_speaker=speaker_raw.lower(),
                    reply_count=0,
                    snippet=body[:80],
                    total_lines=len(lines),
                    anchor_line=anchor_line or 0,
                    anchor_text=normalize_text(anchor_text),
                    root_line=line_no,
                    root_text=normalize_text(root_text),
                    mentioned_agents=[m.lower() for m in mentioned],
                )
                self._threads.append(thread)
            else:
                # Nested reply: update last_speaker
                if self._threads:
                    self._threads[-1].last_speaker = speaker_raw.lower()
                    if mentioned:
                        for m in mentioned:
                            if m.lower() not in self._threads[-1].mentioned_agents:
                                self._threads[-1].mentioned_agents.append(m.lower())
                self._threads[-1].reply_count += 1

        # Pass 2: scan units + YAML
        self._units = []
        current_unit: dict | None = None
        table_buf: list[list[str]] = []
        col_map: dict[str, int] = {}
        in_table = False
        in_code_block = False
        for i, line in enumerate(lines, start=1):
            if RE_FENCE.match(line):
                in_code_block = not in_code_block
                continue
            if in_code_block:
                continue
            m_head = RE_UNIT_HEADING.match(line)
            if m_head:
                kind = m_head.group(1)
                num = m_head.group(2)
                current_unit = {
                    "id": f"{kind}-{num}",
                    "kind": kind,
                    "heading_line": i,
                    "yaml_resolved": "",
                    "yaml_testability": "",
                    "yaml_valid": "",
                    "thread_ids": [],  # linked thread_id
                }
                self._units.append(current_unit)
                continue
            if current_unit is None:
                continue
            if RE_TOP_HEADING.match(line):
                current_unit = None
                continue
            m_row = RE_TABLE_ROW.match(line)
            if m_row:
                cells = [c.strip() for c in m_row.group(1).split("|")]
                table_buf.append(cells)
                if len(table_buf) == 2 and RE_TABLE_SEP.match(line):
                    in_table = True
                    header = table_buf[0]
                    col_map = {}
                    for idx, col_name in enumerate(header):
                        key = COLUMN_ALIASES.get(col_name.strip())
                        if key:
                            col_map[key] = idx
                elif in_table and len(table_buf) >= 3:
                    for key, idx in col_map.items():
                        if idx < len(cells):
                            val = cells[idx]
                            if key == "valid" and not current_unit["yaml_valid"]:
                                current_unit["yaml_valid"] = val
                            elif (
                                key == "testability"
                                and not current_unit["yaml_testability"]
                            ):
                                current_unit["yaml_testability"] = val
                            elif (
                                key == "resolved" and not current_unit["yaml_resolved"]
                            ):
                                current_unit["yaml_resolved"] = val
                continue
            elif m_row is None:
                if table_buf:
                    table_buf = []
                    in_table = False
                    col_map = {}

        # Link threads to units (by root_line range)
        for u in self._units:
            upper = self._next_unit_heading(u["heading_line"])
            for t in self._threads:
                if u["heading_line"] <= t.root_line < upper:
                    u["thread_ids"].append(t.thread_id)

        # is_ready decision (QoderWork P0-NEW + v0.13 fix):
        #   - All FR/NFR-scoped threads must be status=resolved
        #   - US-scoped threads: same
        #   - Plus any thread (FR/NFR/US OR unit-less, e.g. anchored to a chapter
        #     section like "### 5.2 Chat" in architecture/interfaces/test-plan)
        #     that is open OR reopen must block. reopen ≡ open (a thread incorrectly
        #     closed before; still needs work).
        blockers = []
        for u in self._units:
            if u["kind"] in ("FR", "NFR"):
                if u["yaml_resolved"] != "✅":
                    blockers.append(
                        f"{u['id']}: yaml.resolved={u['yaml_resolved']!r} (need ✅)"
                    )
                for tid in u["thread_ids"]:
                    t = next((x for x in self._threads if x.thread_id == tid), None)
                    if t and t.status != STATUS_RESOLVED:
                        blockers.append(
                            f"{u['id']}: thread {tid} status={t.status!r} (need resolved)"
                        )
            else:
                # US and others: no thread = ok
                for tid in u["thread_ids"]:
                    t = next((x for x in self._threads if x.thread_id == tid), None)
                    if t and t.status != STATUS_RESOLVED:
                        blockers.append(f"{u['id']}: thread {tid} status={t.status!r}")

        # Catch-all: any thread NOT yet linked to a unit (e.g. anchored to
        # architecture chapter headings like "### 5.2 Chat") but still open/reopen
        # must also block readiness. Without this, chapter-anchored threads are
        # silently ignored by the gate.
        linked_thread_ids = {
            tid for u in self._units for tid in u["thread_ids"]
        }
        for t in self._threads:
            if t.status == STATUS_RESOLVED:
                continue
            if t.thread_id in linked_thread_ids:
                # Already reported above with FR/NFR/US context
                continue
            anchors = t.anchor_line or t.root_line
            blockers.append(
                f"unanchored thread {t.thread_id} status={t.status!r} at line {anchors} (need resolved)"
            )

        result = ParseResult(
            threads=list(self._threads),
            units=list(self._units),
            is_ready=len(blockers) == 0,
            ready_blockers=blockers,
        )
        return result

    def _find_anchor_line(self, lines: list[str], quote_line: int) -> int | None:
        """Nearest non-empty, non-`>` line **above** the root comment (single-line anchoring, FR-0050)."""
        for i in range(quote_line - 1, 0, -1):
            stripped = lines[i - 1].strip()
            if not stripped:
                continue
            if stripped.startswith(">"):
                continue
            return i
        return None

    def _get_line(self, lines: list[str], line_no: int) -> str:
        if 1 <= line_no <= len(lines):
            return lines[line_no - 1]
        return ""

    def _next_unit_heading(self, current_line: int) -> int:
        """Line number of the next unit heading (in ### US/FR/NFR-XXXX order)."""
        candidates = [
            u["heading_line"] for u in self._units if u["heading_line"] > current_line
        ]
        return min(candidates) if candidates else 10**9

    # ===== 4-level fallback lookup (QoderWork P0-2, FR-0050) =====

    def find_thread(
        self,
        file_path: Path,
        thread_id: str,
        anchor_line: int | None = None,
        anchor_text: str | None = None,
        root_line: int | None = None,
        root_text: str | None = None,
        total_lines: int | None = None,
    ) -> Thread | None:
        """4-level fallback thread lookup.

        Important: parse_file resets the counter each time, so thread_id changes between parses.
        Therefore you cannot index by thread_id directly; you must match content via the
        5-tuple (anchor_line + root_text).

        Priority:
          1. Level 0 exact hit (adjust anchor_line + verify content)
          2. Level 1 Levenshtein window (anchor_line ± max(|delta|+5, 10))
          3. Level 2 full-text root comments (match by root_text + verify speaker)
          4. Level 3 not found (return None)
        """
        # thread_id is kept for agent debugging (in error messages), but matching does not use it
        text = file_path.read_text(encoding="utf-8")
        lines = text.splitlines()
        current_total = len(lines)

        # Find all candidates (needed by Level 2/3)
        current_result = self.parse_file(file_path)
        candidates = current_result.threads

        # If the agent did not pass any locating fields, fall back to Level 2 full-text match (by root_text)
        if anchor_line is None:
            if root_text:
                for t2 in candidates:
                    if t2.root_text == root_text:
                        return t2
                    d = levenshtein(t2.root_text, root_text)
                    if d <= max(5, len(root_text) * 0.2):
                        return t2
            return None

        # Step 0: compute line drift (FR-0050)
        # delta = current_total - stored_total_lines
        # adjusted_anchor = anchor_line + delta
        if total_lines is not None:
            delta = current_total - total_lines
            adjusted_anchor = max(1, anchor_line + delta)
        else:
            delta = 0
            adjusted_anchor = anchor_line

        # Level 0: exact hit - adjust anchor_line + verify content
        # search window: adjusted_anchor ± max(|delta|+5, 5) (tolerate small drift + delta estimation error)
        if anchor_text:
            search_radius = max(abs(delta) + 5, 5)
            for try_anchor in range(
                max(1, adjusted_anchor - search_radius),
                min(current_total, adjusted_anchor + search_radius) + 1,
            ):
                actual = normalize_text(lines[try_anchor - 1])
                if actual == anchor_text:
                    # Found the anchor line. Scan below it for a blockquote root comment
                    for j in range(try_anchor, min(current_total, try_anchor + 10) + 1):
                        m = RE_QUOTE_LINE.match(lines[j - 1])
                        if m and m.group("depth").count(">") == 1:
                            # Found the root comment. Verify root_text matches
                            actual_root = normalize_text(
                                f"{m.group('speaker').strip('*').lstrip('@')}: {m.group('body')}"
                            )
                            if not root_text or actual_root == root_text:
                                # Build a thread to return
                                return Thread(
                                    thread_id="?",
                                    initiator=m.group("speaker")
                                    .strip("*")
                                    .lstrip("@")
                                    .lower(),
                                    status=(m.group("status") or STATUS_OPEN).lower(),
                                    last_speaker=m.group("speaker")
                                    .strip("*")
                                    .lstrip("@")
                                    .lower(),
                                    reply_count=0,
                                    snippet=m.group("body")[:80],
                                    total_lines=current_total,
                                    anchor_line=try_anchor,
                                    anchor_text=anchor_text,
                                    root_line=j,
                                    root_text=actual_root,
                                )
                            break

        # Level 1: Levenshtein window (find approximate line by anchor_text)
        if anchor_text:
            best_anchor_line = None
            best_anchor_dist = 10**9
            for i in range(1, current_total + 1):
                actual = normalize_text(lines[i - 1])
                d = levenshtein(actual, anchor_text)
                if d < best_anchor_dist:
                    best_anchor_dist = d
                    best_anchor_line = i
            threshold = max(5, len(anchor_text) * 0.2)
            if best_anchor_dist <= threshold and best_anchor_line:
                for j in range(
                    best_anchor_line, min(current_total, best_anchor_line + 10) + 1
                ):
                    m = RE_QUOTE_LINE.match(lines[j - 1])
                    if m and m.group("depth").count(">") == 1:
                        actual_root = normalize_text(
                            f"{m.group('speaker').strip('*').lstrip('@')}: {m.group('body')}"
                        )
                        if not root_text or actual_root == root_text:
                            return Thread(
                                thread_id="?",
                                initiator=m.group("speaker")
                                .strip("*")
                                .lstrip("@")
                                .lower(),
                                status=(m.group("status") or STATUS_OPEN).lower(),
                                last_speaker=m.group("speaker")
                                .strip("*")
                                .lstrip("@")
                                .lower(),
                                reply_count=0,
                                snippet=m.group("body")[:80],
                                total_lines=current_total,
                                anchor_line=best_anchor_line,
                                anchor_text=normalize_text(lines[best_anchor_line - 1]),
                                root_line=j,
                                root_text=actual_root,
                            )
                        break

        # Level 2: full-text root comments (match by root_text + speaker)
        if root_text:
            for t2 in candidates:
                if t2.root_text == root_text:
                    return t2
                d = levenshtein(t2.root_text, root_text)
                threshold = max(5, len(root_text) * 0.2)
                if d <= threshold:
                    return t2

        return None  # Level 3

    # ===== Write operations (QoderWork P0-4 write semantics) =====

    def add_thread(
        self,
        file_path: Path,
        anchor_line: int,
        initiator: str,
        body: str,
        status: str = STATUS_OPEN,
    ) -> Thread:
        """Insert a new thread after the first blank line following anchor_line.

        Write op: parse -> insert lines -> atomic write (tmp + rename)
        """
        text = file_path.read_text(encoding="utf-8")
        lines = text.splitlines()
        # Find the first blank line after anchor_line
        insert_at = self._find_insert_line(lines, anchor_line)
        # Build the root comment
        status_marker = f" [{status.upper()}]" if status != STATUS_OPEN else ""
        new_line = f"> **{initiator}**{status_marker}: {body}"
        # Write op: insert + add trailing blank line (CommonMark requires blank lines between blockquotes)
        new_lines = lines[:insert_at] + ["", new_line, ""] + lines[insert_at:]
        new_text = "\n".join(new_lines) + ("\n" if text.endswith("\n") else "")
        self._atomic_write(file_path, new_text)
        # Re-parse
        new_thread = Thread(
            thread_id=f"T-{len(self.parse_file(file_path).threads) + 1:03d}",
            initiator=initiator.lower(),
            status=status,
            last_speaker=initiator.lower(),
            reply_count=0,
            snippet=body[:80],
            total_lines=len(new_lines),
            anchor_line=anchor_line,
            anchor_text=normalize_text(self._get_line(lines, anchor_line))
            if 1 <= anchor_line <= len(lines)
            else "",
            root_line=insert_at
            + 2,  # +2 because a blank line + the line were prepended
            root_text=normalize_text(f"{initiator}: {body}"),
        )
        return new_thread

    def add_reply(
        self,
        file_path: Path,
        thread_id: str,
        body: str,
        speaker: str,
        **loc,
    ) -> None:
        """Append a reply to the end of a thread (loc holds the 5-tuple locating fields)."""
        thread = self.find_thread(file_path, thread_id, **loc)
        if thread is None:
            raise ValueError(f"thread {thread_id} not found")
        text = file_path.read_text(encoding="utf-8")
        lines = text.splitlines()
        # Find the line number of the thread's last nested reply
        # Simple approach: find the last line between thread.root_line and the next root
        next_root = self._next_root_line(lines, thread.root_line)
        if next_root is None:
            next_root = len(lines) + 1
        # Find the last line with the greatest depth in the thread
        last_line = self._find_last_nested_line(lines, thread.root_line, next_root)
        if last_line is None:
            last_line = thread.root_line
        # Insert `> {speaker}: {body}` after last_line
        depth = self._line_depth(lines, last_line)
        new_depth_marker = ">" * (depth + 1)
        new_line = f"{new_depth_marker} **{speaker}**: {body}"
        insert_at = last_line + 1
        # Add a blank line (to separate from the next `>` block)
        new_lines = lines[:insert_at] + ["", new_line, ""] + lines[insert_at:]
        new_text = "\n".join(new_lines) + ("\n" if text.endswith("\n") else "")
        self._atomic_write(file_path, new_text)

    def set_status(
        self,
        file_path: Path,
        thread_id: str,
        new_status: str,
        operator_speaker: str,
        **loc,
    ) -> None:
        """Change a thread's status. RESOLVED requires the initiator; REOPEN can be done by anyone.

        The parser verifies operator_speaker == thread.initiator before allowing RESOLVED.
        """
        thread = self.find_thread(file_path, thread_id, **loc)
        if thread is None:
            raise ValueError(f"thread {thread_id} not found")
        if new_status == STATUS_RESOLVED:
            if thread.initiator != operator_speaker.lower():
                raise PermissionError(
                    f"only initiator ({thread.initiator}) can mark RESOLVED, "
                    f"got operator {operator_speaker}"
                )
        # Modify the status of the root comment line
        text = file_path.read_text(encoding="utf-8")
        lines = text.splitlines()
        root_idx = thread.root_line - 1
        if 0 <= root_idx < len(lines):
            line = lines[root_idx]
            # Remove the old status marker
            line = re.sub(
                r"\s*\[(?:open|resolved|reopen)\]\s*", "", line, flags=re.IGNORECASE
            )
            # Add the new marker (open does not get one)
            if new_status != STATUS_OPEN:
                # Insert status after **Speaker:**
                line = re.sub(
                    r"(\*\*[^*]+?\*\*)\s*:",
                    rf"\1 [{new_status.upper()}]:",
                    line,
                )
            lines[root_idx] = line
        new_text = "\n".join(lines) + ("\n" if text.endswith("\n") else "")
        self._atomic_write(file_path, new_text)

    def edit_comment(
        self,
        file_path: Path,
        thread_id: str,
        depth: int,
        speaker: str,
        new_body: str,
        **loc,
    ) -> None:
        """Edit one of your own comments (original author only)."""
        thread = self.find_thread(file_path, thread_id, **loc)
        if thread is None:
            raise ValueError(f"thread {thread_id} not found")
        text = file_path.read_text(encoding="utf-8")
        lines = text.splitlines()
        # Find the line matching depth + speaker
        target_line_no = None
        for i, line in enumerate(lines, start=1):
            if i < thread.root_line:
                continue
            m = RE_QUOTE_LINE.match(line)
            if not m:
                continue
            line_depth = m.group("depth").count(">")
            line_speaker = m.group("speaker").strip("*").lstrip("@")
            if line_depth == depth and line_speaker.lower() == speaker.lower():
                target_line_no = i
                break
        if target_line_no is None:
            raise ValueError(f"no comment found at depth {depth} by {speaker}")
        # Replace the content (keep the prefix `> ... `)
        old_line = lines[target_line_no - 1]
        m = RE_QUOTE_LINE.match(old_line)
        if not m:
            raise ValueError("internal: line no longer matches")
        depth_prefix = m.group("depth")
        speaker_tag = m.group("speaker")
        status_marker = m.group("status") or ""
        if status_marker:
            status_str = f" [{status_marker.upper()}]"
        else:
            status_str = ""
        # Handle multi-line new_body: continuation lines use the same depth_prefix as the speaker line (CommonMark same paragraph)
        body_lines = new_body.split("\n")
        first = f"{depth_prefix} {speaker_tag}{status_str}: {body_lines[0]}"
        new_lines = [first]
        for bl in body_lines[1:]:
            new_lines.append(f"{depth_prefix}{bl}")
        lines[target_line_no - 1 : target_line_no] = new_lines
        new_text = "\n".join(lines) + ("\n" if text.endswith("\n") else "")
        self._atomic_write(file_path, new_text)

    def is_ready(self, file_path: Path) -> tuple[bool, list[str]]:
        """Return (ready, blockers). Convenience API, equivalent to accessing result.is_ready after parse_file(file_path).

        Usage: cmd_record_lock internally calls self.is_ready(spec_path).
        Compatible with quote_parser: returns a (bool, list[str]) tuple.
        """
        result = self.parse_file(file_path)
        return (result.is_ready, result.ready_blockers)

    # ===== Helper methods =====

    def _find_insert_line(self, lines: list[str], anchor_line: int) -> int:
        """Find the first blank line after anchor_line (QoderWork P0-4 write op)."""
        for i in range(anchor_line, len(lines)):
            if not lines[i].strip():
                return i
        return len(lines)  # fallback: end of file

    def _next_root_line(self, lines: list[str], after_line: int) -> int | None:
        """Line number of the next root comment (depth=1 `>`) after after_line."""
        for i in range(after_line, len(lines)):
            m = RE_QUOTE_LINE.match(lines[i])
            if m and m.group("depth").count(">") == 1:
                return i + 1
        return None

    def _find_last_nested_line(
        self, lines: list[str], start: int, end: int
    ) -> int | None:
        """Line number of the last quote line within the start..end range (inclusive)."""
        last = None
        for i in range(start - 1, end):
            if i < len(lines) and RE_QUOTE_LINE.match(lines[i]):
                last = i + 1
        return last

    def _line_depth(self, lines: list[str], line_no: int) -> int:
        if 1 <= line_no <= len(lines):
            m = RE_QUOTE_LINE.match(lines[line_no - 1])
            if m:
                return m.group("depth").count(">")
        return 1

    def _atomic_write(self, file_path: Path, content: str) -> None:
        """Atomic write: tmp + rename. Also uses flock to prevent concurrent access."""
        import fcntl
        import tempfile

        lock_path = file_path.with_suffix(file_path.suffix + ".lock")
        with open(lock_path, "w", encoding="utf-8") as lock_fd:
            fcntl.flock(lock_fd.fileno(), fcntl.LOCK_EX)
            try:
                fd, tmp_path = tempfile.mkstemp(
                    prefix=file_path.name + ".",
                    dir=str(file_path.parent),
                )
                with open(fd, "w", encoding="utf-8") as f:
                    f.write(content)
                Path(tmp_path).replace(file_path)
            finally:
                fcntl.flock(lock_fd.fileno(), fcntl.LOCK_UN)


# ===== Module-level helper functions (shared by Layer 1) =====


def format_ready(spec_path: Path, fmt: str = "text") -> tuple[int, str]:
    """Format the quote-check output. Returns (exit_code, output_text).

    exit_code: 0 if ready, 1 if not ready.
    Shared by sage.py / lex.py cmd_quote_check, replacing the subprocess call to quote_parser.
    """
    parser = DiscussParser()
    result = parser.parse_file(spec_path)
    exit_code = 0 if result.is_ready else 1

    open_count = sum(1 for t in result.threads if t.status == STATUS_OPEN)
    resolved_count = sum(1 for t in result.threads if t.status == STATUS_RESOLVED)
    reopen_count = sum(1 for t in result.threads if t.status == STATUS_REOPEN)

    if fmt == "json":
        data = {
            "total_threads": len(result.threads),
            "open_count": open_count,
            "resolved_count": resolved_count,
            "reopen_count": reopen_count,
            "is_ready": result.is_ready,
            "ready_blockers": result.ready_blockers,
            "threads": [
                {
                    "thread_id": t.thread_id,
                    "initiator": t.initiator,
                    "status": t.status,
                    "last_speaker": t.last_speaker,
                    "reply_count": t.reply_count,
                    "snippet": t.snippet,
                    "total_lines": t.total_lines,
                    "anchor_line": t.anchor_line,
                    "root_line": t.root_line,
                    "mentioned_agents": t.mentioned_agents,
                }
                for t in result.threads
            ],
            "units": [
                {
                    "id": u["id"],
                    "kind": u["kind"],
                    "yaml_resolved": u["yaml_resolved"],
                    "yaml_valid": u["yaml_valid"],
                    "yaml_testability": u["yaml_testability"],
                    "thread_ids": u["thread_ids"],
                }
                for u in result.units
            ],
        }
        return (exit_code, json.dumps(data, ensure_ascii=False, indent=2))

    # text format
    lines = [f"spec: {spec_path}"]
    lines.append(f"  total threads: {len(result.threads)}")
    lines.append(f"  open: {open_count}")
    lines.append(f"  resolved: {resolved_count}")
    if reopen_count:
        lines.append(f"  reopen: {reopen_count}")
    lines.append(f"  units: {len(result.units)}")
    lines.append(f"  is_ready: {result.is_ready}")
    if result.ready_blockers:
        lines.append("")
        lines.append("[ready] blockers:")
        for b in result.ready_blockers:
            lines.append(f"  {b}")
    if open_count or reopen_count:
        lines.append("")
        lines.append("[open/reopen] threads:")
        for t in result.threads:
            if t.status in (STATUS_OPEN, STATUS_REOPEN):
                lines.append(
                    f"  [{t.status.upper():8}] {t.thread_id} {t.initiator}: {t.snippet}"
                )
    if resolved_count:
        lines.append(f"\n[resolved] threads: {resolved_count} total")
    return (exit_code, "\n".join(lines))


def check_violations(spec_path: Path) -> tuple[int, str]:
    """Detect inline-discussion protocol violations.

    In the new protocol (v0.7-003), RESOLVED can only be set by the initiator (set_status enforces this on write).
    Therefore this function mainly detects: nested replies (depth > 1) that contain a status marker (which the
    parser would ignore, indicating a writer mistake).

    Returns (exit_code, output_text). exit_code: 0 = no violations, 1 = violations found.
    """
    text = spec_path.read_text(encoding="utf-8")
    lines = text.splitlines()
    violations: list[str] = []
    in_code_block = False
    for line_no, raw in enumerate(lines, start=1):
        if RE_FENCE.match(raw):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue
        m = RE_QUOTE_LINE.match(raw)
        if not m:
            continue
        depth = m.group("depth").count(">")
        if depth > 1 and (
            m.group("status") or m.group("check") is not None or m.group("check") == ""
        ):
            speaker = m.group("speaker").strip("*").lstrip("@")
            violations.append(
                f"  L{line_no} d{depth} {speaker}: status marker on nested reply is ignored"
            )
    if not violations:
        return (
            0,
            f"no violations in {spec_path} (inline-discussion enforces RESOLVED at write time)",
        )
    msg = (
        f"VIOLATIONS: {len(violations)} reply line(s) with ignored status marker:\n"
        + "\n".join(violations)
    )
    return (1, msg)
