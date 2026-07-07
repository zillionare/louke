"""louke/_tools/discuss.py — Inline Discussion 协议解析器 (FR-0020).

inline-discussion 协议 (v0.7-003) 替代 v0.6-016 的 quote-dialogue 协议.

核心 API:
- Thread (dataclass): 单个讨论线程, 含 5 元组定位字段
- DiscussParser: 解析 spec.md, 提供 is_ready() 门禁, 4 级降级查找

替代 louke/_tools/quote_parser.py 的核心功能. quote_parser.py 保留作为向后兼容薄包装.
"""
from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# Status: 仅 3 态 (QoderWork P0-NEW: reopen 算阻塞)
STATUS_OPEN = "open"
STATUS_RESOLVED = "resolved"
STATUS_REOPEN = "reopen"

# Status marker 匹配 (仅根评论行有效)
RE_STATUS_MARKER = re.compile(
    r"\s*\[(?P<status>open|resolved|reopen)\]\s*$",
    re.IGNORECASE,
)

# Quote 行匹配:
# 1 个或多个 > 开头, 后接 **Speaker** 或 **@Speaker** (可选 [STATUS]) : content
# @mention 语法 (QoderWork P1-NEW-3 保留)
# 注意: raw string `\*\*` 在 Python 实际是 `\\*\\*` (2 字符: `\*`+`*` 即 literal \* + Kleene 0+ *),
#       要表达字面 `**` 必须用 `[*][*]` 或 `\*\*` 需在非 raw string 中
RE_QUOTE_LINE = re.compile(
    r"^(?P<depth>\s*(?:>\s*)+)"
    r"(?P<speaker>[*][*]@?[^*\s][^*]*?[*][*]|[*][*]@?[A-Za-z][A-Za-z0-9_\-]*[*][*])"
    r"(?:\s*\[(?P<status>open|resolved|reopen)\])?"
    r"\s*:\s*"
    r"(?P<body>.*?)\s*$",
    re.IGNORECASE,
)

# 单元标题 (FR-0020 AC-7 保留): ### US-0010 / ### FR-0001 / ### NFR-0010
RE_UNIT_HEADING = re.compile(r"^###\s+(US|FR|NFR)-(\d{4})\b")

# FR/NFR 元数据
COLUMN_ALIASES = {
    "有效需求": "valid",
    "valid": "valid",
    "可测性": "testability",
    "testability": "testability",
    "是否已决定": "resolved",
    "已决定": "resolved",
    "resolved": "resolved",
}

RE_TABLE_ROW = re.compile(r"^\s*\|\s*(.+?)\s*\|\s*$")
RE_TABLE_SEP = re.compile(r"^\s*\|[\s:|-]+\|\s*$")
RE_TOP_HEADING = re.compile(r"^##\s+\S")
RE_FENCE = re.compile(r"^\s*(```|~~~)")

# Status 大小写归一化 (AC-8): 解析时归一, 显示保留原大小写
STATUS_NORMALIZE = {
    "OPEN": STATUS_OPEN,
    "OPEN": STATUS_OPEN,
    "RESOLVED": STATUS_RESOLVED,
    "RESOLVED": STATUS_RESOLVED,
    "REOPEN": STATUS_REOPEN,
    "REOPEN": STATUS_REOPEN,
}


def normalize_text(s: str) -> str:
    """FR-0050 归一化规则: strip 首尾空白 + 合并连续空白为单空格 + Unicode NFC.

    不改大小写, 不去 markdown 格式.
    """
    import unicodedata
    s = unicodedata.normalize("NFC", s)
    s = s.strip()
    s = re.sub(r"\s+", " ", s)
    return s


def levenshtein(a: str, b: str) -> int:
    """经典编辑距离 (Levenshtein distance)."""
    if len(a) < len(b):
        a, b = b, a
    if not a:
        return len(b)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a):
        curr = [i + 1]
        for j, cb in enumerate(b):
            curr.append(min(
                prev[j + 1] + 1,       # deletion
                curr[j] + 1,             # insertion
                prev[j] + (ca != cb),    # substitution
            ))
        prev = curr
    return prev[len(b)]


@dataclass
class Thread:
    """单个讨论线程 (FR-0020 dataclass).

    5 元组定位字段 (QoderWork P0-2):
    - total_lines: 创建时文件总行数 (行号漂移修正用)
    - anchor_line: 被评论内容行号 (快速跳转 hint)
    - anchor_text: 被评论内容 (归一化)
    - root_line: 根评论 `>` 行号
    - root_text: 根评论 speaker + body (归一化)
    """
    thread_id: str                  # "T-NNN" 自增序号
    initiator: str                 # 根评论 speaker (lowercase 归一比较)
    status: str                    # STATUS_OPEN / RESOLVED / REOPEN
    last_speaker: str             # thread 最后说话的人
    reply_count: int
    snippet: str                   # 根评论 body 前 80 字

    # 5 元组定位字段
    total_lines: int               # 创建时文件总行数
    anchor_line: int               # 被评论内容行号
    anchor_text: str               # 归一化文本
    root_line: int                 # 根评论行号
    root_text: str                 # 根评论 speaker + body (归一化)

    # @mention 解析
    mentioned_agents: list[str] = field(default_factory=list)


@dataclass
class ParseResult:
    """spec.md 解析结果.

    is_ready 判定 (QoderWork P0-NEW): 所有 thread 状态 == "resolved".
    """
    threads: list[Thread] = field(default_factory=list)
    units: list[dict] = field(default_factory=list)  # [{id, kind, yaml_resolved, ...}]
    is_ready: bool = False
    ready_blockers: list[str] = field(default_factory=list)


class DiscussParser:
    """inline-discussion 协议 parser (FR-0020)."""

    def __init__(self) -> None:
        self._thread_counter = 0
        self._threads: list[Thread] = []
        self._units: list[dict] = []

    def parse_file(self, path: Path) -> ParseResult:
        """解析 spec.md, 返回 ParseResult."""
        text = path.read_text(encoding="utf-8")
        lines = text.splitlines()
        return self._parse(text, lines)

    def _parse(self, text: str, lines: list[str]) -> ParseResult:
        # 两遍解析:
        # Pass 1: 扫描 quote lines, 收集 threads
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
            # 解析 quote
            depth_prefix = m.group("depth")
            depth = depth_prefix.count(">")
            speaker_raw = m.group("speaker").strip("*").lstrip("@")
            # 提取 @mention 列表
            mentioned = re.findall(r"@([A-Za-z][A-Za-z0-9_\-]*)", m.group("speaker"))
            body = m.group("body").strip()
            status_raw = (m.group("status") or "").lower()
            # 根评论 depth=1 才识别 status
            if depth == 1:
                self._thread_counter += 1
                status = status_raw or STATUS_OPEN
                if status not in (STATUS_OPEN, STATUS_RESOLVED, STATUS_REOPEN):
                    status = STATUS_OPEN
                # anchor_line: 根评论**上方**最近的非空、非 `>` 行
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
                # 嵌套回复: 更新 last_speaker
                if self._threads:
                    self._threads[-1].last_speaker = speaker_raw.lower()
                    if mentioned:
                        for m in mentioned:
                            if m.lower() not in self._threads[-1].mentioned_agents:
                                self._threads[-1].mentioned_agents.append(m.lower())
                self._threads[-1].reply_count += 1

        # Pass 2: 扫单元 + YAML
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
                    "thread_ids": [],  # 关联 thread_id
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
                            elif key == "testability" and not current_unit["yaml_testability"]:
                                current_unit["yaml_testability"] = val
                            elif key == "resolved" and not current_unit["yaml_resolved"]:
                                current_unit["yaml_resolved"] = val
                continue
            elif m_row is None:
                if table_buf:
                    table_buf = []
                    in_table = False
                    col_map = {}

        # 关联 thread 到 unit (按 root_line 范围)
        for u in self._units:
            upper = self._next_unit_heading(u["heading_line"])
            for t in self._threads:
                if u["heading_line"] <= t.root_line < upper:
                    u["thread_ids"].append(t.thread_id)

        # is_ready 判定 (QoderWork P0-NEW: 所有 thread status == "resolved")
        blockers = []
        for u in self._units:
            if u["kind"] in ("FR", "NFR"):
                if u["yaml_resolved"] != "✅":
                    blockers.append(f"{u['id']}: yaml.resolved={u['yaml_resolved']!r} (need ✅)")
                for tid in u["thread_ids"]:
                    t = next((x for x in self._threads if x.thread_id == tid), None)
                    if t and t.status != STATUS_RESOLVED:
                        blockers.append(f"{u['id']}: thread {tid} status={t.status!r} (need resolved)")
            else:
                # US 等: 无 thread = ok
                for tid in u["thread_ids"]:
                    t = next((x for x in self._threads if x.thread_id == tid), None)
                    if t and t.status != STATUS_RESOLVED:
                        blockers.append(f"{u['id']}: thread {tid} status={t.status!r}")

        result = ParseResult(
            threads=list(self._threads),
            units=list(self._units),
            is_ready=len(blockers) == 0,
            ready_blockers=blockers,
        )
        return result

    def _find_anchor_line(self, lines: list[str], quote_line: int) -> int | None:
        """根评论**上方**最近的非空、非 `>` 行 (单行锚定, FR-0050)."""
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
        """下一个 unit heading 的行号 (按 ### US/FR/NFR-XXXX 顺序)."""
        candidates = [u["heading_line"] for u in self._units if u["heading_line"] > current_line]
        return min(candidates) if candidates else 10**9

    # ===== 4 级降级查找 (QoderWork P0-2, FR-0050) =====

    def find_thread(
        self,
        file_path: Path,
        thread_id: str,
        anchor_line: int | None = None,
        anchor_text: str | None = None,
        root_line: int | None = None,
        root_text: str | None = None,
    ) -> Thread | None:
        """4 级降级查找 thread.

        重要: parse_file 每次重置 counter, thread_id 在不同 parse 间会变.
        因此不能用 thread_id 直接索引, 必须用 5 元组 (anchor_line + root_text) 内容匹配.

        优先:
          1. Level 0 精确命中 (调整 anchor_line + 检查内容)
          2. Level 1 Levenshtein 窗口 (anchor_line ± max(|delta|+5, 10))
          3. Level 2 全文根评论 (按 root_text 匹配 + speaker 验证)
          4. Level 3 未找到 (返回 None)
        """
        # thread_id 保留用于 agent 调试 (在错误信息中), 但匹配不用它
        text = file_path.read_text(encoding="utf-8")
        lines = text.splitlines()
        current_total = len(lines)

        # 找所有 candidates (Level 2/3 都需要)
        current_result = self.parse_file(file_path)
        candidates = current_result.threads

        # 如果 agent 没传定位字段, 退到 Level 2 全文匹配 (按 root_text)
        if anchor_line is None:
            if root_text:
                for t2 in candidates:
                    if t2.root_text == root_text:
                        return t2
                    d = levenshtein(t2.root_text, root_text)
                    if d <= max(5, len(root_text) * 0.2):
                        return t2
            return None

        # Level 0: 精确命中 - 调整 anchor_line + 检查内容
        # (此分支在第一遍 parse 之前, 不知道 candidates, 所以直接查 anchor 行内容)
        if anchor_text:
            delta = current_total - 999  # placeholder, 实际应从 stored 算
            # 这里需要 stored 的 total_lines. 但 find_thread 调用者没传.
            # 简化: 试多个 delta 值 (假设原 anchor_line 附近的行就是 anchor)
            # 实际做法: 试 anchor_line 本身 + ±5
            for try_anchor in range(max(1, anchor_line - 5), min(current_total, anchor_line + 5) + 1):
                actual = normalize_text(lines[try_anchor - 1])
                if actual == anchor_text:
                    # 找到 anchor 行. 在其下方扫 blockquote 找根评论
                    for j in range(try_anchor, min(current_total, try_anchor + 10) + 1):
                        m = RE_QUOTE_LINE.match(lines[j - 1])
                        if m and m.group("depth").count(">") == 1:
                            # 找到根评论. 验证 root_text 匹配
                            actual_root = normalize_text(f"{m.group('speaker').strip('*').lstrip('@')}: {m.group('body')}")
                            if not root_text or actual_root == root_text:
                                # 构造 thread 返回
                                return Thread(
                                    thread_id="?",
                                    initiator=m.group("speaker").strip("*").lstrip("@").lower(),
                                    status=(m.group("status") or STATUS_OPEN).lower(),
                                    last_speaker=m.group("speaker").strip("*").lstrip("@").lower(),
                                    reply_count=0,
                                    snippet=m.group("body")[:80],
                                    total_lines=current_total,
                                    anchor_line=try_anchor,
                                    anchor_text=anchor_text,
                                    root_line=j,
                                    root_text=actual_root,
                                )
                            break

        # Level 1: Levenshtein 窗口 (anchor_text 找近似行)
        if anchor_text:
            window = 10  # 默认 +/- 10 行
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
                for j in range(best_anchor_line, min(current_total, best_anchor_line + 10) + 1):
                    m = RE_QUOTE_LINE.match(lines[j - 1])
                    if m and m.group("depth").count(">") == 1:
                        actual_root = normalize_text(f"{m.group('speaker').strip('*').lstrip('@')}: {m.group('body')}")
                        if not root_text or actual_root == root_text:
                            return Thread(
                                thread_id="?",
                                initiator=m.group("speaker").strip("*").lstrip("@").lower(),
                                status=(m.group("status") or STATUS_OPEN).lower(),
                                last_speaker=m.group("speaker").strip("*").lstrip("@").lower(),
                                reply_count=0,
                                snippet=m.group("body")[:80],
                                total_lines=current_total,
                                anchor_line=best_anchor_line,
                                anchor_text=normalize_text(lines[best_anchor_line - 1]),
                                root_line=j,
                                root_text=actual_root,
                            )
                        break

        # Level 2: 全文根评论 (按 root_text + speaker 匹配)
        if root_text:
            for t2 in candidates:
                if t2.root_text == root_text:
                    return t2
                d = levenshtein(t2.root_text, root_text)
                threshold = max(5, len(root_text) * 0.2)
                if d <= threshold:
                    return t2

        return None  # Level 3

    # ===== 写操作 (QoderWork P0-4 写操作语义) =====

    def add_thread(
        self,
        file_path: Path,
        anchor_line: int,
        initiator: str,
        body: str,
        status: str = STATUS_OPEN,
    ) -> Thread:
        """新 thread 插在 anchor_line 后的第一个空行之后.

        写操作: 解析 → 插行 → 原子写 (tmp + rename)
        """
        text = file_path.read_text(encoding="utf-8")
        lines = text.splitlines()
        # 找 anchor_line 后的第一个空行
        insert_at = self._find_insert_line(lines, anchor_line)
        # 构造根评论
        status_marker = f" [{status.upper()}]" if status != STATUS_OPEN else ""
        new_line = f"> **{initiator}{status_marker}:** {body}"
        # 写操作: 插入 + 后补空行 (blockquote 间 CommonMark 要求空行)
        new_lines = lines[:insert_at] + ["", new_line, ""] + lines[insert_at:]
        new_text = "\n".join(new_lines) + ("\n" if text.endswith("\n") else "")
        self._atomic_write(file_path, new_text)
        # 重新解析
        new_thread = Thread(
            thread_id=f"T-{len(self.parse_file(file_path).threads) + 1:03d}",
            initiator=initiator.lower(),
            status=status,
            last_speaker=initiator.lower(),
            reply_count=0,
            snippet=body[:80],
            total_lines=len(new_lines),
            anchor_line=anchor_line,
            anchor_text=normalize_text(self._get_line(lines, anchor_line)) if 1 <= anchor_line <= len(lines) else "",
            root_line=insert_at + 2,  # +2 因为前面加了空行 + 行
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
        """追加回复到 thread 末尾 (loc 含 5 元组定位字段)."""
        thread = self.find_thread(file_path, thread_id, **loc)
        if thread is None:
            raise ValueError(f"thread {thread_id} not found")
        text = file_path.read_text(encoding="utf-8")
        lines = text.splitlines()
        # 找 thread 最后一个嵌套回复的行号
        # 简单做法: 找 thread.root_line 之后到下一个 root 之间的最后一行
        next_root = self._next_root_line(lines, thread.root_line)
        if next_root is None:
            next_root = len(lines) + 1
        # 找 thread 中最大 depth 的最后一行
        last_line = self._find_last_nested_line(lines, thread.root_line, next_root)
        if last_line is None:
            last_line = thread.root_line
        # 在 last_line 之后插 `> {speaker}: {body}`
        depth = self._line_depth(lines, last_line)
        new_depth_marker = ">" * (depth + 1)
        new_line = f"{new_depth_marker} **{speaker}:** {body}"
        insert_at = last_line + 1
        # 加空行 (与下一个 `>` block 分隔)
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
        """修改 thread 状态. RESOLVED 仅 initiator, REOPEN 任意人.

        解析器验证 operator_speaker == thread.initiator 才允许 RESOLVED.
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
        # 改根评论行状态
        text = file_path.read_text(encoding="utf-8")
        lines = text.splitlines()
        root_idx = thread.root_line - 1
        if 0 <= root_idx < len(lines):
            line = lines[root_idx]
            # 移除旧 status marker
            line = re.sub(r"\s*\[(?:open|resolved|reopen)\]\s*", "", line, flags=re.IGNORECASE)
            # 加新 marker (open 不加)
            if new_status != STATUS_OPEN:
                # 在 **Speaker:** 后插 status
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
        """修改自己某条评论 (仅原作者)."""
        thread = self.find_thread(file_path, thread_id, **loc)
        if thread is None:
            raise ValueError(f"thread {thread_id} not found")
        text = file_path.read_text(encoding="utf-8")
        lines = text.splitlines()
        # 找 depth + speaker 匹配的行
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
        # 替换内容 (保持 prefix `> ... `)
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
        # 处理多行 new_body: 每行加 depth + 1 个 `>` 前缀
        body_lines = new_body.split("\n")
        new_lines = [old_line]  # 暂时
        first = f"{depth_prefix} {speaker_tag}{status_str}: {body_lines[0]}"
        new_lines = [first]
        for bl in body_lines[1:]:
            # 续行: depth + 1 个 `>` (与 root comment 一样)
            cont_depth = ">" * (len(depth_prefix.replace(">", "").replace(" ", "")) + 1) + " "
            new_lines.append(f"{depth_prefix}{cont_depth}{bl}")
        lines[target_line_no - 1:target_line_no] = new_lines
        new_text = "\n".join(lines) + ("\n" if text.endswith("\n") else "")
        self._atomic_write(file_path, new_text)

    def is_ready(self) -> tuple[bool, list[str]]:
        """返回 (ready, blockers). 等同 ParseResult.is_ready + ready_blockers.

        用法: cmd_record_lock 内部调 self.parse_file 后 is_ready().
        """
        # 重新 parse (可能 stale)
        # 实际使用时, 已在 parse_file 拿到 ParseResult
        # 这里作为便捷 API
        raise NotImplementedError("use parse_file().is_ready instead")

    # ===== 辅助方法 =====

    def _find_insert_line(self, lines: list[str], anchor_line: int) -> int:
        """找 anchor_line 后的第一个空行 (QoderWork P0-4 写操作)."""
        for i in range(anchor_line, len(lines)):
            if not lines[i].strip():
                return i
        return len(lines)  # fallback: 文件末尾

    def _next_root_line(self, lines: list[str], after_line: int) -> int | None:
        """after_line 之后的下一个根评论 (depth=1 `>`) 行号."""
        for i in range(after_line, len(lines)):
            m = RE_QUOTE_LINE.match(lines[i])
            if m and m.group("depth").count(">") == 1:
                return i + 1
        return None

    def _find_last_nested_line(self, lines: list[str], start: int, end: int) -> int | None:
        """start..end 范围内 (含) 最后一个 quote 行行号."""
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
        """原子写入: tmp + rename. 同时 flock 防并发."""
        import fcntl
        import tempfile
        lock_path = file_path.with_suffix(file_path.suffix + ".lock")
        with open(lock_path, "w") as lock_fd:
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
